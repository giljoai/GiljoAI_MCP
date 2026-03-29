# Handover 0855f: Setup Wizard — Step 4 (Completion Launchpad) + End-to-End Wiring

**Date:** 2026-03-28
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** ux-designer + tdd-implementor
**Priority:** High
**Estimated Complexity:** 3 hours
**Status:** Not Started
**Series:** 0855a-g (Setup Wizard Redesign)
**Spec:** `handovers/SETUP_WIZARD_REDESIGN.md`

---

## Read First (MANDATORY)

1. `handovers/HANDOVER_INSTRUCTIONS.md` — coding standards, TDD protocol, quality gates
2. `handovers/Reference_docs/QUICK_LAUNCH.txt` — project bootstrap
3. `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md` — agent flow context
4. `handovers/SETUP_WIZARD_REDESIGN.md` — full spec for the wizard redesign

**Search before you build.** Use Serena `find_symbol` / `get_symbols_overview` to check if functionality already exists.

**Brand tokens:** See 0855c handover for the complete design token table.

---

## Task Summary

Build the Step 4 completion launchpad with three "next steps" cards, wire the full overlay lifecycle end-to-end (first login → resume → completion), set `setup_complete: true` on any launchpad action, and delete the old `StartupQuickStart.vue` component with all localStorage references.

---

## Context and Background

Step 4 is the reward — "You're set up!" All 4 steps show green checkmarks. Three cards invite the user to start working: Add Product, Add Project, Add Tasks. Any click sets `setup_complete: true` via the backend PATCH and closes the overlay permanently.

This handover also handles the critical cleanup: removing `StartupQuickStart.vue` (639 lines) and all `giljo_startup_checklist_v1` localStorage references across the codebase.

**What previous handovers provide:**
- 0855a: `PATCH /api/v1/auth/me/setup-state` with `{setup_complete: true, setup_step_completed: 4}`. User store `updateSetupState()` action.
- 0855c: `SetupWizardOverlay.vue` shell with stepper, `mode` prop, dismiss handling
- 0855d: Step 2 component (`SetupStep2Connect.vue`)
- 0855e: Step 3 component (`SetupStep3Commands.vue`)

**Files you'll delete:**
- `frontend/src/components/settings/StartupQuickStart.vue` (639 lines) — the old 6-step localStorage checklist with items: tools, connect, slash, templates, context, integrations
- localStorage key `giljo_startup_checklist_v1` — referenced in `WelcomeView.vue` (line ~103) and `StartupQuickStart.vue` (line ~177)

**Files that import StartupQuickStart:** Grep for `StartupQuickStart` to find all import sites. Known: `frontend/src/views/UserSettings.vue` (startup tab content).

---

## Technical Details

### New Component: `frontend/src/components/setup/SetupStep4Complete.vue`

**Layout:**
- Header: "You're all set!" with success icon
- Subtitle: "Your AI coding tools are connected and ready. Here's what to do next."
- Three cards in a row (responsive: stack on mobile):

| Card | Icon | Title | Body | Button |
|------|------|-------|------|--------|
| Add a Product | `mdi-package-variant-closed` | "Define Your Product" | "Create a product to organize projects, tasks, and agent configurations." | "OPEN PRODUCTS" → `/products` |
| Add a Project | `mdi-folder-open` | "Start a Project" | "Create your first project to begin orchestrating AI agents." | "OPEN PROJECTS" → `/projects` |
| Add Tasks | `mdi-checkbox-marked-outline` | "Track Your Work" | "Add tasks and ideas to your dashboard using /gil_add." | "OPEN TASKS" → `/tasks` |

- Card styling: `#1e3147` background, `smooth-border`, `border-radius: 12px`, icon in yellow-tinted circle
- Button styling: brand yellow primary CTA per card
- Below cards: "Go to Dashboard" link (muted, navigates to `/dashboard`)
- **Any button click:** call `PATCH /me/setup-state` with `{ setup_complete: true, setup_step_completed: 4 }`, then close overlay and navigate

### End-to-End Overlay Lifecycle

Wire in `SetupWizardOverlay.vue`:

1. **Mount:** Read `user.setup_complete` and `user.setup_step_completed` from store
2. **Auto-launch:** If `setup_complete === false`, show overlay. Expand first incomplete step.
3. **Step navigation:** Each step's "Next" advances `setup_step_completed` (PATCH to backend), renders next step
4. **"Do this later" (X button):** Close overlay without setting `setup_complete`. Overlay reopens on next visit.
5. **Resume:** On reopen, expand first incomplete step. Completed steps show collapsed with green checkmark.
6. **Completion:** Step 4 action sets `setup_complete: true`. Overlay never auto-launches again.
7. **Post-completion:** WelcomeView button changes to "How to Use GiljoAI MCP" (wired in 0855c, verified here)

### Cleanup: Delete StartupQuickStart.vue

