# Handover 0367b: API Endpoint MCPAgentJob Migration

**Date**: 2025-12-21
**Status**: Pending
**Priority**: HIGH
**Estimated Time**: 6-8 hours
**Dependencies**:
- Handover 0367a (Service Layer Cleanup) - MUST BE COMPLETE
- 0358_model_mapping_reference.md - COMPLETE
- JobResponse.id: int → str migration (Handover 0358) - COMPLETE

---

## Overview

Migrate all API endpoints in `api/endpoints/` from MCPAgentJob to AgentJob + AgentExecution models. This phase depends on 0367a (service layer) being complete, as endpoints consume service methods.

**Current State**:
- 7 endpoint modules contain MCPAgentJob references (103 total refs)
- Response schemas already migrated (JobResponse.id is str)
- Query logic still uses MCPAgentJob table directly

**Target State**:
- All endpoint queries use AgentJob + AgentExecution
- Response DTOs correctly map new model fields
- WebSocket events emit agent_id (UUID) instead of job_id (int)

---

## Files to Modify

| File | Refs | Action | Complexity | Priority |
|------|------|--------|------------|----------|
| `prompts.py` | 28 | Fix thin client prompts | MEDIUM | HIGH |
| `statistics.py` | 21 | Migrate aggregations | MEDIUM | MEDIUM |
| `agent_jobs/filters.py` | 13 | Update filter queries | LOW | MEDIUM |
| `agent_jobs/table_view.py` | 12 | Update table data | LOW | MEDIUM |
| `agent_jobs/succession.py` | 11 | Fix succession logic | MEDIUM | HIGH |
| `agent_jobs/operations.py` | 10 | Update CRUD operations | MEDIUM | HIGH |
| `projects/status.py` | 8 | Fix status queries | LOW | LOW |

**Total**: 7 files, 103 references

---

## Implementation Steps

### Step 1: Migrate prompts.py (2-3 hours)

**Target**: Thin client prompt generation for orchestrators and agents (28 refs)

**Current Pattern**: Prompts reference MCPAgentJob.job_id (int) for agent identification

```python
# BEFORE
from ..models import MCPAgentJob
job = await session.get(MCPAgentJob, job_id)
prompt = f"Your job ID is {job.job_id} (int)"
```

**New Pattern**: Prompts reference AgentJob.id (UUID) for work order identification

```python
# AFTER
from ..models import AgentJob
agent_job = await session.get(AgentJob, agent_id)
prompt = f"Your agent ID is {agent_job.id} (UUID)"
```

**Key Changes**:

1. **Orchestrator Prompts** (`ThinClientPromptGenerator`):
   - Already uses `get_orchestrator_instructions()` MCP tool (0246 series)
   - Verify no MCPAgentJob references in prompt builder
   - Ensure agent_id (UUID) passed to MCP tools, not job_id (int)

2. **Agent Prompts** (`get_generic_agent_template()`):
   - Replace `job_id` parameter with `agent_id` (UUID)
   - Update `get_agent_mission()` call to use agent_id
   - Remove fallback logic for MCPAgentJob queries

**Actions**:
1. Review all 28 MCPAgentJob references in prompts.py
2. Replace job_id (int) with agent_id (UUID) in prompt variables
3. Update MCP tool calls to use agent_id
4. Remove MCPAgentJob imports
5. Update type hints to use AgentJob

**Validation**:
- Run `pytest tests/api/test_prompts.py -v`
- Test thin client prompt generation via API
- Verify MCP tool calls use correct agent_id (UUID)

---

### Step 2: Migrate statistics.py Aggregations (1-2 hours)

**Target**: Agent job statistics endpoints (21 refs)

**Common Aggregation Patterns**:

#### Pattern 1: Count by Status
```python
# BEFORE
from ..models import MCPAgentJob
result = await session.execute(
    select(func.count(MCPAgentJob.job_id))
    .where(MCPAgentJob.status == "completed")
    .where(MCPAgentJob.tenant_key == tenant_key)
)
count = result.scalar()

# AFTER
from ..models import AgentExecution
result = await session.execute(
    select(func.count(AgentExecution.id))
    .where(AgentExecution.status == "completed")
    .join(AgentJob, AgentExecution.agent_id == AgentJob.id)
    .where(AgentJob.tenant_key == tenant_key)
)
count = result.scalar()
```

