# Testing Guide

This guide will help you test all features of the School Year Management System.

## Prerequisites

1. Python 3.11+ installed
2. Node.js 18+ installed
3. PostgreSQL 14+ installed and running
4. Redis installed and running (for WebSocket support)
5. Docker (optional, for containerized testing)

## Quick Start Testing

### Step 1: Backend Setup

```bash
cd rock-access-web/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp ../.env.example ../.env
# Edit ../.env with your database credentials

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
# Follow prompts to create admin user
```

### Step 2: Start Backend Server

```bash
# Start Redis (if not using Docker)
redis-server

# In another terminal, start Django with Daphne (for WebSocket support)
daphne config.asgi:application

# Or use runserver for basic testing (no WebSocket)
python manage.py runserver
```

### Step 3: Frontend Setup

```bash
cd rock-access-web/frontend

# Install dependencies
npm install

# Start development server
npm start
```

### Step 4: Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Admin Panel: http://localhost:8000/admin
- API Docs: http://localhost:8000/api/docs/

## Test Scenarios

### 1. Authentication Testing

#### Test Login
1. Navigate to http://localhost:3000/login
2. Enter superuser credentials
3. Verify successful login and redirect to dashboard

#### Test OAuth (if configured)
1. Click "Sign in with Google" or "Sign in with Microsoft"
2. Complete OAuth flow
3. Verify user is created and logged in

#### Test MFA Setup
1. After login, navigate to MFA setup endpoint
2. Scan QR code with authenticator app
3. Verify token and enable MFA
4. Test login with MFA

### 2. Session Management Testing

#### Create School Year Session
```bash
# Using API
curl -X POST http://localhost:8000/api/sessions/sessions/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_type": "SY",
    "name": "SY2025-26",
    "start_date": "2025-09-01",
    "end_date": "2026-06-30",
    "is_active": true
  }'
```

#### Create Summer Session
```bash
curl -X POST http://localhost:8000/api/sessions/sessions/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_type": "SUMMER",
    "name": "Summer 2025",
    "start_date": "2025-07-01",
    "end_date": "2025-08-31",
    "is_active": false
  }'
```

#### Test Session Switching
1. Create multiple sessions
2. Use session selector in UI
3. Verify data isolation between sessions

### 3. Data Inheritance Testing

#### Test SY to Summer Inheritance
1. Create SY2024-25 session
2. Add students and employees to SY2024-25
3. Create Summer 2025 session with source_session = SY2024-25
4. Trigger inheritance: `POST /api/sessions/sessions/{summer_id}/inherit_data/`
5. Verify students/employees copied to Summer 2025
6. Verify source data unchanged

#### Test Summer to SY Inheritance
1. Use Summer 2025 as source
2. Create SY2025-26 session
3. Trigger inheritance
4. Verify data copied correctly

### 4. Student Management Testing

#### Create Student
```bash
curl -X POST http://localhost:8000/api/sessions/students/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session": 1,
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "2010-05-15",
    "enrollment_date": "2025-09-01",
    "status": "active",
    "parent_email": "parent@example.com"
  }'
```

#### Test Encrypted Fields
1. Create student with SSN
2. Verify SSN is encrypted in database
3. Verify only admins can decrypt
4. Test medical info encryption

#### Test FERPA Consent
1. Set directory_info_opt_out = true
2. Verify consent record created
3. Test disclosure logging

### 5. Employee Management Testing

#### Create Employee
```bash
curl -X POST http://localhost:8000/api/sessions/employees/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session": 1,
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "jane.smith@school.edu",
    "position": "Teacher",
    "hire_date": "2020-09-01",
    "status": "active"
  }'
```

### 6. Concurrent Editing Testing

#### Test WebSocket Connection
1. Open student edit form in browser
2. Open same student in another browser/tab
3. Verify WebSocket connection established
4. Verify "other user editing" indicator appears

#### Test Optimistic Locking
1. User A opens student edit form (version 1)
2. User B opens same form (version 1)
3. User A saves changes (version 2)
4. User B tries to save → should get conflict error
5. Verify conflict resolution UI appears

#### Test Real-time Updates
1. User A edits student
2. Verify User B sees update notification
3. Verify version number increments

### 7. Access Database Migration Testing

#### Import Access Database
```bash
python manage.py import_access_db /path/to/SY2024-2025.accdb

# Verify output shows:
# - Session created
# - Students imported count
# - Employees imported count
```

#### Verify Imported Data
1. Check admin panel for new session
2. Verify students imported correctly
3. Verify employees imported correctly
4. Check data integrity

