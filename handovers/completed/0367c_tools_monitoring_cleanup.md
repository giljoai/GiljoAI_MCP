# Handover 0367c: Tools & Monitoring MCPAgentJob Cleanup

**Date**: 2025-12-21
**Status**: Pending
**Priority**: HIGH
**Estimated Time**: 6-8 hours
**Dependencies**:
- Handover 0367a (Service Layer Cleanup) - MUST BE COMPLETE
- Handover 0367b (API Endpoint Migration) - MUST BE COMPLETE
- 0358_model_mapping_reference.md - COMPLETE

---

## Overview

Clean up MCPAgentJob references in MCP tools (`src/giljo_mcp/tools/`) and orchestration components (`src/giljo_mcp/orchestration/`). This is the final production code cleanup phase before validation/deprecation (0367d).

**Current State**:
- 8 files contain MCPAgentJob references (102 total refs)
- Tools expose MCP functions to orchestrators/agents
- Monitoring tracks agent health and context usage
- Orchestrator spawning logic uses legacy models

**Target State**:
- All MCP tools return AgentJob + AgentExecution data
- Monitoring queries use new tables exclusively
- Orchestrator spawning creates dual-model records
- Zero MCPAgentJob references in tools/orchestration

---

## Files to Modify

| File | Refs | Action | Complexity | Priority |
|------|------|--------|------------|----------|
| `agent_health_monitor.py` | 23 | Update status checks | MEDIUM | HIGH |
| `orchestrator.py` | 21 | Migrate spawning logic | HIGH | CRITICAL |
| `staging_rollback.py` | 18 | Fix rollback queries | MEDIUM | HIGH |
| `thin_prompt_generator.py` | 17 | Remove fallback logic | LOW | MEDIUM |
| `tools/orchestration_tools.py` | 12 | Update MCP tool responses | MEDIUM | HIGH |
| `tools/agent_coordination.py` | 8 | Fix coordination queries | LOW | MEDIUM |
| `tools/context_tools.py` | 2 | Update context tracking | LOW | LOW |
| `tools/message_tools.py` | 1 | Fix message routing | LOW | LOW |

**Total**: 8 files, 102 references

---

## Implementation Steps

### Step 1: Migrate orchestrator.py Spawning Logic (2-3 hours)

**Target**: Agent spawning and lifecycle management (21 refs)

**Current Pattern**: Spawning creates MCPAgentJob directly

```python
# BEFORE
from ..models import MCPAgentJob
def spawn_agent(self, agent_name: str, mission: str, spawner_job_id: int):
    job = MCPAgentJob(
        agent_template_id=template_id,
        mission_text=mission,
        status="pending",
        spawned_by=spawner_job_id,  # int
        ...
    )
    self.session.add(job)
    self.session.commit()
    return job.job_id  # int
```

**New Pattern**: Spawning creates AgentJob + AgentExecution

```python
# AFTER
from ..models import AgentJob, AgentExecution
async def spawn_agent(
    self,
    agent_name: str,
    mission: str,
    spawner_agent_id: UUID,  # Changed from int
    product_id: UUID,
    tenant_key: str
):
    # Create work order
    agent_job = AgentJob(
        product_id=product_id,
        agent_name=agent_name,
        mission=mission,
        tenant_key=tenant_key
    )
    self.session.add(agent_job)
    await self.session.flush()

    # Create executor
    execution = AgentExecution(
        agent_id=agent_job.id,
        agent_name=agent_name,
        status="pending",
        spawned_by=spawner_agent_id  # UUID
    )
    self.session.add(execution)
    await self.session.commit()

    return agent_job.id  # UUID
```

**Key Changes**:
1. **Return type**: int → UUID
2. **spawned_by**: Uses agent_id (UUID) instead of job_id (int)
3. **Dual creation**: AgentJob + AgentExecution instead of single MCPAgentJob
4. **Async**: Use async session (already standard in codebase)

**Actions**:
1. Replace all MCPAgentJob spawning calls with dual-model creation
2. Update spawned_by parameter to accept UUID instead of int
3. Update return type annotations (int → UUID)
4. Replace `self.session.commit()` with `await self.session.commit()`
5. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/orchestration/test_orchestrator.py -v`
- Test agent spawning workflow end-to-end
- Verify spawned_by chain uses UUIDs

---

### Step 2: Update agent_health_monitor.py (2 hours)

**Target**: Agent health checks and staleness detection (23 refs)

**Current Pattern**: Health monitor queries MCPAgentJob for status/context

```python
# BEFORE
from ..models import MCPAgentJob
def check_agent_health(self, job_id: int):
    job = self.session.get(MCPAgentJob, job_id)
    if not job:
        return {"status": "not_found"}

    staleness = datetime.utcnow() - job.updated_at
    context_pct = (job.context_used / job.context_budget) * 100

    return {
        "job_id": job.job_id,
        "status": job.status,
        "staleness_seconds": staleness.total_seconds(),
        "context_usage_pct": context_pct
    }
