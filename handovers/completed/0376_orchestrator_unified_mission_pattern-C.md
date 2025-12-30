# Handover 0376: Orchestrator Unified Mission Pattern (Use Existing Agent Architecture)

**Status**: Ready for Execution
**Priority**: Medium
**Estimated Effort**: 1 hour
**Risk Level**: Low (prompt-only changes, no database/tools)
**Complexity**: Low (2 prompt generator modifications)

---

## Executive Summary

### What
Enable the orchestrator to persist its execution plan during staging and fetch it during implementation using the **existing agent mission pattern** (`update_agent_mission()` + `get_agent_mission()`). Orchestrator becomes a first-class agent that follows the same workflow as analyzer, implementer, etc.

### Why
Currently:
- **Other agents**: Call `get_agent_mission()` at implementation startup to fetch their mission
- **Orchestrator**: Calls special tool `get_orchestrator_instructions()` with extra context fields

This creates architectural asymmetry. The orchestrator has:
- ✅ An AgentJob record (like other agents)
- ✅ An AgentExecution record (like other agents)
- ✅ A `.mission` field (like other agents)
- ✅ An `agent_id` it can use with `get_agent_mission()` (like other agents)

But doesn't use them uniformly.

During alpha testing (2025-12-25), the orchestrator made execution order decisions:
```
analyzer FIRST → then documenter + implementer in PARALLEL
```
But never persisted this plan, breaking fresh-session orchestration.

### Goal
**Unify the pattern**: Orchestrator uses the same `update_agent_mission()` + `get_agent_mission()` flow as every other agent. No new fields, no new tools, no database changes.

---

## Current Architecture

### Staging Phase - Other Agents (e.g., Analyzer)
1. Orchestrator calls `spawn_agent_job(agent_name="analyzer", ...)`
2. Creates AgentJob with mission
3. Implementation phase: Agent calls `get_agent_mission(agent_id, tenant_key)`
4. Fetches mission from AgentJob.mission field
5. Follows `full_protocol` (5-phase lifecycle)

### Staging Phase - Orchestrator (Currently Special)
1. Orchestrator calls `health_check()`
2. Orchestrator calls `get_orchestrator_instructions()` - special tool with extra context
3. Analyzes requirements
4. Calls `update_project_mission()` - persists project mission
5. Calls `spawn_agent_job()` x N - creates specialist agents
6. Calls `send_message()` broadcast - signals STAGING_COMPLETE
7. **GAP**: No explicit instruction to write orchestrator's execution plan

### Implementation Phase - Orchestrator (Currently Special)
- Orchestrator receives `_build_claude_code_execution_prompt()`
- Does NOT follow same pattern as other agents
- Does NOT call `get_agent_mission()` for its own mission
- Must infer execution strategy from context (risky in fresh session)

---

## Proposed Solution: Use Existing Agent Pattern

### Key Insight
Orchestrator has an `AgentJob` record with `.mission` field, just like every other agent.
Simply tell it to use the same workflow.

### Staging Phase - Add One Instruction
**File**: `src/giljo_mcp/thin_prompt_generator.py::generate_staging_prompt()`

Add step 6 after `spawn_agent_job()` calls:

```markdown
6. PERSIST YOUR EXECUTION PLAN

   Document how you will execute this project:

   mcp__giljo-mcp__update_agent_mission(
       job_id="{orchestrator_id}",
       tenant_key="{tenant_key}",
       mission="""
       # Implementation Plan: {project_name}

       ## Execution Strategy
       - Pattern: [Sequential | Parallel | Hybrid]
       - Rationale: [Why this pattern]

       ## Agent Execution Order

       ### Phase 1: {phase_name}
       - Agent: {agent_name}
       - Job ID: {job_id}
       - Dependencies: None
       - Expected Output: [What this agent produces]

       ### Phase 2: {phase_name}
       - Agents: {agent_1}, {agent_2} (parallel)
       - Dependencies: Phase 1 completion
       - Expected Output: [What these agents produce]

       ## Coordination Checkpoints
       1. After Phase 1: Verify {condition} before proceeding
       2. After Phase 2: Collect outputs and validate

       ## Success Criteria
       - ✅ All agents completed without errors
       - ✅ Deliverables match requirements
       - ✅ No blocking messages unresolved
       """
   )
```

### Implementation Phase - Add Instruction at Top
**File**: `src/giljo_mcp/thin_prompt_generator.py::_build_claude_code_execution_prompt()`

Add at top of SECTION 1 (Context Recap), right after identity:

```markdown
## Your Implementation Plan (from Staging)

You persisted an execution plan during staging. Fetch it now:

mcp__giljo-mcp__get_agent_mission(
    agent_job_id="{orchestrator_id}",
    tenant_key="{tenant_key}"
)

This returns your stored plan with:
- Agent execution order (sequential/parallel/hybrid)
- Dependency graph
- Coordination checkpoints
- Success criteria

Follow this plan to coordinate agents.

---

## Now Spawn Agents
```

