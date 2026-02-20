# Handover: Project Continuation Workflow

**Date:** 2026-02-19 (rewritten from 2026-02-05 original)
**From Agent:** Consulting session (Claude Opus 4.6)
**To Agent:** tdd-implementor, ux-designer
**Priority:** High
**Estimated Complexity:** 10-14 hours (4 phases)
**Status:** Ready for Implementation

---

## Task Summary

Enable users to reopen completed projects and run a new staging/implementation cycle with full historical context. The same project is reused (no new project records), and the continuation orchestrator reads all prior 360 Memory entries, the original mission, and completed agent history before planning new work.

**Why it matters:** Currently, when a project completes, users must create an entirely new project to continue work on the same codebase. This fragments history across projects and loses context.

**Expected outcome:** A "Continue Project" button on the staging tab that collects user instructions, generates a continuation staging prompt, and follows the normal staging-to-implementation flow with historical awareness.

---

## Context and Background

**Origin:** Alpha trial testing (2026-02-05/06) revealed that continuation sessions fragment project history. The original 0486 proposed job reactivation, mission versioning, todo extension, and duration timer. After design review (2026-02-19), the scope was redesigned to leverage existing infrastructure.

**Key Design Decisions:**
1. **Reopen same project** (not create new linked project) -- avoids `parent_project_id`/`root_project_id` complexity
2. **360 Memory sequence IS the lineage** -- entry #1 = phase 1, entry #2 = phase 2, etc.
3. **Git history IS the symbiont link** -- continuation orchestrator fetches `git_history` category for repo continuity
4. **Branching is architecturally impossible** -- project must be `completed` to reopen, reopening sets to `inactive`, only one status at a time
5. **No limit on reopens** -- sequential iterations (A phase 1 → A phase 2 → A phase 3) are fine
6. **This is an edge case feature** -- primary workflow remains `/gil_add --project` for new work

**What was DROPPED from original 0486:**

| Original Feature | Why Dropped |
|---|---|
| Job reactivation (`reopen_job()`) | New orchestrator creates new jobs. Clean separation. |
| Mission versioning (`ProjectMissionHistory` table) | 360 Memory IS the version history. |
| Todo list extension (append mode) | New agents get fresh todos. Old todos visible in history. |
| Duration timer (`paused_duration_seconds`) | New agents have their own timers. |

**Reference data:** Alpha project `8caeae86-c0b8-40c0-a0bc-598fffed2b4c` (TinyContacts product) has 7 completed jobs, 58 todo items, 97 messages, and 360 Memory entry #15 -- ideal for integration testing.

---

## Technical Details

### New Database Fields (Project model)

**File:** `src/giljo_mcp/models/projects.py` (Project class, lines 24-147)

Add 3 columns:

```python
# After line 97 (closeout_checklist)
continuation_count = Column(Integer, default=0, server_default="0", nullable=False)
last_reopened_at = Column(DateTime(timezone=True), nullable=True)
continuation_instructions = Column(Text, nullable=True)
```

- `continuation_count`: Incremented on each reopen. Enables "Phase N" display in UI.
- `last_reopened_at`: Timestamp of most recent reopen. UI shows "Reopened Feb 19."
- `continuation_instructions`: User's text explaining what to continue. Read by orchestrator via `get_orchestrator_instructions()`. Cleared after staging completes.

### Modify: `ProjectService.continue_working()`

**File:** `src/giljo_mcp/services/project_service.py` (lines 863-958)

Current behavior: Sets status to `inactive`, clears `completed_at`, resumes decommissioned agents.

**Changes needed:**
1. Accept optional `continuation_instructions: str` parameter
2. Reset `staging_status` to `None` (currently NOT reset -- blocks re-staging)
3. Reset `implementation_launched_at` to `None` (allows fresh implementation gate)
4. Increment `continuation_count`
5. Set `last_reopened_at` to current timestamp
6. Store `continuation_instructions` on the project
7. Do NOT resume old agent executions (remove the decommissioned→waiting logic). Old agents stay completed. New orchestrator spawns fresh agents.

### Modify: API endpoint