#### Pattern 2: Group by Agent Type
```python
# BEFORE
result = await session.execute(
    select(
        MCPAgentJob.agent_template_id,
        func.count(MCPAgentJob.job_id)
    )
    .group_by(MCPAgentJob.agent_template_id)
)

# AFTER
result = await session.execute(
    select(
        AgentExecution.agent_name,  # No more template_id
        func.count(AgentExecution.id)
    )
    .group_by(AgentExecution.agent_name)
)
```

#### Pattern 3: Context Usage Stats
```python
# BEFORE
avg_context = await session.execute(
    select(func.avg(MCPAgentJob.context_used))
    .where(MCPAgentJob.product_id == product_id)
)

# AFTER
avg_context = await session.execute(
    select(func.avg(AgentExecution.context_used))
    .join(AgentJob, AgentExecution.agent_id == AgentJob.id)
    .where(AgentJob.product_id == product_id)
)
```

**Actions**:
1. Identify all aggregation queries in statistics.py
2. Determine if aggregating work orders (AgentJob) or executions (AgentExecution)
3. Replace table references and update joins
4. Update field mappings (agent_template_id → agent_name)
5. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/api/test_statistics.py -v`
- Verify aggregation counts match expected values
- Test with multi-tenant data (no cross-tenant leakage)

---

### Step 3: Update agent_jobs/filters.py (1 hour)

**Target**: Job filtering logic for table views (13 refs)

**Common Filter Patterns**:

```python
# BEFORE
from ..models import MCPAgentJob
query = select(MCPAgentJob)
if status:
    query = query.where(MCPAgentJob.status == status)
if product_id:
    query = query.where(MCPAgentJob.product_id == product_id)

# AFTER
from ..models import AgentJob, AgentExecution
query = select(AgentJob).join(AgentExecution)
if status:
    query = query.where(AgentExecution.status == status)
if product_id:
    query = query.where(AgentJob.product_id == product_id)
```

**Key Decision**: Filters operate on joined query (AgentJob + AgentExecution)
- **Work order filters**: product_id, agent_name, tenant_key → `AgentJob`
- **Execution filters**: status, context_used, created_at → `AgentExecution`

**Actions**:
1. Replace MCPAgentJob base query with joined AgentJob + AgentExecution
2. Map filter fields to correct table (see decision above)
3. Update response DTOs to populate from both models
4. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/api/agent_jobs/test_filters.py -v`
- Test each filter parameter independently
- Test combined filters (status + product_id)

---

### Step 4: Update agent_jobs/table_view.py (1 hour)

**Target**: Table data serialization for UI (12 refs)

**Current DTO Pattern**:
```python
# BEFORE
class JobTableRow:
    job_id: int
    agent_name: str
    status: str
    product_id: UUID

job = MCPAgentJob(...)
row = JobTableRow(
    job_id=job.job_id,
    agent_name=job.agent_name,
    status=job.status,
    product_id=job.product_id
)
```

**New DTO Pattern**:
```python
# AFTER
class JobTableRow:
    agent_id: str  # UUID as string (Handover 0358)
    agent_name: str
    status: str
    product_id: str  # UUID as string

agent_job = AgentJob(...)
execution = AgentExecution(...)
row = JobTableRow(
    agent_id=str(agent_job.id),
    agent_name=execution.agent_name,
    status=execution.status,
    product_id=str(agent_job.product_id)
)
```

**Actions**:
1. Update JobTableRow schema (job_id → agent_id, int → str)
2. Update DTO population logic to use AgentJob + AgentExecution
3. Map fields from correct model (see field mapping reference)
4. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/api/agent_jobs/test_table_view.py -v`
- Verify JSON serialization (UUIDs as strings)
- Test with UI (StatusBoard component expects agent_id: str)

---

### Step 5: Migrate agent_jobs/succession.py (1-2 hours)

**Target**: Orchestrator succession logic (11 refs)

**Current Pattern**: Succession creates new MCPAgentJob with `spawned_by` referencing old job_id (int)

```python
# BEFORE
old_job = await session.get(MCPAgentJob, job_id)
new_job = MCPAgentJob(
    agent_template_id=old_job.agent_template_id,
    mission_text=handover_summary,
    spawned_by=old_job.job_id,  # int
    ...
)
old_job.succeeded_by = new_job.job_id  # int
```

**New Pattern**: Succession creates new AgentJob + AgentExecution with `spawned_by` referencing old agent_id (UUID)

```python
# AFTER
old_agent_job = await session.get(AgentJob, agent_id)
old_execution = await session.execute(
    select(AgentExecution).where(AgentExecution.agent_id == agent_id)
)
old_execution = old_execution.scalar_one()

