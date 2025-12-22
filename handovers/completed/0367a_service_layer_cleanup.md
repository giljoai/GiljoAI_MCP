# Handover 0367a: Service Layer MCPAgentJob Cleanup

**Date**: 2025-12-21
**Status**: Pending
**Priority**: HIGH
**Estimated Time**: 8-12 hours
**Dependencies**:
- Handover 0358 (AgentJob/AgentExecution dual-model) - COMPLETE
- 0358_model_mapping_reference.md - COMPLETE

---

## Overview

Clean up all MCPAgentJob references in the service layer (`src/giljo_mcp/services/`), removing bridge code, fallback logic, and legacy model imports. The service layer is the foundation for all data operations, so completing this phase enables successful migration of API endpoints (0367b) and tools (0367c).

**Current State**:
- 8 service files contain MCPAgentJob references (317 total refs)
- Bridge code maintains dual-system compatibility (e.g., orchestration_service.py lines 1372-1398)
- Type aliases obscure intent (e.g., `Job = MCPAgentJob` in agent_job_manager.py)

**Target State**:
- All service methods use `AgentJob` + `AgentExecution` exclusively
- Zero MCPAgentJob imports or queries
- Clear semantics: AgentJob = work order, AgentExecution = executor instance

---

## Files to Modify

| File | Refs | Action | Complexity | Priority |
|------|------|--------|------------|----------|
| `project_service.py` | 44 | Replace legacy queries | HIGH | CRITICAL |
| `message_service.py` | 29 | Update job lookups | MEDIUM | HIGH |
| `prompts.py` | 28 | Fix prompt generation | MEDIUM | HIGH |
| `agent_health_monitor.py` | 23 | Update status checks | MEDIUM | HIGH |
| `orchestrator.py` | 21 | Remove spawning logic | HIGH | CRITICAL |
| `statistics.py` | 21 | Migrate aggregations | MEDIUM | MEDIUM |
| `agent_job_manager.py` | 20 | Remove Job alias | HIGH | CRITICAL |
| `orchestration_service.py` | 20 | Remove bridge code | HIGH | CRITICAL |

**Total**: 8 files, 206 references (Note: Some files span service/tools boundaries)

---

## Implementation Steps

### Step 1: Remove Bridge Code in orchestration_service.py (2-3 hours)

**Target Lines**:
- Lines 1372-1398: `_create_agent_job_bridge()` method
- Lines 1815-1879: Fallback logic in job creation

**Current Code Pattern**:
```python
# Bridge code creates both models
agent_job = AgentJob(...)
await session.add(agent_job)
await session.flush()  # Get agent_job.id

# REMOVE: Fallback to MCPAgentJob
mcp_job = MCPAgentJob(
    agent_id=str(agent_job.id),  # Convert UUID to str for legacy
    ...
)
await session.add(mcp_job)
```

**New Code Pattern**:
```python
# Create work order (AgentJob)
agent_job = AgentJob(
    product_id=product_id,
    agent_name=agent_name,
    mission=mission_text,
    context_payload=context_dict,
    tenant_key=tenant_key
)
session.add(agent_job)
await session.flush()  # Get agent_job.id

# Create executor instance (AgentExecution)
execution = AgentExecution(
    agent_id=agent_job.id,
    status="pending",
    spawned_by=spawner_agent_id  # UUID, not legacy job_id
)
session.add(execution)
await session.commit()
```

**Actions**:
1. Remove `_create_agent_job_bridge()` method entirely
2. Replace calls to bridge method with dual-model creation
3. Update spawned_by to use agent_id (UUID) instead of legacy job_id (int)
4. Remove MCPAgentJob import
5. Update type hints to use `AgentJob` and `AgentExecution`

**Validation**:
- Run `pytest tests/services/test_orchestration_service.py -v`
- Verify no MCPAgentJob records created in test database

---

### Step 2: Remove Job Alias in agent_job_manager.py (1-2 hours)

**Target Line**: `Job = MCPAgentJob` alias (obscures intent)

**Current Code Pattern**:
```python
from ..models import MCPAgentJob as Job

class AgentJobManager:
    async def create_job(self, session, **kwargs):
        job = Job(**kwargs)  # Creates MCPAgentJob
        session.add(job)
```

**New Code Pattern**:
```python
from ..models import AgentJob, AgentExecution

class AgentJobManager:
    async def create_job(self, session, **kwargs):
        # Create work order
        agent_job = AgentJob(
            product_id=kwargs['product_id'],
            agent_name=kwargs['agent_name'],
            mission=kwargs['mission'],
            ...
        )
        session.add(agent_job)
        await session.flush()

        # Create executor
        execution = AgentExecution(
            agent_id=agent_job.id,
            status="pending"
        )
        session.add(execution)
        await session.commit()

        return agent_job, execution
```

