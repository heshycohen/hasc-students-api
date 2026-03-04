# Prerequisites Checker for School Year Management System
# Run this script to verify all required software is installed

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Prerequisites Checker" -ForegroundColor Cyan
Write-Host "School Year Management System" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# Check Python (try python first, then py for Windows)
Write-Host "Checking Python..." -ForegroundColor Yellow
$pythonVersion = $null
try { $pythonVersion = python --version 2>&1 } catch { }
if (-not $pythonVersion -or $pythonVersion -match "not found|Microsoft Store") {
    try { $pythonVersion = py --version 2>&1 } catch { }
}
if ($pythonVersion -match "Python (\d+)\.(\d+)") {
    $major = [int]$matches[1]
    $minor = [int]$matches[2]
    if ($major -ge 3 -and $minor -ge 11) {
        Write-Host "  ✅ Python $pythonVersion (Required: 3.11+)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Python $pythonVersion (Required: 3.11+)" -ForegroundColor Red
        $allGood = $false
    }
} else {
    Write-Host "  ❌ Python not found or version could not be determined" -ForegroundColor Red
    Write-Host "     Download from: https://www.python.org/downloads/ (check Add to PATH)" -ForegroundColor Yellow
    Write-Host "     Disable App execution aliases for python.exe in Windows Settings" -ForegroundColor Yellow
    $allGood = $false
}
Write-Host ""

# Check Node.js
Write-Host "Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    if ($nodeVersion -match "v(\d+)\.(\d+)") {
        $major = [int]$matches[1]
        if ($major -ge 18) {
            Write-Host "  ✅ Node.js $nodeVersion (Required: 18+)" -ForegroundColor Green
        } else {
            Write-Host "  ❌ Node.js $nodeVersion (Required: 18+)" -ForegroundColor Red
            $allGood = $false
        }
    } else {
        Write-Host "  ❌ Node.js not found or version could not be determined" -ForegroundColor Red
        $allGood = $false
    }
} catch {
    Write-Host "  ❌ Node.js not installed" -ForegroundColor Red
    Write-Host "     Download from: https://nodejs.org/" -ForegroundColor Yellow
    $allGood = $false
}
# Also verify npm (comes with Node)
try {
    $npmVersion = npm --version 2>&1
    if ($npmVersion -match "^\d+") {
        Write-Host "  ✅ npm $npmVersion" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  npm not found (usually comes with Node.js)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠️  npm not found" -ForegroundColor Yellow
}
Write-Host ""

# Check PostgreSQL
Write-Host "Checking PostgreSQL..." -ForegroundColor Yellow
try {
    $psqlVersion = psql --version 2>&1
    if ($psqlVersion) {
        Write-Host "  ✅ PostgreSQL client found: $psqlVersion" -ForegroundColor Green
        Write-Host "     Make sure PostgreSQL server is running" -ForegroundColor Yellow
    } else {
        Write-Host "  ⚠️  PostgreSQL client not found in PATH" -ForegroundColor Yellow
        Write-Host "     PostgreSQL server may still be installed" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠️  PostgreSQL client not found in PATH" -ForegroundColor Yellow
    Write-Host "     Download from: https://www.postgresql.org/download/" -ForegroundColor Yellow
    Write-Host "     Or use Docker: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:14" -ForegroundColor Yellow
}
Write-Host ""

# Check Redis
Write-Host "Checking Redis..." -ForegroundColor Yellow
try {
    $redisVersion = redis-cli --version 2>&1
    if ($redisVersion) {
        Write-Host "  ✅ Redis client found: $redisVersion" -ForegroundColor Green
        Write-Host "     Make sure Redis server is running" -ForegroundColor Yellow
    } else {
        Write-Host "  ⚠️  Redis not found (Optional for WebSocket features)" -ForegroundColor Yellow
        Write-Host "     Use Docker: docker run -d -p 6379:6379 redis:7-alpine" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠️  Redis not found (Optional for WebSocket features)" -ForegroundColor Yellow
    Write-Host "     Use Docker: docker run -d -p 6379:6379 redis:7-alpine" -ForegroundColor Yellow
}
Write-Host ""

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    if ($dockerVersion) {
        Write-Host "  ✅ Docker found: $dockerVersion" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Docker not found (Optional, but recommended)" -ForegroundColor Yellow
        Write-Host "     Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠️  Docker not found (Optional, but recommended)" -ForegroundColor Yellow
    Write-Host "     Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
}
Write-Host ""

# Check Git
Write-Host "Checking Git..." -ForegroundColor Yellow
try {
    $gitVersion = git --version 2>&1
    if ($gitVersion) {
        Write-Host "  ✅ Git found: $gitVersion" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Git not found (Optional)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠️  Git not found (Optional)" -ForegroundColor Yellow
}
Write-Host ""

# Check project structure
Write-Host "Checking project structure..." -ForegroundColor Yellow
$requiredDirs = @(
    "backend",
    "frontend",
    "backend\config",
    "backend\sessions",
    "backend\users",
    "backend\compliance",
    "frontend\src"
)

$structureGood = $true
foreach ($dir in $requiredDirs) {
    if (Test-Path $dir) {
        Write-Host "  ✅ $dir" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $dir (missing)" -ForegroundColor Red
        $structureGood = $false
        $allGood = $false
    }
}
Write-Host ""

# Check key files
Write-Host "Checking key files..." -ForegroundColor Yellow
$requiredFiles = @(
    "backend\manage.py",
    "backend\config\settings.py",
    "backend\requirements.txt",
    "frontend\package.json",
    "docker-compose.yml"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $file (missing)" -ForegroundColor Red
        $allGood = $false
    }
}
Write-Host ""

# Summary
Write-Host "================================================" -ForegroundColor Cyan
if ($allGood) {
    Write-Host "✅ All critical prerequisites are met!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Ensure PostgreSQL is running" -ForegroundColor White
    Write-Host "2. Start Redis (optional): docker run -d -p 6379:6379 redis:7-alpine" -ForegroundColor White
    Write-Host "3. Run: .\test_setup.bat" -ForegroundColor White
    Write-Host "4. Follow START_TESTING.md for detailed instructions" -ForegroundColor White
} else {
    Write-Host "❌ Some prerequisites are missing" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install the missing software and run this script again." -ForegroundColor Yellow
}
Write-Host "================================================" -ForegroundColor Cyan
