# 0750d: API Endpoint Hardening

**Series:** 0750 (Code Quality Cleanup Sprint)
**Phase:** 4 of 7
**Branch:** `0750-cleanup-sprint`
**Priority:** HIGH -- SECURITY findings (S-1, H-19) + 2 point fixes

### Reference Documents
- **Roadmap:** `handovers/CLEANUP_ROADMAP_2026_02_28.md` (Phase 4 section)
- **Audit report:** `handovers/CODE_QUALITY_AUDIT_REPORT_2026_02_28.md` (findings S-1, H-19)
- **Orchestrator handover:** `handovers/0700_series/0750_ORCHESTRATOR_HANDOVER.md` (Point Fixes items 2 and 3)
- **Previous phase notes:** Read `prompts/0750_chain/chain_log.json` session 0750c `notes_for_next`

### Tracking Files (update these when done)
- **Chain log:** `prompts/0750_chain/chain_log.json`
- **Progress tracker:** `handovers/0700_series/0750_cleanup_progress.json`

---

## Context

The code quality audit found that `api/endpoints/configuration.py` has 12 endpoints with ZERO authentication. This includes critical endpoints that can change the database password, reload configuration, and modify system settings. Additionally, only 11 of 28 endpoint files in the API layer have auth imports at all.

This phase adds authentication to all configuration endpoints, audits other endpoint files, fixes 3 dict returns in the health check endpoint, and addresses two point fixes: a statistics query bug and a rate-limit bypass header.

---

## Auth Pattern (Already Exists)

The auth pattern is defined in `src/giljo_mcp/auth/dependencies.py`:

**For standard endpoints** (any authenticated user):
```python
from giljo_mcp.auth.dependencies import get_current_active_user
from giljo_mcp.auth.models import User

@router.get("/some-endpoint")
async def some_endpoint(current_user: User = Depends(get_current_active_user)):
    ...
```

**For admin-only endpoints** (configuration, database, system management):
```python
from giljo_mcp.auth.dependencies import require_admin
from giljo_mcp.auth.models import User

@router.post("/admin-endpoint")
async def admin_endpoint(current_user: User = Depends(require_admin)):
    ...
```

---

## Scope

### 4A: Add Auth to Configuration Endpoints (`api/endpoints/configuration.py`)

All 12 endpoints currently have ZERO auth. Add auth as follows:

**Admin-only (sensitive system operations):**
- [ ] Line 107: `set_configuration` (PUT `/key/{key_path}`) — add `Depends(require_admin)`
- [ ] Line 133: `update_configurations` (PATCH `/`) — add `Depends(require_admin)`
- [ ] Line 159: `reload_configuration` (POST `/reload`) — add `Depends(require_admin)`
- [ ] Line 243: `delete_tenant_configuration` (DELETE `/tenant`) — add `Depends(require_admin)`
- [ ] Line 292: `get_database_configuration` (GET `/database`) — add `Depends(require_admin)`
- [ ] Line 318: `update_database_password` (POST `/database/password`) — add `Depends(require_admin)`

**Authenticated user (read-only config access):**
- [ ] Line 50: `get_system_configuration` (GET `/`) — add `Depends(get_current_active_user)`
- [ ] Line 84: `get_configuration` (GET `/key/{key_path}`) — add `Depends(get_current_active_user)`
- [ ] Line 173: `get_tenant_configuration` (GET `/tenant`) — add `Depends(get_current_active_user)`
- [ ] Line 201: `set_tenant_configuration` (PUT `/tenant`) — add `Depends(require_admin)`

**Explicitly public (no auth needed):**
- [ ] Line 435: `get_frontend_configuration` (GET `/frontend`) — LEAVE WITHOUT AUTH (frontend needs this pre-login)
- [ ] Line 487: `test_database_connection` (GET `/health/database`) — LEAVE WITHOUT AUTH (health checks must be public)

**Add imports at top of file:**
```python
from giljo_mcp.auth.dependencies import get_current_active_user, require_admin
from giljo_mcp.auth.models import User
```

### 4B: Fix Dict Returns in Health Check (`api/endpoints/configuration.py`)

The health check endpoint has 3 dict returns. Fix them:

- [ ] **Line 493:** `return {"success": False, "error": "Database manager not initialized"}` — raise `HTTPException(status_code=503, detail="Database manager not initialized")`
- [ ] **Line 504:** `return {"success": False, "error": "Database health check returned False"}` — raise `HTTPException(status_code=503, detail="Database health check failed")`
- [ ] **Line 507:** `return {"success": False, "error": f"Database connection failed: {e!s}"}` — raise `HTTPException(status_code=503, detail=f"Database connection failed: {e!s}")`

### 4C: Audit All Other Endpoint Files for Missing Auth

17 of 28 endpoint files have NO auth imports. For each file below, open it and determine:
- Is it a public endpoint (health, login, frontend config)? → Leave as-is
- Does it handle internal/system operations (MCP, websocket setup)? → May not need user auth, but document why
- Does it handle user data or sensitive operations? → Add `Depends(get_current_active_user)` or `Depends(require_admin)`

Files to audit (no auth imports currently):

