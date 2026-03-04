# Healthcare-grade Azure: Front Door Premium + WAF, App Service, Postgres + Redis (private), Key Vault
terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
  # backend "azurerm" { }  # Uncomment and set for remote state
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = merge(var.tags, {
    project     = var.project_name
    environment = var.environment
    managed_by   = "terraform"
  })
}

# Resource group
resource "azurerm_resource_group" "rg" {
  name     = "rg-${local.name_prefix}"
  location = var.location
  tags     = local.common_tags
}

# Log Analytics + App Insights (no PHI in logs; use for requests/errors only)
resource "azurerm_log_analytics_workspace" "law" {
  name                = "law-${local.name_prefix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  tags                = local.common_tags
}

resource "azurerm_application_insights" "ai" {
  name                = "ai-${local.name_prefix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  workspace_id        = azurerm_log_analytics_workspace.law.id
  application_type    = "other"
  tags                = local.common_tags
}

# VNet + subnets: subnet-app (App Service VNet integration), subnet-private-endpoints (Postgres + Redis PEs)
resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-${local.name_prefix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  address_space       = ["10.0.0.0/16"]
  tags                = local.common_tags
}

resource "azurerm_subnet" "app" {
  name                 = "subnet-app"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
  delegation {
    name = "Microsoft.Web.serverFarms"
    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_subnet" "private_endpoints" {
  name                 = "subnet-private-endpoints"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.2.0/24"]
  private_endpoint_network_policies = "Disabled"
}

# Private DNS zones (link to VNet so App Service resolves Postgres/Redis by private hostname)
resource "azurerm_private_dns_zone" "postgres" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "postgres-dns-link"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
}

resource "azurerm_private_dns_zone" "redis" {
  name                = "privatelink.redis.cache.windows.net"
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "redis" {
  name                  = "redis-dns-link"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.redis.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
}

# Key Vault (secrets: SECRET_KEY, DB password, Redis URL, AZURE_AD_CLIENT_SECRET)
resource "azurerm_key_vault" "kv" {
  name                        = "kv-${replace(local.name_prefix, "-", "")}"
  location                    = azurerm_resource_group.rg.location
  resource_group_name         = azurerm_resource_group.rg.name
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  soft_delete_retention_days   = 7
  purge_protection_enabled    = false
  enable_rbac_authorization   = true
  tags                        = local.common_tags
}

data "azurerm_client_config" "current" {}

# Grant current identity (e.g. run Terraform as) access to KV to add secrets; App Service MI gets access below
resource "azurerm_role_assignment" "kv_terraform" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# PostgreSQL Flexible Server — public access OFF, private endpoint only
resource "azurerm_postgresql_flexible_server" "pg" {
  name                   = "psql-${replace(local.name_prefix, "-", "")}"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  version                = "15"
  administrator_login    = var.postgres_admin_user
  administrator_password = var.postgres_admin_password
  sku_name               = "GP_Standard_D2s_v3"
  storage_mb             = 32768
  zone                   = "1"
  tags                   = local.common_tags

  public_network_access_enabled = false
  delegated_subnet_id           = null
  private_dns_zone_id           = azurerm_private_dns_zone.postgres.id
}

resource "azurerm_postgresql_flexible_server_database" "db" {
  name      = "rock_access"
  server_id = azurerm_postgresql_flexible_server.pg.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Private endpoint for Postgres
resource "azurerm_private_endpoint" "pg" {
  name                = "pe-pg-${local.name_prefix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = local.common_tags

  private_service_connection {
    name                           = "psc-pg"
    private_connection_resource_id = azurerm_postgresql_flexible_server.pg.id
    is_manual_connection           = false
    subresource_names              = ["postgresqlServer"]
  }
}

data "azurerm_network_interface" "pg_pe" {
  name                = split("/", azurerm_private_endpoint.pg.network_interface_ids[0])[8]
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_private_dns_a_record" "pg" {
  name                = azurerm_postgresql_flexible_server.pg.name
  zone_name           = azurerm_private_dns_zone.postgres.name
  resource_group_name = azurerm_resource_group.rg.name
  ttl                 = 300
  records             = [data.azurerm_network_interface.pg_pe.private_ip_address]
}

# Azure Cache for Redis — Premium for private endpoint
resource "azurerm_redis_cache" "redis" {
  name                = "redis-${replace(local.name_prefix, "-", "")}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  capacity            = var.redis_capacity
  family              = var.redis_family
  sku_name            = var.redis_sku
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"
  tags                = local.common_tags

  redis_configuration {}
}

resource "azurerm_private_endpoint" "redis" {
  name                = "pe-redis-${local.name_prefix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = local.common_tags

  private_service_connection {
    name                           = "psc-redis"
    private_connection_resource_id = azurerm_redis_cache.redis.id
    is_manual_connection           = false
    subresource_names              = ["redisCache"]
  }
}

# Redis private DNS A record (primary connection hostname → private IP)
# Resolve Redis private endpoint NIC to get private IP for DNS A record
data "azurerm_network_interface" "redis_pe" {
  count               = length(azurerm_private_endpoint.redis.network_interface_ids) > 0 ? 1 : 0
  name                = split("/", azurerm_private_endpoint.redis.network_interface_ids[0])[8]
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_private_dns_a_record" "redis" {
  name                = split(".", azurerm_redis_cache.redis.hostname)[0]
  zone_name           = azurerm_private_dns_zone.redis.name
  resource_group_name = azurerm_resource_group.rg.name
  ttl                 = 300
  records             = length(data.azurerm_network_interface.redis_pe) > 0 ? [data.azurerm_network_interface.redis_pe[0].private_ip_address] : []
}

# Key Vault secrets (no PHI); App Service reads via Managed Identity
resource "random_password" "django_secret" {
  length  = 50
  special = true
}

resource "azurerm_key_vault_secret" "django_secret_key" {
  name         = "DJANGO-SECRET-KEY"
  value        = coalesce(var.django_secret_key, random_password.django_secret.result)
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_terraform]
}

resource "azurerm_key_vault_secret" "db_password" {
  name         = "DB-PASSWORD"
  value        = var.postgres_admin_password
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_terraform]
}