**Actions**:
1. Remove `Job = MCPAgentJob` import alias
2. Replace all `Job()` instantiations with `AgentJob()` + `AgentExecution()`
3. Update method signatures to return tuple: `(AgentJob, AgentExecution)`
4. Update callers to destructure tuple: `agent_job, execution = await manager.create_job(...)`
5. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/services/test_agent_job_manager.py -v`
- Verify return types match expected tuple

---

### Step 3: Migrate project_service.py Queries (3-4 hours)

**Target**: 44 MCPAgentJob references (highest count)

**Common Query Patterns to Replace**:

#### Pattern 1: Job Status Queries
```python
# BEFORE
from ..models import MCPAgentJob
result = await session.execute(
    select(MCPAgentJob).where(MCPAgentJob.product_id == product_id)
)
jobs = result.scalars().all()

# AFTER
from ..models import AgentJob, AgentExecution
result = await session.execute(
    select(AgentJob)
    .join(AgentExecution, AgentJob.id == AgentExecution.agent_id)
    .where(AgentJob.product_id == product_id)
)
jobs = result.scalars().all()
```

#### Pattern 2: Job Creation (Project Launch)
```python
# BEFORE
job = MCPAgentJob(
    product_id=product_id,
    agent_template_id=template_id,
    mission_text=mission,
    status="pending",
    tenant_key=tenant_key
)
session.add(job)

# AFTER
agent_job = AgentJob(
    product_id=product_id,
    agent_name=agent_name,  # From template
    mission=mission,
    tenant_key=tenant_key
)
session.add(agent_job)
await session.flush()

execution = AgentExecution(
    agent_id=agent_job.id,
    status="pending"
)
session.add(execution)
```

#### Pattern 3: Field Mapping (See 0358_model_mapping_reference.md)
```python
# BEFORE: MCPAgentJob.job_id (int, executor instance ID)
job_id = mcp_job.job_id

# AFTER: Use agent_id (UUID, work order ID)
agent_id = agent_job.id  # UUID
execution_id = execution.id  # int, if needed for executor instance
```

**Actions**:
1. Review all 44 references in project_service.py
2. Categorize by query pattern (status, creation, updates, deletes)
3. Replace each with AgentJob + AgentExecution equivalent
4. Update field mappings per 0358 reference doc
5. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/services/test_project_service.py -v`
- Test project launch workflow (creates agent jobs)
- Test project status queries (reads agent jobs)

---

### Step 4: Update message_service.py Job Lookups (2 hours)

**Target**: 29 MCPAgentJob references (agent communication queue)

**Common Pattern**: Message routing uses job_id for agent identification

```python
# BEFORE
from ..models import MCPAgentJob
job = await session.get(MCPAgentJob, job_id)  # job_id is int
if job:
    recipient_agent = job.agent_template_id

# AFTER
from ..models import AgentJob, AgentExecution
# Determine if job_id is UUID (agent_id) or int (execution_id)
# Prefer agent_id (UUID) for message routing (work order level)

agent_job = await session.get(AgentJob, agent_id)  # agent_id is UUID
if agent_job:
    recipient_agent = agent_job.agent_name
```

**Key Decision**: Messages route to `AgentJob` (work order), not `AgentExecution` (instance)
- **Rationale**: Retries should receive same messages as original attempt
- **Implementation**: Use agent_id (UUID) for message routing

