# Run Full Setup and Test
# Execute from rock-access-web in PowerShell:
#   cd \\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web
#   .\run_full_test.ps1
#
# For API test, start the backend first in another terminal (see step 5 below).
# Optional args: .\run_full_test.ps1 -Email "you@example.com" -Password "yourpassword"

param(
    [string]$Email = "admin@example.com",
    [string]$Password = "admin123"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$Backend = Join-Path $ProjectRoot "backend"
$Frontend = Join-Path $ProjectRoot "frontend"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Rock-Access: Full setup and test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Prerequisites
Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Yellow
& (Join-Path $ProjectRoot "check_prerequisites.ps1")
Write-Host ""

# 2. Backend setup
Write-Host "[2/5] Backend setup (venv, pip, .env, migrate)..." -ForegroundColor Yellow
Push-Location $Backend
try {
    if (-not (Test-Path "venv")) {
        python -m venv venv
        Write-Host "   Created venv." -ForegroundColor Green
    }
    & ".\venv\Scripts\pip.exe" install --quiet -r requirements.txt
    Write-Host "   Pip install done." -ForegroundColor Green
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host "   Created .env from .env.example - EDIT backend\.env with DB_PASSWORD." -ForegroundColor Yellow
    }
    & ".\venv\Scripts\python.exe" manage.py migrate --no-input
    Write-Host "   Migrations done." -ForegroundColor Green
} catch {
    Write-Host "   Error: $_" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location
Write-Host ""

# 3. Superuser reminder
Write-Host "[3/5] Ensure a superuser exists. If not, run:" -ForegroundColor Yellow
Write-Host "   cd backend; .\venv\Scripts\activate; python manage.py createsuperuser" -ForegroundColor White
Write-Host ""

# 4. Redis (optional)
Write-Host "[4/5] Redis (optional for WebSocket):" -ForegroundColor Yellow
try {
    $null = docker ps 2>$null
    docker run -d -p 6379:6379 --name rock-access-redis redis:7-alpine 2>$null
    Write-Host "   Redis container started." -ForegroundColor Green
} catch {
    $cid = docker ps -q --filter "name=rock-access-redis" 2>$null
    if ($cid) { Write-Host "   Redis already running." -ForegroundColor Green }
    else { Write-Host "   Skip or run: docker run -d -p 6379:6379 redis:7-alpine" -ForegroundColor Gray }
}
Write-Host ""

# 5. API test (backend must be running)
Write-Host "[5/5] API test..." -ForegroundColor Yellow
Write-Host "   Start backend in another terminal first:" -ForegroundColor Gray
Write-Host "   cd $Backend" -ForegroundColor Gray
Write-Host "   .\venv\Scripts\activate" -ForegroundColor Gray
Write-Host "   daphne config.asgi:application" -ForegroundColor Gray
Write-Host ""
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/sessions/current-session/" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   Backend is up. Running test_api.ps1 ..." -ForegroundColor Green
    & (Join-Path $ProjectRoot "test_api.ps1") -Email $Email -Password $Password
} catch {
    Write-Host "   Backend not reachable at http://localhost:8000 - start it, then run:" -ForegroundColor Yellow
    Write-Host "   .\test_api.ps1 -Email $Email -Password $Password" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Frontend: in another terminal run:" -ForegroundColor Cyan
Write-Host "   cd $Frontend" -ForegroundColor White
Write-Host "   npm install" -ForegroundColor White
Write-Host "   npm start" -ForegroundColor White
Write-Host " Then open http://localhost:3000" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