# Redis private hostname so App Service (VNet) resolves via private DNS zone
locals {
  redis_private_hostname = "${split(".", azurerm_redis_cache.redis.hostname)[0]}.privatelink.redis.cache.windows.net"
}

resource "azurerm_key_vault_secret" "redis_url" {
  name         = "REDIS-URL"
  value        = "rediss://:${azurerm_redis_cache.redis.primary_access_key}@${local.redis_private_hostname}:${azurerm_redis_cache.redis.ssl_port}"
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_terraform]
}

resource "azurerm_key_vault_secret" "azure_ad_tenant_id" {
  count        = var.azure_ad_tenant_id != "" ? 1 : 0
  name         = "AZURE-AD-TENANT-ID"
  value        = var.azure_ad_tenant_id
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_terraform]
}

resource "azurerm_key_vault_secret" "azure_ad_client_id" {
  count        = var.azure_ad_client_id != "" ? 1 : 0
  name         = "AZURE-AD-CLIENT-ID"
  value        = var.azure_ad_client_id
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_terraform]
}

resource "azurerm_key_vault_secret" "azure_ad_client_secret" {
  count        = var.azure_ad_client_secret != "" ? 1 : 0
  name         = "AZURE-AD-CLIENT-SECRET"
  value        = var.azure_ad_client_secret
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_terraform]
}

# App Service Plan + Web App (backend API)
resource "azurerm_service_plan" "asp" {
  name                = "asp-${local.name_prefix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  os_type             = "Linux"
  sku_name            = var.app_service_sku
  tags                = local.common_tags
}

resource "azurerm_linux_web_app" "api" {
  name                = "app-${replace(local.name_prefix, "-", "")}-api"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  service_plan_id     = azurerm_service_plan.asp.id
  https_only          = true
  tags                = local.common_tags

  identity {
    type = "SystemAssigned"
  }

  app_settings = merge({
    "WEBSITES_PORT"                      = "8000"
    "SCM_DO_BUILD_DURING_DEPLOYMENT"    = "true"
    "DJANGO_DEBUG"                      = "False"
    "ALLOWED_HOSTS"                     = var.api_fqdn
    "CORS_ALLOWED_ORIGINS"              = "https://${var.frontend_fqdn}"
    "CSRF_TRUSTED_ORIGINS"              = "https://${var.frontend_fqdn}"
    "FRONTEND_URL"                      = "https://${var.frontend_fqdn}"
    "ONLY_MICROSOFT_LOGIN"              = "true"
    "SECRET_KEY"                        = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.kv.vault_uri}secrets/${azurerm_key_vault_secret.django_secret_key.name}/)"
    "DB_HOST"                           = "${azurerm_postgresql_flexible_server.pg.name}.privatelink.postgres.database.azure.com"
    "DB_NAME"                           = azurerm_postgresql_flexible_server_database.db.name
    "DB_USER"                           = "${var.postgres_admin_user}@${azurerm_postgresql_flexible_server.pg.name}"
    "DB_PASSWORD"                       = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.kv.vault_uri}secrets/${azurerm_key_vault_secret.db_password.name}/)"
    "DB_PORT"                           = "5432"
    "REDIS_URL"                         = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.kv.vault_uri}secrets/${azurerm_key_vault_secret.redis_url.name}/)"
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.ai.connection_string
  }, var.azure_ad_tenant_id != "" && var.azure_ad_client_id != "" && var.azure_ad_client_secret != "" ? {
    "AZURE_AD_TENANT_ID"     = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.kv.vault_uri}secrets/${azurerm_key_vault_secret.azure_ad_tenant_id[0].name}/)"
    "AZURE_AD_CLIENT_ID"     = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.kv.vault_uri}secrets/${azurerm_key_vault_secret.azure_ad_client_id[0].name}/)"
    "AZURE_AD_CLIENT_SECRET" = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.kv.vault_uri}secrets/${azurerm_key_vault_secret.azure_ad_client_secret[0].name}/)"
  } : {})

  site_config {
    always_on        = true
    ftps_state       = "Disabled"
    health_check_path = "/api/health/"
    http2_enabled    = true
    application_stack {
      python_version = "3.11"
    }
  }

  virtual_application {
    virtual_path    = "/"
    physical_path  = "site/wwwroot"
  }
}

