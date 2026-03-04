@echo off
REM Start backend (Django runserver) and frontend - use this if daphne fails with "No module named 'attr'"
REM WebSockets won't work; for full features fix attrs and use start_all.bat

set ROOT=%~dp0
cd /d "%ROOT%"

echo Starting Backend (runserver) and Frontend...
echo.

start "Rock Access - Backend" cmd /k "pushd "%ROOT%backend" && echo Backend starting on http://localhost:8000 && venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000"
timeout /t 3 /nobreak >nul
start "Rock Access - Frontend" cmd /k "pushd "%ROOT%frontend" && (if not exist node_modules\react call npm install) && npm start"

echo.
echo Two windows opened. When ready, open: http://localhost:3000
echo (Using runserver - no WebSockets. For daphne: pip install attrs in backend venv, then start_all.bat)
echo.
pause
