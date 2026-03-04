#!/bin/bash
# Quick setup script for testing

set -e

echo "🚀 Setting up School Year Management System for Testing"
echo "=================================================="

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+"
    exit 1
fi

if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL client not found. Make sure PostgreSQL is installed."
fi

if ! command -v redis-cli &> /dev/null; then
    echo "⚠️  Redis not found. WebSocket features will not work."
fi

echo "✅ Prerequisites check complete"
echo ""

# Backend setup
echo "🔧 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "Checking for .env file..."
if [ ! -f "../.env" ]; then
    echo "Creating .env from example..."
    cp ../.env.example ../.env
    echo "⚠️  Please edit ../.env with your database credentials"
fi

echo "Running migrations..."
python manage.py migrate --no-input

echo "✅ Backend setup complete"
echo ""

# Frontend setup
echo "🎨 Setting up frontend..."
cd ../frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install --silent
fi

echo "✅ Frontend setup complete"
echo ""

# Summary
echo "=================================================="
echo "✅ Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Edit ../.env with your database credentials"
echo "2. Create superuser: cd backend && python manage.py createsuperuser"
echo "3. Start Redis: redis-server (or docker run -d -p 6379:6379 redis:7-alpine)"
echo "4. Start backend: cd backend && daphne config.asgi:application"
echo "5. Start frontend: cd frontend && npm start"
echo ""
echo "Then visit:"
echo "- Frontend: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo "- Admin Panel: http://localhost:8000/admin"
echo "- API Docs: http://localhost:8000/api/docs/"
echo ""
