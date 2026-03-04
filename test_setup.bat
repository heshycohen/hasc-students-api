@echo off
REM Quick setup script for testing on Windows

echo 🚀 Setting up School Year Management System for Testing
echo ==================================================
echo.

REM Check prerequisites
echo 📋 Checking prerequisites...

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.11+
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found. Please install Node.js 18+
    exit /b 1
)

echo ✅ Prerequisites check complete
echo.

REM Backend setup
echo 🔧 Setting up backend...
cd backend

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing Python dependencies...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo Checking for .env file...
if not exist ".env" (
    if exist ".env.example" (
        echo Creating .env from example...
        copy .env.example .env
        echo ⚠️  Please edit backend\.env with your database credentials
    ) else (
        echo ⚠️  No .env or .env.example in backend - create backend\.env with DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
    )
)

echo Running migrations...
python manage.py migrate --no-input

echo ✅ Backend setup complete
echo.

REM Frontend setup
echo 🎨 Setting up frontend...
cd ..\frontend

if not exist "node_modules" (
    echo Installing Node.js dependencies...
    call npm install --silent
)

echo ✅ Frontend setup complete
echo.

REM Summary
echo ==================================================
echo ✅ Setup Complete!
echo.
echo Next steps:
echo 1. Edit backend\.env with your database credentials (DB_PASSWORD etc.)
echo 2. Create superuser: cd backend ^&^& python manage.py createsuperuser
echo 3. Start Redis: docker run -d -p 6379:6379 redis:7-alpine
echo 4. Start backend: cd backend ^&^& daphne config.asgi:application
echo 5. Start frontend: cd frontend ^&^& npm start
echo.
echo Then visit:
echo - Frontend: http://localhost:3000
echo - Backend API: http://localhost:8000
echo - Admin Panel: http://localhost:8000/admin
echo - API Docs: http://localhost:8000/api/docs/
echo.

cd ..
