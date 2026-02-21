# Handover 0440d: Taxonomy Production Hardening

**Date:** 2026-02-21
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Ready
**Series:** 0440 (Project Organization)
**Depends On:** 0440a (DB/Backend), 0440b (Frontend UI), 0440c (Display Integration) - all complete

---

## Task Summary

Harden the 0440c taxonomy inline row implementation to commercial SaaS production quality. A deep audit identified 3 CRITICAL, 5 HIGH, and several MEDIUM issues across backend validation, frontend race conditions, and test coverage gaps. The data layer (DB constraints, tenant isolation) is solid; the validation, error handling, and async logic are not.

---

## Context and Background

Handovers 0440a-c built a project taxonomy system (Type + Serial Number + Suffix = alias like "FEAT-0440c") with:
- Database schema with `uq_project_taxonomy` unique constraint (NULLS NOT DISTINCT)
- CRUD endpoints for project types
- Inline taxonomy row in project create/edit dialog
- Real-time serial number validation with debounced API calls
- Smart suffix dropdown that filters already-used letters
- Taxonomy chips, type filters, and series-aware sorting in the project list

The implementation works functionally but has validation gaps, race conditions, and missing error handling that would cause user-facing issues in production.

---

## Findings (From Audit)

### CRITICAL

| ID | Issue | File | Impact |
|----|-------|------|--------|
| C-1 | Deleted projects block taxonomy namespace | `crud_ops.py:301-371` | User sees "taken" for series owned by trashed projects |
| C-2 | Zero server-side validation on `subseries` and `series_number` | `crud.py:301-350` | Any string accepted as suffix, negative numbers as serial |
| C-3 | TOCTOU race on save shows raw DB IntegrityError to user | `ProjectsView.vue` + `project_service.py` | Cryptic error when two users claim same series simultaneously |

### HIGH

| ID | Issue | File | Impact |
|----|-------|------|--------|
| H-1 | No AbortController on debounced API calls | `ProjectsView.vue:861-914` | Stale responses overwrite fresh state during fast typing |
| H-2 | `seriesCheckTimer` not cleared on unmount | `ProjectsView.vue:788` | Leaked API calls after navigation |
| H-3 | Dialog opens before `usedSubseries` fetch resolves | `ProjectsView.vue:1168-1179` | Suffix dropdown flashes all 26 letters then snaps |
| H-4 | Clearing type while API in-flight overwrites cleared state | `ProjectsView.vue:827-839` | Check/X icons appear when no type selected |
| H-5 | No `response_model` on 4 taxonomy endpoints | `crud.py:265-350` | Unvalidated/undocumented API responses |

---

## Technical Details

### Files to Modify

**Backend (3 files):**

1. **`api/endpoints/project_types/crud_ops.py`**
   - C-1: Add `Project.status != 'deleted'` filter to `check_series_available()`, `get_used_subseries()`, `get_next_series_number()`, `get_available_series_numbers()`
   - C-2: Add input validation: `series_number >= 1`, `subseries` must match `^[a-z]$`

2. **`api/endpoints/projects/crud.py`**
   - C-2: Add `Field` validation on query params: `series_number = Query(ge=1, le=9999)`, `subseries = Query(pattern=r"^[a-z]$")`
   - H-5: Add Pydantic `response_model` to `/check-series`, `/used-subseries`, `/next-series`, `/available-series`

3. **`src/giljo_mcp/services/project_service.py`** (or wherever `create_project`/`update_project` catch exceptions)
   - C-3: Catch `IntegrityError` on the `uq_project_taxonomy` constraint specifically, raise user-friendly error: "This taxonomy combination (FEAT-0440c) is already in use"

**Frontend (1 file):**

4. **`frontend/src/views/ProjectsView.vue`**
   - H-1: Add `AbortController` to `checkSeriesAvailability` - abort previous request when new one starts
   - H-2: Add `onBeforeUnmount` hook to clear `seriesCheckTimer` and abort any in-flight controller
   - H-3: In `editProject()`, await `usedSubseries` fetch before opening dialog, or show loading indicator on suffix dropdown
   - H-4: In `checkSeriesAvailability` response handler, guard against stale responses by checking `projectData.value.project_type_id` still matches the request's type

**Tests (2 files):**

5. **`tests/test_project_taxonomy_display.py`** (backend)
   - Add: test deleted projects excluded from availability checks
   - Add: test input validation rejects invalid series_number and subseries
   - Add: test IntegrityError produces user-friendly error message

