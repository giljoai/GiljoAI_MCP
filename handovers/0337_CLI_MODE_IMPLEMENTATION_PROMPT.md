# Handover 0337: CLI Mode Implementation Prompt Fix

**Status**: READY FOR IMPLEMENTATION
**Priority**: CRITICAL
**Date**: 2025-12-09
**Estimated Effort**: 4-6 hours
**Agent**: Documentation Manager (handover creation), Backend Integration Tester + TDD Implementor (execution)

---

## Executive Summary

The Claude Code CLI mode workflow is **BROKEN** at the implementation phase. Users can successfully stage projects (copy orchestrator prompt → orchestrator plans + spawns agents), but the `{} IMPLEMENT` button shows a misdirecting toast instead of generating the implementation prompt that would enable orchestrators to spawn agents via the Task tool.

**Impact**: CLI mode is unusable for implementation phase, forcing users to either switch to Multi-Terminal mode or manually construct agent spawning commands.

**Root Cause**: Handover 0261 documented the need for `/api/prompts/implementation/{project_id}` endpoint but it was never implemented. The implementation prompt generator method `_build_claude_code_execution_prompt()` exists in `thin_prompt_generator.py` but has no API endpoint calling it.

---

## ARCHITECTURE: Two-Stage CLI Mode Workflow

GiljoAI's Claude Code CLI mode operates in **two distinct stages** separated by user action:

### Stage 1: Staging (🚀 Launch Tab)
**User Action**: Click "Copy Orchestrator Prompt" button
**Purpose**: Plan mission and spawn agent jobs
**Orchestrator Tasks**:
1. Verify identity and MCP health
2. Understand environment and discover available agents
3. Analyze context priorities
4. Create mission plan
5. Spawn agent jobs via `spawn_agent_job()` MCP tool
6. Activate project for execution

**Output**:
- Mission saved to database
- Agent jobs created in `waiting` status
- Dashboard shows "Launch Jobs" button (navigates to {} IMPLEMENT tab)

### Stage 2: Implementation ({} IMPLEMENT Tab)
**User Action**: Click play `(>)` button on orchestrator card, copies implementation prompt
**Purpose**: Execute the planned work via Task tool spawning
**Orchestrator Tasks**:
1. Fetch orchestrator instructions if needed (refresh context)
2. Create TODO list of agents to launch
3. Update dashboard with task count
4. For each agent job, spawn via Task tool:
   ```python
   Task(
       subagent_type="{agent_type}",  # MUST match .claude/agents/{agent_type}.md
       prompt="Call get_agent_mission(job_id='{job_id}', tenant_key='{tenant_key}')"
   )
   ```
5. Monitor progress via `get_workflow_status()`
6. Complete when all agents done

**Output**:
- Agents transition from `waiting` → `working` → `completed`/`failed`/`blocked`
- Real-time dashboard updates
- Project completion

---

## Play Button `(>)` Behavior

The play icon `(>)` on agent cards is the **"copy prompt" button** that copies the agent's execution prompt to clipboard.

### Claude Code CLI Mode (execution_mode = 'claude_code_cli')
- **Orchestrator Card**: Play button `(>)` is FUNCTIONAL → Copies implementation prompt
- **Specialist Cards**: Play button `(>)` is HIDDEN (cards visible, buttons hidden)
- **Execution Pattern**: User pastes one prompt, orchestrator spawns all agents via Task tool

### Multi-Terminal Mode (execution_mode = 'multi_terminal')
- **Orchestrator Card**: Play button `(>)` copies orchestrator's execution prompt
- **Specialist Cards**: Each play button `(>)` copies that agent's individual prompt
- **Execution Pattern**: User pastes N prompts into N separate terminal windows

