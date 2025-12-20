# Handover 0363: Orchestrator Handover Behavior Injection

**Date**: 2025-12-19
**Status**: READY FOR DISCUSSION
**Priority**: Medium
**Type**: Architecture Enhancement
**Estimated Effort**: TBD (needs discussion)
**Related Issues**: Discovered during 0355 implementation (Alpha Trial Remediation)
**Depends On**: 0355 (Protocol Message Handling Fix) - ✅ COMPLETED 2025-12-19

---

## Executive Summary

Orchestrator succession has an architectural gap: successor orchestrators do not receive execution-phase behavior instructions when taking over from a predecessor. The current handover mechanism successfully transfers project state and creates the successor job, but the successor only receives `get_orchestrator_instructions()` which is designed for the staging workflow. This means successor orchestrators miss the execution-phase monitoring guidance that would be added in Handover 0355.

**Impact**: After handover, successor orchestrators lack guidance on:
- How to monitor spawned agents during execution
- When to poll for agent status updates
- Message handling patterns for parallel vs sequential execution
- Coordination patterns for agent handoffs

**Current Workaround**: None - successors rely on general orchestrator knowledge without explicit execution-phase instructions

**Proposed Solutions**: Three architectural options requiring developer discussion before implementation

---

## Problem Statement

### Current Handover Flow (As Implemented)

**Step 1: Predecessor Detects Context Threshold**
- Orchestrator reaches 90% context capacity (or manual trigger)
- Calls `mcp__giljo-mcp__create_successor_orchestrator(current_job_id, tenant_key, reason)`

**Step 2: Successor Job Created**
```python
# File: src/giljo_mcp/tools/succession_tools.py (lines 34-99)
# Creates new MCPAgentJob with:
successor = MCPAgentJob(
    job_id=new_uuid,
    agent_type="orchestrator",
    status="waiting",
    mission="Continue orchestration for {project_name}...",  # Generic handover summary
    instance_number=predecessor.instance_number + 1,
    spawned_by=current_job_id,
    context_used=0,
    context_budget=150000
)
```

**Step 3: User Launches Successor**
- User copies thin launch prompt from UI
- Pastes into new Claude Code session
- Thin prompt instructs: "Call `get_orchestrator_instructions(orchestrator_id, tenant_key)`"

**Step 4: Successor Retrieves Instructions (THE GAP)**
```python
# File: src/giljo_mcp/tools/orchestration.py
# Orchestrator calls get_orchestrator_instructions()

# PROBLEM: This returns STAGING workflow instructions (7 tasks)
# - Task 1: Identity verification
# - Task 2: MCP health check
# - Task 3: Environment understanding
# - Task 4: Agent discovery
# - Task 5: Context prioritization
# - Task 6: Job spawning
# - Task 7: Activation

# BUT: Staging is already complete!
# - Agents already spawned by predecessor
# - Project already activated
# - Context already prioritized

# MISSING: Task 8 (Execution Phase Monitoring) from Handover 0355
# - Sequential/parallel execution patterns
# - Message polling strategy
# - Agent coordination patterns
```

### The Gap Explained

**What Happens Now:**
1. Predecessor orchestrator completes staging (7 tasks) → spawns agents → enters execution phase
2. Predecessor reaches 90% context → triggers succession
3. Successor created with mission: "Continue orchestration" (generic summary)
4. User launches successor via thin prompt
5. Successor calls `get_orchestrator_instructions()` → receives STAGING workflow (7 tasks)
6. Successor sees agents already spawned, work already in progress
7. Successor has NO guidance on execution-phase monitoring (what to do next)

**What's Missing:**
- Execution-phase behavior instructions (from Handover 0355 Task 8)
- Message polling patterns for active agents
- Coordination patterns for sequential/parallel execution
- Progress monitoring and milestone tracking

**Why This Matters:**
- Without execution guidance, successors don't know when to check messages
- Successors may not monitor agent progress effectively
- Risk of repeating Issue #8 from alpha trial: "Orchestrator not monitoring during implementation"

---

## Research Findings

### Orchestrator vs Agent Instruction Mechanisms

**Discovery 1: Orchestrators Use Different Tool**
```python
# Agents call:
get_agent_mission(job_id, tenant_key)
# Returns: { "mission": "...", "full_protocol": "..." }

# Orchestrators call:
get_orchestrator_instructions(orchestrator_id, tenant_key)
# Returns: { "staging_prompt": "...", "context_framing": {...} }
# NOTE: NO full_protocol field!
```