**File:** `api/endpoints/projects/completion.py` (lines 201-235)

- Accept optional `continuation_instructions` in request body (currently no body)
- Pass through to `ProjectService.continue_working()`

### New: Continuation Staging Prompt

**File:** `src/giljo_mcp/thin_prompt_generator.py`

Add method `generate_continuation_staging_prompt()` to `ThinClientPromptGenerator` (after `generate_staging_prompt()` at line 1148).

This is a variant of `generate_staging_prompt()` that:
1. Creates a NEW orchestrator job (same as normal staging)
2. Generates a thin prompt (~150 tokens) that includes:
   - Identity block (agent_id, job_id, project_id)
   - "CONTINUATION" label with `continuation_count` phase number
   - User's continuation instructions inline (they're short, keep in prompt)
   - Two MCP calls: `health_check()` then `get_orchestrator_instructions()`

Template:
```
You are the ORCHESTRATOR for project "{project_name}" (PHASE {continuation_count + 1})

YOUR IDENTITY (use these in all MCP calls):
  YOUR Agent ID: {agent_id}
  YOUR Job ID: {orchestrator_id}
  THE Project ID: {project_id}

MCP Server: {mcp_url}
Note: tenant_key is auto-injected by server from your API key session

CONTINUATION CONTEXT:
This project was reopened by the user with these instructions:
---
{continuation_instructions}
---

START NOW:
1. Verify MCP: mcp__giljo-mcp__health_check()
2. Fetch instructions: mcp__giljo-mcp__get_orchestrator_instructions(job_id='{orchestrator_id}')
   -> Includes continuation context with previous mission, 360 Memory history,
      and completed agent summary. Follow the staging protocol.
```

### Modify: Prompts API endpoint (extend existing)

**File:** `api/endpoints/prompts.py` (line 334, `generate_staging_prompt()`)

Extend the existing `GET /api/v1/prompts/staging/{project_id}` endpoint -- do NOT create a separate endpoint. Inside the handler, after fetching the project, check `project.continuation_count > 0`. If true, call `generator.generate_continuation_staging_prompt()` instead of `generator.generate_staging_prompt()`. This keeps the frontend simple (one staging endpoint, backend dispatches).

### Modify: `get_orchestrator_instructions()`

**File:** `src/giljo_mcp/services/orchestration_service.py` (lines 3224-3516)

When the project has `continuation_count > 0`, inject a `continuation_context` section into the response:

```python
# Inside get_orchestrator_instructions(), after building the base response
if project.continuation_count > 0:
    response["continuation_context"] = {
        "phase": project.continuation_count + 1,
        "user_instructions": project.continuation_instructions,
        "previous_mission": project.mission,  # Mission from last phase
        "last_reopened_at": project.last_reopened_at.isoformat(),
        "note": "Read 360 Memory for full project history. Completed agents from previous phases are visible via get_workflow_status()."
    }
    # Override memory_360 to CRITICAL priority for continuations
    # (ensures orchestrator reads project history before planning)
```

Also update `_build_orchestrator_protocol()` (lines 555-964). CH1 ("Your Mission") currently says "You are staging a NEW project." For continuation projects, replace with a continuation-aware variant. Use Serena to read the current CH1 body (`find_symbol` with `_build_orchestrator_protocol`, `include_body=True`) and add a conditional block:

```python
# Inside _build_orchestrator_protocol(), in the CH1 section
if project.continuation_count > 0:
    ch1_text = f"""CONTINUATION PROJECT (Phase {project.continuation_count + 1})
This project has been reopened. Your job is to plan the NEXT phase of work.

CRITICAL FIRST ACTIONS:
1. Call fetch_context(product_id="{product_id}", categories=["memory_360"]) -- MANDATORY
   This contains completion summaries from all previous phases.
2. Call get_workflow_status(project_id="{project_id}") to see completed agents from prior phases.
3. Read the continuation_context in your instructions for user's new requirements.

Then follow the normal staging protocol (Steps 3-7): discover agents, plan mission, spawn agents, broadcast STAGING_COMPLETE.
Do NOT reuse or reactivate old agents. Spawn fresh agents for the new phase.
The previous mission is preserved in your instructions as reference only -- write a NEW mission for this phase."""
```

