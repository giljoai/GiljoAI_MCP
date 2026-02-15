# Handover 0358b: OrchestrationService Migration to Dual-Model Architecture

**Status**: PENDING
**Estimate**: 8-10 hours
**Priority**: HIGH
**Dependencies**: 0366a (schema complete), 0366b (AgentJobManager pattern reference)

---

## Executive Summary

Migrate OrchestrationService from monolithic MCPAgentJob model to the dual-model architecture (AgentJob + AgentExecution) established in Handover 0366a/b. This enables proper separation between work orders (jobs) and executors (executions), supporting orchestrator succession without duplicating mission data.

**Impact**: 12 methods across 1624 lines of code require migration. Primary concern is maintaining backward compatibility with existing MCP tools and API endpoints.

---

## Scope Boundaries

### IN SCOPE
- spawn_agent_job() - CREATE job + execution
- get_agent_mission() - QUERY with team context generation
- get_workflow_status() - QUERY with status aggregation
- get_pending_jobs() - QUERY with status filtering
- acknowledge_job() - UPDATE execution status
- report_progress() - UPDATE with MessageService integration
- complete_job() - UPDATE execution status
- report_error() - UPDATE execution status
- list_jobs() - QUERY with pagination
- update_context_usage() - UPDATE with succession trigger
- trigger_succession() - CREATE successor execution
- _trigger_auto_succession() - Internal helper
- Helper functions: _generate_team_context_header(), _generate_agent_protocol()

### OUT OF SCOPE
- orchestrate_project() - Uses ProjectOrchestrator, no direct MCPAgentJob access
- MCP tools (src/giljo_mcp/tools/orchestration.py) - Separate handover 0358c
- API endpoints (api/endpoints/agent_jobs/) - Separate handover 0358d

---

## Method Inventory

| Method | Lines | Operation Type | Complexity | Notes |
|--------|-------|---------------|------------|-------|
| spawn_agent_job() | 433-611 | CREATE | HIGH | Creates MCPAgentJob, WebSocket broadcast |
| get_agent_mission() | 612-788 | QUERY/UPDATE | HIGH | Team context header, mission acknowledgment |
| get_workflow_status() | 345-427 | QUERY | MEDIUM | Status aggregation across jobs |
| get_pending_jobs() | 790-848 | QUERY | LOW | Simple filter by status |
| acknowledge_job() | 850-959 | UPDATE | MEDIUM | Status transition, WebSocket |
| report_progress() | 961-1109 | UPDATE | MEDIUM | MessageService integration |
| complete_job() | 1111-1203 | UPDATE | MEDIUM | Status transition, WebSocket |
| report_error() | 1205-1258 | UPDATE | LOW | Simple status update |
| list_jobs() | 1260-1402 | QUERY | MEDIUM | Pagination, steps summary |
| update_context_usage() | 1404-1466 | UPDATE | MEDIUM | Succession trigger |
| trigger_succession() | 1527-1623 | CREATE | HIGH | Creates successor MCPAgentJob |
| _trigger_auto_succession() | 1486-1525 | CREATE | MEDIUM | Internal helper |
| _generate_team_context_header() | 48-150 | HELPER | LOW | Type hints only |
| _generate_agent_protocol() | 153-230 | HELPER | LOW | No MCPAgentJob access |

---

## Files to Modify

### Primary Files
| File | Changes Required |
|------|-----------------|
| src/giljo_mcp/services/orchestration_service.py | Full migration (1624 lines) |
| src/giljo_mcp/models/__init__.py | Add AgentJob, AgentExecution imports |

### Test Files (Update Required)
| File | Test Count | Priority |
|------|-----------|----------|
| tests/unit/test_orchestration_service.py | 15+ tests | HIGH |
| tests/services/test_orchestration_service_agent_mission.py | 8+ tests | HIGH |
| tests/services/test_orchestration_service_team_awareness.py | 5+ tests | HIGH |
| tests/services/test_orchestration_service_websocket_emissions.py | 6+ tests | MEDIUM |
| tests/services/test_orchestration_service_context.py | 4+ tests | MEDIUM |
| tests/services/test_orchestration_service_cli_rules.py | 3+ tests | LOW |
| tests/services/test_orchestration_service_0366b.py | 10+ tests | HIGH |

### API Endpoints (Downstream - Inform Only)
| File | Impact |
|------|--------|
| api/endpoints/agent_jobs/orchestration.py | Uses OrchestrationService methods |
| api/endpoints/agent_jobs/lifecycle.py | Uses OrchestrationService methods |
| api/endpoints/agent_jobs/progress.py | Uses OrchestrationService methods |
| api/endpoints/agent_jobs/succession.py | Uses OrchestrationService methods |

---

## Field Mapping: MCPAgentJob to AgentJob + AgentExecution

### MCPAgentJob Field to New Model Mapping

