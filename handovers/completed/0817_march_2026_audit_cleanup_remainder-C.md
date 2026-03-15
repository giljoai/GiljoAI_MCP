# Handover 0817: March 2026 Audit Cleanup Remainder

**Date:** 2026-03-14
**From Agent:** Code Cleanup Audit (cleaning_march_14 branch)
**To Agent:** Next Session
**Priority:** Low
**Estimated Complexity:** 30 minutes
**Status:** Complete
**Edition Scope:** CE

## Task Summary

Two small cleanup items remaining from the March 2026 dead code audit. Both are low-risk, frontend-only, and can be done in a single session.

## Item 1: Fix Broken E2E Test Selectors

Three E2E test files reference `data-testid="implement-tab"` which was renamed to `data-testid="jobs-tab"` in the 0411a handover (phase labels). The tests will fail if run.

**Files to fix (find-replace `implement-tab` → `jobs-tab`):**

| File | Occurrences |
|------|-------------|
| `frontend/tests/e2e/implement-tab-workflow.spec.ts` | 8 occurrences (lines 33, 102, 137, 178, 214, 251, 287, 320) |
| `frontend/tests/e2e/multi-tenant-isolation.spec.ts` | 2 occurrences (lines 99, 105) |
| `frontend/tests/e2e/memory-leak-detection.spec.ts` | 8 occurrences (lines 47, 106, 122, 167, 202, 242, 254, 346) |

**Note:** The file `implement-tab-workflow.spec.ts` should also be renamed to `jobs-tab-workflow.spec.ts` to match the current terminology.

**Correct testid confirmed at:** `frontend/src/components/projects/ProjectTabs.vue` line 41: `data-testid="jobs-tab"`

## Item 2: Relocate Co-located Test Files

28 test files are inside `frontend/src/` instead of the conventional `frontend/tests/` directory. This is a convention violation — tests should not ship in the source tree.

**Files to move (28 total):**

```
frontend/src/components/settings/__tests__/ContextPriorityConfig.spec.ts
frontend/src/components/projects/__tests__/AgentJobModal.spec.js
frontend/src/components/settings/ContextPriorityConfig.vision.spec.js
frontend/src/components/__tests__/ProductIntroTour.spec.js
frontend/src/components/__tests__/StartupQuickStart.spec.js
frontend/src/components/__tests__/StatusBadge.spec.js
frontend/src/stores/projectMessagesStore.spec.js
frontend/src/stores/projectStateStore.spec.js
frontend/src/stores/websocket.spec.js
frontend/src/views/__tests__/ProductsView.active-count.spec.js
frontend/src/__tests__/components/LaunchTab-simplified.spec.js
frontend/src/__tests__/components/LaunchTab.spec.js
frontend/src/stores/notifications.spec.js
frontend/src/components/projects/JobsTab.0243c.spec.js
frontend/src/components/projects/JobsTab.integration.spec.js
frontend/src/views/__tests__/ProjectsView.spec.js
frontend/src/stores/agentJobsStore.spec.js
frontend/src/__tests__/accessibility/projects-a11y.spec.js
frontend/src/__tests__/integration/projects-workflow.spec.js
frontend/src/components/projects/JobsTab.a11y.spec.js
frontend/src/components/projects/LaunchTab.test.js
frontend/src/components/projects/__tests__/AgentDisplayName.spec.js
frontend/src/services/api.spec.js
frontend/src/stores/websocketEventRouter.spec.js
frontend/src/views/UserSettings.vision.spec.js
frontend/src/views/__tests__/ProjectsViewTaxonomy.spec.js
frontend/src/stores/websocketEventRouter.0259.spec.js
frontend/src/components/__tests__/TemplateManager.export-status.spec.js
```

**Relocation mapping:**
- `frontend/src/components/**` → `frontend/tests/components/**`
- `frontend/src/stores/**` → `frontend/tests/unit/stores/**`
- `frontend/src/views/**` → `frontend/tests/unit/views/**`
- `frontend/src/services/**` → `frontend/tests/unit/services/**`
- `frontend/src/__tests__/accessibility/**` → `frontend/tests/accessibility/**`
- `frontend/src/__tests__/integration/**` → `frontend/tests/integration/**`
- `frontend/src/__tests__/components/**` → `frontend/tests/components/**`

**Important:** After moving, verify each test still resolves its imports correctly. Tests use `@/` alias which resolves to `frontend/src/`, so import paths should remain valid regardless of test file location.

## Item NOT Included (Corrected)

`categoryFilter` and `showCreateDialog` in TasksView were initially flagged as dead but are **actively used** (template conditionals, computed filtering, mount hooks). No action needed.

## Testing Requirements

- Run `npx vitest run` after relocating test files to confirm all tests still pass
- Run E2E tests (if configured) to confirm testid fix works

## Success Criteria

- All 3 E2E files reference `jobs-tab` instead of `implement-tab`
- All 28 test files moved from `frontend/src/` to `frontend/tests/`
- All tests still pass after relocation

## Implementation Summary

### 2026-03-14 - Completed

**Item 1** -- `6b87f67a`
- Replaced 18 occurrences of `implement-tab` with `jobs-tab` across 3 E2E files
- Renamed `implement-tab-workflow.spec.ts` to `jobs-tab-workflow.spec.ts`

**Item 2** -- `da5fc6d6`
- 26 files relocated via `git mv` to conventional test directories
- 2 files (`websocket.spec.js`, `agentJobsStore.spec.js`) removed -- proper tests already existed at destination with different content
- Created `frontend/tests/unit/services/` and `frontend/tests/unit/accessibility/`
- Cleaned up 6 empty `__tests__/` directories from `frontend/src/`
- Verified: zero import resolution errors (the `@/` alias works regardless of test file location)
- Pre-existing test failures unchanged (not caused by relocation)
