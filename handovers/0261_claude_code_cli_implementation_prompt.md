# Handover 0261: Claude Code CLI Implementation Prompt

> **Note**: Staging prompt aspects of this handover are superseded by Handover 0333.
> The two-phase architecture concept remains valid, but staging prompt is simplified.
> See 0333 for the corrected staging prompt pattern.

**Date**: 2025-12-07
**Agent**: Documentation Manager
**Status**: Pending Implementation
**Predecessor**: Handover 0260 (Claude Code CLI Toggle Enhancement)

## Executive Summary

This handover addresses critical gaps in Handover 0260's Claude Code CLI mode implementation. While 0260 successfully implemented toggle persistence and mode-specific prompt generation, it left three key gaps:

1. **Staging Prompt Gap**: Strict `agent_type` vs `agent_name` guidance only added when `claude_code_mode=True`, but staging happens BEFORE mode is relevant
2. **Implementation Phase Gap**: No dedicated implementation prompt for CLI mode orchestrator
3. **Agent Mission Completeness**: Need to verify `get_agent_mission()` returns complete agent protocol

**Impact**: Without these fixes, orchestrators in CLI mode will receive incomplete instructions for Task tool spawning, and staging prompts won't consistently enforce agent_type validation.

---

## CRITICAL: Two-Phase Prompt Architecture

GiljoAI uses a **two-phase prompt approach** that separates planning from execution:

### Phase 1: Staging Prompt (Launch Tab)
- **When**: User clicks "Copy Staging Prompt" in Launch tab
- **Purpose**: Orchestrator analyzes requirements, creates mission, spawns agent jobs
- **Output**: Mission saved, agent jobs in "waiting" status
- **Mode-agnostic**: Same staging prompt regardless of toggle setting
- **Key rule**: `agent_type` MUST be exact template name (enforced ALWAYS)

### Phase 2: Implementation Prompt(s) (Jobs Tab)
- **When**: User clicks copy buttons in Jobs tab (labeled `{} IMPLEMENT`)
- **Purpose**: Execute the planned work

**Toggle OFF (Multi-Terminal Mode)**:
- Each agent has its own copy button
- Each prompt tells that specific agent to fetch its mission and execute
- User opens N terminal windows

**Toggle ON (Claude Code CLI Mode)**:
- Only orchestrator has copy button (specialist copy buttons hidden, agent cards visible)
- ONE implementation prompt for orchestrator
- Orchestrator uses Task tool to spawn subagents
- Each subagent calls `get_agent_mission()` to fetch its mission + protocol

### Why Two Phases?

| Aspect | Staging Prompt | Implementation Prompt |
|--------|---------------|----------------------|
| Context | Heavy (fetches vision, architecture, 360 memory) | Lightweight (just agent jobs list) |
| Purpose | Plan and spawn | Execute and coordinate |
| Output | Mission + agent jobs | Completed work |
| Tokens | ~1000-2000 | ~200-500 |

The separation allows:
1. Re-running implementation without re-staging
2. Different execution modes for same staging
3. Resuming failed implementations
4. Parallel development (one terminal stages, another implements)

---

## Context & Background

### Two-Phase Workflow

GiljoAI orchestration operates in two distinct phases:

**Phase 1: Staging (Launch Tab)**
- User activates project and copies [Stage Project] prompt
- Orchestrator analyzes requirements and creates execution plan
- Spawns specialist agents via `spawn_agent_job()` with exact template names
- Agent jobs created in "waiting" status
- **Result**: Mission planned, agents registered but not executing

**Phase 2: Implementation (Jobs Tab - {} IMPLEMENT)**
- User switches to Jobs tab to execute the planned work
- **Toggle OFF (Multi-Terminal Mode)**: Each agent has copy button → N terminals
- **Toggle ON (Claude Code CLI Mode)**: Only orchestrator has copy button → ONE terminal with Task tool spawning

### Handover 0260 Achievements

Handover 0260 successfully implemented:

1. **Toggle Persistence**:
   - Added `execution_mode` column to `projects` table
   - Toggle state saved on change via WebSocket
   - Retrieved on page load