6. **`frontend/src/views/__tests__/ProjectsViewTaxonomy.spec.js`** (frontend)
   - Add: test `handleTypeChange` resets all taxonomy state including usedSubseries
   - Add: test `resetForm` clears usedSubseries
   - Add: test `onSubseriesChange` triggers re-validation
   - Add: test `taxonomyPrefix` for all edge cases
   - Add: test unmount clears timer (mock clearTimeout)

---

## Implementation Plan

### Phase 1: Backend Validation & Deleted Project Filter (TDD)

**Test first:**
```python
# tests/test_project_taxonomy_display.py
def test_deleted_project_does_not_block_series():
    """Soft-deleted project's series number should be available for reuse"""

def test_check_series_rejects_negative_number():
    """series_number < 1 should return 422"""

def test_check_series_rejects_invalid_subseries():
    """subseries='ZZ' or subseries='1' should return 422"""
```

**Implement:**
1. Add `Project.status != 'deleted'` filter to all 4 functions in `crud_ops.py`
2. Add FastAPI `Query` constraints on `series_number` and `subseries` params
3. Add `response_model` declarations to all 4 taxonomy endpoints
4. Create Pydantic response schemas: `SeriesCheckResponse`, `UsedSubseriesResponse`, `NextSeriesResponse`, `AvailableSeriesResponse`

**Recommended agent:** `tdd-implementor`

### Phase 2: IntegrityError Handling (TDD)

**Test first:**
```python
def test_create_project_taxonomy_conflict_returns_friendly_error():
    """Duplicate taxonomy should raise user-friendly error, not raw IntegrityError"""
```

**Implement:**
1. In `ProjectService.create_project` and `update_project`, catch `IntegrityError` where constraint name contains `uq_project_taxonomy`
2. Raise a domain exception with message: "Taxonomy combination already in use. Please choose a different series number or suffix."
3. Frontend `saveProject` catch block should display this message cleanly (not `alert()`)

**Recommended agent:** `tdd-implementor`

### Phase 3: Frontend Race Condition Fixes

**Implement:**
1. Add `AbortController` ref, abort on each new `checkSeriesAvailability` call
2. Add `onBeforeUnmount` to clear timer + abort controller
3. In `checkSeriesAvailability` response handler, add stale-response guard: `if (projectData.value.project_type_id !== requestedTypeId) return`
4. In `editProject`, either `await` the usedSubseries fetch before `showCreateDialog.value = true`, or set suffix dropdown to loading state until fetch completes

**Recommended agent:** `tdd-implementor`

### Phase 4: Test Coverage + Verification

1. Run `pytest tests/test_project_taxonomy_display.py -v` - all pass
2. Run `cd frontend && npx vitest run src/views/__tests__/ProjectsViewTaxonomy.spec.js` - all pass
3. Manual verification via browser: create dialog, type serial, clear type mid-check, verify no stale state
4. Commit

---

## Cascading Impact Analysis

**Upstream:** None - taxonomy is leaf functionality, no other features depend on it.

**Downstream:** None - taxonomy display in project list (chips, filters, sorting) consumes the same data; no schema changes.

**Sibling:** None - no parallel taxonomy systems exist.

**Installation:** No schema changes. No migration needed. No `install.py` impact.

---

## Success Criteria

- [ ] Deleted projects do not block taxonomy namespace (soft-deleted = available)
- [ ] Invalid `subseries` (not a-z) and `series_number` (< 1 or > 9999) rejected by backend with 422
- [ ] Duplicate taxonomy on save produces clear user-facing message, not raw DB error
- [ ] Fast typing in serial # field does not cause stale state (AbortController in place)
- [ ] Navigating away during pending check does not leak API calls
- [ ] Editing a project pre-loads suffix dropdown correctly (no flash of all 26 letters)
- [ ] Clearing type while check is in-flight does not leave stale validation icons
- [ ] All 4 taxonomy endpoints have `response_model` declarations
- [ ] All new code has tests (TDD: red -> green -> refactor)
- [ ] `pytest tests/test_project_taxonomy_display.py -v` passes
- [ ] `npx vitest run src/views/__tests__/ProjectsViewTaxonomy.spec.js` passes

---

## Rollback Plan

All changes are additive validation/guards. Rollback = `git revert <commit>`. No schema changes, no data migrations.

---

## Items Explicitly NOT in Scope

- Rate limiting on `/check-series` endpoint (MEDIUM - not a correctness issue)
- `type="number"` on serial input field (LOW - cosmetic)
- `__add_custom__` sentinel value refactor (LOW - works correctly)
- Telling user which project owns a taken series number (LOW - nice-to-have)
- Client-side parameter validation before API calls (LOW - backend validates)
