# Handover 0812: Remove Unused task.job_id Foreign Key

**Date:** 2026-03-10
**From Agent:** Tech debt audit session
**To Agent:** Next Session
**Priority:** Low
**Estimated Complexity:** 1-2 hours
**Status:** Completed
**Edition Scope:** CE

## Task Summary

Remove the unused `job_id` column, FK constraint, and indexes from the Task model. This column was added in Handover 0072/0381 for a task-to-agent-job integration feature that was never implemented. No code reads, writes, or queries this field. It is dead schema.

## Context and Background

- Handover 0072 added `agent_job_id` FK to Task for planned task-agent execution integration
- Handover 0381 renamed it to `job_id` during the agent_id/job_id separation cleanup
- The integration was never built -- no `execute_task_with_agent()` tool, no status sync, no automation
- Tasks are a lightweight tech debt tracker. They convert to **projects** (not jobs) when users act on them
- The `job_id` field is always NULL in production data
- Decision made 2026-03-10 to remove rather than implement the abandoned integration

## Cascading Impact Analysis

### Upstream Impact
- **AgentJob model**: Has NO relationship/backref pointing to Tasks. One-way FK only. No impact.
- **No other tables** reference `tasks.job_id`. Clean removal.

### Downstream Impact
- **Task creation**: `TaskCreate` schema does NOT include `job_id`. No impact.
- **Task updates**: `TaskUpdate` schema does NOT include `job_id`. No impact.
- **MCP tools**: `create_task` tool does not expose `job_id`. No impact.
- **Frontend**: No Vue component reads or displays `task.job_id`. No impact.
- **WebSocket events**: No event payload includes `task.job_id`. No impact.
- **Tests**: Zero tests assert on `task.job_id`. No impact.

### Sibling Impact
- Task-to-project conversion (`convert_to_project()`) does not use `job_id`. No impact.
- Task CRUD operations do not reference `job_id`. No impact.

## Files to Modify

### 1. NEW: Alembic Migration

**Create**: `migrations/versions/XXXX_0812_drop_tasks_job_id.py`

Operations (in order):
1. Drop FK constraint `fk_task_agent_job`
2. Drop index `idx_task_tenant_job`
3. Drop index `idx_task_job`
4. Drop column `tasks.job_id`

Include downgrade path that recreates all three (FK, indexes, column) for reversibility.
Use existence checks for idempotency (pattern from `a7c5e0f1d234`).

### 2. Model: `src/giljo_mcp/models/tasks.py`

Remove:
- Line 73: `job_id = Column(String(36), ForeignKey("agent_jobs.job_id"), nullable=True)`
- Line 110: `Index("idx_task_job", "job_id")`
- Line 111: `Index("idx_task_tenant_job", "tenant_key", "job_id")`
- Lines 36, 72: Comments referencing Handover 0072/0381 job_id integration

### 3. Schema: `api/schemas/task.py`

Remove:
- Line 122: `job_id: Optional[str] = Field(None, description="Linked agent job ID for execution tracking")`

### 4. Endpoint: `api/endpoints/tasks.py`

Remove:
- Line 103: `job_id=task.job_id` from the `task_to_response()` helper function

### 5. Documentation: `handovers/techdebt_march_2026.md`

Remove Item 1 (Task-Agent Execution Integration) and move to resolved table.

## Implementation Plan

### Phase 1: Code Changes (30 min)
1. Remove `job_id` column, FK, indexes, and comments from Task model
2. Remove `job_id` from TaskResponse schema
3. Remove `job_id` from `task_to_response()` endpoint helper
4. Update techdebt_march_2026.md

### Phase 2: Migration (30 min)
1. Generate Alembic migration: `alembic revision --autogenerate -m "0812_drop_tasks_job_id"`
2. Review generated migration -- ensure it drops FK, indexes, and column in correct order
3. Add existence checks for idempotency
4. Write downgrade path
5. Run: `alembic upgrade head`

### Phase 3: Testing (30 min)
1. Verify migration runs cleanly (upgrade)
2. Verify migration reverses cleanly (downgrade + re-upgrade)
3. Run existing task tests to confirm no regressions
4. Verify `GET /api/v1/tasks/` response no longer includes `job_id`
5. Verify `POST /api/v1/tasks/` still works
6. Verify `create_task` MCP tool still works

## Testing Requirements

**Existing tests** -- all should continue passing with zero changes:
- Task CRUD tests
- Task service tests
- MCP tool tests for `create_task`

**Manual verification**:
- Create a task via UI -- confirm success
- List tasks via API -- confirm `job_id` absent from response
- Check database: `SELECT column_name FROM information_schema.columns WHERE table_name='tasks' AND column_name='job_id'` returns empty

## Dependencies and Blockers

- None. This is a standalone cleanup with no external dependencies.

## Installation Impact

- Migration runs automatically via `alembic upgrade head` (standard path)
- Fresh installs via `install.py` will include this migration in the chain
- Existing installs will run the migration on next upgrade
- Idempotent -- safe to re-run

## Success Criteria

- `tasks.job_id` column, FK constraint, and indexes removed from database
- Task model, schema, and endpoint no longer reference `job_id`
- All existing tests pass without modification
- Migration is reversible (downgrade path works)

## Rollback Plan

- Run `alembic downgrade -1` to restore the column, FK, and indexes
- Revert code changes via `git revert`
- Column will be re-created as nullable with NULL values (no data loss)

## Risk Assessment

**Risk**: LOW
- Nullable column that is always NULL -- no data loss
- No business logic dependencies -- no behavioral changes
- No frontend impact -- field never displayed
- No MCP tool impact -- field never exposed
- Clean FK with no backrefs -- no ORM cascade issues

## Progress Updates

### 2026-03-12 - Claude Opus 4.6 Session
**Status:** Completed

**Work Done:**
- Removed `job_id` column, FK, 2 indexes, and comments from Task model (`tasks.py`)
- Removed `job_id` from `TaskResponse` schema (`task.py`)
- Removed `job_id` from `task_to_response()` endpoint helper (`tasks.py`)
- Created idempotent Alembic migration `c4d5e6f70812` with full downgrade path
- Updated `techdebt_march_2026.md` to reflect completion
- 133 task tests passing, zero regressions
- Migration reversibility verified (downgrade + re-upgrade)
- All pre-commit hooks passed (ruff, bandit, gitleaks, CE/SaaS boundary)
- Commit: `95b9ec99`

**Files Modified:**
- `src/giljo_mcp/models/tasks.py` (column, indexes, docstring)
- `api/schemas/task.py` (TaskResponse field)
- `api/endpoints/tasks.py` (task_to_response helper)
- `migrations/versions/c4d5e6f70812_0812_drop_tasks_job_id.py` (new)
- `handovers/techdebt_march_2026.md` (resolved table)