This keeps the rest of the protocol (CH2-CH5) identical to normal staging.

### Frontend: LaunchTab Continuation Mode

**File:** `frontend/src/components/projects/LaunchTab.vue`

When `project.continuation_count > 0` AND project was just reopened (status is `inactive`, `staging_status` is null):

1. **Panel 1 (Description):** Show original description (already works)
2. **Panel 2 (Mission):** Show previous mission with "Previous Mission (Phase N)" header
3. **Panel 3 (Agents):** Show completed agents from previous run with "Completed" status chips
4. **New element:** Text area below the panels: "What would you like to continue working on?"
   - Bound to `continuationInstructions` ref
   - Placeholder: "Describe what additional work is needed..."

### Frontend: ProjectTabs Button Logic

**File:** `frontend/src/components/projects/ProjectTabs.vue`

When `project.continuation_count > 0` AND `staging_status` is null:
- Rename "Stage Project" button to "Continue Project"
- On click flow (two sequential API calls):
  1. Save continuation instructions: `PATCH /api/v1/projects/{id}` with `{ continuation_instructions: text }` (use existing project update endpoint)
  2. Generate prompt: `GET /api/v1/prompts/staging/{id}` (same endpoint as normal staging -- backend detects continuation and dispatches)
  3. Copy prompt to clipboard (existing `copyPromptToClipboard()` utility)
- After staging completes (STAGING_COMPLETE broadcast detected via `projectStateStore.handleMessageSent()`), the normal "Implement" button flow takes over identically to a fresh project
- The `continuation_instructions` field is cleared by the backend after the orchestrator calls `get_orchestrator_instructions()` (prevents stale instructions on next reopen)

**Reference -- how the existing "Stage Project" button works** (pattern to follow):
1. `ProjectTabs.handleStageProject()` calls `api.prompts.staging(projectId, { tool, execution_mode })`
2. Backend creates orchestrator job + execution, returns prompt
3. Frontend copies prompt to clipboard, shows toast
4. WebSocket `broadcast` message → `projectStateStore.setStagingComplete(true)` → enables "Implement" button

### Frontend: API Service

**File:** `frontend/src/services/api.js`

- No new API methods needed. The existing `api.prompts.staging()` (line 465) handles both fresh and continuation staging (backend dispatches). The existing `api.projects.update()` saves continuation instructions before the staging call.

---

## Cascading Impact Analysis

### Downstream Impact
- **Agent Jobs:** NOT affected. Old jobs remain completed. New orchestrator creates fresh jobs.
- **Agent Executions:** NOT affected. Old executions stay completed. New executions created for new jobs.
- **Agent Todo Items:** NOT affected. Old items stay. New agents get fresh items.
- **Messages:** NOT affected. Old messages remain. New agents send new messages.
- **360 Memory:** ADDITIVE. New completion entry added after phase 2. All entries readable via `fetch_context`.
- **Tasks:** NOT affected. Task binding is to product, not project lifecycle.

### Upstream Impact
- **Product:** NOT affected. Project remains under same product.
- **Organization/User:** NOT affected. Tenant isolation unchanged.

### Sibling Impact
- **Other projects under same product:** NOT affected. Single Active Project constraint is respected (project reopens as `inactive`, must be activated before staging).

### Installation Flow Protection
- **Schema change:** 3 new nullable columns with defaults. Migration is additive, idempotent. `install.py` baseline schema needs updating.
- **Fresh installs:** `continuation_count` defaults to 0, timestamps default to NULL. No impact.
- **Existing data:** All existing projects get `continuation_count=0`, `last_reopened_at=NULL`, `continuation_instructions=NULL`. No migration of existing data needed.
- **First-run flow:** `/welcome` and `/first-login` unaffected. New fields have sensible defaults.

---

## Implementation Plan

### Phase 1: Database + Service Layer (TDD) -- 3-4 hours
**Recommended Agent:** tdd-implementor