**Key Implementation Detail**: The `{} IMPLEMENT` button on orchestrator card in CLI mode calls `/api/prompts/implementation/{project_id}` (the endpoint we're adding in this handover).

---

## Fresh Session Assumption (CRITICAL)

The implementation prompt MUST assume the user is in a **fresh Claude Code session** (worst-case scenario):

**Why This Matters**:
- User may have closed the terminal after staging
- User may have done other work in between
- User may be resuming after hours/days
- User may have context limits and cleared chat

**Implementation Prompt Requirements**:
1. **Self-Contained**: Include all IDs (orch_id, project_id, tenant_key, job_ids)
2. **Refresh Instructions**: Provide option to re-fetch context if needed:
   ```
   If you need to refresh context:
   - get_orchestrator_instructions(orchestrator_id="{orch_id}", tenant_key="{tenant_key}")
   - get_workflow_status(project_id="{project_id}", tenant_key="{tenant_key}")
   ```
3. **Status Recap**: Brief summary of current state:
   ```
   You previously staged this project and spawned {N} agents:
   - {agent_name_1} (agent_type={type}, job_id={id}, status=waiting)
   - {agent_name_2} (agent_type={type}, job_id={id}, status=waiting)
   ```
4. **No Assumptions**: Don't assume orchestrator remembers prior conversation

**Template Structure**:
```markdown
# GiljoAI Implementation Phase - {project_name}

## Context Recap
You are orchestrator {orch_id} for project {project_id}.

You PREVIOUSLY completed staging:
- Created mission plan
- Spawned {N} agent jobs (now waiting)

## Current State
{agent_jobs_list}

## Your Task NOW
Launch these agents using Task tool...

## If You Need More Context
Call: get_orchestrator_instructions(orchestrator_id="{orch_id}", tenant_key="{tenant_key}")
```

---

## Agent Job State Machine

```
┌─────────┐
│ waiting │  ← Created by spawn_agent_job() in Stage 1
└────┬────┘
     │
     │ get_agent_mission() first call
     │ (atomically transitions state)
     ▼
┌─────────┐
│ working │
└────┬────┘
     │
     ├─→ ┌───────────┐
     │   │ completed │
     │   └───────────┘
     │
     ├─→ ┌────────┐
     │   │ failed │
     │   └────────┘
     │
     └─→ ┌─────────┐
         │ blocked │
         └─────────┘
```

**State Transitions**:
- `waiting`: Created during staging, agent not yet started
- `working`: Agent called `get_agent_mission()` and is executing (automatic transition)
- `completed`: Agent called `complete_job()` with results
- `failed`: Agent called `report_error()` or encountered unrecoverable issue
- `blocked`: Agent waiting on dependency or orchestrator decision

**Belt-and-Suspenders Enforcement**:
State transition instructions appear in TWO places:
1. **Implementation prompt** (this handover) - Tells orchestrator to spawn agents
2. **Agent template files** (`.claude/agents/{agent_type}.md`) - Tells agent to call `get_agent_mission()`

This redundancy ensures proper state transitions even if one instruction source is missed.

---

## Web-Driven Architecture (Server Cannot Push)

**Critical Constraint**: GiljoAI server CANNOT push prompts to user's terminal.

**Data Flow**:
```
Server (GiljoAI) ──WebSocket──> Browser UI
                                    │
                                    │ User copies prompt
                                    ▼
                              Clipboard
                                    │
                                    │ User pastes
                                    ▼
                           Terminal (Claude Code)
```

**Implications**:
- All prompts are **pull-based** (user initiates copy)
- Prompts must be available via HTTP API endpoints
- Frontend provides copy buttons that call API endpoints
- User is the bridge between server and terminal

**Why This Matters for This Handover**:
- We need `/api/prompts/implementation/{project_id}` endpoint
- JobsTab.vue must call this endpoint on button click
- Prompt must be complete and self-contained (no follow-up server communication during execution)

---

## Agent Spawning via Task Tool (Enforcement)

**CRITICAL**: The `subagent_type` parameter in Task tool MUST EXACTLY match the agent template filename.

```python
# ✅ CORRECT - Matches .claude/agents/implementer.md
Task(subagent_type="implementer", prompt="...")

# ❌ WRONG - File not found: .claude/agents/Folder Implementer.md
Task(subagent_type="Folder Implementer", prompt="...")

# ❌ WRONG - File not found: .claude/agents/backend-tester.md (if file is backend_tester.md)
Task(subagent_type="backend-tester", prompt="...")
```

**Validation Requirements**:
1. Implementation prompt MUST include exact `agent_type` from database
2. `agent_type` in database MUST match template filename (enforced by `spawn_agent_job()`)
3. Implementation prompt should list valid agent types for orchestrator reference

**Error Handling**:
If Task tool fails due to missing agent file:
```
Error: Subagent type 'X' not found in .claude/agents/
Available: ['implementer', 'tester', 'database-expert', ...]
```

---

## Dashboard Context

The `{} IMPLEMENT` button navigates to the **implementation dashboard**, a dedicated tab for monitoring execution.

**Dashboard Features**:
- **Agent Status Cards**: Shows all agents with status, progress, messages
- **Status Columns**: Health, status text, read/ack indicators, steps progress
- **Action Icons**: Launch `(>)`, Copy, Message, Cancel, Handover
- **Real-time Updates**: WebSocket-driven status changes

**Implementation Dashboard Layout**:
```
┌─────────────────────────────────────┐
│ {} IMPLEMENT Tab                    │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ Orchestrator Card               │ │
│ │ Status: active                  │ │
│ │ [>] Copy Implementation Prompt  │ │  ← This handover
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Implementer Card                │ │
│ │ Status: waiting                 │ │
│ │ (Play button hidden in CLI mode)│ │  ← Orchestrator spawns via Task
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Tester Card                     │ │
│ │ Status: waiting                 │ │
│ │ (Play button hidden in CLI mode)│ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Navigation Flow**:
1. User completes staging in 🚀 Launch Tab
2. "Launch Jobs" button appears
3. Click "Launch Jobs" → Navigate to {} IMPLEMENT tab
4. Click `(>)` on orchestrator card → Copy implementation prompt
5. Paste into Claude Code → Orchestrator spawns agents
6. Dashboard shows real-time status updates

---

## Multi-Terminal Mode Comparison

Understanding both execution modes helps clarify the requirements:

| Aspect | Claude Code CLI Mode | Multi-Terminal Mode |
|--------|---------------------|---------------------|
| **Terminals** | 1 (orchestrator spawns all) | N (one per agent) |
| **Play `(>)` Buttons** | Orchestrator only (specialist buttons hidden) | All agent cards show play button |
| **Spawning Mechanism** | Task tool (`subagent_type` parameter) | User manually copies/pastes each prompt |
| **Agent Isolation** | Shared terminal, orchestrator sees output | Separate terminals, MCP communication only |
| **Coordination** | Direct visibility + MCP tools | MCP tools only (messages, status checks) |
| **User Action** | Paste 1 prompt | Paste N prompts |
| **Prompt Endpoint** | `/api/prompts/implementation/{project_id}` | `/api/prompts/agent/{job_id}` (per agent) |
| **Agent Template Files** | Required in `.claude/agents/` | Not required (prompts are self-contained) |
| **Context Budget** | Shared among orchestrator + all agents | Separate context per agent |
| **Error Recovery** | Orchestrator can restart failed agents | User must manually re-paste failed agent prompts |
| **Use Case** | Single Claude Code CLI session | Multiple terminals or team collaboration |

**Key Architectural Difference**:
- **CLI Mode**: Server generates ONE implementation prompt that tells orchestrator how to spawn agents
- **Multi-Terminal Mode**: Server generates N agent prompts, each self-contained for that agent

---

## Problem Statement

### Current Broken Workflow

1. ✅ **Staging Phase**: User clicks "Copy Orchestrator Prompt" → Pastes into Claude Code → Orchestrator completes 7-task staging workflow → Agent jobs spawned
2. ❌ **Implementation Phase**: User clicks `{} IMPLEMENT` button on orchestrator job → Toast says "Use Launch tab" → **Dead end**

### What Should Happen

1. ✅ **Staging Phase**: (working)
2. ✅ **Implementation Phase**: User clicks `{} IMPLEMENT` → Prompt copied to clipboard → User pastes into same orchestrator chat → Orchestrator spawns agents via Task tool → Each agent calls `get_agent_mission()` → Implementation proceeds

### Evidence of Broken State

**JobsTab.vue Lines 591-601** (current misdirection):
```javascript
if (agent.agent_type === 'orchestrator') {
    showToast({
        message: "Use 'Copy Orchestrator Prompt' button in Launch tab for orchestrator prompts.",
        type: 'warning',
        duration: 4000
    })
    return
}
```

**No Implementation Endpoint** (`api/endpoints/prompts.py`):
- ✅ `/api/prompts/staging/{project_id}` (works)
- ❌ `/api/prompts/implementation/{project_id}` (MISSING)
- ⚠️ `/api/prompts/execution/{orchestrator_job_id}` (deprecated, redirects to staging)

**Unused Implementation Method** (`thin_prompt_generator.py` lines 1147-1207):
```python
def _build_claude_code_execution_prompt(
    self,
    orchestrator_job_id: str,
    agent_jobs: List[Dict],
    project_name: str,
    current_context_used: int,
    tenant_key: str,
    cli_mode_rules: Optional[Dict] = None,
) -> str:
    """Build Claude Code CLI execution prompt with Task tool instructions.

    THIS METHOD EXISTS BUT IS NEVER CALLED BY ANY ENDPOINT!
    """
```

---

## Technical Analysis

### Missing Components

1. **API Endpoint**: No `/api/prompts/implementation/{project_id}` route
2. **Frontend Integration**: JobsTab.vue shows toast instead of calling API
3. **Agent Naming Enforcement**: Implementation prompt must include agent_type → subagent_type mapping
4. **CLI Mode Rules**: Need to include or reference `cli_mode_rules` from orchestrator instructions

### Existing Assets (Ready to Use)

1. **Prompt Generator**: `_build_claude_code_execution_prompt()` fully implemented
2. **Database Schema**: All required fields exist (agent_jobs, orchestrator succession)
3. **MCP Tools**: `get_agent_mission()`, `get_available_agents()` fully functional
4. **Frontend**: `{} IMPLEMENT` button exists, just needs correct wiring

---

## Implementation Tasks

### Task 1: Create Implementation Prompt Endpoint

**File**: `api/endpoints/prompts.py`

**Requirements**:
- Route: `GET /api/prompts/implementation/{project_id}`
- Auth: Requires `X-API-Key` header
- Validation:
  - Project must exist and belong to authenticated tenant
  - Project must be in CLI mode (`execution_mode = 'claude_code_cli'`)
  - Orchestrator job must exist and be in `active` status
  - At least one spawned agent job must exist
- Response: `{ "prompt": str, "orchestrator_job_id": str, "agent_count": int }`

**Pseudocode**:
```python
@router.get("/implementation/{project_id}")
async def get_implementation_prompt(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_key: str = Depends(get_tenant_key)
):
    # 1. Fetch project (multi-tenant filtered)
    project = await ProjectService.get_by_id(session, project_id, tenant_key)
    if not project:
        raise HTTPException(404, "Project not found")

    # 2. Validate CLI mode
    if project.execution_mode != 'claude_code_cli':
        raise HTTPException(400, "Project is not in CLI mode")

    # 3. Fetch orchestrator job (active status only)
    orchestrator_job = await session.execute(
        select(MCPAgentJob)
        .where(
            MCPAgentJob.project_id == project_id,
            MCPAgentJob.agent_type == 'orchestrator',
            MCPAgentJob.status == 'active'
        )
        .order_by(MCPAgentJob.created_at.desc())
    )
    orch_job = orchestrator_job.scalar_one_or_none()
    if not orch_job:
        raise HTTPException(404, "No active orchestrator found")

    # 4. Fetch spawned agent jobs
    agent_jobs_result = await session.execute(
        select(MCPAgentJob)
        .where(
            MCPAgentJob.spawned_by == orch_job.id,
            MCPAgentJob.status.in_(['pending', 'active'])
        )
        .order_by(MCPAgentJob.created_at)
    )
    agent_jobs = agent_jobs_result.scalars().all()
    if not agent_jobs:
        raise HTTPException(400, "No agent jobs spawned yet - run staging first")

    # 5. Fetch CLI mode rules from orchestrator instructions
    orch_instructions = await OrchestrationService.get_orchestrator_instructions(
        session, orch_job.id, tenant_key
    )
    cli_mode_rules = orch_instructions.get('cli_mode_rules')

    # 6. Generate implementation prompt
    generator = ThinClientPromptGenerator(session, tenant_key)
    agent_jobs_dict = [
        {
            'job_id': str(job.id),
            'agent_type': job.agent_type,
            'agent_name': job.agent_name,
            'status': job.status
        }
        for job in agent_jobs
    ]

    prompt = await generator._build_claude_code_execution_prompt(
        orchestrator_job_id=str(orch_job.id),
        agent_jobs=agent_jobs_dict,
        project_name=project.name,
        current_context_used=orch_job.context_used or 0,
        tenant_key=tenant_key,
        cli_mode_rules=cli_mode_rules
    )

    return {
        "prompt": prompt,
        "orchestrator_job_id": str(orch_job.id),
        "agent_count": len(agent_jobs)
    }
```

**Error Handling**:
- 404: Project not found / No active orchestrator
- 400: Not CLI mode / No spawned agents
- 403: Tenant isolation violation
- 500: Database errors

**Testing Requirements**:
- Unit test: Endpoint validation logic
- Integration test: Full flow (staging → implementation prompt generation)
- E2E test: Manual CLI workflow (paste staging → paste implementation → verify Task tool spawning)

---

### Task 2: Update JobsTab.vue Implementation Button

**File**: `frontend/src/components/projects/JobsTab.vue`

**Current Code** (lines 591-601):
```javascript
if (agent.agent_type === 'orchestrator') {
    showToast({
        message: "Use 'Copy Orchestrator Prompt' button in Launch tab for orchestrator prompts.",
        type: 'warning',
        duration: 4000
    })
    return
}
```

**Replacement**:
```javascript
if (agent.agent_type === 'orchestrator') {
    // CLI mode: Generate implementation prompt
    if (project.execution_mode === 'claude_code_cli') {
        try {
            const response = await api.get(`/api/prompts/implementation/${project.id}`)
            const prompt = response.data.prompt
            await navigator.clipboard.writeText(prompt)
            showToast({
                message: `Implementation prompt copied! (${response.data.agent_count} agents ready)`,
                type: 'success',
                duration: 5000
            })
        } catch (error) {
            const errorMsg = error.response?.data?.detail || 'Failed to generate implementation prompt'
            showToast({
                message: errorMsg,
                type: 'error',
                duration: 6000
            })
        }
        return
    }

    // Multi-terminal mode: Redirect to Launch tab
    showToast({
        message: "Use 'Copy Orchestrator Prompt' button in Launch tab for orchestrator prompts.",
        type: 'warning',
        duration: 4000
    })
    return
}
```

**Considerations**:
- Add loading state during API call
- Handle clipboard permission errors
- Show agent count in success message for user feedback
- Differentiate error messages (404 vs 400 vs 500)

**Testing Requirements**:
- Unit test: Click handler logic (mock API response)
- E2E test: Visual verification of toast messages
- Manual test: Copy-paste workflow in real Claude Code CLI

---

### Task 3: Verify Implementation Prompt Content

**File**: `src/giljo_mcp/thin_prompt_generator.py`

**Method**: `_build_claude_code_execution_prompt()` (lines 1147-1207)

**Required Content Verification**:

The implementation prompt must be **self-contained** and assume a **fresh session**. It should include:

1. **Context Recap** (Fresh Session Support):
   ```markdown
   # GiljoAI Implementation Phase - {project_name}

   ## Who You Are
   You are the Orchestrator (job_id: `{orch_job_id}`) for project `{project_id}`.
   Tenant: `{tenant_key}`

   ## What You've Already Done
   In a PREVIOUS session, you completed staging:
   - Analyzed project requirements
   - Created mission plan (saved to database)
   - Spawned {N} specialist agents (currently waiting)

   ## Current State
   All agent jobs are in "waiting" status, ready for execution.
   ```

2. **Agent Jobs List** (with complete metadata):
   ```markdown
   ## Spawned Agents Ready for Execution

   1. **{agent_name_1}**
      - Agent Type: `{agent_type}` (matches .claude/agents/{agent_type}.md)
      - Job ID: `{job_id}`
      - Status: waiting
      - Mission Summary: {first 100 chars of mission}

   2. **{agent_name_2}**
      - Agent Type: `{agent_type}`
      - Job ID: `{job_id}`
      - Status: waiting
      - Mission Summary: {first 100 chars of mission}

   [... for each agent ...]
   ```

3. **Task Tool Spawning Instructions** (with concrete examples):
   ```markdown
   ## Your Task: Launch Agents via Task Tool

   Use Claude Code's Task tool to spawn each agent. For each agent above:

   ### Spawning Template
   ```python
   Task(
       subagent_type="{agent_type}",  # EXACT match required
       prompt="""
   You are the {agent_name} for project "{project_name}".

   CRITICAL FIRST STEP: Fetch your mission from the server:

   mcp__giljo-mcp__get_agent_mission(
       agent_job_id="{job_id}",
       tenant_key="{tenant_key}"
   )

   This call will:
   1. Transition your status from "waiting" to "working"
   2. Return your complete mission and 6-phase protocol
   3. Provide MCP tool references and communication patterns

   Execute the protocol returned in the "full_protocol" field.
   """
   )
   ```

   ### Example (First Agent)
   ```python
   Task(
       subagent_type="{actual_agent_type_from_db}",
       prompt="""
   You are the {actual_agent_name} for project "{project_name}".

   Call: mcp__giljo-mcp__get_agent_mission(
       agent_job_id="{actual_job_id}",
       tenant_key="{actual_tenant_key}"
   )

   Then execute the full_protocol instructions.
   """
   )
   ```

   **Important**:
   - Spawn all agents in parallel (multiple Task calls simultaneously)
   - Do NOT wait for one agent to complete before spawning the next
   - Orchestrator can monitor progress via `get_workflow_status()`
   ```

4. **Monitoring Instructions**:
   ```markdown
   ## Monitoring Agent Progress

   After spawning all agents:

   1. **Check Overall Status**:
      ```python
      mcp__giljo-mcp__get_workflow_status(
          project_id="{project_id}",
          tenant_key="{tenant_key}"
      )
      ```
      Returns: `{progress_percent, active_agents, completed_agents, failed_agents}`

   2. **Check for Messages**:
      ```python
      mcp__giljo-mcp__receive_messages(agent_id="orchestrator")
      ```
      Agents may send status updates, questions, or blockers.

   3. **Real-time Dashboard**:
      - The GiljoAI dashboard shows live agent status
      - You'll see agents transition: waiting → working → completed
      - Steps column shows TODO-style progress (e.g., "3/5")
   ```

5. **Context Refresh Instructions** (if needed):
   ```markdown
   ## If You Need More Context

   This prompt assumes a fresh session. If you need to refresh your understanding:

   **Fetch Full Orchestrator Instructions**:
   ```python
   mcp__giljo-mcp__get_orchestrator_instructions(
       orchestrator_id="{orch_job_id}",
       tenant_key="{tenant_key}"
   )
   ```
   Returns: Complete mission with context priorities, field depth settings, etc.

   **Check Current Workflow State**:
   ```python
   mcp__giljo-mcp__get_workflow_status(
       project_id="{project_id}",
       tenant_key="{tenant_key}"
   )
   ```
   ```

6. **CLI Mode Constraints** (critical warnings):
   ```markdown
   ## CLI Mode Constraints

   ⚠️ **Agent Template Files Required**:
   - Each agent_type must have a matching file in `.claude/agents/{agent_type}.md`
   - Example: `agent_type="implementer"` requires `.claude/agents/implementer.md`
   - If file missing, Task tool will fail with "Subagent type not found"

   ⚠️ **Exact Naming Required**:
   - Use EXACT agent_type from the list above as subagent_type parameter
   - Do NOT use agent_name (display name) as subagent_type
   - Example: Use "implementer" not "Folder Structure Implementer"

   ⚠️ **MCP Communication**:
   - All agents run in THIS terminal (you can see their output)
   - Agents communicate via MCP tools (send_message, get_next_instruction)
   - No shared memory - all coordination via MCP server
   ```

7. **Completion Instructions**:
   ```markdown
   ## When All Agents Complete

   1. Verify all work via `get_workflow_status()` (progress_percent == 100)
   2. Complete orchestrator job:
      ```python
      mcp__giljo-mcp__complete_job(
          job_id="{orch_job_id}",
          result={"summary": "All {N} agents completed successfully"}
      )
      ```
   3. Optionally add to 360 Memory:
      ```python
      mcp__giljo-mcp__close_project_and_update_memory(
          project_id="{project_id}",
          summary="Project completion summary...",
          key_outcomes=["outcome1", "outcome2"],
          decisions_made=["decision1", "decision2"]
      )
      ```
   ```

**Verification Steps**:
1. Read current implementation of `_build_claude_code_execution_prompt()`
2. Ensure all 7 required sections are present
3. Verify fresh session assumptions (no context from prior conversation)
4. Verify concrete examples use actual data (job_ids, tenant_key, agent_types)
5. Verify Task tool template is copy-paste ready
6. Add unit tests for prompt content validation
7. Test with actual orchestrator in fresh Claude Code session

---

### Task 4: Agent Type Validation

**Requirement**: Ensure agent_type values in spawned jobs match available `.claude/agents/*.md` files.

**Implementation Location**: `_build_claude_code_execution_prompt()` or endpoint validation

**Logic**:
```python
# In endpoint or prompt generator
available_agents = await get_available_agents(tenant_key, active_only=True)
valid_agent_types = {agent['agent_type'] for agent in available_agents}

for agent_job in agent_jobs:
    if agent_job['agent_type'] not in valid_agent_types:
        raise ValueError(
            f"Agent type '{agent_job['agent_type']}' not found in available agents. "
            f"Valid types: {sorted(valid_agent_types)}"
        )
```

**Error Handling**:
- Fail early if spawned agents reference non-existent agent types
- Provide clear error message listing valid agent types
- Log validation errors for debugging

**Testing**:
- Unit test: Invalid agent_type raises ValueError
- Integration test: Staging spawns only valid agent types
- E2E test: Implementation prompt includes only available agents

---

## Success Criteria

### Functional Requirements

✅ **FR1**: `/api/prompts/implementation/{project_id}` endpoint exists and returns prompt
✅ **FR2**: JobsTab `{} IMPLEMENT` button calls endpoint and copies prompt to clipboard
✅ **FR3**: Implementation prompt includes agent list with job_ids
✅ **FR4**: Implementation prompt includes Task tool spawning instructions
✅ **FR5**: Agent spawning uses exact agent_type → subagent_type mapping
✅ **FR6**: CLI mode rules included in prompt (inline or referenced)
✅ **FR7**: Error handling for missing orchestrator / no spawned agents
✅ **FR8**: Multi-tenant isolation enforced at endpoint level

### Testing Requirements

✅ **TR1**: Unit tests for endpoint validation logic (pytest)
✅ **TR2**: Unit tests for prompt content verification (assert sections present)
✅ **TR3**: Integration test: Staging → Implementation prompt generation
✅ **TR4**: E2E manual test: Full CLI workflow (staging + implementation)
✅ **TR5**: Frontend unit test: Click handler with mocked API
✅ **TR6**: Agent type validation unit test (invalid type raises error)

### E2E Manual Test Protocol

**Pre-conditions**:
- Fresh GiljoAI installation with PostgreSQL running
- User registered and logged in
- Project created with `execution_mode = 'claude_code_cli'`
- At least 2 agent templates exist in `.claude/agents/` (e.g., implementer, tester)
- Claude Code CLI installed with MCP configured

**Test Steps**:

**Part 1: Staging Phase**
1. Navigate to 🚀 Launch Tab
2. Click "Copy Orchestrator Prompt" button
3. Open Claude Code CLI terminal
4. Paste staging prompt
5. **Verify**: Orchestrator completes 7-task staging workflow:
   - ✅ Identity verification
   - ✅ MCP health check
   - ✅ Environment understanding
   - ✅ Agent discovery
   - ✅ Context prioritization
   - ✅ Job spawning (at least 2 agents)
   - ✅ Activation
6. **Verify**: Dashboard shows "Launch Jobs" button
7. **Verify**: Database shows agent jobs in `waiting` status:
   ```sql
   SELECT agent_type, status FROM mcp_agent_jobs WHERE project_id = '<project_id>';
   -- Expected: 2+ rows with status='waiting'
   ```

**Part 2: Implementation Phase (This Handover's Focus)**
8. Click "Launch Jobs" button → Navigate to {} IMPLEMENT tab
9. **Verify**: Orchestrator card visible with play `(>)` button
10. **Verify**: Specialist cards visible but play buttons HIDDEN (CLI mode)
11. Click play `(>)` on orchestrator card
12. **Verify**: Toast appears: "Implementation prompt copied! (X agents ready)"
    - ❌ Should NOT show: "Use 'Copy Orchestrator Prompt' button in Launch tab"
13. **Verify**: Clipboard contains implementation prompt
14. Paste implementation prompt into SAME Claude Code terminal (fresh session simulation: can close and reopen)
15. **Verify**: Orchestrator creates TODO list of agents to launch
16. **Verify**: Orchestrator spawns each agent via Task tool:
    ```
    Task(subagent_type="implementer", prompt="...")
    Task(subagent_type="tester", prompt="...")
    ```
17. **Verify**: Each spawned agent calls `get_agent_mission()` as FIRST action
18. **Verify**: Database shows agent status transitions:
    ```sql
    SELECT agent_type, status, mission_acknowledged_at
    FROM mcp_agent_jobs
    WHERE project_id = '<project_id>';
    -- Expected: status='working', mission_acknowledged_at IS NOT NULL
    ```
19. **Verify**: Dashboard updates in real-time:
    - Agent status changes from "waiting" to "working"
    - Steps column shows progress (e.g., "0/5" → "3/5" → "5/5")
    - Health indicators update
20. **Verify**: Agents execute 6-phase protocol:
    - Phase 1: ACKNOWLEDGE (automatic via get_agent_mission)
    - Phase 2: ANALYZE
    - Phase 3: PLAN (report TODO steps)
    - Phase 4: EXECUTE (update progress)
    - Phase 5: VERIFY
    - Phase 6: COMPLETE (call complete_job)
21. **Verify**: Orchestrator monitors via `get_workflow_status()`
22. **Verify**: All agents complete successfully
23. **Verify**: Dashboard shows all agents in "completed" status
24. **Verify**: No manual intervention required (orchestrator handles everything)

**Expected Results**:

✅ **Staging Phase**:
- Orchestrator prompt copies successfully
- Staging completes with all 7 tasks
- Agent jobs created in `waiting` status
- "Launch Jobs" button appears

✅ **Implementation Phase**:
- `{} IMPLEMENT` button shows orchestrator card
- Specialist play buttons hidden (cards remain visible)
- Play `(>)` on orchestrator card copies implementation prompt
- Toast shows agent count (not error message)
- Implementation prompt is self-contained (works in fresh session)

✅ **Prompt Content**:
- Includes context recap (who you are, what you've done)
- Lists all spawned agents with job_ids
- Provides Task tool spawning template
- Includes monitoring instructions
- Has context refresh instructions
- Lists CLI mode constraints

✅ **Execution**:
- Orchestrator spawns all agents via Task tool
- Each agent calls `get_agent_mission()` successfully
- Status transitions: waiting → working → completed
- Dashboard updates in real-time via WebSocket
- All agents complete without errors
- No "file not found" errors for agent templates

**Failure Scenarios to Test**:

❌ **Missing Agent Template**:
- Remove one agent template from `.claude/agents/`
- Verify Task tool fails with clear error: "Subagent type 'X' not found"

❌ **Wrong Agent Type**:
- Manually edit implementation prompt to use agent_name instead of agent_type
- Verify Task tool fails with "file not found"

❌ **No Spawned Agents**:
- Call implementation endpoint before staging completes
- Verify 400 error: "No agent jobs spawned yet - run staging first"

❌ **Multi-Terminal Mode**:
- Switch project to multi-terminal mode
- Verify orchestrator play button shows different prompt (agent-specific, not implementation)

**Performance Criteria**:
- Staging prompt generation: <1 second
- Implementation prompt generation: <500ms
- Agent spawning (orchestrator): <2 seconds per agent
- Status transitions: Real-time (<100ms WebSocket latency)
- Dashboard updates: Immediate visual feedback

**Cleanup**:
```sql
-- After test, verify database state
SELECT
    agent_type,
    status,
    mission_acknowledged_at IS NOT NULL as acknowledged,
    completed_at IS NOT NULL as completed
FROM mcp_agent_jobs
WHERE project_id = '<project_id>'
ORDER BY created_at;

-- Expected: All rows show status='completed', acknowledged=true, completed=true
```

---

## Risk Assessment

### High Risk

1. **Breaking Multi-Terminal Mode**: Ensure new endpoint only activates for CLI mode projects
   - Mitigation: Explicit `execution_mode` check in endpoint
   - Testing: Multi-terminal projects should not be affected

2. **Prompt Content Errors**: Missing sections could break Task tool spawning
   - Mitigation: Unit tests validate all required sections present
   - Testing: Mock prompt generation and assert content structure

### Medium Risk

1. **Agent Type Mismatches**: Spawned agents reference non-existent `.md` files
   - Mitigation: Add agent_type validation in Task 4
   - Testing: Integration test with invalid agent types

2. **Clipboard API Failures**: Browser permissions or HTTPS requirements
   - Mitigation: Try/catch with fallback error message
   - Testing: Manual testing in different browsers

### Low Risk

1. **Context Budget Overflow**: Implementation prompt too large
   - Mitigation: Prompt is ~500-800 tokens (well under budget)
   - Testing: Token counting in unit tests

---

## Related Handovers

- **0261**: CLI Implementation Prompt (documented need, never implemented)
- **0260**: CLI Toggle Enhancement (execution_mode field)
- **0335**: CLI Mode Template Validation (session complete, staleness tracking)
- **0334**: HTTP-Only MCP (full_protocol in get_agent_mission response)
- **0246a-c**: Orchestrator Workflow Pipeline (staging → discovery → spawning → execution)
- **0243c**: JobsTab dynamic status fix (real-time updates foundation)

---

## Implementation Checklist

**Backend** (TDD Implementor):
- [ ] Create `/api/prompts/implementation/{project_id}` endpoint
- [ ] Add endpoint to `api/endpoints/prompts.py`
- [ ] Import endpoint in `api/app.py`
- [ ] Add Pydantic response schema
- [ ] Write unit tests for endpoint validation
- [ ] Write integration test: staging → implementation prompt
- [ ] Verify `_build_claude_code_execution_prompt()` content
- [ ] Add agent_type validation logic
- [ ] Test multi-tenant isolation

**Frontend** (Frontend Tester):
- [ ] Update JobsTab.vue click handler (lines 591-601)
- [ ] Add loading state during API call
- [ ] Differentiate success/error toast messages
- [ ] Write unit test for click handler
- [ ] Manual test in real browser (clipboard API)

**Testing** (Backend Integration Tester):
- [ ] E2E manual test: Full CLI workflow
- [ ] Verify toast messages in UI
- [ ] Verify prompt content in clipboard
- [ ] Test error scenarios (404, 400, 403)
- [ ] Regression test: Multi-terminal mode unaffected

**Documentation** (Documentation Manager):
- [ ] Update `docs/CLI_MODE.md` with implementation workflow
- [ ] Add implementation endpoint to API reference
- [ ] Update user guide with screenshots
- [ ] Create session memory for handover completion

---

## Estimated Timeline

**Total**: 4-6 hours

- **Task 1** (Backend endpoint): 1.5-2 hours
- **Task 2** (Frontend update): 1 hour
- **Task 3** (Prompt verification): 1-1.5 hours
- **Task 4** (Agent validation): 0.5-1 hour
- **Testing & Documentation**: 1 hour

**Dependencies**: None (all required components exist)

**Blockers**: None identified

---

## Notes

- This handover fixes a CRITICAL user-facing workflow gap
- Implementation method already exists → Low implementation risk
- High user impact → Should be prioritized over feature work
- Manual E2E test is REQUIRED before closing handover
- Consider adding telemetry for implementation prompt usage (future enhancement)

**Agent Assignment Recommendation**:
- **Backend**: TDD Implementor (endpoint + tests)
- **Frontend**: Frontend Tester (UI update + E2E verification)
- **Coordination**: Orchestrator Coordinator (workflow validation)

---

## Summary: Key Architectural Clarifications

This handover documents not just the missing implementation, but the complete two-stage architecture:

### Two-Stage Workflow
1. **Staging (🚀 Launch)**: Orchestrator plans → Spawns agent jobs → Jobs wait
2. **Implementation ({} IMPLEMENT)**: Orchestrator executes → Spawns via Task → Agents run

### Play Button `(>)` Behavior
- **CLI Mode**: Orchestrator only (specialists hidden)
- **Multi-Terminal**: All agents (each gets own prompt)

### Fresh Session Design
- Implementation prompt is **self-contained**
- No assumptions about prior conversation
- Includes refresh instructions if needed

### State Machine
```
waiting → working → completed/failed/blocked
         ↑
   get_agent_mission()
   (automatic transition)
```

### Belt-and-Suspenders
- **Implementation prompt**: Tells orchestrator to spawn
- **Agent templates**: Tell agent to call get_agent_mission()

### Web-Driven Pull Architecture
- Server CANNOT push to terminal
- User copies from browser → pastes to terminal
- Prompts via HTTP API endpoints

### Agent Spawning Enforcement
```python
Task(subagent_type="{agent_type}")  # Must match .claude/agents/{agent_type}.md
```

### Dashboard Context
- `{} IMPLEMENT` is a dedicated tab
- Shows agent cards with status/progress
- Real-time WebSocket updates
- Play `(>)` = copy prompt button

---

## Implementation Priority

This handover is **CRITICAL** because:
1. **User-facing workflow is broken** - CLI mode unusable at implementation phase
2. **Code already exists** - Just needs wiring (low implementation risk)
3. **High user impact** - Affects all CLI mode users
4. **Clear acceptance criteria** - Manual E2E test protocol provided

**Recommendation**: Prioritize over new feature work until CLI mode workflow is functional end-to-end.

---

**End of Handover 0337**
