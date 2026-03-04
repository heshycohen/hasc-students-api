@echo off
REM Install prerequisites via winget. Double-click or run from cmd.
REM Requires Windows 10/11 with winget (App Installer).

echo Installing prerequisites...
echo.

winget install Python.Python.3.12     --accept-package-agreements --accept-source-agreements --silent
winget install OpenJS.NodeJS.LTS      --accept-package-agreements --accept-source-agreements --silent
winget install PostgreSQL.PostgreSQL --accept-package-agreements --accept-source-agreements --silent
winget install Docker.DockerDesktop  --accept-package-agreements --accept-source-agreements --silent

echo.
echo Done. Close this window, open a NEW Command Prompt or PowerShell, then:
echo   1. Disable Python App execution aliases (Settings -^> App execution aliases -^> turn OFF python.exe, python3.exe)
echo   2. Create database: psql -U postgres -c "CREATE DATABASE rock_access;"
echo   3. Run: check_prerequisites.ps1
echo   4. See INSTALL_PREREQUISITES.md
echo.
pause