**Actions**:
1. Identify all job lookups in message_service.py
2. Replace `MCPAgentJob` queries with `AgentJob` queries
3. Update job_id parameters to agent_id (UUID)
4. Update message queue schema if job_id stored (change to agent_id)
5. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/services/test_message_service.py -v`
- Test message send/receive workflow
- Verify messages route to correct agent_id

---

### Step 5: Verify Remaining Service Files (1-2 hours)

**Files with Lower Reference Counts**:
- `prompts.py` (28 refs) - Covered in 0367b (API endpoints)
- `agent_health_monitor.py` (23 refs) - Covered in 0367c (tools)
- `orchestrator.py` (21 refs) - Covered in 0367c (tools)
- `statistics.py` (21 refs) - Covered in 0367b (API endpoints)

**Actions**:
1. Review each file for service-layer-specific references
2. If references are in service methods, migrate now
3. If references are in API/tool layers, defer to 0367b/0367c
4. Document any cross-layer dependencies

**Validation**:
- Grep for `MCPAgentJob` in `src/giljo_mcp/services/`
- Verify zero matches (excluding comments)

---

## Success Criteria

### Code Quality
- [ ] Zero `MCPAgentJob` imports in `src/giljo_mcp/services/*.py`
- [ ] Zero `mcp_agent_jobs` table queries in service methods
- [ ] All bridge code removed (orchestration_service.py)
- [ ] All type aliases removed (agent_job_manager.py)
- [ ] All service methods use `AgentJob` + `AgentExecution` models

### Functional Validation
- [ ] Project launch creates AgentJob + AgentExecution (no MCPAgentJob)
- [ ] Agent job queries return correct data from new tables
- [ ] Message routing uses agent_id (UUID) correctly
- [ ] Orchestrator spawning creates dual-model records

### Testing
- [ ] `pytest tests/services/test_orchestration_service.py` passes
- [ ] `pytest tests/services/test_agent_job_manager.py` passes
- [ ] `pytest tests/services/test_project_service.py` passes
- [ ] `pytest tests/services/test_message_service.py` passes
- [ ] No test failures due to missing MCPAgentJob

### Performance
- [ ] No performance regression in job creation (acceptable: +5ms for dual insert)
- [ ] No performance regression in job queries (acceptable: join overhead <2ms)

---

## Rollback Plan

### If Issues Arise During Migration
1. **Stop immediately** - Do not proceed to next file
2. **Revert commits** - `git reset --hard HEAD~N` (N = commits since 0367a start)
3. **Restore bridge code** - Re-enable orchestration_service.py fallback
4. **Restart server** - Clear ORM cache
5. **Verify legacy path** - Test with MCPAgentJob still functional

### If Issues Arise After Completion
1. **Revert entire handover** - `git revert <commit-hash>`
2. **Restore database** - From pre-migration backup
3. **Document failure** - Record specific issue in handover notes
4. **Plan retry** - Address root cause before re-attempting

**Recovery Time**: <15 minutes (Git revert + server restart)

**Data Loss Risk**: LOW (new models already populated by bridge code in 0358)

---

## Testing Strategy

### Unit Tests
- Run service-specific test files after each step
- Verify method behavior unchanged (inputs/outputs consistent)
- Check for proper error handling (invalid agent_id, missing execution)

### Integration Tests
- Test full agent lifecycle: create → spawn → message → complete
- Verify WebSocket events emit correct agent_id (UUID)
- Test project launch workflow end-to-end

### Manual Testing Checklist
- [ ] Create new project → Launch → Verify agent_jobs + agent_executions populated
- [ ] Send message to agent → Verify routing by agent_id
- [ ] Check agent status → Verify correct data from new tables
- [ ] Spawn child agent → Verify spawned_by uses agent_id (UUID)

---

## Field Mapping Reference (Quick Lookup)

| MCPAgentJob Field | AgentJob Field | AgentExecution Field | Notes |
|-------------------|----------------|----------------------|-------|
| `job_id` (int) | - | `id` (int) | Executor instance ID |
| - | `id` (UUID) | `agent_id` (UUID) | Work order ID |
| `product_id` | `product_id` | - | Product association |
| `agent_template_id` | - | - | Derived from agent_name |
| `agent_name` | - | `agent_name` | Agent type |
| `mission_text` | `mission` | - | Instructions (stored once) |
| `status` | - | `status` | Execution status |
| `spawned_by` (int) | - | `spawned_by` (UUID) | Now agent_id, not job_id |
| `succeeded_by` (int) | - | `succeeded_by` (UUID) | Now agent_id, not job_id |
| `context_payload` | `context_payload` | - | Context dict |
| `context_used` | - | `context_used` | Per-execution metric |
| `context_budget` | - | `context_budget` | Per-execution limit |

**Full Reference**: [0358_model_mapping_reference.md](Reference_docs/0358_model_mapping_reference.md)

---

## Notes

### Why Service Layer First?
- **Foundation**: Services are the data access layer; API/tools depend on them
- **Validation**: Service tests validate correctness before exposing to upper layers
- **Cascade**: Clean service layer enables clean API layer (0367b)

### Why Not Remove MCPAgentJob Model Yet?
- **Historical Data**: Table contains records from pre-migration
- **Test Compatibility**: Test files (1,291 refs) still use MCPAgentJob
- **Phased Approach**: Mark deprecated in 0367d, remove in v3.4+

### Performance Considerations
- **Dual Inserts**: Creating both AgentJob + AgentExecution adds ~2-5ms per job
- **Joins**: Querying both tables adds ~1-2ms per query
- **Mitigation**: Add indexes on agent_jobs.product_id, agent_executions.agent_id
- **Acceptable**: Performance impact negligible for typical workloads (<100 jobs/sec)

### Semantic Shift: job_id → agent_id
- **Old**: `job_id` (int) identified executor instance
- **New**: `agent_id` (UUID) identifies work order
- **Impact**: All foreign keys must update (spawned_by, succeeded_by, message routing)
- **Benefit**: Work order ID stable across retries; executor ID transient

---

## Related Documentation

- [0358_model_mapping_reference.md](Reference_docs/0358_model_mapping_reference.md) - Complete field mapping
- [docs/SERVICES.md](../docs/SERVICES.md) - Service layer patterns
- [docs/ORCHESTRATOR.md](../docs/ORCHESTRATOR.md) - Agent lifecycle documentation

---

**Next Step**: After completion, proceed to Handover 0367b (API Endpoint Migration)
