# Tenant Isolation Security Audit - February 15, 2026

## Scope

Full codebase audit of all SQLAlchemy ORM queries across service layer (`src/giljo_mcp/services/`), tool layer (`src/giljo_mcp/tools/`), and API endpoint layer (`api/endpoints/`) for missing `tenant_key` WHERE clause filters.

65 total queries found missing tenant_key filters across 16 service files + tool files.

---

## Phase A - ProjectService (Commit 2b51c20f)

### Root Cause

The tenant isolation bug occurred because `get_deleted_projects()` at `api/endpoints/projects/crud.py:157` called `list_projects(status="deleted")` without passing `tenant_key`. Additionally, `restore_project()` had zero tenant filtering on its UPDATE query, and `switch_project()` had a backward-compatibility fallback that queried without tenant filtering.

### Fixes Applied

| File | Method | Change |
|------|--------|--------|
| `api/endpoints/projects/crud.py:157` | `get_deleted_projects` | Added `tenant_key=current_user.tenant_key` |
| `project_service.py:2035` | `restore_project` | Made `tenant_key` required, added `tenant_key` to WHERE |
| `project_service.py:2083` | `switch_project` | Removed backward-compat fallback, added tenant validation |
| `project_service.py:2094` | `switch_project` | Removed broken lazy import (`from giljo_mcp.tenant`) + redundant `current_tenant.set()` |
| `api/endpoints/projects/lifecycle.py:221` | `restore_project` caller | Passes `tenant_key=current_user.tenant_key` |
| `tools/tool_accessor.py:266-274` | `cancel_project`, `restore_project` | Pass `tenant_key` from TenantManager |

### Regression Tests

`tests/services/test_project_tenant_isolation_regression.py`: 7 tests, all pass.

---

## Phase B - TaskService + MessageService (Commit 2b51c20f)

### TaskService Fixes

| File | Method | Issue | Fix |
|------|--------|-------|-----|
| `task_service.py:493` | `_update_task_impl` | Queried `Task.id` only (CRITICAL) | Added `TenantManager.get_current_tenant()` fallback + ValidationError + `and_(Task.id, Task.tenant_key)` |
| `task_service.py:898` | `_convert_to_project_impl` | Subtask query missing tenant_key | Added `and_(Task.parent_task_id, Task.tenant_key)` |

### MessageService Fixes (7 vulnerabilities)

| Method | Issue | Fix |
|--------|-------|-----|
| `send_message` | Backward-compat fallback bypassed tenant filter | Removed `else` branch, require tenant_key |
| `send_message` | WebSocket broadcast query missing filter | Added `AgentExecution.tenant_key == tenant_key` |
| `send_message` | Recipient counter query missing filter | Added `and_(AgentExecution.agent_id, AgentExecution.tenant_key)` |
| `broadcast` | Zero tenant isolation | Added `tenant_key` param, validation, `AgentJob.tenant_key` filter |
| `get_messages` | Zero tenant isolation | Added `tenant_key` param, validation, `Message.tenant_key` filter |
| `complete_message` | Zero tenant isolation | Added `tenant_key` param, validation, compound WHERE |
| `list_messages` | project_id path missing filter | Added `Message.tenant_key` when available |

### API + ToolAccessor Callers Updated

| File | Changes |
|------|---------|
| `api/endpoints/messages.py` | 3 endpoints now pass `tenant_key=current_user.tenant_key` |
| `tools/tool_accessor.py` | `get_messages`, `complete_message`, `broadcast`, `log_task` pass `tenant_key` |

### Regression Tests

- `tests/services/test_task_tenant_isolation_regression.py`: 8 tests, all pass
- `tests/services/test_message_tenant_isolation_regression.py`: 12 tests, 11 pass + 1 skip (test infrastructure)

---

## Phase C - P0 Items (Post-audit)

### C-a: `update_project_mission()` backward-compat fallback (CRITICAL - FIXED)

- **File**: `src/giljo_mcp/services/project_service.py`
- **Issue**: `else` branch queried `Project.id` only when `tenant_key` was None
- **Fix**: Added TenantManager fallback + ValidationError guard, removed unfiltered branch
- Both UPDATE and SELECT queries now use `and_(Project.tenant_key == tenant_key, Project.id == project_id)`

