# Handover 0824: Closeout Self-Decommission Guard

**Date:** 2026-03-18
**From Agent:** Research Session (Claude Code)
**To Agent:** Next Session
**Priority:** High
**Estimated Complexity:** 2-3 hours
**Status:** Complete
**Edition Scope:** CE

## Task Summary

Add tool-level guards to prevent orchestrators from accidentally decommissioning themselves during project closeout. The prompt-only mitigation at `prompts.py:773` already warns agents not to call `close_project_and_update_memory(force=true)` before completing themselves, but an orchestrator ignored this and got permanently locked out (execution set to "decommissioned", `complete_job` then fails with generic "No active execution found"). This handover hardens the tools themselves so the failure is impossible regardless of agent behavior.

## Context and Background

### The Bug (Observed in Production Run)

1. Orchestrator called `close_project_and_update_memory(force=true)` BEFORE `complete_job()`
2. `_force_decommission_agents()` set ALL active agents to "decommissioned" -- including the orchestrator itself
3. Orchestrator then called `complete_job()` -- query filters `status.not_in(["complete", "decommissioned"])` found nothing
4. `ResourceNotFoundError("No active execution found")` -- orchestrator permanently locked out
5. Final state: execution "decommissioned" (not "completed"), AgentJob stuck as "active"

### Why Prompt Copy Failed

The termination prompt (`prompts.py:773`) says: *"CRITICAL: Do NOT call close_project_and_update_memory(). Calling it with force=true will decommission you before you can self-complete."*

The agent ignored this. Prompt-only guards are soft constraints that LLMs can and do violate. Tool-level enforcement is the only reliable protection.

### Existing Closeout Flows (All Compatible)

