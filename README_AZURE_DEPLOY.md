# Azure Deployment (Rock-Access)

## Required Azure Resources

- **App Service** (Linux, Python 3.11) – runs Django (and optionally serves the React build).
- **PostgreSQL Flexible Server** – database.
- **Azure Cache for Redis** – for Channels (WebSockets) and/or caching; use TLS if required by your tier.
- **Key Vault** (recommended) – store `SECRET_KEY`, DB password, `AZURE_AD_CLIENT_SECRET`, etc.

## App Service Configuration

- **WEBSITES_PORT**: Set to `8000` if the app listens on 8000 (so the platform routes correctly).
- **Startup command** (HTTP only, WSGI):
  ```bash
  gunicorn config.wsgi:application --bind 0.0.0.0:8000
  ```
- If you need **WebSockets**, use ASGI instead and confirm your App Service plan supports WebSockets:
  ```bash
  daphne -b 0.0.0.0 -p 8000 config.asgi:application
  ```

## Deploy Steps

1. **Build frontend** (if Django serves the SPA – Option A):
   ```bash
   cd frontend && npm ci && npm run build
   ```

2. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

3. **Collect static files** (includes SPA build when `FRONTEND_BUILD_DIR` points to `frontend/build`):
   ```bash
   python manage.py collectstatic --noinput
   ```

4. Set all required **environment variables** in App Service (see Environment Variables Checklist in the main implementation plan).

## Environment Variables (Production)

Set in App Service **Configuration → Application settings** (or Key Vault references):

- `DEBUG=False`
- `SECRET_KEY=...`
- `ALLOWED_HOSTS=your-app.azurewebsites.net,yourdomain.com` (comma-separated)
- `CSRF_TRUSTED_ORIGINS=https://your-app.azurewebsites.net,https://yourdomain.com` (comma-separated)
- `CORS_ALLOWED_ORIGINS=https://your-app.azurewebsites.net,https://yourdomain.com` (comma-separated)
- Database: `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT` (or `DATABASE_URL` if you add support)
- `REDIS_URL` for Azure Cache for Redis (e.g. `rediss://...` if TLS)
- `FRONTEND_URL=https://your-app.azurewebsites.net` (or your custom domain)
- `FRONTEND_BUILD_DIR` – path to `frontend/build` on the server if different from default
- `AZURE_AD_TENANT_ID`, `AZURE_AD_CLIENT_ID`, `AZURE_AD_CLIENT_SECRET`
- `ALLOWED_EMAIL_DOMAINS=hasc.net` (optional, comma-separated)
- `DJANGO_SETTINGS_MODULE=config.settings` (or your production settings module if split)

## Allauth Microsoft (Entra ID) setup

For the Microsoft SSO flow you must create a **Social Application** in Django Admin:

1. Open **Sites** and ensure your production domain is listed (e.g. `https://your-app.azurewebsites.net`).
2. Open **Social applications** → Add: **Provider** = Microsoft, **Client id** = `AZURE_AD_CLIENT_ID`, **Secret** = `AZURE_AD_CLIENT_SECRET`.
3. In Azure Portal, set the app registration **Redirect URI** to: `https://your-domain/accounts/microsoft/login/callback/` (replace with your App Service URL).

## Optional: Separate Frontend (Static Web Apps)

If you host the React app on **Azure Static Web Apps** instead of Django:

- Build the frontend with `REACT_APP_API_URL=https://your-backend.azurewebsites.net` (or your API domain).
- Configure CORS and `CSRF_TRUSTED_ORIGINS` on the backend for the SWA origin.
- Set `FRONTEND_URL` to the SWA URL for SSO redirects.
