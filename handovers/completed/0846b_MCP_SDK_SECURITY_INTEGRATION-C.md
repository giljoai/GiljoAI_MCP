# Handover 0846b: Security Re-integration & Old Code Removal

**Date:** 2026-03-29
**From Agent:** Codex session (orchestrator)
**To Agent:** Next Session
**Priority:** High
**Estimated Complexity:** 1.5-2 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Pre-Work Reading (MANDATORY)

1. `handovers/HANDOVER_INSTRUCTIONS.md` — golden rules, quality gates
2. `handovers/Reference_docs/QUICK_LAUNCH.txt` — TDD discipline
3. `handovers/0846_MCP_SDK_STANDARDIZATION.md` — series coordinator, architecture decision
4. `CLAUDE.md` — project conventions (especially tenant isolation rule)
5. **Chain log `notes_for_next` from 0846a** — critical SDK integration details

---

## Task Summary

Wire Bearer token auth and tenant isolation into the new FastMCP server from 0846a. Promote the SDK endpoint from `/mcp/v2` to `/mcp`. Remove the old custom JSON-RPC implementation. Clean up dead code from `mcp_http.py`.

---

## Context

After 0846a, we have a working FastMCP server at `/mcp/v2` with all 30 tools registered but no auth/tenant security. The old custom endpoint still runs at `/mcp`. This phase wires security, promotes the new endpoint, and removes the old one.

### Security layers to re-integrate (from current `mcp_http.py`)

1. **Auth middleware** (lines 1281-1334): Extract Bearer token → try JWT → fallback to API key → create/get session → resolve tenant
2. **Tenant key validation** (lines 60-116): `validate_and_override_tenant_key()` — prevents tenant spoofing by overriding client-supplied tenant_key with session tenant_key
3. **Argument schema allowlist** (lines 198-336): `_TOOL_SCHEMA_PARAMS` dict — strips undeclared arguments. **Note:** The SDK may handle this automatically via tool input schema validation. Verify before re-implementing.
4. **IP logging** (lines 1336-1343): Passive, non-blocking IP logging for API key audit
5. **Session management** (via `MCPSessionManager`): PostgreSQL-backed sessions with 24h expiry

---

## Implementation Plan

### Step 1: Design Auth Integration Pattern

The SDK's FastMCP manages its own transport-level sessions (`Mcp-Session-Id`). Our auth is application-level. These coexist:

**Option A — FastAPI middleware:** Add middleware to the FastAPI app that intercepts requests to `/mcp`, validates Bearer tokens, resolves tenant, and attaches context to request state before the SDK processes the request.

**Option B — SDK auth hooks:** If FastMCP supports `auth` parameter or dependency injection for per-request context, use that.

**Read 0846a's `notes_for_next` in the chain log** — the previous agent will have documented how per-request context works in the SDK.

### Step 2: Implement Auth Middleware

Create auth logic that runs before every MCP tool call:

```python
# Pattern (adjust based on SDK API discovered in 0846a):
async def mcp_auth_middleware(request):
    """Extract Bearer token, resolve tenant, attach to request state."""
    authorization = request.headers.get("authorization", "")
    api_key_header = request.headers.get("x-api-key")

    # Same logic as current mcp_http.py lines 1281-1334
    # 1. Try X-API-Key header
    # 2. Try Bearer token (JWT first, API key fallback)
    # 3. Resolve session via MCPSessionManager
    # 4. Attach tenant_key to request state
    # 5. Set TenantManager.set_current_tenant()
```

### Step 3: Wire Tenant Key Injection into Tool Wrappers

Each `@mcp.tool()` wrapper from 0846a needs to:
1. Get tenant_key from the request context (set by auth middleware)
2. Pass it to `ToolAccessor` methods that accept `tenant_key`
3. Use `validate_and_override_tenant_key()` logic (inspect signature, inject if accepted)

The `validate_and_override_tenant_key()` function from `mcp_http.py` (lines 60-116) can be reused directly — it's pure Python with no transport dependency.

### Step 4: Verify SDK Schema Validation Replaces _TOOL_SCHEMA_PARAMS

The SDK validates tool arguments against the registered `@mcp.tool()` input schema automatically. Test whether this makes `_TOOL_SCHEMA_PARAMS` redundant:

1. Register a tool with specific params (e.g., `create_project(name, description, project_type)`)
2. Call it with an extra undeclared param (e.g., `tenant_key`, `mission`)
3. If SDK strips/rejects undeclared params → `_TOOL_SCHEMA_PARAMS` is redundant, remove it
4. If SDK passes them through → keep the allowlist logic

