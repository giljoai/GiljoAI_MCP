# Handover 0367c-2: Tools & Prompt Generation MCPAgentJob Cleanup

**Date**: 2025-12-21
**Status**: Pending
**Priority**: HIGH
**Estimated Time**: 2-3 hours
**Dependencies**:
- Handover 0367a (Service Layer Cleanup) - COMPLETE
- Handover 0367b (API Endpoint Migration) - COMPLETE
- Handover 0367c-1 (Monitoring & Orchestration Cleanup) - MUST BE COMPLETE
- 0358_model_mapping_reference.md - COMPLETE

---

## Overview

Clean up the remaining MCPAgentJob references in MCP tools and thin client prompt generation. This is part 2 of the 0367c Tools & Monitoring cleanup, focusing on lower-priority files with fewer references but critical functionality.

**Rationale for Split**:
- 0367c-1 handled the high-complexity, high-reference files (orchestrator.py, agent_health_monitor.py)
- 0367c-2 handles the remaining tools and utilities with simpler patterns
- Splitting enables parallel execution and reduces cognitive load per handover

**Current State**:
- 9 files contain MCPAgentJob references (~49 total refs)
- Tools provide MCP functions for agent coordination
- Thin prompt generator has fallback logic to MCPAgentJob
- Staging rollback queries legacy tables

**Target State**:
- All MCP tools return AgentJob + AgentExecution data
- Thin prompt generator uses AgentJob exclusively (no fallback)
- Staging rollback soft-deletes AgentExecution records
- Zero MCPAgentJob references in tools/utilities

---

## Files to Modify

| File | Refs | Action | Complexity | Priority |
|------|------|--------|------------|----------|
| `src/giljo_mcp/staging_rollback.py` | 18 | Fix rollback queries | MEDIUM | P0 |
| `src/giljo_mcp/thin_prompt_generator.py` | 17 | Remove fallback logic | MEDIUM | P0 |
| `src/giljo_mcp/tools/orchestration.py` | 4 | Update MCP tool responses | LOW | P1 |
| `src/giljo_mcp/tools/agent_coordination.py` | 3 | Fix coordination queries | LOW | P1 |
| `src/giljo_mcp/tools/__init__.py` | 2 | Update exports | LOW | P1 |
| `src/giljo_mcp/tools/tool_accessor.py` | 2 | Update imports | LOW | P1 |
| `src/giljo_mcp/tools/agent_status.py` | 1 | Fix status queries | LOW | P2 |
| `src/giljo_mcp/tools/optimization.py` | 1 | Update context tracking | LOW | P2 |
| `src/giljo_mcp/tools/project.py` | 1 | Fix project queries | LOW | P2 |

**Total**: 9 files, ~49 references

---

## Implementation Steps

### Step 1: Fix staging_rollback.py (45 minutes)

**Target**: Orchestrator staging rollback operations (18 refs)

**Current Pattern**: Rollback deletes MCPAgentJob records created during staging

```python
# BEFORE
from src.giljo_mcp.models import MCPAgentJob

async def rollback_staging(session, orchestrator_job_id: int, tenant_key: str):
    # Find all agents spawned by orchestrator
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.spawned_by == orchestrator_job_id,
        MCPAgentJob.tenant_key == tenant_key
    )
    result = await session.execute(stmt)
    children = result.scalars().all()

    # Delete children
    for child in children:
        await session.delete(child)

    # Delete orchestrator
    orchestrator = await session.get(MCPAgentJob, orchestrator_job_id)
    if orchestrator:
        await session.delete(orchestrator)

    await session.commit()
```

**New Pattern**: Rollback soft-deletes AgentExecution records (preserve AgentJob history)

```python
# AFTER
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from sqlalchemy.orm import joinedload

async def rollback_staging(session, orchestrator_agent_id: str, tenant_key: str):
    """Soft-delete all agents spawned during staging orchestrator setup.

    Args:
        orchestrator_agent_id: UUID string of orchestrator work order
        tenant_key: Tenant isolation key
    """
    # Find all agents spawned by orchestrator
    stmt = (
        select(AgentExecution)
        .where(
            AgentExecution.spawned_by == orchestrator_agent_id,
            AgentExecution.tenant_key == tenant_key
        )
    )
    result = await session.execute(stmt)
    children = result.scalars().all()

    # Soft-delete children (set status = "cancelled")
    for child in children:
        child.status = "cancelled"
        child.failure_reason = "Rollback: staging orchestrator failed"

    # Soft-delete orchestrator execution
    orch_stmt = (
        select(AgentExecution)
        .where(
            AgentExecution.agent_id == orchestrator_agent_id,
            AgentExecution.tenant_key == tenant_key
        )
    )
    orch_result = await session.execute(orch_stmt)
    orchestrator = orch_result.scalar_one_or_none()

    if orchestrator:
        orchestrator.status = "cancelled"
        orchestrator.failure_reason = "Rollback: staging failed"

    await session.commit()
```

