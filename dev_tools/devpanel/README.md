# Developer Panel – Scope of Work (Standalone Pack)

This directory holds the complete Developer Panel initiative, scoped to run **outside** the main GiljoAI MCP product. Use these artifacts to plan and build the panel as an optional, experimental toolkit without touching production services.

Contents
- `scope/` – numbered SoW documents (1000–1010) covering discovery, backend services, frontend blueprint, diagrams, config utilities, and security/QA.
- `docs/` – operator manual and references for installing/toggling the panel when you choose to run it locally.
- `scripts/` – helper scripts (indexing, optional install) that read the main repo and write artifacts into `temp/devpanel/` without modifying application code.
- `backend/` – standalone FastAPI service that serves inventories from `temp/devpanel/index/`.
- `run_backend.py` – convenience launcher for the standalone backend (uvicorn reload).
- `frontend/` – static HTML prototype that consumes the backend (open in a browser via `file://` or a simple static server).
- `frontend/flows.html` – dedicated flow-diagram page (Cytoscape) with deep links from the main panel.
- `frontend/flow-editor/` – React + Vite micro-app for editing flows with React Flow (build via `npm install && npm run build`).
- `scripts/start_devpanel.(bat|sh)` – one-click helpers for Windows/Linux to rebuild inventories, launch the backend, and open the prototype UI.

Usage Notes
- Keep this folder on a dev-only branch or local workspace. The main product remains untouched.
- Scripts here import project modules directly; run them from the repo root so `src/` and `api/` stay importable.
- The quick-start scripts create/use an isolated virtual environment under `dev_tools/devpanel/.venv`; no need to touch your main project venv.
- Start backend manually (if needed): `python dev_tools/devpanel/run_backend.py` (listens on `http://127.0.0.1:8283`).
- Generate inventories before hitting endpoints: `python dev_tools/devpanel/scripts/devpanel_index.py --out temp/devpanel/index`.
- Prototype UI: open `dev_tools/devpanel/frontend/index.html` in your browser (uses fetch against `http://127.0.0.1:8283`).
- Build your own UI (Vue/Vite, static site, etc.) under this folder and point it at the backend.
- Flow Editor:
  - JSON data lives under `dev_tools/devpanel/flows/` (auto-created by `scripts/build_flow_data.py`).
  - Start the backend with `ENABLE_DEVPANEL=true` and `ALLOW_DEVPANEL_EDIT=true` for autosave.
  - Install/build once: `cd dev_tools/devpanel/frontend/flow-editor && npm install && npm run build`.
  - Launch from the DevPanel link or open `dev_tools/devpanel/frontend/flow-editor/dist/index.html`.
- Quick start:
  - Windows: `dev_tools\devpanel\scripts\start_devpanel.bat`
  - Linux/macOS: `bash dev_tools/devpanel/scripts/start_devpanel.sh`

See `scope/1001_discovery_and_audit.md` to start with data inventories and work forward.