2. **Mode-Specific Staging Prompts**:
   - `generate_staging_prompt(claude_code_mode: bool)`
   - CLI mode adds strict agent_type guidance

3. **Agent Type Validation**:
   - `spawn_agent_job()` validates `agent_type` against exact template names
   - Raises `ValueError` if invalid

### Gaps Identified

**Gap 1: Staging Prompt Agent Type Guidance Placement**

Current code in `thin_prompt_generator.py`:

```python
if claude_code_mode:
    prompt_parts.append("""
AGENT SPAWNING RULES (CRITICAL):
- agent_type: MUST be EXACTLY one of the template names (e.g., "implementer", "backend-tester")
- agent_name: Can be descriptive for UI display (e.g., "Folder Structure Implementer")
""")
```

**Problem**: Staging happens BEFORE execution mode matters. The staging prompt should ALWAYS enforce strict agent_type, regardless of whether the user will later choose CLI or multi-terminal mode.

**Gap 2: Missing CLI Mode Implementation Prompt**

Current behavior:
- Toggle ON in Jobs tab → Only orchestrator copy button visible
- **But what prompt does it copy?**
- No dedicated "implementation phase" prompt for CLI mode
- Orchestrator needs Task tool spawning instructions

**Gap 3: get_agent_mission() Completeness Unknown**

When Task tool spawns subagent, subagent calls:
```python
get_agent_mission(job_id="{job_id}", tenant_key="{tenant_key}")
```

**Unknown**: Does this return complete agent protocol?
- Mission content ✓ (confirmed in 0260)
- Job lifecycle instructions? (acknowledge, progress, complete)
- Communication behaviors? (how to message orchestrator)
- MCP tool usage patterns?

---

## Detailed Requirements

### Task 1: Move Strict Agent Type Guidance to Base Staging Prompt

**File**: `src/giljo_mcp/thin_prompt_generator.py`

**Change**: Move agent_type vs agent_name rules OUTSIDE the `claude_code_mode` conditional.

**Before** (lines ~120-130):
```python
def generate_staging_prompt(..., claude_code_mode: bool = False):
    prompt_parts = [...]

    if claude_code_mode:
        prompt_parts.append("""
AGENT SPAWNING RULES (CRITICAL):
- agent_type: MUST be EXACTLY one of the template names
...
""")

    return "\n\n".join(prompt_parts)
```

**After**:
```python
def generate_staging_prompt(..., claude_code_mode: bool = False):
    prompt_parts = [...]

    # ALWAYS include strict agent_type guidance (applies to ALL modes)
    prompt_parts.append("""
AGENT SPAWNING RULES (CRITICAL):
- agent_type: MUST be EXACTLY one of the template names (e.g., "implementer", "backend-tester")
- agent_name: Can be descriptive for UI display (e.g., "Folder Structure Implementer")

Example - Spawning 2 implementers:
  spawn_agent_job(agent_type="implementer", agent_name="Folder Structure Implementer", ...)
  spawn_agent_job(agent_type="implementer", agent_name="README Writer", ...)

Validation: The spawn_agent_job() tool will reject invalid agent_type values.
""")

    if claude_code_mode:
        # CLI-specific instructions (if any remaining)
        pass

    return "\n\n".join(prompt_parts)
```

**Rationale**:
- Staging prompt is mode-agnostic (same orchestrator, same validation)
- `spawn_agent_job()` validation happens during staging, before mode selection
- Consistency: All orchestrators should follow same spawning rules

---

### Task 2: Create CLI Mode Implementation Prompt

**Files**:
- `src/giljo_mcp/thin_prompt_generator.py` (new method)
- `api/endpoints/prompts.py` (new endpoint or modify existing)
- `frontend/src/components/projects/JobsTab.vue` (call new endpoint)

**New Method**: `ThinClientPromptGenerator.generate_implementation_prompt()`

