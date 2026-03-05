# Handover 0765a: Dead Code Purge + Bridge Removal

**Date:** 2026-03-02
**Priority:** HIGH
**Estimated effort:** 5-7 hours
**Branch:** `0760-perfect-score` (create from `0750-cleanup-sprint`)
**Chain:** `prompts/0765_chain/chain_log.json` (session 0765a)
**Depends on:** Nothing (first in chain)
**Blocks:** 0765b-g (establishes clean baseline)

---

## Objective

Execute the largest single cleanup batch: delete confirmed dead code, remove all compatibility bridge/alias patterns, fix gap items missed by the 0760 proposal, and clean up stale documentation. This session covers Tier 1 + Tier 2 from the 0760 proposal plus all bridge removal work identified by 4 deep-research agents.

**Score impact:** 7.8 -> ~8.8 (Tier 1 + Tier 2 combined)

---

## Pre-Conditions

1. Branch `0760-perfect-score` created from `0750-cleanup-sprint`
2. `pytest` runs clean (1238 passed, 522 skipped, 0 failed)
3. Read this entire handover before starting any implementation
4. Read `prompts/0765_chain/chain_log.json` — update session status to `in_progress`

---

## Task Group 1: Dead Code Deletion (~45 min)

### 1.1 Delete 19 Dead ToolAccessor Methods [Proposal 1C]

**File:** `src/giljo_mcp/tools/tool_accessor.py`

Delete these 19 methods — ALL verified 0 references via LSP `find_referencing_symbols`:

| Method | Purpose (dead) |
|--------|---------------|
| `list_projects` | Pass-through to ProjectService |
| `get_project` | Pass-through to ProjectService |
| `switch_project` | Pass-through to ProjectService |
| `complete_project` | Pass-through to ProjectService |
| `cancel_project` | Pass-through to ProjectService |
| `restore_project` | Pass-through to ProjectService |
| `get_messages` | Pass-through to MessageService |
| `complete_message` | Pass-through to MessageService |
| `broadcast` | Pass-through to WebSocketManager |
| `log_task` | Pass-through to TaskService |
| `get_context_index` | Pass-through to ContextManager |
| `get_vision` | Pass-through to VisionService |
| `get_vision_index` | Pass-through to VisionService |
| `get_product_settings` | Pass-through to ProductService |
| `list_templates` | Pass-through to TemplateManager |
| `create_template` | Pass-through to TemplateManager |
| `update_template` | Pass-through to TemplateManager |
| `set_product_path` | Pass-through to ProductService |
| `get_product_path` | Pass-through to ProductService |

**Verification:** Before deleting each method, run `find_referencing_symbols` to confirm 0 references. If any method has gained a reference since the audit, keep it and note in deviations.

### 1.2 Delete Dead `activate_project` Standalone Function [Proposal 1D]

**File:** `src/giljo_mcp/tools/tool_accessor.py` lines 43-95
**Size:** 53 lines, 0 references
**Evidence:** Duplicates `ProjectService.activate_project`. No caller exists anywhere.

### 1.3 Delete 7 Confirmed Dead Files [Orphan Analysis]

| File | Lines | Evidence |
|------|-------|---------|
| `frontend/src/stores/orchestration.js` | 117 | 0 imports. Functionality moved to `useAgentJobs` composable [Proposal 1E] |
| `src/giljo_mcp/prompt_generation/memory_instructions.py` | 528 | 0 imports anywhere. Docstring claims MissionPlanner uses it but no import exists |
| `frontend/src/components/AgentCard.vue` | 794 | Superseded by AgentCardEnhanced.vue. Only comment references remain |
| `frontend/src/utils/formatters.js` | 17 | 0 imports. **Caution:** Referenced in test mock path `frontend/tests/unit/views/ProjectsView.deleted-projects.spec.js` — delete the test mock reference too |
| `frontend/src/composables/useNotificationReminder.js` | 133 | 0 imports |
| `frontend/src/composables/useProjectState.js` | 18 | 0 imports. Consumers use useProjectStateStore directly |
| `frontend/src/components/settings/modals/index.ts` | 10 | 0 imports. Barrel file unused; SystemSettings.vue imports modals directly |

**Verification:** For each file, grep the entire project for its filename (without extension) to confirm 0 imports. Pay special attention to `formatters.js` — delete the stale test mock reference in the spec file too.

### 1.4 Delete 5 Dead JobsTab Functions [Proposal 1F]

**File:** `frontend/src/components/projects/JobsTab.vue`

