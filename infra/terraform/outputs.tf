# Healthcare-grade deployment outputs

output "resource_group_name" {
  value       = azurerm_resource_group.rg.name
  description = "Resource group name."
}

output "backend_app_name" {
  value       = azurerm_linux_web_app.api.name
  description = "Backend App Service name (default hostname: <name>.azurewebsites.net)."
}

output "backend_default_hostname" {
  value       = "https://${azurerm_linux_web_app.api.default_hostname}"
  description = "Backend default URL (use only for testing; production uses students-api.hasc.net via Front Door)."
}

output "front_door_endpoint_hostname" {
  value       = azurerm_cdn_frontdoor_endpoint.afd.host_name
  description = "Front Door endpoint hostname; CNAME students.hasc.net and students-api.hasc.net to this."
}

output "frontend_fqdn" {
  value       = var.frontend_fqdn
  description = "Public frontend DNS (students.hasc.net)."
}

output "api_fqdn" {
  value       = var.api_fqdn
  description = "Public API DNS (students-api.hasc.net)."
}

output "key_vault_name" {
  value       = azurerm_key_vault.kv.name
  description = "Key Vault name for secrets (add AZURE_AD_* manually if not set in Terraform)."
}

output "postgres_fqdn" {
  value       = azurerm_postgresql_flexible_server.pg.fqdn
  description = "PostgreSQL server FQDN (resolved privately from VNet)."
}

output "redis_hostname" {
  value       = azurerm_redis_cache.redis.hostname
  description = "Redis hostname (resolved privately from VNet)."
}

output "log_analytics_workspace_id" {
  value       = azurerm_log_analytics_workspace.law.id
  description = "Log Analytics workspace ID for queries and alerts."
}

output "application_insights_connection_string" {
  value       = azurerm_application_insights.ai.connection_string
  sensitive   = true
  description = "Application Insights connection string."
}
