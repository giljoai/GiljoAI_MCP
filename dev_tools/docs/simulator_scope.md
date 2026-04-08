Dev Tool Simulator: Scope and Plan

Version: 0.1 (initial scaffold)
Owner: Dev Tools
Location: dev_tools/simulator

Purpose
- Provide a lightweight simulator UI to exercise core flows without touching the product UI code.
- Launch backend and static frontend locally, then drive API calls for Products, Projects, Tasks, Jobs, Messaging, and MCP over HTTP.
- Show a live log pane per section with success/failure of each action.

Out of Scope (v0.1)
- Visual parity with the main frontend (utility-first look is fine).
- Full E2E assertions; this tool is for manual/interactive exercising and stress.

Architecture
- Simulator Backend: FastAPI app on its own venv and port (default 7390).
  - Manages subprocesses for: API (api/run_api.py) and Frontend server (serve_frontend.py).
  - Provides proxy endpoints to the main API to avoid CORS issues and unify auth.
  - Holds an httpx client with either:
    - API Key auth (X-API-Key) supplied by user, or
    - JWT session cookie obtained via login (username/password).
  - Optional synthetic progress generator for jobs if orchestration is not available.
- Simulator Frontend: Single HTML + JS served by the simulator backend.
  - Tabs: PRODUCT, PROJECT, TASK, JOB, MESSAGING, MCP.
  - Buttons to trigger actions; a log pane per tab prints results in real time.

Key Functions Mapped to API
- Product
  - Create: POST /api/v1/products
  - List: GET /api/v1/products
  - Activate: POST /api/v1/products/{id}/activate
  - Deactivate: POST /api/v1/products/{id}/deactivate
  - Delete/Restore: DELETE /api/v1/products/{id}, POST /api/v1/products/{id}/restore
  - Vision Upload + Chunking: POST /api/v1/products/{id}/upload-vision (uses a .md or .txt file)
  - Vision Chunks: GET /api/v1/products/{id}/vision-chunks
- Project
  - Create/List/Get/Update via /api/v1/projects
  - Activate (returns 501 today per lifecycle handler; tool surfaces result)
  - Cancel/Restore: POST /api/v1/projects/{id}/cancel, /restore
  - Staging cancel: POST /api/v1/projects/{id}/cancel-staging
- Task
  - List/Create/Update/Delete/Convert: /api/v1/tasks and /api/v1/tasks/{id}/convert
- Jobs (Agent Orchestration)
  - Orchestrate: POST /api/agent-jobs/orchestrate/{project_id}
  - Workflow status: GET /api/agent-jobs/workflow/{project_id}
  - Launch: POST /api/agent-jobs/launch-project
  - Regenerate mission: POST /api/agent-jobs/regenerate-mission
  - If endpoints return 4xx/5xx, simulator can optionally simulate progress locally.
- Messaging
  - Send: POST /api/v1/messages
  - List: GET /api/v1/messages (with filters)
  - Acknowledge/Complete: POST /api/v1/messages/{id}/acknowledge, /complete
- MCP over HTTP (JSON-RPC 2.0)
  - POST /mcp with methods initialize, tools/list, tools/call

Dataset / Stress Mode
- Config file: dev_tools/simulator/data/sim_data.yaml
  - Defaults: 10 products, 10 projects per product, 10 tasks per project
  - Name templates and randomization seeds
  - Simulator provides a "Generate Dataset" action that creates entities sequentially with logs

Auth Model
- Preferred: User pastes an API key (X-API-Key) to use for all requests.
- Alternate: Login with username/password via /api/auth/login; simulator stores returned cookie and reuses it.
- Both options are supported; the current selection is visible at top of the UI.

Launcher
- Start/stop backend (api/run_api.py) on port defined in config/env (default 7272).
- Start/stop static frontend server (serve_frontend.py) on port 7274.
- Status endpoint shows PIDs and health checks for both processes.

Run/Setup
- Isolated venv in dev_tools/simulator/. No pollution of the product venv.
- Scripts:
  - setup_venv.sh / setup_venv.bat: create venv and install requirements
  - run.sh / run.bat: activate venv and run simulator (uvicorn dev_tools.simulator.simulator_app:app --port 7390)

Windows Notes
- PostgreSQL path: set per developer in devtools.local.ini (not used by simulator directly).
- Simulator calls the HTTP API; it does not connect to PostgreSQL directly.

MVP Acceptance
- Can start/stop backend and frontend from simulator.
- Can authenticate via API key or login.
- Buttons for core functions execute and produce visible logs.
- Vision upload from a local .md file succeeds and chunk count is shown.
- MCP tools/list test returns list of tools or a clear error.

Next Iterations
- Live WebSocket feed to tail API logs in the log pane.
- Persist simulator sessions and datasets between runs.
- Batch progress visualization for job workflows.

