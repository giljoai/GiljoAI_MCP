# Installation Flow

This document outlines the end‑to‑end installation sequence, including an executive brief and detailed steps.

## Executive Brief
- Verify Python, pip, npm, and PostgreSQL availability.
- Generate or load database credentials; verify connectivity.
- Install backend dependencies and **create database tables** (NO Alembic).
- Start backend (Uvicorn) and frontend (Vite/served UI).
- Detect network adapter IP; set safe CORS origins with localhost and adapter IP.
- Launch setup wizard at `http://127.0.0.1:7274/setup`.
- Create admin user; finalize setup state.
- Redirect to `/login` after setup completes; start using dashboard.

## Detailed Flow
1) Environment Checks
   - `install.py` checks Python version (>=3.10), `pip`, and optionally `npm` for frontend.
   - Verifies PostgreSQL presence: PATH probing, Windows common paths, and fallback to runtime connectivity checks.

2) Database Configuration
   - Loads `.env` and environment variables; constructs `DATABASE_URL` if missing.
   - Writes installer credentials under `installer/credentials/` for audit and support.
   - Initializes an async SQLAlchemy engine
   - **Creates tables using DatabaseManager.create_tables_async()** (Base.metadata.create_all())
   - **NOT using Alembic migrations** - project uses direct table creation

3) Dependency Installation
   - Installs Python requirements from `requirements.txt`.
   - Optional integrations can be installed from `optional-requirements.txt`.

4) Service Startup
   - Backend: Uvicorn launches the FastAPI app; setup mode enabled until wizard completes.
   - Frontend: Dev mode via Vite on `5173` or served UI on `7274`.
   - Health endpoint `/health` reports API, DB, and WebSocket states.

5) Network Configuration
   - Adapter IP detection augments CORS with `http://<adapter_ip>:7274` and dev `:5173`.
   - Default CORS origins always include `127.0.0.1:7274` and `localhost:7274`.

6) Setup Wizard
   - Simplified steps: Admin creation → Complete.
   - Axios interceptor prevents redirect to `/login` while setup is incomplete by checking `/api/setup/status` on 401.
   - On completion, setup state persisted via `SetupStateManager` and setup mode disabled.

7) Post‑Setup
   - Redirects to `/login`; JWT authentication in effect for network clients.
   - Localhost auto‑login available for development convenience.
   - API keys can be generated/loaded for automation; WebSocket connections authenticate via `token` or `api_key` query params.

## Troubleshooting
- If DB connectivity fails, verify `DATABASE_URL` or individual DB env vars; check Postgres service status.
- If frontend fails to connect, inspect CORS origins in `config.yaml` and console logs for adapter IP detection notes.
- Use `/health` to quickly identify API/DB/WebSocket readiness.

