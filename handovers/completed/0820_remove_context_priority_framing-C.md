# Handover 0820: Remove Context Priority Framing (CRITICAL/IMPORTANT/REFERENCE)

**Date:** 2026-03-15
**From Agent:** User + Session Agent
**To Agent:** Fresh session (no prior context)
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Remove the entire context priority framing system (CRITICAL/IMPORTANT/REFERENCE labels, priority values 1/2/3/4) from the codebase. The system assigns priority labels to context categories (product_core, tech_stack, vision_documents, etc.) that were intended to guide LLM fetch decisions. Testing showed LLMs ignore these labels entirely -- they either fetch everything toggled on, or decide based on task relevance regardless of the priority label.

**What stays:** Toggle (on/off per category) and depth controls (how much data to serve). These are genuinely useful.
**What goes:** The priority integer (1/2/3/4) and its labels (CRITICAL/IMPORTANT/REFERENCE), all framing text injected into prompts, the entire framing_helpers.py module, the ContextPriorityConfig UI component (the priority selector portion), the field-priority API endpoints, and all related tests/docs.

---

## Context and Background

The priority framing system was built across handovers 0048, 0248, 0279, 0301, 0313, 0400. It evolved from v1.0 (token budget levels: 10/7/4/0) to v2.0 (fetch order: 1/2/3/4 = CRITICAL/IMPORTANT/REFERENCE/EXCLUDED). The intent was that LLM agents would use these labels to decide which context categories to fetch first or skip under token pressure.

**Why removing:** Real-world testing (March 2026 MCP context fetch sessions) demonstrated:
- LLMs fetch based on task relevance, not priority labels
- If a category is toggled ON, LLMs fetch it regardless of label
- The binary toggle already captures the user's intent (fetch/don't fetch)
- Depth controls already manage payload size (3 vs 10 projects, medium vs full summary)
- The framing adds complexity without influencing behavior

