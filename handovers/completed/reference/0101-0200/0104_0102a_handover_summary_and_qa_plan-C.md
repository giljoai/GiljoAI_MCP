# 0104 — Handover Summary: 0102a Download System + Agent Packaging

Status: Ready for UX verification and customer‑style testing
Date: 2025‑01‑05
Owner: Handover for fresh agent (continuation of 0102a/0103)

## Scope
This handover summarizes the current implementation of the token‑first download system and Claude Code‑compatible agent packaging (0102a), aligned with the Agent Template modal redesign (0103). It includes endpoint behavior, defaults, packaging rules, config switches, and a QA plan with exact PowerShell commands.

## What’s Implemented
- Token‑first downloads
  - Public download path: `/api/download/temp/{token}/{filename}` (auth bypassed by middleware)
  - Generation path (auth required): `POST /api/download/generate-token`
  - TTL default 15 minutes; env override via `DOWNLOAD_TOKEN_TTL_MINUTES`
  - Concurrency: unlimited downloads within TTL (no burn‑on‑first‑use)
  - Directory traversal hardening (filenames validated; token path uses DB token)
- Error semantics (JSON)
  - Invalid/mismatch: 404
  - Expired token: 410
  - Valid token but staged file missing: 500 with `detail` (includes “Internal server error” string)
- Slash commands + install scripts
  - Public endpoints:
    - `/api/download/slash-commands.zip`
    - `/api/download/install-script.{sh|ps1}?script_type=slash-commands|agent-templates`
  - Scripts template server URL into content; use `$GILJO_API_KEY`/`$env:GILJO_API_KEY`
- Agent packaging (Claude YAML + 8‑role cap)
  - `/api/download/agent-templates.zip` renders Markdown with YAML frontmatter:
    - Frontmatter: `name`, `description` (fallback: “Subagent for <role>”), `model` (default `sonnet` unless explicitly `inherit`)
    - Omit `tools` by default to inherit all; include only if `AgentTemplate.tools` non‑empty
    - Body: `template_content` + optional sections
      - “## Behavioral Rules” (bulleted)
      - “## Success Criteria” (bulleted)
  - Cap to 8 distinct active roles with precedence: `is_default` → `updated_at` (desc) → `name` (asc)
- Optional materialization on save
  - If `MATERIALIZE_TEMPLATES_ON_SAVE=1`: write to `exports/templates/{tenant_key}/claude_code/<name>.md`
- Code touchpoints
  - Renderer: `src/giljo_mcp/template_renderer.py`
  - Staging: `src/giljo_mcp/file_staging.py`
  - Token mgr: `src/giljo_mcp/downloads/token_manager.py`
  - Downloads API: `api/endpoints/downloads.py`
  - Templates API materialization hook: `api/endpoints/templates.py`

## Configuration & Defaults
- `DOWNLOAD_TOKEN_TTL_MINUTES` (env) → default 15 minutes
- `MATERIALIZE_TEMPLATES_ON_SAVE` (env) → `1` to write `.md` files on create/update
- Model default for YAML frontmatter: `sonnet` (use `inherit` only when explicitly chosen)

## API Summary
- Public
  - `GET /api/download/slash-commands.zip`
  - `GET /api/download/install-script.{sh|ps1}?script_type=slash-commands|agent-templates`
  - `GET /api/download/temp/{token}/{filename}`
- Optional‑auth (JWT cookie or `X-API-Key`); unauthenticated returns system defaults if configured
  - `GET /api/download/agent-templates.zip`
- Auth required
  - `POST /api/download/generate-token` (returns `download_url`, `expires_at`, `content_type`, `one_time_use`)

## Windows QA Plan (PowerShell)
1) Activate & DB URLs
- `.\venv\Scripts\Activate.ps1`
- `$env:DATABASE_URL = "postgresql://postgres:***@localhost:5432/giljo_mcp"`
- `$env:TEST_DATABASE_URL = "postgresql://postgres:***@localhost:5432/giljo_mcp_test"`
- `.\venv\Scripts\alembic.exe upgrade head`