### C-b: `_purge_project_records()` cascade deletes (CRITICAL - FIXED)

- **File**: `src/giljo_mcp/services/project_service.py`
- **Issue**: 3 DELETE queries (AgentJob, Task, Message) filtered by `project_id` only
- **Fix**: Added `and_(Model.project_id == project.id, Model.tenant_key == tenant_key)` to all 3

### C-c: Silence detector cross-tenant scans (CRITICAL - DOCUMENTED AS BY DESIGN)

- **File**: `src/giljo_mcp/services/silence_detector.py`
- **`_detect_silent_agents()`**: Background health monitor scanning ALL tenants on a timer. No user/tenant context. Cross-tenant scope is intentional (system-level cleanup job).
- **`auto_clear_silent()`**: Called from MCP tool handler with `job_id` from authenticated context. UUID uniqueness + MCP auth prevents cross-tenant access.
- **Fix**: Added explicit documentation comments in code

### C-d: `context.py` 4 endpoints missing tenant injection (HIGH - FIXED)

- **File**: `api/endpoints/context.py`
- **Issue**: GET /index, /vision, /vision/index, /settings had no `Depends(get_tenant_key)`
- **Fix**: Added `tenant_key: str = Depends(get_tenant_key)` to all 4 endpoints
- Pattern matches `chunk_vision_document` which already had the dependency

### Phase C Test Results

47 tests run, 47 passed, 0 failed, 0 skipped.

---

## BATCH 1 - OrchestrationService + MessageService list_messages (Commit 6c6c7221)

### OrchestrationService (7 fixes)

| Method | Finding | Severity | Fix Applied |
|--------|---------|----------|-------------|
| `report_progress` | AgentJob lookup by `job_id` only (line 1543) | HIGH | Added `AgentJob.tenant_key == tenant_key` to WHERE |
| `report_progress` | `DELETE AgentTodoItem` by `job_id` only (line 1596) | CRITICAL | Added `AgentTodoItem.tenant_key == tenant_key` to DELETE WHERE |
| `report_progress` | `SELECT AgentTodoItem` by `job_id` only (line 1629) | HIGH | Added `AgentTodoItem.tenant_key == tenant_key` to SELECT WHERE |
| `get_agent_mission` | `session.get(Project, job.project_id)` bypasses WHERE (line 1023) | HIGH | Replaced with `select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)` |
| `acknowledge_job` | AgentJob lookup by `job_id` only (line 1341) + `session.get(Project)` (line 1352) | HIGH | Added `tenant_key` to AgentJob WHERE; replaced `session.get` with `select().where(tenant_key)` |
| `complete_job` | Sibling AgentExecution query by `job_id` only (line 1838) | HIGH | Added `AgentExecution.tenant_key == tenant_key` to WHERE |
| `report_error` | AgentJob lookup by `job_id` only (line 1990) | HIGH | Added `AgentJob.tenant_key == tenant_key` to WHERE |

### MessageService list_messages (4 fixes)

| Finding | Severity | Fix Applied |
|---------|----------|-------------|
| `tenant_key` parameter was optional, allowing unscoped queries | HIGH | Made `tenant_key` always required (raises error if None) |
| AgentJob lookup conditions only used `tenant_key` conditionally | HIGH | `AgentJob.tenant_key == tenant_key` always applied |
| Message query by `project_id` had conditional tenant filter | HIGH | `Message.tenant_key == tenant_key` always applied |
| Fallback `project.id` query path skipped tenant filter | HIGH | `Project.tenant_key == tenant_key` always applied |

### Regression Tests

- `tests/services/test_orchestration_tenant_isolation_regression.py`: 11 new tests
  - Cross-tenant blocked + same-tenant allowed for: `report_progress`, `get_agent_mission`, `acknowledge_job`, `complete_job`, `report_error`
  - Combined audit test verifying all 5 methods in single fixture
- `tests/services/test_message_tenant_isolation_regression.py`: 3 new tests added
  - `test_list_messages_requires_tenant_key`
  - `test_list_messages_blocks_cross_tenant_by_agent` (raises `ResourceNotFoundError`)
  - `test_list_messages_blocks_cross_tenant_by_project`

