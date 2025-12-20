# Test Agent Status 0366c - RED Phase Summary

**Phase**: RED (Failing Tests)
**Handover**: 0366c - Agent Identity Refactor Phase C
**File**: `tests/tools/test_agent_status_0366c.py`
**Status**: 2 tests failing (as expected), 8 tests passing (documentation/database state)

## Purpose

These tests document expected behavior for refactoring `src/giljo_mcp/tools/agent_status.py` to use semantic parameter naming aligned with the AgentJob/AgentExecution dual-model architecture.

## Current vs Expected Behavior

### Current (OLD - uses job_id)
```python
set_agent_status(job_id, tenant_key, status, ...)
report_progress(job_id, tenant_key, progress)
```

### Expected (NEW - uses agent_id)
```python
set_agent_status(agent_id, tenant_key, status, ...)  # Target executor
report_progress(agent_id, tenant_key, progress)       # Target executor
```

## Semantic Contract

- **agent_id** = Executor UUID (the WHO - specific agent instance)
- **job_id** = Work order UUID (the WHAT - persistent across succession)
- **Health monitoring** targets executions (agent_id), not jobs
- **Status updates** target executions (agent_id), not jobs
- **Response includes** both agent_id (executor) and job_id (work order context)

## Test Coverage (10 tests total)

### ✅ Passing Tests (8) - Documentation/Database State

1. **test_health_check_should_use_agent_id**
   - Documents expected health check behavior using agent_id
   - Tests database state directly (not calling tool)

2. **test_health_check_isolates_between_executions**
   - Verifies health status is per-execution (not per-job)
   - Critical: Two executions on same job have different health states

3. **test_set_agent_status_should_use_agent_id**
   - Documents expected status update behavior using agent_id
   - Verifies execution updated, job unchanged

4. **test_set_agent_status_with_progress_requires_agent_id**
   - Tests progress updates are executor-specific

5. **test_status_update_response_includes_both_ids**
   - Documents expected response structure with both agent_id and job_id

6. **test_status_updates_isolated_between_executions**
   - Verifies status updates target specific execution (not all on job)

7. **test_report_progress_should_use_agent_id**
   - Documents expected progress reporting behavior using agent_id

8. **test_expected_tool_signatures_documentation**
   - Documentation test specifying expected API after refactor

### ❌ Failing Tests (2) - Expected Failures (RED Phase)

1. **test_status_update_blocks_cross_tenant_access** ❌
   ```
   TypeError: set_agent_status() got an unexpected keyword argument 'agent_id'
   ```
   - Expected failure: Tool still uses job_id parameter
   - Will pass after refactor to agent_id

2. **test_status_update_handles_nonexistent_agent_id** ❌
   ```
   TypeError: set_agent_status() got an unexpected keyword argument 'agent_id'
   ```
   - Expected failure: Tool still uses job_id parameter
   - Will pass after refactor to agent_id

## Test Scenarios Covered

### 1. Health Monitoring (Executor-Specific)
- Health check targets specific agent_id (executor)
- Health status isolated between executions on same job
- Response includes both agent_id and job_id

### 2. Status Updates (Executor-Specific)
- Status updates target specific agent_id (executor)
- Updates modify AgentExecution (not AgentJob)
- Progress tracking is per-execution
- Job status remains stable when execution status changes

### 3. Response Structure
- All responses include both agent_id and job_id
- agent_id identifies executor (for succession tracking)
- job_id provides work order context (for UI linking)

### 4. Isolation
- Status updates isolated between executions on same job
- Execution 1 updates don't affect Execution 2 (and vice versa)

### 5. Security
- Multi-tenant isolation enforced
- Tenant A cannot update Tenant B's agent status
- tenant_key filtering blocks cross-tenant access

### 6. Error Handling
- Graceful handling of nonexistent agent_id
- Clear error messages for not found cases

## Expected Changes for GREEN Phase

### 1. Parameter Renaming
```python
# agent_status.py
async def set_agent_status(
    agent_id: str,  # Changed from job_id
    tenant_key: str,
    status: str,
    ...
):
```

### 2. Database Lookup Changes
```python
# OLD (current)
stmt = select(Job).where(Job.job_id == job_id, Job.tenant_key == tenant_key)

# NEW (after refactor)
stmt = select(AgentExecution).where(
    AgentExecution.agent_id == agent_id,
    AgentExecution.tenant_key == tenant_key
)
```

### 3. Response Structure Changes
```python
# OLD (current)
return {
    "success": True,
    "job_id": job_id,
    "old_status": old_status,
    "new_status": status,
    ...
}

# NEW (after refactor)
return {
    "success": True,
    "agent_id": execution.agent_id,  # NEW: executor identifier
    "job_id": execution.job_id,       # NEW: work order context
    "old_status": old_status,
    "new_status": status,
    ...
}
```

### 4. Update Target Changes
```python
# OLD (current) - Updates Job table
job.status = status
job.progress = progress

# NEW (after refactor) - Updates AgentExecution table
execution.status = status
execution.progress = progress
# Leave job.status unchanged (job status is stable)
```

## Implementation Checklist for GREEN Phase

- [ ] Rename `job_id` parameter to `agent_id` in `set_agent_status()`
- [ ] Rename `job_id` parameter to `agent_id` in `report_progress()`
- [ ] Change database lookup from `Job` to `AgentExecution`
- [ ] Update WHERE clause to use `AgentExecution.agent_id`
- [ ] Modify response to include both `agent_id` and `job_id`
- [ ] Update field assignments to target `execution.*` (not `job.*`)
- [ ] Update WebSocket events to include both IDs
- [ ] Update tool registration decorator parameters
- [ ] Update docstrings to reflect new semantics
- [ ] Verify all 10 tests pass

## Success Criteria

All 10 tests should pass after refactor:
- 2 currently failing tests will pass (cross-tenant, nonexistent agent)
- 8 currently passing tests will continue to pass (documentation/state)

## Related Files

- **Implementation**: `src/giljo_mcp/tools/agent_status.py`
- **Models**: `src/giljo_mcp/models/agent_identity.py`
- **Service Layer**: `src/giljo_mcp/services/message_service_0366b.py` (reference)
- **Related Tests**: `tests/tools/test_agent_communication_0366c.py` (pattern reference)

## Notes

- Tests use database state verification (not MCP tool calls) for most cases
- Only tests that call the tool directly will fail (expected RED phase behavior)
- After refactor, all tests should pass without modification
- Tests serve as executable documentation of expected behavior