| Function | Line | Evidence |
|----------|------|---------|
| `getShortId` | 463 | Not in template, not called by other methods |
| `copyId` | 471 | Not in template, not called by other methods |
| `formatCount` | 645 | Not in template, not called by other methods |
| `getMessagesSent` | 688 | Not in template, not called by other methods |
| `getMessagesRead` | 703 | Not in template, not called by other methods |

### 1.5 Delete Remaining Dead Code Batch [Proposal 2D]

| Target | File | Lines | Evidence |
|--------|------|-------|---------|
| `acknowledgedMessages` computed | `frontend/src/stores/messages.js` | 29 | Dead computed, never read |
| `BroadcastMessageRequest` schema | `api/schemas/prompt.py` | 53-65 | 0 references |
| `BroadcastMessageResponse` schema | `api/schemas/prompt.py` | 66-75 | 0 references |
| 3 dead fixtures | `tests/conftest.py` | varies | `vision_test_files`, `product_service_with_session`, `mock_message_queue` |
| Dead fixture | `tests/integration/conftest.py` | 383-418 | `test_project_with_orchestrator` — also has a bug (references non-existent field) |
| Dead import | `tests/services/test_successor_spawning.py` | 20 | `AgentExecution` import unused |
| 10 STATS DEBUG lines | `api/endpoints/statistics.py` | 145-179 | `[STATS DEBUG]` logger.debug lines — remove all 10 |

---

## Task Group 2: WebSocket Alias Bridge Removal (~60 min)

This is the largest bridge removal. The system currently emits DUPLICATE WebSocket messages for every event that has an alias (4 events x 2 = 8 messages per broadcast instead of 4).

### 2.1 Backend: Delete Alias Machinery

**File:** `api/websocket.py`

1. **Delete `EVENT_TYPE_ALIASES` dict** (lines 21-28) — the 4 canonical-to-legacy mappings
2. **Delete `_event_types_for_broadcast()` method** (lines 70-82) — generates alias lists
3. **Remove `emit_legacy_aliases` parameter** from `WebSocketManager.__init__` (line 34-35)
4. **Simplify `broadcast_event_to_tenant()`** — at line 126, it calls `_event_types_for_broadcast()` and then iterates to send multiple messages at lines 160-161. Change to send a single message with the canonical event type only.

**File:** `api/startup/core_services.py` line 42
- Remove `emit_legacy_aliases=True` if it was passed explicitly (it may be using the default)

### 2.2 Frontend: Remove Legacy Event Handlers

**File:** `frontend/src/stores/websocketEventRouter.js`

Remove these entries from `EVENT_MAP` (lines 89-391):

| Remove | Line | Reason |
|--------|------|--------|
| `agent_update` handler | 93-101 | Legacy underscore variant. Canonical `agent:update` handler at 102-110 is kept |
| `agent:updated` handler | 111-119 | NEVER emitted by backend — pure dead code |
| `product:memory_updated` handler | 389 | Legacy underscore. Canonical `product:memory:updated` at 386 is kept |
| `product:learning_added` handler | 390 | Legacy underscore. Canonical `product:learning:added` at 387 is kept |
| `product:status_changed` handler | 391 | Legacy underscore. Canonical `product:status:changed` at 388 is kept |

Also in `PROJECT_SCOPED_EVENTS` set (lines 29-37):
- Remove `'agent_update'` (line ~35)
- Remove `'agent:updated'` (line ~33)

**IMPORTANT: DO NOT TOUCH the payload normalizers:**
- `frontend/src/stores/websocket.js` lines 427-438 — handles flat vs nested payload format. NOT alias-related. KEEP.
- `frontend/src/stores/websocketEventRouter.js` lines 399-413 — `normalizeWebsocketEvent()`. Same purpose. KEEP.

### 2.3 Dead Event Handler: `product:learning:added`

The canonical `product:learning:added` event has **NO backend emitter**. The frontend handler at `websocketEventRouter.js` line 387 is dead code.

**Decision:** KEEP the canonical handler for now (future-proofing — a learning system may emit this). Remove ONLY the legacy `product:learning_added` handler at line 390.

### 2.4 Update Frontend Tests

| Test File | Change | Line |
|-----------|--------|------|
| `frontend/tests/stores/websocket.spec.js` | Change `agent_update` to `agent:update` | 470, 474 |
| `frontend/tests/e2e/complete-project-lifecycle.spec.ts` | Change `product:memory_updated` to `product:memory:updated` | 197-198 |
| `frontend/src/stores/websocketEventRouter.spec.js` | No changes needed (already uses canonical names) | -- |

---

## Task Group 3: MCP/API Argument Alias Removal (~30 min)

### 3.1 Tier 1: Safe Immediate Removals (ZERO risk)

