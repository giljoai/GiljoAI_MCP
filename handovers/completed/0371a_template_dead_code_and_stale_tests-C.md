# Handover 0371a: Template Dead Code Removal & Stale Test Remediation

**Date**: 2026-02-21
**Status**: READY FOR IMPLEMENTATION
**Priority**: MEDIUM
**Type**: Dead Code Removal + Test Remediation + Minor Fix
**Estimated Time**: 4-5 hours
**Parent**: 0371 (Dead Code Cleanup Project -- Phases 4.6+)
**Closes**: 0254 (resolved by organic evolution, remaining scraps captured here)

---

## Executive Summary

Handover 0254 (Three-Layer Instruction Cleanup, Nov 2025) was closed as resolved -- the core problem of conflicting agent instructions across three layers was fixed by the 0700 cleanup series, 0431 MCP section trim, 0407 todo_items refactor, and 0334 HTTP-only migration. What remains are dead code artifacts and 50 stale tests that need cleanup.

**Scope**:
1. Delete dead `GenericAgentTemplate` class and entire `src/giljo_mcp/templates/` package
2. Delete dead `export_claude_templates.py` (root)
3. Delete orphaned `claude_agent_templates/` folder
4. Remove dead `_get_template_metadata()` call in `template_seeder.py`
5. Fix 50 failing template seeder tests across 8 test files
6. Fix 7 bare-name MCP tool references in `thin_prompt_generator.py`

---

## Phase 1: Dead Code Deletion (30 min)

### 1a. Delete `src/giljo_mcp/templates/` package (CONFIRMED DEAD)

**Evidence**: Zero consumers in production. `__init__.py` exports `GenericAgentTemplate` but nobody imports from the package. Not imported by `thin_prompt_generator.py`, `orchestration_service.py`, or any API endpoint. The actual agent lifecycle protocol lives in `orchestration_service.py:_generate_agent_protocol()` (lines 215-394) and is delivered via `get_agent_mission()` as `full_protocol`.

**Files to delete**:
- `src/giljo_mcp/templates/__init__.py` (12 lines, only exports GenericAgentTemplate)
- `src/giljo_mcp/templates/generic_agent_template.py` (168 lines, GenericAgentTemplate class)

**Impact check**: Search for `from giljo_mcp.templates` or `from .templates` -- zero results in `src/` and `api/`.

**Test files that import GenericAgentTemplate** (must also fix):
- `tests/unit/test_template_seeder_layer_separation.py` lines 6, 26, 60 -- remove import and adjust tests

### 1b. Delete `export_claude_templates.py` (CONFIRMED DEAD)

**Location**: Project root `F:\GiljoAI_MCP\export_claude_templates.py` (287 lines)

**Evidence**: Zero Python imports anywhere. Only referenced in documentation. Contains 5 instances of obsolete MCP commands (`update_job_status`, `receive_agent_messages`, `send_agent_message`).

**The 4 LIVE export/download code paths are ALL separate and clean**:
- **Path A** (Direct ZIP): `api/endpoints/downloads.py:download_agent_templates()` -> `template_renderer.py:render_claude_agent()`
- **Path B** (Timed token): `download_tokens.py:TokenManager` -> `file_staging.py:stage_agent_templates()` -> `template_renderer.py:render_claude_agent()`
- **Path C** (UI clipboard): `frontend/src/components/ClaudeCodeExport.vue` -> POST `/api/download/generate-token`
- **Path D** (Filesystem): `api/endpoints/claude_export.py:export_claude_code_endpoint()` -> `claude_export.py:generate_yaml_frontmatter()`

None of these paths reference `export_claude_templates.py`.

### 1c. Delete `claude_agent_templates/` folder (CONFIRMED DEAD)

**Location**: `F:\GiljoAI_MCP\claude_agent_templates/`

**Contents**: Only `VALIDATION_REPORT.md` (historic artifact from Oct 2025). The .md template files referenced in handover 0254 are already gone.

**Evidence**: Zero code references in any Python, JS, Vue, or config file.

```bash
rm -rf claude_agent_templates/
```

### 1d. Remove dead `_get_template_metadata()` call (PARTIALLY DEAD)

**File**: `src/giljo_mcp/template_seeder.py`

**The call at line 165**: Return value is discarded (bare function call, not assigned).
```python
# line 163-165:
# Define comprehensive metadata for each template
# Extracted from original template content and handover requirements
_get_template_metadata()       # <-- RETURN VALUE DISCARDED
```

**BUT**: `dev_tools/devpanel/scripts/devpanel_index.py` line 227-229 is a LIVE consumer. So the function itself must stay, only the dead call at line 165 should be removed.

**Also**: The function has dead code inside it -- `mcp_rules = []` and `mcp_success = []` with comments referencing GenericAgentTemplate (lines 598-605). Clean up those comments.

---

## Phase 2: Stale Test Remediation (3 hours)

**Scale**: 50 tests FAIL across 8 files. 5 more pass vacuously (assertions never execute).

