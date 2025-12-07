# Handover 0260: Claude Code CLI Toggle Enhancement

**Date:** 2025-12-07
**From Agent:** Documentation Manager (Planning Session)
**To Agent:** TDD Implementor + Backend Integration Tester
**Priority:** High
**Estimated Complexity:** 2-3 days
**Status:** Ready for Implementation

---

## Task Summary

Enhance the "Enable Claude Code CLI" toggle to persist per-project in the database, consolidate duplicate launch button logic into a single source of truth, and generate **mode-specific orchestrator prompts** that enforce strict Task tool agent naming in Claude Code CLI mode.

**Expected Outcome:** Toggle state survives page refresh, orchestrator receives execution mode-specific instructions, and agent naming is strictly enforced in CLI mode.

---

## Context and Background

### Current Issues
1. **Toggle is UI-only** - `ref(false)` at `JobsTab.vue:372` resets on page refresh
2. **No backend persistence** - Toggle state not stored in database
3. **3 duplicate functions** performing identical logic across components:
   - `JobsTab.vue:shouldShowCopyButton()` (lines 577-590)
   - `actionConfig.js:shouldShowLaunchAction()` (lines 108-116)
   - `AgentTableView.vue:canLaunchAgent()` (lines 208-227)
4. **No mode awareness** - Staging endpoint doesn't receive `execution_mode` parameter
5. **Agent naming problem** - Orchestrator invents extended names instead of exact template filenames

### Desired Behavior (from Vision Slides 24-37)
- **Claude Code CLI Mode (ON)**: Strict Task tool instructions, exact `.claude/agents/*.md` template names, only orchestrator gets launch button
- **Multi-Terminal Mode (OFF)**: All agents get prompts with copy buttons, more lenient orchestrator coordination

### CLI Subagent MCP Protocol (v1 Decision – See 0262)
To keep hidden Claude Code CLI subagents predictable and thin, we are standardizing on the following protocol (formalized in **0262_agent_mission_protocol_merge_analysis.md**):

- Subagents MUST:
  - Optionally call `health_check()` to verify MCP connectivity.
  - Then call `get_agent_mission(agent_job_id, tenant_key)` as their **first MCP tool call**.
- The first successful `get_agent_mission` for a waiting job will:
  - Set `mission_acknowledged_at`,
  - Transition status from `waiting` → `working` (if applicable),
  - Emit `job:mission_acknowledged` and `agent:status_changed` WebSocket events for the dashboard.
- Subsequent `get_agent_mission` calls are idempotent mission re-reads and MUST NOT change status or timestamps.
- `acknowledge_job(job_id, agent_id, tenant_key)` is reserved for:
  - Queue/worker flows (`get_pending_jobs` → `acknowledge_job` → `get_agent_mission`), and
  - Admin/HTTP actions that explicitly “claim” a job.
  It is **not required** in the standard Claude Code CLI subagent protocol and SHOULD NOT be used by CLI subagents for normal startup.
- During execution, subagents coordinate and report via:
  - `send_message(...)` / `receive_messages(...)` and `get_next_instruction(job_id, agent_type, tenant_key)` for message-based instructions,
  - `complete_job(job_id, result)` when done, or `report_error(job_id, error)` if blocked,
  - `report_progress(job_id, progress)` for both narrative updates and **TODO-style Steps** using:
    - `progress = {"mode": "todo", "total_steps": N, "completed_steps": k, "current_step": "short description"}` for the numeric Steps indicator on the dashboard,
    - `progress = {"status": "in_progress", "message": "..."}` for coarse-grained narrative progress.
- For plan and narrative content, subagents should use:
  - `send_message(..., message_type="plan")` for plan/TODO content,
  - `send_message(..., message_type="progress")` for narrative/log-style updates.

The implementation tasks in this handover (toggle persistence, prompt generation, tool catalog wiring) should respect this protocol when designing mode-specific prompts and tests.

---

## Technical Details

### Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `frontend/src/utils/actionConfig.js` | Keep | Already has correct `shouldShowLaunchAction()` logic |
| `frontend/src/components/projects/JobsTab.vue` | 372, 577-590 | Remove duplicate, persist toggle via API |
| `frontend/src/components/orchestration/AgentTableView.vue` | 208-227 | Remove `canLaunchAgent()`, use `actionConfig.js` |
| `src/giljo_mcp/models/projects.py` | ~100 | Add `execution_mode` column (after `closeout_checklist`) |
| `api/schemas/project.py` | TBD | Add field to `ProjectResponse`, `ProjectUpdate` |
| `api/endpoints/projects.py` | TBD | Handle toggle updates in project update endpoint |
| `api/endpoints/prompts.py` | 393-396 | Add `execution_mode` query parameter |
| `src/giljo_mcp/thin_prompt_generator.py` | 111, 940+ | Mode-specific staging prompt generation |
| `src/giljo_mcp/tools/orchestration.py` | 1405+ | Add `agent_spawning_constraint` to MCP response |
| `alembic/versions/` | NEW | Migration: `add_execution_mode_to_project.py` |

