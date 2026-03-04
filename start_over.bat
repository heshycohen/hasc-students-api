@echo off
REM Start over: fresh backend venv and frontend node_modules. Run from rock-access-web (or double-click).
REM Use a drive letter (e.g. R:) or pushd so we're not on a UNC path.

set ROOT=%~dp0
pushd "%ROOT%"

echo ========================================
echo   Start Over - Fresh Setup
echo ========================================
echo.

REM --- Backend: remove venv, recreate, install ---
echo [1/5] Removing old backend venv...
cd backend
if exist venv (
    rmdir /s /q venv
    echo      Old venv removed.
) else (
    echo      No venv found.
)
echo.

echo [2/5] Creating new virtual environment...
python -m venv venv
if errorlevel 1 (
    echo      ERROR: python -m venv failed. Check Python is installed.
    popd
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

echo [3/5] Installing backend dependencies (pip, setuptools, requirements)...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo      ERROR: pip install failed.
    popd
    pause
    exit /b 1
)

if not exist ".env" if exist ".env.example" (
    echo      Copying .env from .env.example...
    copy .env.example .env
)
echo Running migrations...
python manage.py migrate --no-input
echo Creating admin user (admin@example.com / admin123)...
python manage.py ensure_admin_user
cd ..
echo      Backend ready.
echo.

REM --- Frontend: reinstall node_modules ---
echo [4/5] Reinstalling frontend dependencies...
cd frontend
if exist node_modules (
    rmdir /s /q node_modules
    echo      Old node_modules removed.
)
call npm install
cd ..
echo      Frontend ready.
echo.

echo [5/5] Done.
echo ========================================
echo   Next: double-click start_all.bat
echo   Then open http://localhost:3000
echo   Log in: admin@example.com / admin123
echo ========================================
echo.
popd
pause
