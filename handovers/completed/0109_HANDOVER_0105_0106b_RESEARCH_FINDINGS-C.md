---
**Handover**: 0109 Research Supplement
**Date**: 2025-01-06
**Status**: Research Complete - Ready for Implementation
**Related Handovers**: 0105, 0106b, 0109
---

# Research Findings: Existing Claude Code Sub-Agent Logic (Handovers 0105 & 0106b)

## Executive Summary

**CRITICAL DISCOVERY**: Comprehensive Claude Code sub-agent spawning logic **ALREADY EXISTS** in handovers 0105 and 0106b. This validates and clarifies the Product Owner's statement: *"We have some of this logic done I think, we did in project 103-108 somewhere."*

**Key Findings**:
1. ✅ **Handover 0105**: Claude Code toggle UI implemented (frontend)
2. ✅ **Handover 0106b**: Complete sub-agent spawning guide (640 lines, production-ready)
3. ✅ **Agent ID Passing**: Fully documented mechanism via `spawn_agent_job()` MCP tool
4. ✅ **Integration Code**: `claude_code_integration.py` provides helper functions
5. ❌ **Gap**: ThinClientPromptGenerator NOT YET enhanced for execution phase

---

## Part 1: Handover 0105 Implementation (Completed 2025-11-06)

### What Was Implemented

**Feature 1: Claude Code Toggle UI** ✅
- **File**: `frontend/src/components/projects/JobsTab.vue` (+62 lines)
- **Component**: `v-switch` with orange robot icon
- **Default State**: OFF (multi-terminal mode)
- **Toggle Behavior**:
  - **OFF**: All agent buttons active (yellow rocket icon, "Launch Agent")
  - **ON**: Only orchestrator active, others disabled (grey pause icon, "Claude Code Mode")

**Feature 2: Mission Persistence Fix** ✅
- **File**: `src/giljo_mcp/thin_prompt_generator.py` (lines 242-255)
- **Change**: Added Step 3 to orchestrator staging prompt
  ```
  3. PERSIST mission: mcp__giljo-mcp__update_project_mission('{project_id}', mission)
  ```
- **Purpose**: Saves orchestrator-created mission to database for UI display

### Key Code References

**Toggle State Control** (`JobsTab.vue:348-355`):
```javascript
function shouldDisablePromptButton(agent) {
  if (!usingClaudeCodeSubagents.value) return false
  return agent.agent_type !== 'orchestrator'
}
```

**Dynamic Hint Text** (`JobsTab.vue:58-62`):
```javascript
const toggleHintText = computed(() => {
  return usingClaudeCodeSubagents.value
    ? 'Only orchestrator prompt active - Claude spawns subagents via MCP'
    : 'Normal mode - All agents launch as independent MCP instances'
})
```

### Architectural Decisions (ADRs)

**ADR-0105-01**: UI-Only Toggle (No Database Persistence)
- **Rationale**: User preference may vary per session
- **Consequence**: Must toggle ON each time (could add localStorage later)

**ADR-0105-02**: Default Toggle State is OFF
- **Rationale**: Preserves existing workflow, least surprise
- **Consequence**: Claude Code users must manually toggle ON

**ADR-0105-03**: Thin Prompt Instruction Pattern
- **Rationale**: Explicit control, auditable, thin client philosophy
- **Alternative Rejected**: Auto-save in `get_orchestrator_instructions()`

### What's Missing from 0105

❌ **Execution Phase Prompts**: Toggle changes button states but NOT prompt content
❌ **Prompt Generation Logic**: No different prompts for multi-terminal vs Claude Code mode
❌ **Agent Spawn Instructions**: Orchestrator prompt doesn't include sub-agent spawn commands

---

## Part 2: Handover 0106b Implementation Guide (640 Lines)

### Complete Sub-Agent Spawning Flow

**Document**: `handovers/completed/reference/0106/0106b_claude_code_subagent_spawning_guide.md`
**Lines**: 640 (comprehensive implementation guide)
**Status**: Production-ready, tested patterns

### THREE-STEP SPAWNING PROCESS

#### **Step 1: Backend Registration** (Lines 43-93)