```python
def generate_implementation_prompt(
    self,
    project_id: str,
    tenant_key: str,
    orchestrator_job_id: str,
    agent_jobs: list[dict]  # [{"job_id": "...", "agent_type": "...", "agent_name": "..."}]
) -> str:
    """
    Generate implementation prompt for Claude Code CLI mode.

    Called after staging is complete (mission planned, agents spawned).
    Orchestrator uses Claude Code Task tool to spawn subagents who fetch their missions.
    """

    agent_list = "\n".join([
        f"- {job['agent_name']} (agent_type={job['agent_type']}, job_id={job['job_id']})"
        for job in agent_jobs
    ])

    return f"""# GiljoAI Implementation Phase (Claude Code CLI Mode)

**Project ID**: {project_id}
**Orchestrator Job ID**: {orchestrator_job_id}
**Tenant Key**: {tenant_key}

## Your Role

You are the **Orchestrator** for this project. Staging is complete:
- Mission has been planned and saved
- Specialist agents have been spawned and are waiting
- You will now coordinate their execution using Claude Code's Task tool

## Agent Jobs to Execute

{agent_list}

## Execution Instructions

### Step 1: Spawn Subagents Using Task Tool

For each agent job above, use Claude Code's built-in Task tool:

```
Use Task tool with:
- subagent_type: Exact agent_type from list above (e.g., "implementer", "backend-tester")
- instructions: "Call get_agent_mission(job_id='{{job_id}}', tenant_key='{tenant_key}') to fetch your mission and begin execution."
```

**Example**:
If agent list shows:
- Folder Structure Implementer (agent_type=implementer, job_id=abc-123)

You would:
```
Task(
    subagent_type="implementer",
    instructions="Call get_agent_mission(job_id='abc-123', tenant_key='{tenant_key}') to fetch your mission and begin execution."
)
```

### Step 2: Monitor Subagent Progress

    Each subagent will:
    1. Call `get_agent_mission(job_id, tenant_key)` as its FIRST MCP tool call to atomically
       acknowledge the job and fetch its specific mission
2. Execute their 6-phase protocol (acknowledge → analyze → plan → execute → verify → complete)
3. Report progress via MCP message tools
4. Mark job complete when done

You should:
- Monitor messages from subagents via `receive_messages()`
- Check workflow status via `get_workflow_status()`
- Coordinate dependencies if agents are blocked
- Escalate issues if agents fail

### Step 3: Complete Orchestration

When all agents report completion:
1. Verify all work is done via `get_workflow_status()`
2. Complete your orchestrator job via `complete_job()`
3. Optionally call `close_project_and_update_memory()` to add this project to 360 Memory

## MCP Tools Available

- `get_agent_mission(job_id, tenant_key)` - Fetch agent-specific mission (used by subagents)
- `receive_messages(agent_id)` - Check messages from subagents
- `get_workflow_status(project_id, tenant_key)` - Monitor overall progress
- `complete_job(job_id, result)` - Mark orchestrator job complete
- `close_project_and_update_memory(project_id, summary, ...)` - Add to 360 Memory

## Notes

- **Subagent Isolation**: Each Task tool invocation creates a separate Claude conversation
- **Mission Fetch**: Subagents are thin clients - they fetch full instructions from server
- **Auditability**: All agent activity tracked in database (job status, messages, progress)
- **Real-time Updates**: WebSocket events notify UI of status changes

Begin by spawning the first subagent using the Task tool.
"""
```

**New API Endpoint**: `GET /api/prompts/implementation/{project_id}`

```python
@router.get("/implementation/{project_id}")
async def get_implementation_prompt(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate implementation prompt for Claude Code CLI mode.
    Called from Jobs tab when toggle is ON and user clicks orchestrator copy button.
    """
    # Fetch project and verify execution_mode = "claude_code_cli"
    project = await session.get(Project, project_id)
    if not project or project.execution_mode != "claude_code_cli":
        raise HTTPException(status_code=400, detail="Project not in CLI mode")

    # Fetch orchestrator job
    orchestrator_job = await session.execute(
        select(AgentJob)
        .where(AgentJob.project_id == project_id)
        .where(AgentJob.agent_type == "orchestrator")
        .where(AgentJob.status.in_(["active", "waiting"]))
    )
    orchestrator_job = orchestrator_job.scalar_one_or_none()

    # Fetch spawned agent jobs (waiting status)
    agent_jobs_result = await session.execute(
        select(AgentJob)
        .where(AgentJob.project_id == project_id)
        .where(AgentJob.agent_type != "orchestrator")
        .where(AgentJob.status == "waiting")
    )
    agent_jobs = [
        {"job_id": job.id, "agent_type": job.agent_type, "agent_name": job.agent_name}
        for job in agent_jobs_result.scalars()
    ]

    # Generate prompt
    generator = ThinClientPromptGenerator(session)
    prompt = generator.generate_implementation_prompt(
        project_id=project_id,
        tenant_key=current_user.tenant_key,
        orchestrator_job_id=orchestrator_job.id,
        agent_jobs=agent_jobs
    )

    return {"prompt": prompt}
```