### Database Schema Addition

```python
# src/giljo_mcp/models/projects.py (line ~100, after closeout_checklist)
execution_mode = Column(String(20), nullable=False, default='multi_terminal')
# Values: 'claude_code_cli' or 'multi_terminal'
```

---

## Implementation Plan

### Phase 1: Consolidate Duplicate Functions
**Goal:** Single source of truth for launch button logic

**Actions:**
- Keep `actionConfig.js:shouldShowLaunchAction(job, claudeCodeCliMode)` as canonical implementation
- Remove `JobsTab.vue:shouldShowCopyButton()` (lines 577-590)
- Remove `AgentTableView.vue:canLaunchAgent()` (lines 208-227)
- Update both components to import from `actionConfig.js`

**Testing:** Unit tests for `actionConfig.js` function, verify components use shared logic

---

### Phase 2: Backend Persistence
**Goal:** Store toggle state per-project in database

**Actions:**
- Add `execution_mode` column to `src/giljo_mcp/models/projects.py`
- Create Alembic migration with default value `'multi_terminal'` (preserves existing behavior)
- Add field to `api/schemas/project.py` (ProjectResponse, ProjectUpdate)
- Update `api/endpoints/projects.py` to handle toggle updates

**Testing:** Integration tests for project update endpoint, verify persistence across page refresh

---

### Phase 3: Frontend Toggle Persistence
**Goal:** Load saved state, persist changes via API

**Actions:**
- Replace `ref(false)` at `JobsTab.vue:372` with computed property from project data
- Update `toggleExecutionMode()` (lines 556-565) to call API and emit WebSocket event
- Bind toggle to reactive `project.execution_mode` from store/composable

**Testing:** E2E test verifying toggle state survives page refresh

---

### Phase 4: Mode-Specific Prompt Generation (CRITICAL)
**Goal:** Orchestrator receives strict Task tool instructions in CLI mode

**Current Flow:**
1. `api/endpoints/prompts.py:393` - Staging endpoint
2. `src/giljo_mcp/thin_prompt_generator.py:111` - `generate()` method
3. `src/giljo_mcp/thin_prompt_generator.py:940` - `generate_staging_prompt()` (7-task workflow)

**Actions:**
- Add `execution_mode` query parameter to staging endpoint (`api/endpoints/prompts.py:393`)
- Add `execution_mode` parameter to `ThinClientPromptGenerator.generate()` signature (line 111)
- Insert mode-specific instructions in staging prompt after Task 4 (agent discovery)

**Claude Code CLI Mode Instructions** (insert at line ~1045):
```markdown
## CLAUDE CODE CLI MODE - STRICT TASK TOOL REQUIREMENTS

CRITICAL: You are running in Claude Code CLI single-terminal mode.
You MUST spawn agents using Claude Code's native Task tool.

### EXACT AGENT NAMING (NO EXCEPTIONS)
When spawning via Task tool, use subagent_type parameter with EXACT template names:
- ALLOWED: subagent_type="backend-tester" (matches backend-tester.md)
- FORBIDDEN: subagent_type="backend-tester-for-api-validation"
- FORBIDDEN: subagent_type="Backend Tester Agent"

Available agents (from get_available_agents):
{agent_list_here}

You may ONLY spawn agents from this list. DO NOT invent, extend, or modify names.

### AGENT SPAWNING RULES (CRITICAL)
When calling spawn_agent_job(), you MUST follow these rules:

1. **agent_type parameter**: MUST be EXACTLY one of the template names from agent_templates list
   - ALLOWED: `agent_type="implementer"` (matches template name)
   - FORBIDDEN: `agent_type="folder-structure-implementer"` (invented name)

2. **agent_name parameter**: Can be descriptive for UI display
   - ALLOWED: `agent_name="Folder Structure Implementer"` (human-readable label)

3. **Available agent_type values**: Listed in agent_templates from get_orchestrator_instructions()

If you need multiple agents of same type:
```
spawn_agent_job(agent_type="implementer", agent_name="Folder Structure Implementer", ...)
spawn_agent_job(agent_type="implementer", agent_name="README Writer", ...)
```

The `agent_type` is used by Claude Code Task tool. The `agent_name` is for human display only.

### AGENT BEHAVIOR REQUIREMENTS
Each spawned agent MUST:
1. Call `get_agent_mission(job_id, tenant_key)` immediately on start (for CLI subagents this both **acknowledges** and **fetches** the mission, and triggers UI signaling as defined in 0262).
2. Use `send_message(...)` and `get_next_instruction(job_id, agent_type, tenant_key)` to communicate and read instructions between major steps.
3. Optionally call `report_progress(job_id, progress)` at major milestones (coarse-grained), when additional structured progress is useful beyond messages.
4. Call `complete_job(job_id, result)` or `report_error(job_id, error)` when finished or blocked so that status and timestamps are updated for the dashboard and audit trail.
```

