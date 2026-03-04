# Azure Production Deployment and Login Plan

Step-by-step plan to deploy Rock-Access to Azure and enable Microsoft (Azure AD) login in production.

---

## Part 1: Azure production deployment

### 1.1 Choose hosting model

- **Option A – App Service (simplest)**  
  - Backend: Azure App Service (Linux, Python 3.11).  
  - Frontend: Static Web Apps or App Service (Node static).  
  - DB: Azure Database for PostgreSQL (Flexible Server).  
  - Redis: Azure Cache for Redis.  

- **Option B – Containers**  
  - Backend + frontend: Azure Container Apps or AKS.  
  - Same DB and Redis as above.  

Below steps assume **Option A** (App Service + Static Web Apps + managed DB/Redis). Adjust if you use containers.

### 1.2 Azure resources to create

1. **Resource group**  
   - e.g. `rg-rockaccess-prod`, region close to users.

2. **Azure Database for PostgreSQL – Flexible Server**  
   - Create server and database (e.g. `rock_access`).  
   - Enable **TLS** (enforce SSL).  
   - Enable **encryption at rest** (default).  
   - Note: host, port, DB name, user, password for `DB_*` env vars.

3. **Azure Cache for Redis**  
   - Create Redis instance.  
   - Note: host and port (and key if required) for `REDIS_HOST`, `REDIS_PORT` (and any auth).

4. **App Service plan and Web App (backend)**  
   - Plan: **Standard (S1)** or higher (see DEPLOYMENT.md).  
   - Web App: Linux, Python 3.11, e.g. `rockaccess-api`.  
   - Enable **HTTPS Only**.  
   - Set **WEBSITE_PORT=8000** if your container/startup uses 8000.  
   - Deploy backend (code or container).  
   - In Configuration → Application settings, add all env vars (see 1.4).  
   - If using custom domain, add it and bind TLS cert.

5. **Static Web App or second App Service (frontend)**  
   - Build frontend with production API URL (e.g. `REACT_APP_API_URL=https://rockaccess-api.azurewebsites.net`).  
   - Deploy.  
   - Note final frontend URL (e.g. `https://rockaccess.azurestaticapps.net` or custom domain).

6. **Optional – Key Vault**  
   - If using Azure Key Vault for app secrets or KMS: create Key Vault, enable **Managed Identity** on the backend App Service and grant the identity access to secrets/keys.  
   - Use same vault for encryption keys if you set `KMS_PROVIDER=azure` (see COMPLETION_GUIDE.md §1).

### 1.3 Networking and DNS

- Prefer **VNet integration** for backend if you need private DB/Redis access (Premium plan or VNet rules).  
- Point your public DNS (e.g. `app.yourdomain.com`) to:  
  - Backend: App Service (or API gateway).  
  - Frontend: Static Web App / frontend App Service.  
- Use **TLS 1.2+** (and 1.3 where possible) on App Service / frontend.

### 1.4 Backend environment variables (production)

Set these in App Service → Configuration → Application settings (or Key Vault references):

```env
# Django
DEBUG=False
SECRET_KEY=<strong-random-secret>
ALLOWED_HOSTS=rockaccess-api.azurewebsites.net,app.yourdomain.com,...

# Database (Azure PostgreSQL)
DB_HOST=<your-postgres-server>.postgres.database.azure.com
DB_PORT=5432
DB_NAME=rock_access
DB_USER=<user>
DB_PASSWORD=<password>

# Redis (Azure Cache for Redis)
REDIS_HOST=<your-redis>.redis.cache.windows.net
REDIS_PORT=6380

# Frontend URL (for Microsoft login redirect)
FRONTEND_URL=https://rockaccess.azurestaticapps.net

# Microsoft (Azure AD) login – see Part 2
AZURE_AD_TENANT_ID=<tenant-id>
AZURE_AD_CLIENT_ID=<app-client-id>
AZURE_AD_CLIENT_SECRET=<client-secret>
ONLY_MICROSOFT_LOGIN=True

# Optional: KMS (if using Azure Key Vault for encryption)
KMS_PROVIDER=azure
AZURE_KEY_VAULT_URL=https://<vault>.vault.azure.net/
AZURE_KEY_NAME=<key-name>
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_ID=<managed-identity-or-app-id>
AZURE_CLIENT_SECRET=<if-not-using-managed-identity>
```

Run migrations after first deploy (e.g. from App Service SSH/console or CI):