### Root Causes (fix these patterns, not individual tests)

| # | Root Cause | Tests Affected | Fix |
|---|-----------|---------------|-----|
| 1 | Template count 6 -> 5 (orchestrator is SYSTEM_MANAGED, skipped in seeding) | 29 tests | Change `== 6` to `== 5`, remove orchestrator-specific queries that use `scalar_one()` |
| 2 | MCP section slimmed in 0431 (header changed from `MCP COMMUNICATION PROTOCOL` to `MCP Tool Usage`, tool names removed) | 15+ tests | Update assertions to match current slim section |
| 3 | Dict key is `user_instructions` not `system_instructions` in `_get_default_templates_v103()` return | 3 tests | Fix key name |
| 4 | Orchestrator vs non-orchestrator get different `system_instructions` | 2 tests | Remove "identical system_instructions" assertion |
| 5 | Obsolete tool names (`get_next_instruction`, `update_job_status`, `get_pending_jobs`) | 5+ tests | Remove or replace with current tool names |
| 6 | Metadata field values changed (`variables=[]`, `version="1.0.0"`, `is_default=True`) | 3 tests | Update expected values |
| 7 | Latent code bugs (undefined `expected` variable, tautological comparisons) | 2 tests | Fix or delete |

### File-by-File Breakdown

#### File 1: `tests/unit/test_template_seeder.py` (431 lines, 19 tests)
- **14 FAIL, 3 PASS, 2 vacuous**
- Key fixes: Lines 36/43/58/94/111/227/236/302-303 change `== 6` to `== 5`. Lines 118 remove orchestrator KeyError. Lines 160 fix undefined `expected` variable. Lines 180-186 remove 7 obsolete tool name assertions. Lines 347/352/351 update section header and remove phase/checkpoint assertions. Line 359 remove `update_job_status` assertion.

#### File 2: `tests/unit/test_template_seeder_layer_separation.py` (85 lines, 2 tests)
- **2 PASS** -- these test `_get_template_metadata()` and are correct
- BUT: imports `GenericAgentTemplate` at line 6 -- fix import after Phase 1a deletion

#### File 3: `tests/templates/test_template_seeder_messaging_contract.py` (107 lines, 7 tests)
- **5 FAIL, 2 PASS**
- Key fixes: Remove `acknowledge_message` assertions (lines 42, 73). Fix `send_message` presence check for orchestrator section (line 71). Fix broadcast assertion (line 84/87).

#### File 4: `tests/test_template_seeder.py` (403 lines, 18 tests)
- **11 FAIL, 7 PASS**
- Key fixes: Lines 39/46/54/160/173/226/227/232/238/265/288/298 change `== 6` to `== 5`. Line 87 remove orchestrator `scalar_one()` query. Lines 124/128/130 fix metadata values. Line 326 update MCP section header.

#### File 5: `tests/test_enhanced_templates.py` (613 lines, 24 tests)
- **14 FAIL, 10 PASS (3 vacuous)**
- Key fixes: Lines 62/67/72 update behavioral rules assertions for removed MCP rules. Remove orchestrator-specific tests (lines 76, 251). Lines 178/183/186/192 update MCP section assertions. Lines 216-221 remove obsolete tool name assertions. Lines 372 change `== 6` to `== 5`. Lines 404/407 adjust behavioral_rules/success_criteria count thresholds. Line 534 fix `variables` assertion.

#### File 6: `tests/services/test_template_seeder_slimming.py` (248 lines, 16 tests)
- **16 PASS** -- all correct for current slim sections. No changes needed.

#### File 7: `tests/unit/test_context_request_section.py` (223 lines, 13 tests)
- **12 PASS, 1 FAIL**
- Line 106: Test asserts `get_next_instruction` in system_instructions -- replace with `receive_messages`

#### File 8: `tests/integration/test_template_seeding_with_context_request.py` (159 lines, 6 tests)
- **5 FAIL, 1 PASS**
- Lines 27/32 change `== 6` to `== 5`. Line 39 update MCP section header. Line 53 remove orchestrator `scalar_one()` query. Line 118 fix logical comparison bug. Line 133 replace `get_next_instruction` with `receive_messages`.

### Strategy

**Recommended approach**: Fix by root cause, not by file:
1. First: Global find-replace `== 6` template count assertions to `== 5` (but verify each -- some test `_get_default_templates_v103()` which returns 6, only seeding returns 5)
2. Second: Remove all orchestrator-specific `scalar_one()` queries (orchestrator not seeded)
3. Third: Update MCP section assertions for current slim format
4. Fourth: Remove obsolete tool name assertions
5. Fifth: Fix metadata value assertions
6. Sixth: Fix latent bugs (undefined variables, tautological comparisons)
7. Run `pytest tests/unit/test_template_seeder.py tests/test_template_seeder.py tests/test_enhanced_templates.py tests/templates/ tests/unit/test_template_seeder_layer_separation.py tests/unit/test_context_request_section.py tests/integration/test_template_seeding_with_context_request.py tests/services/test_template_seeder_slimming.py tests/services/test_legacy_messaging_cleanup.py -v` to verify

