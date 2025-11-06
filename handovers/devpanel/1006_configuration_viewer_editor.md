# 1006 – Configuration Viewer and Controlled Editor

Objective
- Expose non‑sensitive configuration for viewing and (optionally) editing specific whitelisted fields through the Developer Panel.

In Scope
- Read‑only view of `.env` (redacted) and `config.yaml` (safe keys only).
- Editable fields: whitelisted paths (e.g., `installation.version`, feature flags) with audit logging.
- Validation and change preview before commit.

Out of Scope
- Secrets management or dynamic DB URL changes.
- Tenant‑wide destructive actions.

Deliverables
- `GET /api/v1/developer/config` (redacted view).
- `POST /api/v1/developer/config/preview` → diff, validations.
- `POST /api/v1/developer/config/apply` → writes to `config.yaml` with backup, audit log entry.
- Redaction rules and whitelist documented in code and `docs/`.

Acceptance Criteria
- Redaction covers secrets, salts, tokens, URLs with creds.
- All edits require explicit enable flag (`ALLOW_DEVPANEL_EDIT=true`).
- Rollback file created on every write with timestamp.

Primary Data Sources
- `.env.example`, `config.yaml.example`, `src/giljo_mcp/config_manager.py`

Implementation Notes
- Use YAML round‑trip (ruamel.yaml) to preserve comments where possible.
- Record audit entries in a local file under `logs/devpanel_audit.log`.

Estimate / Owner
- 1–1.5 days; Backend.