**Multi-Terminal Mode** (default - existing behavior):
```markdown
## MULTI-TERMINAL MODE

User will manually launch each agent in separate terminal windows.
Each agent has [Copy Prompt] button enabled in the UI.
Coordinate via MCP messaging: send_message(), broadcast(), get_messages()
```

**Testing:** Unit tests for prompt content based on mode, integration test verifying orchestrator receives correct instructions

---

### Phase 5: Agent Name Enforcement (Two Parts - Belt and Suspenders)

#### Phase 5a: Constraint in `get_orchestrator_instructions`
**Goal:** Add explicit spawning constraint to MCP response when in CLI mode

**File:** `src/giljo_mcp/tools/orchestration.py:1405-1550+`

**Logic to Add:**
When `execution_mode='claude_code_cli'`, add constraint to MCP response:
```python
if execution_mode == 'claude_code_cli':
    result['agent_spawning_constraint'] = {
        'mode': 'strict_task_tool',
        'allowed_agent_types': [t['name'] for t in agent_templates],
        'instruction': 'You MUST use Task tool with exact subagent_type names from this list.'
    }
```

**Testing:** Unit test verifying constraint appears in MCP response when mode is `claude_code_cli`

---

#### Phase 5b: Validation in `spawn_agent_job`
**Goal:** Reject invalid `agent_type` values at spawn time

**File:** `src/giljo_mcp/tools/orchestration.py` - `spawn_agent_job` function

**Validation Logic to Add:**
```python
available_templates = get_available_agents(tenant_key, active_only=True)
valid_agent_types = [t['name'] for t in available_templates]

if agent_type not in valid_agent_types:
    return {
        "success": False,
        "error": f"Invalid agent_type '{agent_type}'. Must be one of: {valid_agent_types}",
        "hint": "Use agent_name for descriptive labels, agent_type must match template exactly"
    }
```

**Testing:** Integration test verifying rejection of invalid agent types, acceptance of valid types

**Combined Outcome:** Belt-and-suspenders enforcement - prompt instructs + MCP validates

---

## Testing Requirements

### Unit Tests
- `actionConfig.js:shouldShowLaunchAction()` - All edge cases (orchestrator, specialists, both modes)
- `ThinClientPromptGenerator` - Mode-specific prompt content verification
- `get_orchestrator_instructions()` - Spawning constraint structure when in CLI mode

### Integration Tests
- Toggle persistence: Change mode → refresh page → verify state preserved
- Project update API: PATCH request updates `execution_mode` correctly
- Staging endpoint: Query parameter `execution_mode` affects prompt output
- WebSocket events: Toggle change emits `project:updated` event

### E2E Tests
1. Claude Code CLI mode: Only orchestrator has launch button, others have copy buttons
2. Multi-terminal mode: All agents have launch buttons
3. Prompt verification: CLI mode prompt contains strict naming instructions
4. Agent spawning: Orchestrator in CLI mode receives agent constraint in MCP response

---

## Dependencies and Blockers

### Dependencies
- None blocking implementation

---

## Success Criteria

1. ✅ Toggle state persists per-project in database
2. ✅ Single source of truth for launch button logic in `actionConfig.js`
3. ✅ Claude Code CLI mode prompt contains strict Task tool instructions with exact agent names
4. ✅ `get_orchestrator_instructions()` returns `agent_spawning_constraint` when in CLI mode
5. ✅ Multi-terminal mode works as before (all agents get prompts)
6. ✅ Agent names in prompt exactly match `/.claude/agents/*.md` templates
7. ✅ `spawn_agent_job` validates `agent_type` against available templates
8. ✅ `agent_name` displayed in UI as human-readable label
9. ✅ All tests passing (>80% coverage)
10. ✅ No regressions in existing functionality

---

## Rollback Plan

### If Database Migration Fails
- Default value `'multi_terminal'` preserves existing behavior
- Can rollback migration: `alembic downgrade -1`

### If Staging Endpoint Breaks
- Parameter is optional, defaults to `'multi_terminal'`
- Existing API clients unaffected

### If Frontend State Desync Occurs
- WebSocket event emission ensures real-time sync
- Page refresh loads from database (source of truth)

### If Claude Ignores Naming Instructions
- Explicit "FORBIDDEN" examples in prompt
- "ONLY" constraint language
- MCP response includes machine-readable constraint
- Can revert to multi-terminal mode per-project

---

## Execution Order

