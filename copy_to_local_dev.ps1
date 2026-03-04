# Copy Rock-Access project to C:\Dev for local development (avoids network drive slowness/issues).
# Run this from the network share (e.g. from rock-access-web folder or Rock-Access folder).
# Usage: .\copy_to_local_dev.ps1

$ErrorActionPreference = "Stop"
$SourceRoot = $PSScriptRoot
if ($SourceRoot -match "rock-access-web$") {
    $SourceRoot = Split-Path $SourceRoot -Parent
}
$DestRoot = "C:\Dev\Rock-Access"

Write-Host "Creating C:\Dev if needed..."
New-Item -ItemType Directory -Path "C:\Dev" -Force | Out-Null

Write-Host "Copying project from $SourceRoot to $DestRoot (excluding venv, node_modules, .git)..."
robocopy "$SourceRoot" "$DestRoot" /E /XD venv node_modules .git __pycache__ /R:2 /W:5 /MT:8
$rc = $LASTEXITCODE
# Robocopy: 0-7 = success (0 = nothing to copy, 1+ = copied)
if ($rc -ge 8) {
    Write-Error "Robocopy failed with exit code $rc"
    exit $rc
}

Write-Host "`nCopy complete. Local path: $DestRoot" -ForegroundColor Green
Write-Host "`n--- Next steps (run these after you're back) ---" -ForegroundColor Cyan
Write-Host "1. Open PowerShell and go to the backend:"
Write-Host "   cd $DestRoot\rock-access-web\backend"
Write-Host "2. Create a fresh venv with Python 3.12 (recommended):"
Write-Host "   py -3.12 -m venv venv"
Write-Host "   .\venv\Scripts\Activate.ps1"
Write-Host "3. Install dependencies and migrate:"
Write-Host "   pip install -r requirements.txt"
Write-Host "   python manage.py migrate"
Write-Host "   python manage.py makemigrations"
Write-Host "   python manage.py migrate"
Write-Host "   python manage.py createsuperuser"
Write-Host "4. Copy .env from network if needed (DB credentials, SECRET_KEY, etc.):"
Write-Host "   Copy-Item '\\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web\.env' '$DestRoot\rock-access-web\.env'"
Write-Host "5. Start backend:  daphne config.asgi:application"
Write-Host "6. In another terminal, frontend:  cd $DestRoot\rock-access-web\frontend ; npm install ; npm start"
Write-Host "`nDone."