# Create new work order
new_agent_job = AgentJob(
    product_id=old_agent_job.product_id,
    agent_name=old_execution.agent_name,
    mission=handover_summary,
    tenant_key=old_agent_job.tenant_key
)
session.add(new_agent_job)
await session.flush()

# Create new executor
new_execution = AgentExecution(
    agent_id=new_agent_job.id,
    status="pending",
    spawned_by=old_agent_job.id,  # UUID
    agent_name=old_execution.agent_name
)
session.add(new_execution)

# Update old executor succession
old_execution.succeeded_by = new_agent_job.id  # UUID
await session.commit()
```

**Actions**:
1. Replace MCPAgentJob queries with AgentJob + AgentExecution
2. Update spawned_by and succeeded_by to use agent_id (UUID)
3. Generate handover summary from old_agent_job.mission (not recreating)
4. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/api/agent_jobs/test_succession.py -v`
- Test orchestrator handover workflow end-to-end
- Verify lineage chain (spawned_by → succeeded_by) uses UUIDs

---

### Step 6: Update agent_jobs/operations.py (1 hour)

**Target**: CRUD operations for agent jobs (10 refs)

**Operations to Migrate**:

1. **Create** (POST /agent_jobs):
   - Delegate to service layer (already migrated in 0367a)
   - Verify response DTO uses agent_id (UUID)

2. **Read** (GET /agent_jobs/{agent_id}):
   - Replace `session.get(MCPAgentJob, job_id)` with `session.get(AgentJob, agent_id)`
   - Join AgentExecution for status/context fields

3. **Update** (PUT /agent_jobs/{agent_id}):
   - Update AgentExecution.status, not AgentJob
   - AgentJob is immutable (work order); AgentExecution is mutable (executor state)

4. **Delete** (DELETE /agent_jobs/{agent_id}):
   - Soft delete: Set AgentExecution.status = "cancelled"
   - Do NOT delete AgentJob (preserve work order history)

