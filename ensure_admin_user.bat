@echo off
REM Create or reset admin@example.com (password: admin123). Double-click or run from rock-access-web.
pushd "%~dp0backend"
call venv\Scripts\activate.bat
python manage.py ensure_admin_user
popd
pause