| # | File | Line | Current Code | Change To | Evidence |
|---|------|------|-------------|-----------|---------|
| 1 | `api/endpoints/mcp_http.py` | 931 | `arguments.get("job_id") or arguments.get("agent_job_id")` | `arguments.get("job_id")` | DEAD CODE: `_TOOL_SCHEMA_PARAMS` allowlist strips `agent_job_id` before this line executes |
| 2 | `api/auth_utils.py` | 127 | `headers.get("x-api-key") or headers.get("x-api-key".lower())` | `headers.get("x-api-key")` | NO-OP: `"x-api-key".lower()` == `"x-api-key"` (already lowercase) |
| 3 | `api/endpoints/downloads.py` | 537 | `body.get("content_type") or body.get("download_type")` | `body.get("content_type")` | Zero callers pass `download_type` via JSON body |
| 4 | `src/giljo_mcp/template_manager.py` | 41 | `augmentation.get("type") or augmentation.get("augmentation_type", "append")` | `augmentation.get("type", "append")` | Old `augmentation_type` format removed in Handover 0423 |
| 5 | `src/giljo_mcp/template_manager.py` | 43 | `augmentation.get("target") or augmentation.get("target_section", "")` | `augmentation.get("target", "")` | Same — old format removed in Handover 0423 |

### 3.2 Tier 2: Safe With Verification

| # | File | Line | Current Code | Change To | Verification Required |
|---|------|------|-------------|-----------|----------------------|
| 6 | `api/middleware/auth.py` | 102 | `auth_result.get("user_id") or auth_result.get("user")` | `auth_result.get("user_id")` | Verify auth manager always returns `user_id` key (confirmed: both JWT and API key paths return `user_id`) |

### 3.3 Tier 3: Investigate Before Removal

| # | File | Line | Current Code | Investigation |
|---|------|------|-------------|---------------|
| 7 | `src/giljo_mcp/services/orchestration_service.py` | 1409 | `progress.get("message") or progress.get("current_step")` | Check if any REST API or direct caller sends `progress` dict with `message` key. The internal builder at line 1343-1351 always uses `current_step`. If no external caller sends `message`, remove the fallback |
| 8 | `src/giljo_mcp/tools/_memory_helpers.py` | 20 | `product_memory.get("git_integration") or product_memory.get("github") or {}` | Check if any `product_memory.json` files in the repo or user data use `github` key. If none found, remove the fallback |

**Action for Tier 3:** Investigate both items. If safe, remove. If not safe, document why and leave with a `# TODO(0765a): investigate` comment.

### 3.4 Do NOT Remove (Intentional Design)

These are NOT aliases — they are data normalization for external inputs:

| File | Line | Pattern | Reason to KEEP |
|------|------|---------|----------------|
| `src/giljo_mcp/tools/_memory_helpers.py` | 114 | `commit.get("lines_added") or commit.get("stats", {}).get("additions")` | External git API data shape varies — not our alias |
| `run_api.py` | 110 | `os.environ.get("GILJO_PORT") or os.environ.get("GILJO_API_PORT")` | Both intentionally supported by installer |
| `port_manager.py` | 213 | Multiple env var checks | Deliberate multi-env-var support |

### 3.5 Dead Auth State — Remove Entire Assignment Block

**File:** `api/middleware/auth.py` line 102

The entire `request.state.user_id` and `request.state.user` assignment block is **DEAD CODE**:
- No endpoint in the codebase reads `request.state.user_id` or `request.state.user`
- Authentication is handled independently by `get_current_user` in `api/auth/dependencies.py`
- The only consumer is the warning log at line 109 in the same file

**Action:** Delete the `request.state.user_id` assignment, the `request.state.user` assignment, and the associated warning log. Keep the `request.state.tenant_key` assignment (which IS used downstream).

---

## Task Group 4: Stale Documentation Cleanup (~30 min)

### 4.1 HIGH Priority — Production Code Docstrings

| # | File | Line | Current Text | Fix |
|---|------|------|-------------|-----|
| 1 | `src/giljo_mcp/services/project_service.py` | 557 | `"broadcasts the mission update via WebSocket HTTP bridge"` | Change to `"broadcasts the mission update via in-process WebSocketManager"` |
| 2 | `src/giljo_mcp/services/project_service.py` | 612 | `"# Broadcast mission update via WebSocket HTTP bridge"` | Change to `"# Broadcast mission update via WebSocketManager"` |

### 4.2 MEDIUM Priority — Dead Bridge Infrastructure

These should already be deleted by Task Group 2.1, but verify after WebSocket bridge removal:

| # | File | Line | What | Action |
|---|------|------|------|--------|
| 3 | `api/endpoints/websocket_bridge.py` | entire file | Dead endpoint file | DELETE (entire file) |
| 4 | `api/app.py` | 431 | `app.include_router(websocket_bridge.router, ...)` | DELETE this line |
| 5 | `api/middleware/auth.py` | 158 | `"/api/v1/ws-bridge"` in public paths list | DELETE this entry |

### 4.3 MEDIUM Priority — Stale Test Mocks

| # | File | Line | What | Action |
|---|------|------|------|--------|
| 6 | `tests/services/test_orchestration_service_agent_mission.py` | 133 | `"# Stub httpx to avoid real WebSocket bridge calls"` | Verify if httpx mock is still needed. If not (bridge is gone), remove the mock block entirely |
| 7 | `tests/services/test_orchestration_implementation_phase_gate.py` | 189 | Same stale comment and mock | Same treatment as #6 |

### 4.4 LOW Priority — Misleading Schema Labels

**File:** `api/events/schemas.py`

Remove `(legacy)` from these field descriptions — `job_id`, `from_agent`, `to_agent`, `message` are all still active fields:

| Line | Current Description | New Description |
|------|-------------------|-----------------|
| 292 | `"Sender job_id (legacy)"` | `"Sender agent job UUID"` |
| 294 | `"Sender label (legacy)"` | `"Sender display label"` |
| 295 | `"Recipient label (legacy)"` | `"Recipient display label"` |
| 299 | `"Message preview (legacy)"` | `"Message preview"` |
| 329 | `"Sender job_id (legacy)"` | `"Sender agent job UUID"` |
| 331 | `"Sender label (legacy)"` | `"Sender display label"` |
| 332 | `"Recipient agent IDs (legacy)"` | `"Recipient agent IDs"` |
| 336 | `"Message preview (legacy)"` | `"Message preview"` |

### 4.5 LOW Priority — Stale Comments and Dev Scripts

| # | File | Line | Action |
|---|------|------|--------|
| 8 | `tests/services/test_orchestration_service_websocket_emissions.py` | 5 | Simplify docstring — remove parenthetical bridge reference |
| 9 | `api/websocket_event_listener.py` | 175 | Fix comment: change `"Canonical field name"` to `"Agent job ID from event data"` |
| 10 | `scripts/simulate_mcp.ps1` | 27 | Update `$bridge` URL — either remove the bridge call or note it requires the now-deleted endpoint |

### 4.6 Placeholder Label Clarity

**File:** `src/giljo_mcp/prompt_generation/thin_prompt_generator.py` lines 235, 246

The placeholder `job_id="<agent_job_id>"` is confusing (looks like the old parameter name). Change to `job_id="<their_job_id>"` or `job_id="<agent_job_id_value>"` for clarity.

---

## Task Group 5: Gap Item Fixes (~60 min)

### 5.1 Fix 2 Pre-Existing Test Failures [NEW-4]

**File:** `tests/api/test_auth_org_endpoints.py`

Failing tests:
- `test_create_first_admin_accepts_workspace_name`
- `test_create_first_admin_defaults_workspace_name`

**Root cause:** Tests expect a 201 path but the test environment already has existing admin/users, so the endpoint returns 400 "Administrator account already exists."

**Fix options (choose one):**
1. **Preferred:** Add a fixture that resets the admin state before these tests (delete existing admin in test DB)
2. **Alternative:** Change the assertion to expect 400 when admin exists, and add a separate test with a clean DB that tests the 201 path
3. **Skip with marker:** If the fixture approach is too complex, add `@pytest.mark.skip(reason="Requires empty DB — tracked in 0765a")` and document

### 5.2 Fix 3 Prompts Endpoints Returning Raw Dicts [M-9]

**File:** `api/endpoints/prompts.py`

| Endpoint | Line | Current | Fix |
|----------|------|---------|-----|
| staging prompt | ~432 | Returns raw dict | Wrap in Pydantic response model |
| implementation prompt | ~624 | Returns raw dict | Wrap in Pydantic response model |
| termination prompt | ~790 | Returns raw dict | Wrap in Pydantic response model |

Create a simple `PromptResponse` schema in `api/schemas/prompt.py` with the dict structure, then use it as the response model. This aligns these endpoints with the rest of the API.

### 5.3 Fix Statistics Endpoints [Proposal 2B]

**File:** `api/endpoints/statistics.py`

1. **Remove 4 hardcoded fake metrics:**
   - `avg_response_time=30.0` — Replace with `None` or compute from real data
   - `avg_processing_time=45.0` — Replace with `None` or compute from real data
   - `active_sessions=1` — Replace with actual count from WebSocket connections
   - `error_rate=0.1` — Replace with `None` or compute from real data