1. **Delete:** `frontend/src/components/settings/StartupQuickStart.vue` (639 lines)
2. **Remove imports** of StartupQuickStart from:
   - `frontend/src/views/UserSettings.vue` — remove the startup tab content, replace with link to overlay or brief summary
3. **Remove localStorage references:**
   - Search for `giljo_startup_checklist_v1` across entire frontend
   - Remove from `WelcomeView.vue` (the `isChecklistComplete` computed, `showTutorialCta` logic)
   - Remove any `localStorage.getItem/setItem/removeItem` calls for this key
4. **Update UserSettings.vue startup tab:** Replace with a brief "Setup complete" message or a button to reopen the wizard overlay

### Cascading Analysis

- **StartupQuickStart removal:** Check all imports, all route references (`tab=startup`), all emits/events. The UserSettings Startup tab needs replacement content.
- **localStorage cleanup:** Grep for `giljo_startup_checklist` and `checklist` across all frontend files.
- **WelcomeView:** Old CTA logic must be fully replaced by the overlay-based logic from 0855c.

---

## Implementation Plan

### Phase 1: Step 4 Component
1. Build `SetupStep4Complete.vue` with three cards
2. Wire button clicks to PATCH + navigate + close overlay

### Phase 2: End-to-End Lifecycle
1. Wire all 4 steps into overlay stepper with forward/back navigation
2. Implement auto-launch, resume, dismiss, and completion flows
3. Verify state persists across browser refresh (reads from backend via store)

### Phase 3: Cleanup
1. Delete `StartupQuickStart.vue`
2. Remove all localStorage references
3. Update UserSettings startup tab
4. Grep for any remaining dead references

### Phase 4: Testing
1. Write Vitest tests for Step 4 and overlay lifecycle
2. Manual E2E test: fresh user → complete all steps → verify overlay closes → verify button label changes

**Recommended Sub-Agents:** ux-designer (Step 4 cards), tdd-implementor (tests)

---

## Testing Requirements

**Vitest Component Tests:**
- Step 4 renders three cards with correct labels and routes
- Card button click calls PATCH with setup_complete: true
- Card button click navigates to correct route
- Overlay auto-launches when setup_complete === false
- Overlay hidden when setup_complete === true
- Resume expands correct step based on setup_step_completed
- "X" dismiss closes without setting setup_complete

**Cleanup Verification:**
- No references to `StartupQuickStart` in any file
- No references to `giljo_startup_checklist_v1` in any file
- UserSettings startup tab renders without errors

---

## Dependencies and Blockers

**Dependencies:**
- 0855a (PATCH endpoint for setup_complete)
- 0855c (overlay shell)
- 0855d (Step 2 component)
- 0855e (Step 3 component)

**Blockers:** None known.

---

## Success Criteria

- [ ] Step 4 renders with three "next steps" cards
- [ ] Any card action sets `setup_complete: true` and closes overlay
- [ ] Full lifecycle works: auto-launch → resume → complete
- [ ] `StartupQuickStart.vue` deleted, no dead references remain
- [ ] `giljo_startup_checklist_v1` localStorage fully removed
- [ ] UserSettings startup tab updated
- [ ] Vitest tests passing

---

## Rollback Plan

Restore `StartupQuickStart.vue` from git, revert WelcomeView and UserSettings changes.

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/components/setup/SetupStep4Complete.vue` | **New** — completion launchpad |
| `frontend/src/components/setup/SetupWizardOverlay.vue` | Full lifecycle wiring |
| `frontend/src/views/WelcomeView.vue` | Remove old checklist logic |
| `frontend/src/views/UserSettings.vue` | Remove StartupQuickStart import, update tab |
| `frontend/src/components/settings/StartupQuickStart.vue` | **Delete** |
| `frontend/tests/` | New spec files, remove old StartupQuickStart tests if any |

---

## Chain Execution Instructions (Orchestrator-Gated v3)

You are session 6 of 7 in the 0855 chain. You are on branch `feature/0855-setup-wizard`.

### Step 1: Read Chain Log
Read `prompts/0855_chain/chain_log.json`
- Check `orchestrator_directives` — if STOP, halt immediately
- Review previous session's `notes_for_next` for any deviations from this handover's assumptions

### Step 2: Mark Session Started
Update your session in chain_log.json: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Follow the Implementation Plan above. Use ux-designer and tdd-implementor subagents.

### Step 4: Update Chain Log
Update your session in `prompts/0855_chain/chain_log.json` with:
- `tasks_completed`, `deviations`, `blockers_encountered`
- `notes_for_next`: Document what was deleted (StartupQuickStart.vue, localStorage keys), what replaced it in UserSettings, and the overlay mode prop interface. 0855g adds learning mode.
- `cascading_impacts`: Any changes that affect downstream handovers
- `summary`, `status`: "complete", `completed_at`

### Step 5: STOP
**Do NOT spawn the next terminal.** Commit your chain log update and exit.