---

## BATCH 2 - tools/agent.py, tool_accessor.py, message_service, agent_job_manager (Commit 9afff7ec)

### tools/agent.py (6 helper functions hardened)

| Function | Finding | Severity | Fix Applied |
|----------|---------|----------|-------------|
| `_ensure_agent_with_session` | `select(Project).where(Project.id == project_id)` -- no tenant_key (line 134) | HIGH | Added `tenant_key` param; when provided, adds `Project.tenant_key == tenant_key` to WHERE |
| `_decommission_agent_with_session` | Same pattern (line 236) | HIGH | Same fix |
| `_get_agent_health_with_session` | `select(AgentExecution).where(agent_name.like(...))` -- no tenant_key (line 310) | HIGH | Added `AgentExecution.tenant_key == tenant_key` when provided |
| `_get_agent_health_with_session` | `select(AgentExecution)` with zero WHERE clause -- returns ALL tenants (line 326) | HIGH | Added `AgentExecution.tenant_key == tenant_key` when provided |
| `_get_agent_health_with_session` | `select(AgentJob).where(job_id)` -- no tenant_key (line 333) | HIGH | Added `AgentJob.tenant_key == tenant_key` when provided |
| `_handoff_agent_work_with_session` | `select(Project).where(Project.id == project_id)` -- no tenant_key (line 371) | HIGH | Same pattern as ensure/decommission |

All 4 wrapper functions (`_ensure_agent`, `_decommission_agent`, `_get_agent_health`, `_handoff_agent_work`) updated to accept and pass through `tenant_key`.

### tool_accessor.py (3 pass-throughs fixed)

| Method | Finding | Severity | Fix Applied |
|--------|---------|----------|-------------|
| `acknowledge_job` | Accepts `tenant_key` from MCP caller but doesn't pass to OrchestrationService | HIGH | Added `tenant_key=tenant_key` to `acknowledge_job()` call |
| `complete_job` | Same silent drop | HIGH | Added `tenant_key=tenant_key` to `complete_job()` call |
| `report_error` | Same silent drop | HIGH | Added `tenant_key=tenant_key` to `report_error()` call |

### message_service.py (2 AgentJob lookups)

| Method | Finding | Severity | Fix Applied |
|--------|---------|----------|-------------|
| `send_message` (line 466) | Sender's AgentJob lookup by `job_id` only | HIGH | Added `AgentJob.tenant_key == tenant_key` |
| `receive_messages` (line 829) | AgentJob lookup by `job_id` only | HIGH | Added `AgentJob.tenant_key == tenant_key` |

### agent_job_manager.py (1 AgentExecution lookup)

| Method | Finding | Severity | Fix Applied |
|--------|---------|----------|-------------|
| `complete_job_lifecycle` (line 389) | `select(AgentExecution).where(job_id)` -- no tenant_key | HIGH | Added `AgentExecution.tenant_key == tenant_key` |

---

## BATCH 3 - TenantManager hardening + mission_planner session.get (Commit 308ffa68)

### TenantManager fail-open behavior (2 fixes)

| Method | Finding | Severity | Fix Applied |
|--------|---------|----------|-------------|
| `apply_tenant_filter()` | When called with `tenant_key=None` and no ContextVar set, silently returned the unfiltered query | HIGH | Now raises `ValueError("apply_tenant_filter called without tenant_key and no tenant context set...")` |
| `ensure_tenant_isolation()` | When called with `tenant_key=None` and no ContextVar set, silently returned without checking | HIGH | Now raises `ValueError("ensure_tenant_isolation called without tenant_key and no tenant context set...")` |

Note: Only 2 production callers use `apply_tenant_filter` (200+ queries use inline `.where()` clauses). The fix ensures any future callers cannot accidentally get unfiltered results.

### mission_planner.py session.get() replacement (2 fixes)

| Method | Finding | Severity | Fix Applied |
|--------|---------|----------|-------------|
| `_store_token_metrics` async path (line 3124) | `session.get(Project, project_id)` bypasses WHERE | HIGH | Replaced with `select(Project).where(Project.id == project_id)` |
| `_store_token_metrics` sync path (line 3136) | Same `session.get()` pattern | HIGH | Same replacement |