2. **Fix N+1 query:** `get_project_statistics_by_id` iterates all projects. Add `current_user` parameter and filter by user's projects only.

### 5.4 Convert ActionIcons.vue to Script Setup [Proposal 2F]

**File:** `frontend/src/components/StatusBoard/ActionIcons.vue`

Currently a hybrid (Options API shell + Composition API internals). Already uses `ref()`, `computed()`. Mechanical conversion to `<script setup>` — straightforward.

### 5.5 Fix Stale Status Strings [Proposal 2E]

| File | Line | Issue | Fix |
|------|------|-------|-----|
| `api/repositories/statistics_repository.py` | 371 | Filter uses `"idle"` (invalid status) | Replace with valid statuses: `waiting`, `working`, `blocked`, `complete`, `silent`, `decommissioned` |
| `api/repositories/agent_job_repository.py` | 111 | Docstring references `"pending"/"failed"` | Update to valid status names |

---

## Execution Order

Execute in this sequence to minimize merge conflicts and allow incremental testing:

1. **Task Group 1** (Dead Code Deletion) — biggest line reduction, no behavioral change
2. **Task Group 2** (WebSocket Aliases) — requires backend + frontend coordination
3. **Task Group 3** (Argument Aliases) — small surgical changes across many files
4. **Task Group 4** (Documentation) — text-only changes, zero risk
5. **Task Group 5** (Gap Items) — behavioral changes, requires testing

**Commit strategy:** One commit per task group. Prefix with `cleanup(0765a):`.

---

## Testing Requirements

### After Task Group 1 (Dead Code)
- `pytest tests/ -x -q` — full suite must remain green (1238+ passed)
- Frontend: `npm run build` in `frontend/` — must compile without errors
- Verify no import errors after file deletions

### After Task Group 2 (WebSocket Aliases)
- `pytest tests/services/test_orchestration_service_websocket_emissions.py -v` — all WS tests pass
- Frontend: Check websocketEventRouter.spec.js still passes
- Manual check: Start the app, navigate to a project, verify agent status updates arrive via WebSocket

### After Task Group 3 (Argument Aliases)
- `pytest tests/api/ -x -q` — all API tests pass
- `pytest tests/services/ -x -q` — all service tests pass

### After Task Group 5 (Gap Items)
- `pytest tests/api/test_auth_org_endpoints.py -v` — NEW-4 failures fixed
- `pytest tests/ -x -q` — full green suite

---

## Cascading Impact Analysis

### Entity Hierarchy Impact
- **No model changes** — all changes are at the code/documentation level
- **No database migrations** — no schema changes
- **No installation impact** — `install.py` unaffected

### Downstream Impact
- WebSocket alias removal: Frontend must be updated in the SAME commit or prior commit. Never remove backend aliases without updating frontend handlers first.
- Bridge endpoint deletion: `scripts/simulate_mcp.ps1` dev script will break — acceptable, document the change.
- Dead file deletion: `formatters.js` has a test mock reference — delete the mock reference too.

### Upstream Impact
- None. All changes are subtractive (removing dead code) or corrective (fixing stale docs).

---

## Success Criteria

- [ ] 19 dead ToolAccessor methods deleted
- [ ] 7 dead files deleted (~1,617 lines)
- [ ] 5 dead JobsTab functions deleted
- [ ] WebSocket EVENT_TYPE_ALIASES system fully removed (backend + frontend)
- [ ] 6+ argument alias fallbacks removed
- [ ] Dead `request.state.user_id`/`request.state.user` removed
- [ ] WebSocket bridge endpoint deleted (file + router + auth exemption)
- [ ] 25 stale documentation references fixed
- [ ] NEW-4 test failures resolved
- [ ] M-9 prompts endpoints wrapped in response models
- [ ] Statistics fake metrics removed
- [ ] ActionIcons.vue converted to `<script setup>`
- [ ] All tests pass: `pytest tests/ -x -q` green
- [ ] Frontend builds: `npm run build` clean
- [ ] Chain log updated: session 0765a status = `complete`

---

## Completion Protocol

1. Run full test suite and frontend build
2. Update `prompts/0765_chain/chain_log.json` — set 0765a status to `complete`, fill in `tasks_completed`, `deviations`, `notes_for_next`, `summary`
3. Write completion summary back to THIS handover (append to bottom, max 400 words)
4. Commit with message: `cleanup(0765a): Dead code purge + bridge removal — Tier 1+2 complete`
