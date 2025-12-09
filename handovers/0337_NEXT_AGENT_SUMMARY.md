# Next Agent Summary: Handover 0337 Implementation

**Date**: 2025-12-09
**Previous Session**: Completed 0336 (bug fixes), documented 0337 (implementation prompt)
**Your Task**: Implement the CLI Mode Implementation Prompt feature

---

## Context

The Claude Code CLI mode has a **two-stage workflow**:

1. **Stage 1 - Staging** (🚀 Launch Tab): User copies staging prompt → Orchestrator plans and spawns agent jobs (status: "waiting")

2. **Stage 2 - Implementation** ({} IMPLEMENT Tab): User clicks play `(>)` button on orchestrator card → **THIS IS BROKEN** - currently shows toast "Use Launch tab" instead of copying implementation prompt

---

## What You Need to Implement

### Task 1: Create API Endpoint
**File**: `api/endpoints/prompts.py`

Create `GET /api/prompts/implementation/{project_id}` that:
- Validates project is in CLI mode (`execution_mode='claude_code_cli'`)
- Fetches orchestrator job and spawned agent jobs
- Calls `generator._build_claude_code_execution_prompt()` (method EXISTS but unused)
- Returns implementation prompt for clipboard

### Task 2: Update JobsTab.vue
**File**: `frontend/src/components/projects/JobsTab.vue`

Replace toast (lines ~591-601) with API call:
```javascript
if (project.execution_mode === 'claude_code_cli' && agent.agent_type === 'orchestrator') {
    const response = await api.get(`/api/prompts/implementation/${project.id}`)
    await navigator.clipboard.writeText(response.data.prompt)
    showSnackbar('Implementation prompt copied')
}
```

### Task 3: Verify Prompt Content
**File**: `src/giljo_mcp/thin_prompt_generator.py`

The `_build_claude_code_execution_prompt()` method (lines 1147-1207) should include:
- Orchestrator identity (IDs, tenant_key)
- Context recap ("You have PREVIOUSLY created mission, spawned agents...")
- Agent jobs table (agent_name, agent_type, job_id)
- Task tool spawning instructions with exact `subagent_type` enforcement
- Instructions for agents to call `get_agent_mission(job_id, tenant_key)`

---

## Key Architecture Points

1. **Fresh Session Assumption**: Implementation prompt must be self-contained (user may have closed terminal)

2. **Agent Type Enforcement**: `Task(subagent_type="implementer")` MUST match `.claude/agents/implementer.md` filename

3. **Agent States**: `waiting` → `working` (via get_agent_mission) → `completed`/`failed`/`blocked`

4. **Play Button `(>)`**: This is the copy prompt button on agent cards in Jobs tab

---

## Files Reference

| File | Purpose |
|------|---------|
| `handovers/0337_CLI_MODE_IMPLEMENTATION_PROMPT.md` | Full handover doc (1,110 lines) |
| `handovers/0261_claude_code_cli_implementation_prompt.md` | Original spec (never implemented) |
| `src/giljo_mcp/thin_prompt_generator.py:1147-1207` | `_build_claude_code_execution_prompt()` |
| `api/endpoints/prompts.py` | Where to add new endpoint |
| `frontend/src/components/projects/JobsTab.vue:591-601` | Toast to replace |

---

## Testing

After implementation:
1. Create project → Stage it → Verify agent jobs created
2. Toggle CLI mode ON
3. Go to {} IMPLEMENT tab
4. Click play `(>)` on orchestrator card
5. Verify implementation prompt copied (not toast)
6. Paste into Claude Code → Verify Task tool spawning works

---

## Commits from Previous Session

```
19344801 feat(0336-0337): Add integration tests and update implementation prompt handover
f14b5d71 feat: Implement vision_chunking depth configuration
96ad33b3 test: Add tests for vision_chunking depth configuration
62c5e86f docs(0336): Add handover for tech stack encoding and token estimation bugs
```

---

## Estimated Effort

4-6 hours total:
- Task 1 (API endpoint): 2 hours
- Task 2 (Frontend): 1 hour
- Task 3 (Prompt verification): 1 hour
- Testing: 1-2 hours

Good luck!