| MCPAgentJob Field | Target Model | Target Field | Notes |
|-------------------|--------------|--------------|-------|
| id (Integer PK) | - | - | Dropped (use UUIDs) |
| job_id | AgentJob | job_id | PK in new model |
| tenant_key | BOTH | tenant_key | Duplicated for query performance |
| project_id | AgentJob | project_id | FK to projects |
| agent_type | AgentExecution | agent_type | Executor property |
| agent_name | AgentExecution | agent_name | Executor property |
| mission | AgentJob | mission | Work order property |
| status | AgentExecution | status | Executor status |
| spawned_by | AgentExecution | spawned_by | Points to agent_id |
| context_chunks | - | - | Dropped (use fetch_context) |
| messages | AgentExecution | messages | Executor messages |
| started_at | AgentExecution | started_at | Executor timestamp |
| completed_at | AgentExecution | completed_at | Executor timestamp |
| created_at | AgentJob | created_at | Job creation |
| progress | AgentExecution | progress | Executor progress |
| block_reason | AgentExecution | block_reason | Executor state |
| current_task | AgentExecution | current_task | Executor state |
| estimated_completion | - | - | Dropped (rarely used) |
| tool_type | AgentExecution | tool_type | Executor property |
| instance_number | AgentExecution | instance_number | Succession tracking |
| handover_to | AgentExecution | succeeded_by | Renamed for clarity |
| handover_summary | AgentExecution | handover_summary | Executor state |
| handover_context_refs | - | - | Dropped (use fetch_context) |
| succession_reason | AgentExecution | succession_reason | Executor state |
| context_used | AgentExecution | context_used | Executor tracking |
| context_budget | AgentExecution | context_budget | Executor tracking |
| job_metadata | AgentJob | job_metadata | Work order config |
| last_health_check | AgentExecution | last_health_check | Executor health |
| health_status | AgentExecution | health_status | Executor health |
| health_failure_count | AgentExecution | health_failure_count | Executor health |
| last_progress_at | AgentExecution | last_progress_at | Executor activity |
| last_message_check_at | AgentExecution | last_message_check_at | Executor activity |
| decommissioned_at | AgentExecution | decommissioned_at | Executor lifecycle |
| mission_acknowledged_at | AgentExecution | mission_acknowledged_at | Executor lifecycle |
| template_id | AgentJob | template_id | Work order property |
| failure_reason | AgentExecution | failure_reason | Executor state |

### Key Semantic Changes
1. **job_id** - Now refers to WORK ORDER (persists across succession)
2. **agent_id** - NEW - Refers to EXECUTOR (changes on succession)
3. **spawned_by** - Now points to agent_id (executor), not job_id
4. **handover_to** - Renamed to succeeded_by (executor chain)

---

## Cascading Impact Analysis

### Return Value Changes

Several methods return dictionaries with job_id fields. After migration:

| Method | Current Return | New Return | Breaking Change |
|--------|---------------|------------|-----------------|
| spawn_agent_job() | {"agent_job_id": uuid} | {"job_id": uuid, "agent_id": uuid} | YES - New field |
| get_agent_mission() | {"agent_job_id": uuid} | {"job_id": uuid, "agent_id": uuid} | YES - New field |
| list_jobs() | [{"job_id": uuid}] | [{"job_id": uuid, "agent_id": uuid}] | YES - New field |
| trigger_succession() | {"successor_job_id": uuid} | {"successor_agent_id": uuid} | YES - Renamed |

### Callers That Must Be Updated

1. **MCP Tools** (src/giljo_mcp/tools/orchestration.py):
   - Uses spawn_agent_job() result directly
   - Must extract agent_id for protocol generation

2. **API Endpoints** (api/endpoints/agent_jobs/):
   - launch_project() uses MCPAgentJob directly - needs migration
   - WebSocket broadcasts use job_id - may need agent_id

3. **WebSocket Events**:
   - agent:created - Should include both job_id and agent_id
   - agent:status_changed - Currently uses job_id, may need agent_id

---

## Implementation Steps (Ordered)

### Phase 1: Import Updates (30 min)
1. Add imports for AgentJob, AgentExecution from giljo_mcp.models.agent_identity
2. Keep MCPAgentJob import temporarily for deprecation warnings
3. Update type hints in helper functions

### Phase 2: spawn_agent_job() Migration (2 hours)


```python
# BEFORE (MCPAgentJob)
agent_job = MCPAgentJob(
    job_id=agent_job_id,
    project_id=project_id,
    tenant_key=tenant_key,
    agent_type=agent_type,
    agent_name=agent_name,
    mission=mission,
    spawned_by=parent_job_id,
    status="waiting",
    metadata=metadata_dict,
)

# AFTER (AgentJob + AgentExecution)
job = AgentJob(
    job_id=agent_job_id,
    project_id=project_id,
    tenant_key=tenant_key,
    job_type=agent_type,  # Note: renamed field
    mission=mission,
    job_metadata=metadata_dict,
)
execution = AgentExecution(
    agent_id=str(uuid4()),  # NEW: separate executor ID
    job_id=job.job_id,
    tenant_key=tenant_key,
    agent_type=agent_type,
    agent_name=agent_name,
    instance_number=1,
    spawned_by=parent_job_id,  # Points to agent_id of parent
    status="waiting",
)
session.add(job)
session.add(execution)
```