```python
# Orchestrator calls MCP tool FIRST
result = spawn_agent_job(
    agent_type="implementer",
    agent_name="implementer-backend",
    mission="Implement user authentication endpoints",
    project_id="{project_id}",
    tenant_key="{tenant_key}"
)

# Extract credentials (THIS IS HOW AGENT ID IS PASSED!)
agent_id = result['agent_id']    # e.g., "implementer-abc123"
job_id = result['job_id']        # e.g., "job-xyz789"
```

**Error Handling**:
- Agent type not active (not in 8 active types)
- Rate limiting (max 10 agents per minute)
- Multi-tenant isolation errors

#### **Step 2: Claude Code Task Tool** (Lines 99-211)

```python
# Prepare instructions with credentials
instructions = f"""
# YOUR IDENTITY
Agent ID: {agent_id}
Job ID: {job_id}
Tenant Key: {tenant_key}
Project ID: {project_id}
Agent Type: implementer

# YOUR MISSION
Implement user authentication endpoints...

# CHECK-IN PROTOCOL (CRITICAL)
After each milestone:
1. report_progress(job_id="{job_id}", agent_id="{agent_id}", ...)
2. receive_messages(agent_id="{agent_id}", ...)
3. Handle cancel/pause commands

# MCP TOOLS YOU MUST USE
- acknowledge_job(job_id="{job_id}", agent_id="{agent_id}", tenant_key="{tenant_key}")
- complete_job(job_id="{job_id}", result={...}, tenant_key="{tenant_key}")
- send_message(to_agent="orchestrator", message="...", tenant_key="{tenant_key}")
- report_error(job_id="{job_id}", error="...", tenant_key="{tenant_key}")

BEGIN YOUR WORK:
"""

# Spawn subagent using Task tool (ANTHROPIC API)
response = client.messages.create(
    model="claude-sonnet-4",
    max_tokens=8000,
    tools=[{"name": "task", "description": "Spawn a subagent"}],
    messages=[{
        "role": "user",
        "content": [{
            "type": "tool_use",
            "name": "task",
            "input": {
                "name": "implementer-backend",
                "instructions": instructions
            }
        }]
    }]
)
```

**KEY INSIGHT**: Agent ID is **INJECTED INTO INSTRUCTIONS STRING** as part of identity section!

#### **Step 3: Monitor Execution** (Lines 215-260)

```python
async def monitor_subagent(job_id, timeout_minutes=30):
    while True:
        job = await get_job_status(job_id, tenant_key)

        if job['status'] == 'complete':
            # Success
            break
        elif job['status'] == 'failed':
            # Handle failure
            break
        elif job['status'] == 'blocked':
            # Send guidance
            await send_message(...)

        # Check timeout
        if elapsed > timeout_minutes:
            await request_job_cancellation(job_id, "Timeout", tenant_key)
            break

        await asyncio.sleep(30)
```

### Error Scenarios (Lines 264-379)

**Scenario 1**: Subagent never calls `acknowledge_job()`
- **Detection**: Job stuck in `waiting` after 5 minutes
- **Solutions**: Check logs, verify credentials, respawn

**Scenario 2**: Subagent stops reporting progress
- **Detection**: 0107 passive monitoring (10+ minutes stale)
- **Action**: Send nudge message, wait 5 min, then cancel if unresponsive

**Scenario 3**: Claude Code Task tool fails
- **Error**: `anthropic.APIError: Task tool not available`
- **Solutions**: Check Claude Code version >= 1.5.0, verify MCP connection, fallback to multi-terminal

**Scenario 4**: Wrong credentials passed
- **Symptom**: "Job not found" or "Access denied"
- **Solution**: Verify `job_id`, `agent_id`, `tenant_key` injection

### Testing Checklist (Lines 381-483)

**6 Comprehensive Tests**:
1. ✅ Basic subagent spawn
2. ✅ Progress reporting
3. ✅ Message reception (cancel command)
4. ✅ Error handling (blocked status)
5. ✅ Dynamic spawning (add 4th agent mid-execution)
6. ✅ Failure recovery (kill terminal, detect stale)

### Integration Points

**With 0106 (Template Protection)**:
- System Instructions (non-editable): Sub-agent spawn protocol
- User Instructions (editable): Role-specific guidance

**With 0107 (Monitoring & Cancellation)**:
- Check-in protocol: `report_progress()` + `receive_messages()`
- Passive monitoring detects stale sub-agents
- Graceful cancellation via message queue