```

**New Pattern**: Health monitor queries AgentExecution (join AgentJob for product info)

```python
# AFTER
from ..models import AgentJob, AgentExecution
async def check_agent_health(self, agent_id: UUID):
    result = await self.session.execute(
        select(AgentJob, AgentExecution)
        .join(AgentExecution, AgentJob.id == AgentExecution.agent_id)
        .where(AgentJob.id == agent_id)
    )
    row = result.one_or_none()
    if not row:
        return {"status": "not_found"}

    agent_job, execution = row
    staleness = datetime.utcnow() - execution.updated_at
    context_pct = (execution.context_used / execution.context_budget) * 100

    return {
        "agent_id": str(agent_job.id),
        "status": execution.status,
        "staleness_seconds": staleness.total_seconds(),
        "context_usage_pct": context_pct,
        "agent_name": execution.agent_name
    }
```

**Key Changes**:
1. **Parameter**: job_id (int) → agent_id (UUID)
2. **Query**: Join AgentJob + AgentExecution for complete health data
3. **Response**: job_id → agent_id, include agent_name
4. **Status Source**: AgentExecution.status (executor state)
5. **Context Source**: AgentExecution.context_used/context_budget (per-execution)

**Actions**:
1. Replace all MCPAgentJob health queries with joined queries
2. Update parameter types (int → UUID)
3. Update response DTOs (job_id → agent_id)
4. Source health metrics from AgentExecution (status, context, updated_at)
5. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/orchestration/test_agent_health_monitor.py -v`
- Test staleness detection with mock updated_at values
- Verify context usage calculations correct

---

### Step 3: Fix staging_rollback.py (1-2 hours)

**Target**: Orchestrator staging rollback operations (18 refs)

**Current Pattern**: Rollback deletes MCPAgentJob records created during staging

```python
# BEFORE
from ..models import MCPAgentJob
def rollback_staging(self, orchestrator_job_id: int):
    # Find all agents spawned by orchestrator
    children = self.session.execute(
        select(MCPAgentJob).where(MCPAgentJob.spawned_by == orchestrator_job_id)
    ).scalars().all()

    # Delete children
    for child in children:
        self.session.delete(child)

    # Delete orchestrator
    orchestrator = self.session.get(MCPAgentJob, orchestrator_job_id)
    self.session.delete(orchestrator)
    self.session.commit()
```

**New Pattern**: Rollback soft-deletes AgentExecution records (preserve AgentJob history)

```python
# AFTER
from ..models import AgentJob, AgentExecution
async def rollback_staging(self, orchestrator_agent_id: UUID):
    # Find all agents spawned by orchestrator
    result = await self.session.execute(
        select(AgentExecution)
        .where(AgentExecution.spawned_by == orchestrator_agent_id)
    )
    children = result.scalars().all()

    # Soft-delete children (set status = "cancelled")
    for child in children:
        child.status = "cancelled"
        child.error_message = "Rollback: staging failed"

    # Soft-delete orchestrator execution
    orch_result = await self.session.execute(
        select(AgentExecution)
        .where(AgentExecution.agent_id == orchestrator_agent_id)
    )
    orchestrator = orch_result.scalar_one()
    orchestrator.status = "cancelled"
    orchestrator.error_message = "Rollback: staging failed"

    await self.session.commit()
```

**Key Changes**:
1. **Soft Delete**: Set status = "cancelled" instead of DELETE
2. **Preserve History**: AgentJob records remain (work order history)
3. **Parameter**: orchestrator_job_id (int) → orchestrator_agent_id (UUID)
4. **Query**: Use spawned_by (UUID) to find children
5. **Error Message**: Document rollback reason

**Actions**:
1. Replace hard deletes with soft deletes (status update)
2. Update parameter types (int → UUID)
3. Add error_message field population
4. Preserve AgentJob records (only update AgentExecution)
5. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/orchestration/test_staging_rollback.py -v`
- Test rollback doesn't delete AgentJob records
- Verify cancelled agents not visible in active queries

---

### Step 4: Remove Fallback in thin_prompt_generator.py (1 hour)

**Target**: Legacy fallback logic in thin client prompt generation (17 refs)

**Current Pattern**: Generator falls back to MCPAgentJob if AgentJob not found

```python
# BEFORE
from ..models import AgentJob, MCPAgentJob
def generate_prompt(self, agent_id: UUID):
    agent_job = self.session.get(AgentJob, agent_id)
    if not agent_job:
        # Fallback to legacy model
        try:
            legacy_id = int(str(agent_id))  # Attempt conversion
            agent_job = self.session.get(MCPAgentJob, legacy_id)
        except:
            raise ValueError(f"Agent {agent_id} not found")
