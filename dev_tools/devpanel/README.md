# Developer Panel – Standalone Toolkit

This directory holds the Developer Panel, an optional toolkit that runs **outside** the main GiljoAI MCP product. It reads the main repo and generates inventories (API catalog, DB schema, dependency graph, etc.) without modifying application code.

Contents
- `docs/` – operator manual and references for installing/toggling the panel.
- `scripts/` – helper scripts (indexing, optional install) that read the main repo and write artifacts into `temp/devpanel/` without modifying application code.
- `backend/` – standalone FastAPI service that serves inventories from `temp/devpanel/index/`.
- `run_backend.py` – convenience launcher for the standalone backend (uvicorn reload).
- `frontend/` – static HTML prototype that consumes the backend (open in a browser via `file://` or a simple static server).
- `scripts/start_devpanel.(bat|sh)` – one-click helpers for Windows/Linux to rebuild inventories, launch the backend, and open the prototype UI.

Usage Notes
- Keep this folder on a dev-only branch or local workspace. The main product remains untouched.
- Scripts here import project modules directly; run them from the repo root so `src/` and `api/` stay importable.
- The quick-start scripts create/use an isolated virtual environment under `dev_tools/devpanel/.venv`; no need to touch your main project venv.
- Start backend manually (if needed): `python dev_tools/devpanel/run_backend.py` (listens on `http://127.0.0.1:8283`).
- Generate inventories before hitting endpoints: `python dev_tools/devpanel/scripts/devpanel_index.py --out temp/devpanel/index`.
- Prototype UI: open `dev_tools/devpanel/frontend/index.html` in your browser (uses fetch against `http://127.0.0.1:8283`).
- Build your own UI (Vue/Vite, static site, etc.) under this folder and point it at the backend.
- Quick start:
  - Windows: `dev_tools\devpanel\scripts\start_devpanel.bat`
  - Linux/macOS: `bash dev_tools/devpanel/scripts/start_devpanel.sh`
