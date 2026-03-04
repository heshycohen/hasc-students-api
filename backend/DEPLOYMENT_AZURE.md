# Deploy Django API to Azure App Service (Healthcare-Grade)

**Target:** App Service `students-api` (Linux, Python 3.11), PostgreSQL Flexible Server `hasc-students-prod-pg` (db: `students`).

---

## 1. Exact Azure App Service settings

Configure in **Azure Portal** → **students-api** → **Configuration** → **Application settings** (and **General settings** where noted).

### Application settings (env vars)

| Name | Value | Notes |
|------|--------|--------|
| `DEBUG` | `False` | Required in production |
| `SECRET_KEY` | *long random string* | Or Key Vault reference (see Security) |
| `ALLOWED_HOSTS` | `students-api.azurewebsites.net,students-api.hasc.net` | Optional; defaults include these |
| `FRONTEND_URL` | `https://students.hasc.net` | Used for CORS/CSRF defaults |
| `DB_HOST` | `hasc-students-prod-pg.postgres.database.azure.com` | PostgreSQL Flexible Server FQDN |
| `DB_NAME` | `students` | Database name |
| `DB_USER` | *e.g.* `psqladmin` or `hascadmin` | Server admin user (often `user@servername`) |
| `DB_PASSWORD` | *secret* | Or Key Vault reference |
| `DB_PORT` | `5432` | Default PostgreSQL port |

Optional (if using Microsoft login, Key Vault, Redis):

- `CORS_ALLOWED_ORIGINS` – override (comma-separated); default = `FRONTEND_URL` + `https://students.hasc.net`
- `CSRF_TRUSTED_ORIGINS` – override; same default in production
- `AZURE_AD_TENANT_ID`, `AZURE_AD_CLIENT_ID`, `AZURE_AD_CLIENT_SECRET`, `ONLY_MICROSOFT_LOGIN`
- `REDIS_URL` if using Azure Cache for Redis

### General settings

| Setting | Value |
|---------|--------|
| **Startup Command** | `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 120` |
| **WEBSITES_PORT** | `8000` (add as Application setting if not in stack) |

### Health check (optional but recommended)

- **Settings** → **Health check** → Enable.
- **Path:** `/health`
- **Interval:** e.g. 120 seconds.

---

## 2. Deployment: GitHub Actions or Zip Deploy

### Option A: Deploy from GitHub

1. **App Service** → **Deployment Center** → Source: **GitHub** → authorize and select repo/branch.
2. Build settings (e.g. **Python 3.11**):
   - **Application stack:** Python 3.11
   - **Startup command:** (as above)
3. In **Configuration** → **Application settings**, add all env vars from the table above.
4. **Post-deployment:** Run migrations and collectstatic. Either:
   - Use a **Deployment slot** and run commands via **SSH** or **Console**, or
   - Add a **GitHub Actions** step (or **Azure DevOps**) that runs after deploy:
     ```yaml
     - name: Run migrations and collectstatic
       run: |
         az webapp ssh --resource-group <rg> --name students-api --command "cd /home/site/wwwroot && python manage.py migrate --noinput && python manage.py collectstatic --noinput"
     ```
     Or use **Run From Package** and run a one-off migration job (Azure Functions logic or script that calls the same commands).

### Option B: Zip Deploy (manual or script)

1. From your machine (backend directory):
   ```bash
   cd backend
   pip install -r requirements.txt -t .python_packages/lib/site-packages
   zip -r deploy.zip . -x "*.git*" -x "__pycache__/*" -x "*.pyc" -x "venv/*" -x ".env"
   ```
2. Deploy zip:
   ```bash
   az webapp deploy --resource-group <resource-group> --name students-api --src-path deploy.zip --type zip
   ```
3. **After deploy**, run migrations and collectstatic via **SSH** or **Console**:
   ```bash
   cd /home/site/wwwroot
   python manage.py migrate --noinput
   python manage.py collectstatic --noinput
   ```

### Post-deploy commands (any method)

Run once after each deploy that changes models or static files:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

---

## 3. Logs and troubleshooting

- **Enable logs:** **App Service** → **Monitoring** → **App Service logs**:
  - **Application Logging:** On (Filesystem or Blob), Level **Information** or **Error**.
  - **Web server logging:** On.
  - **Detailed Error Messages:** Off in production.
- **Stream logs:** **Log stream** in the portal, or:
  ```bash
  az webapp log tail --resource-group <rg> --name students-api
  ```
- **Download logs:** **Advanced Tools (Kudu)** → **Debug console** → browse `LogFiles/`, or **Monitoring** → **Log stream** / **Diagnose and solve problems**.
- **Common failures:**
  - **502/503:** Check startup command and `WEBSITES_PORT=8000`; ensure Gunicorn binds to `0.0.0.0:8000`.
  - **DB connection:** Check `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, firewall rules / private endpoint, and SSL (see Security).
  - **Static 404:** Run `collectstatic --noinput` after deploy.
  - **CORS/CSRF:** Ensure `FRONTEND_URL` and/or `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` include `https://students.hasc.net`.

---

## 4. Security hardening checklist

### App Service

| Item | Action |
|------|--------|
| **HTTPS only** | **Configuration** → **General settings** → **HTTPS Only:** On. |
| **Disable FTP** | **Configuration** → **General settings** → **FTP state:** Disabled. |
| **Managed Identity** | **Identity** → **System assigned:** On. Use this identity to read secrets from Key Vault (no secrets in app settings). |
| **Key Vault references** | For `SECRET_KEY`, `DB_PASSWORD`, etc.: add app setting value `@Microsoft.KeyVault(SecretUri=https://<vault>.vault.azure.net/secrets/<secret-name>/)`. Grant the App Service’s managed identity **Key Vault Secrets User** on the vault. |
| **Minimum TLS** | **Configuration** → **General settings** → **Minimum TLS Version:** 1.2. |

### Database (PostgreSQL Flexible Server: hasc-students-prod-pg)

| Item | Action |
|------|--------|
| **Prefer private access** | Prefer **Private access** (VNet integration or Private Endpoint). If not yet in place, use firewall + SSL. |
| **Restrict firewall** | **Networking** → allow only required outbound IPs (e.g. App Service outbound IPs or VNet). Deny public 0.0.0.0/0 except for temporary admin if needed. |
| **Require SSL** | **PostgreSQL** connection: use `sslmode=require` (Django production settings already use this when `DB_HOST` is not localhost). |
| **Private endpoint** | When ready, add Private Endpoint and disable public access; point `DB_HOST` to private FQDN. |

### Application Insights and alerts

| Item | Action |
|------|--------|
| **Application Insights** | **App Service** → **Application Insights** → **Enable** and create/link a workspace. |
| **Alerts** | In **Application Insights** or **Monitor** → **Alerts**: e.g. alert when **5xx** count &gt; 0 or **Failed requests** &gt; threshold, or **Availability** (e.g. `/health`) fails. |
| **No PHI in logs** | Ensure application logs do not include PHI; use structured logging and avoid logging request bodies or user identifiers in production. |

---

## 5. Quick reference: Django production behavior

- **DEBUG, SECRET_KEY, ALLOWED_HOSTS, FRONTEND_URL** read from env.
- **CORS_ALLOWED_ORIGINS / CSRF_TRUSTED_ORIGINS:** If not set in env, production uses `FRONTEND_URL` + `https://students.hasc.net`.
- **DB:** Uses `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`; SSL required when not localhost.
- **SSL:** `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` forced for production (`DEBUG=False`).
- **Health:** `GET/HEAD /health` returns `200` and `{"status":"ok"}` (no auth).
