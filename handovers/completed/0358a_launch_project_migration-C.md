# Handover 0358a: ProjectService.launch_project() Migration

**Status**: PENDING
**Estimate**: 3-4 hours
**Priority**: HIGH
**Dependencies**: None (first in 0358 series)
**TDD Approach**: MANDATORY

---

## Executive Summary

Migrate `ProjectService.launch_project()` from creating `MCPAgentJob` directly to using the dual-model architecture (`AgentJob` + `AgentExecution`). This method creates the orchestrator agent when a project is launched and is the first critical migration in the 0358 series.

**Why this matters**: The current implementation creates `MCPAgentJob` directly, bypassing the new dual-model architecture established in Handover 0366a/b. This prevents proper job/execution separation and breaks succession tracking.

**Expected Outcome**: `launch_project()` creates:
1. One `AgentJob` (persistent work order for orchestrator mission)
2. One `AgentExecution` (first executor instance, instance_number=1)

---

## Scope Boundaries

### IN SCOPE

- Migrate `ProjectService.launch_project()` method (lines 1688-1853)
- Replace direct `MCPAgentJob` creation with `AgentJob` + `AgentExecution` pair
- Update return value to include both `job_id` and `agent_id`
- Maintain backward compatibility in API response structure
- Update all tests in `tests/api/test_launch_project_depth_config.py`
- Update unit tests in `tests/unit/test_project_service.py`

### OUT OF SCOPE

- Other methods in ProjectService (covered in 0358b-d)
- Frontend changes (covered in 0358e)
- API endpoint changes (response schema remains compatible)
- MCP tool changes (covered in 0358d)

---

## Files to Modify

| File | Lines | Change Description |
|------|-------|-------------------|
| `src/giljo_mcp/services/project_service.py` | 1688-1853 | Replace MCPAgentJob with AgentJob + AgentExecution |
| `src/giljo_mcp/services/project_service.py` | 30-40 | Update imports (add AgentJob, AgentExecution) |
| `tests/services/test_project_service_launch.py` | NEW | TDD tests for migration |
| `tests/api/test_launch_project_depth_config.py` | 168, 343, 488 | Update MCPAgentJob references |
| `tests/unit/test_project_service.py` | ~19 | Update MCPAgentJob import |

---

## Field Mapping (MCPAgentJob -> AgentJob + AgentExecution)

### Fields Moving to AgentJob (Work Order)

| MCPAgentJob Field | AgentJob Field | Notes |
|-------------------|----------------|-------|
| `job_id` | `job_id` | Primary key (UUID string) |
| `tenant_key` | `tenant_key` | Multi-tenant isolation |
| `project_id` | `project_id` | FK to projects |
| `mission` | `mission` | Agent instructions (stored ONCE) |
| `agent_type` | `job_type` | RENAME: "orchestrator" |
| `job_metadata` | `job_metadata` | field_priorities, depth_config, user_id |
| N/A | `template_id` | Optional FK to agent_templates |
| N/A | `status` | Job status: active/completed/cancelled |
| N/A | `created_at` | Auto-generated |
| N/A | `completed_at` | Set when job completes |

### Fields Moving to AgentExecution (Executor)

| MCPAgentJob Field | AgentExecution Field | Notes |
|-------------------|----------------------|-------|
| N/A (auto) | `agent_id` | Primary key (UUID string) |
| `job_id` | `job_id` | FK to AgentJob |
| `tenant_key` | `tenant_key` | Multi-tenant isolation |
| `agent_type` | `agent_type` | "orchestrator" |
| `agent_name` | `agent_name` | "Orchestrator #N" |
| `status` | `status` | Execution status: waiting/working/complete/etc. |
| `instance_number` | `instance_number` | Sequential (1, 2, 3...) |
| `context_used` | `context_used` | Current token usage |
| `context_budget` | `context_budget` | Max tokens allowed |
| `tool_type` | `tool_type` | Default "universal" |
| `spawned_by` | `spawned_by` | Parent agent_id |
| `progress` | `progress` | 0-100% |
| `messages` | `messages` | JSONB array |
| `health_status` | `health_status` | unknown/healthy/warning/critical/timeout |
| `last_progress_at` | `last_progress_at` | Activity timestamp |
| `started_at` | `started_at` | When started |
| `completed_at` | `completed_at` | When finished |