```

**New Pattern**: Generator uses AgentJob exclusively (no fallback)

```python
# AFTER
from ..models import AgentJob
async def generate_prompt(self, agent_id: UUID):
    agent_job = await self.session.get(AgentJob, agent_id)
    if not agent_job:
        raise ValueError(f"Agent {agent_id} not found")
```

**Key Changes**:
1. **Remove Fallback**: No MCPAgentJob lookup
2. **Error Handling**: Raise immediately if not found
3. **Simplicity**: Single model, single code path

**Actions**:
1. Remove all MCPAgentJob fallback logic
2. Remove try/except blocks for legacy conversion
3. Update error messages (no "legacy" mentions)
4. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/orchestration/test_thin_prompt_generator.py -v`
- Verify ValueError raised for invalid agent_id
- Test prompt generation with valid agent_id

---

### Step 5: Update tools/orchestration_tools.py (1-2 hours)

**Target**: MCP tools for orchestrator coordination (12 refs)

**Tools to Migrate**:

1. **`get_orchestrator_instructions(orchestrator_id, tenant_key)`**:
   - Replace MCPAgentJob query with AgentJob query
   - Return mission from AgentJob.mission (not MCPAgentJob.mission_text)

2. **`get_available_agents(tenant_key, active_only)`**:
   - Query AgentExecution for active agents (status != "cancelled")
   - Join AgentJob for product context

3. **`spawn_agent(agent_name, mission, spawner_agent_id, ...)`**:
   - Delegate to orchestrator.spawn_agent() (already migrated in Step 1)
   - Return agent_id (UUID) instead of job_id (int)

**Actions**:
1. Replace MCPAgentJob queries with AgentJob + AgentExecution
2. Update return types (job_id → agent_id, int → str for JSON)
3. Update parameter types (spawner_job_id → spawner_agent_id)
4. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/tools/test_orchestration_tools.py -v`
- Test MCP tool calls via HTTP endpoint (/mcp)
- Verify JSON responses use agent_id (str, UUID)

---

### Step 6: Fix tools/agent_coordination.py (30 minutes)

**Target**: Agent-to-agent coordination MCP tools (8 refs)

**Tools to Migrate**:

1. **`send_message_to_agent(recipient_agent_id, message, ...)`**:
   - Already uses agent_id (UUID) from 0367a migration
   - Verify no MCPAgentJob lookups for validation

2. **`check_peer_status(agent_id)`**:
   - Replace MCPAgentJob query with AgentExecution query
   - Return status from AgentExecution.status

**Actions**:
1. Replace MCPAgentJob status queries with AgentExecution queries
2. Verify message routing uses agent_id (UUID)
3. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/tools/test_agent_coordination.py -v`
- Test send_message with valid/invalid agent_id
- Test check_peer_status returns correct status

---

### Step 7: Update tools/context_tools.py (15 minutes)

**Target**: Context tracking MCP tools (2 refs)

**Tools to Migrate**:

1. **`report_context_usage(agent_id, context_used)`**:
   - Update AgentExecution.context_used (not MCPAgentJob)
   - Query AgentExecution by agent_id (UUID)

**Actions**:
1. Replace MCPAgentJob update with AgentExecution update
2. Verify agent_id parameter is UUID
3. Remove MCPAgentJob import

**Validation**:
- Run `pytest tests/tools/test_context_tools.py -v`
- Test context usage updates reflected in AgentExecution

---

### Step 8: Fix tools/message_tools.py (15 minutes)

**Target**: Message routing MCP tools (1 ref)

**Tools to Migrate**:

1. **`get_messages_for_agent(agent_id)`**:
   - Already uses agent_id (UUID) from 0367a migration
   - Verify no MCPAgentJob lookups

**Actions**:
1. Verify message queue uses agent_id (UUID) correctly
2. Remove any MCPAgentJob references (likely in comments)

**Validation**:
- Run `pytest tests/tools/test_message_tools.py -v`
- Test message retrieval by agent_id

---

## Success Criteria

