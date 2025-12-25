# Handover 0376: Orchestrator Implementation Mission Persistence

**Status**: Ready for Execution
**Priority**: Medium
**Estimated Effort**: 2-3 hours
**Risk Level**: Low (additive change, no breaking modifications)
**Complexity**: Low-Moderate (new field + prompt generation logic)

---

## Executive Summary

### What
Add an "implementation mission" field to the orchestrator job record that captures the orchestrator's execution plan during staging. This plan is then retrievable during the implementation phase, enabling session-independent orchestration.

### Why
Currently, staging persists:
- **Project mission** (`update_project_mission()`) - what the project needs
- **Agent missions** (`spawn_agent_job()`) - what each specialist does

But NOT:
- **Orchestrator's execution plan** - how to coordinate agents

This creates a gap when:
1. Implementation runs in a fresh session/terminal (rare but supported)
2. Orchestrator needs to recall execution strategy decisions
3. Debugging requires visibility into orchestrator's coordination plan

During alpha testing (2025-12-25), we observed that the orchestrator made decisions like:
```
analyzer FIRST → then documenter + implementer in PARALLEL
```
But this decision was not persisted anywhere, making fresh-session handover incomplete.

### Goal
Enable orchestrators to write their execution plan during staging, which can be retrieved via `get_orchestrator_instructions()` during implementation phase.

---

## Current Architecture

### Staging Phase (what orchestrator does now)
1. `health_check()` - verify MCP connection
2. `get_orchestrator_instructions()` - fetch project context
3. Analyze requirements
4. `update_project_mission()` - persist PROJECT mission
5. `spawn_agent_job()` x N - create specialist agents
6. `send_message()` broadcast - signal STAGING_COMPLETE

### Gap
Step 4 persists what the PROJECT needs, but not HOW the orchestrator plans to execute it.

---

## Proposed Solution

### New Step in Staging Workflow
Add step between current 5 and 6:

```
5. spawn_agent_job() x N - create specialist agents
6. NEW: update_orchestrator_implementation_plan() - persist execution strategy
7. send_message() broadcast - signal STAGING_COMPLETE
```

### Option A: New Dedicated Field (Recommended)
Add `implementation_plan` field to orchestrator job record.

**Pros:**
- Clean separation of concerns
- Explicit purpose
- Easy to query/debug

**Cons:**
- Database schema change required
- New MCP tool needed

### Option B: Reuse Existing Mission Field
Store implementation plan in orchestrator's `mission` field on the AgentJob record.

**Pros:**
- No schema change
- Existing `get_agent_mission()` retrieves it

**Cons:**
- Overloads meaning of "mission" field
- Less explicit

### Recommendation
**Option A** - cleaner architecture, worth the schema change.

---

## Implementation Plan

### Phase 1: Database Schema

#### File: `src/giljo_mcp/models.py`

Add field to `AgentJob` model:

```python
class AgentJob(Base):
    # ... existing fields ...

    # NEW: Orchestrator's execution plan (only populated for orchestrator jobs)
    implementation_plan = Column(Text, nullable=True, default=None)
```

#### Migration
Create Alembic migration:
```bash
alembic revision --autogenerate -m "add_implementation_plan_to_agent_job"
alembic upgrade head
```

### Phase 2: MCP Tool

#### File: `src/giljo_mcp/tools/orchestration.py`

Add new tool:

```python
@mcp_tool(
    name="update_orchestrator_implementation_plan",
    description="Persist orchestrator's execution plan during staging. Called after spawning agents."
)
async def update_orchestrator_implementation_plan(
    job_id: str,
    tenant_key: str,
    implementation_plan: str
) -> dict:
    """
    Store the orchestrator's execution strategy for retrieval during implementation phase.

    Args:
        job_id: Orchestrator's job UUID
        tenant_key: Tenant isolation key
        implementation_plan: Execution strategy document (markdown format recommended)

    Returns:
        Success confirmation with plan summary
    """
    # Validate tenant access
    # Update AgentJob.implementation_plan where job_id matches
    # Return confirmation
```

### Phase 3: Update get_orchestrator_instructions()

#### File: `src/giljo_mcp/tools/orchestration.py`

Modify `get_orchestrator_instructions()` to include `implementation_plan` in response if it exists:

```python
# In get_orchestrator_instructions response
return {
    "identity": {...},
    "project_description_inline": {...},
    "context_fetch_instructions": {...},
    "agent_templates": [...],
    # NEW: Include implementation plan if present
    "implementation_plan": orchestrator_job.implementation_plan,  # None during staging, populated during implementation
    ...
}
```

### Phase 4: Update Prompts

