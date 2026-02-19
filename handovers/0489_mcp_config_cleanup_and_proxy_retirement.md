# Handover 0489: MCP Config Generator Revamp, Proxy Retirement & Backend Cleanup

**Date:** 2026-02-19
**From Agent:** Research session (deep-researcher subagents)
**To Agent:** orchestrator-coordinator
**Priority:** HIGH
**Estimated Complexity:** 3-4 hours
**Status:** Not Started
**Merges:** 0397 (Deprecate stdio proxy) + original 0489 (Cleanup API MCP)

---

## Task Summary

Revamp the frontend MCP configuration generators for Claude Code/Codex/Gemini CLI, remove all Cursor references, delete dead proxy code, fix a zero-authentication security gap on `mcp_tools.py`, and clean up stale stdio references. This is a merged handover combining the original 0489 (MCP cleanup, 85% done by 0700 series) and 0397 (stdio proxy deprecation, partially obsoleted when proxy was deleted in 0725b).

## Context and Background

**Research performed (2026-02-19):**
- All 3 CLI tools (Claude Code, Codex, Gemini) now support native HTTP MCP transport
- The stdio proxy file (`mcp_http_stdin_proxy.py`) was already deleted in Handover 0725b
- Frontend `codexPrompt()` still generates a command referencing the deleted proxy -- **broken**
- `CodexCliIntegration.vue` is dead (downloads non-existent .whl for deleted proxy)
- `mcp_tools.py` has **zero authentication** on all endpoints -- security gap
- `CodexConfigModal.vue` shows fabricated TOML config that doesn't match actual Codex CLI format
- Codex CLI does NOT support `--header` CLI flag -- must generate TOML config block instead

**What each CLI tool needs:**
- **Claude Code**: Current `claudePrompt()` is CORRECT. No changes needed.
- **Codex CLI**: Cannot use `--header` flag. Must generate TOML config block for `~/.codex/config.toml` with `http_headers` field.
- **Gemini CLI**: Current `geminiPrompt()` is CORRECT. No changes needed.
- **Cursor**: REMOVE COMPLETELY from all layers (user directive).

**Hierarchy impact:** None. This handover touches only test infrastructure, frontend components, API endpoints for config generation, and documentation. No database schema, no model changes, no service layer changes. No cascade analysis required.

**Installation impact:** Removing `mcp==1.12.3` from `pyproject.toml` reduces dependencies. No migration needed. `install.py` unaffected.

---

## Phase 1: Frontend Config Generators & Cursor Removal (Use `ux-designer` subagent)

### 1.1 Fix `codexPrompt()` in AiToolConfigWizard.vue

**File:** `frontend/src/components/AiToolConfigWizard.vue`

**Current (BROKEN, line 237-241):**
```javascript
function codexPrompt(serverUrl, apiKey) {
  // StdIO proxy with env managed by Codex (no shell restart required)
  // Proxy module is provided by the giljo-mcp wheel installed via pip.
  return `codex mcp add giljo-mcp --env GILJO_MCP_SERVER_URL="${serverUrl}" --env GILJO_API_KEY="${apiKey}" -- python -m giljo_mcp.mcp_http_stdin_proxy`
}
```

**Replace with:**
```javascript
function codexPrompt(serverUrl, apiKey) {
  // Codex CLI does not support --header flag. Generate TOML config block.
  return `# Add to ~/.codex/config.toml\n[mcp_servers.giljo-mcp]\nurl = "${serverUrl}/mcp"\nhttp_headers = { "X-API-Key" = "${apiKey}" }`
}
```

**Why:** Codex CLI v0.44.0+ supports native HTTP but has no `--header` CLI flag. The `http_headers` TOML field is the official way to set custom headers. See [Codex Config Reference](https://developers.openai.com/codex/config-reference/).

### 1.2 Remove Cursor from AiToolConfigWizard.vue

**Same file.** Remove these Cursor references:
- Line 160: `if (/Cursor/i.test(ua)) return 'cursor'` -- remove this line from `detectAITool()`
- Line 177: `{ name: 'Cursor', value: 'cursor' }` -- remove from `aiTools` array
- Line 194: `cursor: '/claude_pix.svg',` -- remove from `toolLogo` computed
- Line 204: `cursor: 'Cursor',` -- remove from `makeKeyName()` map
- Lines 248-252: Delete entire `cursorPrompt()` function
- Lines 262-263: Remove `case 'cursor': return cursorPrompt(...)` from `buildPromptFor()` switch

### 1.3 Fix CodexConfigModal.vue

**File:** `frontend/src/components/settings/modals/CodexConfigModal.vue`

Replace the fabricated TOML config template with the correct Codex CLI format:

**Correct TOML (for display in modal):**
```toml
# ~/.codex/config.toml
[mcp_servers.giljo-mcp]
url = "http://your-server:7272/mcp"
http_headers = { "X-API-Key" = "your-api-key" }
```

Update the download function to generate correct TOML content. Remove any references to `endpoint`, `api_key`, `agents`, `orchestrator_enabled`, `subagent_coordination`, `context_sharing` -- none of these are real Codex config fields.

### 1.4 Fix GeminiConfigModal.vue

**File:** `frontend/src/components/settings/modals/GeminiConfigModal.vue`

Replace the config template with correct Gemini CLI format:

**Correct JSON (for display in modal):**
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "httpUrl": "http://your-server:7272/mcp",
      "headers": {
        "X-API-Key": "your-api-key"
      }
    }
  }
}
```

