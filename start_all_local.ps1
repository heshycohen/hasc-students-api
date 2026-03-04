# Start all Rock-Access services locally
# Run from: C:\Dev\Rock-Access\rock-access-web
# Usage: .\start_all_local.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"
$FrontendPath = Join-Path $ProjectRoot "frontend"

Write-Host "=== Rock-Access Local Startup ===" -ForegroundColor Cyan

# 1. Ensure venv exists and dependencies installed
if (-not (Test-Path (Join-Path $BackendPath "venv\Scripts\python.exe"))) {
    Write-Host "Creating backend venv (Python 3.12)..." -ForegroundColor Yellow
    Push-Location $BackendPath
    try {
        py -3.12 -m venv venv 2>$null
        if (-not $?) { python -m venv venv }
        & .\venv\Scripts\Activate.ps1
        pip install --no-cache-dir -r requirements.txt -q
        Write-Host "Backend dependencies installed." -ForegroundColor Green
    } finally { Pop-Location }
}

# 2. Run migrations
Write-Host "Running migrations..." -ForegroundColor Yellow
Push-Location $BackendPath
try {
    & .\venv\Scripts\python.exe manage.py migrate --noinput 2>&1 | Out-Host
} finally { Pop-Location }

# 3. Start Redis (Docker) if available
$redisRunning = $false
try {
    docker ps 2>$null | Select-String "6379" | Out-Null
    if ($?) { $redisRunning = $true }
} catch {}
if (-not $redisRunning) {
    Write-Host "Starting Redis via Docker..." -ForegroundColor Yellow
    Start-Process -FilePath "docker" -ArgumentList "run -d -p 6379:6379 redis:7-alpine" -Wait -NoNewWindow -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -eq 0) { Write-Host "Redis started." -ForegroundColor Green }
    else { Write-Host "Redis not started (Docker may not be running). WebSocket features may not work." -ForegroundColor Yellow }
}

# 4. Start backend (daphne)
Write-Host "Starting backend (daphne)..." -ForegroundColor Yellow
$daphneJob = Start-Process -FilePath (Join-Path $BackendPath "venv\Scripts\daphne.exe") `
    -ArgumentList "config.asgi:application" `
    -WorkingDirectory $BackendPath `
    -PassThru -WindowStyle Normal
Write-Host "Backend PID: $($daphneJob.Id) - http://localhost:8000" -ForegroundColor Green

# 5. Install frontend deps if needed, start React
if (-not (Test-Path (Join-Path $FrontendPath "node_modules"))) {
    Write-Host "Installing frontend dependencies (npm install)..." -ForegroundColor Yellow
    Push-Location $FrontendPath
    npm install
    Pop-Location
}
Write-Host "Starting frontend (npm start)..." -ForegroundColor Yellow
Start-Process -FilePath "npm" -ArgumentList "start" -WorkingDirectory $FrontendPath -WindowStyle Normal

Write-Host "`n=== Services Started ===" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3000"
Write-Host "Backend API: http://localhost:8000"
Write-Host "Admin: http://localhost:8000/admin"
Write-Host "API Docs: http://localhost:8000/api/docs/"
Write-Host "`nCreate superuser if needed: cd backend; .\venv\Scripts\Activate.ps1; python manage.py createsuperuser"