**Key Changes**:
1. **Soft Delete**: Set status = "cancelled" instead of DELETE
2. **Preserve History**: AgentJob records remain (work order history)
3. **Parameter**: orchestrator_job_id (int) → orchestrator_agent_id (str, UUID)
4. **Query**: Use spawned_by (UUID) to find children
5. **Error Message**: Document rollback reason in failure_reason field

**Actions**:
1. Replace hard deletes with soft deletes (status update)
2. Update parameter types (int → str for UUID)
3. Add failure_reason field population
4. Preserve AgentJob records (only update AgentExecution)
5. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/services/test_staging_rollback.py -v`
- Test rollback doesn't delete AgentJob records
- Verify cancelled agents not visible in active queries (status != "cancelled")

---

### Step 2: Remove Fallback in thin_prompt_generator.py (45 minutes)

**Target**: Legacy fallback logic in thin client prompt generation (17 refs)

**Current Pattern**: Generator falls back to MCPAgentJob if AgentJob not found

```python
# BEFORE
from src.giljo_mcp.models import AgentJob, MCPAgentJob

class ThinClientPromptGenerator:
    async def generate_prompt(self, session, agent_id: str, tenant_key: str):
        # Try new model first
        agent_job = await session.get(AgentJob, agent_id)

        if not agent_job:
            # Fallback to legacy model
            try:
                legacy_id = int(agent_id)  # Attempt conversion
                mcp_job = await session.get(MCPAgentJob, legacy_id)
                if mcp_job:
                    # Convert legacy to new format
                    return self._build_legacy_prompt(mcp_job)
            except (ValueError, TypeError):
                pass

            raise ValueError(f"Agent {agent_id} not found")
```

**New Pattern**: Generator uses AgentJob + AgentExecution exclusively (no fallback)

```python
# AFTER
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from sqlalchemy.orm import joinedload

class ThinClientPromptGenerator:
    async def generate_prompt(self, session, agent_id: str, tenant_key: str):
        """Generate thin client prompt for agent.

        Args:
            agent_id: UUID string of agent work order
            tenant_key: Tenant isolation key

        Returns:
            Thin client prompt string

        Raises:
            ValueError: If agent not found
        """
        # Fetch AgentJob with execution details
        stmt = (
            select(AgentJob)
            .options(joinedload(AgentJob.executions))
            .where(
                AgentJob.id == agent_id,
                AgentJob.tenant_key == tenant_key
            )
        )
        result = await session.execute(stmt)
        agent_job = result.scalar_one_or_none()

        if not agent_job:
            raise ValueError(f"Agent {agent_id} not found")

        # Get latest execution
        execution = (
            agent_job.executions[0]
            if agent_job.executions
            else None
        )

        return self._build_prompt(agent_job, execution)
```

**Key Changes**:
1. **Remove Fallback**: No MCPAgentJob lookup
2. **Error Handling**: Raise immediately if not found
3. **Simplicity**: Single model, single code path
4. **Type Safety**: agent_id is UUID string (not int conversion)

**Actions**:
1. Remove all MCPAgentJob fallback logic
2. Remove try/except blocks for legacy conversion
3. Update error messages (no "legacy" mentions)
4. Remove MCPAgentJob import
5. Update docstrings to reflect UUID-only parameters

**Validation**:
- Run `pytest tests/services/test_thin_prompt_generator.py -v`
- Verify ValueError raised for invalid agent_id
- Test prompt generation with valid agent_id (UUID)
- Verify no integer conversion attempts

---

### Step 3: Update tools/orchestration.py (30 minutes)

**Target**: MCP tools for orchestrator coordination (4 refs)

**Tools to Migrate**:

1. **`get_orchestrator_instructions(orchestrator_id, tenant_key)`**:
   ```python
   # BEFORE
   from src.giljo_mcp.models import MCPAgentJob
   job = await session.get(MCPAgentJob, orchestrator_id)
   return {"mission": job.mission_text}

   # AFTER
   from src.giljo_mcp.models.agent_identity import AgentJob
   agent_job = await session.get(AgentJob, orchestrator_id)
   return {"mission": agent_job.mission}
   ```

2. **`get_available_agents(tenant_key, active_only)`**:
   ```python
   # BEFORE
   stmt = select(MCPAgentJob).where(MCPAgentJob.tenant_key == tenant_key)
   if active_only:
       stmt = stmt.where(MCPAgentJob.status == "running")

   # AFTER
   from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
   stmt = (
       select(AgentExecution)
       .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
       .where(AgentJob.tenant_key == tenant_key)
   )
   if active_only:
       stmt = stmt.where(AgentExecution.status == "working")
   ```

**Actions**:
1. Replace MCPAgentJob queries with AgentJob + AgentExecution
2. Update return types (job_id → agent_id, int → str for JSON)
3. Update field names (mission_text → mission)
4. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/tools/test_orchestration.py -v`
- Test MCP tool calls via HTTP endpoint (/mcp)
- Verify JSON responses use agent_id (str, UUID)

