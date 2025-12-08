# Handover 0333: Staging Prompt Architecture Correction

## Status: READY FOR IMPLEMENTATION

## Priority: HIGH - Staging prompt is currently broken

## Supersedes / Corrects
- **0260**: Move CLI toggle from Implement tab → Launch tab
- **0261**: Remove broken staging prompt, restore simple pattern
- **Preserves**: 0262 backend protocol (atomic get_agent_mission), 0297/0331 UI work (Steps, MessageAuditModal)

---

## Executive Summary

The staging prompt was over-engineered from a simple ~40 line prompt into a 150+ line "7-task monster" that references non-existent MCP tools and violates the two-phase architecture. This handover restores the simple, working pattern while adding proper mode awareness.

---

## The Problem

### What Broke
The `generate_staging_prompt()` method in `src/giljo_mcp/thin_prompt_generator.py` (lines 939-1187) currently:

1. **References non-existent MCP tool** `get_available_agents()` - appears 4 times but doesn't exist in HTTP MCP router
2. **Instructs shell commands** (`ls ~/.claude/agents/*.md`) - violates HTTP-only MCP contract
3. **Mixes execution-phase protocol into staging** - 47-line CLI block with agent behavior instructions
4. **Claims to verify things with no MCP tools** - "Check WebSocket", "Confirm project ID" with no mechanism

### What Was Working (Commit `051addde`)
A simple ~40 line prompt that:
1. Provided identity (orchestrator_id, project_id, tenant_key)
2. Told orchestrator to call `get_orchestrator_instructions()`
3. Let the MCP tool return everything needed (including agent templates!)

---

## The Key Discovery

**`get_orchestrator_instructions()` ALREADY returns active agents from the database!**

From `src/giljo_mcp/tools/tool_accessor.py` lines 593-608:
```python
# Get agent templates
result = await session.execute(
    select(AgentTemplate)
    .where(and_(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active == True))
    .limit(8)
)
templates = result.scalars().all()

template_list = [
    {"name": t.name, "role": t.role, "description": t.description[:200] if t.description else ""}
    for t in templates
]

return {
    ...
    "agent_templates": template_list,  # <-- Active agents from database!
    ...
}
```

The `get_available_agents()` calls in the staging prompt were **completely unnecessary** - the data was already being returned by `get_orchestrator_instructions()`.

---

## Architecture Context

### User Flow (Current)
1. Create Product → Create Project → Activate Project
2. **Launch Tab** (`?tab=launch`): `[Stage Project]` button → copies staging prompt
3. User pastes in terminal → Orchestrator stages project
4. `[Launch Jobs]` button activates
5. **Implement Tab** (`?tab=jobs`): Shows agents, dashboard
6. **Currently**: CLI toggle is HERE (too late!)

### User Flow (After Fix)
1. Create Product → Create Project → Activate Project
2. **Launch Tab**: **Toggle: CLI vs Multi-Terminal** → `[Stage Project]` button
3. Staging prompt is **mode-aware** from the start
4. **Implement Tab**:
   - CLI Mode: Single orchestrator prompt (spawns agents via Task tool)
   - Multi-Terminal: Each agent has [Copy Prompt] button

---

## Implementation Plan

### Phase 1: Move Toggle to Launch Tab (Frontend)

**Files to modify:**
- `frontend/src/components/projects/LaunchTab.vue`
- `frontend/src/components/projects/JobsTab.vue`

**Tasks:**
1. Add execution mode toggle to LaunchTab.vue (before [Stage Project] button)
   - Use Vuetify switch or button group
   - Options: "Claude Code CLI" vs "Multi-Terminal"
   - Default: Multi-Terminal (safer default)
2. Store selection in component state
3. Pass `claude_code_mode` parameter to staging prompt API call
4. Remove toggle from JobsTab.vue (no longer needed there)

**Example Toggle UI:**
```vue
<v-btn-toggle v-model="executionMode" mandatory>
  <v-btn value="multi_terminal">Multi-Terminal</v-btn>
  <v-btn value="claude_code_cli">Claude Code CLI</v-btn>
</v-btn-toggle>
```

### Phase 2: Restore Simple Staging Prompt (Backend)

**File to modify:**
- `src/giljo_mcp/thin_prompt_generator.py`

**Tasks:**
1. Delete the entire 7-task staging prompt (lines 993-1170 approximately)
2. Replace `generate_staging_prompt()` with this simple pattern:

```python
async def generate_staging_prompt(
    self,
    orchestrator_id: str,
    project_id: str,
    claude_code_mode: bool = False
) -> str:
    """
    Generate simple orchestrator staging prompt.

    Restores the working pattern from commit 051addde with mode awareness.
    """
    project = await self._fetch_project(project_id)
    product = await self._fetch_product(project_id)

    if not project or not product:
        raise ValueError(f"Project {project_id} or its product not found")

    # Get MCP server URL
    config = get_config()
    mcp_host = self._get_external_host()
    mcp_port = config.server.api_port
    mcp_url = f"http://{mcp_host}:{mcp_port}"

    execution_mode = "Claude Code CLI" if claude_code_mode else "Multi-Terminal"

    # Mode-specific instructions
    if claude_code_mode:
        mode_block = """CLAUDE CODE CLI MODE:
- You will spawn agents using Claude Code's Task tool
- agent_type parameter = subagent_type (MUST match template name exactly)
- Agents are hidden subprocesses - user sees progress via dashboard
- After spawning, agents call get_agent_mission() to start work"""
    else:
        mode_block = """MULTI-TERMINAL MODE:
- User will manually copy/paste prompts for each agent
- Each agent has [Copy Prompt] button in the Implementation tab
- Coordinate agents via MCP messaging tools"""

    prompt = f"""I am Orchestrator for GiljoAI Project "{project.name}".

IDENTITY:
- Orchestrator ID: {orchestrator_id}
- Project ID: {project_id}
- Tenant Key: {self.tenant_key}
- Execution Mode: {execution_mode}

MCP CONNECTION:
- Server URL: {mcp_url}
- Tool Prefix: mcp__giljo-mcp__

YOUR ROLE: PROJECT STAGING (NOT EXECUTION)
You are STAGING the project. Your job:
1) Analyze requirements
2) Create mission plan
3) Assign work to specialist agents

STARTUP SEQUENCE:
1. Verify MCP: health_check()
2. Fetch context: get_orchestrator_instructions('{orchestrator_id}', '{self.tenant_key}')
   Returns: Project description, Product context, AVAILABLE AGENT TEMPLATES
3. CREATE MISSION: Analyze requirements and generate execution plan
4. PERSIST MISSION: update_project_mission('{project_id}', your_mission)
5. SPAWN AGENTS: spawn_agent_job() for each specialist
   CRITICAL: agent_type MUST exactly match template name from Step 2
   agent_name can be descriptive (for UI display only)

{mode_block}

Begin by calling health_check(), then get_orchestrator_instructions().
"""

    return prompt
```

