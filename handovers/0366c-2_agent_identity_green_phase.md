# Handover 0366c-2: Agent Identity Refactor - GREEN Phase Completion

**Date**: 2025-12-20
**Phase**: Continuation of 0366c
**Status**: Ready for Execution
**Estimated Duration**: 4-6 hours
**TDD Approach**: GREEN phase (tests already written, make them pass)
**Dependencies**: 0366c Phase 1 COMPLETE (commit 052b280b)

---

## Context

Handover 0366c was split due to scope. Phase 1 fixed 14 code quality issues and achieved 87% test pass rate. This handover completes the remaining 11 RED phase tests.

## Objective

Make all 11 failing tests pass by implementing the missing AgentJob/AgentExecution integration in:
1. `agent_job_status.py` - 6 tests
2. `project.py` - 5 tests

---

## Failing Tests to Fix

### 1. agent_job_status.py (6 tests)

**File**: `tests/tools/test_agent_job_status_0366c.py`

| Test | What It Expects |
|------|-----------------|
| `test_get_agent_status_returns_executor_status` | Query AgentExecution by agent_id, return status/progress |
| `test_get_agent_status_old_executor` | Find specific executor even after succession |
| `test_get_agent_status_tenant_isolation` | Block cross-tenant access to agent status |
| `test_update_job_status_uses_job_id_parameter` | Update AgentJob status using job_id (not agent_id) |
| `test_response_includes_both_identifiers` | Return both job_id and agent_id in responses |
| `test_get_agent_status_with_succession_chain` | Include succession chain info in status response |

**Implementation Needed**:

```python
# In src/giljo_mcp/tools/agent_job_status.py

async def get_agent_status(
    agent_id: str,  # Executor UUID (the WHO)
    tenant_key: str
) -> dict[str, Any]:
    """Get status of specific agent execution."""
    async with _get_session() as session:
        from sqlalchemy import select
        from giljo_mcp.models.agent_identity import AgentExecution

        result = await session.execute(
            select(AgentExecution).where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant_key
            )
        )
        execution = result.scalar_one_or_none()

        if not execution:
            return {"success": False, "error": f"Agent {agent_id} not found"}

        return {
            "success": True,
            "agent_id": execution.agent_id,
            "job_id": execution.job_id,  # Include work order ID
            "status": execution.status,
            "progress": execution.progress,
            "instance_number": execution.instance_number,
            "spawned_by": execution.spawned_by,
            "succeeded_by": execution.succeeded_by
        }
```

### 2. project.py (5 tests)

**File**: `tests/tools/test_project_0366c.py`

| Test | What It Expects |
|------|-----------------|
| `test_create_project_with_auto_job` | When `auto_create_orchestrator_job=True`, create AgentJob + AgentExecution |
| `test_list_projects_includes_execution_aggregates` | Return job_count, execution_count, active_agents per project |
| `test_project_status_returns_job_and_execution_details` | Nested structure: jobs[] with executions[] |
| `test_close_project_updates_job_and_execution_statuses` | Set job.status=completed, execution.status=decommissioned |
| `test_project_with_multiple_jobs_and_executions` | Handle complex scenarios with multiple jobs/executions |

**Implementation Needed** (already partially done in 0366c, needs verification):

```python
# In src/giljo_mcp/tools/project.py

@mcp.tool()
async def create_project(
    name: str,
    mission: str,
    product_id: Optional[str] = None,
    tenant_key: Optional[str] = None,
    auto_create_orchestrator_job: bool = False,  # NEW PARAMETER
) -> dict[str, Any]:
    """Create project with optional orchestrator job."""
    # ... existing code ...

    if auto_create_orchestrator_job:
        from giljo_mcp.models.agent_identity import AgentJob, AgentExecution

        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_key,
            project_id=project.id,
            mission=mission,
            job_type="orchestrator",
            status="active"
        )
        session.add(job)

        execution = AgentExecution(
            agent_id=str(uuid4()),
            job_id=job.job_id,
            tenant_key=tenant_key,
            agent_type="orchestrator",
            instance_number=1,
            status="waiting"
        )
        session.add(execution)

        result["job_id"] = job.job_id
        result["agent_id"] = execution.agent_id

    return result
```

---

## TDD Approach (GREEN Phase)

Since tests already exist and are RED, your job is:

1. **Read each failing test** to understand expected behavior
2. **Implement minimal code** to make test pass
3. **Run test** to verify GREEN
4. **Repeat** for all 11 tests

### Verification Commands

```bash
# Run specific failing tests
python -m pytest tests/tools/test_agent_job_status_0366c.py -v --no-cov -k "get_agent_status"
python -m pytest tests/tools/test_project_0366c.py -v --no-cov

# Run all 0366c tests
python -m pytest tests/tools/test_*_0366c.py -v --no-cov

# Target: 83/84 tests passing (1 skipped for schema issue)
```

---

## Semantic Contract Reminder

| Parameter | Meaning | Use When |
|-----------|---------|----------|
| **job_id** | Work order UUID | Querying work scope, mission, overall status |
| **agent_id** | Executor UUID | Targeting specific agent instance |
| **project_id** | Workspace UUID | Project-level operations |

---

## Files to Modify

1. `src/giljo_mcp/tools/agent_job_status.py` - Add/update get_agent_status()
2. `src/giljo_mcp/tools/project.py` - Verify/fix AgentJob/AgentExecution integration

---

## Success Criteria

- [ ] All 6 agent_job_status tests pass
- [ ] All 5 project tests pass (except 1 skipped)
- [ ] Total: 83/84 tests passing
- [ ] No regressions in existing tests
- [ ] Code follows semantic contract (job_id vs agent_id)

---

## Reference Documents

- **Memory**: `handover_0366c_completion_status.md` (Serena)
- **Phase 1 Commit**: `052b280b`
- **Original Spec**: `handovers/0366c_mcp_tool_standardization.md`
- **Models**: `src/giljo_mcp/models/agent_identity.py`

---

## Kickoff Prompt

```
Mission: Complete Handover 0366c-2 - GREEN phase for agent identity refactor

Context: 11 failing TDD tests need implementation. Tests are already written (RED phase complete).
Your job is to make them pass with minimal code changes.

Files:
- agent_job_status.py: 6 tests for get_agent_status()
- project.py: 5 tests for AgentJob/AgentExecution integration

Approach:
1. Read failing test
2. Implement minimal code to pass
3. Verify with pytest
4. Repeat

Target: 83/84 tests passing (from current 72/84)

Reference: Read memory file handover_0366c_completion_status.md for context.
```
