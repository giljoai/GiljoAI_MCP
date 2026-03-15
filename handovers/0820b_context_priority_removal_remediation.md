# Handover 0820b: Context Priority Removal -- Audit Remediation

**Date:** 2026-03-15
**From Agent:** Audit session
**To Agent:** Fresh session (no prior context)
**Priority:** High
**Estimated Complexity:** 2-3 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Handover 0820 removed the CRITICAL/IMPORTANT/REFERENCE priority framing system across 53 files (-5,698 net lines). A 4-agent audit found 1 CRITICAL, 4 HIGH, and 11 MEDIUM issues: a data compatibility bug, toggle normalization gaps, broken tests referencing deleted features, and stale documentation. This handover fixes all of them.

**Parent handover:** 0820 (Remove Context Priority Framing) -- COMPLETE, archived at `handovers/completed/0820_remove_context_priority_framing-C.md`

---

## Phase 1: Backend Data Compatibility (CRITICAL + HIGH)

### Fix 1 (CRITICAL): Normalize legacy data in API endpoint

**File:** `api/endpoints/users.py`
**Problem:** The `FieldPriorityConfig` Pydantic validator (lines 149-197) rejects v2.0 stored data (integer priorities like `{"product_core": 1, "vision_documents": 2}`). Users with old configs get a 500 on `GET /me/field-priority`.
**Fix:** In the `get_field_priority_config` endpoint (line 617), normalize the config dict before constructing the Pydantic model. Import and use `_normalize_field_toggles` from `protocol_builder.py` to convert any legacy integers to `{"toggle": bool}` dicts. The normalizer already handles integers (`value < 4` = enabled). Apply normalization to the `priorities` sub-dict before returning.

### Fix 2 (HIGH): Normalize toggle dicts in prompts.py

**File:** `api/endpoints/prompts.py`
**Lines:** 177, 382
**Problem:** Both `generate_prompt` and `generate_staging_prompt` extract raw `user_field_config.get("priorities", {})` which yields nested dicts like `{"product_core": {"toggle": True}}`. These flow to `ThinClientPromptGenerator.generate()` without flattening. A category with `{"toggle": False}` evaluates as truthy (non-empty dict), so disabled categories get included.
**Fix:** After extracting `field_toggles`, normalize to flat booleans:
```python
field_toggles = {k: (v.get("toggle", True) if isinstance(v, dict) else bool(v)) for k, v in field_toggles.items()}
```
Apply this at both line 177 and line 382.

### Fix 3 (HIGH): Same normalization in project_service.py

**File:** `src/giljo_mcp/services/project_service.py`
**Lines:** 2021-2023
**Problem:** Same raw nested dict extraction stored into `job_metadata["field_toggles"]` without normalization.
**Fix:** Same flattening pattern as Fix 2, applied after `field_toggles = user.field_priority_config.get("priorities", {})` at line 2023.

### Fix 4 (HIGH): Add fallback for old job_metadata key

**File:** `src/giljo_mcp/services/orchestration_service.py`
**Line:** 2493
**Problem:** `metadata.get("field_toggles", {})` returns empty dict for pre-0820 jobs that stored under `"field_priorities"`.
**Fix:** Change to `metadata.get("field_toggles", metadata.get("field_priorities", {}))`.

### Fix 5 (MEDIUM): Stale docstring

**File:** `src/giljo_mcp/services/user_service.py`
**Line:** 1142
**Fix:** Change `"priority_config_updated"` to `"toggle_config_updated"` in the docstring example.

### Fix 6 (MEDIUM): Stale comment

**File:** `src/giljo_mcp/thin_prompt_generator.py`
**Line:** 596
**Fix:** Change `"field priorities"` to `"field toggles"`.

**Run after Phase 1:** `pytest tests/ -x --tb=short -k "not test_auth_org and not test_user_service_crud"` (the excluded tests have pre-existing bcrypt/Python 3.14 failures unrelated to 0820).

---

## Phase 2: Backend Test Fixes

### Fix 7 (HIGH): Delete stale depth_config test

**File:** `tests/services/test_depth_config_standardization.py`
**Lines:** 151-168
**Problem:** `test_frontend_test_spec_uses_vision_documents` asserts `ContextPriorityConfig.vision.spec.js` exists. That file was intentionally deleted in 0820.
**Fix:** Delete this test method entirely. The remaining tests in the class are still valid.

### Fix 8 (MEDIUM): Fix framing-based context test

**File:** `tests/services/test_orchestration_service_instructions.py`
**Line:** 97
**Problem:** `assert isinstance(result["context_fetch_instructions"], dict)` fails because `_build_fetch_instructions()` now returns a `list[dict]`. Test name references "framing based context".
**Fix:** Change `dict` to `list`. Rename test to `test_returns_toggle_based_context`. Update docstring.

### Fix 9 (MEDIUM): Fix test data types in thin_prompt tests

