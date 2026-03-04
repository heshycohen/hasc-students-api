# Production Readiness Checklist

Use this checklist to work through **COMPLETION_GUIDE.md** and **DEPLOYMENT.md** before going live.

---

## 1. COMPLETION_GUIDE.md (HIPAA/FERPA hardening)

| # | Item | Guide section | Status |
|---|------|----------------|--------|
| 1 | **Cloud KMS** – Use AWS, Azure, or GCP KMS for encryption keys (or keep `KMS_PROVIDER=local` with strong `ENCRYPTION_KEY`) | §1 | ⬜ |
| 2 | **Encryption at rest** – Enable on DB (RDS/Cloud SQL TDE or equivalent) | §2 | ⬜ |
| 3 | **TLS 1.3** – Nginx/reverse proxy with TLS 1.2/1.3, HSTS, security headers | §3 | ⬜ |
| 4 | **MFA enforcement** – Require MFA for all users; middleware + session handling | §4 | ⬜ |
| 5 | **Audit logging** – Rotation, retention, and reporting per guide | §5 | ⬜ |
| 6 | **Backup encryption** – Encrypted DB backups + restore procedure | §6 | ⬜ |
| 7 | **Access controls** – RBAC/ABAC verified; minimum necessary | §7 | ⬜ |
| 8 | **Business Associate Agreements** – Signed BAAs with cloud/vendors; see `docs/BAA_TEMPLATE.md` | §8 | ⬜ |
| 9 | **Incident response plan** – Documented and accessible; see `docs/INCIDENT_RESPONSE_PLAN.md` | §9 | ⬜ |
| 10 | **Security monitoring** – Alerts, dashboard, scheduled checks | §10 | ⬜ |

---

## 2. DEPLOYMENT.md (go-live)

| Step | Action | Status |
|------|--------|--------|
| A | Set `DEBUG=False`, strong `SECRET_KEY`, production `ALLOWED_HOSTS` | ⬜ |
| B | Configure production DB (managed PostgreSQL, SSL) | ⬜ |
| C | Run migrations and create superuser on production | ⬜ |
| D | Deploy app (Docker/cloud) with env vars and TLS termination | ⬜ |
| E | Configure OAuth (Google/Microsoft) if using | ⬜ |

For Azure production and Microsoft (Azure AD) login, follow [docs/AZURE_PRODUCTION_PLAN.md](docs/AZURE_PRODUCTION_PLAN.md).
| F | Import/cutover data; verify in UI | ⬜ |
| G | Final compliance review (HIPAA/FERPA) | ⬜ |

---

## 3. Quick reference

- **Full step-by-step:** [COMPLETION_GUIDE.md](./COMPLETION_GUIDE.md)  
- **Deploy steps:** [DEPLOYMENT.md](./DEPLOYMENT.md)  
- **TLS/reverse proxy:** [nginx.conf.example](./nginx.conf.example)  
- **BAA template:** [docs/BAA_TEMPLATE.md](./docs/BAA_TEMPLATE.md)  
- **Incident response:** [docs/INCIDENT_RESPONSE_PLAN.md](./docs/INCIDENT_RESPONSE_PLAN.md)

---

*Mark items ⬜ → ✅ as you complete them.*