**Discovery 2: Orchestrator Instructions Are Staging-Focused**
```python
# File: src/giljo_mcp/thin_prompt_generator.py (lines 239-449)
async def _build_staging_prompt(...):
    """
    Build orchestrator staging prompt (7-task workflow).

    Tasks:
    1. Identity verification
    2. MCP health check
    3. Environment understanding
    4. Agent discovery
    5. Context prioritization
    6. Job spawning
    7. Activation
    """
    # NO TASK 8 for execution phase monitoring
```

**Discovery 3: Handover Only Transfers State, Not Behavior**
```python
# File: src/giljo_mcp/orchestrator_succession.py
# Handover summary includes:
handover_summary = {
    "project_status": "60% complete",
    "active_agents": [...],
    "completed_phases": [...],
    "pending_decisions": [...],
    "next_steps": "Implement API endpoints..."
}

# BUT: Does NOT include behavior instructions
# No "How to monitor agents" or "When to check messages"
```

### Succession Flow Walkthrough

**File: `src/giljo_mcp/tools/succession_tools.py`**

Lines 34-99: `create_successor_orchestrator()`
- Creates new orchestrator job (instance_number + 1)
- Generates handover summary (<10K tokens)
- Marks predecessor as complete
- Returns successor details to user

**File: `src/giljo_mcp/thin_prompt_generator.py`**

Lines 255-276: Successor job creation
```python
orchestrator = MCPAgentJob(
    tenant_key=self.tenant_key,
    job_id=orchestrator_id,
    agent_name=f"Orchestrator #{instance_number}",
    status="waiting",
    mission=placeholder_mission,  # "Continue orchestration for {project}"
    job_metadata={
        "field_priorities": {...},
        "depth_config": {...},
        "created_via": "thin_client_generator"
    }
)
```

**Key Observation**: Successor job's `mission` field is a placeholder. The REAL instructions come from calling `get_orchestrator_instructions()` after launch.

**File: `src/giljo_mcp/tools/orchestration.py`**

Lines 200+: `get_orchestrator_instructions()` implementation
- Fetches orchestrator job from database
- Calls `_build_staging_prompt()` to generate 7-task workflow
- Returns staging instructions + context framing
- **Gap**: No awareness of "this is a successor orchestrator"

### Handover 0355 Context

**What 0355 Adds** (when implemented):
- **Phase 1**: Enhanced agent protocol with message checks after each TodoWrite task
- **Phase 2**: **Task 8: Execution Phase Monitoring** added to orchestrator staging prompt
  - Sequential execution pattern (spawn → poll → handoff → spawn next)
  - Parallel execution pattern (spawn all → poll all → coordinate)
  - Mandatory final message check before completion

**Why Successors Need This**:
- Handover 0355 adds Task 8 to `_build_staging_prompt()`
- Staging prompt returned by `get_orchestrator_instructions()`
- **BUT**: Successors SKIP staging (already done by predecessor)
- **SO**: Successors never see Task 8 guidance

---

## Questions for Discussion

### 1. Handover Mechanism Review

**Question**: How does the user currently give the successor orchestrator its continuation mission?

**Current Behavior**:
1. User clicks "Launch Successor" button in Jobs tab
2. UI generates thin launch prompt:
   ```bash
   # Copy and paste into Claude Code:
   Call mcp__giljo-mcp__get_orchestrator_instructions(
       orchestrator_id="orch-a1b2c3d4-...",
       tenant_key="tenant-xyz"
   )
   ```
3. Successor calls this tool → receives staging prompt (7 tasks)
4. Successor sees agents already spawned, adapts on the fly

**Developer Input Needed**:
- Is this the intended flow?
- Should successors receive different instructions than first-time orchestrators?
- Is there a better injection point for execution-phase guidance?

### 2. Instruction Injection Point

**Question**: Where should execution-phase behavior instructions be injected?

**Option A**: Enhance handover mission text in database
- Store execution guidance in `MCPAgentJob.mission` during handover
- Successor reads mission directly without calling `get_orchestrator_instructions()`
- **Pro**: Simple, no tool changes needed
- **Con**: Mission becomes very long (staging + execution + handover state)