### Phase 3: Update Implement Tab Based on Mode (Frontend)

**File to modify:**
- `frontend/src/components/projects/JobsTab.vue`

**Tasks:**
1. Read `execution_mode` from project data (already stored by staging)
2. CLI Mode display:
   - Show single "Copy Orchestrator Prompt" button
   - Show agent jobs table (read-only status view)
3. Multi-Terminal Mode display:
   - Show "Copy Prompt" button for EACH agent
   - Existing behavior preserved

### Phase 4: Add Supersedes Notes to Old Handovers

**Files to modify:**
- `handovers/0260_claude_code_cli_mode.md`
- `handovers/0261_claude_code_cli_implementation_prompt.md`

**Add to top of each file:**
```markdown
> **Note**: Staging prompt aspects of this handover are superseded by Handover 0333.
> Backend execution mode toggle and 0262 protocol remain valid.
```

---

## What NOT to Change

These components are working correctly - DO NOT MODIFY:

| Component | Location | Why It Works |
|-----------|----------|--------------|
| `get_agent_mission()` atomic start | `orchestration_service.py` | 0262 protocol - first call sets mission_acknowledged_at, transitions waiting→working |
| `report_progress()` TODO mode | `orchestration_service.py` | 0297 - stores steps in job_metadata.todo_steps |
| Steps column | `JobsTab.vue`, `AgentTableView.vue` | 0297 - displays completed/total from steps |
| MessageAuditModal | `MessageAuditModal.vue` | 0331 - message inspection working |
| `get_orchestrator_instructions()` | `tool_accessor.py` | Already returns agent_templates from database |
| WebSocket events | Various | job:mission_acknowledged, agent:status_changed working |

---

## Testing Checklist

### Phase 1 Tests
- [ ] Toggle appears on Launch tab before [Stage Project] button
- [ ] Toggle default is Multi-Terminal
- [ ] Toggle selection persists during session
- [ ] Toggle removed from Implement tab

### Phase 2 Tests
- [ ] Staging prompt is ~50 lines (not 150+)
- [ ] No references to `get_available_agents()`
- [ ] No shell commands (`ls`, etc.)
- [ ] Mode label appears in IDENTITY section
- [ ] Orchestrator successfully calls `get_orchestrator_instructions()`
- [ ] Orchestrator receives `agent_templates` in response

### Phase 3 Tests
- [ ] CLI Mode: Single orchestrator prompt button
- [ ] CLI Mode: Agent jobs visible but no copy buttons
- [ ] Multi-Terminal: Each agent has copy prompt button
- [ ] Mode display matches what was selected at staging

### End-to-End Tests
- [ ] CLI Mode: Orchestrator spawns agents with correct agent_type
- [ ] CLI Mode: Spawned agents successfully call `get_agent_mission()`
- [ ] Multi-Terminal: Each copied prompt works independently
- [ ] Dashboard updates in real-time for both modes

---

## Reference Information

### Key Commits
- **Working simple prompt**: `051addde` - 292-line file, ~40 line prompt
- **When over-engineering began**: `b9572420` - 0246a added 7-task workflow
- **When it broke for CLI**: `c3b5c1b8` - 0260 added CLI block to staging

### Available HTTP MCP Tools (for reference)
```
health_check, get_orchestrator_instructions, update_project_mission,
spawn_agent_job, get_agent_mission, acknowledge_job, complete_job,
report_progress, report_error, send_message, receive_messages,
list_messages, get_next_instruction, get_workflow_status
```

**NOT available** (do not reference in prompts):
- `get_available_agents` - DOES NOT EXIST
- WebSocket health check - DOES NOT EXIST

---

## Related Handovers

- **0260**: Claude Code CLI Mode Toggle (superseded for staging, backend valid)
- **0261**: CLI Implementation Prompt (superseded for staging)
- **0262**: Agent Mission Protocol (PRESERVED - atomic get_agent_mission)
- **0297**: Steps/TODO Progress Tracking (PRESERVED)
- **0331**: Message Audit Modal (PRESERVED)
- **0332**: Agent Staging & Execution Overview (reference architecture)

---

## Success Criteria

1. Toggle appears on Launch tab (before staging)
2. Staging prompt is ~50 lines (not 150+)
3. Orchestrator successfully reads `agent_templates` from `get_orchestrator_instructions()`
4. Orchestrator spawns agents with exact template names as `agent_type`
5. CLI mode: Single orchestrator prompt, agents spawned via Task tool
6. Multi-terminal mode: Each agent has copy prompt button
7. All 0262/0297/0331 functionality continues working
