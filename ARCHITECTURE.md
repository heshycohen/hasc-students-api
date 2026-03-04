# Rock-Access Target Architecture

## Production Auth & API

- **SPA (React)** uses the **backend as API**. All API requests go to the same origin (or configured backend URL) with Bearer tokens.
- **Auth**: Microsoft SSO (Entra ID / Azure AD) → backend issues **SimpleJWT** access/refresh tokens → SPA stores and uses them as today (localStorage, `Authorization: Bearer <access_token>`).

## Key Decision: Allauth + Post-Login JWT Exchange

We use **django-allauth** for Microsoft (Entra ID) login, then a **post-login callback** that:

1. Runs after the user is authenticated via session (allauth completed).
2. Exchanges the session-authenticated user into **SimpleJWT** access + refresh tokens.
3. Redirects back to the SPA with tokens in the **URL fragment** (e.g. `/login/callback#access_token=...&refresh_token=...`) so tokens do not hit server logs as query params.

Flow:

1. User clicks "Sign in with Microsoft" in SPA → `GET /api/auth/microsoft/login/` → redirect to allauth Microsoft provider.
2. User signs in at Microsoft (HASC tenant) → Microsoft redirects to allauth callback → session is established.
3. Allauth redirects to `LOGIN_REDIRECT_URL` = `/api/auth/sso/success/`.
4. `/api/auth/sso/success/` (session required): mint JWT, redirect to `FRONTEND_URL/login/callback#access_token=...&refresh_token=...`.
5. SPA `/login/callback` parses fragment, stores tokens, loads user, redirects to `/`.

## Hosting (Option A)

Django serves the React build: static and SPA `index.html` from the same app (WhiteNoise + catch-all for non-API paths). API paths (`/api/...`) are unchanged.

## HASC / Entra ID

- Single-tenant: **AZURE_AD_TENANT_ID** fixed; backend rejects logins if ID token `tid` does not match.
- Optional: **ALLOWED_EMAIL_DOMAINS** (e.g. `hasc.net`) for extra hardening.