**Option B**: Modify `get_orchestrator_instructions()` to detect successors
- Add `is_successor` flag to orchestrator job metadata
- When `is_successor=True`, return execution-only instructions (skip staging)
- **Pro**: Clean separation, successors get exactly what they need
- **Con**: Requires conditional logic in tool, two instruction templates

**Option C**: Create separate `get_orchestrator_execution_instructions()` tool
- New MCP tool specifically for execution-phase guidance
- Thin prompt tells successor: "Skip staging, call execution tool instead"
- **Pro**: Explicit, clear purpose, reusable for manual execution phase entry
- **Con**: Adds new tool, requires UI changes, more complex flow

**Developer Input Needed**:
- Which option aligns best with architecture vision?
- Should successors re-read staging instructions and adapt, or get tailored guidance?

### 3. Staging vs Execution Phase Distinction

**Question**: Should orchestrators always call `get_orchestrator_instructions()` at startup, or should there be phase-aware tool routing?

**Current Assumption**: Single tool serves all orchestrator startup needs

**Alternative**: Phase-aware routing
- STAGING PHASE: Call `get_orchestrator_instructions()` → 7-task workflow
- EXECUTION PHASE: Call `get_orchestrator_execution_instructions()` → monitoring patterns
- SUCCESSION: Thin prompt routes to execution tool automatically

**Developer Input Needed**:
- Is phase distinction worth the complexity?
- Do orchestrators ever need to "re-enter" staging phase mid-project?
- What happens if staging fails and needs retry?

### 4. Handover Summary Content

**Question**: Should the handover summary include execution behavior instructions, or just state?

**Current Behavior**: State-only
```json
{
  "project_status": "60% complete",
  "active_agents": [...],
  "completed_phases": [...],
  "pending_decisions": [...],
  "next_steps": "Implement API endpoints..."
}
```

**Alternative**: State + Behavior
```json
{
  "project_status": "60% complete",
  "active_agents": [...],
  "execution_guidance": {
    "mode": "parallel",
    "monitoring_pattern": "Poll all agents every 2-3 minutes...",
    "coordination_rules": "When analyzer completes first..."
  },
  "next_steps": "Continue monitoring analyzer and documenter..."
}
```

**Developer Input Needed**:
- Should handover summary be purely state, or include behavior?
- Would embedding instructions in handover violate separation of concerns?
- How much duplication is acceptable (instructions in multiple places)?

---

## Proposed Solutions (Options)

### Option A: Inject Behavior in Handover Mission Text

**Approach**: Enhance `create_successor_orchestrator()` to embed execution instructions in the successor's `mission` field.

**Implementation**:
```python
# File: src/giljo_mcp/tools/succession_tools.py

# When creating successor:
handover_mission = f"""
## Successor Orchestrator Handover

### Project State
{handover_summary}

### Execution Phase Instructions (Handover 0355 Task 8)

You are continuing work from Orchestrator Instance {predecessor.instance_number}.
Staging is COMPLETE. Agents are ALREADY SPAWNED. Your role is execution monitoring.

**Sequential Execution Pattern**:
1. Poll agent status every 2-3 minutes via receive_messages()
2. When agent completes, check results
3. Send guidance to next agent if needed
4. Continue monitoring until all complete

**Parallel Execution Pattern**:
1. Poll ALL agent statuses every 2-3 minutes
2. As agents finish, check results and send follow-up
3. Continue until ALL complete

**MANDATORY**: Before calling complete_job(), call receive_messages() to check for blocks.
"""

successor.mission = handover_mission
```

**Pros**:
- ✅ Simple to implement (one-file change)
- ✅ Successors get tailored instructions immediately
- ✅ No new MCP tools or UI changes required
- ✅ Self-contained in handover flow

**Cons**:
- ❌ Mission field becomes very long (state + instructions + context)
- ❌ Duplication: Same instructions stored in every successor's mission
- ❌ Not fetched from authoritative source (instructions baked into DB)
- ❌ Hard to update instructions retroactively

**Token Impact**: +400-500 tokens per successor mission

### Option B: Create `get_orchestrator_execution_instructions()` Tool

**Approach**: Add new MCP tool specifically for execution-phase guidance.

