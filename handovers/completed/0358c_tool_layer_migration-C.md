# Handover 0358c: Tool Layer Migration - MCPAgentJob to AgentJob + AgentExecution

**Status**: PENDING
**Date**: 2025-12-20
**Estimate**: 8-12 hours
**Priority**: MEDIUM
**Dependencies**: 0366a (models), 0366b (services), 0366c (partial tool updates)

---

## Executive Summary

This handover addresses the remaining tool layer files that still use the deprecated MCPAgentJob model directly. The 0366 series (a, b, c) established the new AgentJob + AgentExecution identity model and migrated high-traffic tools. This handover completes the migration for the remaining tool files: agent.py, tool_accessor.py, and claude_code_integration.py.

**Impact**: 3 tool files with 50+ MCPAgentJob references need migration.

**Key Challenge**: These files contain legacy code patterns that predate the 0366 refactor. They mix concerns (database access, business logic, WebSocket events) and will require careful untangling.

---

## Scope Boundaries

### IN SCOPE (Files to Migrate)

| File | MCPAgentJob Occurrences | Methods Affected | Migration Complexity |
|------|------------------------|------------------|---------------------|
| tools/agent.py | 34 | 10 functions (launch_agent, ensure_agent, decommission, health, handoff, etc.) | HIGH |
| tools/tool_accessor.py | 12 | 6 methods (get_orchestrator_instructions, spawn_agent_job, get_agent_mission, get_workflow_status, etc.) | MEDIUM |
| tools/claude_code_integration.py | 4 | 2 functions (get_agent_mapping, generate_orchestrator_prompt) | LOW |

### OUT OF SCOPE (Already Migrated in 0366c)

These tools were migrated in the 0366 series and should NOT be touched:

| File | Status | Migrated By |
|------|--------|-------------|
| agent_communication.py | COMPLETE | 0366c |
| agent_coordination.py | COMPLETE | 0366c |
| agent_job_status.py | COMPLETE | 0366c |
| agent_status.py | COMPLETE | 0366c |
| context.py | COMPLETE | 0366c |
| succession_tools.py | COMPLETE | 0366c |
| project.py | COMPLETE | 0366c-2 |
| orchestration.py | PARTIAL (spawn_agent_job still uses MCPAgentJob) | 0366c |

### SPECIAL CASE: orchestration.py

The orchestration.py file has **partial migration**:
- Functions like get_agent_mission() already use AgentJob/AgentExecution
- But spawn_agent_job() at lines 830-880 still creates MCPAgentJob records
- **Decision**: Include spawn_agent_job migration in THIS handover (not 0366c)


---

## Tool File Inventory

### 1. tools/agent.py (34 occurrences - HIGH priority)

**Import Statement** (line 15):
    from giljo_mcp.models import AgentInteraction, Job, MCPAgentJob, Message, Project, Task

**Functions Using MCPAgentJob**:

| Function | Lines | MCPAgentJob Usage | Migration Action |
|----------|-------|-------------------|-----------------|
| launch_agent() | 28-130 | Query by job_id, update status | Replace with AgentExecution query |
| log_interaction_legacy() | N/A | Query for parent_agent | Migrate to AgentExecution |
| _ensure_agent_with_session() | 154-210 | Query and create agents | Split into AgentJob + AgentExecution |
| _decommission_agent_with_session() | 222-270 | Query and update status | Update AgentExecution status |
| _get_agent_health_with_session() | 277-330 | Query single/all agents | Query AgentExecution table |
| _handoff_agent_work_with_session() | 332-400 | Transfer work between agents | Create successor AgentExecution |
| register_agent_tools/ensure_agent | 394-410 | Query agent by project/name | Update to use AgentJob lookup |
| register_agent_tools/activate_agent | 481-520 | Update agent status | Update AgentExecution status |
| register_agent_tools/assign_job | 561+ | Query agent, update mission | Update AgentJob.mission |
| register_agent_tools/agent_health | 753+ | Query agents for project | Query AgentExecution table |
| register_agent_tools/spawn_and_log_sub_agent | 818+ | Create and track sub-agents | Create AgentJob + AgentExecution |
| register_agent_tools/log_sub_agent_completion | 1031+ | Query parent agent | Query AgentExecution.spawned_by |