Note: These lookups don't yet filter by `tenant_key` because the method doesn't receive one. The `session.get` -> `select().where()` migration removes the ORM shortcut that bypasses query-level filtering, making it straightforward to add `tenant_key` when available.

---

## Test Results After Full Remediation

- 61 tenant isolation regression tests across 3 test files, all passing
- 159 total tests passing in full suite
- 1 pre-existing failure (`test_acknowledge_message_happy_path`) confirmed unrelated to tenant isolation changes

---

## Not Fixed (Documented - Per Remediation Scope)

| Item | Category | Reason |
|------|----------|--------|
| `silence_detector.py` (2 CRITICAL) | By design | Ephemeral background service, non-persistent, no user/tenant context available |
| `context.py` broken endpoints (ImportError + arg mismatch) | Functional bug | Pre-existing broken code, not a security issue |
| `GET /context/index` filesystem path disclosure | Separate issue | Not a tenant isolation vulnerability |
| 10 MEDIUM defense-in-depth items | Backlog | Parent entity validation provides coverage |
| `process_product_vision` `session.get(Product)` (2 instances) | Backlog | Post-fetch check partially mitigates; needs `select().where()` replacement |
| Cross-tenant purge operations (`purge_expired_deleted_products`, `purge_expired_deleted_projects`) | By design | Startup cleanup jobs, similar to silence_detector |

---

## Remaining Gaps (P2 - Defense in Depth)

16 MEDIUM findings where queries lack direct tenant_key filters but are mitigated by parent entity validation:

- `product_service.py`: PK lookups with post-fetch checks, count queries on pre-validated products
- `consolidation_service.py`: PK lookup with post-fetch check
- `project_service.py`: Join queries on pre-validated projects
- `task_service.py`: User lookups for permission checks (task already validated)
- `template_service.py`: Role lookup by template_id
- `orchestration_service.py`: System default template fallback (intentional)
- `silence_detector.py`: Global settings read

### Code quality items

- `api/endpoints/tasks.py:167`: Passes `tenant_key=None` explicitly (works via ContextVar, but inconsistent)
- `api/endpoints/agent_jobs/executions.py:48`: Execution query missing tenant_key (job validated)
- `api/endpoints/statistics.py:469`: No auth dependency (mock data currently)

---

## LOW / BY DESIGN (22 items - no action needed)

- `auth_service.py`: Login by username (9 items) - must span tenants
- `org_service.py`: Organization operations (5 items) - orgs span tenants by design
- `user_service.py`: Username/email uniqueness, admin paths (7 items)
- `template_service.py`: Cross-tenant existence check for 403 vs 404 (1 item)

---

## Architecture Notes

### Two Tenant Isolation Mechanisms

1. **Explicit `tenant_key` parameter**: Endpoint passes `tenant_key=current_user.tenant_key`. Safest.
2. **Implicit TenantManager ContextVar**: DI function calls `set_current_tenant()`. Service reads `get_current_tenant()`. Async-safe via `contextvars.ContextVar`.

### Common Anti-Patterns Found

1. **`session.get(Model, pk)`** bypasses WHERE entirely (8 occurrences found, 4 fixed)
2. **AgentJob lookup by `job_id` only** (7 occurrences, all fixed)
3. **Project lookup by `project_id` only** (5 occurrences in tools/agent.py, all fixed)
4. **Backward-compat `else` fallback** removing filter (3 found, all fixed in Phase A-C)
5. **Background services scanning all tenants** (3 found, documented as BY DESIGN)
6. **ToolAccessor silently dropping `tenant_key`** (3 found, all fixed in BATCH 2)
7. **TenantManager utilities failing open on None** (2 found, hardened in BATCH 3)

### Recommendations for Prevention

1. Ban `session.get()` for tenant-scoped entities -- always use `select().where(tenant_key)`
2. Make `tenant_key` non-optional in service method signatures
3. Add SQLAlchemy query mixin that auto-appends `WHERE tenant_key`
4. Add linting rule or test that scans for unscoped queries on tenant-key-bearing tables
5. Require all new service methods to have regression tests verifying cross-tenant access is blocked