**File:** `tests/services/test_thin_client_prompt_generator_agent_templates_core.py`
**Lines:** 58-60, 130, 228, 232
**Problem:** Tests use integer format `{"agent_templates": 2}` instead of v3.0 toggle format. They pass by coincidence.
**Fix:** Change to proper v3.0 format: `{"priorities": {"agent_templates": {"toggle": True}, ...}, "version": "3.0"}` and extract `["priorities"]` when passing as `field_toggles`.

**Run after Phase 2:** `pytest tests/ -x --tb=short -k "not test_auth_org and not test_user_service_crud"`

---

## Phase 3: Frontend Test Fixes

### Fix 10 (HIGH): Delete broken UserSettings priority test block

**File:** `frontend/tests/views/UserSettings.spec.js`
**Lines:** 66-380 (the entire `'Context Priority Management (Handover 0052)'` describe block)
**Problem:** References `wrapper.vm.priority1Fields`, `unassignedFields`, `removeField()`, `ALL_AVAILABLE_FIELDS`, `fieldToggleHasChanges`, `saveFieldToggle()` -- none exist on the component anymore.
**Fix:** Delete the entire describe block. The P1/P2/P3 bucket UI is gone; these tests are dead.

### Fix 11 (MEDIUM): Clean up selector validation files

**File 1:** `frontend/tests/e2e/selector-validation.spec.ts`
- Lines 259-282: Delete the `'ContextPriorityConfig - priority-* dynamic selectors exist'` test.
- Lines 456-477: In `'ContextPriorityConfig selectors appear in context tab'`, remove the `priority-*` assertion (keep `depth-*`).

**File 2:** `frontend/selector-validation.test.js`
- Lines 244-275: Delete the `'ContextPriorityConfig: Dynamic priority-* selectors exist'` test.

**File 3:** `frontend/validate-selectors.js`
- Lines 115-123: Delete the `priority-* (dynamic)` selector entry (keep `depth-*`).

### Fix 12 (MEDIUM): Remove ESLint ignore

**File:** `frontend/eslint.config.js`
**Line:** 24
**Fix:** Remove `'src/components/settings/ContextPriorityConfig.vue'` from the ignores array. Run `npx eslint src/components/settings/ContextPriorityConfig.vue` and fix any lint errors.

### Fix 13 (MEDIUM): Rename data-testid

**File:** `frontend/src/components/settings/ContextPriorityConfig.vue`
**Line:** 9
**Fix:** Change `data-testid="reset-context-priority-btn"` to `data-testid="reset-context-config-btn"`. Update any test files that reference the old testid.

**Run after Phase 3:** `cd frontend && npm run test -- --run` (expect pre-existing failures from other handovers, but zero NEW failures from these changes).

---

## Phase 4: Documentation Cleanup

### Fix 14 (MEDIUM): Deep-clean ORCHESTRATOR_CONTEXT_FLOW_SSoT.md

**File:** `docs/architecture/ORCHESTRATOR_CONTEXT_FLOW_SSoT.md`
**Problem:** ~64 stale priority references with full code examples showing Priority 0-10 scale, `_extract_tech_stack(priority: int)`, tiered extraction logic. Key stale sections: lines 30-51 (old priority table), 68-72 (drag-between-levels UI), 196-325 (tech_stack priority extraction), 341-439 (agent templates priority), 457-553 (360 Memory priority), 587-695 (Git/Serena priority), 741-817 (codebase summary priority), 956-965 (priority comparison table), 1000-1100 (ASCII diagrams), 1265-1395 (DB schema examples).
**Fix:** Replace priority-integer code examples with the toggle-based equivalents. Replace "priority levels" language with "toggle + depth" language throughout. The fetch pattern is now: `if toggle_enabled: fetch(depth=user_depth_config)`.

### Fix 15 (MEDIUM): Update 4 missed doc files

- `docs/SERVICES.md` line 24: Update method descriptions to reflect toggle semantics.
- `docs/architecture/service_response_models.md` lines 91-93: Update signatures and remove stale `{"success": True}` format.
- `docs/guides/SELECTOR_TEST_EXAMPLES.md` lines 454-528+: Replace priority selector examples with toggle/depth test patterns.
- `docs/guides/SELECTOR_TEST_GUIDE.md` lines 215-265, 440-488: Replace priority selector docs with toggle-based selectors.

### Fix 16 (MEDIUM): Fix Simple_Vision.md leftover

**File:** `handovers/Reference_docs/Simple_Vision.md`
**Line:** 454
**Fix:** Change "context priority configurator" to "context configuration".

**Run after Phase 4:** Grep verification:
```bash
grep -r "priority.*framing\|CRITICAL.*IMPORTANT.*REFERENCE\|inject_priority_framing\|apply_rich_entry_framing\|build_framed_context_response\|build_priority_excluded_response" src/ api/ frontend/src/ --include="*.py" --include="*.js" --include="*.vue"
```
Should return zero results.

---

## Verification Checklist

- [ ] `pytest tests/ -x --tb=short` -- no new failures
- [ ] `cd frontend && npm run test -- --run` -- no new failures
- [ ] Grep for orphaned priority framing references returns zero
- [ ] All 16 fixes applied and committed
