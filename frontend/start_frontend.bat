@echo off
REM Start React dev server from a drive letter (avoids UNC path limitation)
pushd "%~dp0"
if not exist "node_modules\react" (
    echo Installing dependencies...
    call npm install
)
npm start
popd
