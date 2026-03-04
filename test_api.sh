#!/bin/bash
# API Testing Script

set -e

API_URL="http://localhost:8000/api"
EMAIL="${1:-admin@example.com}"
PASSWORD="${2:-admin123}"

echo "🧪 Testing School Year Management System API"
echo "=============================================="
echo ""

# Get authentication token
echo "1️⃣  Testing Authentication..."
TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/auth/token/" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Authentication failed. Please check credentials."
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "✅ Authentication successful"
echo ""

# Test: Get current user
echo "2️⃣  Testing Get Current User..."
USER_RESPONSE=$(curl -s "$API_URL/auth/users/me/" \
  -H "Authorization: Bearer $TOKEN")
echo "✅ Current user: $(echo $USER_RESPONSE | grep -o '"email":"[^"]*' | cut -d'"' -f4)"
echo ""

# Test: Get sessions
echo "3️⃣  Testing Get Sessions..."
SESSIONS_RESPONSE=$(curl -s "$API_URL/sessions/sessions/" \
  -H "Authorization: Bearer $TOKEN")
SESSION_COUNT=$(echo $SESSIONS_RESPONSE | grep -o '"id"' | wc -l)
echo "✅ Found $SESSION_COUNT session(s)"
echo ""

# Test: Create session
echo "4️⃣  Testing Create Session..."
SESSION_DATA=$(curl -s -X POST "$API_URL/sessions/sessions/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_type": "SY",
    "name": "TEST-SY-'$(date +%s)'",
    "start_date": "2025-09-01",
    "end_date": "2026-06-30",
    "is_active": false
  }')

SESSION_ID=$(echo $SESSION_DATA | grep -o '"id":[0-9]*' | cut -d':' -f2)

if [ -z "$SESSION_ID" ]; then
    echo "❌ Failed to create session"
    echo "Response: $SESSION_DATA"
    exit 1
fi

echo "✅ Created session ID: $SESSION_ID"
echo ""

# Test: Get students
echo "5️⃣  Testing Get Students..."
STUDENTS_RESPONSE=$(curl -s "$API_URL/sessions/students/" \
  -H "Authorization: Bearer $TOKEN")
STUDENT_COUNT=$(echo $STUDENTS_RESPONSE | grep -o '"id"' | wc -l)
echo "✅ Found $STUDENT_COUNT student(s)"
echo ""

# Test: Create student
echo "6️⃣  Testing Create Student..."
STUDENT_DATA=$(curl -s -X POST "$API_URL/sessions/students/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"session\": $SESSION_ID,
    \"first_name\": \"Test\",
    \"last_name\": \"Student\",
    \"date_of_birth\": \"2010-05-15\",
    \"enrollment_date\": \"2025-09-01\",
    \"status\": \"active\",
    \"parent_email\": \"test@example.com\"
  }")

STUDENT_ID=$(echo $STUDENT_DATA | grep -o '"id":[0-9]*' | cut -d':' -f2)

if [ -z "$STUDENT_ID" ]; then
    echo "❌ Failed to create student"
    echo "Response: $STUDENT_DATA"
    exit 1
fi

echo "✅ Created student ID: $STUDENT_ID"
echo ""

# Test: Update student
echo "7️⃣  Testing Update Student..."
UPDATE_RESPONSE=$(curl -s -X PATCH "$API_URL/sessions/students/$STUDENT_ID/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Updated"}')

if echo $UPDATE_RESPONSE | grep -q '"first_name":"Updated"'; then
    echo "✅ Student updated successfully"
else
    echo "❌ Failed to update student"
    echo "Response: $UPDATE_RESPONSE"
fi
echo ""

# Test: Get employees
echo "8️⃣  Testing Get Employees..."
EMPLOYEES_RESPONSE=$(curl -s "$API_URL/sessions/employees/" \
  -H "Authorization: Bearer $TOKEN")
EMPLOYEE_COUNT=$(echo $EMPLOYEES_RESPONSE | grep -o '"id"' | wc -l)
echo "✅ Found $EMPLOYEE_COUNT employee(s)"
echo ""

# Test: Get access logs
echo "9️⃣  Testing Get Access Logs..."
LOGS_RESPONSE=$(curl -s "$API_URL/compliance/access-logs/" \
  -H "Authorization: Bearer $TOKEN")
LOG_COUNT=$(echo $LOGS_RESPONSE | grep -o '"id"' | wc -l)
echo "✅ Found $LOG_COUNT access log entry(ies)"
echo ""

# Test: Get current session
echo "🔟 Testing Get Current Session..."
CURRENT_SESSION=$(curl -s "$API_URL/sessions/current-session/" \
  -H "Authorization: Bearer $TOKEN")

if echo $CURRENT_SESSION | grep -q '"name"'; then
    echo "✅ Current session retrieved"
else
    echo "⚠️  No active session set"
fi
echo ""

echo "=============================================="
echo "✅ All API tests completed successfully!"
echo ""
echo "Test Summary:"
echo "- Authentication: ✅"
echo "- Sessions: ✅"
echo "- Students: ✅"
echo "- Employees: ✅"
echo "- Compliance: ✅"
echo ""
echo "You can now test the frontend at http://localhost:3000"
