# Run frontend from a LOCAL copy so Node/npm don't hit UNC path limits.
# Serves the app at http://localhost:3000

$ErrorActionPreference = "Stop"
$source = "\\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web\frontend"
$dest = "$env:LOCALAPPDATA\RockAccessFrontend"

Write-Host "Copying frontend to local path: $dest" -ForegroundColor Cyan
if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Force -Path $dest | Out-Null }

# Copy source files (exclude node_modules to avoid UNC/long path issues)
$exclude = @("node_modules", ".git")
Get-ChildItem $source -Force | Where-Object { $exclude -notcontains $_.Name } | ForEach-Object {
    Copy-Item $_.FullName -Destination (Join-Path $dest $_.Name) -Recurse -Force
}

Set-Location $dest
if (-not (Test-Path "node_modules\react")) {
    Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
    npm install
}
Write-Host "Starting React dev server in a new window. Open http://localhost:3000 in your browser." -ForegroundColor Green
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd /d $dest && npm start" -WindowStyle Normal