**Frontend Integration**: Modify `JobsTab.vue` orchestrator copy button click handler:

```javascript
async function copyOrchestratorPrompt() {
  if (project.execution_mode === 'claude_code_cli') {
    // CLI mode: Fetch implementation prompt
    const response = await fetch(`/api/prompts/implementation/${project.id}`);
    const data = await response.json();
    await navigator.clipboard.writeText(data.prompt);
  } else {
    // Multi-terminal mode: Use existing staging prompt
    // (or fetch agent-specific prompt if orchestrator is a specialist too)
    const response = await fetch(`/api/prompts/agent/${orchestratorJob.id}`);
    const data = await response.json();
    await navigator.clipboard.writeText(data.prompt);
  }

  showSnackbar('Orchestrator prompt copied to clipboard');
}
```

---

### Task 3: Verify and Enhance get_agent_mission() Completeness

**File**: `src/giljo_mcp/tools/orchestration.py`

**Current Implementation** (from Handover 0260):
```python
@mcp_server.call_tool()
async def get_agent_mission(
    job_id: str,
    tenant_key: str
) -> Sequence[types.TextContent]:
    """Fetch agent-specific mission for spawned agent."""

    async with DatabaseSessionManager.get_session() as session:
        agent_job = await session.get(AgentJob, job_id)

        # Return mission content
        return [types.TextContent(type="text", text=agent_job.mission)]
```

**Enhancement Needed**: Return COMPLETE agent protocol, not just mission text.

**Proposed Enhanced Implementation**:

```python
@mcp_server.call_tool()
async def get_agent_mission(
    job_id: str,
    tenant_key: str
) -> Sequence[types.TextContent]:
    """
    Fetch complete agent protocol for spawned specialist agent.

    Returns:
    - Agent-specific mission
    - Job lifecycle instructions (acknowledge, progress, complete)
    - Communication behaviors (messaging orchestrator)
    - MCP tool usage patterns
    """

    async with DatabaseSessionManager.get_session() as session:
        agent_job = await session.get(AgentJob, job_id)

        if not agent_job or agent_job.tenant_key != tenant_key:
            raise ValueError(f"Agent job {job_id} not found for tenant {tenant_key}")

        # Build complete agent protocol
        protocol = f"""# Agent Mission: {agent_job.agent_name}

**Agent Type**: {agent_job.agent_type}
**Job ID**: {job_id}
**Project ID**: {agent_job.project_id}
**Tenant Key**: {tenant_key}

---

## Your Mission

{agent_job.mission}

---

## Job Lifecycle Protocol

You MUST follow this 6-phase protocol:

### Phase 1: INITIALIZE & FETCH MISSION
- Optionally call `health_check()` to verify MCP connectivity.
- Then call `get_agent_mission(job_id="{job_id}", tenant_key="{tenant_key}")` as your FIRST MCP tool call.
  This SINGLE call both acknowledges the job and fetches your mission in CLI subagent mode.

### Phase 2: ANALYZE
- Understand your mission thoroughly
- Identify dependencies on other agents
- Check `get_workflow_status(project_id="{agent_job.project_id}", tenant_key="{tenant_key}")` if blocked

### Phase 3: PLAN
- Break mission into concrete steps
- Send structured plan/TODOs to orchestrator:
  `send_message(to_agents=["orchestrator"], content="Plan: ...", project_id="{agent_job.project_id}", message_type="plan")`

### Phase 4: EXECUTE
- Implement your mission
- Report incremental progress and TODO-style Steps:
  `report_progress(job_id="{job_id}", progress={{"mode": "todo", "total_steps": N, "completed_steps": k, "current_step": "short description"}})`

### Phase 5: VERIFY
- Test your work
- Ensure quality standards met
- Send verification update to orchestrator

### Phase 6: COMPLETE
Call `complete_job(job_id="{job_id}", result={{"summary": "...", "files_modified": [...]}})` when done.

---

## Communication Rules

**Messaging Orchestrator**:
```python
send_message(
    to_agents=["orchestrator"],
    content="Your message here",
    project_id="{agent_job.project_id}",
    message_type="direct",
    priority="normal"  # or "high" for urgent issues
)
```

**Broadcasting to All Agents**:
```python
send_message(
    to_agents=["all"],
    content="Announcement",
    project_id="{agent_job.project_id}",
    message_type="broadcast"
)
```

**Checking Messages**:
```python
receive_messages(agent_id="{agent_job.agent_type}")
```

---

## Error Handling

If you encounter blocking issues:
1. Send urgent message to orchestrator with `priority="high"`
2. Call `report_error(job_id="{job_id}", error="Description")` to pause job
3. Wait for orchestrator guidance

---

## MCP Tools Available

- `acknowledge_job(job_id, agent_id)` - Mark job as active
- `report_progress(job_id, progress)` - Incremental updates
- `complete_job(job_id, result)` - Mark job complete
- `report_error(job_id, error)` - Pause job and escalate
- `send_message(to_agents, content, project_id, ...)` - Send messages
- `receive_messages(agent_id)` - Check inbox
- `get_workflow_status(project_id, tenant_key)` - Monitor overall progress
- `get_next_instruction(job_id, agent_type, tenant_key)` - Check for orchestrator updates

---

Begin with Phase 1: Acknowledge your job to mark yourself as active.
"""

        return [types.TextContent(type="text", text=protocol)]
```

