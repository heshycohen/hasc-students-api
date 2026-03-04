# School Year Management System

A HIPAA and FERPA compliant web-based system for managing student and employee data across School Years (SY) and Summer Sessions.

## ✅ Implementation Status: COMPLETE

All components from the plan have been fully implemented and are ready for testing and deployment.

## Features

- **Session Management**: Separate data isolation for each School Year and Summer Session
- **Data Inheritance**: Automatic data copying between sessions (Summer from previous SY, SY from previous Summer)
- **Multi-user Editing**: Concurrent access with conflict resolution via WebSocket
- **HIPAA/FERPA Compliance**: Full compliance with encryption, audit logging, and access controls
- **OAuth Authentication**: Google/Microsoft login with MFA support
- **Access Database Migration**: Import existing Access databases (.accdb files)

## Technology Stack

- **Backend**: Django 4.x, Django REST Framework, Django Channels (WebSocket)
- **Database**: PostgreSQL 14+ with encryption
- **Frontend**: React 18, Material-UI, DOMPurify (XSS protection)
- **Authentication**: OAuth 2.0 with MFA (TOTP)
- **Encryption**: Field-level encryption for PHI/PII
- **Real-time**: WebSocket (WSS) for concurrent editing

## New computer? Install prerequisites first

See **[INSTALL_PREREQUISITES.md](INSTALL_PREREQUISITES.md)** for installing Python, Node.js, PostgreSQL, and optional Redis/Docker on a new machine. Then run `.\check_prerequisites.ps1` to verify.

## Quick Start

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm start
```

### 3. Start Services

**Terminal 1 - Redis (for WebSocket):**
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

**Terminal 2 - Backend:**
```bash
cd backend
daphne config.asgi:application
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm start
```

### 4. Access Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Admin Panel: http://localhost:8000/admin
- API Docs: http://localhost:8000/api/docs/

## Import Access Databases

```bash
python manage.py import_access_db /path/to/SY2024-2025.accdb
python manage.py import_access_db /path/to/Summer2025.accdb
```

## Documentation

- **START_TESTING.md** - Quick start testing guide
- **TESTING_GUIDE.md** - Comprehensive test scenarios
- **DEPLOYMENT.md** - Production deployment instructions
- **CONCURRENT_EDITING.md** - WebSocket and concurrent editing guide
- **IMPLEMENTATION_COMPLETE.md** - Implementation overview
- **FINAL_STATUS.md** - Complete verification report

## Compliance

This system is designed to meet HIPAA and FERPA compliance requirements including:

### HIPAA
- ✅ Encryption at rest and in transit
- ✅ Comprehensive audit logging (6+ year retention)
- ✅ Role-based access control
- ✅ Automatic session timeout (15 minutes)
- ✅ Field-level encryption for PHI/PII
- ✅ Access controls (minimum necessary principle)

### FERPA
- ✅ Directory information controls
- ✅ Consent management system
- ✅ Disclosure logging
- ✅ Access logging for educational records
- ✅ Legitimate educational interest verification

## Key Components

### Backend
- Session management with data isolation
- Data inheritance service (SY ↔ Summer)
- REST API with security middleware
- WebSocket consumers for real-time editing
- Access database migration tool
- Comprehensive audit logging
- Field-level encryption

### Frontend
- React application with routing
- Session selector with timeout warnings
- Student/Employee management interfaces
- Compliance reports dashboard
- Concurrent editing with conflict resolution
- Security headers and XSS protection

## Architecture

```
rock-access-web/
├── backend/          # Django backend
│   ├── config/       # Django settings
│   ├── sessions/     # Session/Student/Employee models & APIs
│   ├── users/        # Authentication & authorization
│   ├── compliance/   # HIPAA/FERPA compliance features
│   └── migration_tool/ # Access DB importer
├── frontend/         # React frontend
│   └── src/
│       ├── components/  # UI components
│       ├── services/    # API & WebSocket clients
│       └── contexts/    # React contexts
└── docker-compose.yml # Docker configuration
```

## Testing

See **START_TESTING.md** for detailed testing instructions.

Quick test:
```bash
# Run setup script
./test_setup.bat  # Windows
./test_setup.sh   # Linux/Mac

# Test API
./test_api.sh admin@example.com password
```

## Deployment

See **DEPLOYMENT.md** for production deployment instructions.

## Support

For issues or questions:
1. Check documentation files
2. Review API docs at `/api/docs/`
3. Check compliance checklist in `COMPLIANCE_CHECKLIST.md`

## License

Proprietary - Internal Use Only
