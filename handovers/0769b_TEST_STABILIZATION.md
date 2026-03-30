# 0769b: Test Stabilization

**Series:** 0769 (Code Quality & Fragility Remediation Sprint)
**Phase:** 2 of 7
**Branch:** `feature/0769-quality-sprint`
**Priority:** HIGH — tests must pass before touching components
**Estimated Time:** 3-4 hours

### Reference Documents
- **Audit report:** `handovers/0769_CODE_QUALITY_FRAGILITY_AUDIT.md` (section H2)
- **Project rules:** `CLAUDE.md`, `handovers/HANDOVER_INSTRUCTIONS.md`

### Tracking Files
- **Chain log:** `prompts/0769_chain/chain_log.json`

---

## Context

The test suite has 115 failures and 6 unhandled errors across 23 test files. ALL failures stem from component refactors (setup wizard 0855, StatusBadge, settings cards) not propagated to tests. No tests are testing removed features — they just need updating to match current component APIs.

Additionally, there is a duplicate `frontend/__tests__/` directory that should be removed.

---

## Scope

### Pre-Work: Remove Duplicate Test Directory

Delete `frontend/__tests__/` — it contains 2 test files that duplicate tests in `frontend/tests/`:
- `frontend/__tests__/components/settings/integrations/GitIntegrationCard.spec.js`
- `frontend/__tests__/views/UserSettings.spec.js`

The canonical location is `frontend/tests/`. Verify with `npx vitest run` that removing `__tests__/` doesn't reduce the passing test count.

### Group 1: CreateAdminAccount (9 fails + 6 unhandled errors) — FIX FIRST

**File:** `frontend/tests/unit/views/CreateAdminAccount.spec.js`

**Root cause:** Component uses `confirmPasswordField.value.validate()` and `step2Form.value.validate()` which are null/undefined in test environment. Vuetify form ref mocking is missing.

**Fix:** Add proper Vuetify form/field ref mocks with `validate()` stubs. The component at `frontend/src/views/CreateAdminAccount.vue` uses template refs for form validation — the test's Vuetify stubs need to provide mock `validate()` functions.

**Priority:** Highest — the 6 unhandled errors from this file can cause false positives across the entire suite.

### Group 2: StatusBadge (17 fails)

**File:** `frontend/tests/unit/components/StatusBadge.spec.js`

**Root cause:** Component was refactored from a v-menu with actions to a simple v-chip. Tests reference `availableActions` (removed) and expect `statusColor` = `'success'` but component now uses hex colors.

**Fix:** Read the current `StatusBadge.vue` component, then rewrite tests to match the chip-based API. Do NOT try to patch the old tests — rewrite them.

### Group 3: Setup Wizard (20 fails across 4 files)

**Files:**
- `frontend/tests/unit/components/setup/SetupStep3Commands.spec.js` (9 fails)
- `frontend/tests/unit/composables/useMcpConfig.spec.js` (5 fails)
- `frontend/tests/unit/components/setup/SetupStep2Connect.spec.js` (4 fails)
- `frontend/tests/unit/components/setup/SetupWizardOverlay.spec.js` (2 fails)

**Root cause:** Setup wizard was redesigned in handover 0855e. Tests expect old UI text/structure (e.g., `'Install the GiljoAI CLI integration'`, `'Copy to Clipboard'`, `'Fetching bootstrap prompt'`).

**Fix:** Read each current component, update expected text strings and DOM structure to match. The components are at `frontend/src/components/setup/`.

### Group 4: Vuetify Stub Depth (20 fails across 2 files)

**Files:**
- `frontend/tests/unit/components/products/DeletedProductsRecoveryDialog.spec.js` (16 fails)
- `frontend/tests/unit/components/products/ProductDetailsDialog.spec.js` (4 fails)

**Root cause:** Vuetify stubs are too shallow — rendered HTML no longer contains expected text. Stubs don't pass through slot content.

**Fix:** Either switch to mounting with a real Vuetify instance or use deeper stubs that pass through content. Check how other passing tests in the project handle Vuetify dialogs.