Key fixes: `httpUrl` not `url`, `headers` is a flat object (no `apiKey` field, no `capabilities` array, no `description`).

### 1.5 Remove CodexCliIntegration.vue (dead component)

**File:** `frontend/src/components/CodexCliIntegration.vue` -- DELETE entirely.

Also remove its import and usage from `frontend/src/views/UserSettings.vue` (imported at line 172, used at line 217 approximately -- verify exact lines).

### 1.6 Remove Cursor from McpIntegration.vue

**File:** `frontend/src/views/McpIntegration.vue`
- Line 23: Remove "Cursor" from text "Claude Code, Cursor, Windsurf, etc."
- Line 58: Remove "Cursor" from restart instruction
- Line 253: Remove the `<li>` for Cursor config path `~/.cursor/mcp.json`

### 1.7 Sync backend ai_tools.py

**File:** `api/endpoints/ai_tools.py`

The backend `get_codex_config()` (lines 70-87) currently generates:
```python
return (
    f'export GILJO_API_KEY="{api_key}"\n'
    f"codex mcp add --url {server_url}/mcp --bearer-token-env-var GILJO_API_KEY giljo-mcp"
)
```

This is better than the frontend but still uses `--bearer-token-env-var` which sends `Authorization: Bearer` instead of `X-API-Key`. Update to match the TOML config approach:

```python
def get_codex_config(server_url: str, api_key: str) -> str:
    return (
        f"# Add to ~/.codex/config.toml\n"
        f"[mcp_servers.giljo-mcp]\n"
        f'url = "{server_url}/mcp"\n'
        f'http_headers = {{ "X-API-Key" = "{api_key}" }}'
    )
```

---

## Phase 2: Dead Proxy Code Removal (Use `tdd-implementor` subagent)

### 2.1 Remove `download_proxy_wheel()` from mcp_installer.py

**File:** `api/endpoints/mcp_installer.py` lines 327-360

Delete the entire `download_proxy_wheel()` function. The endpoint `/api/mcp-installer/proxy-wheel` serves a non-existent `.whl` file and always returns 500.

### 2.2 Remove or auth-gate `mcp_tools.py`

**File:** `api/endpoints/mcp_tools.py` (537 lines)

**CRITICAL SECURITY:** This file provides:
- `POST /mcp/tools/execute` -- executes ANY tool with arbitrary `tenant_key` from request body
- `GET /mcp/tools/list` -- lists all tools with examples
- `GET /mcp/tools/health` -- health check

**NONE have authentication.** The canonical MCP path is `/mcp` (JSON-RPC endpoint in `mcp_http.py`) which HAS authentication.

**Decision needed:** Is `/mcp/tools/*` used by anything?
- Search frontend for `/mcp/tools` references
- Search for any client code calling these endpoints
- If unused (likely): DELETE `mcp_tools.py` entirely and remove its router registration from `api/app.py` (line ~448)
- If used: Add `Depends(get_current_user)` authentication to all endpoints

### 2.3 Clean stale stdio/proxy references

**Files with stale references to clean:**
- `api/app.py` line ~447: Comment "MCP tool endpoints for stdio-to-HTTP bridge" -- update or remove if `mcp_tools.py` is deleted
- `api/endpoints/mcp_tools.py` line 4: Docstring "instead of stdio" -- update or file is deleted
- `src/giljo_mcp/tools/__init__.py` line 35: "Stdio/FastMCP transport was removed in Handover 0334" -- keep as historical note, it's accurate
- `pyproject.toml` line 48: `"mcp==1.12.3"` -- evaluate removal (see 2.4)