**Implementation**:
```python
# File: src/giljo_mcp/tools/orchestration.py

@mcp.tool()
async def get_orchestrator_execution_instructions(
    orchestrator_id: str,
    tenant_key: str
) -> dict[str, Any]:
    """
    Retrieve execution-phase monitoring instructions for orchestrator.

    Use this when:
    - You are a successor orchestrator continuing work
    - Staging is already complete
    - Agents are already spawned

    Returns:
    - Sequential execution monitoring pattern
    - Parallel execution monitoring pattern
    - Message polling strategy
    - Agent coordination patterns
    """
    return {
        "execution_mode": "monitoring",
        "instructions": _build_execution_prompt(orchestrator_id),
        "coordination_patterns": {...},
        "message_polling": {...}
    }
```

**Thin Prompt for Successor**:
```bash
# Successor orchestrator thin prompt (modified)
You are Successor Orchestrator Instance #2.

1. Call get_orchestrator_execution_instructions(orchestrator_id, tenant_key)
   - Get execution monitoring guidance
   - Review active agent status
   - Understand coordination patterns

2. DO NOT call get_orchestrator_instructions() (staging already complete)

3. Resume execution monitoring where predecessor left off
```

**Pros**:
- ✅ Clean separation: Staging tool vs Execution tool
- ✅ Single source of truth for execution instructions
- ✅ Can update instructions without DB migrations
- ✅ Reusable: First-time orchestrators can also call for execution guidance

**Cons**:
- ❌ Adds new MCP tool (schema overhead, documentation, testing)
- ❌ Requires UI changes (thin prompt generator must detect successors)
- ❌ More complex flow (two tools instead of one)
- ❌ Risk of confusion: When to call which tool?

**Token Impact**: +100 tokens (new tool in catalog), +200 tokens (execution instructions)

### Option C: Flag in `get_orchestrator_instructions()` to Skip Staging

**Approach**: Add conditional logic to existing tool to detect successors and return phase-appropriate instructions.

**Implementation**:
```python
# File: src/giljo_mcp/tools/orchestration.py

@mcp.tool()
async def get_orchestrator_instructions(
    orchestrator_id: str,
    tenant_key: str
) -> dict[str, Any]:
    """
    Retrieve orchestrator instructions (staging or execution phase).

    Automatically detects:
    - First-time orchestrator → Returns staging workflow (7 tasks)
    - Successor orchestrator → Returns execution monitoring guidance only
    """
    # Fetch orchestrator job
    orchestrator = await _get_orchestrator_job(orchestrator_id, tenant_key)

    # Check if this is a successor (has spawned_by value)
    is_successor = orchestrator.spawned_by is not None

    if is_successor:
        # Return execution-only instructions
        return {
            "mode": "execution",
            "instructions": _build_execution_prompt(orchestrator),
            "handover_context": orchestrator.mission  # Includes state from predecessor
        }
    else:
        # Return staging workflow (current behavior)
        return {
            "mode": "staging",
            "staging_prompt": _build_staging_prompt(...),
            "context_framing": {...}
        }
```

