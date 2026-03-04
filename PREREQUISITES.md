# Prerequisites Checklist

**Setting up on a new computer?** See **[INSTALL_PREREQUISITES.md](INSTALL_PREREQUISITES.md)** for step-by-step install and verification.

## Required Software

### 1. Python 3.11+ ✅ Required
- **Check**: `python --version`
- **Download**: https://www.python.org/downloads/
- **Purpose**: Backend Django application
- **Status**: Run `check_prerequisites.ps1` to verify

### 2. Node.js 18+ ✅ Required
- **Check**: `node --version`
- **Download**: https://nodejs.org/
- **Purpose**: Frontend React application
- **Status**: Run `check_prerequisites.ps1` to verify

### 3. PostgreSQL 14+ ✅ Required
- **Check**: `psql --version`
- **Download**: https://www.postgresql.org/download/
- **Purpose**: Database server
- **Alternative**: Use Docker: `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:14`
- **Status**: Run `check_prerequisites.ps1` to verify

### 4. Redis ⚠️ Optional (Required for WebSocket)
- **Check**: `redis-cli --version`
- **Download**: https://redis.io/download
- **Purpose**: WebSocket channel layer for concurrent editing
- **Alternative**: Use Docker: `docker run -d -p 6379:6379 redis:7-alpine`
- **Status**: Run `check_prerequisites.ps1` to verify

### 5. Docker ⚠️ Optional (Recommended)
- **Check**: `docker --version`
- **Download**: https://www.docker.com/products/docker-desktop
- **Purpose**: Containerized deployment
- **Status**: Run `check_prerequisites.ps1` to verify

## Quick Check

Run the prerequisite checker:
```powershell
cd rock-access-web
.\check_prerequisites.ps1
```

Or check manually:

```powershell
# Python
python --version  # Should be 3.11+

# Node.js
node --version    # Should be 18+

# PostgreSQL
psql --version    # Should be 14+

# Redis (optional)
redis-cli --version

# Docker (optional)
docker --version
```

## Installation Guide

### Windows

1. **Python**:
   - Download from https://www.python.org/downloads/
   - Check "Add Python to PATH" during installation
   - Verify: `python --version`

2. **Node.js**:
   - Download LTS version from https://nodejs.org/
   - Install with default options
   - Verify: `node --version` and `npm --version`

3. **PostgreSQL**:
   - Download from https://www.postgresql.org/download/windows/
   - Install with default options
   - Remember the postgres user password
   - Verify: `psql --version`

4. **Redis** (Optional):
   - Option 1: Use Docker (recommended)
     ```powershell
     docker run -d -p 6379:6379 redis:7-alpine
     ```
   - Option 2: Download Windows version from https://github.com/microsoftarchive/redis/releases

5. **Docker** (Optional):
   - Download Docker Desktop from https://www.docker.com/products/docker-desktop
   - Install and start Docker Desktop
   - Verify: `docker --version`

### Linux/Mac

1. **Python**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install python3.11 python3-pip python3-venv
   
   # macOS
   brew install python@3.11
   ```

2. **Node.js**:
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt-get install -y nodejs
   
   # macOS
   brew install node@18
   ```

3. **PostgreSQL**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql-14
   sudo systemctl start postgresql
   
   # macOS
   brew install postgresql@14
   brew services start postgresql@14
   ```

4. **Redis**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   sudo systemctl start redis
   
   # macOS
   brew install redis
   brew services start redis
   ```

5. **Docker**:
   ```bash
   # Follow instructions at https://docs.docker.com/get-docker/
   ```

## Verify Installation

After installing, run:
```powershell
.\check_prerequisites.ps1
```

Expected output:
```
✅ Python 3.11.x
✅ Node.js v18.x.x
✅ PostgreSQL client found
✅ Redis client found (or ⚠️ Optional)
✅ Docker found (or ⚠️ Optional)
✅ Project structure OK
```

## Next Steps

Once all prerequisites are installed:

1. **Set up backend**:
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Set up frontend**:
   ```powershell
   cd frontend
   npm install
   ```

3. **Configure database**:
   - Create PostgreSQL database
   - Update `.env` file with credentials

4. **Start services**:
   - Start PostgreSQL
   - Start Redis (if using WebSocket)
   - Run migrations
   - Start backend and frontend

See `START_TESTING.md` for detailed setup instructions.

## Troubleshooting

### Python not found
- Ensure Python is added to PATH
- Restart terminal after installation
- Try `python3` instead of `python` on Linux/Mac

### Node.js not found
- Ensure Node.js is added to PATH
- Restart terminal after installation
- Verify npm is also installed: `npm --version`

### PostgreSQL connection issues
- Ensure PostgreSQL service is running
- Check if port 5432 is available
- Verify credentials in `.env` file

### Redis connection issues
- Ensure Redis is running: `redis-cli ping` (should return PONG)
- Check if port 6379 is available
- Use Docker if local installation fails

### Docker issues
- Ensure Docker Desktop is running
- Check Docker daemon: `docker ps`
- Verify Docker has sufficient resources allocated