### 2. tools/tool_accessor.py (12 occurrences - MEDIUM priority)

**Import Statements** (line 16, plus 4 inline imports):
    from giljo_mcp.models import MCPAgentJob, Message, Product, Project, Task

**Methods Using MCPAgentJob**:

| Method | Lines | MCPAgentJob Usage | Migration Action |
|--------|-------|-------------------|-----------------|
| get_orchestrator_instructions() | 480-575 | Query orchestrator by job_id | Query AgentExecution, join to AgentJob |
| spawn_agent_job() | ~790-850 | Query job by current_job_id | Query AgentExecution |
| get_agent_mission() | 864-920 | Query job by job_id | Query AgentExecution, get AgentJob.mission |
| get_workflow_status() | 1294-1370 | Check/create orchestrator | Check/create AgentJob + AgentExecution |
| get_pending_jobs() | 1358-1400 | Query jobs by project | Query AgentJob table |

### 3. tools/claude_code_integration.py (4 occurrences - LOW priority)

**Import Statement** (line 11):
    from ..models import MCPAgentJob, Project

**Functions Using MCPAgentJob**:

| Function | Lines | MCPAgentJob Usage | Migration Action |
|----------|-------|-------------------|-----------------|
| register_claude_code_tools/get_agent_mapping() | 80-95 | Query active jobs | Query AgentJob + AgentExecution |

### 4. tools/orchestration.py - spawn_agent_job() (SPECIAL CASE)

**Affected Code** (lines 830-880) - Currently creates MCPAgentJob directly.

**Migration Action**: Create BOTH AgentJob AND AgentExecution, following pattern from project.py.

---

## MCP Tool Contract Analysis

### Breaking API Changes

The following MCP tools expose job-related fields in their responses. API contracts must be preserved.

| Tool | Current Response | Migration Impact |
|------|-----------------|------------------|
| spawn_agent_job() | {"agent_job_id": "uuid", ...} | Add agent_id for executor UUID |
| get_orchestrator_instructions() | {"job_id": "uuid", ...} | Add agent_id for executor UUID |
| get_agent_mission() | Job fields directly | Return both job_id and agent_id |
| agent_health() | Array of agent statuses | Use AgentExecution fields |

### Backward Compatibility Strategy

1. **Preserve existing response fields**: Keep agent_job_id and job_id in responses
2. **Add new fields**: Include agent_id where executors are involved
3. **Document deprecation**: Add comments marking old fields for removal in v4.0


---

## Implementation Steps

### Phase 1: agent.py Migration (4-6 hours)

**Order of operations** (dependency-driven):

1. **Update import statement** (line 15):
   - Remove MCPAgentJob from giljo_mcp.models import
   - Add: from giljo_mcp.models.agent_identity import AgentJob, AgentExecution

2. **Migrate launch_agent()** (lines 28-130):
   - Query AgentExecution by agent_id (not MCPAgentJob by job_id)
   - Update AgentExecution.status

3. **Migrate _ensure_agent_with_session()** (lines 154-210):
   - Query AgentJob by project_id + agent_type
   - If not exists, create AgentJob first, then AgentExecution
   - Use AgentJobManager for coordinated creation

4. **Migrate _decommission_agent_with_session()** (lines 222-270):
   - Query AgentExecution by agent_name + project_id
   - Set AgentExecution.status = "decommissioned"
   - Set AgentJob.status = "completed" if all executions done

5. **Migrate _get_agent_health_with_session()** (lines 277-330):
   - Query AgentExecution table instead of MCPAgentJob

6. **Migrate _handoff_agent_work_with_session()** (lines 332-400):
   - Create new AgentExecution for successor
   - Set current.succeeded_by = new.agent_id
   - Set new.spawned_by = current.agent_id

7. **Migrate register_agent_tools functions** (lines 394+):
   - Update all @mcp.tool() decorated functions to use new models

### Phase 2: tool_accessor.py Migration (2-3 hours)

1. **Update import statement** (line 16)