1. **Database first:** Add column + migration (Phase 2)
2. **Backend API:** Schemas, endpoints (Phase 2 cont'd)
3. **Consolidation:** Remove duplicates, use `actionConfig.js` (Phase 1)
4. **Frontend persistence:** Toggle binding (Phase 3)
5. **Prompt generation:** Mode-specific templates (Phase 4)
6. **MCP tool enhancement:** Add constraint (Phase 5)
7. **Testing:** Unit, integration, E2E (all phases)

---

## Additional Resources

### Related Documentation
- Vision Slides 24-37: Claude Code CLI vs Multi-Terminal mode comparison
- `docs/ORCHESTRATOR.md` - Orchestrator workflow and prompt generation
- `docs/components/STAGING_WORKFLOW.md` - 7-task staging workflow details
- `docs/SERVICES.md` - Service layer patterns and multi-tenant isolation

### Related Files
- `frontend/src/utils/actionConfig.js` - Action availability configuration (keep this)
- `src/giljo_mcp/thin_prompt_generator.py` - Thin client prompt generator (v3.1+)
- `src/giljo_mcp/tools/orchestration.py` - MCP orchestration tools

### Implementation References
- Handover 0246a-c: Orchestrator workflow series (staging, discovery, spawning)
- Handover 0243: GUI redesign series (action buttons, status indicators)

---

## Agent Naming Strategy (RESOLVED)

**Decision Made:** Two-parameter approach in `spawn_agent_job`:

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `agent_type` | MUST match template name exactly (for Task tool) | `"implementer"` |
| `agent_name` | Descriptive label for UI display | `"Folder Structure Implementer"` |

**Example - Spawning 2 implementers:**
```python
spawn_agent_job(agent_type="implementer", agent_name="Folder Structure Implementer", ...)
spawn_agent_job(agent_type="implementer", agent_name="README Writer", ...)
```

**Validation in `spawn_agent_job`** (Phase 5b):
```python
available_templates = get_available_agents(tenant_key, active_only=True)
valid_agent_types = [t['name'] for t in available_templates]

if agent_type not in valid_agent_types:
    return {
        "success": False,
        "error": f"Invalid agent_type '{agent_type}'. Must be one of: {valid_agent_types}",
        "hint": "Use agent_name for descriptive labels, agent_type must match template exactly"
    }
```

**Files Affected:**
- `src/giljo_mcp/thin_prompt_generator.py` - Add AGENT SPAWNING RULES to prompt (Phase 4)
- `src/giljo_mcp/tools/orchestration.py` - Add validation to `spawn_agent_job` (Phase 5b)
- `src/giljo_mcp/tools/orchestration.py` - Add constraint to `get_orchestrator_instructions` (Phase 5a)

---

## Progress Updates

### 2025-12-07 - Documentation Manager (Initial Creation)
**Status:** Handover document created
**Work Done:**
- Analyzed plan from `twinkling-greeting-avalanche.md`
- Created structured handover following project template
- Documented 5-phase implementation approach
- Identified all affected files with line numbers
- Defined comprehensive testing requirements

**Next Steps:**
- TDD Implementor to execute phases 1-5 with test-first approach
- Backend Integration Tester to verify E2E workflows
- Update this document with implementation progress

---

### 2025-12-07 - Planning Session (Agent Naming Resolution)
**Status:** Agent naming decision RESOLVED
**Decision Made:**
- `agent_type` = MUST match template name exactly (for Task tool)
- `agent_name` = Can be descriptive (for UI display)
- Validation added to `spawn_agent_job` MCP tool
- Applies to Claude Code CLI mode only (other modes use multi-terminal)

**Documentation Updates:**
- Added "Agent Spawning Rules" section to Phase 4 Claude Code CLI instructions
- Updated Phase 5 with validation logic for `spawn_agent_job`
- Removed "Deferred Decisions" section - no longer deferred
- Updated success criteria to include agent naming validation

---

### 2025-12-07 - Documentation Manager (Plan File Synchronization)
**Status:** Handover fully synchronized with plan file
**Work Done:**
- Split Phase 5 into two distinct parts (5a: constraint in MCP response, 5b: validation in spawn_agent_job)
- Added prominent "Agent Naming Strategy" section with clear examples
- Updated acceptance criteria to match plan file order exactly
- Verified belt-and-suspenders enforcement approach documented
- Confirmed all code examples from plan file included

**Changes Made:**
1. Phase 5 now clearly shows TWO parts with separate testing requirements
2. Agent naming strategy promoted from progress update to dedicated section
3. Acceptance criteria expanded from 9 to 10 items matching plan file
4. Added this progress update entry to track synchronization work

**Next Steps:**
- TDD Implementor to execute phases 1-5 with test-first approach
- Backend Integration Tester to verify E2E workflows
