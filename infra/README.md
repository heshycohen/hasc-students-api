# Azure healthcare-grade infrastructure

Terraform and runbook for deploying Rock-Access with:

- **Azure Front Door Premium** + WAF (rate limiting, managed rules)
- **App Service** (Linux, Python 3.11) with VNet integration and Managed Identity
- **PostgreSQL Flexible Server** and **Azure Cache for Redis** with private endpoints only (no public access)
- **Key Vault** for secrets; App Service reads via Managed Identity
- **Log Analytics** and **Application Insights** for monitoring (no PHI in logs)

## Public DNS (target)

- Frontend: **https://students.hasc.net**
- API: **https://students-api.hasc.net**

## Quick start

1. Copy `terraform/terraform.tfvars.example` to `terraform/terraform.tfvars` and set required variables (including `postgres_admin_password`).
2. Run Terraform: `cd terraform && terraform init && terraform apply`.
3. Follow **[RUNBOOK_AZURE_HEALTHCARE.md](RUNBOOK_AZURE_HEALTHCARE.md)** for DNS, Entra redirect URIs, backend/frontend deploy, and smoke tests.

## Contents

| Path | Description |
|------|-------------|
| `terraform/` | Terraform (VNet, Front Door, WAF, App Service, Postgres, Redis, Key Vault, App Insights) |
| `RUNBOOK_AZURE_HEALTHCARE.md` | Step-by-step setup, DNS, Entra, deploy, smoke test checklist |

## Constraints

- DB and Redis are not publicly reachable (private endpoint only).
- Secrets live in Key Vault; no secrets in repo.
- CORS/CSRF and ALLOWED_HOSTS are locked to `https://students.hasc.net` in production.
