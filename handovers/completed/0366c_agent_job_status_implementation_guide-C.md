# Agent Job Status Tool Implementation Guide

**Handover**: 0366c
**Phase**: C - MCP Tool Standardization
**Component**: `src/giljo_mcp/tools/agent_job_status.py`
**Test File**: `tests/tools/test_agent_job_status_0366c.py`
**Status**: RED Phase Complete (12 failing tests)

## Overview

Refactor agent job status tools to enforce semantic clarity between work orders (jobs) and executors (agents).

## Current State (Before Refactor)

**Existing Tool**:
- `update_job_status(job_id, tenant_key, new_status, reason)` - Updates job status

**Issues**:
1. No read-only status query tools
2. Parameter naming ambiguous (`job_id` could mean work order OR executor)
3. Response doesn't include both identifiers
4. No way to query executor-specific status

## Target State (After Refactor)

**New Tools**:
1. `get_job_status(job_id, tenant_key)` - Query work order status (WHAT)
2. `get_agent_status(agent_id, tenant_key)` - Query executor status (WHO)

**Enhanced Tool**:
3. `update_job_status(job_id, tenant_key, new_status, reason)` - Update work order (clarified semantics)

## Semantic Contract

```python
# WHAT - Work order (persists across succession)
job_id = "build-auth"           # Work to be done
get_job_status(job_id) → {
    "job_id": "build-auth",
    "status": "active",         # Work order still in progress
    "job_type": "orchestrator",
    "executions": [             # All executor instances
        {"agent_id": "orch-001", "status": "complete"},
        {"agent_id": "orch-002", "status": "working"}
    ]
}

# WHO - Executor instance (changes on succession)
agent_id = "orch-002"           # Specific executor
get_agent_status(agent_id) → {
    "agent_id": "orch-002",
    "job_id": "build-auth",     # Context: which work order
    "status": "working",        # Executor status
    "instance_number": 2,
    "progress": 45,
    "current_task": "Implementing OAuth2",
    "spawned_by": "orch-001"    # Succession chain
}
```

## Implementation Tasks

### 1. Add `get_job_status()` Tool

**Location**: `src/giljo_mcp/tools/agent_job_status.py`

```python
@mcp.tool()
async def get_job_status(
    job_id: str,
    tenant_key: str,
) -> dict[str, Any]:
    """
    Query work order status (job-level).

    Returns:
    - job_id: Work order UUID
    - status: Job status (active, completed, cancelled)
    - job_type: Job type
    - created_at: Job creation timestamp
    - executions: List of all executor instances (optional)
    - current_agent_id: Current executor ID (if active)
    """
```

**Database Query**:
- Table: `agent_jobs`
- Filter: `job_id` + `tenant_key`
- Optional: Join with `agent_executions` for execution history

### 2. Add `get_agent_status()` Tool

**Location**: `src/giljo_mcp/tools/agent_job_status.py`

```python
@mcp.tool()
async def get_agent_status(
    agent_id: str,
    tenant_key: str,
) -> dict[str, Any]:
    """
    Query executor status (execution-level).

    Returns:
    - agent_id: Executor UUID
    - job_id: Work order UUID (context)
    - status: Execution status (waiting, working, blocked, complete, ...)
    - agent_type: Agent type
    - instance_number: Sequential instance
    - progress: Completion percentage (0-100)
    - current_task: Current task description
    - spawned_by: Parent executor ID (succession)
    - succeeded_by: Successor executor ID (if decommissioned)
    - started_at: Execution start timestamp
    - completed_at: Execution completion timestamp
    - decommissioned_at: Decommission timestamp
    """
```

**Database Query**:
- Table: `agent_executions`
- Filter: `agent_id` + `tenant_key`

### 3. Update `update_job_status()` Response

**Enhancement**: Add both identifiers to response

```python
# Current response (job_id only)
{
    "success": True,
    "job_id": "...",
    "old_status": "...",
    "new_status": "...",
}

# Enhanced response (clarify scope)
{
    "success": True,
    "job_id": "...",          # Work order affected
    "old_status": "...",
    "new_status": "...",
    "scope": "job",           # Clarify this is job-level update
    "affected_executions": 2  # How many executors affected
}
```

## Test Coverage (12 Tests)

