# Test This Setup — Quick Runbook

Use this to verify the School Year Management System (rock-access-web) end-to-end.

---

## Start over (fresh setup)

If the backend venv is broken (e.g. `pip` not found, `pkg_resources` missing) or you want a clean install:

1. Go to `rock-access-web` in File Explorer (e.g. **R:\Rock-Access\rock-access-web** or the UNC path).
2. **Double‑click `start_over.bat`**.
3. Wait for it to finish (new venv, backend deps, migrations, admin user, frontend npm install).
4. Then **double‑click `start_all.bat`** to start backend and frontend.
5. Open **http://localhost:3000** and log in with **admin@example.com** / **admin123**.

Ensure **PostgreSQL** is running and **backend\\.env** has the correct database settings before running `start_over.bat`.

---

## Quick: Test in browser now

**Backend** and **frontend** have been started in the background. Try these in your browser:

| What | URL |
|------|-----|
| **Frontend (login, app)** | **http://localhost:3000** |
| **Backend API** | http://localhost:8000 |
| **Django admin** | http://localhost:8000/admin |
| **API docs** | http://localhost:8000/api/docs/ |

- If **frontend** doesn’t load: double‑click  
  `\\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web\frontend\start_frontend.bat`  
  (Running from a UNC path in a terminal can fail; double‑clicking the batch uses a drive letter.)
- If **backend** doesn’t respond: ensure PostgreSQL is running and `backend\.env` has the correct `DB_PASSWORD`, then start the backend again (see section 3 below).
- **Create a user and log in:** double‑click **ensure_admin_user.bat** (creates `admin@example.com` / `admin123`), then log in at http://localhost:3000. Or run `python manage.py createsuperuser` from `backend` with venv activated (see LOGIN_AND_LOGO.md).
- **Add your logo:** see **LOGIN_AND_LOGO.md** (put `logo.png` or `logo.svg` in `frontend\public\`).

---

## 1. Prerequisites (one-time)

In PowerShell from `rock-access-web`:

```powershell
.\check_prerequisites.ps1
```

You need: **Python 3.11+**, **Node.js 18+**, **PostgreSQL** (client + server). Redis and Docker are optional (Redis needed for WebSockets).

---

## 2. One-time setup

From `rock-access-web`:

```powershell
.\test_setup.bat
```

This creates `backend\venv`, installs backend and frontend dependencies, and runs migrations. If there is no `backend\.env`, it is created from `backend\.env.example`.

**Configure database:** Edit `rock-access-web\backend\.env` and set at least:

- `DB_NAME=rock_access` (or your DB name)
- `DB_USER=postgres`
- `DB_PASSWORD=your_postgres_password`
- `DB_HOST=localhost`
- `DB_PORT=5432`

Ensure the PostgreSQL server is running and the database exists (create with `createdb rock_access` if needed).

**Create admin user (pick one):**

- **Quick:** Double‑click **ensure_admin_user.bat** in `rock-access-web`. Creates `admin@example.com` with password `admin123`. Use these to log in at http://localhost:3000.
- **Custom:** From `rock-access-web` run:
  ```powershell
  cd backend
  .\venv\Scripts\activate
  python manage.py createsuperuser
  ```
  Enter your own email and password when prompted. Use them for login and for the API test script.

---

## 3. Start services (3 terminals)

**Terminal 1 – Redis (optional, for WebSocket):**

```powershell
docker run -d -p 6379:6379 redis:7-alpine
```

**Terminal 2 – Backend:**

```powershell
cd \\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web\backend
.\venv\Scripts\activate
daphne config.asgi:application
```

You should see the server listening on port 8000.

**Terminal 3 – Frontend:**

Because the project is on a UNC path, use the helper batch (it uses `pushd` so Node runs from a drive letter):

```cmd
\\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web\frontend\start_frontend.bat
```

Or from a **mapped drive** (e.g. `R:` → `\\hasc-aws-sql01\ACCESS\Rock-Access`):

```powershell
R:
cd R:\Rock-Access\rock-access-web\frontend
npm install
npm start
```

Browser should open at http://localhost:3000.

---

## 4. Manual UI test

1. Open **http://localhost:3000**
2. Log in with the superuser email/password
3. Create a session (e.g. SY2025-26)
4. Add a student and an employee
5. Open **Compliance Reports** and confirm actions are logged

---

## 5. API test (PowerShell)

With the **backend** running, from `rock-access-web`:

```powershell
.\test_api.ps1 -Email "your_admin@example.com" -Password "your_password"
```

Default if omitted: `admin@example.com` / `admin123`. The script checks auth, current user, sessions, creates a session and a student.

---

## 6. Useful URLs

| What        | URL                        |
|------------|----------------------------|
| Frontend   | http://localhost:3000      |
| Backend API| http://localhost:8000      |
| Admin      | http://localhost:8000/admin |
| API docs   | http://localhost:8000/api/docs/ |

---

## Troubleshooting

- **Backend won’t start:** PostgreSQL running? Correct `backend\.env`? Port 8000 free? If you see `No module named 'pkg_resources'`, run `pip install setuptools` in the backend venv, then start the backend again.
- **Migrations:** `cd backend`, activate venv, then `python manage.py migrate`
- **Frontend:** From `frontend`, run `npm install` again; ensure port 3000 is free
- **WebSocket:** Use Redis and start the backend with `daphne` (not `runserver`)

More detail: **START_TESTING.md**, **TESTING_GUIDE.md**, **QUICK_TEST.md**.