### Step 5: Promote Endpoint

Once security is verified:
1. Remove the old `/mcp` route from `mcp_http.py` or remove the router entirely
2. Move the SDK mount from `/mcp/v2` to `/mcp` in `app.py`
3. Verify all three CLI configs still work with the same URL

### Step 6: Remove Dead Code

After promotion, these become dead code — **delete them** (git has the history):

From `mcp_http.py` (the entire file may be deletable, but verify first):
- `JSONRPCRequest`, `JSONRPCResponse`, `JSONRPCError`, `JSONRPCErrorResponse` models
- `handle_initialize()`, `handle_tools_list()`, `handle_tools_call()` functions
- `mcp_endpoint()` route handler
- All `_build_*_tools()` schema builder functions (6 functions, ~700 lines)
- `tool_map` dictionary
- `_TOOL_SCHEMA_PARAMS` dict (if SDK handles validation)
- `HIDDEN_FROM_SCHEMA_TOOLS` set

**Keep** (move to `mcp_sdk_server.py` or a shared module if still needed):
- `validate_and_override_tenant_key()` — unless replaced by SDK middleware

From `app.py`:
- Remove `include_router(mcp_http.router)` line
- Keep the SDK mount

### Step 7: Write Security Tests

**TDD — write failing tests first:**

Create or extend `tests/integration/test_mcp_sdk_security.py`:

1. **Test: No auth → rejected.** Call tool without Bearer token, verify 401/error
2. **Test: Valid API key → tool works.** Call health_check with valid API key, verify success
3. **Test: Valid JWT → tool works.** Call with JWT Bearer token, verify success
4. **Test: Tenant isolation.** Call create_project, verify tenant_key in DB matches session tenant
5. **Test: Tenant spoofing blocked.** Send `tenant_key: "other_tenant"` in args, verify it's overridden
6. **Test: Undeclared args stripped.** Send extra args not in tool schema, verify they don't reach ToolAccessor
7. **Test: IP logging.** Call with API key, verify IP logged (non-blocking)
8. **Test: Session persistence.** Make two calls, verify same session reused

---

## Files to Modify/Delete

| File | Action | Notes |
|------|--------|-------|
| `api/endpoints/mcp_sdk_server.py` | MODIFY | Add auth middleware, tenant injection to tool wrappers |
| `api/endpoints/mcp_http.py` | **DELETE or gut** | Remove all custom JSON-RPC transport code |
| `api/app.py` | MODIFY | Remove old router, promote SDK mount to `/mcp` |
| `tests/integration/test_mcp_sdk_security.py` | **CREATE** | Auth + tenant isolation tests |

**Files to keep unchanged:**
- `api/endpoints/mcp_session.py` — `MCPSessionManager` stays, used by new auth middleware
- `src/giljo_mcp/tools/tool_accessor.py` — business logic untouched

---

## Key Constraints

- Every tool call MUST have tenant_key resolved from auth — no anonymous access
- `validate_and_override_tenant_key()` signature inspection logic must be preserved or equivalent
- `MCPSessionManager` PostgreSQL sessions must still work (24h expiry, IP logging)
- Bearer token dual-path (JWT → API key fallback) must be preserved
- The transition from `/mcp/v2` to `/mcp` should be atomic in one commit

---

## Success Criteria

- [ ] Bearer token auth works on SDK endpoint (both JWT and API key paths)
- [ ] Tenant key injected into all tenant-aware tools
- [ ] Tenant spoofing blocked (client-supplied tenant_key overridden)
- [ ] Undeclared args stripped or rejected
- [ ] Old `mcp_http.py` custom transport code deleted (or file deleted entirely)
- [ ] `app.py` references only the SDK server, not the old router
- [ ] All security tests pass
- [ ] All existing tests still pass (`pytest tests/ -x` green)
- [ ] Server starts clean, no import errors

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0846_chain/chain_log.json`
- Check `orchestrator_directives` — if STOP, halt immediately
- **Review 0846a's `notes_for_next`** — critical SDK integration details
- Verify 0846a status is `complete`

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Follow the implementation plan above. Use TDD discipline.

### Step 4: Update Chain Log
Update your session with:
- `tasks_completed`, `deviations`, `blockers_encountered`
- `notes_for_next`: **Critical info for 0846c** — what was deleted from mcp_http.py, which docs reference deleted constructs, any frontend config changes needed
- `cascading_impacts`: List any docs or frontend files that now reference dead code/patterns
- `summary`, `status`: "complete", `completed_at`

### Step 5: STOP
**Do NOT spawn the next terminal.** Commit your chain log update and exit.