1. Write tests for new Project fields (`continuation_count`, `last_reopened_at`, `continuation_instructions`)
2. Add columns to `Project` model
3. Update baseline migration in `install.py`
4. Write tests for enhanced `continue_working()`:
   - Increments `continuation_count`
   - Sets `last_reopened_at`
   - Stores `continuation_instructions`
   - Resets `staging_status` to None
   - Resets `implementation_launched_at` to None
   - Does NOT resume old agent executions
5. Implement the service changes
6. Update API endpoint to accept `continuation_instructions` body
7. Verify all existing `continue_working` tests still pass

### Phase 2: Prompt Generation + Orchestrator Instructions -- 3-4 hours
**Recommended Agent:** tdd-implementor

1. Write tests for `generate_continuation_staging_prompt()`:
   - Prompt includes "PHASE N" label
   - Prompt includes continuation instructions
   - Creates new orchestrator job (not reuses old)
   - Returns valid thin prompt structure
2. Implement `generate_continuation_staging_prompt()` on `ThinClientPromptGenerator`
3. Write tests for `get_orchestrator_instructions()` continuation context:
   - Returns `continuation_context` when `continuation_count > 0`
   - Includes previous mission, user instructions, phase number
   - Does NOT return `continuation_context` for fresh projects
4. Implement continuation detection in `get_orchestrator_instructions()`
5. Update `_build_orchestrator_protocol()` CH1 for continuation awareness
6. Add/extend prompts API endpoint

### Phase 3: Frontend -- 3-4 hours
**Recommended Agent:** ux-designer or tdd-implementor

1. LaunchTab.vue: Add continuation mode detection
2. LaunchTab.vue: Text area for continuation instructions
3. LaunchTab.vue: "Previous Mission" display with phase label
4. LaunchTab.vue: Completed agents display from prior phases
5. ProjectTabs.vue: "Continue Project" button variant
6. ProjectTabs.vue: Wire button to continuation staging flow
7. api.js: Update `restoreCompleted()` and add continuation staging call

### Phase 4: Integration Testing -- 2-3 hours
**Recommended Agent:** backend-integration-tester

1. Full continuation scenario using alpha project data:
   - Reopen completed project
   - Verify `continuation_count` incremented
   - Fill in continuation instructions
   - Generate continuation staging prompt
   - Verify prompt structure
   - Verify `get_orchestrator_instructions()` returns continuation context
   - Verify 360 Memory accessible for project
2. Verify existing staging flow unaffected (fresh project has `continuation_count=0`)
3. Verify double-reopen prevented (project must be completed)
4. WebSocket event verification

---

## Testing Requirements

### Unit Tests
- `test_continue_working_increments_count()`
- `test_continue_working_sets_reopened_at()`
- `test_continue_working_stores_instructions()`
- `test_continue_working_resets_staging_status()`
- `test_continue_working_resets_implementation_launched_at()`
- `test_continue_working_does_not_resume_old_agents()`
- `test_continuation_prompt_includes_phase_number()`
- `test_continuation_prompt_includes_user_instructions()`
- `test_orchestrator_instructions_includes_continuation_context()`
- `test_orchestrator_instructions_no_continuation_for_fresh_project()`
- `test_fresh_project_staging_unaffected()`

### Integration Tests
- E2E continuation staging prompt generation
- Continuation orchestrator reads 360 Memory history
- WebSocket events on project reopen

### Manual Testing
1. Open completed alpha project in browser
2. Click "Continue Working" on /projects page
3. Navigate to staging tab -- verify "Continue Project" button shown
4. Fill in continuation instructions
5. Click "Continue Project" -- verify prompt copied to clipboard
6. Verify prompt contains PHASE 2 label and user instructions
7. Verify staging tab shows previous mission and completed agents

---

## Dependencies and Blockers

**Dependencies:**
- Existing `continue_working` endpoint (exists, needs enhancement)
- Existing `ThinClientPromptGenerator` (exists, needs new method)
- Existing `get_orchestrator_instructions()` (exists, needs continuation detection)
- Alpha project data for testing (exists in database)

**No blockers.** All required infrastructure exists.

**Questions for User:**
1. Should the "Continue Project" button require confirmation ("Are you sure?") or just proceed?
2. Should there be a max limit on `continuation_count` or truly unlimited?