**Pros**:
- ✅ No new tools (keeps schema lean)
- ✅ Automatic detection (user doesn't choose)
- ✅ Single tool serves both use cases
- ✅ Minimal UI changes (thin prompt stays same)

**Cons**:
- ❌ Overloaded tool (one function, two very different behaviors)
- ❌ Hidden magic: User doesn't know which path they'll get
- ❌ Harder to test (conditional branching)
- ❌ Risk: What if successor NEEDS to re-stage for some reason?

**Token Impact**: Neutral (same instructions, just conditional routing)

### Option D: Hybrid - Execution Instructions in Staging Prompt (Context-Aware)

**Approach**: Keep single tool, but enhance staging prompt to include BOTH staging AND execution phases. Successors receive full context and self-navigate.

**Implementation**:
```python
# File: src/giljo_mcp/thin_prompt_generator.py

async def _build_staging_prompt(...):
    """
    Build orchestrator staging prompt with execution phase included.
    """
    prompt = """
    ## Orchestrator Workflow (8 Tasks)

    ### STAGING PHASE (Tasks 1-7)
    [Current 7-task workflow]

    ### EXECUTION PHASE (Task 8 - AFTER STAGING COMPLETE)
    [Handover 0355 execution monitoring guidance]

    ---

    **IMPORTANT**: If you are a successor orchestrator:
    - Tasks 1-7 are ALREADY COMPLETE (done by predecessor)
    - Start directly at Task 8 (Execution Phase Monitoring)
    - Review handover summary in your mission for current state
    """
    return prompt
```

**Successors Self-Navigate**:
- Call `get_orchestrator_instructions()` (same as always)
- Receive full 8-task workflow
- Read "IMPORTANT" note → skip to Task 8
- Adapt based on mission context

**Pros**:
- ✅ No new tools, no conditional logic
- ✅ Full context for all orchestrators (first-time and successors)
- ✅ Self-documenting (orchestrators understand full lifecycle)
- ✅ Minimal code changes (just add Task 8 to staging prompt)

**Cons**:
- ❌ Longer prompt for ALL orchestrators (even if staging-only)
- ❌ Relies on orchestrator intelligence to skip irrelevant tasks
- ❌ Potential confusion: "Do I stage again or not?"
- ❌ Token overhead for first-time orchestrators who don't need execution yet

**Token Impact**: +250 tokens for all orchestrators (staging + execution)

---

## Implementation Dependencies

### Handover 0355 (MUST BE COMPLETE FIRST)

This handover DEPENDS on 0355 being implemented because:
1. **0355 defines Task 8**: Execution phase monitoring instructions
2. **Without Task 8, there's nothing to inject**: No execution guidance exists yet
3. **0355 adds agent protocol changes**: Message handling that orchestrators must understand

**Sequence**:
1. Implement 0355 (add Task 8 to `_build_staging_prompt()`)
2. Verify first-time orchestrators use Task 8 successfully
3. THEN implement 0363 (ensure successors also get Task 8)

### Related Handovers

- **0080**: Orchestrator Succession Architecture (foundation)
- **0080a**: `/gil_handover` slash command (manual trigger)
- **0246a**: Orchestrator Staging Workflow (7-task pipeline)
- **0334**: HTTP-only MCP and full_protocol introduction
- **0355**: Protocol Message Handling Fix (defines Task 8)

---

## Testing Strategy

### Manual Testing Scenarios

**Scenario 1: Successor Receives Execution Guidance**
1. Launch first-time orchestrator for simple project
2. Orchestrator completes staging → spawns agents → enters execution
3. Trigger manual succession via `/gil_handover`
4. Launch successor orchestrator
5. **Verify**: Successor receives execution monitoring instructions
6. **Verify**: Successor does NOT attempt to re-stage
7. **Verify**: Successor begins polling agent status immediately

**Scenario 2: Successor Adapts to Active Agents**
1. First orchestrator spawns analyzer + documenter (parallel mode)
2. Analyzer still working when succession triggered
3. Documenter completes during handover window
4. Successor launched
5. **Verify**: Successor detects mixed agent states (one working, one complete)
6. **Verify**: Successor applies parallel execution pattern from instructions
7. **Verify**: Successor coordinates handoff when analyzer completes

**Scenario 3: Multi-Level Succession**
1. Create orchestrator chain: Instance 1 → 2 → 3
2. Each successor triggers after predecessor reaches 90% context
3. **Verify**: Instance 2 receives execution instructions
4. **Verify**: Instance 3 ALSO receives execution instructions (not degraded)
5. **Verify**: All successors can monitor agents effectively

### Integration Testing

**File**: `tests/integration/test_orchestrator_succession_behavior.py`

**New Tests**:
1. `test_successor_receives_execution_instructions()`
   - Create predecessor, trigger succession
   - Launch successor, verify it gets execution guidance
   - Assert Task 8 instructions present in response

2. `test_successor_skips_staging_tasks()`
   - Verify successor does NOT re-run agent discovery
   - Verify successor does NOT re-spawn agents
   - Assert successor starts at execution monitoring

3. `test_multiple_successors_behavior_consistency()`
   - Create 3-instance chain
   - Verify all successors receive same execution guidance quality

4. `test_handover_mission_includes_state_not_behavior()` (if Option A chosen)
   - Verify handover summary is state-focused
   - OR verify it includes behavior if that's the chosen approach

### Regression Testing

**Verify No Breaking Changes**:
- Existing first-time orchestrators still work (get staging workflow)
- Existing succession flow still creates valid successor jobs
- Handover summaries still compress to <10K tokens
- Multi-tenant isolation still enforced (successors stay in same tenant)

---

## Success Criteria

### Functional Requirements

1. **Successor Orchestrators Receive Execution Guidance**
   - [ ] Successors get Task 8 instructions (from Handover 0355)
   - [ ] Successors understand sequential vs parallel execution patterns
   - [ ] Successors know when to poll agent status
   - [ ] Successors apply message handling patterns correctly

2. **No Redundant Staging**
   - [ ] Successors do NOT re-run agent discovery
   - [ ] Successors do NOT re-spawn existing agents
   - [ ] Successors do NOT re-activate already active project

3. **Consistency Across Succession Levels**
   - [ ] Instance 2 gets same quality instructions as Instance 1
   - [ ] Instance 3+ maintain instruction quality (no degradation)
   - [ ] All successors can coordinate agent handoffs

### Documentation Requirements

1. **Code Documentation**
   - [ ] Chosen option (A/B/C/D) documented in implementation files
   - [ ] Handover flow diagram updated to show instruction injection point
   - [ ] Comments explain successor detection logic (if Option B/C chosen)

2. **User-Facing Documentation**
   - [ ] `docs/ORCHESTRATOR.md` updated with succession behavior section
   - [ ] `docs/quick_reference/succession_quick_ref.md` includes execution phase notes
   - [ ] User guide explains what happens when successor launches

3. **Developer Documentation**
   - [ ] This handover (0363) marked as COMPLETE when implemented
   - [ ] Decision rationale documented (which option chosen and why)
   - [ ] Migration guide if tool changes affect existing integrations

---

## Risks & Mitigations

### Risk 1: Successors Confused by Mixed Instructions

**Risk**: If using Option D (full staging + execution prompt), successors may not understand they should skip staging.

**Likelihood**: Medium
**Impact**: Medium (wasted time re-staging, possible duplicate agent spawns)

**Mitigation**:
- Use VERY explicit language: "IF YOU ARE A SUCCESSOR, START AT TASK 8"
- Add conditional check in staging instructions: "Check your mission - if it mentions predecessor, skip to execution"
- Test with real handover scenarios during alpha trials

### Risk 2: Instruction Drift Between Staging and Handover

**Risk**: If using Option A (embed in mission), execution instructions become stale if staging prompt updated.

**Likelihood**: Medium (happens whenever we update staging workflow)
**Impact**: Medium (successors get old instructions)

**Mitigation**:
- If Option A chosen, accept that instructions are "baked in" at handover time
- Alternative: Use Option B/C to maintain single source of truth
- Document that handover missions reflect instructions at time of succession

### Risk 3: Token Budget Overflow

**Risk**: Adding execution instructions pushes orchestrator prompts over budget.

**Likelihood**: Low
**Impact**: Low (current staging: ~930 tokens, execution: +250, total: ~1,180)

**Mitigation**:
- Current budget: 2K tokens (soft limit)
- Execution guidance adds ~250 tokens
- Still well under limit
- If needed, compress other sections (e.g., examples)

### Risk 4: Breaking Existing Succession Flow

**Risk**: Changes to `get_orchestrator_instructions()` break in-flight handovers.

**Likelihood**: Low
**Impact**: Medium (active successors fail to launch)

**Mitigation**:
- Successor jobs created BEFORE implementation continue using old flow
- Tool changes only affect NEW successors (created AFTER deployment)
- No database migration required (changes are prompt-generation only)
- Existing successor jobs have `mission` field with old-style handover summary

---

## Rollout Plan

### Phase 1: Design Decision (2-3 hours)
1. Discuss options A/B/C/D with developer
2. Choose approach based on:
   - Architectural alignment (separation of concerns)
   - Token budget impact
   - Maintainability
   - User experience
3. Document decision rationale in this handover

### Phase 2: Implementation (2-4 hours, varies by option)

**If Option A (Mission Embedding)**:
1. Modify `create_successor_orchestrator()` in `succession_tools.py`
2. Add execution instructions template
3. Test handover mission generation
4. Verify token budget compliance

**If Option B (New Tool)**:
1. Create `get_orchestrator_execution_instructions()` tool
2. Modify thin prompt generator to detect successors
3. Update UI to use correct thin prompt for successors
4. Add tool to MCP catalog and documentation

**If Option C (Conditional Logic)**:
1. Add `is_successor` detection to `get_orchestrator_instructions()`
2. Implement conditional branching (staging vs execution)
3. Test both paths thoroughly
4. Update tool documentation to explain dual behavior

**If Option D (Context-Aware Staging)**:
1. Enhance `_build_staging_prompt()` to include Task 8
2. Add "IMPORTANT" note for successors
3. Test that first-time orchestrators don't get confused
4. Verify successors self-navigate correctly

### Phase 3: Testing (1-2 hours)
1. Run integration test suite
2. Manual succession scenario testing
3. Multi-level succession (3+ instances)
4. Regression: Verify existing flows unaffected

### Phase 4: Documentation (1 hour)
1. Update `docs/ORCHESTRATOR.md` with succession behavior
2. Update `docs/quick_reference/succession_quick_ref.md`
3. Document chosen option in architecture docs
4. Mark handover as COMPLETE

**Total Estimated Time**: 4-10 hours (depends on chosen option)

---

## Developer Discussion Required

**Before implementing this handover, discuss the following:**

### Critical Questions

1. **Which option aligns with GiljoAI architecture vision?**
   - Should successors get tailored instructions (A/B/C) or full context (D)?
   - Is single tool (C/D) better than multiple tools (B)?
   - What's the right balance between simplicity and clarity?

2. **Token budget priorities**
   - Is +250 tokens per orchestrator acceptable for Option D?
   - Should we optimize for first-time orchestrators or all orchestrators?
   - Would separate tools (Option B) reduce total token usage?

3. **Maintenance considerations**
   - Which option is easiest to update when execution patterns change?
   - If we embed instructions (Option A), how do we version them?
   - What happens if we need to retroactively update successor behavior?

4. **User experience**
   - Should successors be "smart" (auto-detect, Option C) or "explicit" (different tool, Option B)?
   - Is it okay for orchestrators to receive irrelevant instructions they must skip (Option D)?
   - How do we prevent confusion in the succession UI?

### Recommended Approach (Documentation Manager Opinion)

**Preliminary Recommendation**: **Option C (Conditional Logic in Existing Tool)**

**Rationale**:
- ✅ Keeps MCP schema lean (no new tools)
- ✅ Automatic phase detection (user doesn't choose)
- ✅ Single source of truth for each phase
- ✅ Easier to test than full-context approach (Option D)
- ✅ Less duplication than mission embedding (Option A)

**Trade-offs Accepted**:
- Conditional branching in tool (manageable complexity)
- Tool has dual behavior (but clearly documented)
- Slight increase in test coverage needed

**Alternative If Rejected**: Option D (full context, self-navigate)
- Simpler implementation
- Relies on orchestrator intelligence
- Slightly higher token cost but within budget

**NOT Recommended**:
- Option A: Instruction drift risk, hard to update
- Option B: Schema overhead, UI complexity

---

## Next Steps

1. **Developer Review**: Discuss options and choose approach
2. ~~**Wait for 0355**~~: ✅ 0355 is COMPLETE - Step 7 (Execution Phase Monitoring) now exists in `thin_prompt_generator.py` lines 1003-1009
3. **Implement Chosen Option**: Follow rollout plan for selected approach
4. **Test in Alpha Trial**: Verify successors monitor agents effectively
5. **Update Documentation**: Close the loop on succession behavior docs

---

**Handover prepared by**: Documentation Manager Agent
**Review requested from**: Orchestrator Coordinator, System Architect
**Implementation assigned to**: TDD Implementor (backend changes), Frontend Tester (if UI changes needed)

---

## Session Context

This handover originated from the **0355 Implementation Research Session** (2025-12-19) where we discovered that orchestrator succession has a behavioral gap distinct from the message handling issues being fixed in 0355.

**Key Insight**: Agents get `full_protocol` with 5-phase lifecycle, but orchestrators get `staging_prompt` with 6-step workflow + Step 7 (execution monitoring). Successors need execution-phase guidance to complete the succession architecture.

**0355 Implementation Reference** (completed 2025-12-19):
- Agent protocol enhanced: `src/giljo_mcp/services/orchestration_service.py` lines 153-227
- Step 7 added: `src/giljo_mcp/thin_prompt_generator.py` lines 1003-1009
- Tests: `tests/services/test_orchestration_service_agent_mission.py`, `tests/thin_prompt/test_thin_prompt_unit.py`
- Commit: `484933e6 feat(0355): implement protocol message handling fix`

**Related Discussion**: See `handovers/0355_protocol_message_handling_fix.md` (Status: COMPLETE) for full implementation details.
