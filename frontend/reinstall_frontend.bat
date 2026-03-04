@echo off
REM Fix "Cannot find module 'shebang-regex'" - clean reinstall of frontend deps
cd /d "%~dp0"

echo Removing node_modules...
if exist node_modules rmdir /s /q node_modules

echo Reinstalling dependencies...
call npm install

echo.
echo Done. Run: npm start
pause
