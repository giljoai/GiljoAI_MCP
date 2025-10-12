# Architecture V3

This document explains GiljoAI MCP’s architecture for future AI coding agents and maintainers using the Golden Circle: Why, How, What.

## Why
- Orchestrate multi‑agent coding workflows with clear APIs and real‑time status.
- Provide a simple installation path and consistent local network behavior.
- Enforce secure, tenant‑aware access across API, WebSocket, and tools.

## How
- Backend: FastAPI application exposing REST and WebSocket interfaces, with explicit CORS origins and setup‑mode gating.
- Persistence: PostgreSQL via SQLAlchemy (async) and Alembic migrations.
- Auth: JWT via python‑jose, password hashing via passlib; API keys for trusted automation; localhost auto‑login for setup.
- Tenancy: Lightweight tenant isolation using `X-Tenant-Key` header, enforced across API and WebSocket subscriptions.
- Real‑time: WebSocket channel `/ws/{client_id}` managed by a `WebSocketManager` with heartbeat and per‑entity subscriptions.
- Installer: `install.py` validates prerequisites, configures database, writes credentials, and launches the simplified setup wizard.
- Frontend: Vue 3 + Vite + Vuetify UI that talks to the REST API and WebSocket; axios interceptor aligns login redirects with setup state.
- Network detection: Adapter IP detection augments CORS origins alongside localhost to support LAN access safely.

## What
### Repository Structure (high‑level)
- `api/` FastAPI app, endpoints, middleware, and WebSocket handling.
- `src/giljo_mcp/` Core modules: auth, config, DB, tenant, tools.
- `frontend/` Vue 3 dashboard (Pinia, Vuetify, socket.io‑client).
- `installer/` Installer components and configuration helpers.
- `install.py` One‑shot installer and environment validation utility.
- `startup.py` Server bootstrap, service orchestration, and health logic.
- `tests/` Unit, integration, and manual verification utilities.
- `docs/` Documentation, guides, devlogs, and this architecture reference.

### Key Runtime Services
- REST API: `/api/v1/*` app resources; `/api/auth`, `/api/users`; `/api/setup/*` for first‑run flow.
- WebSocket: `/ws/{client_id}` with authenticated connections (JWT or API key) and authorized subscriptions.
- Health: `/health` returns API, DB, and WebSocket status.

### Major Dependencies
Backend
- FastAPI, Uvicorn, Pydantic, Pydantic‑Settings
- SQLAlchemy (async), Alembic, asyncpg/psycopg2
- python‑jose, passlib[bcrypt], python‑multipart
- httpx, websockets, rich, typer, PyYAML

Frontend
- Vue 3, Vite, Vuetify, Vue Router, Pinia
- axios, socket.io‑client, date‑fns

Installer/Tooling
- dotenv, click, colorama; shell scripts for Docker/dev flows

### Setup Mode and Flow
- On first run, `SetupStateManager` toggles setup mode; DB initialization is deferred.
- Frontend axios interceptor checks `/api/setup/status` before redirecting to `/login` on 401.
- Wizard reduces steps to admin creation and completion; server listens on `127.0.0.1:7272` by default for local flow.

### Security Highlights
- Explicit CORS origins (no wildcards); LAN IPs injected when detected.
- Auth middleware after setup middleware ensures setup endpoints work unauthenticated while protecting others.
- WebSocket auth validated before accept; unauthorized connections rejected with proper close codes.

### Extensibility
- Tools accessed via `ToolAccessor` with tenant context.
- Additional API routers mount under `/api` with consistent middleware ordering.

