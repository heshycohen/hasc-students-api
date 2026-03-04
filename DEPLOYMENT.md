# Deployment Guide

## Prerequisites

- Docker and Docker Compose
- PostgreSQL 14+ (or use Docker)
- Python 3.11+
- Node.js 18+

## Local Development Setup

1. **Clone and navigate to project:**
   ```bash
   cd rock-access-web
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start database:**
   ```bash
   docker-compose up -d db
   ```

4. **Set up backend:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Set up frontend:**
   ```bash
   cd ../frontend
   npm install
   ```

6. **Run development servers:**
   ```bash
   # Backend (in backend directory)
   python manage.py runserver

   # Frontend (in frontend directory)
   npm start
   ```

## Production Deployment

### Using Docker Compose

1. **Configure environment:**
   - Set `DEBUG=False`
   - Set strong `SECRET_KEY`
   - Configure database credentials
   - Set encryption key
   - Configure OAuth providers

2. **Build and start:**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

3. **Run migrations:**
   ```bash
   docker-compose exec backend python manage.py migrate
   docker-compose exec backend python manage.py createsuperuser
   ```

### Cloud Deployment (AWS/Azure/GCP)

**Azure step-by-step:** See [docs/AZURE_PRODUCTION_PLAN.md](docs/AZURE_PRODUCTION_PLAN.md) for deploying to Azure and configuring Microsoft (Azure AD) login.

#### Azure App Service Plan (if using Azure)

| Tier | Use case | Notes |
|------|----------|--------|
| **Basic (B1)** | Dev/test, very light production | Custom domain + SSL; no staging slots; shared infra. |
| **Standard (S1)** | **Typical production** | Staging slots, auto-scale, daily backup; suitable for many HIPAA workloads with BAA. |
| **Premium (P1v3 / P2v3)** | Higher traffic, VNet integration | Better isolation, scale-out; good for PHI when you need VNet. |
| **Isolated (I1)** | Strongest isolation / compliance | Dedicated VNet, dedicated workers; often chosen for strict HIPAA posture. |

**Recommendation for Rock-Access (HIPAA/FERPA):** Use **Standard (S1)** as a minimum for production (custom domain, HTTPS, staging, backups). Prefer **Premium (P1v3)** or **Isolated (I1)** if you need VNet integration, dedicated compute, or stricter isolation; HIPAA compliance is achieved via BAA + configuration, not a specific tier. Check [Azure App Service pricing](https://azure.microsoft.com/pricing/details/app-service/plans/) and the [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/) for current costs and regions.

1. **Database:**
   - Use managed PostgreSQL service
   - Enable encryption at rest
   - Configure SSL/TLS connections

2. **Application:**
   - Deploy to container service (ECS, AKS, GKE) or Azure App Service
   - Use load balancer with SSL termination
   - Configure environment variables
   - Set up monitoring and logging

3. **Security:**
   - Enable WAF
   - Configure DDoS protection
   - Set up backup encryption
   - Configure KMS for encryption keys

## Data Migration from Access Databases

1. **Copy Access database files to server**

2. **Run migration command:**
   ```bash
   python manage.py import_access_db /path/to/SY2024-2025.accdb
   python manage.py import_access_db /path/to/Summer2025.accdb
   ```

3. **Verify data:**
   - Check session data in admin panel
   - Verify student and employee counts
   - Test data inheritance

## OAuth Configuration

### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials
3. Add authorized redirect URI: `https://yourdomain.com/accounts/google/login/callback/`
4. Add credentials to `.env`

### Microsoft OAuth

1. Go to [Azure Portal](https://portal.azure.com/)
2. Register application
3. Add redirect URI: `https://yourdomain.com/accounts/microsoft/login/callback/`
4. Add credentials to `.env`

## Compliance Checklist

> **📘 Detailed Implementation Guide**: See [COMPLETION_GUIDE.md](./COMPLETION_GUIDE.md) for step-by-step instructions to complete all items below.

- [ ] Encryption at rest enabled (database)
- [ ] TLS 1.3 configured
- [ ] MFA enabled for all users
- [ ] Audit logging configured
- [ ] Backup encryption enabled
- [ ] Access controls configured
- [ ] Business Associate Agreements signed
- [ ] Incident response plan documented
- [ ] Security monitoring enabled