2. **Migrate get_orchestrator_instructions()** (lines 480-575):
   - Query AgentExecution first
   - Join to AgentJob for mission and metadata
   - Return both job_id and agent_id

3. **Migrate spawn_agent_job()** (lines 790-850):
   - Replace MCPAgentJob query with AgentExecution query

4. **Migrate get_agent_mission()** (lines 864-920):
   - Query AgentExecution by job_id
   - Return AgentJob.mission (via relationship)

5. **Migrate get_workflow_status()** (lines 1294-1370):
   - Check for existing AgentJob (not MCPAgentJob)
   - Create AgentJob + AgentExecution if needed

6. **Migrate get_pending_jobs()** (lines 1358-1400):
   - Query AgentJob table for project

### Phase 3: claude_code_integration.py Migration (1 hour)

1. **Update import statement** (line 11)

2. **Migrate get_agent_mapping()** (lines 80-95):
   - Query AgentJob + AgentExecution
   - Map agent_type from AgentExecution (or AgentJob.job_type)

### Phase 4: orchestration.py spawn_agent_job() (1-2 hours)

1. **Locate spawn_agent_job()** (lines 760-960)

2. **Replace MCPAgentJob creation** (lines 865-880):
   - Create AgentJob (work order) first
   - Then create AgentExecution (executor)

3. **Update response** (lines 952-960):
   - Add agent_id to response

---

## TDD Test Plan

### New Tests to Create

| Test File | Test Cases | Priority |
|-----------|------------|----------|
| tests/tools/test_agent_0358c.py | launch_agent uses AgentExecution, ensure_agent creates both models, decommission updates both, health queries AgentExecution, handoff creates succession chain | HIGH |
| tests/tools/test_tool_accessor_0358c.py | get_orchestrator_instructions joins tables, spawn_agent_job returns agent_id, get_agent_mission via AgentJob.mission | HIGH |
| tests/tools/test_claude_code_integration_0358c.py | get_agent_mapping uses new models | LOW |
| tests/tools/test_spawn_agent_job_0358c.py | Creates AgentJob + AgentExecution, returns both IDs | HIGH |

### Existing Tests to Verify (Regression)

Run all 0366c tests to ensure no regressions:
    python -m pytest tests/tools/test_*_0366c.py -v --no-cov


---

## Rollback Strategy

### If Migration Fails

1. **Revert file changes**: git checkout HEAD -- src/giljo_mcp/tools/{agent,tool_accessor,claude_code_integration,orchestration}.py
2. **MCPAgentJob still exists**: Database table unchanged (no migration needed)
3. **0366c tools unaffected**: They use AgentJob/AgentExecution independently

### Partial Rollback

If only one file fails:
- Revert that specific file
- Other files can remain migrated
- Document partial state in git commit message

---

## Success Criteria

### Functional Requirements
- [ ] All 50+ MCPAgentJob references in scope files replaced
- [ ] agent.py uses AgentJob + AgentExecution for all operations
- [ ] tool_accessor.py uses AgentJob + AgentExecution
- [ ] claude_code_integration.py uses AgentJob + AgentExecution
- [ ] orchestration.py spawn_agent_job() creates both models
- [ ] API responses include both job_id and agent_id where applicable

### Quality Requirements
- [ ] All new tests pass (test_*_0358c.py files)
- [ ] All 0366c regression tests pass
- [ ] No runtime errors in tool layer
- [ ] Backward compatibility maintained (old response fields preserved)

### Test Coverage
- [ ] >80% coverage for modified functions
- [ ] Integration tests for spawn -> mission -> completion workflow
- [ ] Tenant isolation tests for all modified tools

---

## Migration Pattern Reference

### Pattern 1: Simple Query Replacement

**Before**:
    query = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id)

**After**:
    query = select(AgentExecution).where(AgentExecution.agent_id == agent_id)

### Pattern 2: Creation (Dual Model)

**Before**: Create MCPAgentJob with all fields