### Fields NOT Migrated (Stay in MCPAgentJob for Backward Compat)

These fields exist in MCPAgentJob but are not used by launch_project():
- `id` (autoincrement integer PK - not needed, job_id is sufficient)
- `block_reason` (set later, not at creation)
- `handover_to`, `handover_summary`, `handover_context_refs` (succession fields)
- `succession_reason` (set during succession)
- `estimated_completion` (not used)
- `failure_reason` (set on failure)
- `last_health_check`, `health_failure_count` (set by health monitoring)
- `last_message_check_at`, `mission_acknowledged_at` (set by MCP tools)
- `decommissioned_at` (set on decommission)

---

## Cascading Impact Analysis

### Direct Callers of launch_project()

1. **api/endpoints/projects/lifecycle.py:launch_project()** (lines 465-512)
   - Calls: `project_service.launch_project(project_id, user_id, launch_config)`
   - Expects: `{"success": True, "data": {"project_id", "orchestrator_job_id", "launch_prompt", "status"}}`
   - **Impact**: None - response structure unchanged
   - **orchestrator_job_id**: Will now be `job_id` from AgentJob (same semantics)

2. **Tests in tests/api/test_launch_project_depth_config.py**
   - Lines 168, 343: Query `MCPAgentJob` by `job_id` to verify creation
   - **Impact**: Must update to query `AgentJob` and `AgentExecution`

### Downstream Consumers of Created Job

The orchestrator_job_id returned is used by:

1. **MCP Tools** (via `get_orchestrator_instructions()`)
   - Currently queries `MCPAgentJob` by `job_id`
   - **Impact**: Out of scope (0358d) but must remain compatible
   - **Temporary Fix**: Can query both tables, AgentJob wins

2. **Frontend** (stores in Pinia store)
   - Uses `orchestrator_job_id` to track active orchestrator
   - **Impact**: None - still receives valid UUID

3. **WebSocket Events** (project:launched)
   - Broadcasts `orchestrator_job_id`
   - **Impact**: None - field value semantics unchanged

---

## Implementation Steps

### Phase 1: RED (Write Failing Tests First)

**File**: `tests/services/test_project_service_launch.py` (NEW)

Create new test file with these test classes:

1. **TestLaunchProjectCreatesAgentJobAndExecution**
   - `test_launch_creates_agent_job` - Verify AgentJob record exists with correct fields
   - `test_launch_creates_agent_execution` - Verify AgentExecution record with instance=1
   - `test_launch_returns_both_ids` - Response contains orchestrator_job_id
   - `test_launch_stores_depth_config_in_job_metadata` - job_metadata has depth_config, user_id
   - `test_launch_increments_instance_number` - Second launch has instance_number=2

2. **TestLaunchProjectDoesNotCreateMCPAgentJob**
   - `test_no_mcp_agent_job_created` - MCPAgentJob count unchanged after launch

### Phase 2: GREEN (Implement Migration)

**File**: `src/giljo_mcp/services/project_service.py`

**Step 1: Update Imports** (around line 35)

Add to existing imports:
```python
from giljo_mcp.models.agent_identity import AgentJob, AgentExecution
```

**Step 2: Replace MCPAgentJob Creation** (lines 1786-1808)

Replace current MCPAgentJob creation with:
1. Create AgentJob (work order) - stores mission, job_type, job_metadata
2. Create AgentExecution (executor) - stores instance_number, status, context settings

**Step 3: Update Instance Number Query** (lines 1775-1784)

Query from AgentExecution for instance_number with backward compat fallback to MCPAgentJob during transition period.

### Phase 3: REFACTOR (Clean Up)

After tests pass:
1. Remove backward compat MCPAgentJob query (once all jobs migrated)
2. Update docstring to reflect new architecture
3. Add logging for debugging

