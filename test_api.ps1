# API Testing Script for PowerShell
# Tests the School Year Management System API

param(
    [string]$Email = "admin@example.com",
    [string]$Password = "admin123"
)

$API_URL = "http://localhost:8000/api"

Write-Host "🧪 Testing School Year Management System API" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Authentication
Write-Host "1️⃣  Testing Authentication..." -ForegroundColor Yellow
try {
    $body = @{
        email = $Email
        password = $Password
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$API_URL/auth/token/" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body `
        -ErrorAction Stop

    $token = $response.access
    if ($token) {
        Write-Host "✅ Authentication successful" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "❌ Authentication failed - no token received" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Authentication failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Make sure the backend server is running on port 8000" -ForegroundColor Yellow
    exit 1
}

# Test 2: Get Current User
Write-Host "2️⃣  Testing Get Current User..." -ForegroundColor Yellow
try {
    $headers = @{
        Authorization = "Bearer $token"
    }
    $userResponse = Invoke-RestMethod -Uri "$API_URL/auth/users/me/" `
        -Headers $headers `
        -ErrorAction Stop
    Write-Host "✅ Current user: $($userResponse.email)" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "❌ Failed to get current user: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
}

# Test 3: Get Sessions
Write-Host "3️⃣  Testing Get Sessions..." -ForegroundColor Yellow
try {
    $sessionsResponse = Invoke-RestMethod -Uri "$API_URL/sessions/sessions/" `
        -Headers $headers `
        -ErrorAction Stop
    $sessionCount = if ($sessionsResponse -is [array]) { $sessionsResponse.Count } else { $sessionsResponse.results.Count }
    Write-Host "✅ Found $sessionCount session(s)" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "❌ Failed to get sessions: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
}

# Test 4: Create Session (requires a site; use first available site)
Write-Host "4️⃣  Testing Create Session..." -ForegroundColor Yellow
$siteId = $null
try {
    $sitesResponse = Invoke-RestMethod -Uri "$API_URL/sessions/sites/" -Headers $headers -ErrorAction SilentlyContinue
    $sitesList = if ($sitesResponse -is [array]) { $sitesResponse } else { @($sitesResponse.results) }
    if ($sitesList -and $sitesList.Count -gt 0) { $siteId = $sitesList[0].id }
} catch { }
if (-not $siteId) { $siteId = 1 }
try {
    $uniqueName = "SY2025-26-API-Test-" + (Get-Date -Format "yyyyMMdd-HHmmss")
    $sessionData = @{
        site = $siteId
        session_type = "SY"
        name = $uniqueName
        start_date = "2025-09-01"
        end_date = "2026-06-30"
        is_active = $true
    } | ConvertTo-Json

    $newSession = Invoke-RestMethod -Uri "$API_URL/sessions/sessions/" `
        -Method POST `
        -Headers @{
            Authorization = "Bearer $token"
            "Content-Type" = "application/json"
        } `
        -Body $sessionData `
        -ErrorAction Stop

    Write-Host "✅ Session created: $($newSession.name) (ID: $($newSession.id))" -ForegroundColor Green
    $sessionId = $newSession.id
    Write-Host ""
} catch {
    Write-Host "❌ Failed to create session: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    $sessionId = $null
}

# Test 5: Create Student (if session created)
if ($sessionId) {
    Write-Host "5️⃣  Testing Create Student..." -ForegroundColor Yellow
    try {
        $studentData = @{
            session = $sessionId
            first_name = "John"
            last_name = "Doe"
            date_of_birth = "2010-05-15"
            enrollment_date = "2025-09-01"
            status = "active"
            parent_email = "parent@example.com"
        } | ConvertTo-Json

        $newStudent = Invoke-RestMethod -Uri "$API_URL/sessions/students/" `
            -Method POST `
            -Headers @{
                Authorization = "Bearer $token"
                "Content-Type" = "application/json"
            } `
            -Body $studentData `
            -ErrorAction Stop

        Write-Host "✅ Student created: $($newStudent.first_name) $($newStudent.last_name) (ID: $($newStudent.id))" -ForegroundColor Green
        Write-Host ""
    } catch {
        Write-Host "❌ Failed to create student: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
    }
}

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "✅ API Testing Complete!" -ForegroundColor Green
Write-Host ""