**Rationale**:
- **Self-Contained**: Agent receives complete instructions in one call
- **Standardized Protocol**: All agents follow same 6-phase workflow
- **Communication Patterns**: Clear examples of how to message orchestrator
- **Error Handling**: Guidance on what to do when blocked
- **MCP Tool Reference**: Quick reference for available tools

**Testing**:
1. Spawn agent job via `spawn_agent_job()`
2. Call `get_agent_mission()` with job_id
3. Verify returned text includes:
   - Mission content
   - 6-phase protocol instructions
   - Communication examples with correct project_id/tenant_key
   - MCP tool reference

---

### Task 4: Update Jobs Tab UI for CLI Mode Copy Behavior

**File**: `frontend/src/components/projects/JobsTab.vue`

**Current Behavior** (from Handover 0260):
```javascript
// Toggle ON: Only orchestrator copy button visible
// Toggle OFF: All agent copy buttons visible
```

**Required Changes**:

1. **Orchestrator Copy Button**: Call different endpoint based on toggle state
2. **Specialist Copy Buttons**: Hide when toggle ON (but keep agent cards visible)

**Implementation**:

```vue
<template>
  <!-- Claude Code CLI Mode Toggle -->
  <v-switch
    v-model="claudeCodeMode"
    label="Claude Code CLI Mode"
    @change="saveExecutionMode"
    density="compact"
  />

  <!-- Orchestrator Section -->
  <v-card v-if="orchestratorJob">
    <v-card-title>Orchestrator</v-card-title>
    <v-card-text>
      <p>{{ orchestratorJob.agent_name }}</p>
      <v-btn @click="copyOrchestratorPrompt" color="primary">
        {{ claudeCodeMode ? 'Copy Implementation Prompt' : 'Copy Orchestrator Prompt' }}
      </v-btn>
    </v-card-text>
  </v-card>

  <!-- Specialist Agents Section -->
  <v-card v-for="job in specialistJobs" :key="job.id">
    <v-card-title>{{ job.agent_name }}</v-card-title>
    <v-card-text>
      <p>Type: {{ job.agent_type }}</p>
      <p>Status: {{ job.status }}</p>

      <!-- Copy button hidden in CLI mode, but card remains visible -->
      <v-btn
        v-if="!claudeCodeMode"
        @click="copyAgentPrompt(job.id)"
        color="secondary"
      >
        Copy Agent Prompt
      </v-btn>

      <p v-else class="text-caption">
        (Execution handled by orchestrator via Task tool)
      </p>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useProjectStore } from '@/stores/project';

const projectStore = useProjectStore();
const claudeCodeMode = ref(false);

const orchestratorJob = computed(() =>
  projectStore.agentJobs.find(j => j.agent_type === 'orchestrator')
);

const specialistJobs = computed(() =>
  projectStore.agentJobs.filter(j => j.agent_type !== 'orchestrator')
);

async function copyOrchestratorPrompt() {
  const endpoint = claudeCodeMode.value
    ? `/api/prompts/implementation/${projectStore.activeProject.id}`
    : `/api/prompts/agent/${orchestratorJob.value.id}`;

  const response = await fetch(endpoint);
  const data = await response.json();
  await navigator.clipboard.writeText(data.prompt);

  showSnackbar('Orchestrator prompt copied to clipboard');
}

async function copyAgentPrompt(jobId) {
  const response = await fetch(`/api/prompts/agent/${jobId}`);
  const data = await response.json();
  await navigator.clipboard.writeText(data.prompt);

  showSnackbar('Agent prompt copied to clipboard');
}

async function saveExecutionMode() {
  const mode = claudeCodeMode.value ? 'claude_code_cli' : 'multi_terminal';
  await fetch(`/api/projects/${projectStore.activeProject.id}/execution-mode`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ execution_mode: mode })
  });
}

onMounted(async () => {
  // Load toggle state from project
  claudeCodeMode.value = projectStore.activeProject.execution_mode === 'claude_code_cli';
});
</script>
```

