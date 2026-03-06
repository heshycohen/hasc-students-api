# AGENTS.md

## Cursor Cloud specific instructions

### Architecture overview

This is a **School Year Management System** (HASC) with a Django backend and React frontend. See `README.md` for the full tech stack and quick-start commands.

| Service | Command | Port |
|---------|---------|------|
| PostgreSQL | `sudo pg_ctlcluster 16 main start` | 5432 |
| Backend (Daphne) | `cd backend && source venv/bin/activate && daphne -b 0.0.0.0 -p 8000 config.asgi:application` | 8000 |
| Frontend (React) | `cd frontend && BROWSER=none npm start` | 3000 |

### Non-obvious setup notes

- **setuptools version**: `setuptools>=82` removed `pkg_resources`, which breaks `rest_framework_simplejwt`. The update script pins `setuptools<82` to avoid this. If you see `ModuleNotFoundError: No module named 'pkg_resources'`, run `pip install 'setuptools<82'` in the backend venv.
- **unixodbc-dev**: Required system package for `pyodbc` (Access DB import tests). Without it, `import pyodbc` fails and one test module errors. Already installed in the VM snapshot.
- **PostgreSQL**: The database `rock_access` must exist with user `postgres` and password `devpassword`. The `.env` at `backend/.env` has these defaults.
- **Superuser**: `admin@example.com` / `admin123` (username: `admin`). Created during initial setup.
- **Redis**: Optional. Core CRUD/auth works without it; only WebSocket concurrent-editing features require Redis.
- **Frontend proxy**: `frontend/package.json` has `"proxy": "http://localhost:8000"` — API calls from the React dev server are proxied to the backend automatically.
- **DEBUG mode**: `backend/.env` sets `DEBUG=True`, which enables console email backend, disables SSL redirect, and sets email verification to `optional`.
- **No frontend tests**: The frontend has no test files — `npm test` exits with code 1 unless `--passWithNoTests` is passed.

### Lint / Test / Build commands

- **Backend lint**: `cd backend && source venv/bin/activate && python manage.py check`
- **Backend tests**: `cd backend && source venv/bin/activate && python manage.py test`
- **Frontend lint**: `cd frontend && npx eslint src/`
- **Frontend build**: `cd frontend && npm run build`
- **Frontend tests**: `cd frontend && CI=true npm test -- --watchAll=false --passWithNoTests`