### get_job_status() Tests (3 tests)
1. ✅ `test_get_job_status_returns_work_order_status` - Basic job query
2. ✅ `test_get_job_status_with_multiple_executions` - Job with succession
3. ✅ `test_get_job_status_nonexistent_job` - Error handling

### get_agent_status() Tests (3 tests)
4. ✅ `test_get_agent_status_returns_executor_status` - Basic executor query
5. ✅ `test_get_agent_status_old_executor` - Decommissioned executor
6. ✅ `test_get_agent_status_nonexistent_agent` - Error handling

### Multi-Tenant Isolation Tests (2 tests)
7. ✅ `test_get_job_status_tenant_isolation` - Job query isolation
8. ✅ `test_get_agent_status_tenant_isolation` - Executor query isolation

### Response Schema Tests (2 tests)
9. ✅ `test_update_job_status_uses_job_id_parameter` - Existing tool semantics
10. ✅ `test_response_includes_both_identifiers` - Both IDs in response

### Edge Cases (2 tests)
11. ✅ `test_get_agent_status_with_succession_chain` - Succession tracking
12. ✅ `test_get_job_status_shows_current_executor` - Current executor info

## Database Schema Reference

### AgentJob Table (Work Order)
```sql
CREATE TABLE agent_jobs (
    job_id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    project_id VARCHAR(36),
    mission TEXT NOT NULL,
    job_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',  -- active, completed, cancelled
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    ...
);
```

### AgentExecution Table (Executor)
```sql
CREATE TABLE agent_executions (
    agent_id VARCHAR(36) PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL,  -- FK to agent_jobs
    tenant_key VARCHAR(36) NOT NULL,
    agent_type VARCHAR(100) NOT NULL,
    instance_number INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'waiting',  -- waiting, working, blocked, complete, ...
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    decommissioned_at TIMESTAMP,
    spawned_by VARCHAR(36),      -- Parent executor ID
    succeeded_by VARCHAR(36),    -- Successor executor ID
    progress INTEGER DEFAULT 0,
    current_task TEXT,
    ...
);
```

## Implementation Checklist

### Phase 1: Add Read-Only Tools
- [ ] Implement `get_job_status()` tool
  - [ ] Query `agent_jobs` table
  - [ ] Filter by `job_id` + `tenant_key`
  - [ ] Return job-level status
  - [ ] Optional: Include execution list
- [ ] Implement `get_agent_status()` tool
  - [ ] Query `agent_executions` table
  - [ ] Filter by `agent_id` + `tenant_key`
  - [ ] Return execution-level status
  - [ ] Include succession chain info

### Phase 2: Response Schema Updates
- [ ] Update `update_job_status()` response
  - [ ] Add scope clarification
  - [ ] Add affected execution count
- [ ] Ensure all responses include relevant identifiers
  - [ ] Job queries: `job_id` (primary)
  - [ ] Agent queries: `agent_id` (primary) + `job_id` (context)

### Phase 3: Error Handling
- [ ] Not found errors
- [ ] Tenant isolation enforcement
- [ ] Invalid parameter validation

### Phase 4: Testing
- [ ] Run test suite: `pytest tests/tools/test_agent_job_status_0366c.py -v`
- [ ] Verify all 12 tests pass
- [ ] Check coverage: `pytest --cov=src/giljo_mcp/tools/agent_job_status`

## Success Criteria

1. All 12 tests pass (GREEN phase)
2. Response schemas include both identifiers where meaningful
3. Multi-tenant isolation enforced
4. Clear semantic distinction: job_id (WHAT) vs agent_id (WHO)
5. Backward compatibility: `update_job_status()` still works

## Notes

- This is part of Agent Identity Refactor Series (0366a-d)
- Phase A: Database models (AgentJob + AgentExecution) - COMPLETE
- Phase B: Service layer refactor - COMPLETE
- **Phase C: MCP Tool Standardization - IN PROGRESS**
- Phase D: Frontend migration - PENDING

## Related Files

- Models: `src/giljo_mcp/models/agent_identity.py`
- Services: `src/giljo_mcp/services/agent_job_service_0366b.py`
- Tests: `tests/tools/test_agent_job_status_0366c.py`
- Documentation: `handovers/completed/0366a_agent_identity_models.md`
