@echo off
REM Create backend venv with Python 3.12 (Django 4.2 does not support Python 3.14)
REM Run from backend folder or project root. Requires: py -3.12 available (install Python 3.12 if needed)

set BACKEND=%~dp0
if not exist "%BACKEND%requirements.txt" set BACKEND=%~dp0backend\
cd /d "%BACKEND%"

echo Using Python 3.12 for Django compatibility...
py -3.12 -m venv venv
if errorlevel 1 (
    echo Python 3.12 not found. Install from https://www.python.org/downloads/ or run: py -0p to see installed versions
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Done. Start backend with: python manage.py runserver 0.0.0.0:8000
pause
