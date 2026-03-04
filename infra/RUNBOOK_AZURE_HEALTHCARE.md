# Runbook: Healthcare-Grade Azure Deployment (students.hasc.net / students-api.hasc.net)

This runbook covers deploying the Rock-Access stack to Azure with private networking, Front Door Premium + WAF, Key Vault, and Microsoft Entra SSO. **No PHI in logs;** DB and Redis are not publicly reachable.

## Prerequisites

- Azure subscription with permissions to create resource groups, VNets, App Service, PostgreSQL, Redis, Key Vault, Front Door, Log Analytics.
- Terraform 1.x and Azure CLI (`az`) installed and logged in (`az login`).
- DNS control for `hasc.net` (to add CNAMEs for `students.hasc.net` and `students-api.hasc.net`).
- Microsoft Entra (Azure AD) app registration for HASC (or create in Step 4).

---

## Step 1: Create infrastructure (Terraform)

1. **Go to the Terraform directory:**
   ```bash
   cd rock-access-web/infra/terraform
   ```

2. **Create a `terraform.tfvars` file** (do not commit; add to `.gitignore`):
   ```hcl
   location               = "eastus"
   project_name           = "students-hasc"
   environment             = "prod"
   frontend_fqdn          = "students.hasc.net"
   api_fqdn                = "students-api.hasc.net"
   postgres_admin_user     = "psqladmin"
   postgres_admin_password = "YOUR_SECURE_DB_PASSWORD"

   # Optional: set these to store Entra secrets in Key Vault via Terraform
   azure_ad_tenant_id     = "YOUR_HASC_TENANT_ID"
   azure_ad_client_id      = "YOUR_APP_CLIENT_ID"
   azure_ad_client_secret  = "YOUR_APP_CLIENT_SECRET"

   # After creating Static Web App (Step 6), set:
   # frontend_origin_hostname = "xxx.azurestaticapps.net"
   ```

3. **Initialize and apply:**
   ```bash
   terraform init
   terraform plan -out=tfplan
   terraform apply tfplan
   ```

4. **Note outputs** (or run `terraform output` later):
   - `front_door_endpoint_hostname` — CNAME target for both hostnames (Step 2).
   - `backend_app_name` — Backend App Service name (e.g. for deploy and startup command).
   - `key_vault_name` — Where secrets are stored.

5. **Startup command for Backend App Service:**  
   In Azure Portal → App Service → Configuration → General settings, set **Startup Command** to:
   ```bash
   gunicorn config.wsgi:application --bind 0.0.0.0:8000
   ```
   (Or use the same in your deployment script; App Service uses port 8000 via `WEBSITES_PORT=8000`.)

---

## Step 2: Configure DNS

1. In your DNS provider for `hasc.net`, add **CNAME** records:
   - **students.hasc.net** → `front_door_endpoint_hostname` (e.g. `endpoint-studentshascprod-xxx.z01.azurefd.net`).
   - **students-api.hasc.net** → same `front_door_endpoint_hostname`.

2. Wait for DNS propagation. Front Door will serve both hostnames with managed TLS once the custom domains are validated (automatic when CNAME points to the FD endpoint).

---

## Step 3: Add Entra (Azure AD) redirect URIs

1. In **Azure Portal** → **Microsoft Entra ID** → **App registrations** → your HASC app (or create one):
   - **Authentication** → **Add a platform** → **Web**.
   - **Redirect URI:** `https://students-api.hasc.net/api/auth/microsoft/callback/`
   - For local testing you can also add: `http://localhost:8000/api/auth/microsoft/callback/`

2. **API permissions:** Ensure `openid`, `email`, `profile` (Delegated) are present.

3. If you did **not** set `azure_ad_tenant_id` / `azure_ad_client_id` / `azure_ad_client_secret` in Terraform, add the secrets to Key Vault manually:
   - **Key Vault** → **Secrets** → Create: `AZURE-AD-TENANT-ID`, `AZURE-AD-CLIENT-ID`, `AZURE-AD-CLIENT-SECRET`.
   - Then in **App Service** → **Configuration** → Application settings, set:
     - `AZURE_AD_TENANT_ID` = `@Microsoft.KeyVault(SecretUri=https://<vault>.vault.azure.net/secrets/AZURE-AD-TENANT-ID/)`
     - (and similarly for `AZURE_AD_CLIENT_ID`, `AZURE_AD_CLIENT_SECRET`).

