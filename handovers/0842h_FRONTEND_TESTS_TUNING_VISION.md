# Handover 0842h: Frontend Tests — Tuning Icon & Vision Analysis Banner

**Date:** 2026-03-27
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** frontend-tester
**Priority:** Medium
**Estimated Complexity:** 1 hour
**Status:** Not Started
**Standalone handover** (follow-up to 0842d deviation #1 — agent incorrectly reported no test framework)
**Depends on:** 0842d (the components to test)

---

## Task Summary

Write Vitest component tests for the two new UI features added in 0842d: the tuning icon on product cards and the vision analysis prompt banner. The 0842d agent skipped tests claiming "no existing test framework setup found" — this was incorrect. The project has Vitest + @vue/test-utils + @pinia/testing fully configured with 105+ existing spec files.

---

## Test Framework (Already Set Up)

- **Run tests**: `cd frontend && npm run test:run`
- **Config**: `frontend/vitest.config.js`
- **Global setup**: `frontend/tests/setup.js` (499 lines — Vuetify stubs, API mocks, WebSocket mocks)
- **Existing tests**: `frontend/tests/unit/`, `frontend/tests/components/`, `frontend/tests/stores/`
- **Coverage**: `npm run test:coverage` (thresholds: 80/80/75/80)

---

## Tests to Write

### File: `frontend/tests/unit/components/ProductCardTuning.spec.js`

Test the tuning icon added to `ProductsView.vue`:

1. **Tune icon renders on every product card** — mount with product list, assert `mdi-tune` icon button exists per card
2. **No dot badge when tuning state is normal** — product with no `tuning_state.pending_proposals` and no stale notification → `v-badge` not visible
3. **Warning dot when proposals pending** — product with `tuning_state.pending_proposals` non-null → `v-badge` visible with `color="warning"`
4. **Info dot when stale** — notification store has `context_tuning` entry for this product → `v-badge` visible with `color="info"`
5. **Click opens ProductDetailsDialog** — click tune icon → dialog opens (or emits the right event)

### File: `frontend/tests/unit/components/VisionAnalysisBanner.spec.js`

Test the analysis banner in `ProductForm.vue`:

1. **Banner renders in edit mode after vision doc upload** — mount ProductForm in edit mode with vision documents → analysis prompt card visible
2. **"Stage Analysis" copies prompt to clipboard** — click button → clipboard contains expected prompt text with product name and ID
3. **"No Thanks" dismisses banner** — click dismiss → banner hidden
4. **Banner reappears on new document upload** — dismiss, upload new doc → banner visible again
5. **Custom instructions textarea renders** — mount in edit mode → `extraction_custom_instructions` textarea visible
6. **Custom instructions value persists** — set text, trigger save → value included in form data

### Key Existing Code to Reference

- **Similar test patterns**: `frontend/tests/unit/components/` — follow the existing mount/wrapper patterns
- **Vuetify stubs**: Defined in `frontend/tests/setup.js` — use them, don't re-declare
- **Pinia testing**: `@pinia/testing` is installed — use `createTestingPinia()` for store injection
- **ProductsView**: `frontend/src/views/ProductsView.vue` — tuning icon at product card action bar
- **ProductForm**: `frontend/src/components/products/ProductForm.vue` — analysis banner + custom instructions

---

## Implementation Plan

1. Read 2-3 existing spec files in `frontend/tests/unit/components/` to match the project's test patterns
2. Write ProductCardTuning tests (5 tests)
3. Write VisionAnalysisBanner tests (6 tests)
4. Run `npm run test:run` — all existing + new tests pass
5. Commit

## Success Criteria

- [ ] 11 new tests across 2 spec files
- [ ] All existing 105+ tests still pass
- [ ] Tests follow existing patterns in `frontend/tests/`
- [ ] No skipped tests

## MANDATORY: Pre-Work Reading

1. `handovers/HANDOVER_INSTRUCTIONS.md` — quality gates, frontend code discipline
2. `frontend/tests/README.md` — test suite documentation
3. Read 2-3 existing spec files for patterns

**Use `frontend-tester` subagent for all implementation.**