**With 0105 (Mission Workflow)**:
- Toggle ON → Only orchestrator button active
- All sub-agent buttons grayed out (spawned automatically)

---

## Part 3: Existing Integration Code

### File: `src/giljo_mcp/tools/claude_code_integration.py`

**Purpose**: Helper functions for Claude Code integration

**Key Functions**:

1. **`get_claude_code_agent_type(mcp_role)`**
   - Maps GiljoAI roles to Claude Code agent types
   - Example: `"database"` → `"database-expert"`
   - Example: `"backend"` → `"tdd-implementor"`

2. **`generate_agent_spawn_instructions(project_id, tenant_key)`**
   - Reads project agents from database
   - Creates mapping for orchestrator spawning
   - Returns agent list with missions

3. **`generate_orchestrator_prompt(project_id, tenant_key)`**
   - **LEGACY**: Generates orchestrator prompt with agent list
   - **NOTE**: NOT using thin client pattern (pre-0088)
   - **ACTION NEEDED**: Replace with ThinClientPromptGenerator enhancement

**Agent Type Mapping**:
```python
CLAUDE_CODE_AGENT_TYPES = {
    "orchestrator": "orchestrator-coordinator",
    "database": "database-expert",
    "backend": "tdd-implementor",
    "implementor": "tdd-implementor",
    "tester": "backend-integration-tester",
    "researcher": "deep-researcher",
    "architect": "system-architect",
    "frontend": "ux-designer",
    "security": "network-security-engineer",
    "documentation": "documentation-manager",
    "reviewer": "general-purpose",
}
```

**NOTE**: This mapping is for **Claude Code's native agent types**, NOT GiljoAI's custom agent templates!

---

## Part 4: Gap Analysis - What Still Needs Implementation

### HIGH PRIORITY

#### 1. **ThinClientPromptGenerator Enhancement** 🔴

**Current State**: Generates ONLY staging prompt
**Needed**: Generate execution phase prompts with Claude Code mode support

**Files to Modify**:
- `src/giljo_mcp/thin_prompt_generator.py`
- Add `generate_execution_prompt()` method
- Add `claude_code_mode` parameter

**Prompt Differences Needed**:

**Multi-Terminal Mode Execution Prompt**:
```
PROJECT EXECUTION PHASE - MULTI-TERMINAL MODE

Your role: COORDINATE AGENT WORKFLOW
- Agents will check in as they start
- You coordinate, agents execute
- User will manually nudge terminals as needed

AGENT TEAM:
- Implementer1 (Agent ID: {uuid1})
- Tester1 (Agent ID: {uuid2})
- Reviewer1 (Agent ID: {uuid3})
```

**Claude Code Subagent Mode Execution Prompt**:
```
PROJECT EXECUTION PHASE - CLAUDE CODE SUBAGENT MODE

STEP 1: ACTIVATE YOUR AGENT TEAM
Spawn the following sub-agents (use Task tool):

FOR EACH AGENT:
1. Call spawn_agent_job() to get credentials
2. Extract agent_id and job_id
3. Build instructions with identity + mission + check-in protocol
4. Spawn via Task tool with instructions

AGENT LIST:
- Implementer1: {mission from MCPAgentJob}
- Tester1: {mission from MCPAgentJob}
- Reviewer1: {mission from MCPAgentJob}

STEP 2: REMIND AGENTS
Each sub-agent must:
- acknowledge_job() at startup
- report_progress() after milestones
- receive_messages() for commands
- complete_job() when done

STEP 3: IF YOU NEED MORE AGENTS
- Call spawn_agent_job() for new agent
- Get new agent_id
- Spawn sub-agent with instructions
```

**Implementation Estimate**: 3-4 hours

---

#### 2. **API Endpoint for Execution Prompts** 🔴

**Missing**: `GET /api/prompts/execution/{orchestrator_job_id}`

**Requirements**:
- Accept `claude_code_mode` query parameter (boolean)
- Fetch existing MCPAgentJob records for project
- Generate appropriate prompt based on mode
- Return thin prompt (~15-20 lines)

**File to Create**: `api/endpoints/prompts.py` (add new endpoint)

**Implementation Estimate**: 2 hours

---

#### 3. **Frontend Integration** 🟡

