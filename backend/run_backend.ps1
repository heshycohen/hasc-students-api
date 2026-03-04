# Run Django backend (use venv's Python directly - no activation needed)
# Prerequisites: 1) Fix DB_PASSWORD in backend\.env  2) PostgreSQL running  3) pip install -r ..\requirements.txt into venv once

$ErrorActionPreference = "Stop"
$BackendDir = $PSScriptRoot
$VenvPython = Join-Path $BackendDir "venv\Scripts\python.exe"
$Requirements = Join-Path (Split-Path $BackendDir -Parent) "requirements.txt"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating venv..."
    Push-Location $BackendDir
    python -m venv venv
    Pop-Location
}

Write-Host "Installing/updating dependencies into venv..."
& $VenvPython -m pip install -q -r $Requirements

Write-Host "Starting Django on 0.0.0.0:8000 ..."
Set-Location $BackendDir
& $VenvPython manage.py runserver 0.0.0.0:8000