### 8. Compliance Testing

#### Test Audit Logging
1. Perform any CRUD operation
2. Check `/api/compliance/access-logs/`
3. Verify log entry created with:
   - User ID
   - Action type
   - Timestamp
   - IP address

#### Test Disclosure Logging
```bash
curl -X POST http://localhost:8000/api/compliance/disclosures/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student": 1,
    "disclosed_to": "Third Party Organization",
    "purpose": "Educational research",
    "consent_obtained": true
  }'
```

#### Test Security Events
1. Attempt failed login
2. Check `/api/compliance/security-events/`
3. Verify event logged

#### Test Access Controls
1. Login as viewer role
2. Attempt to create/edit student → should fail
3. Login as editor → should succeed
4. Login as admin → full access

### 9. Session Timeout Testing

#### Test 15-Minute Timeout
1. Login to application
2. Wait 15 minutes without activity
3. Attempt API call → should get 401 Unauthorized
4. Verify redirect to login page

### 10. API Testing

#### Test Rate Limiting
```bash
# Make many rapid requests
for i in {1..200}; do
  curl http://localhost:8000/api/sessions/students/ \
    -H "Authorization: Bearer YOUR_TOKEN"
done
# Should eventually get rate limit error
```

#### Test CORS
1. Make request from different origin
2. Verify CORS headers present
3. Verify preflight requests work

## Automated Testing Script

Create a test script to run all tests:

```bash
#!/bin/bash
# test_all.sh

echo "Starting comprehensive tests..."

# Test 1: Health Check
echo "Test 1: Health Check"
curl -f http://localhost:8000/api/sessions/current-session/ || echo "FAILED"

# Test 2: Authentication
echo "Test 2: Authentication"
TOKEN=$(curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}' \
  | jq -r '.access')
echo "Token: $TOKEN"

# Test 3: Create Session
echo "Test 3: Create Session"
SESSION_ID=$(curl -X POST http://localhost:8000/api/sessions/sessions/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_type":"SY","name":"TEST-SY","start_date":"2025-09-01","end_date":"2026-06-30"}' \
  | jq -r '.id')
echo "Session ID: $SESSION_ID"

# Test 4: Create Student
echo "Test 4: Create Student"
STUDENT_ID=$(curl -X POST http://localhost:8000/api/sessions/students/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"session\":$SESSION_ID,\"first_name\":\"Test\",\"last_name\":\"Student\",\"date_of_birth\":\"2010-01-01\",\"enrollment_date\":\"2025-09-01\"}" \
  | jq -r '.id')
echo "Student ID: $STUDENT_ID"

# Test 5: Update Student
echo "Test 5: Update Student"
curl -X PATCH http://localhost:8000/api/sessions/students/$STUDENT_ID/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Updated"}' || echo "FAILED"

# Test 6: Check Audit Log
echo "Test 6: Check Audit Log"
curl -f http://localhost:8000/api/compliance/access-logs/ \
  -H "Authorization: Bearer $TOKEN" || echo "FAILED"

echo "Tests completed!"
```

## Common Issues and Solutions

### Issue: Database Connection Error
**Solution**: Check PostgreSQL is running and credentials in `.env` are correct

### Issue: Redis Connection Error (WebSocket)
**Solution**: 
```bash
# Start Redis
redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### Issue: Migration Errors
**Solution**:
```bash
python manage.py makemigrations
python manage.py migrate
```

### Issue: CORS Errors
**Solution**: Check `CORS_ALLOWED_ORIGINS` in settings.py includes frontend URL

### Issue: WebSocket Not Connecting
**Solution**: 
- Verify Daphne is running (not runserver)
- Check Redis is running
- Verify WebSocket URL in frontend matches backend

## Performance Testing

### Load Testing
```bash
# Install Apache Bench
ab -n 1000 -c 10 http://localhost:8000/api/sessions/students/
```

### Database Performance
```sql
-- Check query performance
EXPLAIN ANALYZE SELECT * FROM students WHERE session_id = 1;

-- Check indexes
\d students
```

## Security Testing

### Test SQL Injection Protection
```bash
# Should be sanitized
curl "http://localhost:8000/api/sessions/students/?search=' OR '1'='1"
```

### Test XSS Protection
```bash
# Should be sanitized
curl -X POST http://localhost:8000/api/sessions/students/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"first_name":"<script>alert(1)</script>"}'
```

## Next Steps

After testing:
1. Review test results
2. Fix any issues found
3. Run production deployment checklist
4. Perform security audit
5. Set up monitoring