### Code Quality
- [ ] Zero `MCPAgentJob` imports in `src/giljo_mcp/tools/*.py`
- [ ] Zero `MCPAgentJob` imports in `src/giljo_mcp/orchestration/*.py`
- [ ] Zero `mcp_agent_jobs` table queries in tools/orchestration
- [ ] All MCP tools use agent_id (UUID) parameters

### Functional Validation
- [ ] Orchestrator spawning creates AgentJob + AgentExecution
- [ ] Health monitoring queries AgentExecution for status/context
- [ ] Staging rollback soft-deletes executions (preserves jobs)
- [ ] Thin client prompts use AgentJob exclusively
- [ ] MCP tools return agent_id (str, UUID) in JSON responses

### MCP Tool Validation
- [ ] `get_orchestrator_instructions()` returns mission from AgentJob
- [ ] `get_available_agents()` queries AgentExecution for active agents
- [ ] `spawn_agent()` returns agent_id (UUID) instead of job_id (int)
- [ ] `check_peer_status()` returns status from AgentExecution
- [ ] `report_context_usage()` updates AgentExecution.context_used

### Testing
- [ ] `pytest tests/orchestration/` passes (all modules)
- [ ] `pytest tests/tools/` passes (all modules)
- [ ] Integration test: orchestrator spawn → agent execute → health check
- [ ] No test failures due to missing MCPAgentJob

---

## Rollback Plan

### If Issues Arise During Migration
1. **Stop immediately** - Do not proceed to next file
2. **Revert commits** - `git reset --hard HEAD~N` (N = commits since 0367c start)
3. **Verify dependencies** - Ensure 0367a/0367b intact (don't revert those)
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
- Run tool-specific test files after each step
- Verify MCP tool responses match expected schema
- Check error handling (invalid agent_id, not found)

### Integration Tests
- Test full orchestrator lifecycle: spawn → health check → rollback
- Verify MCP tool calls via HTTP endpoint (/mcp)
- Test multi-agent coordination (send_message, check_peer_status)

### MCP Tool Testing Checklist
- [ ] Call `get_orchestrator_instructions(agent_id, tenant_key)` → Returns mission
- [ ] Call `get_available_agents(tenant_key, active_only=True)` → Returns active agents
- [ ] Call `spawn_agent(agent_name, mission, spawner_agent_id, ...)` → Returns agent_id (UUID)
- [ ] Call `check_peer_status(agent_id)` → Returns status from AgentExecution
- [ ] Call `report_context_usage(agent_id, context_used)` → Updates AgentExecution

---

## MCP Tool Response Schema Updates

### Before (MCPAgentJob)
```json
{
  "job_id": 12345,
  "agent_name": "backend-integration-tester",
  "status": "running",
  "mission": "Test API endpoints"
}
```

### After (AgentJob + AgentExecution)
```json
{
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_name": "backend-integration-tester",
  "status": "running",
  "mission": "Test API endpoints"
}
```

**Key Changes**:
- `job_id` (int) → `agent_id` (str, UUID)
- mission from AgentJob.mission (not MCPAgentJob.mission_text)
- status from AgentExecution.status (not MCPAgentJob.status)

---

## Notes

### Why Tools/Orchestration Last?
- **Dependencies**: Tools consume service layer (0367a) and APIs (0367b)
- **MCP Isolation**: Tools are stateless; failures don't corrupt data
- **Testing**: Easier to test tools after foundation is solid

### Why Soft Delete in Rollback?
- **History**: Preserve work order history (AgentJob) for debugging
- **Auditability**: Track why staging failed (error_message)
- **Queries**: Cancelled agents excluded from active queries (status != "cancelled")

### Performance Considerations
- **Joins**: Health monitor queries join AgentJob + AgentExecution (~1-2ms overhead)
- **Indexes**: Ensure indexes on agent_executions.spawned_by, agent_executions.agent_id
- **MCP Tools**: Stateless, no caching; overhead negligible

### Orchestrator Spawning Semantics
- **Old**: spawn_agent() returns job_id (int, executor instance)
- **New**: spawn_agent() returns agent_id (UUID, work order)
- **Impact**: Callers must update to expect UUID instead of int
- **Benefit**: Work order ID stable across retries

---

## Related Documentation

- [0358_model_mapping_reference.md](Reference_docs/0358_model_mapping_reference.md) - Complete field mapping
- [docs/ORCHESTRATOR.md](../docs/ORCHESTRATOR.md) - Orchestrator lifecycle
- [docs/api/mcp_tools.md](../docs/api/mcp_tools.md) - MCP tool reference

---

**Next Step**: After completion, proceed to Handover 0367d (Validation & Deprecation)