Then rest of sections continue as-is (Agent Jobs, Spawning Template, Monitoring, etc.)

---

## Implementation Plan

### Two Simple File Changes

**No database migrations, no new tools, no new fields needed.**

The orchestrator already has:
- ✅ AgentJob record with `.mission` field
- ✅ AgentExecution record with agent_id
- ✅ Can call `update_agent_mission()` to write its plan
- ✅ Can call `get_agent_mission()` to read its plan

### Change 1: Staging Prompt - Tell Orchestrator to Write Its Mission

**File**: `src/giljo_mcp/thin_prompt_generator.py`
**Method**: `generate_staging_prompt()` (lines 940-1036)
**Action**: Add instruction in the STARTUP SEQUENCE section

**Current line 1018** (after "SPAWN AGENTS: spawn_agent_job()..."):
```markdown
6. SIGNAL COMPLETE: send_message(to_agents=['all']...
```

**Insert new step 6 before SIGNAL COMPLETE**:
```markdown
6. WRITE YOUR EXECUTION PLAN: update_agent_mission()

   Persist how you will execute this project. Document:
   - Agent execution order (sequential/parallel/hybrid)
   - Dependency graph between agents
   - Coordination checkpoints
   - Success criteria for each phase

   Use update_agent_mission() with your orchestrator job_id and the plan as mission.
   Example format provided in get_orchestrator_instructions() response.
```

Then renumber the current "6. SIGNAL COMPLETE" to "7. SIGNAL COMPLETE".

---

### Change 2: Implementation Prompt - Tell Orchestrator to Fetch Its Mission

**File**: `src/giljo_mcp/thin_prompt_generator.py`
**Method**: `_build_claude_code_execution_prompt()` (lines 1087-1313)
**Action**: Add section at top of SECTION 1 (Context Recap)

**Current SECTION 1** starts at line 1097:
```python
context_recap = [
    "# GiljoAI Implementation Phase - Claude Code CLI Mode",
    "",
    "## Who You Are",
    f"You are Orchestrator (job_id: {orchestrator_id}) for project '{project.name}'",
    ...
]
```

**Insert new subsection after "## Who You Are" and before "## What You've Already Done"**:
```python
context_recap.insert(7, "")  # blank line after tenant section
context_recap.insert(8, "## Your Implementation Plan (from Staging)")
context_recap.insert(9, "")
context_recap.insert(10, "Fetch your stored execution plan:")
context_recap.insert(11, "```python")
context_recap.insert(12, f'get_agent_mission(agent_job_id="{orchestrator_id}", tenant_key="{self.tenant_key}")')
context_recap.insert(13, "```")
context_recap.insert(14, "")
context_recap.insert(15, "This returns your plan from staging with:")
context_recap.insert(16, "- Agent execution order (sequential/parallel/hybrid)")
context_recap.insert(17, "- Dependency graph between agents")
context_recap.insert(18, "- Coordination checkpoints")
context_recap.insert(19, "- Success criteria for each phase")
context_recap.insert(20, "")
context_recap.insert(21, "Follow this plan. If plan was not written during staging, proceed with best judgment.")
context_recap.insert(22, "")
```

Or simpler approach - just add text string at beginning of context_recap list.

---

## Implementation Plan Format

Recommend orchestrators write execution plans in this format (to be persisted via `update_agent_mission()`):

```markdown
# Implementation Plan: {project_name}

## Execution Strategy
- Pattern: [Sequential | Parallel | Hybrid]
- Rationale: [Why this pattern was chosen]

## Agent Execution Order

### Phase 1: {phase_name}
- Agent: {agent_name}
- Job ID: {job_id}
- Dependencies: None
- Expected Output: [What this agent produces]

### Phase 2: {phase_name}
- Agents: {agent_1}, {agent_2} (parallel)
- Dependencies: Phase 1 completion
- Expected Output: [What these agents produce]

## Coordination Checkpoints
1. After Phase 1: Verify {condition} before proceeding
2. After Phase 2: Collect outputs and validate

## Success Criteria
- ✅ All agents completed without errors
- ✅ Deliverables match project requirements
- ✅ No blocking messages unresolved

