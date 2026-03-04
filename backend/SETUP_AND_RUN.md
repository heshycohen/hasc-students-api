# Backend setup and run

## 1. Fix PostgreSQL password (required)

The app connects as user `postgres`. Edit **`backend\.env`** and set the real password:

```env
DB_PASSWORD=your_actual_postgres_password
```

If you don't know it, set a new one in PostgreSQL then put that in `.env`. The database `rock_access` must exist (create it in pgAdmin or: `psql -U postgres -c "CREATE DATABASE rock_access;"`).

## 2. Install dependencies into the venv

From **`backend`** folder, use the venv's Python so packages install inside the venv (not global):

```powershell
cd U:\Rock-Access\rock-access-web\backend
.\venv\Scripts\python.exe -m pip install -r ..\requirements.txt
```

If `venv` doesn't exist yet:

```powershell
cd U:\Rock-Access\rock-access-web\backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r ..\requirements.txt
```

## 3. Activate venv (optional)

PowerShell may block scripts. To activate the venv:

```powershell
# Allow running local scripts (once per machine)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate
.\venv\Scripts\Activate.ps1
```

If you prefer not to activate, use the venv Python explicitly: `.\venv\Scripts\python.exe manage.py ...`

## 4. Migrate and run

```powershell
cd U:\Rock-Access\rock-access-web\backend
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

Or use the helper script (after fixing `DB_PASSWORD` in `.env`):

```powershell
cd U:\Rock-Access\rock-access-web\backend
.\run_backend.ps1
```

## Permission denied on `venv\Scripts\python.exe`

- Close any other terminal or IDE that’s using this venv (e.g. a running `runserver`).
- If the project is on a network drive, copying the project to a local disk and running from there can avoid locking issues.
