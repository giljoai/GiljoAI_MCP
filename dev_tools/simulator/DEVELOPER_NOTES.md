Dev Tools Simulator — Developer Notes

Purpose
- Provide a lightweight, isolated tool to rapidly exercise core backend flows for Products, Projects, Tasks, Jobs, Messaging, and MCP.
- Avoid editing or depending on the product’s main frontend; keep changes in `dev_tools/simulator` only.

High-Level Architecture
- Simulator Backend (FastAPI): `dev_tools/simulator/simulator_app.py`
  - Exposes `/api/sim/*` endpoints that wrap the main API.
  - Serves a static single-page UI under `/` from `static/index.html`.
  - Uses `APIClient` for outbound calls to the main API (httpx, stateful headers/cookies).
  - Manages created IDs for cleanup (`CreatedRegistry`).
  - Manages subprocesses for starting/stopping the main API and static frontend (`ProcessManager`).
- Simulator Frontend (HTML + JS): `dev_tools/simulator/static/index.html`
  - Tabs for PRODUCT, PROJECT, TASK, JOBS, MESSAGING, MCP.
  - Minimal fetch()-based calls to simulator endpoints, logs results per tab.
- Isolated venv and launch scripts:
  - Windows: `dev_tools/simulator/run.bat`
  - macOS/Linux: `dev_tools/simulator/run.sh`
  - Both set PYTHONPATH to include repo root so `dev_tools` imports work.

Key Modules
- `simulator_app.py`
  - Static UI mount: `/` and `/static`.
  - Auth endpoints: `/api/auth/api_key` and `/api/auth/login` (pass-through to main API via `APIClient`).
  - Process control:
    - `POST /api/process/start_api` → runs `api/run_api.py` using the repo’s `.venv` python if present.
    - `POST /api/process/stop_api`
    - `POST /api/process/start_frontend` → runs `serve_frontend.py`.
    - `POST /api/process/stop_frontend`
    - `GET  /api/process/status`
  - Sim actions (selected):
    - Products: `/api/sim/product/*` (create, activate, deactivate, delete, upload_vision)
    - Projects: `/api/sim/project/*` (create, cancel, restore)
    - Tasks: `/api/sim/task/*` (create, delete, convert)
    - Jobs: `/api/sim/jobs/*` (orchestrate, workflow)
    - Messages: `/api/sim/messages/*` (send, ack, complete)
    - MCP: `/api/sim/mcp/*` (initialize, tools_list, tools_call)
    - Dataset: `/api/sim/dataset/generate`
    - Cleanup:
      - `/api/sim/cleanup/created` (uses registry)
      - `/api/sim/cleanup/purge_sim` (best-effort by name prefix)
- `api_client.py`
  - Async httpx client, maintains headers/cookies.
  - Auth modes: `X-API-Key` header or JWT login.
  - Convenience methods for all simulated flows; returns consistent `{success, status, data}` shape.
- `process_manager.py`
  - Spawns API and frontend subprocesses.
  - Picks `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` from repo root when available; fallback to current interpreter.
- `created_registry.py`
  - Persists created IDs to `dev_tools/simulator/state/created.json` for cleanup.
- `static/index.html`
  - Minimal UI with tabs and buttons; logs responses as JSON into textareas.
- `requirements.txt`
  - FastAPI, Uvicorn, httpx, Jinja2, python-multipart.

Data & Stress
- `data/sim_data.yaml`: default dataset parameters (10 × 10 × 10) used by dataset generator.

Runtime Behavior
- Target base URL defaults to `http://localhost:7272` (main API).
- Frontend static server binds to 7274 (per `serve_frontend.py`).
- Simulator binds to 7390 by default (run scripts).

Cleanup Semantics
- `cleanup/created`: deletes/cancels items tracked in registry (tasks deleted, products soft-deleted, projects cancelled). Messages/jobs cleared locally (no delete endpoints).
- `purge_sim`: scans lists for names starting with `SIM_` and attempts delete/cancel operations.

Limitations / Known Gaps
- No WebSocket tail of API logs in the UI.
- No message/job delete endpoints in the main API (best-effort cleanup only).
- Frontend port override is not honored by `serve_frontend.py` (fixed to 7274).

Extending
- Add new wrapper endpoints in `simulator_app.py` and call them from the UI.
- Expand `APIClient` with new convenience methods as API grows.
- Add WebSocket client to surface live events/health.