### 2.4 Evaluate `mcp==1.12.3` dependency removal

**File:** `pyproject.toml`

Search for ANY import of `mcp` in production code:
```bash
grep -r "from mcp" src/ api/ --include="*.py"
grep -r "import mcp" src/ api/ --include="*.py"
```

If zero imports remain (proxy was the only consumer), REMOVE `"mcp==1.12.3"` from dependencies. This also eliminates security vulnerability GHSA-9h52-p55h-vw2f.

### 2.5 Remove Cursor from tests and docs

**Files:**
- `tests/unit/test_mcp_templates.py` lines 109-112: `test_cursor_detection()` -- remove or update
- `tests/unit/test_mcp_templates.py` lines 163-167: `test_cursor_detection_linux()` -- remove or update
- `docs/guides/code_patterns.md` line 541: Remove Cursor mention from auto-detect description
- `.pre-commit-config.yaml` line 10: Update comment to remove Cursor mention

**NOTE:** `installer/templates/` .bat/.sh templates may also reference Cursor -- check and clean if found.

### 2.6 Remove stale htmlcov artifact

**File:** `htmlcov/z_21ecb78308d63551_mcp_http_stdin_proxy_py.html` -- DELETE (stale coverage for deleted file).

---

## Phase 3: Backend MCP Polish (Use `tdd-implementor` subagent)

### 3.1 Fix error leakage in mcp_http.py

**File:** `api/endpoints/mcp_http.py` line 1046

**Current:**
```python
error=JSONRPCError(code=-32603, message=f"Internal error: {e!s}")
```

**Fix:** Use generic message for unexpected errors:
```python
error=JSONRPCError(code=-32603, message="Internal server error")
```

Log the actual error server-side: `logger.exception("Unexpected MCP endpoint error")`

**Note:** Line 950 intentionally sends error details to agents (tool execution feedback) -- leave that as-is.

### 3.2 Move inline imports to module level in mcp_http.py

**File:** `api/endpoints/mcp_http.py`

Move these inline imports to the top of the file:
- Line 76: `import inspect`
- Line 785: `from api.app import state` (may need lazy import pattern if circular)
- Line 914: `from src.giljo_mcp.services.silence_detector import auto_clear_silent`
- Line 927-929: `import json`, `from pydantic import BaseModel`
- Line 939: `from src.giljo_mcp.exceptions import ValidationError`

**Caution:** `from api.app import state` at module level may cause circular imports. If so, keep it inline and add a comment explaining why.

### 3.3 Add docstrings to mcp_session.py

**File:** `api/endpoints/mcp_session.py`

Add docstrings to these 6 methods of `MCPSessionManager`:
- `authenticate_api_key()`
- `get_or_create_session()`
- `get_session()`
- `update_session_data()`
- `cleanup_expired_sessions()`
- `delete_session()`

### 3.4 Resolve TODO in mcp_installer.py

**File:** `api/endpoints/mcp_installer.py` line 232

**Current:**
```python
# TODO: Query from APIKey table if needed
api_key = getattr(current_user, "api_key", f"gk_{current_user.username}_default")
```

Fix by querying the actual API key or removing the TODO with a proper fallback comment.

---

## Phase 4: Verify & Cleanup

### 4.1 Run linting
```bash
ruff check src/ api/ frontend/ --fix
```

### 4.2 Run tests
```bash
python run_tests.py tests/unit/test_mcp_templates.py --no-cov
python run_tests.py tests/api/ --no-cov --timeout 30 --suite-timeout 120
python run_tests.py tests/integration/ --no-cov --timeout 60
python run_tests.py --no-cov --suite-timeout 600
```

### 4.3 Frontend build check
```bash
cd frontend && npm run build
```

### 4.4 Commit
Single commit covering all changes. Use prefix `fix:` for the security gap, `cleanup:` or `refactor:` for the rest.

---

## Subagent Strategy

| Phase | Recommended Subagent | Parallelizable |
|-------|---------------------|----------------|
| Phase 1 (Frontend) | `ux-designer` | Yes - run in parallel with Phase 2 |
| Phase 2 (Dead code removal) | `tdd-implementor` | Yes - run in parallel with Phase 1 |
| Phase 3 (Backend polish) | `tdd-implementor` | After Phase 2 (same files) |
| Phase 4 (Verify) | `backend-tester` + `frontend-tester` | After all phases |