**After**:
    job_id = str(uuid4())
    agent_id = str(uuid4())

    # Create work order
    agent_job = AgentJob(job_id=job_id, tenant_key=tenant_key, project_id=project_id,
                         mission=mission, job_type=agent_type, status="active")
    session.add(agent_job)

    # Create executor
    agent_execution = AgentExecution(agent_id=agent_id, job_id=job_id, tenant_key=tenant_key,
                                     agent_type=agent_type, instance_number=1, status="waiting")
    session.add(agent_execution)

### Pattern 3: Status Updates

**Before**: agent.status = "complete"

**After**:
    # Update execution (executor) status
    execution.status = "complete"
    # Optionally update job (work order) if all executions done
    job.status = "completed"  # Note: different value for job vs execution

---

## Cascading Impact Analysis

### Frontend Components

These components consume tool responses and may need updates:

| Component | Affected Response | Impact |
|-----------|------------------|--------|
| JobsTab.vue | agent_health, spawn_agent_job | May need agent_id handling |
| AgentTableView.vue | get_pending_jobs | Already uses agent_id from 0366d |
| StatusChip.vue | Status values | No impact (status values unchanged) |

### WebSocket Events

Events emitted by tools must continue working:

| Event | Emitter | Fields | Impact |
|-------|---------|--------|--------|
| agent:created | spawn_agent_job | agent_id, agent_job_id | Add agent_id field |
| agent:status_changed | launch_agent, decommission | status | No change needed |
| sub_agent:spawned | spawn_and_log_sub_agent | parent_id, child_id | Use agent_id for both |


---

## Commit Message Template

    feat(0358c): migrate tool layer from MCPAgentJob to AgentJob + AgentExecution

    Files migrated:
    - src/giljo_mcp/tools/agent.py (34 occurrences)
    - src/giljo_mcp/tools/tool_accessor.py (12 occurrences)
    - src/giljo_mcp/tools/claude_code_integration.py (4 occurrences)
    - src/giljo_mcp/tools/orchestration.py spawn_agent_job() (1 function)

    Changes:
    - All agent queries now use AgentExecution table
    - All agent creation now creates AgentJob + AgentExecution pair
    - API responses include both job_id and agent_id for backward compat
    - Status updates target AgentExecution (not job)
    - Succession tracking via spawned_by/succeeded_by on AgentExecution

    Tests:
    - Added test_agent_0358c.py
    - Added test_tool_accessor_0358c.py
    - Added test_spawn_agent_job_0358c.py
    - All 0366c regression tests passing



---

## Related Handovers

| Handover | Relationship | Status |
|----------|--------------|--------|
| 0366a | Models (AgentJob, AgentExecution) | COMPLETE |
| 0366b | Services (AgentJobManager) | COMPLETE |
| 0366c | High-traffic tool migration | COMPLETE |
| 0366c-2 | project.py completion | COMPLETE |
| 0366d-1 to 0366d-4 | Frontend + docs | COMPLETE |
| 0358 | WebSocket state overhaul | PENDING |
| 0358c | THIS handover | PENDING |

---

## Kickoff Prompt

    Mission: Implement Handover 0358c - Tool layer migration from MCPAgentJob to AgentJob + AgentExecution

    Context: The 0366 series established the AgentJob + AgentExecution identity model. Most high-traffic tools
    were migrated in 0366c. This handover completes the remaining tool files.

    Files to Migrate:
    1. tools/agent.py (34 references) - HIGH priority
    2. tools/tool_accessor.py (12 references) - MEDIUM priority
    3. tools/claude_code_integration.py (4 references) - LOW priority
    4. tools/orchestration.py spawn_agent_job() - SPECIAL case

    TDD Approach:
    1. Write failing tests first (test_*_0358c.py)
    2. Migrate imports and queries
    3. Update responses to include both job_id and agent_id
    4. Verify tests pass
    5. Run 0366c regression tests

    Semantic Contract:
    - job_id = work order UUID (persistent across succession)
    - agent_id = executor UUID (specific instance)

    Reference: Read handovers/0358c_tool_layer_migration.md for complete specifications.
    Reference: Review completed 0366c files for migration patterns.

    First Step: Create tests/tools/test_agent_0358c.py with failing tests for launch_agent().
