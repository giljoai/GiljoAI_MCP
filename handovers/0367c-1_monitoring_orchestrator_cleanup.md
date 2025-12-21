# Handover 0367c-1: Monitoring & Orchestrator MCPAgentJob Cleanup (Part 1 of 2)

**Date**: 2025-12-21
**Status**: Pending
**Priority**: HIGH
**Estimated Time**: 2-3 hours
**Dependencies**:
- Handover 0367a (Service Layer Cleanup) - COMPLETE
- Handover 0367b (API Endpoint Migration) - COMPLETE
- 0358_model_mapping_reference.md - COMPLETE

---

## Overview

Clean up MCPAgentJob references in core orchestration and monitoring files. This is part 1 of 0367c, focusing on the 3 highest-priority files (46 references). Part 2 will handle tools and remaining cleanup.

**Current State**:
- 3 critical files contain MCPAgentJob references (46 total refs)
- Bridge code maintains dual-system compatibility
- Monitoring/orchestration queries still use MCPAgentJob table

**Target State**:
- All monitoring queries use AgentJob + AgentExecution exclusively
- Orchestrator spawning logic uses new dual-model pattern
- Zero MCPAgentJob imports in these 3 files

**Split Rationale**: 0367c originally had 102 refs across 8+ files. Splitting into two parts:
- **0367c-1** (this handover): Core orchestration (46 refs, 3 files) - 2-3 hours
- **0367c-2** (future): Tools + remaining (56 refs, 5+ files) - 3-4 hours

---

## Files to Modify

| File | Refs | Action | Complexity | Priority |
|------|------|--------|------------|----------|
| `src/giljo_mcp/monitoring/agent_health_monitor.py` | 23 | Update health checks | MEDIUM | P0 |
| `src/giljo_mcp/orchestrator.py` | 21 | Fix spawning logic | HIGH | P0 |
| `src/giljo_mcp/orchestrator_succession.py` | 2 | Update succession | LOW | P1 |

**Total**: 3 files, 46 references

---

## Implementation Steps

### Step 1: Migrate agent_health_monitor.py (1-1.5 hours)

**Target**: Agent health status monitoring (23 refs)

**Current Pattern**: Health checks query MCPAgentJob for status/staleness

```python
# BEFORE
from src.giljo_mcp.models import MCPAgentJob

async def check_agent_health(session: AsyncSession, tenant_key: str):
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.tenant_key == tenant_key,
        MCPAgentJob.status.in_(["running", "waiting"])
    )
    result = await session.execute(stmt)
    active_jobs = result.scalars().all()

    for job in active_jobs:
        staleness = (datetime.utcnow() - job.last_heartbeat).total_seconds()
        if staleness > STALE_THRESHOLD:
            job.health_status = "stale"
```

**New Pattern**: Health checks query AgentExecution (join AgentJob for tenant)

```python
# AFTER
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from sqlalchemy.orm import joinedload

async def check_agent_health(session: AsyncSession, tenant_key: str):
    stmt = (
        select(AgentExecution)
        .options(joinedload(AgentExecution.job))
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(
            AgentJob.tenant_key == tenant_key,
            AgentExecution.status.in_(["running", "waiting"])
        )
    )
    result = await session.execute(stmt)
    active_executions = result.scalars().all()

    for execution in active_executions:
        staleness = (datetime.utcnow() - execution.last_heartbeat).total_seconds()
        if staleness > STALE_THRESHOLD:
            execution.health_status = "stale"
```

**Key Changes**:

1. **Import Migration**:
   - Remove: `from src.giljo_mcp.models import MCPAgentJob`
   - Add: `from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution`

2. **Query Pattern**:
   - Base query: `select(AgentExecution)` (not MCPAgentJob)
   - Join: `AgentJob` for tenant_key filtering
   - Use `joinedload()` to eager-load job relationship (avoid N+1 queries)

3. **Status Checks**:
   - Health status stored in `AgentExecution.health_status` (execution-level)
   - Last heartbeat in `AgentExecution.last_heartbeat` (execution-level)
   - Tenant filtering via join on `AgentJob.tenant_key`

4. **Staleness Detection**:
   - Same logic, different model field
   - `execution.last_heartbeat` instead of `job.last_heartbeat`
   - Update `execution.health_status` instead of `job.health_status`

**Actions**:
1. Replace MCPAgentJob import with AgentJob + AgentExecution
2. Update all 23 query patterns to use AgentExecution base query
3. Add AgentJob joins for tenant_key filtering
4. Update field references (job.field → execution.field)
5. Remove MCPAgentJob references