**Key Points**:
- **Orchestrator Button Text**: Changes based on toggle ("Copy Implementation Prompt" vs "Copy Orchestrator Prompt")
- **Orchestrator Endpoint**: Routes to `/api/prompts/implementation/{project_id}` in CLI mode
- **Specialist Cards**: Remain visible in CLI mode for status monitoring
- **Specialist Buttons**: Hidden in CLI mode with explanatory text
- **Toggle Persistence**: Saved to `projects.execution_mode` on change

---

## Implementation Checklist

### Backend Changes
- [ ] Move strict agent_type guidance to base staging prompt (Task 1)
- [ ] Add `generate_implementation_prompt()` method to `ThinClientPromptGenerator` (Task 2)
- [ ] Create `/api/prompts/implementation/{project_id}` endpoint (Task 2)
- [ ] Enhance `get_agent_mission()` to return complete agent protocol (Task 3)
- [ ] Write unit tests for implementation prompt generation
- [ ] Write integration test for CLI mode end-to-end flow

### Frontend Changes
- [ ] Update `JobsTab.vue` orchestrator copy button handler (Task 4)
- [ ] Update button text based on toggle state (Task 4)
- [ ] Hide specialist copy buttons (not cards) when toggle ON (Task 4)
- [ ] Add explanatory text for specialist cards in CLI mode (Task 4)

### Testing
- [ ] Verify staging prompt includes agent_type guidance in both modes
- [ ] Test implementation prompt generation with multiple agents
- [ ] Verify `get_agent_mission()` returns complete protocol
- [ ] E2E test: Stage project → Toggle ON → Copy implementation prompt → Verify content
- [ ] E2E test: Stage project → Toggle OFF → Copy agent prompts → Verify content

### Documentation
- [ ] Update `docs/ORCHESTRATOR.md` with two-phase workflow explanation
- [ ] Update `docs/components/STAGING_WORKFLOW.md` with CLI mode details
- [ ] Add implementation prompt example to `docs/guides/`
- [ ] Update handover completion status in this document

---

## Success Criteria

1. **Staging Prompt Consistency**:
   - `generate_staging_prompt()` ALWAYS includes strict agent_type guidance
   - Both CLI and multi-terminal modes receive same spawning rules
   - Validation: Review generated staging prompt in both modes

2. **CLI Mode Implementation Prompt**:
   - `/api/prompts/implementation/{project_id}` endpoint returns complete prompt
   - Prompt includes Task tool spawning instructions for each agent job
   - Orchestrator copy button in Jobs tab calls correct endpoint
   - Validation: Copy implementation prompt and verify it includes all spawned agents