**JobsTab Enhancement Needed**:
- Orchestrator card needs "Copy Execution Prompt" button
- Button calls new API endpoint with toggle state
- Dialog displays generated prompt

**File to Modify**: `frontend/src/components/projects/JobsTab.vue`

**Implementation Estimate**: 1-2 hours

---

### MEDIUM PRIORITY

#### 4. **Update `claude_code_integration.py`** 🟡

**Current Issue**: Uses legacy prompt generation (pre-thin client)

**Action**:
- Mark `generate_orchestrator_prompt()` as DEPRECATED
- Add note: "Use ThinClientPromptGenerator.generate_execution_prompt() instead"
- Keep `CLAUDE_CODE_AGENT_TYPES` mapping for reference

**Implementation Estimate**: 30 minutes

---

## Part 5: Answer to Product Owner's Question

### Original Question

> "We have some of this logic done I think, we did in project 103-108 somewhere. If not we need to."

### Answer

**YES, IT EXISTS!** ✅

**What's Done** (Handovers 0105 & 0106b):
1. ✅ Claude Code toggle UI (0105)
2. ✅ Complete sub-agent spawning guide (0106b - 640 lines)
3. ✅ Agent ID passing mechanism (via `spawn_agent_job()` + instructions string injection)
4. ✅ Error handling scenarios (documented)
5. ✅ Testing checklist (6 comprehensive tests)
6. ✅ Integration with templates, monitoring, cancellation

