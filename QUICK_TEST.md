# Quick Test Guide

## Step 1: Initial Setup

### Windows:
```cmd
test_setup.bat
```

### Linux/Mac:
```bash
chmod +x test_setup.sh
./test_setup.sh
```

## Step 2: Configure Environment

Edit `.env` file with your database credentials:
```env
DB_NAME=rock_access
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your-secret-key-here
```

## Step 3: Create Admin User

```bash
cd backend
python manage.py createsuperuser
```

## Step 4: Start Services

### Terminal 1 - Start Redis (for WebSocket):
```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install and run locally
redis-server
```

### Terminal 2 - Start Backend:
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
daphne config.asgi:application
```

### Terminal 3 - Start Frontend:
```bash
cd frontend
npm start
```

## Step 5: Test the Application

1. **Open Browser**: http://localhost:3000
2. **Login** with your superuser credentials
3. **Create a Session**:
   - Click "Sessions" or use API
   - Create SY2025-26 session
   - Set as active
4. **Add a Student**:
   - Navigate to Students
   - Click "Add Student"
   - Fill in form and save
5. **Test Concurrent Editing**:
   - Open student edit in two browser tabs
   - Make changes in both
   - Verify conflict resolution
6. **Check Audit Logs**:
   - Navigate to Compliance Reports
   - Verify all actions are logged

## Step 6: Test API (Optional)

### Windows:
```cmd
test_api.bat admin@example.com your_password
```

### Linux/Mac:
```bash
chmod +x test_api.sh
./test_api.sh admin@example.com your_password
```

## Quick Verification Checklist

- [ ] Backend server starts without errors
- [ ] Frontend loads at http://localhost:3000
- [ ] Can login with superuser
- [ ] Can create a session
- [ ] Can add a student
- [ ] Can add an employee
- [ ] Session selector works
- [ ] Audit logs are created
- [ ] WebSocket connects (check browser console)

## Common Issues

### Database Connection Error
- Verify PostgreSQL is running
- Check credentials in `.env`
- Test connection: `psql -U postgres -d rock_access`

### Redis Connection Error
- Start Redis: `docker run -d -p 6379:6379 redis:7-alpine`
- Or install Redis locally

### Port Already in Use
- Backend (8000): Change in settings or stop other service
- Frontend (3000): Change PORT in package.json
- Redis (6379): Change in docker-compose.yml

### Migration Errors
```bash
python manage.py makemigrations
python manage.py migrate
```

## Next Steps After Testing

1. Review test results
2. Import your Access databases
3. Configure OAuth providers
4. Set up production environment
5. Review compliance checklist

For detailed testing scenarios, see `TESTING_GUIDE.md`