### Phase 3: Query Method Migrations (2 hours)
Migrate in order of complexity:
1. get_pending_jobs() - Simple query
2. get_workflow_status() - Join required
3. list_jobs() - Complex with pagination
4. get_agent_mission() - Team context requires joins

### Phase 4: Update Method Migrations (2 hours)
Migrate in order:
1. report_error() - Simple update
2. acknowledge_job() - Status transition
3. complete_job() - Status + WebSocket
4. report_progress() - MessageService integration
5. update_context_usage() - Succession trigger

### Phase 5: Succession Migrations (1.5 hours)
1. _trigger_auto_succession() - Creates new execution, NOT new job
2. trigger_succession() - Creates new execution, links via succeeded_by

### Phase 6: Helper Function Updates (30 min)
1. _generate_team_context_header() - Update type hints
2. _generate_agent_protocol() - No changes needed

### Phase 7: Test Updates (1.5 hours)
1. Update mock fixtures to use dual-model
2. Fix assertions for new return fields
3. Add new tests for agent_id vs job_id semantics

---

## TDD Test Plan

### RED Phase Tests (Write First)

```python
# tests/services/test_orchestration_service_dual_model.py

class TestSpawnAgentJobDualModel:
    """Verify spawn_agent_job creates BOTH AgentJob and AgentExecution."""

    @pytest.mark.asyncio
    async def test_spawn_creates_both_job_and_execution(self, orchestration_service):
        result = await orchestration_service.spawn_agent_job(
            agent_type="implementer", agent_name="impl-1",
            mission="Test mission", project_id=project_id, tenant_key="tenant-test"
        )
        assert result["success"] is True
        assert "job_id" in result
        assert "agent_id" in result
        assert result["job_id"] != result["agent_id"]


class TestSuccessionDualModel:
    """Verify succession creates new execution, not new job."""

    @pytest.mark.asyncio
    async def test_succession_creates_new_execution_same_job(self, orchestration_service):
        spawn_result = await orchestration_service.spawn_agent_job(
            agent_type="orchestrator", mission="Orchestrate", 
            project_id=project_id, tenant_key="tenant-test"
        )
        succession_result = await orchestration_service.trigger_succession(
            job_id=spawn_result["agent_id"], reason="context_limit", tenant_key="tenant-test"
        )
        assert succession_result["success"] is True


class TestQueryMethodsDualModel:
    """Verify query methods use correct joins."""

    @pytest.mark.asyncio
    async def test_list_jobs_returns_both_ids(self, orchestration_service):
        result = await orchestration_service.list_jobs(tenant_key="tenant-test")
        for job_dict in result["jobs"]:
            assert "job_id" in job_dict
            assert "agent_id" in job_dict
```

### GREEN Phase Implementation

Implement migrations following Phase 2-6 steps until all RED tests pass.

### REFACTOR Phase

1. Remove MCPAgentJob import
2. Add deprecation warnings for old field names
3. Update docstrings to reference dual-model architecture

---

## Rollback Strategy

### Immediate Rollback
```bash
git revert HEAD
```

### Partial Rollback (If Only Tests Fail)
```bash
git checkout HEAD~1 -- tests/services/test_orchestration_*.py
```

### Database Rollback
Not required - AgentJob and AgentExecution tables already exist from 0366a.

---

## Success Criteria

### Functional Requirements
- [ ] All existing API endpoints work with same request/response format
- [ ] WebSocket events include both job_id and agent_id
- [ ] Succession creates new execution, not new job
- [ ] Mission is stored once per job (no duplication)
- [ ] All existing tests pass after migration

### Performance Requirements
- [ ] list_jobs() query time <= current (indexed joins)
- [ ] spawn_agent_job() creates 2 records atomically
- [ ] No N+1 query patterns in workflow status

### Test Coverage
- [ ] >80% line coverage for migrated methods
- [ ] Unit tests for each method dual-model behavior
- [ ] Integration tests for succession flow

---

## Commit Message Template

```
feat(0358b): migrate OrchestrationService to dual-model architecture

- Migrate spawn_agent_job() to create AgentJob + AgentExecution
- Migrate query methods (list_jobs, get_workflow_status, get_pending_jobs)
- Migrate update methods (acknowledge_job, complete_job, report_progress)
- Migrate succession methods to create new execution, not new job
- Update return values to include both job_id and agent_id
- Update tests for dual-model semantics

BREAKING CHANGE: Return values now include agent_id in addition to job_id


```

---

## Appendix: Migration Pattern Reference

The AgentJobManager service (src/giljo_mcp/services/agent_job_manager.py) provides the canonical pattern for dual-model operations. Use this pattern for all CREATE operations in OrchestrationService migration.

---

## Related Handovers

- **0366a**: Schema and Models - AgentJob/AgentExecution definitions
- **0366b**: Service Layer Updates - AgentJobManager implementation
- **0358**: Parent handover for WebSocket and UI state overhaul
- **0358c**: MCP Tools Migration (future)
- **0358d**: API Endpoints Migration (future)
