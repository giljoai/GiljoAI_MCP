# Handover 0834: Dynamic Protocol Resolution (HTTP/HTTPS)

**Date:** 2026-03-22
**From Agent:** Claude Code Session
**To Agent:** Next Session
**Priority:** High
**Estimated Complexity:** 2-3 Hours
**Status:** Complete
**Edition Scope:** CE

## Task Summary

When `features.ssl_enabled` is toggled to `true` in admin settings, all URL-generating code paths must switch from `http://` to `https://` and `ws://` to `wss://`. Currently ~25 hardcoded `http://` references across 14 files produce broken URLs when HTTPS is enabled — MCP config prompts, download URLs, installer scripts, and dashboard displays all serve `http://` URLs that fail against an HTTPS-only Uvicorn server (connection refused, no redirect).

## Context and Background

- Handover 0832 implemented the SSL/HTTPS admin UI toggle (`features.ssl_enabled` in config.yaml)
- When Uvicorn starts with SSL, it only listens HTTPS — no HTTP listener, no redirect
- MCP tools (Claude Code, Codex CLI, Gemini CLI) all support HTTPS URLs with `--transport http`
- The backend config endpoint (`/api/v1/config/frontend`) already serves `api.protocol` dynamically
- `api/endpoints/ai_tools.py:207` already has the correct pattern: `protocol = "https" if getattr(config.features, "ssl_enabled", False) else "http"`
- Database is clean — no persisted URLs with hardcoded protocol schemes

## Research Findings

- All three CLI tools (Claude Code, Codex, Gemini) support HTTPS MCP URLs
- No database columns store local server URLs — protocol toggle is safe from a data perspective
- MCP protocol responses (`initialize`, `tools/list`) contain no advertised URLs
- No HTTP→HTTPS redirect exists (out of scope for this handover)

## Implementation Plan

### Phase 1 — P0 Fixes (Critical: user-facing MCP config prompts)

1. `frontend/src/components/AiToolConfigWizard.vue:228` — `buildServerUrl()` uses `window.location.protocol`
2. `api/endpoints/mcp_installer.py:82,85` — `get_server_url()` checks `ssl_enabled` from config
3. `src/giljo_mcp/tools/tool_accessor.py:414` — download URL checks `ssl_enabled` from config

### Phase 2 — P1 Fixes (Important: user-visible URLs)

4. `api/endpoints/downloads.py:50-55` — check `ssl_enabled` first, `x-forwarded-proto` as fallback
5. `api/endpoints/mcp_installer.py:364-368` — share link URLs use same pattern
6. `frontend/src/views/DashboardView.vue:43,279,297,302` — LAN guide uses `window.location.protocol`
7. `installer/core/config.py:237-238` + `Linux_Installer/core/config.py:227-228` — read SSL setting when generating .env
8. `.env.example` — add comments showing HTTPS variants (don't change defaults)

### Phase 3 — P2/P3 Fixes (Lower priority)

9. `api/app.py:697-698` — OpenAPI servers list
10. `startup_prod.py:316-349` — console display URLs
11. `api/endpoints/mcp_http.py:30` — docstring example
12. `frontend/src/components/settings/tabs/NetworkSettingsTab.vue:132` — placeholder text

### Not In Scope

- HTTP→HTTPS redirect (post-CE feature)
- Self-signed certificate trust documentation for CLI tools

## Testing Requirements

One integration test: toggle `ssl_enabled=true` in test config, call every endpoint that returns or generates a URL, assert none contain `http://` or `ws://`.

## Reference Pattern

Backend (from `ai_tools.py:207`):
```python
protocol = "https" if getattr(config.features, "ssl_enabled", False) else "http"
server_url = f"{protocol}://{host}:{port}"
```

Frontend:
```javascript
const protocol = window.location.protocol === 'https:' ? 'https' : 'http'
```

## Key Files Modified

- `frontend/src/components/AiToolConfigWizard.vue`
- `frontend/src/views/DashboardView.vue`
- `frontend/src/components/settings/tabs/NetworkSettingsTab.vue`
- `api/endpoints/mcp_installer.py`
- `api/endpoints/downloads.py`
- `api/endpoints/mcp_http.py`
- `api/app.py`
- `src/giljo_mcp/tools/tool_accessor.py`
- `startup_prod.py`
- `installer/core/config.py`
- `Linux_Installer/core/config.py`
- `.env.example`
- `tests/integration/test_protocol_resolution.py` (new)

## Success Criteria

- All URL-generating code respects `ssl_enabled` setting
- Integration test passes with `ssl_enabled=true` (all URLs use `https://`/`wss://`)
- Integration test passes with `ssl_enabled=false` (all URLs use `http://`/`ws://`)
- No regressions — existing tests still pass
- `ruff check src/ api/` passes clean

## Installation Impact

None. No schema changes. No new dependencies. Config.yaml already has `features.ssl_enabled`.

## Rollback Plan

All changes are string replacements in URL construction. Revert the commit.

## Implementation Summary

### What Was Built
- **P0 fixes**: AiToolConfigWizard.vue, mcp_installer.py, tool_accessor.py, ai_tools.py (broken `getattr` pattern fixed to `get_nested`)
- **P1 fixes**: downloads.py (ssl_enabled + proxy fallback), DashboardView.vue LAN guide, installer .env generators (both Windows + Linux)
- **P2/P3 fixes**: OpenAPI servers list dynamic, startup_prod.py display URLs, mcp_http.py docstring, NetworkSettingsTab placeholder, downloads.py docstring
- **Test**: 16 integration tests covering all URL-generating paths with ssl_enabled toggle
- **Bug found**: `ai_tools.py:207` used `getattr(config.features, "ssl_enabled", False)` which always returns `False` because `FeatureFlags` dataclass doesn't have `ssl_enabled`. Fixed to `config.get_nested("features.ssl_enabled", False)`.

### Key Discovery
The canonical pattern for reading `ssl_enabled` is `config.get_nested("features.ssl_enabled", False)`, NOT `getattr(config.features, ...)`. The `FeatureFlags` dataclass only has `multi_tenant` and `enable_websockets`. The `ssl_enabled` flag lives in the raw config dict only.

### Files Modified (14)
- `frontend/src/components/AiToolConfigWizard.vue` — window.location.protocol
- `frontend/src/views/DashboardView.vue` — computed serverProtocol
- `frontend/src/components/settings/tabs/NetworkSettingsTab.vue` — placeholder
- `api/endpoints/mcp_installer.py` — get_server_url() + share links
- `api/endpoints/downloads.py` — ssl_enabled check + proxy fallback
- `api/endpoints/ai_tools.py` — fixed broken getattr to get_nested
- `api/endpoints/mcp_http.py` — docstring
- `api/app.py` — dynamic OpenAPI servers list
- `src/giljo_mcp/tools/tool_accessor.py` — download URL protocol
- `startup_prod.py` — console display URLs
- `installer/core/config.py` — .env VITE_API_URL/VITE_WS_URL
- `Linux_Installer/core/config.py` — same
- `.env.example` — CORS HTTPS comment
- `tests/integration/test_protocol_resolution.py` — new, 16 tests

### Status
Complete. All 16 integration tests passing. No lint regressions.
