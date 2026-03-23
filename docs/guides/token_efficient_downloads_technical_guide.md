# Token-Efficient Downloads - Technical Guide

**Version:** 2.0  
**Last Updated:** 2026-01-03  
**Audience:** Developers / System Architects

---

## Purpose

Avoid large in-chat file payloads (agent templates, slash commands) by serving ZIPs over HTTP and returning short, token-first install instructions.

Key principles:
- Slash commands ZIP is **public** (no secrets)
- Agent templates ZIP is **token-staged** (one-time URL) via MCP tool
- All tenant data remains isolated (tenant_key = user-level tenancy)

---

## Public HTTP Endpoints

### 1) Slash commands ZIP (public)

- `GET /api/download/slash-commands.zip`
- Contains:
  - `gil_get_agents.md`
  - `gil_activate.md`
  - `gil_launch.md`
  - `gil_handover.md`
  - `install.sh`, `install.ps1`

Implementation: `api/endpoints/downloads.py`

### 2) Agent templates ZIP (optional-auth)

- `GET /api/download/agent-templates.zip?active_only=true|false`
- Behavior:
  - Authenticated (JWT cookie / Bearer / X-API-Key): returns tenant templates
  - Unauthenticated: returns system defaults (tenant_key IS NULL) if present
- Package cap: max 8 templates per ZIP (see `select_templates_for_packaging`)

Implementation: `api/endpoints/downloads.py`

### 3) Install scripts (public)

- `GET /api/download/install-script.sh?script_type=slash-commands|agent-templates`
- `GET /api/download/install-script.ps1?script_type=slash-commands|agent-templates`

Scripts live under `installer/templates/` and use `{{SERVER_URL}}` substitution.

---

## Token-Staged Downloads (One-Time URLs)

### Why tokens

Agents should not paste large template content into chat. Instead:
- MCP tool creates a one-time token
- Server stages ZIP to a temp directory
- Tool returns a short download URL

### Core pieces

- DB token records: `src/giljo_mcp/models` (`DownloadToken`)
- Token manager: `src/giljo_mcp/downloads/token_manager.py`
- File staging: `src/giljo_mcp/file_staging.py`
- Temp download endpoint: `api/endpoints/downloads.py` (`/api/download/temp/{token}/{filename}`)

---

## MCP Tools (User-Facing Setup)

### `setup_slash_commands`

- Purpose: return a one-shot download URL + a Bash install command to install slash commands into `~/.claude/commands/`.
- Implementation: `src/giljo_mcp/tools/tool_accessor.py` (`ToolAccessor.setup_slash_commands`)

### `get_agent_download_url`

- Purpose: stage active agent templates and return a one-shot ZIP URL.
- Used by the `/gil_get_agents` slash command.
- Implementation: `src/giljo_mcp/tools/tool_accessor.py` (`ToolAccessor.get_agent_download_url`)

---

## Notes on Schema / Exposure

The public MCP tool surface is defined in `api/endpoints/mcp_http.py` (`tool_map`).

Legacy download-flow tools were removed (Jan 2026):
- `gil_fetch`
- `gil_import_productagents`
- `gil_import_personalagents`

---

## Testing Pointers

- Public slash commands ZIP content: `tests/test_downloads.py`
- End-to-end downloads flow (ZIP integrity, auth, multi-tenant): `tests/integration/test_downloads_integration.py`
- MCP tools/list consistency: `tests/integration/test_mcp_http_tool_catalog.py`