**Validation**:
- Run `pytest tests/monitoring/test_agent_health_monitor.py -v`
- Verify staleness detection still works
- Test multi-tenant isolation (no cross-tenant health checks)

---

### Step 2: Migrate orchestrator.py Spawning Logic (1-1.5 hours)

**Target**: Agent spawning and lifecycle management (21 refs)

**Current Pattern**: Orchestrator spawns agents by creating MCPAgentJob records

```python
# BEFORE
from src.giljo_mcp.models import MCPAgentJob

async def spawn_agent(
    session: AsyncSession,
    agent_type: str,
    mission: str,
    product_id: UUID,
    tenant_key: str,
    spawner_job_id: int  # Orchestrator's job_id
) -> MCPAgentJob:
    agent_job = MCPAgentJob(
        job_id=None,  # Auto-increment
        tenant_key=tenant_key,
        product_id=product_id,
        agent_type=agent_type,
        mission=mission,
        status="waiting",
        spawned_by=spawner_job_id,  # int
        instance_number=1
    )
    session.add(agent_job)
    await session.commit()
    await session.refresh(agent_job)
    return agent_job
```

**New Pattern**: Orchestrator spawns agents with dual-model creation

```python
# AFTER
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from uuid import uuid4

async def spawn_agent(
    session: AsyncSession,
    agent_type: str,
    mission: str,
    product_id: UUID,
    tenant_key: str,
    spawner_agent_id: UUID  # Orchestrator's agent_id (UUID, not int!)
) -> tuple[AgentJob, AgentExecution]:
    # Step 1: Create work order
    job_id = str(uuid4())
    agent_job = AgentJob(
        job_id=job_id,
        tenant_key=tenant_key,
        project_id=product_id,  # AgentJob uses project_id, not product_id
        mission=mission,
        job_type=agent_type,  # WHAT work (e.g., "implement feature")
        status="active"  # Work order is active
    )
    session.add(agent_job)
    await session.flush()  # Get job_id

    # Step 2: Create executor instance
    agent_id = str(uuid4())
    agent_execution = AgentExecution(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=tenant_key,
        agent_type=agent_type,  # WHO does work (e.g., "backend-developer")
        agent_name=f"{agent_type.title()} Agent",
        instance_number=1,
        status="waiting",  # Executor is waiting
        spawned_by=spawner_agent_id,  # UUID reference to parent
        progress=0,
        messages=[]
    )
    session.add(agent_execution)
    await session.commit()

    return agent_job, agent_execution
```

**Key Changes**:

1. **Function Signature**:
   - Parameter: `spawner_job_id: int` → `spawner_agent_id: UUID`
   - Return type: `MCPAgentJob` → `tuple[AgentJob, AgentExecution]`

2. **Two-Step Creation**:
   - First: Create `AgentJob` (work order)
   - Flush to get `job_id` assigned
   - Second: Create `AgentExecution` (executor instance)
   - Both share same `job_id` (links them)

3. **Field Mapping**:
   - `spawned_by`: Now takes `agent_id` (UUID), not `job_id` (int)
   - `product_id` → `project_id` in AgentJob model
   - `agent_type`: Duplicated in both models (WHAT vs WHO semantic)
   - `status`: Different enums (AgentJob: 3 values, AgentExecution: 7 values)

4. **Caller Updates**:
   - All callers must update to destructure tuple: `job, execution = await spawn_agent(...)`
   - Pass orchestrator's `agent_id` (UUID), not `job_id` (int)

**Actions**:
1. Replace MCPAgentJob import with AgentJob + AgentExecution
2. Update spawn_agent() function signature and return type
3. Implement two-step creation pattern (job → execution)
4. Update all 21 caller sites to destructure tuple
5. Update spawned_by references to use agent_id (UUID)
6. Remove MCPAgentJob references

**Validation**:
- Run `pytest tests/orchestrator/test_orchestrator.py -v`
- Test agent spawning workflow end-to-end
- Verify spawned_by chain uses UUIDs correctly
- Test lineage tracking (parent → child relationships)

---

### Step 3: Update orchestrator_succession.py (15-30 minutes)

**Target**: Orchestrator succession logic (2 refs)

**Current Pattern**: Succession helper creates new orchestrator MCPAgentJob