| File | Likely Action |
|------|---------------|
| `agent_management.py` | Needs auth — manages agents |
| `configuration.py` | Being fixed in 4A above |
| `context.py` | Needs auth — accesses project context |
| `database_setup.py` | Needs admin — DB initialization |
| `downloads.py` | Needs auth — file downloads |
| `git.py` | Needs auth — git operations |
| `mcp_http.py` | Investigate — MCP protocol handler |
| `mcp_installer.py` | Needs admin — installs MCP servers |
| `mcp_session.py` | Investigate — MCP session management |
| `network.py` | Investigate — network operations |
| `orchestration.py` | Needs auth — manages orchestration |
| `serena.py` | Investigate — Serena integration |
| `setup.py` | Needs admin — system setup |
| `setup_security.py` | Needs admin — security setup |
| `slash_commands.py` | Needs auth — user commands |
| `statistics.py` | Needs auth — project statistics |
| `vision_documents.py` | Needs auth — document management |
| `websocket_bridge.py` | Investigate — WebSocket handler (may use different auth) |

**For each file:** Read the endpoints, add appropriate auth. If unsure whether a specific endpoint should be public, default to requiring auth (safer).

**IMPORTANT:** Some endpoint files may use `request.state.tenant_key` for tenant context but no user auth. These still need `Depends(get_current_active_user)` — tenant context is not authentication.

### 4D: Point Fix — `get_project_statistics_by_id` limit=1 Bug

**File:** `api/endpoints/statistics.py` (line 262-269)

**Current broken code:**
```python
@router.get("/project/{project_id}", response_model=ProjectStatsResponse)
async def get_project_statistics_by_id(request: Request, project_id: str):
    stats = await get_project_statistics(request, limit=1)  # BUG: only gets first project
    for stat in stats:
        if stat.project_id == project_id:
            return stat
    raise HTTPException(status_code=404, detail="Project not found")
```

**Fix:** Replace with a direct lookup that queries for the specific project_id:
```python
@router.get("/project/{project_id}", response_model=ProjectStatsResponse)
async def get_project_statistics_by_id(request: Request, project_id: str):
    stats = await get_project_statistics(request, project_id=project_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Project not found")
    return stats[0]
```

If `get_project_statistics` doesn't support a `project_id` filter, either:
1. Add the filter parameter, or
2. Remove the `limit=1` and let it search all results (less efficient but correct)

Read the `get_project_statistics` function to determine the best approach.

### 4E: Point Fix — Remove X-Test-Mode Rate Limit Bypass

**File:** `api/middleware/auth_rate_limiter.py` (lines 88-91)

**Current broken code:**
```python
# Skip rate limiting in test mode
if request.headers.get("X-Test-Mode") == "true":
    return True
```

**Fix:** Remove the `X-Test-Mode` header check entirely. Any client can send this header to bypass rate limiting in production. The `http://test` base URL check (lines 93-95) is acceptable since the server controls the base URL, but the header check must go.

- [ ] Delete lines 88-91 (the X-Test-Mode header check and its comment)
- [ ] Search for any other references to `X-Test-Mode` in the codebase and remove them
- [ ] Keep the `http://test` base URL check (line 93-95) — this is safe

### 4F: Run Tests

After all changes:
```bash
python -m pytest tests/ -x -q --timeout=60
```

Must still be GREEN: 1238 passed, 522 skipped, 0 failed.

---

## What NOT To Do

- Do NOT remove any existing endpoints
- Do NOT modify the auth system itself (`auth/dependencies.py`, `auth/models.py`)
- Do NOT add auth to explicitly public endpoints: login, health check, frontend config
- Do NOT change WebSocket auth patterns (they use a different mechanism)
- Do NOT modify any files outside `api/` and `src/giljo_mcp/api/` (except the rate limiter middleware)
- Do NOT create new auth roles or permissions — use existing `get_current_active_user` and `require_admin`
- Do NOT change the rate limiter logic beyond removing the X-Test-Mode bypass

---

## Acceptance Criteria

- [ ] All configuration endpoints (except `/frontend` and `/health/database`) require auth
- [ ] Admin-only endpoints use `Depends(require_admin)`
- [ ] Zero dict returns in `api/` directory: `grep -rn 'return {"success": False' api/` returns 0 matches
- [ ] `get_project_statistics_by_id` correctly returns statistics for any valid project_id
- [ ] No `X-Test-Mode` header bypass in rate limiter
- [ ] All other endpoint files audited — auth added where appropriate
- [ ] Test suite still GREEN: 1238 passed, 522 skipped, 0 failed
- [ ] Existing auth tests still pass

---

## Completion Steps

### Step 1: Verify branch
```bash
git branch --show-current
# Must show: 0750-cleanup-sprint
```

### Step 2: Commit
```bash
git add api/endpoints/ src/giljo_mcp/api/ api/middleware/
git commit -m "security(0750d): Harden API endpoints — add auth to config, fix stats bug, remove test bypass"
```

### Step 3: Record commit hash
```bash
git rev-parse --short HEAD
```

### Step 4: Update chain log
Read `prompts/0750_chain/chain_log.json`, update session `0750d`:
- Set `"status": "complete"`
- Set `"started_at"` and `"completed_at"` to timestamps
- Fill in `"tasks_completed"` with what you did
- Fill in `"deviations"` if anything changed from plan
- Fill in `"blockers_encountered"` if any
- Fill in `"notes_for_next"` with: which endpoint files were left unprotected and why, any auth issues found
- Fill in `"summary"` with a 2-3 sentence summary

### Step 5: Update progress tracker
Read `handovers/0700_series/0750_cleanup_progress.json`, update `phases[3]`:
- Set `"status": "complete"`
- Set `"commits": ["<hash>"]`
- Set `"notes"` to brief summary

### Step 6: Verify
```bash
grep -rn 'return {"success": False' api/
grep -rn 'X-Test-Mode' src/ api/
python -m pytest tests/ -x -q --timeout=60
```

### Step 7: Done
Do NOT spawn the next terminal. The orchestrator session handles chaining.
Print "0750d COMPLETE" as your final message.