# VNet integration for App Service (so it can reach Postgres/Redis private endpoints)
resource "azurerm_app_service_virtual_network_swift_connection" "api" {
  app_service_id = azurerm_linux_web_app.api.id
  subnet_id      = azurerm_subnet.app.id
}

# Key Vault: grant App Service Managed Identity access to read secrets
resource "azurerm_role_assignment" "kv_api" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_web_app.api.identity[0].principal_id
}

# Optional: restrict backend to Front Door only via access restrictions (handled by Front Door origin; optional IP allow list)
# You can add azurerm_linux_web_app_slot or app_service custom access_restriction block for Front Door subnet + corporate IPs.

# Front Door Premium + WAF
resource "azurerm_cdn_frontdoor_profile" "afd" {
  name                = "afd-${replace(local.name_prefix, "-", "")}"
  resource_group_name = azurerm_resource_group.rg.name
  sku_name            = var.front_door_sku
  tags                = local.common_tags
}

resource "azurerm_cdn_frontdoor_firewall_policy" "waf" {
  name                              = "waf-${local.name_prefix}"
  resource_group_name               = azurerm_resource_group.rg.name
  sku_name                          = azurerm_cdn_frontdoor_profile.afd.sku_name
  enabled                           = true
  mode                              = "Prevention"
  redirect_url                      = "https://${var.frontend_fqdn}/blocked"
  custom_block_response_status_code = 403
  custom_block_response_body        = base64encode("Access denied by WAF.")
  tags                              = local.common_tags

  custom_rule {
    name                       = "RateLimit"
    enabled                    = true
    priority                   = 100
    rate_limit_duration_in_minutes = 1
    rate_limit_threshold        = 100
    type                       = "RateLimitRule"
    action                     = "Block"
  }

  managed_rule {
    type    = "Microsoft_DefaultRuleSet"
    version = "1.0"
    action  = "Block"
  }
  managed_rule {
    type    = "Microsoft_ManagedRuleSet"
    version = "1.0"
    action  = "Block"
    rule_group_override {
      rule_group_name = "PHP"
      rule {
        rule_id = "933111"
        enabled = false
      }
    }
  }
}

# Front Door origin groups and endpoints: API origin = App Service default hostname (backend only via FD)
resource "azurerm_cdn_frontdoor_origin_group" "api" {
  name                    = "og-api"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.afd.id
  session_affinity_enabled = false
  restore_traffic_time_to_healed_origin_in_minutes = 10
  health_probe {
    interval_in_seconds = 60
    path                = "/api/health/"
    request_type        = "HEAD"
    protocol            = "Https"
  }
  load_balancing {
    additional_latency_in_milliseconds = 0
    sample_size                        = 16
    successful_samples_required        = 3
    unsuccessful_samples_required     = 3
  }
}

resource "azurerm_cdn_frontdoor_origin" "api" {
  name                           = "origin-api"
  cdn_frontdoor_origin_group_id   = azurerm_cdn_frontdoor_origin_group.api.id
  host_name                      = "${azurerm_linux_web_app.api.name}.azurewebsites.net"
  origin_host_header             = "${azurerm_linux_web_app.api.name}.azurewebsites.net"
  priority                       = 1
  weight                         = 1000
  certificate_name_check_enabled = true
  http_port                      = 80
  https_port                     = 443
}

resource "azurerm_cdn_frontdoor_origin_group" "frontend" {
  count                   = var.frontend_origin_hostname != "" ? 1 : 0
  name                    = "og-frontend"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.afd.id
  session_affinity_enabled = false
  restore_traffic_time_to_healed_origin_in_minutes = 10
  health_probe {
    interval_in_seconds = 60
    path                = "/"
    request_type        = "GET"
    protocol            = "Https"
  }
  load_balancing {
    additional_latency_in_milliseconds = 0
    sample_size                        = 16
    successful_samples_required        = 3
    unsuccessful_samples_required     = 3
  }
}