```python
# BEFORE
from src.giljo_mcp.models import MCPAgentJob

async def trigger_succession(
    session: AsyncSession,
    old_orchestrator: MCPAgentJob,
    handover_summary: str
) -> MCPAgentJob:
    new_orchestrator = MCPAgentJob(
        tenant_key=old_orchestrator.tenant_key,
        product_id=old_orchestrator.product_id,
        agent_type="orchestrator",
        mission=handover_summary,
        spawned_by=old_orchestrator.job_id,  # int
        instance_number=old_orchestrator.instance_number + 1
    )
    session.add(new_orchestrator)

    old_orchestrator.succeeded_by = new_orchestrator.job_id  # int
    old_orchestrator.status = "decommissioned"

    await session.commit()
    return new_orchestrator
```

**New Pattern**: Succession creates new AgentJob + AgentExecution

```python
# AFTER
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from uuid import uuid4

async def trigger_succession(
    session: AsyncSession,
    old_job: AgentJob,
    old_execution: AgentExecution,
    handover_summary: str
) -> tuple[AgentJob, AgentExecution]:
    # Create new work order (SAME job_id for work continuity)
    # NOTE: This is succession, so we REUSE the same job_id
    # (New execution instance, same work order)

    new_agent_id = str(uuid4())
    new_execution = AgentExecution(
        agent_id=new_agent_id,
        job_id=old_job.job_id,  # SAME job_id (work order continues)
        tenant_key=old_job.tenant_key,
        agent_type="orchestrator",
        agent_name=f"Orchestrator #{old_execution.instance_number + 1}",
        instance_number=old_execution.instance_number + 1,
        status="waiting",
        spawned_by=old_job.job_id,  # Parent is the work order
        progress=0,
        messages=[],
        context_payload={"handover_summary": handover_summary}
    )
    session.add(new_execution)

    # Update old execution succession link
    old_execution.succeeded_by = new_agent_id  # UUID
    old_execution.status = "decommissioned"

    # Update job mission with handover summary
    old_job.mission = handover_summary  # Update work order instructions

    await session.commit()
    return old_job, new_execution  # Same job, new execution
```

**Key Changes**:

1. **Succession Semantics**:
   - OLD: Created entirely new MCPAgentJob (new job_id)
   - NEW: Reuse same `AgentJob.job_id`, create new `AgentExecution`
   - **Rationale**: Work order continues, executor instance changes

2. **Function Signature**:
   - Parameters: `old_orchestrator: MCPAgentJob` → `old_job: AgentJob, old_execution: AgentExecution`
   - Return: `MCPAgentJob` → `tuple[AgentJob, AgentExecution]`

3. **Succession Links**:
   - `spawned_by`: References work order `job_id` (UUID)
   - `succeeded_by`: References new executor `agent_id` (UUID)
   - Both are UUIDs now (was int before)

4. **Mission Update**:
   - Update `AgentJob.mission` with handover summary
   - Provides fresh context for successor executor

**Actions**:
1. Replace MCPAgentJob import with AgentJob + AgentExecution
2. Update function signature to accept both old_job and old_execution
3. Implement new execution creation (reuse same job_id)
4. Update succeeded_by to use agent_id (UUID)
5. Remove MCPAgentJob references

**Validation**:
- Run `pytest tests/orchestrator/test_orchestrator_succession.py -v`
- Test orchestrator handover workflow
- Verify succession chain (old_execution.succeeded_by → new_execution.agent_id)
- Verify work order continuity (same job_id across instances)

---

## Success Criteria

### Code Quality
- [ ] Zero `MCPAgentJob` imports in 3 target files
- [ ] Zero `mcp_agent_jobs` table queries in health monitor
- [ ] All spawning logic uses AgentJob + AgentExecution
- [ ] All succession logic uses agent_id (UUID) for lineage

### Functional Validation
- [ ] Health monitoring detects stale agents correctly
- [ ] Agent spawning creates dual-model records (AgentJob + AgentExecution)
- [ ] Spawned_by references use agent_id (UUID), not job_id (int)
- [ ] Succession creates new executor with same job_id
- [ ] Succession links use agent_id (UUID) for succeeded_by

### Testing
- [ ] `pytest tests/monitoring/test_agent_health_monitor.py` passes
- [ ] `pytest tests/orchestrator/test_orchestrator.py` passes
- [ ] `pytest tests/orchestrator/test_orchestrator_succession.py` passes
- [ ] No test failures due to missing MCPAgentJob

### Integration Validation
- [ ] Project launch spawns orchestrator with dual-model pattern
- [ ] Orchestrator spawns child agents with correct spawned_by chain
- [ ] Succession workflow creates new executor instance (same job)
- [ ] Health checks run without errors on new model structure

---

## Rollback Plan

### If Issues Arise During Migration
1. **Stop immediately** - Do not proceed to next file
2. **Revert commits** - `git reset --hard HEAD~N` (N = commits since 0367c-1 start)
3. **Verify 0367a/0367b intact** - Ensure service/API layers still functional
4. **Restart server** - Clear ORM cache
5. **Document issue** - Record specific failure in handover notes