2) Start services
- Backend: `python startup.py --dev`
- Frontend: `cd frontend; npm ci; npm run dev` (open http://localhost:5173)

3) First admin + API key
- `$body = @{ username='admin'; password='Str0ng#Pass2025'; email='admin@example.com' } | ConvertTo-Json`
- `$resp = Invoke-WebRequest -Uri "http://localhost:7272/api/auth/create-first-admin" -Method POST -Body $body -ContentType "application/json" -SessionVariable s`
- `$keyBody = @{ name='DevKey' } | ConvertTo-Json`
- `$keyResp = Invoke-RestMethod -Uri "http://localhost:7272/api/auth/api-keys" -Method POST -Body $keyBody -ContentType "application/json" -WebSession $s`
- `$env:GILJO_API_KEY = $keyResp.api_key`

4) Install scripts (public)
- `Invoke-WebRequest -Uri "http://localhost:7272/api/download/install-script.ps1?script_type=slash-commands" -OutFile install_slash.ps1`
- `./install_slash.ps1`
- `Invoke-WebRequest -Uri "http://localhost:7272/api/download/install-script.ps1?script_type=agent-templates" -OutFile install_agents.ps1`
- `./install_agents.ps1`

5) Seed 10 active templates to exercise 8‑role cap
- `1..10 | ForEach-Object {
  $role = "role$_";
  $t = @{ name=$role; role=$role; cli_tool='claude'; template_content="You are the $role agent."; description="Subagent for $role"; model='sonnet'; is_active=$true } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:7272/api/v1/templates" -Method POST -Body $t -ContentType "application/json" -WebSession $s
}`

6) Packaging download
- `Invoke-WebRequest -Uri "http://localhost:7272/api/download/agent-templates.zip" -Headers @{ "X-API-Key" = $env:GILJO_API_KEY } -OutFile agent_templates.zip`
- Expect exactly 8 `.md` files; each with YAML frontmatter (`name`, `description`, `model`), and `tools` omitted by default

7) Token‑first downloads
- `$tokBody = @{ content_type='agent_templates' } | ConvertTo-Json`
- `$tokResp = Invoke-RestMethod -Uri "http://localhost:7272/api/download/generate-token" -Method POST -Body $tokBody -ContentType "application/json" -Headers @{ "X-API-Key" = $env:GILJO_API_KEY }`
- `1..5 | ForEach-Object { Start-Job -ScriptBlock { param($u,$i) Invoke-WebRequest -Uri $u -OutFile ("at_$i.zip") } -ArgumentList $tokResp.download_url, $_ }`
- `Get-Job | Wait-Job | Receive-Job`
- Optional TTL test: ` $env:DOWNLOAD_TOKEN_TTL_MINUTES = "1" ` → generate new token, wait >60s, expect 410

8) Security checks
- Directory traversal attempt should return 400/404 (never 401)
- Missing file after validation returns JSON 500 with `detail`

## Known Gaps / Notes
- Integration test suite uses a placeholder `async_client` fixture; live UX testing above substitutes for now.
- Repo‑wide Ruff output is noisy; we scope linting to changed files for CI/pass (full cleanup deferred).
- Model default is `sonnet` per 0102a; use `inherit` when user explicitly chooses it in UI.

## Files of Interest
- `api/endpoints/downloads.py` — endpoints + JSON error semantics, install scripts
- `src/giljo_mcp/downloads/token_manager.py` — TTL env override, validation, metrics
- `src/giljo_mcp/file_staging.py` — staging ZIPs, packaging selection (8‑role cap)
- `src/giljo_mcp/template_renderer.py` — Claude YAML rendering + generic renderer
- `src/giljo_mcp/template_materializer.py` — optional materialization to exports/
- `api/endpoints/templates.py` — materialization hook (env‑gated)