**Backup:** Branch `Removal_context_framing` preserves the full codebase before any changes. Full filesystem + database backup at `D:\E_Drive_backup\Coding\GiljoAI_MCP_Backup_20260315_framing_removal\`.

---

## Technical Details

### Files to Modify/Remove -- Backend

#### 1. `src/giljo_mcp/config/defaults.py` (MODIFY)
- **Remove:** The `"priority"` key from each category in `DEFAULT_FIELD_PRIORITY["priorities"]` -- keep only `"toggle"` per category
- **Remove:** `get_categories_by_priority()` function (lines ~135-155)
- **Remove:** `get_priority_for_category()` function (lines ~158-174)
- **Remove:** `validate_default_config()` function's priority validation (lines ~210-249) -- keep toggle validation
- **Keep:** `DEFAULT_FIELD_PRIORITY` dict (rename to `DEFAULT_FIELD_TOGGLES` or similar), `DEFAULT_DEPTH_CONFIG`, `get_toggle_for_category()`, `get_depth_for_category()`
- **Update:** All comments referencing CRITICAL/IMPORTANT/REFERENCE labels
- **Simplify:** Data structure from `{"toggle": True, "priority": 1}` to just `{"toggle": True}` or even `True/False`

#### 2. `src/giljo_mcp/tools/context_tools/framing_helpers.py` (REMOVE ENTIRELY or GUTTED)
- Contains 8 functions all related to priority framing: `apply_rich_entry_framing`, `_extract_priorities`, `get_user_priority`, `inject_priority_framing`, `build_priority_excluded_response`, `build_framed_context_response`, etc.
- Also contains `format_list_safely` and `_stringify_content` which MAY be used elsewhere -- check references before deleting
- **Action:** Check if `format_list_safely` or `_stringify_content` are imported elsewhere. If not, delete entire file. If yes, move those helpers to a utils module.

#### 3. `src/giljo_mcp/tools/context_tools/__init__.py` (MODIFY)
- Remove exports of framing_helpers symbols

#### 4. `src/giljo_mcp/thin_prompt_generator.py` (MODIFY -- CRITICAL FILE)
- Lines ~424-426: `field_priorities = user.field_priority_config.get("priorities", {})`
- Lines ~659-660: `tech_priority = field_priorities.get("tech_stack", 2)` and similar checks
- Lines ~680-681: `arch_priority = field_priorities.get("architecture", 2)` and similar
- Lines ~810: Docstring references to `1=CRITICAL, 2=IMPORTANT, 3=NICE_TO_HAVE, 4=EXCLUDED`
- Lines ~868: Priority configuration auto-application comment
- **Replace:** Priority-based logic with simple toggle checks: `if toggle_config.get("tech_stack", True):`

#### 5. `src/giljo_mcp/tools/project_closeout.py` (MODIFY)
- Lines 398-406: `_derive_priority()` function that maps to 1=CRITICAL, 2=IMPORTANT, 3=REFERENCE
- **Action:** Remove function. If the return value is stored in closeout data, decide whether to replace with a simpler signal or remove entirely.

#### 6. `src/giljo_mcp/mission_planner.py` (MODIFY)
- Contains `priority_label` references
- **Action:** Remove framing injection into mission plans

#### 7. `src/giljo_mcp/services/user_service.py` (MODIFY)
- `get_field_priority_config()` and `update_field_priority_config()` methods
- **Action:** Simplify to toggle-only config (remove priority validation, keep toggle persistence)

#### 8. `src/giljo_mcp/services/protocol_builder.py` (MODIFY -- SIGNIFICANT)
- Lines ~25-26: Imports `DEFAULT_FIELD_PRIORITY`
- Line ~412: `DEFAULT_FIELD_PRIORITIES = _DEFAULT_FIELD_PRIORITY["priorities"]` flattened for use
- Lines ~416-443: `_normalize_field_priorities()` converts nested `{"toggle": True, "priority": X}` to flat ints, with toggle=False becoming priority 4 (EXCLUDED)
- Lines ~446-558: `_get_user_config()` fetches user's `field_priority_config` from DB
- **Action:** Simplify normalization to toggle-only. Remove priority int extraction. Keep depth config logic.

#### 9. `src/giljo_mcp/services/orchestration_service.py` (MODIFY -- SIGNIFICANT)
- Line ~2387: `get_orchestrator_instructions()` -- "framing-based context instructions"
- Line ~2506: Calls `planner._build_fetch_instructions()` for tiered instructions
- Line ~2544: "Build framing-based response"
- Line ~2575: Response includes `"architecture": "framing_based"`
- Line ~2611: Log message `"[FRAMING_BASED] Returning framing-based orchestrator instructions"`
- **Action:** Replace framing-based architecture with simple toggle-based fetch list. Remove tier grouping.

#### 10. `src/giljo_mcp/services/project_service.py` (CHECK)
- May reference field_priority -- check and clean up

#### 11. `src/giljo_mcp/tools/context_tools/fetch_context.py` (MODIFY)
- Line ~103: `"apply_user_config: Apply user's saved priority/depth settings"`
- **Action:** Remove priority application, keep depth application. Update parameter docs.

#### 10. `src/giljo_mcp/prompt_generation/testing_config_generator.py` (MODIFY)
- References to priority/CRITICAL/IMPORTANT
- **Action:** Remove priority-related test config generation

### Files to Modify -- API Endpoints

#### 11. `api/endpoints/users.py` (MODIFY -- MAJOR)
- Lines 132-147: `FieldPriorityConfig` Pydantic model -- simplify to toggle-only schema
- Lines 624-668: `GET /me/field-priority` endpoint -- simplify or rename to `/me/field-toggles`
- Lines 671-760: `PUT /me/field-priority` endpoint -- remove priority validation, keep toggle updates
- Lines 760+: `POST /me/field-priority/reset` endpoint -- simplify
- **Decision needed:** Rename endpoints from `field-priority` to `field-toggles`? Or keep URL for backwards compat and just change payload?

#### 12. `api/endpoints/prompts.py` (CHECK)
- May reference field_priority -- clean up

#### 13. `api/endpoints/agent_jobs/simple_handover.py` (CHECK)
- May reference field_priority -- clean up

### Files to Modify -- Database

#### 14. `src/giljo_mcp/models/auth.py` (MODIFY)
- Line ~115: `field_priority_config = Column(JSONB, nullable=True, default=None, ...)`
- **Decision:** Keep the column but store simplified toggle config, OR rename column
- **Recommendation:** Keep column name for now, just change stored data format from `{"version": "2.1", "priorities": {"product_core": {"toggle": true, "priority": 1}, ...}}` to `{"version": "3.0", "toggles": {"product_core": true, ...}}`
- **No migration needed** if column stays JSONB and nullable -- existing data just gets overwritten on next save

### Files to Modify -- Frontend

#### 15. `frontend/src/components/settings/ContextPriorityConfig.vue` (MAJOR REWRITE or REMOVE)
- This is the main UI component for configuring priorities
- **Action:** Either strip down to toggle-only UI, or replace entirely with a simpler toggle list
- The toggle switches and depth controls should remain; the priority dropdowns/badges (CRITICAL/IMPORTANT/REFERENCE) go away

#### 16. `frontend/src/stores/settings.js` (MODIFY)
- Line 27: `fieldPriorityConfig` ref
- Lines 159, 169, 179: Setting fieldPriorityConfig.value
- Line 200: Export
- **Action:** Simplify to toggle-only state, or rename to `fieldToggleConfig`

#### 17. `frontend/src/services/api.js` (MODIFY)
- Lines 347-350: `getFieldPriorityConfig`, `updateFieldPriorityConfig`, `resetFieldPriorityConfig`
- **Action:** Rename or simplify API calls

#### 18. `frontend/src/composables/useFieldPriority.js` (MODIFY or REMOVE)
- Composable for field priority logic
- **Action:** Simplify to toggle-only logic, or remove if ContextPriorityConfig component handles it directly

#### 19. `frontend/src/views/UserSettings.vue` (MODIFY)
- Imports and renders ContextPriorityConfig
- **Action:** Update import if component is renamed

#### 20. `frontend/src/views/ProductsView.vue` (CHECK)
- May reference field priority -- clean up

### Files to Remove/Modify -- Tests

#### 21. Backend Tests
- `tests/unit/test_framing_helpers_validation.py` -- **DELETE** (tests removed module)
- `tests/services/test_user_field_priorities.py` -- **REWRITE** (test toggle-only behavior)
- `tests/services/test_user_service_auth_config.py` -- **MODIFY** (remove priority references)
- `tests/services/conftest.py` -- **MODIFY** (remove priority fixtures)
- `tests/services/test_thin_client_prompt_generator_agent_templates_context.py` -- **MODIFY**
- `tests/services/test_thin_client_prompt_generator_agent_templates_core.py` -- **MODIFY**

#### 22. Frontend Tests (ALL priority-specific tests DELETE, others MODIFY)
- `frontend/tests/unit/components/settings/ContextPriorityConfig.spec.js` -- **DELETE or REWRITE**
- `frontend/tests/unit/components/settings/ContextPriorityConfig.spec.ts` -- **DELETE or REWRITE**
- `frontend/tests/unit/components/settings/ContextPriorityConfig.dual-endpoint.spec.js` -- **DELETE**
- `frontend/tests/unit/components/settings/ContextPriorityConfig.vision.spec.js` -- **DELETE or REWRITE**
- `frontend/tests/unit/components/settings/ContextPriorityConfig.websocket-realtime.spec.js` -- **DELETE or REWRITE**
- `frontend/__tests__/components/settings/ContextPriorityConfig.spec.js` -- **DELETE or REWRITE**
- `frontend/tests/views/UserSettings.spec.js` -- **MODIFY**
- `frontend/__tests__/views/UserSettings.spec.js` -- **MODIFY** (if it exists and references priority)
- `frontend/tests/unit/global-tab-styles.spec.js` -- **CHECK** (may reference component)
- `frontend/eslint.config.js` -- **CHECK** (may have ignore rules for the component)
- `frontend/selector-validation.test.js` / `frontend/validate-selectors.js` / `frontend/tests/e2e/selector-validation.spec.ts` -- **CHECK** for ContextPriorityConfig references

### User-Facing Copy (Product Descriptions, Onboarding, "What is GiljoAI")

#### 23. `frontend/src/components/settings/ProductIntroTour.vue` (MODIFY -- USER-FACING)
- Line 168: `{ icon: 'mdi-layers-triple', title: 'Context controls', caption: 'Priority + depth settings' }`
  - **Change to:** `caption: 'Toggleable categories + depth settings'` (or similar)
- Line 173: `'Context priority + depth controls decide what to include.'`
  - **Change to:** `'Context toggles + depth controls decide what to include.'`
- These are shown in the "What is GiljoAI MCP" intro tour that appears on first use

#### 24. `frontend/src/components/settings/ContextPriorityConfig.vue` (RENAME considerations)
- Line 4: Title reads `"Context Priority Configuration"` -- should become `"Context Configuration"` or `"Context Toggle & Depth"`
- Component filename itself may warrant renaming to `ContextConfig.vue` or `ContextToggleConfig.vue`
- If renamed, update all imports in `UserSettings.vue`, test files, `eslint.config.js`, `selector-validation` files

### Documentation Updates

#### 25. Active docs to update (find priority framing references and remove/update):
- `docs/user_guides/field_priorities_guide.md` -- **DELETE or FULL REWRITE** (entire file is a user guide for the old v1.0 priority system with 0-10 scale -- completely obsolete)
- `docs/architecture/FIELD_PRIORITIES_SYSTEM.md` -- **DELETE or REWRITE** to describe toggle-only system
- `docs/guides/context_configuration_guide.md` -- **UPDATE** (line 7: "Priority (WHAT to fetch)" -> toggle language)
- `docs/api/context_tools.md` -- **UPDATE** (line 61: "Apply saved priority/depth settings")
- `docs/SERVICES.md` -- **UPDATE** (line 24: remove `get_field_priority_config`, `update_field_priority_config`, `reset_field_priority_config`)
- `docs/ORCHESTRATOR.md` -- **UPDATE** (line 124: "Apply user's context priority settings (3-tier: CRITICAL/IMPORTANT/REFERENCE)")
- `docs/SERVER_ARCHITECTURE_TECH_STACK.md` -- **UPDATE** (lines 722, 752, 825, 860: priority config references)
- `docs/architecture/ORCHESTRATOR_CONTEXT_FLOW_SSoT.md` -- **UPDATE** (lines 14, 22, 24, 171: "context priority cards", "13 Context Priority Cards")
- `docs/README_FIRST.md` -- **UPDATE** (line 35: "Context Priority Management")
- `docs/components/STAGING_WORKFLOW.md` -- **UPDATE** (line 304: "Fetch user's context priority configuration")
- `docs/architecture/service_response_models.md` -- **CHECK**
- `docs/agent-templates/*.md` (analyzer, documenter, reviewer, tester, implementer) -- **CHECK**

#### 26. Reference docs (update if still actively read):
- `handovers/Reference_docs/QUICK_LAUNCH.txt` -- **UPDATE** (line ~1360 references priority framing)
- `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md` -- **UPDATE** (line 332: "Context priority settings")
- `handovers/Reference_docs/HARMONIZED_WORKFLOW.md` -- **UPDATE** (line 115: "Reads all context based on priority settings")
- `handovers/Reference_docs/start_to_finish_agent_FLOW.md` -- **UPDATE** (line 269: "Reads context based on user's priority settings")
- `handovers/Reference_docs/Simple_Vision.md` -- **UPDATE** (line 228: "Applies field priority settings from My Settings")
- `handovers/Reference_docs/resource_index.md` -- **CHECK**
- `WEBSITE_MESSAGING_REVISION_BRIEF.md` -- **UPDATE** (line 316: "tiered priority toggles (CRITICAL / IMPORTANT / REFERENCE)")
- `frontend/CONTEXT_PRIORITY_CONFIG_DUAL_ENDPOINT_IMPLEMENTATION.md` -- **DELETE** (entire file documents the dual-endpoint priority implementation)

Note: Completed handovers in `handovers/completed/` are historical records and should NOT be modified.

---

## Implementation Plan

### Phase 1: Backend Core (Priority: First)
**Recommended Agent:** tdd-implementor

1. **Simplify `defaults.py`** -- remove priority integers from DEFAULT_FIELD_PRIORITY, keep toggle/depth only
2. **Remove/gut `framing_helpers.py`** -- check for reusable helpers first, then delete or strip
3. **Update `__init__.py`** exports in context_tools
4. **Update `thin_prompt_generator.py`** -- replace all priority-based logic with toggle checks
5. **Update `mission_planner.py`** -- remove framing injection
6. **Remove `_derive_priority()` from `project_closeout.py`**
7. **Simplify `user_service.py`** -- toggle-only validation
8. **Clean up `protocol_builder.py`** and `project_service.py`
9. **Clean up `testing_config_generator.py`**
10. **Simplify `orchestration_service.py`** -- replace framing-based architecture with toggle-based fetch list
11. **Delete `tests/unit/test_framing_helpers_validation.py`**, update other backend tests

**Testing:** Run `pytest tests/ -x --tb=short` after each major file change

### Phase 2: API Endpoints
**Recommended Agent:** tdd-implementor

1. **Simplify `FieldPriorityConfig` model** in `api/endpoints/users.py` -- toggle-only schema
2. **Update 3 field-priority endpoints** -- accept/return toggle-only payload
3. **Clean up `prompts.py`** and `simple_handover.py`
4. **Update conftest.py** fixtures

**Testing:** Run API tests for user endpoints

### Phase 3: Frontend
**Recommended Agent:** ux-designer or tdd-implementor

1. **Rewrite `ContextPriorityConfig.vue`** -- strip priority selectors, keep toggle switches + depth controls
2. **Simplify `settings.js` store** -- toggle-only state
3. **Update `api.js`** service calls
4. **Simplify/remove `useFieldPriority.js`** composable
5. **Update `UserSettings.vue`** if component name changes
6. **Delete priority-specific test files**, rewrite toggle-focused tests
7. **Update selector validation** files if needed

**Testing:** Run frontend tests `npm run test -- --run`

### Phase 4: Documentation & Cleanup
**Recommended Agent:** documentation-manager

1. **Update/delete `FIELD_PRIORITIES_SYSTEM.md`**
2. **Update `context_configuration_guide.md`**
3. **Update all docs with priority framing references** (see list in Technical Details section 23-24)
4. **Final grep** for orphaned references: `CRITICAL.*IMPORTANT.*REFERENCE`, `priority.*framing`, `field_priority`, `1.*CRITICAL`

---

## Testing Requirements

### Backend Tests
- All existing tests pass after modification (run full `pytest`)
- Toggle-only behavior: toggled ON categories included in context, toggled OFF excluded
- Depth config still works independently of priority removal
- User service saves/loads toggle config correctly
- Thin prompt generator uses toggles correctly

### Frontend Tests
- Toggle switches work (on/off per category)
- Depth controls still functional
- Settings save/load correctly via API
- No references to CRITICAL/IMPORTANT/REFERENCE in rendered UI

### Manual Testing
1. Open User Settings > Context Configuration
2. Verify priority dropdowns are gone, toggle switches remain
3. Toggle categories on/off, verify they save
4. Adjust depth controls, verify they save
5. Start a new agent project, verify context is served based on toggles (not priorities)

---

## Dependencies and Blockers

- **No external dependencies** -- purely internal refactoring
- **Database:** No migration needed (JSONB column stays, data format changes on write)
- **Pre-requisite:** Ensure `Removal_context_framing` branch exists as backup (DONE)

---

## Success Criteria

1. Zero references to CRITICAL/IMPORTANT/REFERENCE priority framing in production code (excluding completed handovers archive)
2. `framing_helpers.py` deleted (or stripped to non-priority helpers only)
3. All `pytest` tests pass
4. All frontend tests pass
5. UI shows toggle + depth controls only, no priority selectors
6. Existing toggle + depth functionality preserved and working
7. `grep -r "priority.*framing\|CRITICAL.*IMPORTANT.*REFERENCE\|inject_priority_framing\|apply_rich_entry_framing" src/ api/ frontend/src/` returns zero results

---

## Rollback Plan

1. **Git branch:** `git checkout Removal_context_framing` to get full pre-change codebase
2. **Filesystem backup:** `D:\E_Drive_backup\Coding\GiljoAI_MCP_Backup_20260315_framing_removal\code\`
3. **Database backup:** Restore with `pg_restore -U postgres -d giljo_mcp D:\E_Drive_backup\Coding\GiljoAI_MCP_Backup_20260315_framing_removal\giljo_mcp_db.dump`

---

## Additional Resources

- Backup branch: `Removal_context_framing` (created from master at commit `5a37cb73`)
- Original implementation handovers: 0048, 0248, 0279, 0301, 0313, 0400 (in `handovers/completed/`)
- Context configuration guide: `docs/guides/context_configuration_guide.md`
- Field priorities system doc: `docs/architecture/FIELD_PRIORITIES_SYSTEM.md`
