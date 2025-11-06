# 1000 – Dev Install and Data Isolation Strategy

Decision
- Yes: ship a dedicated dev installer that provisions the Developer Panel as an optional, isolated add-on with its own database. It only reads from the project database, never writes, to avoid cross-contamination.

Goals
- Zero impact on main product data (projects/products/tenants).
- Reproducible install/uninstall; local-only and gated.
- Simple cleanup: delete env flags and dev DB to remove all traces.

Architecture
- Dev Panel DB (writeable): Stores search indexes, diagram JSON, audit log, export artifacts.
  - Default: `sqlite:///devpanel.db` (local file, simplest).
  - Optional: PostgreSQL database `giljo_devpanel` on same cluster.
- Read-Only access to Main DB: A dedicated RO user connects to the primary DB to build inventories.
  - Option A (recommended): PostgreSQL RO role limited to SELECT on all tables.
  - Option B: Application-level read-only sessions (no commit) with defensive guards.

Provisioning Flow (dev_install)
1) Validate environment, detect main `DATABASE_URL` (or prompt/arg).
2) Create Dev Panel DB: SQLite by default; or PG if `--panel-db-url` provided.
3) (Optional) Create RO user on main DB if `--create-ro-user` is provided and admin credentials are available; grant SELECT on schemas.
4) Generate `.env.devpanel` with:
   - `ENABLE_DEVPANEL=true`
   - `ALLOW_DEVPANEL_EDIT=false` (default safe)
   - `DEVPANEL_DATABASE_URL=...`
   - `DEVPANEL_READONLY_DB_URL=...` (if RO user configured)
5) Print verification steps (start API, open `/developer`).

Security & Gating
- Panel routes mount only when `ENABLE_DEVPANEL=true` AND request is localhost.
- Config editing additionally requires `ALLOW_DEVPANEL_EDIT=true`.
- All reads use RO session; writes go only to Dev Panel DB.
- All edits/audit trail written to `logs/devpanel_audit.log`.

Uninstall
- Delete `devpanel.db` (or drop PG DB) and remove env flags.
- Confirm no dev routes mounted without `ENABLE_DEVPANEL`.

Acceptance Criteria
- Running the installer does not modify main product data.
- Disabling `ENABLE_DEVPANEL` fully removes the feature surface.
- All inventories rebuild from RO connection only.

CLI (planned)
- `python dev_tools/devpanel/scripts/devpanel_install.py --panel-db-url sqlite:///devpanel.db`
- `python dev_tools/devpanel/scripts/devpanel_install.py --panel-db-url postgresql+psycopg://user:pass@host:5432/giljo_devpanel --source-db-url postgresql+psycopg://admin:pass@host:5432/giljo_main --create-ro-user --ro-username devpanel_ro --ro-password *****`

Risks / Notes
- Creating RO user requires admin connection; fall back to app-level RO guards if not provided.
- If using PG dev DB, enforce separate credentials from main DB.
