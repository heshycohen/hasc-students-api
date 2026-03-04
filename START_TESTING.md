# 🧪 Start Testing - Step by Step

## Quick Start (5 Minutes)

### 1. Check Prerequisites ✅

Make sure you have:

- ✅ Python 3.11+ installed
- ✅ Node.js 18+ installed  
- ✅ PostgreSQL running
- ✅ Redis (optional, for WebSocket features)

### 2. Backend Setup

```powershell
# Navigate to backend
cd rock-access-web\backend

# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (if not exists)
if (!(Test-Path ..\.env)) {
    Copy-Item ..\.env.example ..\.env
    Write-Host "⚠️  Please edit ..\.env with your database credentials"
}

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 3. Start Services

**Terminal 1 - Redis (for WebSocket):**
```powershell
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or download Redis for Windows
```

**Terminal 2 - Backend:**
```powershell
cd rock-access-web\backend
.\venv\Scripts\activate
daphne config.asgi:application
# Should see: "Starting server at tcp:port=8000:interface=127.0.0.1"
```

**Terminal 3 - Frontend:**
```powershell
cd rock-access-web\frontend
npm install
npm start
# Should open http://localhost:3000
```

### 4. Test Basic Functionality

1. **Open Browser**: http://localhost:3000
2. **Login**: Use your superuser credentials
3. **Create Session**: 
   - Go to Dashboard
   - Or use API: `POST http://localhost:8000/api/sessions/sessions/`
4. **Add Student**: Navigate to Students → Add Student
5. **Check Logs**: Go to Compliance Reports (admin only)

## Manual Testing Checklist

### Authentication ✅
- [ ] Can login with superuser
- [ ] Session timeout works (wait 15 min)
- [ ] Logout works

### Sessions ✅
- [ ] Create SY session
- [ ] Create Summer session
- [ ] Switch between sessions
- [ ] Set active session

### Students ✅
- [ ] Create student
- [ ] Edit student
- [ ] Delete student
- [ ] View student list
- [ ] Test encrypted fields (SSN, medical info)

### Employees ✅
- [ ] Create employee
- [ ] Edit employee
- [ ] Delete employee
- [ ] View employee list

### Data Inheritance ✅
- [ ] Create SY2024-25 with students
- [ ] Create Summer 2025, inherit from SY2024-25
- [ ] Verify students copied
- [ ] Create SY2025-26, inherit from Summer 2025
- [ ] Verify data copied correctly

### Concurrent Editing ✅
- [ ] Open student edit in 2 browser tabs
- [ ] See "other user editing" indicator
- [ ] Make changes in both tabs
- [ ] Verify conflict detection
- [ ] Test conflict resolution

### Compliance ✅
- [ ] Check access logs after any action
- [ ] Create disclosure log entry
- [ ] View compliance reports
- [ ] Check security events

## API Testing

### Get Authentication Token
```powershell
$body = @{
    email = "admin@example.com"
    password = "your_password"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/token/" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

$token = $response.access
Write-Host "Token: $token"
```

### Create Session
```powershell
$headers = @{
    Authorization = "Bearer $token"
    "Content-Type" = "application/json"
}

$sessionData = @{
    session_type = "SY"
    name = "SY2025-26"
    start_date = "2025-09-01"
    end_date = "2026-06-30"
    is_active = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/sessions/sessions/" `
    -Method POST `
    -Headers $headers `
    -Body $sessionData
```

### Create Student
```powershell
$studentData = @{
    session = 1
    first_name = "John"
    last_name = "Doe"
    date_of_birth = "2010-05-15"
    enrollment_date = "2025-09-01"
    status = "active"
    parent_email = "parent@example.com"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/sessions/students/" `
    -Method POST `
    -Headers $headers `
    -Body $studentData
```

## Import Access Database

```powershell
cd rock-access-web\backend
.\venv\Scripts\activate
python manage.py import_access_db "C:\path\to\your\SY2024-2025.accdb"
```

## Verify Everything Works

### Check Backend Health
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/sessions/current-session/" `
    -Headers @{Authorization = "Bearer $token"}
```

### Check Frontend
- Open http://localhost:3000
- Should see login page
- After login, should see dashboard

### Check WebSocket (if Redis running)
- Open browser console
- Edit a student
- Should see WebSocket connection messages

## Troubleshooting

### Backend won't start
- Check PostgreSQL is running
- Verify database credentials in `.env`
- Check port 8000 is not in use

### Frontend won't start
- Run `npm install` again
- Check port 3000 is not in use
- Clear browser cache

### WebSocket not connecting
- Verify Redis is running
- Check Daphne is running (not runserver)
- Check browser console for errors

### Database errors
```powershell
python manage.py makemigrations
python manage.py migrate
```

## Next Steps

1. ✅ Complete basic testing
2. ✅ Import your Access databases
3. ✅ Test with real data
4. ✅ Configure OAuth (optional)
5. ✅ Review compliance features
6. ✅ Plan production deployment

## Need Help?

- **Detailed Testing**: See `TESTING_GUIDE.md`
- **Deployment**: See `DEPLOYMENT.md`
- **API Docs**: http://localhost:8000/api/docs/
- **Concurrent Editing**: See `CONCURRENT_EDITING.md`
