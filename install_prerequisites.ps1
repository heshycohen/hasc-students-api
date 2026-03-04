# Install prerequisites for Rock Access using winget (Windows Package Manager)
# Run in PowerShell: .\install_prerequisites.ps1
# Or right-click -> Run with PowerShell (may need: Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned)

$ErrorActionPreference = "Continue"
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Rock Access - Install Prerequisites (winget)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check winget
try {
    $null = winget --version
} catch {
    Write-Host "winget not found. Install App Installer from Microsoft Store or use Windows 11/10 (build 10.0.17763+)." -ForegroundColor Red
    exit 1
}

$packages = @(
    @{ Id = "Python.Python.3.12";     Name = "Python 3.12";     Required = $true  },
    @{ Id = "OpenJS.NodeJS.LTS";      Name = "Node.js LTS";     Required = $true  },
    @{ Id = "PostgreSQL.PostgreSQL"; Name = "PostgreSQL";      Required = $true  },
    @{ Id = "Docker.DockerDesktop";   Name = "Docker Desktop";  Required = $false }
)

foreach ($p in $packages) {
    $req = if ($p.Required) { "Required" } else { "Optional" }
    Write-Host "Installing $($p.Name) ($req)..." -ForegroundColor Yellow
    $out = winget install $p.Id --accept-package-agreements --accept-source-agreements --silent 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: $($p.Name)" -ForegroundColor Green
    } else {
        Write-Host "  Note: $($out -join ' ')" -ForegroundColor Gray
    }
    Write-Host ""
}

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Done. Next steps:" -ForegroundColor Cyan
Write-Host "1. Close and reopen PowerShell/Command Prompt (so PATH updates)." -ForegroundColor White
Write-Host "2. Disable Python App Execution Aliases: Win -> Manage app execution aliases -> turn OFF python.exe, python3.exe" -ForegroundColor White
Write-Host "3. Create PostgreSQL database: open pgAdmin or run: psql -U postgres -c \"CREATE DATABASE rock_access;\"" -ForegroundColor White
Write-Host "4. Run: .\check_prerequisites.ps1" -ForegroundColor White
Write-Host "5. See INSTALL_PREREQUISITES.md for backend/frontend one-time setup." -ForegroundColor White
Write-Host "================================================" -ForegroundColor Cyan