**What's NOT Done**:
1. ❌ Execution phase prompt generation (staging prompt exists, execution doesn't)
2. ❌ ThinClientPromptGenerator enhancement for Claude Code mode
3. ❌ API endpoint for execution prompts
4. ❌ Frontend "Copy Execution Prompt" button

**Estimated Effort to Complete**: 6-8 hours
- ThinClientPromptGenerator: 3-4 hours
- API endpoint: 2 hours
- Frontend integration: 1-2 hours

---

## Part 6: Implementation Priority Recommendation

Based on findings, recommended implementation order:

### Phase 1: Complete Execution Prompt Generation (HIGH PRIORITY)

**Tasks**:
1. Enhance `ThinClientPromptGenerator` with execution phase logic
2. Add `generate_execution_prompt()` method
3. Support multi-terminal mode prompt
4. Support Claude Code subagent mode prompt
5. Create API endpoint `/api/prompts/execution/{orchestrator_job_id}`

**Effort**: 5-6 hours
**Blockers**: None (toggle UI already exists)
**Value**: Completes the orchestrator → execution flow

---

### Phase 2: Frontend Integration (MEDIUM PRIORITY)

**Tasks**:
1. Add "Copy Execution Prompt" button to orchestrator card
2. Call new API endpoint with toggle state
3. Display prompt in dialog

**Effort**: 1-2 hours
**Blockers**: Requires Phase 1 completion
**Value**: User-friendly prompt access

---

### Phase 3: Deprecate Legacy Code (LOW PRIORITY)

**Tasks**:
1. Mark `claude_code_integration.py` functions as deprecated
2. Update documentation to reference ThinClientPromptGenerator
3. Add migration notes

**Effort**: 30 minutes
**Blockers**: None
**Value**: Code cleanup, prevent confusion

---

## Part 7: Key Takeaways for Handover 0109

### Critical Insights

1. **Agent ID Passing Mechanism**: ✅ FULLY DOCUMENTED
   - Orchestrator calls `spawn_agent_job()` MCP tool
   - Receives `agent_id` and `job_id` in response
   - Injects into instructions string for sub-agent
   - Sub-agent reads identity from instructions

2. **Two-Phase Orchestrator Model**: ✅ VALIDATED
   - **Staging Phase**: Orchestrator creates mission, spawns agent records
   - **Execution Phase**: Orchestrator activates agents (multi-terminal OR Claude Code)
   - Product Owner's vision is CORRECT

3. **Template Export NOT Automatic**: ✅ CLARIFIED
   - Developer responsibility (via Template Manager UI)
   - Export happens BEFORE staging/execution
   - Templates must be in `~/.claude/agents/` for Claude Code mode

4. **Toggle Changes Prompt Content**: ✅ IDENTIFIED GAP
   - Toggle UI exists (0105)
   - Prompt generation logic MISSING (needs implementation)

### Updated Implementation Gaps

**From Original 0109 Investigation**:
- ❌ Missing `/api/v1/orchestration/launch-project` endpoint (still needed)
- ❌ Agent template context request behavior (still needed)
- ⚠️ ThinClientPromptGenerator for Claude Code mode (partially exists, needs execution phase)
- ⚠️ Claude Code sub-agent spawning (documented in 0106b, needs prompt integration)

**From 0105/0106b Research**:
- ✅ Toggle UI exists
- ✅ Sub-agent spawning patterns documented
- ✅ Agent ID passing mechanism clarified
- ❌ Execution prompt generation MISSING
- ❌ API endpoint for execution prompts MISSING
- ❌ Frontend prompt copy button MISSING

---

## Part 8: Code References

### Key Files

**Handover Documents**:
- `F:\GiljoAI_MCP\handovers\completed\0105_IMPLEMENTATION_COMPLETE-C.md`
- `F:\GiljoAI_MCP\handovers\completed\reference\0106\0106b_claude_code_subagent_spawning_guide.md`

**Implementation Files**:
- `F:\GiljoAI_MCP\frontend\src\components\projects\JobsTab.vue` (toggle UI)
- `F:\GiljoAI_MCP\frontend\src\components\projects\AgentCardEnhanced.vue` (button states)
- `F:\GiljoAI_MCP\src\giljo_mcp\thin_prompt_generator.py` (staging prompt only)
- `F:\GiljoAI_MCP\src\giljo_mcp\tools\claude_code_integration.py` (legacy, pre-thin client)
- `F:\GiljoAI_MCP\src\giljo_mcp\tools\orchestration.py` (spawn_agent_job MCP tool)

**Testing Files**:
- `F:\GiljoAI_MCP\tests\integration\test_claude_code_integration.py`

---

## Part 9: Next Steps for Handover 0109

### Immediate Actions

1. ✅ **Research Complete**: 0105 & 0106b analyzed
2. ⏳ **Update Handover 0109**: Add findings to main document
3. ⏳ **Create Implementation Plan**: Based on validated patterns
4. ⏳ **Prioritize Tasks**: Launch endpoint → Execution prompts → Context requests

### Questions Answered

**Q1**: How do spawned sub-agents receive their Agent ID?
**A1**: Orchestrator injects `agent_id` into instructions string (documented in 0106b:99-211)

**Q2**: Do agent templates in ~/.claude/agents/ automatically get MCP tool access?
**A2**: Yes, templates include MCP instructions in system_instructions field (0106 protection)

**Q3**: Where was Claude Code sub-agent logic previously implemented?
**A3**: Handover 0106b (640-line implementation guide) + Handover 0105 (toggle UI)

**Q4**: Can orchestrator dynamically create new agent jobs and spawn them mid-project?
**A4**: Yes, documented in 0106b:453-465 (Test 5: Dynamic Spawning)

---

## Conclusion

**Research Validates Product Owner's Statement**: The logic DOES exist (Handovers 0105 & 0106b), but needs final integration with ThinClientPromptGenerator for execution phase.

**Estimated Completion Time**: 6-8 hours to fully wire together existing components

**Recommended Next Step**: Implement execution phase prompts in ThinClientPromptGenerator, leveraging patterns from 0106b

---

## Progress Updates

### 2025-11-06: Research Complete and Implementation Delivered ✅
- **Status**: Research objectives completed and all recommendations implemented
- **Research Findings**: Validated existing Claude Code sub-agent logic in Handovers 0105 & 0106b
- **Implementation Status**: ThinClientPromptGenerator execution phase support fully delivered
- **Key Deliverables**: 
  - ✅ `generate_execution_prompt()` method implemented (Multi-Terminal & Claude Code modes)
  - ✅ API endpoint `/api/v1/prompts/execution/{orchestrator_job_id}` deployed
  - ✅ Comprehensive test coverage (420+ lines)
  - ✅ Production validation complete
- **Follow-up**: Minor WebSocket issues tracked in Handover 0111

**Research Document Status**: ✅ COMPLETE - Served its purpose, implementation delivered

---

**Document Status**: Research Complete
**Next Document**: Updated Handover 0109 with integrated findings
**Implementation Ready**: Phase 1 tasks can begin immediately

---
