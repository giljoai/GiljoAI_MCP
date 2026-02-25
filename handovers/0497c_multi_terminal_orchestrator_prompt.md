# Handover 0497c: Multi-Terminal Orchestrator Implementation Prompt

**Date:** 2026-02-25
**From Agent:** Research/Architecture Session
**To Agent:** system-architect + tdd-implementor
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Not Started
**Chain:** 0497a → 0497b → **0497c** → 0497d → 0497e (Multi-Terminal Production Parity)
**Depends On:** 0497a (thin prompt endpoint must work)

## Task Summary

In CLI mode, the orchestrator gets a dedicated implementation prompt via `GET /api/v1/prompts/implementation/{project_id}` (built by `_build_claude_code_execution_prompt()`). Multi-terminal mode has NO equivalent — the orchestrator play button was a dead end showing a toast. Build a `_build_multi_terminal_orchestrator_prompt()` that tells the orchestrator its post-staging role: reactive coordinator in its own terminal, monitoring when asked, handling messages, and closing out the project when all agents finish.

## Context and Background

### CLI Mode (Reference Implementation)
The implementation endpoint (`api/endpoints/prompts.py:465`, function `get_implementation_prompt()`) calls `ThinClientPromptGenerator._build_claude_code_execution_prompt()` which returns a 7-section prompt:
1. Context Recap (identity, health check, fetch stored plan)
2. Agent Jobs List (all spawned agents with job_ids)
3. Task Tool Spawning Template (Task() syntax with concrete examples)
4. Monitoring Instructions (get_workflow_status, handle blockers, messaging)
5. Context Refresh (re-read orchestrator mission)
6. CLI Mode Constraints (template files, naming rules)
7. Completion (verify all agents, git closeout, complete_job)

### Multi-Terminal Mode (What We Need)
The orchestrator in multi-terminal mode has a fundamentally different role:
- It does NOT spawn agents via Task() — the user does that manually via play buttons
- It IS reactive — the user asks it to check status, relay messages, coordinate
- The MCP server is passive over HTTP — no polling loops, no bash sleep
- It should announce itself as ready and wait for user commands
- It should know its team (agent names, IDs, roles) for coordination
- It should guide the user through closeout when all agents complete

### Architecture Decision: Separate Prompt Builder
**DO NOT modify `get_orchestrator_instructions()`** — it's been extensively tuned for CLI mode staging and must not be impacted. Instead, build a parallel `_build_multi_terminal_orchestrator_prompt()` in `ThinClientPromptGenerator`, mirroring how CLI mode has its own `_build_claude_code_execution_prompt()`.

### Git References
- CLI implementation prompt: Search `_build_claude_code_execution_prompt` in `src/giljo_mcp/thin_prompt_generator.py` (line ~1202)
- Implementation endpoint: `api/endpoints/prompts.py:465` function `get_implementation_prompt()`
- Frontend play button: `frontend/src/components/projects/JobsTab.vue:828-862`
- Bandaid commit: `e79291ec` (orchestrator falls through to generic agentPrompt)

## Technical Details

### Files to Modify

**`src/giljo_mcp/thin_prompt_generator.py`** — New method:

**Signature design decision:** The existing `_build_claude_code_execution_prompt()` uses simple/untyped parameters:
```python
def _build_claude_code_execution_prompt(
    self, orchestrator_id: str, project, agent_jobs: list, git_enabled: bool = False
) -> str:
```
The caller at `get_implementation_prompt()` (line 623-627) unwraps ORM objects before passing them. For consistency, **match the existing pattern** (simple types). If you prefer typed ORM objects, that's a valid improvement but should apply to both methods in a separate refactor.

Recommended signature (matching existing pattern):
```python
def _build_multi_terminal_orchestrator_prompt(
    self,
    orchestrator_id: str,
    project,
    agent_jobs: list,
    git_enabled: bool = False,
) -> str:
```