| Flow | Trigger | Memory Tool Used | Affected by this fix? |
|------|---------|-----------------|----------------------|
| Stop Project | `JobsTab.vue:770` -> termination prompt | `write_360_memory` | No (doesn't use `close_project_and_update_memory`) |
| Handover | `JobsTab.vue:738` -> simple_handover API | `write_360_memory` | No (doesn't use `close_project_and_update_memory`) |
| Manual Closeout (UI) | `ManualCloseoutModal.vue` -> REST API | `projects.completeWithData()` | No (REST endpoint, not MCP tool) |
| CloseoutModal (UI) | `CloseoutModal.vue` -> `projects.archive()` | REST API | No |
| Normal Agent Completion | Agent-initiated | `close_project_and_update_memory` | Yes -- guard catches incorrect ordering |

## Technical Details

### Fix 1 (Primary): Pre-flight guard in `close_project_and_update_memory`

**File:** `src/giljo_mcp/tools/project_closeout.py`
**Location:** Between lines 136-137 (after readiness check, before `_force_decommission_agents`)

**Current code (lines 136-144):**
```python
if not is_ready and force:
    decommissioned = await _force_decommission_agents(active_session, project_id, tenant_key)
    if decommissioned:
        logger.warning(...)
```

**Required change:** Before calling `_force_decommission_agents`, query for an active orchestrator execution. If found, raise `ProjectStateError` with a structured error that tells the agent exactly what to do instead.

```python
if not is_ready and force:
    # Guard: Block force-close if orchestrator is still active
    # The calling orchestrator would decommission itself, making complete_job() impossible
    orch_stmt = (
        select(AgentExecution)
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(
            and_(
                AgentJob.project_id == project_id,
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.status.in_(_ACTIVE_STATUSES),
            )
        )
    )
    orch_result = await active_session.execute(orch_stmt)
    active_orchestrator = orch_result.scalar_one_or_none()

    if active_orchestrator:
        raise ProjectStateError(
            "Cannot force-close: orchestrator is still active and would be decommissioned",
            context={
                "status": "ORCHESTRATOR_SELF_DECOMMISSION_BLOCKED",
                "message": (
                    "force=true will decommission ALL active agents including the orchestrator. "
                    "Complete your own job first, then the project will close cleanly."
                ),
                "required_sequence": [
                    f"1. complete_job(job_id='{active_orchestrator.job_id}') -- complete yourself first",
                    "2. write_360_memory(...) -- write memory entry (if not already written)",
                    "3. close_project_and_update_memory(force=false) -- should now pass since all agents are complete",
                ],
                "hint": "Or use write_360_memory() + complete_job() and let the frontend handle project archival.",
            },
        )

    decommissioned = await _force_decommission_agents(active_session, project_id, tenant_key)
    ...
```

### Fix 2 (Diagnostic): Better error in `complete_job` for decommissioned executions

**File:** `src/giljo_mcp/services/orchestration_service.py`
**Location:** Around line 1657 (after execution query returns None, inside the `else` branch around line 1842)

**Current behavior:** When no active execution found, raises `ResourceNotFoundError("No active execution found for job {job_id}")` -- generic, unhelpful.

**Required change:** Before raising the generic error, check if a decommissioned execution exists for this job. If so, return a specific error explaining the cause:

```python
# Check if execution was decommissioned (better error for self-decommission scenario)
decomm_stmt = (
    select(AgentExecution)
    .where(
        AgentExecution.job_id == job_id,
        AgentExecution.tenant_key == tenant_key,
        AgentExecution.status == "decommissioned",
    )
    .order_by(AgentExecution.started_at.desc())
    .limit(1)
)
decomm_res = await session.execute(decomm_stmt)
decommissioned_exec = decomm_res.scalar_one_or_none()

if decommissioned_exec:
    raise ResourceNotFoundError(
        message=(
            f"Job {job_id} was decommissioned and cannot transition to 'completed'. "
            f"This typically happens when close_project_and_update_memory(force=true) "
            f"was called before complete_job()."
        ),
        context={
            "job_id": job_id,
            "method": "complete_job",
            "execution_status": "decommissioned",
            "cause": "Project was force-closed before this job called complete_job()",
        },
    )
```

### Fix 3 (Diagnostic): Same pattern in `report_progress`

**File:** `src/giljo_mcp/services/orchestration_service.py`
**Location:** Around line 1381 (similar pattern -- after execution query returns None)

Same check: if execution is decommissioned, explain why instead of generic error. Find the exact error handling location in `report_progress` where it raises `ResourceNotFoundError` when no active execution is found, and add the same decommissioned-check pattern.

## Implementation Plan

### Phase 1: Pre-flight guard (Fix 1)

1. Read `project_closeout.py` fully (already done in research)
2. Write test: `test_force_close_blocked_when_orchestrator_active` -- call `close_project_and_update_memory(force=true)` with a working orchestrator, assert `ProjectStateError` with `ORCHESTRATOR_SELF_DECOMMISSION_BLOCKED`
3. Write test: `test_force_close_allowed_when_only_non_orchestrator_active` -- ensure force=true still works for stuck non-orchestrator agents
4. Write test: `test_force_close_allowed_when_orchestrator_already_complete` -- force=true works if orchestrator is "complete" but other agents are stuck
5. Implement the guard in `close_project_and_update_memory`
6. Verify all 3 tests pass

### Phase 2: Diagnostic errors (Fixes 2 & 3)

1. Find the exact error-raise location in `complete_job` (around line 1842 in the `else` branch)
2. Write test: `test_complete_job_decommissioned_gives_specific_error` -- decommission an execution, call complete_job, assert error message mentions "decommissioned"
3. Implement the decommissioned check in `complete_job`
4. Find the equivalent location in `report_progress`
5. Write test: `test_report_progress_decommissioned_gives_specific_error`
6. Implement the decommissioned check in `report_progress`

### Phase 3: Verification

1. Run full test suite to check for regressions
2. Verify the existing 61 tenant isolation tests still pass
3. Verify no lint issues

**Recommended Sub-Agent:** `tdd-implementor` (TDD workflow with clear test-first approach)

## Testing Requirements

### Unit/Integration Tests (TDD -- write FIRST)

| Test Name | What It Validates |
|-----------|------------------|
| `test_force_close_blocked_when_orchestrator_active` | Guard blocks force=true when orchestrator is working |
| `test_force_close_allowed_when_only_specialists_active` | Guard allows force=true when only non-orchestrator agents stuck |
| `test_force_close_allowed_when_orchestrator_complete` | Guard doesn't trigger when orchestrator already completed |
| `test_force_close_error_includes_orchestrator_job_id` | Error context has job_id for remediation |
| `test_complete_job_decommissioned_specific_error` | Decommissioned execution returns descriptive error, not generic |
| `test_report_progress_decommissioned_specific_error` | Same for report_progress |

### Test File Location

Place tests in existing test files that cover these tools:
- Closeout guard tests: find existing `project_closeout` test file or create `tests/test_closeout_guard.py`
- Diagnostic error tests: add to existing orchestration_service tests

## Dependencies and Blockers

**Dependencies:** None -- all target files exist and are stable.
**Blockers:** None.
**Database changes:** None.
**Migration:** None.
**Frontend changes:** None.
**Installation impact:** None.

## Success Criteria

1. An orchestrator calling `close_project_and_update_memory(force=true)` while its own execution is active gets a `ProjectStateError` with `ORCHESTRATOR_SELF_DECOMMISSION_BLOCKED` status and actionable remediation steps
2. `force=true` still works when only non-orchestrator agents are stuck (no orchestrator in active status)
3. `complete_job()` on a decommissioned execution returns an error mentioning "decommissioned" and the likely cause, not "No active execution found"
4. `report_progress()` on a decommissioned execution returns similar descriptive error
5. All existing tests pass (no regressions)
6. Zero lint issues

## Rollback Plan

All changes are additive guards (pre-flight checks and better error messages). To rollback:
- Revert the guard in `project_closeout.py` (remove the orchestrator check block)
- Revert the decommissioned checks in `orchestration_service.py` (restore generic error)
- No database or schema changes to revert

## Key Files

| File | Change |
|------|--------|
| `src/giljo_mcp/tools/project_closeout.py` | Add orchestrator guard before `_force_decommission_agents()` |
| `src/giljo_mcp/services/orchestration_service.py` | Better error in `complete_job` (~L1842) and `report_progress` (~L1381) for decommissioned executions |
| `tests/test_closeout_guard.py` (new) | TDD tests for the guard and diagnostic errors |

## Additional Resources

- Serena memory: `closeout_flow_deep_research_2026_03_18` -- full research with file paths and line numbers
- Related handovers: 0498 (Early Termination Protocol), 0491 (Agent Status Simplification), 0819a (Closeout UI State)
- Status values: `_ACTIVE_STATUSES = {"waiting", "working", "blocked", "silent"}` (project_closeout.py:230)
- Agent model: `src/giljo_mcp/models/agent_identity.py` -- AgentJob (3 statuses), AgentExecution (6 statuses)