```bash
python manage.py migrate --no-input
python manage.py createsuperuser  # if needed for first admin
```

---

## Part 2: Azure AD (Microsoft) login in production

Backend already supports Microsoft login via `/api/auth/microsoft/login/` and `/api/auth/microsoft/callback/`. You only need to register the app and set env vars.

### 2.1 Register app in Azure AD

1. In **Azure Portal** → **Microsoft Entra ID (Azure AD)** → **App registrations** → **New registration**.  
2. Name: e.g. `Rock-Access Production`.  
3. **Supported account types**: “Accounts in this organizational directory only” (single-tenant for HASC).  
4. **Redirect URI**:  
   - Type: **Web**.  
   - URI: `https://<your-backend-host>/api/auth/microsoft/callback/`  
   - Example: `https://rockaccess-api.azurewebsites.net/api/auth/microsoft/callback/`  
   - If you use a custom domain: `https://api.yourdomain.com/api/auth/microsoft/callback/`  
5. Register. Note **Application (client) ID** and **Directory (tenant) ID**.

### 2.2 Client secret

1. In the app → **Certificates & secrets** → **New client secret**.  
2. Description e.g. “Rock-Access prod”, expiry as per policy.  
3. Copy the **Value** once (this is `AZURE_AD_CLIENT_SECRET`).

### 2.3 API permissions

1. **API permissions** → **Add a permission**.  
2. **Microsoft Graph** → **Delegated**:  
   - `openid`  
   - `email`  
   - `profile`  
3. Grant admin consent if required by your tenant.

### 2.4 Backend configuration

- **AZURE_AD_TENANT_ID**: Directory (tenant) ID.  
- **AZURE_AD_CLIENT_ID**: Application (client) ID.  
- **AZURE_AD_CLIENT_SECRET**: Client secret value.  
- **FRONTEND_URL**: Exact production frontend origin (e.g. `https://rockaccess.azurestaticapps.net`) so the callback redirects to the right SPA.  
- **ONLY_MICROSOFT_LOGIN**: Set to `True` if you want to disable email/password login in production.

Callback URL is built as: `request.build_absolute_uri('/api/auth/microsoft/callback/')`, so it will use the backend’s public URL (App Service or custom domain). Ensure **ALLOWED_HOSTS** includes that host.

### 2.5 Frontend

- Frontend should call backend at production API URL (e.g. `REACT_APP_API_URL=https://rockaccess-api.azurewebsites.net`).  
- “Sign in with Microsoft” should open:  
  `GET /api/auth/microsoft/login/`  
  (or your frontend’s link that triggers that URL).  
- After login, backend redirects to:  
  `FRONTEND_URL/login/callback?access_token=...&refresh_token=...`  
  Frontend must handle this route and store tokens (e.g. in memory or httpOnly cookie) and then go to the app.

### 2.6 Checklist – Microsoft login

- [ ] App registered in Azure AD (single-tenant).  
- [ ] Redirect URI = `https://<backend>/api/auth/microsoft/callback/`.  
- [ ] Client secret created and copied.  
- [ ] Graph delegated permissions: openid, email, profile (admin consent if needed).  
- [ ] Backend env: `AZURE_AD_TENANT_ID`, `AZURE_AD_CLIENT_ID`, `AZURE_AD_CLIENT_SECRET`, `FRONTEND_URL`.  
- [ ] Backend host in `ALLOWED_HOSTS`.  
- [ ] Frontend uses production API URL and handles `/login/callback` with tokens.

---

## Part 3: Post-deploy

- Run migrations and create superuser if needed.  
- Test Microsoft login from production frontend.  
- Confirm TLS and HSTS (see COMPLETION_GUIDE.md §3 and `nginx.conf.example` if you use Nginx).  
- Configure backups, monitoring, and BAAs as in PRODUCTION_READINESS.md and COMPLETION_GUIDE.md.

---

## Quick reference

| Item | Where |
|------|--------|
| App Service tier | DEPLOYMENT.md (Standard S1 minimum) |
| Env vars | `backend/.env.example`, §1.4 above |
| Microsoft login | `backend/users/views.py` (MicrosoftLoginView, MicrosoftCallbackView) |
| KMS (Azure Key Vault) | COMPLETION_GUIDE.md §1, `backend/compliance/encryption.py` |
| TLS / Nginx | `nginx.conf.example`, COMPLETION_GUIDE.md §3 |