3. **Complete Agent Protocol**:
   - `get_agent_mission()` returns mission + 6-phase protocol + communication patterns
   - Spawned Task tool agents can successfully fetch and execute missions
   - Validation: Call `get_agent_mission()` and verify response includes all sections

4. **UI Behavior**:
   - Toggle ON: Orchestrator copy button visible, specialist buttons hidden
   - Toggle OFF: All copy buttons visible
   - Agent cards remain visible in both modes for status monitoring
   - Validation: Manual testing of Jobs tab with toggle in both states

---

## Related Handovers

- **Handover 0260**: Claude Code CLI Toggle Enhancement (predecessor)
- **Handover 0262**: Agent Mission Protocol Merge Analysis (companion - discusses get_agent_mission vs GenericAgentTemplate)
- **Handover 0246a-c**: Orchestrator Workflow Pipeline (staging workflow)
- **Handover 0253**: Universal Orchestrator Prompt (prompt generation patterns)
- **Handover 0088**: Thin Client Architecture (MCP tool-based mission fetching)

---

## Notes for Implementer

### Architecture Context

This handover completes the Claude Code CLI mode feature by addressing the **implementation phase**. The architecture is:

1. **Staging Phase** (Launch Tab):
   - Orchestrator plans mission
   - Spawns agent jobs with exact template names
   - Jobs created in "waiting" status

2. **Implementation Phase** (Jobs Tab):
   - **Multi-Terminal Mode**: User copies N prompts, opens N terminals, each agent runs independently
   - **CLI Mode**: User copies 1 prompt, orchestrator uses Task tool to spawn subagents, subagents fetch missions via `get_agent_mission()`

### Why Two Separate Prompts?

**Staging Prompt**:
- Analysis and planning
- Context-heavy (fetches product vision, architecture, etc.)
- Outputs: mission plan + spawned agent jobs

**Implementation Prompt** (CLI mode only):
- Execution coordination
- Lightweight (just lists agent jobs and Task tool instructions)
- Outputs: Task tool invocations for each specialist

### Agent Type Validation Flow

```
User → Orchestrator Staging Prompt
  ↓
Orchestrator calls spawn_agent_job(agent_type="implementer", ...)
  ↓
Tool validates agent_type against exact template names
  ↓
If valid: Creates AgentJob with mission
If invalid: Raises ValueError

User → Implementation Prompt (CLI mode)
  ↓
Orchestrator spawns Task(subagent_type="implementer", instructions="fetch mission...")
  ↓
Task tool agent calls get_agent_mission(job_id="...")
  ↓
Returns complete agent protocol (mission + lifecycle + communication)
```

### Testing Strategy

1. **Unit Tests**:
   - `test_generate_staging_prompt_always_includes_agent_type_rules()`
   - `test_generate_implementation_prompt_includes_all_agents()`
   - `test_get_agent_mission_returns_complete_protocol()`

2. **Integration Tests**:
   - `test_cli_mode_implementation_prompt_endpoint()`
   - `test_staging_to_implementation_flow()`

3. **E2E Tests**:
   - Create project → Activate → Stage → Toggle ON → Copy implementation prompt
   - Verify prompt includes Task tool instructions for all spawned agents
   - Verify `get_agent_mission()` returns complete protocol when called

---

## Estimated Effort

**Total**: 6-8 hours

- Task 1 (Move agent_type guidance): 1 hour
- Task 2 (Implementation prompt + endpoint): 3-4 hours
- Task 3 (Enhance get_agent_mission): 1-2 hours
- Task 4 (Frontend UI updates): 1 hour
- Testing & Documentation: 1-2 hours

---

## Completion Checklist

- [ ] All backend changes implemented and tested
- [ ] All frontend changes implemented and tested
- [ ] E2E test passing for CLI mode workflow
- [ ] Documentation updated (ORCHESTRATOR.md, STAGING_WORKFLOW.md)
- [ ] Handover reviewed and approved by orchestrator
- [ ] Code committed with reference to Handover 0261
- [ ] This document moved to `handovers/completed/` upon completion

---

**End of Handover 0261**