**Actions**:
1. Update each CRUD operation per above patterns
2. Verify service layer delegation (don't duplicate logic)
3. Update response DTOs to use AgentJob + AgentExecution
4. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/api/agent_jobs/test_operations.py -v`
- Test full CRUD cycle via API
- Verify soft delete doesn't remove AgentJob

---

### Step 7: Fix projects/status.py (30 minutes)

**Target**: Project status queries (8 refs)

**Current Pattern**: Query MCPAgentJob to get agent job counts per project

```python
# BEFORE
from ..models import MCPAgentJob
result = await session.execute(
    select(func.count(MCPAgentJob.job_id))
    .where(MCPAgentJob.product_id == product_id)
    .where(MCPAgentJob.status == "running")
)
running_count = result.scalar()
```

**New Pattern**: Query AgentExecution (join AgentJob for product_id)

```python
# AFTER
from ..models import AgentJob, AgentExecution
result = await session.execute(
    select(func.count(AgentExecution.id))
    .join(AgentJob, AgentExecution.agent_id == AgentJob.id)
    .where(AgentJob.product_id == product_id)
    .where(AgentExecution.status == "running")
)
running_count = result.scalar()
```

**Actions**:
1. Replace MCPAgentJob count queries with AgentExecution counts
2. Add AgentJob join for product_id filter
3. Update response schema to use agent_id (UUID)
4. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/api/projects/test_status.py -v`
- Verify status counts match dashboard UI
- Test with multiple projects (no cross-project leakage)

---

## Success Criteria

### Code Quality
- [ ] Zero `MCPAgentJob` imports in `api/endpoints/*.py`
- [ ] Zero `mcp_agent_jobs` table queries in endpoint handlers
- [ ] All response DTOs use agent_id (str, UUID) instead of job_id (int)
- [ ] All filter/aggregation queries use AgentJob + AgentExecution

### Functional Validation
- [ ] Thin client prompts reference agent_id (UUID) correctly
- [ ] Statistics endpoints return accurate counts from new tables
- [ ] Table views serialize agent_id as string (UUID)
- [ ] Succession workflow creates new AgentJob + AgentExecution with correct spawned_by
- [ ] CRUD operations work with agent_id (UUID) parameter

### API Compatibility
- [ ] GET /agent_jobs/{agent_id} returns JobResponse with id: str
- [ ] POST /agent_jobs creates AgentJob + AgentExecution (no MCPAgentJob)
- [ ] PUT /agent_jobs/{agent_id} updates AgentExecution.status
- [ ] DELETE /agent_jobs/{agent_id} soft-deletes execution
- [ ] WebSocket events emit agent_id (str, UUID)

### Testing
- [ ] `pytest tests/api/test_prompts.py` passes
- [ ] `pytest tests/api/test_statistics.py` passes
- [ ] `pytest tests/api/agent_jobs/` passes (all 4 modules)
- [ ] `pytest tests/api/projects/test_status.py` passes
- [ ] No test failures due to missing MCPAgentJob

---

## Rollback Plan

### If Issues Arise During Migration
1. **Stop immediately** - Do not proceed to next file
2. **Revert commits** - `git reset --hard HEAD~N` (N = commits since 0367b start)
3. **Restore service layer** - Ensure 0367a changes intact (don't revert those)
4. **Restart server** - Clear API route cache
5. **Verify API still functional** - Test key endpoints

### If Issues Arise After Completion
1. **Revert entire handover** - `git revert <commit-hash>`
2. **Rollback service layer if needed** - If cascading failures from 0367a
3. **Document failure** - Record specific issue in handover notes
4. **Plan retry** - Address root cause before re-attempting

**Recovery Time**: <10 minutes (Git revert + server restart)

**Data Loss Risk**: NONE (read-only endpoints; writes delegate to service layer)

---

## Testing Strategy

### Unit Tests
- Run endpoint-specific test files after each step
- Verify response schemas match expected structure (agent_id: str)
- Check for proper error handling (invalid agent_id, not found)

### Integration Tests
- Test full workflows: project launch → agent spawn → succession
- Verify WebSocket events emit correct agent_id (UUID)
- Test multi-tenant isolation (no cross-tenant data leakage)

### API Testing Checklist
- [ ] GET /prompts/thin-client/{agent_id} → Returns prompt with correct agent_id
- [ ] GET /statistics/jobs → Returns counts from agent_executions table
- [ ] GET /agent_jobs?status=running → Filters by AgentExecution.status
- [ ] POST /agent_jobs/succession → Creates new AgentJob + AgentExecution
- [ ] GET /projects/{product_id}/status → Returns job counts per status

---

## Response DTO Reference

### JobResponse (Already Migrated in 0358)
```python
class JobResponse(BaseModel):
    id: str  # agent_id (UUID) as string
    agent_name: str  # From AgentExecution
    status: str  # From AgentExecution
    product_id: str  # From AgentJob (UUID as string)
    mission: str  # From AgentJob
    context_used: int  # From AgentExecution
    context_budget: int  # From AgentExecution
    spawned_by: Optional[str]  # From AgentExecution (UUID as string)
    succeeded_by: Optional[str]  # From AgentExecution (UUID as string)
```

**Field Sources**:
- `AgentJob`: id, product_id, mission, context_payload, tenant_key
- `AgentExecution`: agent_name, status, context_used, context_budget, spawned_by, succeeded_by

---

## WebSocket Event Updates

**Current Events**: Emit job_id (int) in payloads

**New Events**: Emit agent_id (str, UUID) in payloads

```python
# BEFORE
await ws_manager.broadcast({
    "event": "job_status_update",
    "job_id": 12345,  # int
    "status": "running"
})

# AFTER
await ws_manager.broadcast({
    "event": "job_status_update",
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",  # UUID as str
    "status": "running"
})
```

**Frontend Compatibility**: StatusBoard components already expect agent_id (str) from 0358 migration.

---

## Notes

### Why API Layer After Service Layer?
- **Dependency**: Endpoints consume service methods; services must be clean first
- **Delegation**: Many endpoints delegate to services (already migrated in 0367a)
- **Testing**: Service tests validate correctness before exposing to API

### Why Response DTOs Already Migrated?
- **Handover 0358**: Changed JobResponse.id from int to str (UUID)
- **Frontend Ready**: StatusBoard components expect agent_id: str
- **This Handover**: Focus on query logic, not response schemas

### Performance Considerations
- **Joins**: AgentJob + AgentExecution join adds ~1-2ms per query
- **Indexes**: Ensure indexes on agent_jobs.id, agent_executions.agent_id
- **Acceptable**: Performance impact negligible for typical API workloads

### Semantic Clarity
- **Work Order (AgentJob)**: Immutable, reusable across retries
- **Executor (AgentExecution)**: Mutable, one per attempt
- **API Response**: Combines both (mission from work order, status from executor)

---

## Related Documentation

- [0358_model_mapping_reference.md](Reference_docs/0358_model_mapping_reference.md) - Complete field mapping
- [docs/api/](../docs/api/) - API endpoint documentation
- [docs/SERVICES.md](../docs/SERVICES.md) - Service layer patterns

---

**Next Step**: After completion, proceed to Handover 0367c (Tools & Monitoring Cleanup)
