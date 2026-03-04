# Healthcare-grade Azure deployment: students.hasc.net + students-api.hasc.net
# Terraform 1.x + azurerm provider ~> 3.0

variable "environment" {
  type        = string
  default     = "prod"
  description = "Environment name (prod, staging)."
}

variable "location" {
  type        = string
  default     = "eastus"
  description = "Azure region for all resources."
}

variable "project_name" {
  type        = string
  default     = "students-hasc"
  description = "Short project name used in resource naming."
}

variable "frontend_fqdn" {
  type        = string
  default     = "students.hasc.net"
  description = "Public DNS for frontend (Static Web App or App Service)."
}

variable "api_fqdn" {
  type        = string
  default     = "students-api.hasc.net"
  description = "Public DNS for API (Backend App Service behind Front Door)."
}

variable "postgres_admin_user" {
  type        = string
  default     = "psqladmin"
  description = "PostgreSQL flexible server admin username."
}

variable "postgres_admin_password" {
  type        = string
  sensitive   = true
  description = "PostgreSQL admin password. Use TF_VAR_postgres_admin_password or -var."
}

variable "redis_sku" {
  type        = string
  default     = "Premium"
  description = "Redis SKU: Premium required for private endpoint."
}

variable "redis_family" {
  type        = string
  default     = "P"
  description = "Redis family: P for Premium."
}

variable "redis_capacity" {
  type        = number
  default     = 1
  description = "Redis capacity (1 for P1 Premium)."
}

variable "app_service_sku" {
  type        = string
  default     = "P1v3"
  description = "App Service Plan SKU (P1v3 for VNet integration and production)."
}

variable "allowed_corporate_ips" {
  type        = list(string)
  default     = []
  description = "Optional list of CIDR blocks for admin access to backend (e.g. office IP)."
}

variable "front_door_sku" {
  type        = string
  default     = "Premium_AzureFrontDoorValue"
  description = "Front Door SKU; Premium required for WAF and advanced features."
}

variable "log_retention_days" {
  type        = number
  default     = 90
  description = "Log Analytics retention in days."
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags applied to all resources."
}

# Azure AD (Entra) — store in Key Vault; set via TF_VAR_ or -var (do not commit)
variable "azure_ad_tenant_id" {
  type        = string
  default     = ""
  description = "Microsoft Entra (Azure AD) tenant ID for HASC."
}

variable "azure_ad_client_id" {
  type        = string
  default     = ""
  description = "App registration (client) ID."
}

variable "azure_ad_client_secret" {
  type        = string
  sensitive   = true
  default     = ""
  description = "App registration client secret."
}

variable "django_secret_key" {
  type        = string
  sensitive   = true
  default     = ""
  description = "Django SECRET_KEY. If empty, a random value is generated."
}

variable "frontend_origin_hostname" {
  type        = string
  default     = ""
  description = "Frontend origin hostname (e.g. xxx.azurestaticapps.net). Set after creating Static Web App."
}
