# Developer Panel – Quick User Manual (Standalone)

Purpose
- A localhost-only, dev-only toolkit that lives entirely under `dev_tools/devpanel`. It inspects the main repo (architecture, APIs, MCP tools, agent templates, DB schema, dependencies) without touching production services.

Prerequisites
- No changes needed to your main project venv. The quick-start scripts will create an isolated environment under `dev_tools/devpanel/.venv` the first time they run.

Install (one-time)
- Optional: run the installer in `dev_tools/devpanel/scripts/` if you want a dedicated `.env.devpanel` file:
  - `python dev_tools/devpanel/scripts/devpanel_install.py`
  - This writes `.env.devpanel` with safe defaults:
    - `ENABLE_DEVPANEL=true`
    - `ALLOW_DEVPANEL_EDIT=false`
    - `DEVPANEL_DATABASE_URL=sqlite:///devpanel.db`
- Optional: create a read-only DB user on Postgres for inventories.
  - `python dev_tools/devpanel/scripts/devpanel_install.py --source-db-url postgresql+psycopg://admin:pass@host:5432/giljo_mcp --create-ro-user --ro-username devpanel_ro --ro-password *****`
  - Run the printed SQL manually, then set `DEVPANEL_READONLY_DB_URL`.

Enable / Disable (toggle)
- Enable for current shell: `source .env.devpanel`
- One-off export:
  - Bash/zsh: `export ENABLE_DEVPANEL=true`
  - PowerShell: `$env:ENABLE_DEVPANEL='true'`
- Disable: start a fresh shell without sourcing `.env.devpanel` (or `unset ENABLE_DEVPANEL`).
- Never commit `.env.devpanel` or the flags.

Generate Indexes (Phase 1001)
- Build inventories without running the API server:
  - `python dev_tools/devpanel/scripts/devpanel_index.py --out temp/devpanel/index`
- Outputs: `temp/devpanel/index/*.json` (API catalog, DB schema, MCP tools, dependency graph, flows, search seed, tech stack).

Run / Inspect
- Quick start helpers (auto-manage isolated venv):
  - Windows: `dev_tools\devpanel\scripts\start_devpanel.bat`
  - Linux/macOS: `bash dev_tools/devpanel/scripts/start_devpanel.sh`
- Manual: `python dev_tools/devpanel/run_backend.py` (defaults to `http://127.0.0.1:8283`).
- Endpoints require `ENABLE_DEVPANEL=true` in the environment (auto-set by the launcher) and only accept localhost requests.
- Quick prototype: open `dev_tools/devpanel/frontend/index.html` in a browser after starting the backend.
- You can build your own frontend (e.g., Vite app) under `dev_tools/devpanel` that consumes these endpoints, or simply inspect the JSON inventories.
Uninstall / Clean Up
- Remove the env file and dev DB:
  - `rm .env.devpanel devpanel.db`
- Remove any optional RO DB user if created.

Troubleshooting
- Missing modules (`No module named 'dotenv'`, `No module named 'sqlalchemy'`): activate the venv and install dev dependencies.
- Inventories empty: rerun the indexer after syncing code/docs.
- Safety: keep `ALLOW_DEVPANEL_EDIT=false` unless you explicitly whitelist configuration edits inside dev tools.

File Map (for reference)
- `dev_tools/devpanel/scripts/devpanel_install.py`
- `dev_tools/devpanel/scripts/devpanel_index.py`
- `dev_tools/devpanel/README.md`

Notes
- This toolkit is experimental. Keep it off release branches and delete the env file when not in use.
