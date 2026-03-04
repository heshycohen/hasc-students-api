@echo off
REM Start backend and frontend in separate windows so you can log in at http://localhost:3000
REM Double-click this file (or run from cmd). Ensure PostgreSQL is running and backend\.env is set.

set ROOT=%~dp0
cd /d "%ROOT%"

echo Starting Backend and Frontend...
echo.

REM Backend window: use venv\Scripts\python.exe directly (no activate.bat needed)
start "Rock Access - Backend" cmd /k "pushd "%ROOT%backend" && echo Backend starting on http://localhost:8000 && venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000"

REM Give backend a moment to bind
timeout /t 3 /nobreak >nul

REM Frontend window (uses pushd so UNC path works)
start "Rock Access - Frontend" cmd /k "pushd "%ROOT%frontend" && (if not exist node_modules\react call npm install) && npm start"

echo.
echo Two windows opened:
echo   1. Backend  - http://localhost:8000
echo   2. Frontend - http://localhost:3000
echo.
echo When both are ready, open: http://localhost:3000 and log in.
echo.
echo No user yet? Double-click ensure_admin_user.bat (creates admin@example.com / admin123)
echo Or create one: cd backend, venv\Scripts\activate, python manage.py createsuperuser
echo.
pause
