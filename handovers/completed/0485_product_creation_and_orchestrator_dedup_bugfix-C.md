# Handover: Product Creation UI Reset & Orchestrator Dedup Bugfix

**Date:** 2026-02-05
**From Agent:** Orchestrator (diagnostic session)
**To Agent:** tdd-implementor (Bug A frontend), backend-integration-tester (Bug B backend)
**Priority:** High
**Estimated Complexity:** 2-3 hours
**Status:** Ready for Implementation

---

## Task Summary

Fix two critical bugs discovered during 0700 cleanup series testing. Neither bug was introduced by 0700 -- both are pre-existing issues that 0700 testing surfaced.

**Bug A**: Creating a new product auto-switches the frontend to the empty product, making all tasks/jobs/projects appear to vanish. One-line frontend fix.

**Bug B**: Reactivating a project always creates a new orchestrator instead of finding the existing one. Status filter guard is too narrow. Multi-file backend fix.

**Diagnostic report**: `handovers/0700_series/bug_diagnostic_report.md`

---

## Context and Background

- Bug A reported by user during alpha testing: "created a product and everything disappeared"
- Bug B reported by user: "reactivated project and got a new orchestrator"
- Full root cause analysis completed by 3 parallel deep-researcher agents
- Both bugs confirmed as pre-existing (not 0700-introduced)
- Bug B already documented in tech debt (commit `5a59c4d7`)

---

## Technical Details

### Bug A: Product Creation UI Reset

**Root cause**: `frontend/src/stores/products.js:177` -- `createProduct()` calls `setCurrentProduct(response.data.id)` after creation, switching the UI to view the new empty product.

**Files to modify**:
1. `frontend/src/stores/products.js` -- Remove auto-switch in `createProduct()`

**Change**:
```javascript
// BEFORE (line 177):
await setCurrentProduct(response.data.id)

// AFTER: Remove this line entirely. Product is added to list but UI stays on current product.
```

### Bug B: Orchestrator Dedup on Reactivation

**Root cause**: `src/giljo_mcp/services/project_service.py:1150-1161` -- `_ensure_orchestrator_fixture()` only checks `status.in_(["waiting", "working"])`. Completed/failed/cancelled orchestrators are invisible.

**Files to modify**:
1. `src/giljo_mcp/services/project_service.py` -- Expand status filter in `_ensure_orchestrator_fixture()` (line ~1158)
2. `src/giljo_mcp/thin_prompt_generator.py` -- Expand same status filter (line ~212)
3. `src/giljo_mcp/services/project_service.py` -- Add dedup guard in `launch_project()` (line ~1916)

**Design decision**: When a completed orchestrator is found on reactivation, leave it as `"complete"`. User can re-stage explicitly. Do NOT auto-reset status.

**Change for _ensure_orchestrator_fixture**:
```python
# BEFORE (line ~1158):
AgentExecution.status.in_(["waiting", "working"])

# AFTER - use exclusion list (more robust against new statuses):
~AgentExecution.status.in_(["failed", "cancelled"])
```

This keeps orchestrators in `"waiting"`, `"working"`, `"complete"`, and `"blocked"` status visible to the dedup check.

**Change for launch_project**: Add an existence check before creating a new orchestrator, similar to the fixture pattern.

---

## Implementation Plan

### Phase 1: Bug A -- Frontend Fix (tdd-implementor)
1. Write test: verify `currentProductId` does NOT change after `createProduct()`
2. Remove `await setCurrentProduct(response.data.id)` from `createProduct()` in `products.js:177`
3. Verify existing tests still pass
4. Optional: add success feedback (console log or event) so calling code knows product was created

### Phase 2: Bug B -- Backend Fix (backend-integration-tester)
1. Write test: activate project with completed orchestrator, verify no new orchestrator created
2. Write test: activate project with failed orchestrator, verify new orchestrator IS created (failed = should retry)
3. Expand status filter in `_ensure_orchestrator_fixture()`
4. Write test: staging flow with completed orchestrator, verify no duplicate
5. Expand status filter in `ThinClientPromptGenerator.generate()`
6. Write test: `launch_project()` with existing orchestrator, verify no duplicate
7. Add dedup guard to `launch_project()`
8. Run full test suite to verify no regressions

### Phase 3: Verification
1. Run `pytest tests/` -- all tests pass
2. Run `cd frontend && npm run build` -- no build errors

---

## Testing Requirements

**Unit Tests (Bug A)**:
- `test_create_product_does_not_switch_current_product` -- verify store state unchanged
- `test_create_product_adds_to_list` -- verify product appears in products array

**Unit Tests (Bug B)**:
- `test_activate_project_with_completed_orchestrator_no_duplicate`
- `test_activate_project_with_failed_orchestrator_creates_new`
- `test_activate_project_with_working_orchestrator_no_duplicate`
- `test_staging_with_completed_orchestrator_no_duplicate`
- `test_launch_project_with_existing_orchestrator_no_duplicate`

**Integration Tests**:
- `test_deactivate_reactivate_cycle_single_orchestrator`
- `test_continue_project_no_duplicate_orchestrator`

---

## Dependencies and Blockers

**Dependencies**: None -- both bugs are independent and can be fixed in parallel.

**Known related issues** (do NOT fix in this handover):
- `skip-bug-001`: UnboundLocalError `total_jobs` at project_service.py:1545
- `skip-bug-002`: Validation bug in complete endpoint
- `skip-bug-003`: Service fallback methods without tenant filtering

---

## Success Criteria

- [ ] Bug A: Creating a product does not change `currentProductId` in the frontend store
- [ ] Bug B: Reactivating a project with a completed orchestrator does not create a new one
- [ ] Bug B: `launch_project()` checks for existing orchestrator before creating
- [ ] Bug B: `ThinClientPromptGenerator.generate()` status filter aligned
- [ ] All new tests pass
- [ ] All existing tests still pass
- [ ] No frontend build errors

---

## Rollback Plan

Both changes are isolated and low-risk:
- Bug A: Re-add the `setCurrentProduct()` call if product creation UX requires auto-switch
- Bug B: Revert status filter to `["waiting", "working"]` if broader filter causes issues