---

### Step 4: Fix tools/agent_coordination.py (20 minutes)

**Target**: Agent-to-agent coordination MCP tools (3 refs)

**Tools to Migrate**:

1. **`check_peer_status(agent_id, tenant_key)`**:
   ```python
   # BEFORE
   from src.giljo_mcp.models import MCPAgentJob
   job = await session.get(MCPAgentJob, int(agent_id))
   return {"status": job.status}

   # AFTER
   from src.giljo_mcp.models.agent_identity import AgentExecution
   stmt = select(AgentExecution).where(
       AgentExecution.agent_id == agent_id,
       AgentExecution.tenant_key == tenant_key
   )
   result = await session.execute(stmt)
   execution = result.scalar_one_or_none()
   return {"status": execution.status if execution else "not_found"}
   ```

2. **`send_message_to_agent(recipient_agent_id, message, ...)`**:
   - Already uses agent_id (UUID) from 0367a migration
   - Verify no MCPAgentJob lookups for validation

**Actions**:
1. Replace MCPAgentJob status queries with AgentExecution queries
2. Remove integer conversion of agent_id
3. Verify message routing uses agent_id (UUID)
4. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/tools/test_agent_coordination.py -v`
- Test send_message with valid/invalid agent_id
- Test check_peer_status returns correct status

---

### Step 5: Update tools/__init__.py (10 minutes)

**Target**: Tool module exports (2 refs)

**Current Pattern**: May have MCPAgentJob imports for type hints

```python
# BEFORE
from src.giljo_mcp.models import MCPAgentJob
from typing import List

def get_all_jobs() -> List[MCPAgentJob]:
    ...
```

**New Pattern**: Use AgentJob + AgentExecution for type hints

```python
# AFTER
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from typing import List, Tuple

def get_all_jobs() -> List[Tuple[AgentJob, AgentExecution]]:
    ...
```

**Actions**:
1. Update import statements
2. Update type hints to use new models
3. Verify __all__ exports don't reference MCPAgentJob

**Validation**:
- Run `pytest tests/tools/ -v`
- Verify no import errors

---

### Step 6: Update tools/tool_accessor.py (10 minutes)

**Target**: Tool accessor base class (2 refs)

**Current Pattern**: May use MCPAgentJob for validation

```python
# BEFORE
from src.giljo_mcp.models import MCPAgentJob

class ToolAccessor:
    async def validate_agent(self, session, job_id: int):
        job = await session.get(MCPAgentJob, job_id)
        return job is not None
```

**New Pattern**: Use AgentJob for validation

```python
# AFTER
from src.giljo_mcp.models.agent_identity import AgentJob

class ToolAccessor:
    async def validate_agent(self, session, agent_id: str):
        agent_job = await session.get(AgentJob, agent_id)
        return agent_job is not None
```

**Actions**:
1. Replace MCPAgentJob validation with AgentJob validation
2. Update parameter types (job_id: int → agent_id: str)
3. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/tools/test_tool_accessor.py -v`
- Verify validation works with UUID strings

---

### Step 7: Fix tools/agent_status.py (10 minutes)

**Target**: Agent status MCP tools (1 ref)

**Pattern**: Simple status query migration

```python
# BEFORE
from src.giljo_mcp.models import MCPAgentJob
stmt = select(MCPAgentJob.status).where(MCPAgentJob.job_id == job_id)

# AFTER
from src.giljo_mcp.models.agent_identity import AgentExecution
stmt = select(AgentExecution.status).where(AgentExecution.agent_id == agent_id)
```

**Actions**:
1. Replace MCPAgentJob query with AgentExecution query
2. Update parameter (job_id → agent_id)
3. Remove MCPAgentJob import

---

### Step 8: Update tools/optimization.py (10 minutes)

**Target**: Context optimization tracking (1 ref)