---

## Phase 3: Spawn Prompt Prefix Fix (30 min)

**File**: `src/giljo_mcp/thin_prompt_generator.py`
**Method**: `_build_claude_code_execution_prompt()` (lines 1181-1432)

7 bare-name MCP tool references need the `mcp__giljo-mcp__` prefix:

| Line | Current (bare) | Should Be |
|------|---------------|-----------|
| 1211 | `get_agent_mission(job_id=...)` | `mcp__giljo-mcp__get_agent_mission(job_id=...)` |
| 1335 | `get_workflow_status(project_id=...)` | `mcp__giljo-mcp__get_workflow_status(project_id=...)` |
| 1351 | `send_message(to_agents=...)` | `mcp__giljo-mcp__send_message(to_agents=...)` |
| 1355 | `report_progress()` / `send_message()` | Add prefix to both |
| 1368 | `get_orchestrator_instructions(job_id=...)` | `mcp__giljo-mcp__get_orchestrator_instructions(job_id=...)` |
| 1404 | `get_workflow_status()` | `mcp__giljo-mcp__get_workflow_status()` |
| 1411 | `complete_job(job_id=...)` | `mcp__giljo-mcp__complete_job(job_id=...)` |

**Why this matters**: Claude Code presents tools with the `mcp__giljo-mcp__` prefix. The MCP HTTP server exposes bare names, but the client adds the prefix. All other prompt methods (`build_continuation_prompt`, `generate_staging_prompt`, `_build_thin_prompt`, `_generate_thin_prompt`, `build_retirement_prompt`) and `_generate_agent_protocol()` in orchestration_service.py consistently use the full prefix.

**Sub-agents are NOT affected** -- the spawn template inside `Task()` (lines 1279, 1302) already uses the full prefix, and agents receive correctly-prefixed `full_protocol` from `get_agent_mission()`.

---

## Current 22 MCP Tools (Reference)

| Tool | Required Params |
|------|----------------|
| `health_check` | (none) |
| `get_agent_mission` | `job_id` |
| `acknowledge_job` | `job_id`, `agent_id` |
| `report_progress` | `job_id` (optional: `todo_items` array) |
| `complete_job` | `job_id`, `result` |
| `report_error` | `job_id`, `error` |
| `send_message` | `to_agents`, `content`, `project_id`, `from_agent` |
| `receive_messages` | (none required, optional: `agent_id`, `limit`) |
| `list_messages` | (none required) |
| `get_orchestrator_instructions` | `job_id` |
| `spawn_agent_job` | `agent_display_name`, `agent_name`, `mission`, `project_id` |
| `get_workflow_status` | `project_id` |
| `update_agent_mission` | `job_id`, `mission` |
| `update_project_mission` | `project_id`, `mission` |
| `fetch_context` | `product_id` |
| `close_project_and_update_memory` | `project_id`, `summary`, `key_outcomes`, `decisions_made` |
| `write_360_memory` | `project_id`, `summary`, `key_outcomes`, `decisions_made` |
| `create_project` | `name`, `description` |
| `create_task` | `title`, `description` |
| `get_pending_jobs` | `agent_display_name` |
| `generate_download_token` | `content_type` |

`tenant_key` is auto-injected by server via `validate_and_override_tenant_key()`.

**Obsolete (confirmed removed)**: `update_job_status` (internal only), `receive_agent_messages`, `send_agent_message`, `acknowledge_message` (internal only), `update_job_progress`, `get_next_instruction` (never existed).

---

## Success Criteria

- [ ] `src/giljo_mcp/templates/` package deleted, no import errors
- [ ] `export_claude_templates.py` deleted
- [ ] `claude_agent_templates/` folder deleted
- [ ] Dead `_get_template_metadata()` call at line 165 removed
- [ ] All 107 template seeder tests pass (0 failures, 0 vacuous passes)
- [ ] Spawn prompt uses consistent `mcp__giljo-mcp__` prefix
- [ ] `ruff check src/ api/` passes clean
- [ ] `pytest` full suite shows no regressions

## Rollback Plan

Per-file git checkout:
```bash
git checkout HEAD -- src/giljo_mcp/templates/
git checkout HEAD -- export_claude_templates.py
git checkout HEAD -- claude_agent_templates/
git checkout HEAD -- src/giljo_mcp/template_seeder.py
git checkout HEAD -- src/giljo_mcp/thin_prompt_generator.py
git checkout HEAD -- tests/
```

---

## Notable Side Finding (Not in Scope)

**Duplicate template renderer**: Path D filesystem export (`claude_export.py:generate_yaml_frontmatter()`) uses a different, older renderer than Paths A/B/C (`template_renderer.py:render_claude_agent()`). They produce different output for the same templates. This is a consistency gap worth a separate handover but NOT in scope for 0371a.

---

**END OF HANDOVER 0371a**
