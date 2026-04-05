# Handover 0950k: Frontend: God-Component Splits

**Date:** 2026-04-05
**From Agent:** Planning Session
**To Agent:** Next Session (frontend-focused)
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Not Started
**Edition Scope:** CE
**Series:** 0950k of 0950a–0950n — read `prompts/0950_chain/chain_log.json` first

---

## 1. Task Summary

Split every Vue component that exceeds 1000 lines into focused sub-components and composables. The 0950 sprint targets a score of 9.0/10 on the code quality rubric; oversized god-components are the primary reason the "code organisation" dimension falls short on the frontend side. This handover runs in parallel with the backend track (0950g–0950j) because the frontend has zero dependency on backend file structure.

---

## 2. Context and Background

The 0700 cleanup series (Feb 2026) removed ~15,800 lines of accumulated drift. The 0765 audit established a frontend baseline of 1,893 passing Vitest tests with zero skips. The 0950 sprint targets a full 9.0/10 audit score before release. Handover 0950e (hardcoded hex colour sweep) must complete before this handover starts — all styling changes land first so splits do not reintroduce old patterns.

This handover runs on branch `feature/0950-pre-release-quality` alongside the backend split track. No coordination with backend sessions is required; they operate on completely separate files.

**Critical agent rules — read before touching any file:**
- Before deleting ANY code: verify zero upstream/downstream references using grep across `frontend/src/`
- Tests that fail must be fixed or deleted — never skip
- No commented-out code — delete it
- Commit with descriptive message prefixed `cleanup(0950k):`
- Update chain log session entry at `prompts/0950_chain/chain_log.json` before stopping
- Do NOT spawn the next terminal — orchestrator handles that
- Read `orchestrator_directives` in chain log FIRST before starting work

---

## 3. Technical Details

### Scope

- `frontend/src/views/` — all `.vue` files
- `frontend/src/components/` — all `.vue` files (including subdirectories)

### Design system conventions (non-negotiable on all extracted components)

Every extracted component and composable must conform to the following. Read `frontend/design-system-sample-v2.html` in a browser before doing any styling work.

- **Smooth borders:** Use `.smooth-border`, `.smooth-border-2`, or `.smooth-border-accent` CSS classes on rounded cards, chips, and pill buttons. Never use a CSS `border` property on a rounded element.
- **Design tokens:** Use `var(--agent-*-primary)` or `getAgentColor()` from `agentColors.js` for agent colours. Never hardcode hex values.
- **Dialog anatomy:** All modals use `.dlg-header` / `.dlg-footer` from `main.scss`. Never use `v-card-title` or `v-card-actions` for dialog chrome.
- **Text accessibility:** `--text-muted` is `#8895a8`. Never use Vuetify's `text-medium-emphasis` class — use a scoped CSS class.
- **Agent badges:** Use `.agent-badge-sq` (tinted initials) for agent-specific contexts; `Giljo_YW_Face.svg` for generic branding.

### Files to create

| File | Purpose |
|------|---------|
| `frontend/src/composables/<name>.js` | Extracted reactive logic (one composable per coherent concern) |
| `frontend/src/components/<dir>/<SubComponent>.vue` | Extracted sub-components (same directory as their parent) |
| `frontend/src/composables/<name>.spec.js` | Vitest unit tests for each new composable |

### Files to modify

| File | Change |
|------|--------|
| Each oversized parent `.vue` | Replace extracted sections with imports and `<SubComponent />` usage |

---

## 4. Implementation Plan

### Step 1: Identify oversized components

Run this to find every `.vue` file over 1000 lines and review the list:

```bash
find /media/patrik/Work/GiljoAI_MCP/frontend/src -name "*.vue" -exec wc -l {} + | sort -n | tail -20
```

Record each file path and line count in the chain log under `tasks_completed` as you work through them.

### Step 2: For each oversized component (TDD workflow)

Work through each file in descending line-count order (largest first):

**a. Read the component in full.** Identify:
- Coherent blocks of reactive state + methods that belong together (composable candidates)
- Large template sections with their own local state (sub-component candidates)
- Emits, props, and inject/provide contracts that will need to cross the boundary

**b. Write the Vitest test FIRST** (TDD — test must fail initially):
- Create `frontend/src/composables/<name>.spec.js`
- Test the composable's PUBLIC interface only (inputs in, outputs out, side effects via mocks)
- Use descriptive names: `test_composable_returns_empty_list_when_no_jobs_present`
- Run `cd frontend && npx vitest run composables/<name>.spec.js` — confirm it fails

**c. Extract the composable** to `frontend/src/composables/<name>.js`:
- Re-run the test — must now pass
- If the composable relies on Pinia store, inject the store inside the composable using `useStore()`
- Do not pass the store as a parameter — that leaks internal store names into the caller

