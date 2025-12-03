# 0102a — Enhancement Work and Testing Summary

This handover captures decisions, implementation notes, test guidance, and UI ↔ DB ↔ YAML mapping for the 0102 “single‑token, token‑first download system” and Agent Template packaging for Claude Code sub‑agents. Use this as the source of truth for continuing work and for aligning the Create Agent UI with backend rendering.

## Overview
- Token‑first lifecycle for downloads: pending → ready → failed; public download path; JSON errors.
- Public path `/api/download/temp/{token}/{filename}` bypasses auth; the token/folder serves as the security boundary.
- Concurrency: multiple downloads allowed within token expiry (no single‑use burn) per 0102.
- Agent Templates: DB is canonical; export/packaging renders Claude Code‑compatible Markdown files with YAML frontmatter + body.
- “Max 8 active roles”: unlimited template creation, but UI blocks toggling more than 8 active at once; packaging respects cap to 8 distinct active roles.

## Key Behavior Decisions
- Auth bypass: Downloads are public by design; generation of tokens stays authenticated (JWT/API key). Middleware must early‑bypass `/api/download/temp` consistently.
- JSON error responses: All error paths return JSON with `detail` for diagnostics. Tests assert on status and `detail` presence.
- Concurrency semantics: concurrent downloads of the same token within expiry all succeed (200). No decrement/burn on first use.
- Directory traversal: Requests with traversal patterns (e.g., `../../../`) return 400/404; never 401.

## Data Model & Migrations
- If the DB already has base tables, Alembic may error with “relation already exists.” In that case, stamp to the correct baseline then upgrade:
  - Windows (PowerShell):
    - `$env:DATABASE_URL="postgresql://postgres:***@localhost:5432/giljo_mcp_test"`
    - `./venv/Scripts/alembic.exe stamp 631adb011a79`
    - `./venv/Scripts/alembic.exe upgrade head`
- Keep separate URLs for dev vs. test DBs to avoid cross‑contamination.

## Testing Status & Guidance
- Expectation: all download endpoint tests green once middleware bypass, JSON error shaping, and concurrency semantics are in place.
- Windows quick runs:
  - Pytest (file): `./venv/Scripts/pytest.exe -c pytest_no_coverage.ini tests/api/test_download_endpoints.py -q`
  - Pytest (verbose): `./venv/Scripts/pytest.exe -c pytest_no_coverage.ini -vv -x -s`
  - Ruff (scoped): `./venv/Scripts/ruff.exe check src/giljo_mcp/downloads src/giljo_mcp/file_staging.py api/endpoints/downloads.py --fix`
- Manual UX (recommended after tests):
  - Generate token via API (auth required), then download zip unauthenticated using the token URL.
  - Attempt directory traversal tokens; expect 400/404.
  - Verify missing file returns 500 JSON with `detail`.
  - Spawn 5 concurrent downloads for the same token; all should return 200 during validity window.

## Agent Templates: UI → DB → YAML Mapping
This aligns 1:1 with Claude Code’s “Create new agent” flow.

- Agent type (identifier)
  - UI: unique slug (lowercase with hyphens)
  - DB: `name` (unique per tenant)
  - YAML frontmatter: `name`
- System prompt
  - UI: long text (min length validation recommended, e.g., ≥20 chars)
  - DB: `template_content`
  - YAML body: markdown body following the frontmatter
  - Optional UI sections that map into body: “Behavioral Rules”, “Success Criteria” (stored as separate fields; rendered as markdown sections)
- Description
  - UI: short description (required)
  - DB: `description`
  - YAML frontmatter: `description`
- Tools selection
  - UI: All tools / subset (checkboxes for MCP servers and individual tools)
  - DB: `tools` (array or comma‑separated string)
  - YAML frontmatter: `tools: tool1, tool2` (omit the `tools` field entirely to inherit all, matching Claude Code behavior)
- Model selection
  - UI: Sonnet (default), Opus, Haiku, Inherit from parent
  - DB: `model`
  - YAML frontmatter: `model`
  - Default: use `sonnet` if blank to align with Claude Code UI default (not `inherit`)
- Color (UI only)
  - UI: color chip for visual grouping
  - DB: optional `ui_color` for UI state
  - YAML: not exported
- Active toggle
  - UI: `is_active` toggle; enforce ≤8 active roles (block toggle with warning if limit exceeded)
  - DB: `is_active`
  - Packaging: only active roles are candidates; cap to 8 distinct roles
- Optional fields
  - DB: `version` (default `1.0.0`), `tags` (list), `behavioral_rules`, `success_criteria`, `is_default` (for precedence)

## Renderer Defaults (when blank)
- `model`: `sonnet`
- `tools`: inherit (omit `tools` field in YAML)
- `description`: `Subagent for <role>` (fallback if UI leaves blank)
- `version`: `1.0.0`
- Body layout:
  - Start with `template_content`
  - If `behavioral_rules` present, render a “Behavioral Rules” section under the body
  - If `success_criteria` present, render a “Success Criteria” section