---

## Step 4: Deploy backend and run migrations

1. **Deploy code** to the Backend App Service (e.g. from Git, GitHub Actions, or ZIP deploy). Ensure the deployment uses:
   - Python 3.11
   - Install: `pip install -r requirements.txt`
   - No need to set DB/REDIS/SECRET in app settings if using Key Vault references from Terraform.

2. **Run migrations** (one-time; use SSH or Console, or a release script):
   ```bash
   cd /home/site/wwwroot
   python manage.py migrate --noinput
   python manage.py collectstatic --noinput
   ```

3. **Verify App Service** has:
   - **VNet Integration** enabled (to reach Postgres and Redis via private endpoints).
   - **Managed Identity** ON; Key Vault access (Key Vault Secrets User) is granted by Terraform.

---

## Step 5: Deploy frontend

**Option A — Azure Static Web Apps (recommended for SPA):**

1. Create an **Azure Static Web App** (e.g. in the same resource group). Build command: `npm run build`; output: `build`.

2. Set **build-time** environment variable in the SWA workflow or Configuration:
   - `REACT_APP_API_URL=https://students-api.hasc.net/api`

3. After the first deploy, copy the **default hostname** (e.g. `xxx.azurestaticapps.net`). Then in Terraform:
   - Set `frontend_origin_hostname = "xxx.azurestaticapps.net"` in `terraform.tfvars`.
   - Run `terraform apply` again so Front Door has a frontend origin and route for `students.hasc.net`.

**Option B — Same App Service as backend (Django serves SPA):**

1. Build locally:
   ```bash
   cd frontend
   cp .env.production.example .env.production
   # Edit .env.production: REACT_APP_API_URL=https://students-api.hasc.net/api
   npm ci && npm run build
   ```
2. Deploy backend with `frontend/build` included and `FRONTEND_BUILD_DIR` pointing to it; Django will serve the SPA for non-API routes.

---

## Step 6: Smoke test checklist

- [ ] **https://students.hasc.net** loads (frontend or “coming soon” if frontend not yet wired).
- [ ] **https://students-api.hasc.net/api/** returns JSON (`api`, `auth`, `sessions`, etc.).
- [ ] **https://students-api.hasc.net/api/health/** returns `{"status":"ok"}` (no auth).
- [ ] **Login:** Click “Sign in with Microsoft” → redirects to Microsoft → after login, returns to app with JWT; API calls from SPA succeed.
- [ ] **WAF:** Front Door WAF is enabled; test with a simple malicious query and confirm block (optional).
- [ ] **App Insights:** In Azure Portal, App Insights shows requests and errors (no PHI in logs).
- [ ] **Private access:** Postgres and Redis show no public access (firewall / public network access OFF; private endpoint only).
- [ ] **CORS/CSRF:** Only `https://students.hasc.net` is allowed; `DEBUG=False` in production.

---

## Security and compliance notes

- **Secrets:** All sensitive values (SECRET_KEY, DB password, Redis URL, Azure AD secret) are in Key Vault; App Service uses Managed Identity to read them.
- **No PHI in logs:** Application and Front Door logs must not contain PHI; use structured logging and avoid logging request bodies or PII.
- **Defender for Cloud:** Review and apply recommendations for the resource group (App Service, Postgres, Redis, Key Vault).
- **HSTS / HTTPS:** Enforced at Front Door and App Service; cookies are secure.

---

## Troubleshooting

- **502/503 from Front Door:** Check backend health at `https://<backend-app-name>.azurewebsites.net/api/health/` (and VNet integration so the app can reach Postgres/Redis).
- **Microsoft login fails:** Confirm redirect URI exactly `https://students-api.hasc.net/api/auth/microsoft/callback/` and that Key Vault secrets are set and referenced correctly.
- **CORS errors:** Ensure `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` include `https://students.hasc.net` (no trailing slash).
