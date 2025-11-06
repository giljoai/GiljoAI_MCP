# Developer Panel Setup Session Log

Date: $(date +"%Y-%m-%d" 2>/dev/null || echo "2025-11-06")

Summary
- Migrated all Developer Panel assets out of the production tree into `dev_tools/devpanel/`.
- Recreated the multi-phase scope (1000–1010), user manual, and install/index scripts in the new location.
- Added a standalone FastAPI backend (`backend/app.py`) with localhost-only gating.
- Added `run_backend.py` convenience launcher and a static HTML prototype under `frontend/`.
- Created quick-start scripts (`scripts/start_devpanel.bat` / `start_devpanel.sh`) that rebuild inventories, start the backend, and open the UI.
- Updated docs to describe install, toggle, run, and cleanup steps.

Quick Use
1. Activate dev venv (`pip install -e .[dev]`).
2. Run the platform script:
   - Windows: `dev_tools\devpanel\scripts\start_devpanel.bat`
   - Linux/macOS: `bash dev_tools/devpanel/scripts/start_devpanel.sh`
3. Prototype UI opens in browser; backend listens on `http://127.0.0.1:8283`.

Notes
- Inventories are written to `temp/devpanel/index/`; regenerate via `devpanel_index.py` when code/docs change.
- Backend requires `ENABLE_DEVPANEL=true` (set automatically by the launch scripts).
- Everything remains isolated from the main product—no production files modified.
