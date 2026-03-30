# 0769a: Security & Critical Fixes

**Series:** 0769 (Code Quality & Fragility Remediation Sprint)
**Phase:** 1 of 7
**Branch:** `feature/0769-quality-sprint`
**Priority:** SECURITY — must be first
**Estimated Time:** 30 minutes

### Reference Documents
- **Audit report:** `handovers/0769_CODE_QUALITY_FRAGILITY_AUDIT.md` (sections S1, H1, M1, M2)
- **Project rules:** `CLAUDE.md`, `handovers/HANDOVER_INSTRUCTIONS.md`

### Tracking Files
- **Chain log:** `prompts/0769_chain/chain_log.json`

---

## Context

Audit 0769 found a SECURITY-level WebSocket tenant isolation leak, a critical pattern violation in `agent_coordination.py`, and several defense-in-depth tenant isolation gaps. These must be fixed before any other work to prevent the sprint branch from shipping with known security issues.

---

## Scope

### Task 1: WebSocket Cross-Tenant Subscription Leak (SECURITY)

**File:** `api/app.py`, lines 635-649

**Problem:** The WebSocket subscription handler resolves an entity's `tenant_key` from the database but never validates it matches `auth_context["tenant_key"]`. An authenticated user in Tenant A can subscribe to Tenant B's updates by guessing entity IDs.

**Fix:** After resolving `tenant_key` from the entity query (around line 648), add:
```python
if tenant_key != auth_context.get("tenant_key"):
    logger.warning(f"Cross-tenant subscription blocked: user tenant={auth_context.get('tenant_key')}, entity tenant={tenant_key}")
    return
```

**Verify:** The fix must be applied to ALL entity type branches (Project, AgentExecution, Message) in the subscription handler.

### Task 2: Rewrite agent_coordination.py (HIGH — multiple violations)

**File:** `src/giljo_mcp/tools/agent_coordination.py`

**Problems (4 in one file):**
1. **Dict return regression:** 9 paths return `{"success": False, "error": ...}` instead of raising exceptions (post-0480 violation)
2. **Service bypass:** Raw SQLAlchemy DB operations instead of delegating to `AgentJobManager.spawn_agent()` at `services/agent_job_manager.py`
3. **Dangling query:** Lines 201-204 contain a `select()` statement that is built but never executed
4. **Stale import:** `from src.giljo_mcp.database` should be `from giljo_mcp.database`

**Fix approach:**
- Read `AgentJobManager` at `src/giljo_mcp/services/agent_job_manager.py` to understand the service API
- Rewrite `spawn_agent()` to delegate to `AgentJobManager.spawn_agent()` — remove all raw DB logic
- Rewrite `get_team_agents()` to delegate to the appropriate service method
- Replace all `return {"success": False, ...}` with appropriate exception raises (use `ResourceNotFoundError`, `ValidationError`, or `ServiceError` from `giljo_mcp.exceptions`)
- Fix the import path
- Remove the dangling query

**CRITICAL:** Use `find_referencing_symbols` or grep to check all callers of these functions before changing signatures. The tool functions are called from MCP tool handlers — ensure the callers handle exceptions correctly.

### Task 3: Tenant Isolation Defense-in-Depth (MEDIUM)

**File 1:** `api/endpoints/auth_pin_recovery.py`
- **Line 86:** `select(User).where(User.username == request_data.username)` — add `.where(User.tenant_key == tenant_key)` (get tenant_key from request context or default tenant)
- **Line 173:** Same pattern — add tenant_key filter

**File 2:** `api/endpoints/mcp_session.py`
- **Lines 52-56:** API key verification iterates all active keys across tenants. Add `.where(APIKey.tenant_key == tenant_key)` to the query. The tenant_key should be derivable from the request context or the API key prefix.

**File 3:** `api/endpoints/mcp_installer.py`
- **Line 188:** `select(User).where(User.id == user_id, User.is_active)` — add tenant_key filter. The user_id comes from a validated token which should contain tenant_key.

### Task 4: Add Broad-Catch Annotations (MEDIUM)

Add inline justification comments to these 6 unannotated `except Exception` blocks:

1. `src/giljo_mcp/services/message_service.py:1676` — `get_message_status`
2. `src/giljo_mcp/services/orchestration_service.py:2306` — `reactivate_job`
3. `src/giljo_mcp/services/orchestration_service.py:2416` — `dismiss_reactivation`
4. `src/giljo_mcp/services/product_service.py:899` — `purge_product`
5. `src/giljo_mcp/tools/context_tools/fetch_context.py:134` — `_is_category_enabled`
6. `src/giljo_mcp/tools/context_tools/fetch_context.py:212` — `_load_user_depth_config`

Format: `except Exception as e:  # Broad catch: <justification>`

---

## What NOT To Do

- Do NOT refactor any service classes — that is Phase 0769c
- Do NOT touch test files — that is Phase 0769b
- Do NOT fix frontend issues — that is Phase 0769d
- Do NOT change any function signatures unless absolutely required for security

---

## Acceptance Criteria

- [ ] WebSocket subscription validates tenant_key before subscribing (all entity types)
- [ ] agent_coordination.py delegates to service layer, raises exceptions, no dict returns
- [ ] PIN recovery, MCP session, and MCP installer queries filter by tenant_key
- [ ] All 6 broad catches have annotation comments
- [ ] `ruff check src/ api/` passes with 0 issues
- [ ] No new test failures introduced (run `npx vitest run` to verify count stays at 115 or decreases)

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0769_chain/chain_log.json`
- Check `orchestrator_directives` — if STOP, halt immediately
- This is the first session — no previous session to review

### Step 2: Mark Session Started
Update your session in chain_log.json: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Execute Tasks 1-4 above in order.

### Step 4: Update Chain Log
Update your session with:
- `tasks_completed`, `deviations`, `blockers_encountered`
- `notes_for_next`: Critical info for the test stabilization agent (any changed function signatures, new exceptions, etc.)
- `cascading_impacts`: Changes that affect downstream handovers
- `summary`, `status`: "complete", `completed_at`

### Step 5: STOP
**Do NOT spawn the next terminal.** The orchestrator will review your results, adjust downstream handovers if needed, and spawn the next session. Commit your chain log update and exit.