---

## TDD Test Plan

| Test Name | File | Assertion |
|-----------|------|-----------|
| `test_launch_creates_agent_job` | `tests/services/test_project_service_launch.py` | AgentJob record exists with correct fields |
| `test_launch_creates_agent_execution` | `tests/services/test_project_service_launch.py` | AgentExecution record exists with instance=1 |
| `test_launch_returns_both_ids` | `tests/services/test_project_service_launch.py` | Response contains orchestrator_job_id |
| `test_launch_stores_depth_config_in_job_metadata` | `tests/services/test_project_service_launch.py` | job_metadata has depth_config, user_id |
| `test_launch_increments_instance_number` | `tests/services/test_project_service_launch.py` | Second launch has instance_number=2 |
| `test_no_mcp_agent_job_created` | `tests/services/test_project_service_launch.py` | MCPAgentJob count unchanged after launch |

**Existing Tests to Update**:

| Test File | Changes Needed |
|-----------|---------------|
| `tests/api/test_launch_project_depth_config.py` | Replace `MCPAgentJob` queries with `AgentJob` |
| `tests/unit/test_project_service.py` | Update mock to use AgentJob/AgentExecution |

---

## Rollback Strategy

### If Tests Fail After Deployment

1. **Immediate**: Revert commit (single file change)
2. **Data**: No data migration needed - both tables exist simultaneously
3. **Verification**: Run `pytest tests/services/test_project_service_launch.py -v`

### Database Considerations

- AgentJob and AgentExecution tables already exist (Handover 0366a)
- MCPAgentJob table remains unchanged (backward compat)
- No migration scripts needed for this handover

---

## Success Criteria

| Criteria | Verification |
|----------|-------------|
| All new TDD tests pass | `pytest tests/services/test_project_service_launch.py -v` |
| Existing launch tests pass | `pytest tests/api/test_launch_project_depth_config.py -v` |
| No MCPAgentJob created | Verified by `test_no_mcp_agent_job_created` |
| AgentJob + AgentExecution created | Verified by individual tests |
| API response unchanged | Verify `orchestrator_job_id` returned |
| WebSocket events work | Manual test: launch project, observe dashboard |

---

## Commit Message Template

```
feat(0358a): migrate launch_project() to AgentJob + AgentExecution

Handover 0358a: ProjectService.launch_project() Migration

BREAKING CHANGE: None (backward compatible)

Changes:
- Replace MCPAgentJob creation with AgentJob + AgentExecution pair
- AgentJob stores mission and job_metadata (stored ONCE)
- AgentExecution stores execution state (instance_number, status, etc.)
- Instance number query checks both tables during transition
- All existing tests updated and passing

Test coverage:
- tests/services/test_project_service_launch.py (6 new tests)
- tests/api/test_launch_project_depth_config.py (updated)

Generated with Claude Code
```

---

## Related Handovers

| Handover | Status | Dependency |
|----------|--------|------------|
| 0366a: Schema and Models | COMPLETE | Creates AgentJob/AgentExecution tables |
| 0366b: Service Layer Updates | COMPLETE | AgentJobManager.spawn_agent() pattern |
| 0358b: Other ProjectService Methods | PENDING | Depends on 0358a |
| 0358c: MCP Tool Updates | PENDING | Depends on 0358a |
| 0358d: Frontend Updates | PENDING | Depends on 0358c |

---

## Notes for Implementor

1. **TDD is MANDATORY**: Write tests FIRST, verify they FAIL, then implement
2. **Do NOT modify MCPAgentJob**: It remains for backward compat
3. **Instance number transition**: Query BOTH tables during transition period
4. **Test with real database**: Integration tests, not just mocks
5. **WebSocket events**: Verify manually after implementation

## Estimated Timeline

| Phase | Duration |
|-------|----------|
| RED (write failing tests) | 1 hour |
| GREEN (implement migration) | 1.5 hours |
| REFACTOR (clean up, update existing tests) | 1 hour |
| Manual verification | 0.5 hours |
| **Total** | **4 hours** |