**Pattern**: Update context usage tracking

```python
# BEFORE
from src.giljo_mcp.models import MCPAgentJob
job = await session.get(MCPAgentJob, job_id)
job.context_used = context_used

# AFTER
from src.giljo_mcp.models.agent_identity import AgentExecution
execution = await session.get(AgentExecution, agent_id)
execution.context_used = context_used
```

**Actions**:
1. Replace MCPAgentJob update with AgentExecution update
2. Update parameter (job_id → agent_id)
3. Remove MCPAgentJob import

---

### Step 9: Fix tools/project.py (10 minutes)

**Target**: Project-related MCP tools (1 ref)

**Pattern**: Project query migration

```python
# BEFORE
from src.giljo_mcp.models import MCPAgentJob
stmt = select(func.count(MCPAgentJob.job_id)).where(
    MCPAgentJob.project_id == project_id
)

# AFTER
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
stmt = (
    select(func.count(AgentExecution.id))
    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
    .where(AgentJob.project_id == project_id)
)
```

**Actions**:
1. Replace MCPAgentJob count with AgentExecution count
2. Add AgentJob join for project_id filter
3. Remove MCPAgentJob import

---

## Success Criteria

### Code Quality
- [ ] Zero `MCPAgentJob` imports in all 9 target files
- [ ] Zero `mcp_agent_jobs` table queries in tools/utilities
- [ ] All MCP tools use agent_id (UUID string) parameters
- [ ] All type hints use AgentJob + AgentExecution

### Functional Validation
- [ ] Staging rollback soft-deletes executions (preserves jobs)
- [ ] Thin client prompts use AgentJob exclusively (no fallback)
- [ ] MCP tools return agent_id (str, UUID) in JSON responses
- [ ] Tool accessor validates with UUID strings
- [ ] Context tracking updates AgentExecution.context_used

### MCP Tool Validation
- [ ] `get_orchestrator_instructions()` returns mission from AgentJob
- [ ] `get_available_agents()` queries AgentExecution for active agents
- [ ] `check_peer_status()` returns status from AgentExecution
- [ ] All tools handle invalid agent_id gracefully

### Testing
- [ ] `pytest tests/services/test_staging_rollback.py` passes
- [ ] `pytest tests/services/test_thin_prompt_generator.py` passes
- [ ] `pytest tests/tools/` passes (all modules)
- [ ] No test failures due to missing MCPAgentJob

---

## Field Mapping Reference (Quick Lookup)

| MCPAgentJob Field | AgentJob Field | AgentExecution Field | Notes |
|-------------------|----------------|----------------------|-------|
| `job_id` (int) | - | `id` (int) | Executor instance ID |
| - | `id` (UUID) | `agent_id` (UUID) | Work order ID |
| `project_id` | `project_id` | - | Product association |
| `agent_type` | `job_type` | `agent_type` | WHAT vs WHO |
| `mission_text` | `mission` | - | Instructions (stored once) |
| `status` | `status` (3 values) | `status` (7 values) | Different enums |
| `spawned_by` (int) | - | `spawned_by` (UUID) | Now agent_id, not job_id |
| `succeeded_by` (int) | - | `succeeded_by` (UUID) | Now agent_id, not job_id |
| `context_used` | - | `context_used` | Per-execution metric |
| `context_budget` | - | `context_budget` | Per-execution limit |
| `failure_reason` | - | `failure_reason` | Execution-level |

**Full Reference**: [0358_model_mapping_reference.md](Reference_docs/0358_model_mapping_reference.md)

---

## Code Patterns

### Pattern 1: Query for Agent Data (READ)

**OLD (MCPAgentJob):**
```python
from src.giljo_mcp.models import MCPAgentJob

stmt = select(MCPAgentJob).where(
    MCPAgentJob.job_id == job_id,
    MCPAgentJob.tenant_key == tenant_key,
)
result = await session.execute(stmt)
job = result.scalar_one_or_none()
```

**NEW (AgentExecution with Job):**
```python
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from sqlalchemy.orm import joinedload

stmt = (
    select(AgentExecution)
    .options(joinedload(AgentExecution.job))
    .where(
        AgentExecution.agent_id == agent_id,  # UUID string
        AgentExecution.tenant_key == tenant_key,
    )
)
result = await session.execute(stmt)
execution = result.scalar_one_or_none()

# Access job data via relationship
mission = execution.job.mission
project_id = execution.job.project_id
```

### Pattern 2: Soft Delete (Rollback)

**OLD (MCPAgentJob):**
```python
job = await session.get(MCPAgentJob, job_id)
await session.delete(job)  # Hard delete
```