#### Staging Prompt Addition
Add to staging prompt after "SPAWN AGENTS" section:

```markdown
6. WRITE IMPLEMENTATION PLAN: update_orchestrator_implementation_plan()
   Document your execution strategy:
   - Agent execution order (sequential/parallel/hybrid)
   - Dependency graph between agents
   - Coordination checkpoints
   - Expected handoff points
   - Success criteria for each phase
```

#### Implementation Prompt Simplification
Implementation prompt can now say:

```markdown
## Your Execution Plan
Your implementation plan from staging is available in the `implementation_plan` field
from `get_orchestrator_instructions()`. Follow that plan to coordinate agents.
```

### Phase 5: Thin Prompt Generator Update

#### File: `src/giljo_mcp/thin_prompt_generator.py`

Update `_build_staging_prompt()` to include new step 6.

Update `_build_implementation_prompt()` to reference `implementation_plan` field.

---

## Implementation Plan Content Structure

Recommend orchestrators write implementation plans in this format:

```markdown
# Implementation Plan: {project_name}

## Execution Strategy
- Pattern: [Sequential | Parallel | Hybrid]
- Rationale: [Why this pattern was chosen]

## Agent Execution Order

### Phase 1: {phase_name}
- Agent: {agent_name}
- Job ID: {job_id}
- Dependencies: [None | list of prior agents]
- Expected Output: [What this agent produces]

### Phase 2: {phase_name}
- Agents: {agent_1}, {agent_2} (parallel)
- Dependencies: Phase 1 completion
- Expected Output: [What these agents produce]

## Coordination Checkpoints
1. After Phase 1: Verify {condition} before proceeding
2. After Phase 2: Collect outputs and validate

## Success Criteria
- [ ] All agents completed without errors
- [ ] Deliverables match project requirements
- [ ] No blocking messages unresolved

## Fallback Strategy
- If {agent} fails: {recovery action}
- If blocked: {escalation path}
```

---

## Verification Checklist

### Database
```bash
# Verify migration applied
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d agent_jobs" | grep implementation_plan
# Expected: implementation_plan | text | nullable
```

### MCP Tool
```python
# Test new tool exists
from giljo_mcp.tools.orchestration import update_orchestrator_implementation_plan
# No import error
```

### Integration Test
```python
# 1. Create orchestrator job
# 2. Call update_orchestrator_implementation_plan() with test plan
# 3. Call get_orchestrator_instructions()
# 4. Verify implementation_plan field populated in response
```

---

## Rollback Plan

### Step 1: Revert Migration
```bash
alembic downgrade -1
```

### Step 2: Remove Tool
Delete `update_orchestrator_implementation_plan` from `orchestration.py`

### Step 3: Revert Prompt Changes
Restore original staging/implementation prompts

---

## Success Criteria

- [ ] `implementation_plan` field added to `AgentJob` model
- [ ] Migration applied successfully
- [ ] `update_orchestrator_implementation_plan()` MCP tool functional
- [ ] `get_orchestrator_instructions()` returns `implementation_plan` when present
- [ ] Staging prompt includes new step 6
- [ ] Implementation prompt references `implementation_plan` field
- [ ] Fresh session orchestrator can retrieve and follow execution plan
- [ ] All existing tests pass (no breaking changes)

---

## Risk Assessment

### Low Risk Items
1. **Additive schema change** - new nullable field, no existing data affected
2. **New MCP tool** - doesn't modify existing tools
3. **Prompt updates** - additions only, no removals

### Considerations
1. **Backward compatibility** - Old orchestrator prompts without step 6 still work (field just stays null)
2. **Token budget** - Implementation plan adds ~200-500 tokens to orchestrator context
3. **Optional adoption** - Orchestrators can skip writing plan (graceful degradation)

---

## Related Documentation

- **Staging/Implementation Prompts**: `src/giljo_mcp/thin_prompt_generator.py`
- **Orchestration Tools**: `src/giljo_mcp/tools/orchestration.py`
- **Agent Job Model**: `src/giljo_mcp/models.py`
- **Context Reference**: `handovers/Agent instructions and where they live.md`

---

## Origin

This improvement was identified during alpha testing (2025-12-25) of Claude Code CLI mode orchestration. During staging, the orchestrator made execution order decisions (sequential vs parallel) that were not persisted, creating a gap when implementation runs in a fresh session.

Testing session context:
- Project: TinyContacts (test project)
- Mode: Claude Code CLI
- Observation: Orchestrator decided "analyzer first, then documenter + implementer in parallel" but this was not captured for fresh-session retrieval

---

**Handover 0376**: Orchestrator Implementation Mission Persistence