## Fallback Strategy
- If {agent} fails: {recovery action}
- If blocked: {escalation path}
```

---

## Verification Checklist

### Staging Prompt Change
```bash
# Verify step 6 is in the prompt
grep -n "WRITE YOUR EXECUTION PLAN" src/giljo_mcp/thin_prompt_generator.py
# Expected: Found in generate_staging_prompt() method
```

### Implementation Prompt Change
```bash
# Verify fetch instruction is in the prompt
grep -n "Your Implementation Plan" src/giljo_mcp/thin_prompt_generator.py
# Expected: Found in _build_claude_code_execution_prompt() method
```

### Integration Test
```python
# 1. Orchestrator calls update_agent_mission() with execution plan during staging
# 2. Implementation phase: Orchestrator calls get_agent_mission()
# 3. Verify mission returned contains the execution plan
# 4. Orchestrator follows the plan to spawn and coordinate agents
# 5. All agents complete successfully
```

---

## Rollback Plan

### Revert Both Changes
```bash
git checkout src/giljo_mcp/thin_prompt_generator.py
```

That's it. No database migrations to revert, no tools to remove.

---

## Success Criteria

- [ ] Staging prompt includes instruction to write execution plan via `update_agent_mission()`
- [ ] Implementation prompt includes instruction to fetch plan via `get_agent_mission()`
- [ ] Orchestrator can write plan during staging (uses existing tool)
- [ ] Orchestrator can fetch plan during implementation (uses existing tool)
- [ ] Fresh session orchestrator can retrieve and follow execution plan
- [ ] All existing tests pass (no breaking changes)
- [ ] No database migrations required
- [ ] No new MCP tools required
- [ ] No new database fields required

---

## Risk Assessment

### Risk Level: MINIMAL ✅

Changes are prompt-only, no infrastructure modifications.

### Low Risk Items
1. **Prompt-only changes** - No database, no tools, no schema changes
2. **Additive instructions** - Orchestrators already have the tools, just adding guidance to use them
3. **Graceful degradation** - If orchestrator skips step 6 during staging, step 1 of implementation still works (just warns user)

### Considerations
1. **Backward compatibility** - Existing orchestrators not changed, only new orchestrators see new instructions
2. **Token impact** - ~50 tokens added to prompts (minimal)
3. **Optional adoption** - Orchestrators can skip writing plan (graceful degradation)

---

## Related Documentation

- **Prompt Generator**: `src/giljo_mcp/thin_prompt_generator.py` (modified by this handover)
- **Orchestration Tools**: `src/giljo_mcp/tools/orchestration.py` (uses existing update_agent_mission + get_agent_mission)
- **Agent Mission Fetching**: Handover 0088 (Thin Client Architecture)
- **Context Reference**: docs/ORCHESTRATOR.md (orchestrator workflow overview)

---

## Architecture Insight

### Before This Handover
- Orchestrator: special tool (`get_orchestrator_instructions`)
- Other agents: standard tool (`get_agent_mission`)
- Result: Asymmetric architecture

### After This Handover
- Orchestrator: standard tool (`get_agent_mission`)
- Other agents: standard tool (`get_agent_mission`)
- Result: Unified architecture ✅

The orchestrator is just another agent that happens to coordinate work. It should use the same mission pattern as everyone else.

---

## Origin

This improvement was identified during alpha testing (2025-12-25) of Claude Code CLI mode orchestration. During staging, the orchestrator made execution order decisions but never persisted them:

```
Decision made: "analyzer first → then documenter + implementer in parallel"
Problem: Decision not saved anywhere
Result: Fresh session orchestrator must re-analyze and re-decide (wasteful, risky)
```

User insight: "Why not use the same `get_agent_mission()` that other agents use? Orchestrator has an AgentJob record just like them."

**Handover revised** to implement this simpler, more elegant solution.

---

## Implementation Summary (2025-12-27)

**Status**: ✅ COMPLETE

### What Was Implemented

| Change | File | Lines Modified |
|--------|------|----------------|
| Staging prompt - write execution plan | `thin_prompt_generator.py` | 1019-1031 |
| Implementation prompt - fetch plan | `thin_prompt_generator.py` | 1115-1130 |

### Commits

| Commit | Description |
|--------|-------------|
| `cad708cb` | feat(0376): Orchestrator unified mission pattern |

### Files Modified

- `src/giljo_mcp/thin_prompt_generator.py` - Added step 6 (write plan) to staging, added fetch section to implementation
- `tests/thin_prompt/test_thin_client_generator.py` - Added test for staging prompt
- `tests/test_thin_prompt_generator.py` - New file with implementation prompt tests

### Tests Added

| Test | Status |
|------|--------|
| `test_staging_prompt_includes_execution_plan_step` | ✅ PASSED |
| `test_execution_plan_section_in_implementation_prompt` | ✅ PASSED |
| `test_execution_plan_section_formatting` | ✅ PASSED |

### Effort

- **Estimated**: 1 hour
- **Actual**: ~30 minutes (parallel TDD agents)

### Key Architectural Decision

Chose **unified agent pattern** over original proposal (dedicated field + tool):
- ❌ Original: Add `implementation_plan` field + new MCP tool (2-3 hours, DB migration)
- ✅ Implemented: Use existing `update_agent_mission()` + `get_agent_mission()` (1 hour, prompt-only)

Result: Orchestrator is now a first-class agent following the same mission pattern as all other agents.

---

**Handover 0376**: Orchestrator Unified Mission Pattern (Use Existing Agent Architecture)
