# Developer Panel – Quick User Manual

Purpose
- A localhost‑only, dev‑only panel at `/developer` to explore architecture, APIs, MCP tools, agents/templates, DB schema, dependency graphs, and configuration surfaces. It is optional, isolated, and removable.

Prerequisites
- Use your project venv and dev deps.
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -e .[dev]` (or `pip install -r requirements.txt -r dev-requirements.txt`)

Install (one‑time)
- Run the installer to create a separate Dev Panel DB and env file:
  - `python scripts/devpanel_install.py`
  - This writes `.env.devpanel` with safe defaults:
    - `ENABLE_DEVPANEL=true` (gates panel routes)
    - `ALLOW_DEVPANEL_EDIT=false` (keeps edits disabled)
    - `DEVPANEL_DATABASE_URL=sqlite:///devpanel.db` (isolated DB file)
- Optional: Create a read‑only DB user on Postgres (safer for inventories)
  - `python scripts/devpanel_install.py --source-db-url postgresql+psycopg://admin:pass@host:5432/giljo_mcp --create-ro-user --ro-username devpanel_ro --ro-password *****`
  - Follow the printed SQL; then set `DEVPANEL_READONLY_DB_URL` accordingly.

Enable / Disable (toggle)
- Enable for current shell (recommended):
  - `source .env.devpanel`
- Or set in shell (one‑off):
  - Bash/zsh: `export ENABLE_DEVPANEL=true`
  - PowerShell: `$env:ENABLE_DEVPANEL='true'`
- Disable: unset or open a fresh shell without sourcing `.env.devpanel`.
- Do NOT commit `.env.devpanel` or enable flags to VCS.

Generate Indexes (Phase 1001)
- Build inventories without running the API server:
  - `python scripts/devpanel_index.py --out temp/devpanel/index`
- Outputs: `temp/devpanel/index/*.json` (API catalog, DB schema, MCP tools, dependencies, flows, search seed).

Run the API / Access Panel
- Start API: `python api/run_api.py --reload --port 7272`
- Open: `http://127.0.0.1:7272/developer`
- Notes:
  - Panel routes only mount when `ENABLE_DEVPANEL=true` and requests come from localhost.
  - Config edits remain disabled unless you explicitly set `ALLOW_DEVPANEL_EDIT=true` (not recommended).

Uninstall / Clean Up
- Remove the env file and DB file:
  - `rm .env.devpanel devpanel.db` (or drop the PG dev DB if used)
- Restart the API; `/developer` should return 404 or not exist in route list.

Troubleshooting
- Indexer shows `No module named 'dotenv'` or `No module named 'sqlalchemy'`:
  - Activate venv and install dev deps.
- `/developer` not visible:
  - Confirm `ENABLE_DEVPANEL=true` is exported in the running process.
  - Access via localhost (127.0.0.1) only.
- Safety:
  - Keep `ALLOW_DEVPANEL_EDIT=false` unless you need whitelisted edits.
  - The Dev Panel uses its own DB; it reads from the main DB via RO access (recommended) or read‑only sessions.

File Map (for reference)
- `scripts/devpanel_install.py`:1 – optional installer (creates `.env.devpanel`).
- `scripts/devpanel_index.py`:1 – builds JSON inventories (no server required).
- `handovers/devpanel/1000_dev_install_and_isolation.md`:1 – isolation strategy.
- `handovers/devpanel/README.md`:1 – scope pack overview.

Notes
- The panel is strictly dev‑only and will be removed/disabled for releases. It does not block normal product development when disabled.