---

## Success Criteria

- [ ] Completed project can be reopened via UI
- [ ] `continuation_count` increments, `last_reopened_at` set, `staging_status` reset
- [ ] Continuation instructions stored on project
- [ ] "Continue Project" button appears on staging tab for reopened projects
- [ ] Continuation staging prompt generated with phase label + user instructions
- [ ] `get_orchestrator_instructions()` returns continuation context with previous mission + 360 Memory pointers
- [ ] Normal staging flow for fresh projects is completely unaffected
- [ ] All existing tests pass, new tests achieve >80% coverage

---

## Rollback Plan

Low-risk additive change. Rollback steps:
1. **Database:** 3 nullable columns with defaults. Can be dropped without data loss.
2. **Service layer:** `continue_working()` changes are backward-compatible. Default behavior preserved when `continuation_instructions` not provided.
3. **Frontend:** Continuation mode only activates when `continuation_count > 0`. Fresh projects see no change.
4. **Revert:** Standard `git revert` of feature commits.

---

## Key File References

| File | Lines | Purpose |
|------|-------|---------|
| `src/giljo_mcp/models/projects.py` | 24-147 | Project model (add 3 columns) |
| `src/giljo_mcp/services/project_service.py` | 863-958 | `continue_working()` (enhance) |
| `api/endpoints/projects/completion.py` | 201-235 | API endpoint (add body param) |
| `src/giljo_mcp/thin_prompt_generator.py` | 1069-1148 | `generate_staging_prompt()` (basis for continuation variant) |
| `src/giljo_mcp/thin_prompt_generator.py` | 60-144 | `build_continuation_prompt()` (reference for prompt patterns) |
| `src/giljo_mcp/services/orchestration_service.py` | 3224-3516 | `get_orchestrator_instructions()` (add continuation context) |
| `src/giljo_mcp/services/orchestration_service.py` | 555-964 | `_build_orchestrator_protocol()` (CH1 continuation variant) |
| `frontend/src/components/projects/LaunchTab.vue` | -- | Staging tab (add continuation mode) |
| `frontend/src/components/projects/ProjectTabs.vue` | -- | Button container (rename button) |
| `frontend/src/services/api.js` | 251, 465 | API calls (enhance) |

---

## Existing Flow Reference (READ BEFORE IMPLEMENTING)

The continuation flow is a variant of the existing staging flow. Before writing any code, use Serena to understand these methods:

1. **`ThinClientPromptGenerator.generate()`** (thin_prompt_generator.py:259-508) -- Main entry point. Creates orchestrator job + execution, generates thin prompt, regenerates mission. Your `generate_continuation_staging_prompt()` follows this same pattern but with continuation-specific prompt text.

2. **`ThinClientPromptGenerator.generate_staging_prompt()`** (thin_prompt_generator.py:1069-1148) -- Ultra-lean staging prompt. Your continuation variant replaces the template text but uses the same infrastructure (job creation, agent_id resolution, MCP URL).

3. **`OrchestrationService.get_orchestrator_instructions()`** (orchestration_service.py:3224-3516) -- Returns identity, protocol, context fetch instructions. Your change adds a `continuation_context` dict to the response when `continuation_count > 0`.

4. **`ProjectService.continue_working()`** (project_service.py:863-958) -- Current reopen logic. Read the full body to understand what it does today (sets inactive, clears completed_at, resumes decommissioned agents). Your changes modify the reset behavior and add the new fields.

5. **`projectStateStore`** (frontend/src/stores/projectStateStore.js) -- Tracks staging completion via WebSocket broadcast detection. The continuation flow uses this identically to the normal flow.

6. **`ProjectTabs.handleStageProject()`** -- The button click handler. Find it with Serena in ProjectTabs.vue. Your "Continue Project" button follows the same pattern (call prompts API, copy to clipboard, show toast).

## Supersedes

This handover **replaces** the original 0486 scope (2026-02-05). The four original features (job reactivation, mission versioning, todo extension, duration timer) were dropped in favor of continuation-aware re-staging.