**Execution order:** Phase 1 + Phase 2 in parallel, then Phase 3, then Phase 4.

---

## Testing Requirements

**Unit Tests:** Modified test files must pass (`test_mcp_templates.py` after Cursor removal)
**API Tests:** `python run_tests.py tests/api/ --no-cov --timeout 30`
**Integration:** `python run_tests.py tests/integration/ --no-cov --timeout 60`
**Frontend:** `cd frontend && npm run build` must succeed
**Full Suite:** `python run_tests.py --no-cov --suite-timeout 600`

---

## Success Criteria

- [ ] `codexPrompt()` generates correct TOML config block (native HTTP, no proxy)
- [ ] `claudePrompt()` unchanged (already correct)
- [ ] `geminiPrompt()` unchanged (already correct)
- [ ] Zero Cursor references in frontend components, backend endpoints, tests, and docs
- [ ] `CodexCliIntegration.vue` deleted, imports removed
- [ ] `CodexConfigModal.vue` shows correct Codex TOML format
- [ ] `GeminiConfigModal.vue` shows correct Gemini JSON format
- [ ] `download_proxy_wheel()` endpoint removed
- [ ] `mcp_tools.py` either deleted (if unused) or auth-gated
- [ ] `mcp==1.12.3` removed from pyproject.toml (if no imports remain)
- [ ] No stale stdio/proxy references in active code
- [ ] Error leakage fixed in mcp_http.py
- [ ] All tests pass, ruff clean, frontend builds

---

## Rollback Plan

All changes are frontend components, API endpoints, and test files. No database or model changes.
```bash
git checkout master -- frontend/src/components/ api/endpoints/ tests/
```

---

## Reference: Correct MCP CLI Commands

### Claude Code (CURRENT -- no change needed)
```bash
claude mcp add --transport http giljo-mcp http://localhost:7272/mcp --header "X-API-Key: YOUR_KEY"
```

### Codex CLI (NEW -- TOML config block)
```toml
# Add to ~/.codex/config.toml
[mcp_servers.giljo-mcp]
url = "http://localhost:7272/mcp"
http_headers = { "X-API-Key" = "YOUR_KEY" }
```

### Gemini CLI (CURRENT -- no change needed)
```bash
gemini mcp add -t http -H "X-API-Key: YOUR_KEY" giljo-mcp http://localhost:7272/mcp
```

---

## Reference: Files to Modify/Delete

| File | Action | Phase |
|------|--------|-------|
| `frontend/src/components/AiToolConfigWizard.vue` | Edit (codexPrompt + remove Cursor) | 1 |
| `frontend/src/components/settings/modals/CodexConfigModal.vue` | Edit (correct TOML format) | 1 |
| `frontend/src/components/settings/modals/GeminiConfigModal.vue` | Edit (correct JSON format) | 1 |
| `frontend/src/components/CodexCliIntegration.vue` | DELETE | 1 |
| `frontend/src/views/UserSettings.vue` | Edit (remove CodexCliIntegration import) | 1 |
| `frontend/src/views/McpIntegration.vue` | Edit (remove Cursor refs) | 1 |
| `api/endpoints/ai_tools.py` | Edit (sync codex config) | 1 |
| `api/endpoints/mcp_installer.py` | Edit (remove proxy-wheel endpoint, fix TODO) | 2 |
| `api/endpoints/mcp_tools.py` | DELETE or auth-gate | 2 |
| `api/app.py` | Edit (remove mcp_tools router if deleted, fix comment) | 2 |
| `pyproject.toml` | Edit (remove mcp==1.12.3 if safe) | 2 |
| `tests/unit/test_mcp_templates.py` | Edit (remove Cursor tests) | 2 |
| `docs/guides/code_patterns.md` | Edit (remove Cursor mention) | 2 |
| `api/endpoints/mcp_http.py` | Edit (error leakage, inline imports) | 3 |
| `api/endpoints/mcp_session.py` | Edit (add docstrings) | 3 |
| `htmlcov/z_*_mcp_http_stdin_proxy_py.html` | DELETE | 2 |

---

## Related Handovers

- **0397** (Deprecate stdio proxy): RETIRED -- merged into this handover. Proxy already deleted by 0725b; this handover cleans the residual references.
- **Original 0489** (Cleanup API MCP): SUPERSEDED -- 85% was completed by 0700 series. Remaining items folded into this handover.