**NEW (AgentExecution):**
```python
execution = await session.get(AgentExecution, agent_id)
execution.status = "cancelled"
execution.failure_reason = "Rollback: staging failed"
# AgentJob remains for history
```

### Pattern 3: MCP Tool Response

**OLD (MCPAgentJob):**
```python
return {
    "job_id": job.job_id,  # int
    "status": job.status,
    "mission": job.mission_text
}
```

**NEW (AgentJob + AgentExecution):**
```python
return {
    "agent_id": str(agent_job.id),  # UUID as string
    "status": execution.status,
    "mission": agent_job.mission
}
```

---

## Rollback Plan

### If Issues Arise During Migration
1. **Stop immediately** - Do not proceed to next file
2. **Revert commits** - `git reset --hard HEAD~N` (N = commits since 0367c-2 start)
3. **Verify dependencies** - Ensure 0367a/0367b/0367c-1 intact (don't revert those)
4. **Restart server** - Clear MCP tool cache
5. **Test MCP endpoints** - Verify /mcp still functional

### If Issues Arise After Completion
1. **Revert entire handover** - `git revert <commit-hash>`
2. **Rollback previous handovers if needed** - If cascading failures
3. **Document failure** - Record specific issue in handover notes
4. **Plan retry** - Address root cause before re-attempting

**Recovery Time**: <10 minutes (Git revert + server restart)

**Data Loss Risk**: LOW (tools are stateless; rollback only undoes queries)

---

## Testing Strategy

### Unit Tests
- Run file-specific test files after each step
- Verify MCP tool responses match expected schema
- Check error handling (invalid agent_id, not found)
- Test soft delete (status update, not record deletion)

### Integration Tests
- Test staging rollback workflow: spawn → fail → rollback
- Verify thin client prompts work with UUID agent_id
- Test MCP tool calls via HTTP endpoint (/mcp)

### Manual Testing Checklist
- [ ] Create orchestrator → trigger rollback → verify soft delete
- [ ] Generate thin client prompt with UUID agent_id → verify no fallback
- [ ] Call MCP tools via /mcp endpoint → verify agent_id in responses
- [ ] Check cancelled agents not visible in active queries

---

## Notes

### Why Split 0367c into Two Parts?

**0367c-1 (Monitoring & Orchestration)**:
- High complexity: orchestrator.py (21 refs), agent_health_monitor.py (23 refs)
- Core orchestration logic (spawning, succession)
- Est: 4-5 hours

**0367c-2 (Tools & Prompt Generation)**:
- Lower complexity: 9 files with 1-18 refs each
- Utility functions and MCP tool wrappers
- Est: 2-3 hours

**Benefit**: Parallel execution possible, clearer scope per handover

### Why Soft Delete in Rollback?

- **History**: Preserve work order history (AgentJob) for debugging
- **Auditability**: Track why staging failed (failure_reason field)
- **Queries**: Cancelled agents excluded from active queries (status != "cancelled")
- **Forensics**: Can review failed staging attempts in database

### Thin Prompt Generator No Fallback?

- **After 0367a/0367b**: All creation paths use AgentJob + AgentExecution
- **No Legacy Data**: MCPAgentJob table only has historical records
- **Fail Fast**: ValueError if agent not found (better than silent fallback)
- **Type Safety**: No integer conversion attempts (UUID strings only)

### Performance Considerations

- **Joins**: Tools query join AgentJob + AgentExecution (~1-2ms overhead)
- **Indexes**: Ensure indexes on agent_executions.agent_id, agent_jobs.id
- **MCP Tools**: Stateless, no caching; overhead negligible
- **Soft Delete**: UPDATE faster than DELETE (no cascade checks)

---

## Related Documentation

- [0358_model_mapping_reference.md](Reference_docs/0358_model_mapping_reference.md) - Complete field mapping
- [0367_kickoff.md](0367_kickoff.md) - Series overview
- [0367a_service_layer_cleanup.md](0367a_service_layer_cleanup.md) - Service layer patterns
- [0367b_api_endpoint_migration.md](0367b_api_endpoint_migration.md) - API endpoint patterns
- [0367c_tools_monitoring_cleanup.md](0367c_tools_monitoring_cleanup.md) - Original 0367c (now split)
- [docs/ORCHESTRATOR.md](../docs/ORCHESTRATOR.md) - Orchestrator lifecycle
- [docs/api/mcp_tools.md](../docs/api/mcp_tools.md) - MCP tool reference

---

**Next Step**: After completion, update 0367_kickoff.md handover notes and proceed to Handover 0367d (Validation & Deprecation)