Prompt sections (modeled after CLI mode's 7 sections):

**Section 1 — Identity & Context Recap:**
- "You are the ORCHESTRATOR for project {name}"
- Your Agent ID, Job ID, Project ID
- "You completed staging. Your team is now running in separate terminals."
- Health check mandate: `mcp__giljo-mcp__health_check()`

**Section 2 — Your Team:**
- Table of all spawned agents: agent_display_name, agent_id (UUID), role/agent_name, status
- "These agents are running independently. They may message you."

**Section 3 — Your Role (Reactive Coordinator):**
- "You are idle by default. Tell the user: 'I am launched and ready to support the team. Ask me to check agent status, relay messages, or coordinate when needed.'"
- "Do NOT poll or loop. The MCP server is passive — you act when the user asks."
- Available MCP tools with exact call syntax:
  - `get_workflow_status(project_id)` — check all agent statuses
  - `receive_messages(agent_id, tenant_key)` — check your inbox
  - `send_message(to_agents, content, from_agent, project_id)` — relay guidance
  - `report_progress(job_id, tenant_key, todo_items)` — update your own progress
  - `get_orchestrator_instructions(job_id)` — re-read your own mission for context refresh (matches CLI prompt Section 5)

**Section 4 — Handling Agent Issues:**
- "If a tester or agent reports problems, you can spawn a fresh agent via `spawn_agent_job()`"
- "The new agent appears on the dashboard. Tell the user to copy its prompt into a NEW terminal (fresh context is better than context fog)."
- "The new agent should read the predecessor's completion result and git commits to understand prior work."

**Section 5 — Project Closeout:**
- "When all agents show status 'complete' (check via `get_workflow_status`):"
  1. Call `receive_messages()` to process any final reports
  2. Call `write_360_memory()` to preserve project knowledge
  3. Call `complete_job()` to mark yourself complete
  4. Tell the user: "Project is complete. Use /gil_add to save follow-up projects or technical debt tasks."

**`api/endpoints/prompts.py`** — Modify `get_implementation_prompt()`:
- Currently gated to CLI mode only (line ~527: validates `execution_mode == "claude_code_cli"`, returns 400 for other modes)
- Make it mode-aware: if `multi_terminal`, call `_build_multi_terminal_orchestrator_prompt()` instead
- Keep CLI mode path completely untouched

**`frontend/src/components/projects/JobsTab.vue`** — Modify `handlePlay()`:
- The orchestrator branch (line 831) currently has two paths: CLI mode calls implementation endpoint, multi-terminal falls through to generic agentPrompt
- Change multi-terminal path to also call `api.prompts.implementation(projectId)` (same as CLI)
- Add `api.projects.launchImplementation(projectId)` call before prompt fetch (opens the phase gate for agents)
- This means clicking the orchestrator play button in multi-terminal mode: opens gate + copies orchestrator prompt

### Frontend Flow After Fix
```
User clicks orchestrator play button (multi-terminal mode):
  1. Calls PATCH /launch-implementation (opens phase gate)
  2. Calls GET /implementation/{project_id} (returns multi-terminal orchestrator prompt)
  3. Copies to clipboard
  4. Shows success toast
  → Agent play buttons now work (gate is open)
  → User pastes orchestrator prompt into terminal
  → Orchestrator announces "I am ready"
```

## Implementation Plan

### Phase 1: Write Tests (TDD)
1. Test `_build_multi_terminal_orchestrator_prompt()` contains team roster
2. Test prompt contains reactive coordinator instructions (not polling)
3. Test prompt contains MCP tool call syntax for monitoring
4. Test prompt contains closeout instructions
5. Test `get_implementation_prompt()` returns multi-terminal prompt when mode is `multi_terminal`
6. Test `get_implementation_prompt()` still returns CLI prompt when mode is `claude_code_cli` (regression)

### Phase 2: Build Prompt Builder
1. Implement `_build_multi_terminal_orchestrator_prompt()` in ThinClientPromptGenerator
2. Follow the 5-section structure above
3. Token budget: the CLI implementation prompt is ~1400-1500 tokens across 272 lines. The multi-terminal variant should be shorter (5 sections vs 7, no Task spawning template, no CLI constraints). Aim for ~800-1200 tokens, which is achievable given fewer sections.

### Phase 3: Wire Endpoint
1. Modify `get_implementation_prompt()` to branch on execution_mode
2. Multi-terminal path: query orchestrator + all agent executions, call new builder
3. CLI path: untouched

### Phase 4: Wire Frontend
1. Orchestrator play button in multi-terminal mode calls implementation endpoint
2. Includes `launchImplementation()` call to open phase gate
3. Success toast on copy

**Recommended Sub-Agents:** system-architect (prompt design), tdd-implementor (implementation)

## Testing Requirements

### Unit Tests
- Prompt builder output format validation
- Mode-aware endpoint routing (CLI vs multi-terminal)
- CLI mode regression (CRITICAL — must not change)

### Integration Tests
- End-to-end: stage project → click orchestrator play → verify prompt → paste in terminal → verify orchestrator calls health_check + announces ready

### Manual Testing
1. Create project in multi-terminal mode
2. Stage it (orchestrator spawns agents)
3. Go to Jobs tab
4. Click orchestrator play button
5. Verify clipboard contains multi-terminal orchestrator prompt
6. Paste into terminal — verify orchestrator announces itself
7. Click specialist agent play buttons — verify they work (gate is open)

## Dependencies and Blockers
- **Depends on 0497a**: The specialist agent play buttons must return thin prompts
- **Does NOT depend on 0497b**: Completion results are enhancement, not required for orchestrator prompt
- **Deployment ordering**: The backend endpoint change (removing the 400 gate) MUST deploy before the frontend change (calling implementation endpoint for multi-terminal). Otherwise, the multi-terminal play button hits a 400 error instead of falling through to agentPrompt.
- **`git_enabled` consideration**: The existing CLI prompt has git closeout logic gated by `git_enabled` (derived from product config + user field priorities, lines 604-619 of `get_implementation_prompt`). Consider including git closeout guidance in the multi-terminal variant too.

## Success Criteria
- Multi-terminal orchestrator gets a dedicated implementation prompt
- CLI mode is completely unaffected (regression tests pass)
- Orchestrator announces "ready" when launched and waits for user
- Phase gate opens when orchestrator play button is clicked
- All agent play buttons work after orchestrator is launched

## Rollback Plan
- `git revert` — orchestrator falls back to generic agentPrompt (functional but not role-appropriate)
- CLI mode is untouched throughout, zero rollback risk there

## Cascading Analysis
- **Downstream**: No model changes
- **Upstream**: No model changes
- **Sibling**: CLI mode implementation prompt is untouched (separate code path)
- **Installation**: No `install.py` changes needed