### Group 5: Settings Integration Cards (17 fails across 4 files)

**Files:**
- `frontend/tests/unit/components/settings/integrations/GitIntegrationCard.spec.js` (7 fails)
- `frontend/tests/unit/components/settings/tabs/NetworkSettingsTab.spec.js` (5 fails)
- `frontend/tests/unit/components/settings/integrations/McpIntegrationCard.spec.js` (4 fails)
- `frontend/tests/unit/components/settings/integrations/SerenaIntegrationCard.spec.js` (1 fail)

**Root cause:** String literal mismatches from UI copy updates. E.g., tests expect `'Git + 360 Memory'` but component renders `'Git + GiljoAI 360 Memory'`.

**Fix:** Read each current component, update expected strings. These are mostly simple text replacements.

### Group 6: View/Tab Refactors (17 fails across 6 files)

**Files:**
- `frontend/tests/unit/views/UserSettings.handover0028.spec.js` (8 fails)
- `frontend/tests/integration/product_ui_refactor.spec.js` (4 fails)
- `frontend/tests/unit/views/ProjectsView.deleted-projects.spec.js` (2 fails)
- `frontend/tests/unit/views/TasksView.spec.js` (1 fail)
- `frontend/tests/views/ProjectsView.spec.js` (1 fail)
- `frontend/tests/views/ProjectsViewTaxonomy.spec.js` (1 fail)

**Root cause:** Tab order changes, state management changes, rendering structure changes.

**Fix:** Read each component, update tab order expectations, selectors, and state assertions.

### Group 7: Project Component Refactors (13 fails across 4 files)

**Files:**
- `frontend/tests/components/projects/ProjectReviewModal.spec.js` (8 fails)
- `frontend/tests/components/projects/ProjectTabs.spec.js` (2 fails)
- `frontend/tests/components/projects/AgentMissionEditModal.spec.js` (2 fails)
- `frontend/tests/unit/components/projects/JobsTab.0829.spec.js` (1 fail)

**Root cause:** Modal/tab behavior changes, StatusBadge review actions moved, selectors changed.

**Fix:** Read each component, update selectors and event assertions.

---

## Agent Protocols (MANDATORY)

### Rejection Authority
You have freedom to reject any audit proposal if you find the application already has valid reasoning or a sound current implementation. Do NOT blindly fix things. If a test was intentionally skipped, if a component API change makes old tests irrelevant, or if the audit's understanding was wrong — document your reasoning in the chain log `deviations` field and move on.

### Flow Investigation
Before changing ANY test, investigate the component it tests — upstream and downstream. Understand WHY the component changed and what the current behavior is. Do not just pattern-match old assertions to new HTML — understand the intent. If you discover a test failure reveals an actual component BUG (not just a test-component mismatch), STOP and set your status to `blocked` in the chain log so the orchestrator can decide whether to fix the component or update the test.

---

## What NOT To Do

- Do NOT refactor or modify any production component code — only test files
- Do NOT delete tests that test valid current behavior — update them
- Do NOT add new test coverage — just stabilize existing tests
- Do NOT fix the 28 oversized test files — that is housekeeping for later
- Do NOT touch backend Python code

---

## Acceptance Criteria

- [ ] `frontend/__tests__/` directory removed
- [ ] `npx vitest run` shows 0 failures and 0 unhandled errors
- [ ] Total passing tests >= 1,792 (current passing count, must not decrease)
- [ ] No test uses `it.skip`, `describe.skip`, or `test.skip`

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0769_chain/chain_log.json`
- Check `orchestrator_directives` — if STOP, halt immediately
- Review 0769a's `notes_for_next` for any changed function signatures or new exceptions

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Work through Groups 1-7 in order. Run `npx vitest run` after each group to verify progress.

### Step 4: Update Chain Log
Update your session with all fields. In `notes_for_next`, include:
- Final test count (pass/fail/error)
- Any components whose test expectations reveal API changes that downstream phases should know about

### Step 5: STOP
Do NOT spawn the next terminal. Commit chain log update and exit.