resource "azurerm_cdn_frontdoor_origin" "frontend" {
  count                          = var.frontend_origin_hostname != "" ? 1 : 0
  name                           = "origin-frontend"
  cdn_frontdoor_origin_group_id  = azurerm_cdn_frontdoor_origin_group.frontend[0].id
  host_name                      = var.frontend_origin_hostname
  origin_host_header             = var.frontend_origin_hostname
  priority                       = 1
  weight                         = 1000
  certificate_name_check_enabled = true
  http_port                      = 80
  https_port                     = 443
}

# Front Door routes and endpoints
resource "azurerm_cdn_frontdoor_endpoint" "afd" {
  name                    = "endpoint-${replace(local.name_prefix, "-", "")}"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.afd.id
  tags                    = local.common_tags
}

resource "azurerm_cdn_frontdoor_route" "api" {
  name                            = "route-api"
  cdn_frontdoor_endpoint_id       = azurerm_cdn_frontdoor_endpoint.afd.id
  cdn_frontdoor_origin_group_id   = azurerm_cdn_frontdoor_origin_group.api.id
  cdn_frontdoor_origin_ids        = [azurerm_cdn_frontdoor_origin.api.id]
  cdn_frontdoor_rule_set_ids      = []
  supported_protocols             = ["Https"]
  patterns_to_match               = ["/*"]
  forwarding_protocol             = "HttpsOnly"
  link_to_default_domain           = false
  cdn_frontdoor_custom_domain_ids = [azurerm_cdn_frontdoor_custom_domain.api.id]
}

resource "azurerm_cdn_frontdoor_route" "frontend" {
  count                           = var.frontend_origin_hostname != "" ? 1 : 0
  name                            = "route-frontend"
  cdn_frontdoor_endpoint_id       = azurerm_cdn_frontdoor_endpoint.afd.id
  cdn_frontdoor_origin_group_id   = azurerm_cdn_frontdoor_origin_group.frontend[0].id
  cdn_frontdoor_origin_ids        = [azurerm_cdn_frontdoor_origin.frontend[0].id]
  cdn_frontdoor_rule_set_ids      = []
  supported_protocols             = ["Https"]
  patterns_to_match               = ["/*"]
  forwarding_protocol             = "HttpsOnly"
  link_to_default_domain          = false
  cdn_frontdoor_custom_domain_ids = [azurerm_cdn_frontdoor_custom_domain.frontend[0].id]
}

# Custom domains + TLS: attach students-api.hasc.net and students.hasc.net to Front Door
# You must own the DNS and add CNAME to Front Door endpoint; then add custom domain in Azure.
resource "azurerm_cdn_frontdoor_custom_domain" "api" {
  name                     = "domain-api"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.afd.id
  host_name                = var.api_fqdn
  cdn_frontdoor_certificate_id = null
  certificate_type         = "ManagedCertificate"
  tls_minimum_version      = "TLS12"
}

resource "azurerm_cdn_frontdoor_custom_domain" "frontend" {
  count                    = var.frontend_origin_hostname != "" ? 1 : 0
  name                     = "domain-frontend"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.afd.id
  host_name                = var.frontend_fqdn
  cdn_frontdoor_certificate_id = null
  certificate_type         = "ManagedCertificate"
  tls_minimum_version      = "TLS12"
}

# Link WAF policy to Front Door profile (applies to custom domains)
resource "azurerm_cdn_frontdoor_security_policy" "waf" {
  name                     = "security-waf"
  cdn_frontdoor_profile_id  = azurerm_cdn_frontdoor_profile.afd.id
  security_policies {
    firewall {
      association {
        domain_ids         = concat([azurerm_cdn_frontdoor_custom_domain.api.id], var.frontend_origin_hostname != "" ? [azurerm_cdn_frontdoor_custom_domain.frontend[0].id] : [])
        patterns_to_match  = ["/*"]
      }
      cdn_frontdoor_firewall_policy_id = azurerm_cdn_frontdoor_firewall_policy.waf.id
    }
  }
}

# Diagnostics: App Service and Front Door to Log Analytics
resource "azurerm_monitor_diagnostic_setting" "api" {
  name                       = "diag-api"
  target_resource_id         = azurerm_linux_web_app.api.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  metric {
    category = "AllMetrics"
    enabled  = true
  }
  enabled_log {
    category = "AppServiceHTTPLogs"
  }
  enabled_log {
    category = "AppServiceAppLogs"
  }
  enabled_log {
    category = "AppServicePlatformLogs"
  }
}

resource "azurerm_monitor_diagnostic_setting" "afd" {
  name                       = "diag-afd"
  target_resource_id         = azurerm_cdn_frontdoor_profile.afd.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  metric {
    category = "AllMetrics"
    enabled  = true
  }
}
