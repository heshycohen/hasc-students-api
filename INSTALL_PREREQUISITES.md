# Install All Prerequisites (New Computer Setup)

Use this guide when setting up the **Rock Access** project on a new machine. Install in order and verify each step before continuing.

---

## Before You Start (Windows)

1. **Disable Python App Execution Aliases** (so `python` runs your real install):
   - Press **Win**, type **Manage app execution aliases**, open it.
   - Under **App Installer**, turn **OFF**: `python.exe` and `python3.exe`.

2. **Use a new Command Prompt or PowerShell** after each install so PATH updates.

---

## 1. Python 3.11+ (Required – Backend)

| Step | Action |
|------|--------|
| **Download** | https://www.python.org/downloads/ → Windows installer |
| **Install** | Run installer → **Check "Add python.exe to PATH"** → Complete |
| **Verify** | Open a **new** Command Prompt: `py --version` or `python --version` → should show 3.11+ |

If only `py` works, use `py` instead of `python` in all backend commands.

---

## 2. Node.js 18+ (Required – Frontend)

| Step | Action |
|------|--------|
| **Download** | https://nodejs.org/ → **LTS** Windows installer |
| **Install** | Run with default options (includes "Add to PATH") |
| **Verify** | Open a **new** Command Prompt: `node --version` and `npm --version` → both should show versions |

**If `npm` says "running scripts is disabled" in PowerShell:** run once (current user only):  
`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`  
Or use **Command Prompt (cmd)** instead of PowerShell for `npm install` and `npm start`; no policy there.

---

## 3. PostgreSQL 14+ (Required – Database)

| Step | Action |
|------|--------|
| **Download** | https://www.postgresql.org/download/windows/ |
| **Install** | Run installer; remember the **postgres user password** you set. |
| **Create DB** | After install, create database: `rock_access` (e.g. pgAdmin or `psql -U postgres -c "CREATE DATABASE rock_access;"`) |
| **Verify** | `psql --version` (optional; server can run without `psql` in PATH). Ensure **PostgreSQL service is running** (Services → postgresql-x64-14). |

---

## 4. Redis (Optional – WebSockets / concurrent editing)

| Option | Action |
|--------|--------|
| **Docker** | `docker run -d -p 6379:6379 redis:7-alpine` (if you have Docker) |
| **Windows** | https://github.com/microsoftarchive/redis/releases – install and run Redis. |
| **Skip** | App runs without Redis; WebSocket features will be disabled. |

---

## 5. Docker (Optional – run everything in containers)

| Step | Action |
|------|--------|
| **Download** | https://www.docker.com/products/docker-desktop |
| **Install** | Install Docker Desktop and start it. |
| **Verify** | `docker --version` and `docker compose version`. |

If Docker is installed, you can use `docker compose up -d` instead of installing Python, Node, and Redis locally (PostgreSQL can run in Docker too).

---

## Verify Everything

From the project root in PowerShell (you may need to allow scripts once: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`):

```powershell
cd "\\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web"
.\check_prerequisites.ps1
```

Or in Command Prompt, check manually:

```cmd
py --version
node --version
npm --version
psql --version
```

---

## One-Time Project Setup (After Prerequisites)

### Backend

```cmd
cd /d "\\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web\backend"
py -m venv venv
venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python manage.py migrate
```

(Use `python` if it works; otherwise `py` for the first two and `py -m pip` / `py manage.py` for the rest.)

### Environment (Database)

- Copy or create `backend\.env` (or ensure root `.env` has DB settings and backend reads it).
- Set at least: `DB_PASSWORD=` (your PostgreSQL password), `SECRET_KEY=` (long random string).
- Defaults: `DB_HOST=localhost`, `DB_NAME=rock_access`, `DB_USER=postgres`, `DB_PORT=5432`.

### Frontend

```cmd
cd /d "\\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web\frontend"
npm install
```

---

## Start the App

Double-click **`start_all.bat`** in the project root, or:

- **Terminal 1 – Backend:** `cd backend` → `venv\Scripts\activate.bat` → `daphne config.asgi:application`
- **Terminal 2 – Frontend:** `cd frontend` → `npm start`

Then open **http://localhost:3000**.

---

## Corrupt venv or "No such file" / "invalid distribution ~ip" after network drop

If pip fails with `FileNotFoundError` under `venv\Lib\site-packages\pip` or "invalid distribution ~ip", the venv is likely corrupted (e.g. after a network disconnect when the project is on a mapped/UNC path). Recreate the venv from the **same path** you use to run the app (e.g. Z:):

```powershell
cd Z:\Rock-Access\rock-access-web\backend
Remove-Item -Recurse -Force venv -ErrorAction SilentlyContinue
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py runserver 0.0.0.0:8000
```

Use **runserver** (or **start_all_runserver.bat**) to avoid the daphne/attr issue. For daphne later, ensure `attrs` is installed in the new venv.

---

## Moved project or different drive? "Unable to create process... python.exe"

If you see **Fatal error in launcher** pointing to a path like `P:\...\venv\Scripts\python.exe` but your project is now on Z: or a UNC path, the venv was created elsewhere. Recreate it:

**Command Prompt (cmd):**
```cmd
cd /d Z:\Rock-Access\rock-access-web\backend
rmdir /s /q venv
py -m venv venv
venv\Scripts\activate.bat
python -m pip install -r requirements.txt
py manage.py migrate
```

**PowerShell:** (use `cd` without `/d`, and `Remove-Item` instead of `rmdir /s /q`)
```powershell
cd Z:\Rock-Access\rock-access-web\backend
Remove-Item -Recurse -Force venv -ErrorAction SilentlyContinue
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
py manage.py migrate
```

Then run `start_all.bat` or start daphne again.

---

## Quick Reference

| Prerequisite | Required? | Check command |
|--------------|-----------|----------------|
| Python 3.11+ | Yes | `py --version` or `python --version` |
| Node.js 18+ | Yes | `node --version` |
| npm | Yes (with Node) | `npm --version` |
| PostgreSQL 14+ | Yes | Service running + DB `rock_access` |
| Redis | Optional | `redis-cli ping` → PONG |
| Docker | Optional | `docker --version` |