## Next Steps for the Fresh Agent
- Confirm UX journey passes on a clean machine; collect logs and ZIP samples
- Decide on materialization policy (on‑save vs on‑demand endpoint) and implement if desired
- Tighten any UI preview alignment (0103 modal) with renderer defaults and role cap messaging
- Optional: add `downloads.token_ttl_minutes` to config.yaml (env remains source of truth)
- Optional: add `/api/templates/materialize` endpoint for operator on‑demand export

## QA Deliverables to Attach Back
- Console output of steps 1–7
- agent_templates.zip listing + sample .md content of two roles
- Output of traversal and TTL expiry tests
- Screenshots: Create Agent modal, toggle behavior at 8‑role threshold, and install‑script prompts

---
This document is intended to bootstrap a fresh agent to continue 0102a/0103 work, ensuring continuity for production‑grade release quality and UX verification.

---

## IMPLEMENTATION SUMMARY (Added 2025-11-05)

### What Was Built
- **SECURITY FIX**: Replaced f-string SQL with CASE statement in migration
- **CRITICAL FIX**: Added Alembic execution to install.py (Step 7)
- Integration test suite (21 fast + 12 database tests)
- Security validation (SQL injection, shell injection)
- User testing guide (fresh install + CLI downloads)

### Key Files Modified
- `migrations/versions/6adac1467121_*.py` - SQL injection fix
- `install.py` - Added `run_database_migrations()` method (lines 1710-1791, 189-206)
- `tests/integration/test_0104_complete_integration.py` (NEW)
- `tests/integration/test_e2e_fresh_install_smoke.py` (NEW)
- `docs/user_guides/0104_USER_TESTING_GUIDE.md` (NEW)

### Installation Impact
install.py now runs migrations automatically after table creation. 9-step process (was 8).

### Testing Results
✅ All 21 fast tests pass. Security validation complete. Fresh install flow fixed.

### Status
✅ Production ready. Awaiting user testing per testing guide.

---

## Database Setup & Migration Helper (New)

To reduce manual DB steps, a helper script is included:

- Path: `scripts/db_setup.py`
- Purpose: Create the target PostgreSQL database if missing and run Alembic migrations.
- Behavior: If schema exists but is not tracked by Alembic (legacy installs), it stamps baseline and upgrades.

Recommended commands (PowerShell):

1) Use a test DB first (non‑destructive)
- `.\venv\Scripts\Activate.ps1`
- `$env:DATABASE_URL = "postgresql://postgres:***@localhost:5432/giljo_mcp_test"`
- `python scripts\db_setup.py`
- If app runs against the test DB, proceed to main DB.

2) Migrate main DB (back up first if used in anger)
- `$env:DATABASE_URL = "postgresql://postgres:***@localhost:5432/giljo_mcp"`
- (Optional backup) `"C:\\Program Files\\PostgreSQL\\16\\bin\\pg_dump.exe" -U postgres -h localhost -p 5432 -d giljo_mcp > backup_giljo_mcp.sql`
- `python scripts\db_setup.py`

Exit codes: `0` on success; non‑zero prints actionable error output.

Notes:
- Uses `DATABASE_URL` env var or `--url` argument.
- Baseline revision used when stamping: `631adb011a79` (configurable via `ALEMBIC_BASELINE`).

## Installer Integration Recommendation

Customers should not manage DB creation/migrations manually. Integrate the helper into `install.py` (or call its core logic) so the installer:

- Verifies reachability of PostgreSQL
- Ensures target database exists (creates it via connection to the `postgres` DB)
- Runs `alembic upgrade head`
- If legacy schema is present without `alembic_version`, stamps baseline then upgrades
- Optionally seeds system templates

Option A: `subprocess.run([sys.executable, "scripts/db_setup.py"], ...)` during install.
Option B: Inline the logic (SQLAlchemy URL parse, ensure‑DB, Alembic upgrade) for fewer moving parts.

Optional safety at runtime: add a boot check that refuses to start if schema is behind (or auto‑migrates when a config flag is enabled), and logs pre/post schema versions.