## YAML/Markdown Output (Claude Code compatible)
Stored/packaged as `exports/templates/{tenant_key}/claude_code/<name>.md` (slug‑safe filename). Example:

```
---
name: implementor
description: Subagent for implementor
model: sonnet
# tools omitted to inherit all tools
---
You are the implementor agent...

## Behavioral Rules
- Prefer incremental commits
- Add tests when feasible

## Success Criteria
- PR reviews pass
- CI is green
```

Notes:
- Omit `tools` frontmatter to inherit all; include it only when a specific subset is chosen in the UI.
- If the user selects “Inherit from parent” for model, set `model: inherit` in YAML; otherwise use selected model. If left blank, default to `sonnet`.

## Packaging Rules and Cap (8 Active Roles)
- Creation is unlimited; toggling `is_active` beyond 8 is blocked in UI.
- Packaging cap: include at most 8 distinct active roles. If more than 8 are active (e.g., due to legacy state), apply precedence:
  1) `is_default` templates first
  2) `updated_at` descending (most recent first)
  3) `name` ascending (stable fallback)
- Slash commands ZIP remains a separate artifact from agent templates.

## Materialization Strategy
- DB remains canonical. On create/update/seed, optionally materialize files to `exports/templates/{tenant_key}/claude_code/<name>.md` for operator visibility and backup. Packaging can render from DB directly to avoid stale files.

## What to Tell the “Add Agent UI” Owner
- Fields to implement
  - Required: `name` (slug), `description`, `template_content`, `is_active`
  - Recommended: `model` (Sonnet default; Opus/Haiku/Inherit), `tools` selector (All vs. granular), `behavioral_rules`, `success_criteria`
  - Optional: `tags`, `version` (default `1.0.0`), `ui_color` (UI only), `is_default`
- Validation & UX
  - Enforce unique `name` within tenant; validate slug format
  - System prompt min length (≥20 chars)
  - Unlimited creation; block `is_active` toggle beyond 8 with a clear warning (creation still allowed)
  - Show live YAML preview (frontmatter + body) and link to Claude Code docs
- Semantics
  - “All tools” → omit `tools` field in YAML
  - “Inherit model from parent” → `model: inherit`; blank → default to `sonnet`
  - Color is not exported
  - Filenames are `<name>.md` (slug), placed under tenant path during export
- Persistence
  - Save to DB first (DB is canonical)
  - Export/materialize files for operator visibility when requested or on save, depending on product decision

## Next Steps Requested for QA
- >8 Agents scenario
  - Create 10 templates; ensure UI allows creation but blocks toggling the 9th active with a warning
  - Verify packaging/export includes only 8 distinct active roles and follows precedence
- Download flows
  - Token generation requires auth; download with token works without auth
  - 5 concurrent downloads using the same valid token all return 200 within expiry
  - Directory traversal token returns 400/404 (never 401)
  - Missing file after token validation returns 500 with JSON `detail`
- End‑to‑End
  - Prefer running Pytests first, then full UX via laptop → MCP server → GUI to validate real‑world flows (settings → Agent Template Manager → export/download)

## Quick Windows Commands
- Pytests:
  - `./venv/Scripts/pytest.exe -c pytest_no_coverage.ini tests/api/test_download_endpoints.py -q`
  - `./venv/Scripts/pytest.exe -c pytest_no_coverage.ini -vv -x -s`
- Ruff (scoped to touched areas):
  - `./venv/Scripts/ruff.exe check src/giljo_mcp/downloads src/giljo_mcp/file_staging.py api/endpoints/downloads.py --fix`
- Alembic (test DB):
  - `$env:DATABASE_URL="postgresql://postgres:***@localhost:5432/giljo_mcp_test"`
  - `./venv/Scripts/alembic.exe stamp 631adb011a79`
  - `./venv/Scripts/alembic.exe upgrade head`

## References
- Claude Code sub‑agents docs (frontmatter + body structure; inherit tools by omitting `tools`; model defaults)
- Internal tests: `tests/api/test_download_endpoints.py`

---
This document is intended to prevent context loss between agents and to harmonize UI and backend expectations for commercial release quality.

---

## IMPLEMENTATION SUMMARY (Added 2025-11-05)

### What Was Built
- Token-first download system with 15min TTL
- Public download path (auth bypassed in middleware)
- Install scripts (PowerShell + Bash) with URL templating
- 8-role cap for agent template packaging
- Error handling (JSON 404/410/500 responses)

### Key Files Modified
- `api/endpoints/downloads.py` - Token generation, public downloads
- `src/giljo_mcp/file_staging.py` - ZIP packaging, 8-role cap
- `src/giljo_mcp/template_renderer.py` - Claude YAML rendering
- `api/middleware.py` - Auth bypass for /api/download/temp/*

### Installation Impact
No install.py changes for 0102a (migration handled in 0104).

### Testing Results
✅ All download endpoint tests pass. Token generation, concurrent downloads, and install scripts verified.

### Status
✅ Production ready. Testing via UI required (see 0104_USER_TESTING_GUIDE.md).

---