### If Issues Arise After Completion
1. **Revert entire handover** - `git revert <commit-hash>`
2. **Verify partial migration state** - Check if 0367a/0367b still work
3. **Document failure** - Record specific issue for retry planning
4. **Plan retry** - Address root cause before re-attempting

**Recovery Time**: <10 minutes (Git revert + server restart)

**Data Loss Risk**: NONE (read-mostly operations; writes use service layer)

---

## Testing Strategy

### Unit Tests
- Run file-specific test modules after each step
- Verify method behavior unchanged (inputs/outputs consistent)
- Check for proper error handling (invalid agent_id, missing records)

### Integration Tests
- Test full orchestrator lifecycle: spawn → run → succession
- Verify health monitoring detects staleness correctly
- Test multi-tenant isolation (no cross-tenant spawning/monitoring)

### Manual Testing Checklist
- [ ] Create project → Launch → Verify orchestrator spawned with dual models
- [ ] Spawn child agent → Verify spawned_by uses parent agent_id (UUID)
- [ ] Trigger succession → Verify new executor created (same job_id)
- [ ] Check health monitor → Verify staleness detection on AgentExecution

---

## Field Mapping Reference (Quick Lookup)

| MCPAgentJob Field | AgentJob Field | AgentExecution Field | Notes |
|-------------------|----------------|----------------------|-------|
| `job_id` (int) | - | `id` (int) | Executor instance ID |
| - | `job_id` (UUID str) | `job_id` (UUID str) | Work order ID (links models) |
| - | `id` (UUID) | `agent_id` (UUID) | Primary key (work order / executor) |
| `product_id` | `project_id` | - | Renamed in AgentJob |
| `agent_type` | `job_type` | `agent_type` | WHAT work vs WHO does it |
| `mission` | `mission` | - | Stored in AgentJob only |
| `status` | `status` (3 values) | `status` (7 values) | Different enums! |
| `spawned_by` (int) | - | `spawned_by` (UUID) | Now agent_id, not job_id |
| `succeeded_by` (int) | - | `succeeded_by` (UUID) | Now agent_id, not job_id |
| `instance_number` | - | `instance_number` | Execution-level |
| `last_heartbeat` | - | `last_heartbeat` | Execution-level |
| `health_status` | - | `health_status` | Execution-level |

**Full Reference**: [0358_model_mapping_reference.md](Reference_docs/0358_model_mapping_reference.md)

---

## Notes

### Why Split 0367c into Two Parts?
- **Original 0367c**: 102 refs across 8+ files (6-8 hour estimate)
- **Split Rationale**:
  - Part 1 (this): Core orchestration (46 refs, 3 files, 2-3 hours)
  - Part 2 (future): Tools + remaining (56 refs, 5+ files, 3-4 hours)
- **Benefit**: Smaller, focused handovers complete faster with less risk

### Why Orchestrator Files First?
- **Foundation**: Orchestrator spawning is critical path for all agent lifecycle
- **Dependency**: Tools (part 2) may call orchestrator methods
- **Testing**: Orchestrator tests validate correctness before tool migration

### Succession Semantic Shift
- **OLD (MCPAgentJob)**: Succession created entirely new job (new job_id)
- **NEW (AgentJob + AgentExecution)**: Succession creates new executor (same job_id)
- **Rationale**: Work order persists, executor instance changes
- **Benefit**: Work continuity across succession (same mission, new executor)

### Performance Considerations
- **Health Checks**: Join adds ~1-2ms per check (acceptable)
- **Spawning**: Dual insert adds ~2-5ms per spawn (acceptable)
- **Mitigation**: Eager loading with `joinedload()` prevents N+1 queries

---

## Related Documentation

- [0358_model_mapping_reference.md](Reference_docs/0358_model_mapping_reference.md) - Complete field mapping
- [docs/ORCHESTRATOR.md](../docs/ORCHESTRATOR.md) - Orchestrator lifecycle documentation
- [0367_kickoff.md](0367_kickoff.md) - Overall MCPAgentJob cleanup roadmap
- [0367a_service_layer_cleanup.md](0367a_service_layer_cleanup.md) - Service layer patterns
- [0367b_api_endpoint_migration.md](0367b_api_endpoint_migration.md) - API endpoint patterns

---

**Next Step**: After completion, proceed to Handover 0367c-2 (Tools & Remaining Cleanup) or 0367d (Validation & Deprecation) if 0367c-2 deferred.