**d. Extract sub-components** to `frontend/src/components/<dir>/<SubComponent>.vue`:
- Each extracted component must declare its own props and emits
- Before deleting the original block: `grep -rn "ComponentName\|function_name" frontend/src/` — zero matches elsewhere means safe to delete
- No commented-out code in the extraction — delete superseded lines

**e. Update the parent component** to import and use the extracted pieces:
- Use `<SubComponent v-bind="relevantProps" @event="handler" />` patterns
- Keep the parent under 1000 lines after extraction

### Step 3: Re-run full test suite

```bash
cd /media/patrik/Work/GiljoAI_MCP/frontend && npx vitest run
```

All tests must pass. If any test references a now-moved symbol: fix the import path, do not skip.

### Step 4: Build verification

```bash
cd /media/patrik/Work/GiljoAI_MCP/frontend && npm run build
```

Must produce a clean build. Resolve any tree-shaking or missing-export warnings.

### Step 5: Commit

```bash
git add frontend/src/
git commit -m "cleanup(0950k): split god-components — <list of components split>"
```

---

## 5. Testing Requirements

### New composable tests (`frontend/src/composables/*.spec.js`)

- Written BEFORE extraction (TDD)
- Cover the composable's public API
- Target >= 80% line coverage on each composable
- Mock Pinia stores using `@pinia/testing` createTestingPinia
- Mock API calls using the existing vi.mock pattern from `frontend/tests/setup.js`

### Existing tests

- All 1,893 existing tests must continue to pass
- Zero new skips introduced
- If an existing test breaks because of a moved symbol, fix the import path in the test

### Manual verification

After extraction, visually confirm in the browser (dev server) that each affected view renders correctly and that all user interactions still work.

---

## 6. Dependencies and Blockers

**Must complete first:**
- 0950e (hardcoded hex colour sweep) — ensures all styling is token-based before splits land

**Can run in parallel with:**
- 0950g, 0950h, 0950i, 0950j (backend split track) — no shared files

**Known blockers:** None anticipated. If a component uses a dynamic `import()` in a way that prevents static analysis, note it in the chain log and proceed.

---

## 7. Success Criteria

- No Vue component in `frontend/src/` exceeds 1000 lines
- Every new composable has a `.spec.js` test file at >= 80% coverage
- `cd frontend && npx vitest run` passes with >= 1893 tests, zero skips
- `cd frontend && npm run build` produces a clean build
- All extracted components conform to design system conventions (smooth borders, design tokens, dlg-header/dlg-footer, WCAG AA text)
- No hardcoded hex colour values introduced during extraction

---

## 8. Rollback Plan

```bash
git checkout -- frontend/src/
```

This handover touches only `frontend/src/`. No backend files, no migrations, no config changes.

---

## 9. Additional Resources

- Design system reference: `frontend/design-system-sample-v2.html` (open in browser)
- Existing composables for style reference: `frontend/src/composables/`
- Vitest setup and mocks: `frontend/tests/setup.js`
- Design tokens: `frontend/src/styles/design-tokens.scss` and `frontend/src/utils/agentColors.js`
- Color utility: `frontend/src/utils/colorUtils.js` (`hexToRgba()`)

---

## Chain Execution Instructions (Orchestrator-Gated v3)

You are **session 0950k** in the 0950 Pre-Release Quality Sprint.

### Step 1: Read Chain Log and Directives

```
Read prompts/0950_chain/chain_log.json
```

Check `orchestrator_directives` for session `0950k`. If it contains "STOP", halt immediately and document the reason. Read `notes_for_next` from any prior session that affects frontend work.

### Step 2: Mark Session Started

Update your session entry in `prompts/0950_chain/chain_log.json`:
```json
"status": "in_progress"
```

### Step 3: Confirm 0950e is Complete

Verify the chain log shows `0950e` as `"status": "complete"` before writing any code.

### Step 4: Execute

Work through the implementation plan above. Use the `ux-designer` and `frontend-tester` subagent profiles for complex component splits.

### Step 5: Update Chain Log Before Stopping

Update your session entry with:
- `tasks_completed`: list each component split (file path, lines before, lines after)
- `deviations`: any components that could not be split below 1000 lines and why
- `blockers_encountered`: any issues hit during extraction
- `notes_for_next`: exact composable names, file paths, and any patterns 0950l should know about for coverage gaps
- `cascading_impacts`: any component or composable that 0950l's test sweep needs to pick up
- `summary`: 2-3 sentences including commit hash
- `status`: "complete"

### Step 6: Commit and STOP

```bash
git add frontend/src/
git commit -m "cleanup(0950k): split god-components — all Vue files under 1000 lines"
git add prompts/0950_chain/chain_log.json
git commit -m "docs: 0950k chain log — session complete"
```

**Do NOT spawn the next terminal.** The orchestrator reviews the chain log and spawns 0950l when both 0950j and 0950k are complete.
