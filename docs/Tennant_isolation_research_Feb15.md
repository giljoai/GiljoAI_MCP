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

## Remaining Gaps (P1 - Next Sprint)

### OrchestrationService - AgentJob lookups by job_id (4 methods)

| Method | Line | Model | Risk |
|--------|------|-------|------|
| `acknowledge_job` | 1341 | AgentJob | HIGH |
| `report_progress` | 1543 | AgentJob | HIGH |
| `complete_job` | 1838 | AgentExecution | HIGH |
| `report_error` | 1990 | AgentJob | HIGH |

All query by `job_id` only without `tenant_key`. Reads feed directly into writes. Mitigated by UUID uniqueness + MCP auth.

### OrchestrationService - session.get() PK lookups

| Method | Line | Model | Risk |
|--------|------|-------|------|
| `get_agent_mission` | 1023 | Project | HIGH |
| `acknowledge_job` | 1352 | Project | HIGH |
| `process_product_vision` | 2446 | Product | HIGH (post-fetch check mitigates) |
| `process_product_vision` | 2478 | Product | HIGH (no post-fetch check) |

Fix: Replace `session.get(Model, pk)` with `select(Model).where(id, tenant_key)`.

### OrchestrationService - AgentTodoItem DELETE

| Method | Line | Model | Risk |
|--------|------|-------|------|
| `report_progress` | 1596 | AgentTodoItem | CRITICAL |

DELETE without tenant filter. Fix: add `tenant_key` to WHERE.

### tools/agent.py - All internal helpers

| Method | Line | Model | Risk |
|--------|------|-------|------|
| `_ensure_agent_with_session` | 134 | Project | HIGH |
| `_decommission_agent_with_session` | 236 | Project | HIGH |
| `_get_agent_health_with_session` | 310 | AgentExecution | HIGH |
| `_get_agent_health_with_session` | 326 | AgentExecution | **CRITICAL - NO FILTER AT ALL** |
| `_handoff_agent_work_with_session` | 371 | Project | HIGH |

Line 326 returns ALL agent executions across ALL tenants with zero WHERE clause.

### MessageService - Internal AgentJob lookups

| Method | Line | Model | Risk |
|--------|------|-------|------|
| `send_message` | 466 | AgentJob | HIGH |
| `receive_messages` | 830 | AgentJob | HIGH |

Mitigated by job_id UUID uniqueness.

### ToolAccessor - Silently dropped tenant_key

| Method | Line | Risk |
|--------|------|------|
| `acknowledge_job` | 778 | HIGH (defense-in-depth) |
| `complete_job` | 801 | HIGH (defense-in-depth) |
| `report_error` | 806 | HIGH (defense-in-depth) |

Accept `tenant_key` from MCP callers but don't pass to OrchestrationService.

### agent_job_manager.py - AgentExecution lookup

| Method | Line | Model | Risk |
|--------|------|-------|------|
| `complete_job` | 389 | AgentExecution | HIGH |

Partially mitigated by prior AgentJob tenant check.

### Cross-tenant purge operations (likely BY DESIGN)

| File | Method | Line | Risk |
|------|--------|------|------|
| `product_service.py` | `purge_expired_deleted_products` | 1591 | CRITICAL |
| `project_service.py` | `purge_expired_deleted_projects` | 2586 | HIGH |

Both are startup cleanup jobs. Likely BY DESIGN (like silence_detector). Need documentation.

---

## Remaining Gaps (P2 - Defense in Depth)

16 MEDIUM findings where queries lack direct tenant_key filters but are mitigated by parent entity validation:

- `product_service.py`: PK lookups with post-fetch checks, count queries on pre-validated products
- `consolidation_service.py`: PK lookup with post-fetch check
- `project_service.py`: Join queries on pre-validated projects
- `message_service.py`: Conditional list_messages paths
- `task_service.py`: User lookups for permission checks (task already validated)
- `template_service.py`: Role lookup by template_id
- `orchestration_service.py`: System default template fallback
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

1. **`session.get(Model, pk)`** bypasses WHERE entirely (5 occurrences)
2. **AgentJob lookup by `job_id` only** (7 occurrences)
3. **Project lookup by `project_id` only** (5 occurrences)
4. **Backward-compat `else` fallback** removing filter (3 found, all fixed)
5. **Background services scanning all tenants** (3 found, 2 documented as BY DESIGN)

### Recommendations for Prevention

1. Make `tenant_key` non-optional in service method signatures
2. Add SQLAlchemy query mixin that auto-appends `WHERE tenant_key`
3. Fix `TenantManager.apply_tenant_filter()` to raise instead of returning unfiltered queries
4. Add linting rule requiring tenant_key on all tenant-scoped queries
