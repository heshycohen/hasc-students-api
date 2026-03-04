# Clean venv and reinstall - run from backend folder
# Usage: .\rebuild_venv.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== Cleaning and rebuilding venv ===" -ForegroundColor Cyan

# Use venv2 if venv is locked (something using it)
$venvName = "venv"
if (Test-Path venv) {
    $venvBackup = "venv_old_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Write-Host "Attempting to rename existing venv to $venvBackup..." -ForegroundColor Yellow
    try {
        Rename-Item -Path venv -NewName $venvBackup -Force
        Write-Host "Old venv renamed." -ForegroundColor Green
    } catch {
        Write-Host "Venv is in use; creating fresh venv as 'venv2'. Activate with: .\venv2\Scripts\Activate.ps1" -ForegroundColor Yellow
        $venvName = "venv2"
    }
}

# Create new venv
Write-Host "`nCreating new venv ($venvName)..." -ForegroundColor Yellow
python -m venv $venvName
if (-not $?) { throw "Failed to create venv" }
Write-Host "Venv created." -ForegroundColor Green

# Activate and install
Write-Host "`nActivating venv and installing packages..." -ForegroundColor Yellow
& ".\$venvName\Scripts\Activate.ps1"
python -m pip install --upgrade pip --quiet
python -m pip install --no-cache-dir -r requirements.txt
if (-not $?) { throw "Failed to install requirements" }
Write-Host "Packages installed." -ForegroundColor Green

# Run test
Write-Host "`nRunning Azure KMS test..." -ForegroundColor Yellow
python test_azure_kms.py

Write-Host "`n=== Done ===" -ForegroundColor Cyan
