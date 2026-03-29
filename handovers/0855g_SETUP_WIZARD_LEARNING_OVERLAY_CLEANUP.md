# Handover 0855g: Setup Wizard — "How to Use" Learning Overlay + Final Cleanup

**Date:** 2026-03-28
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** ux-designer + documentation-manager
**Priority:** Medium
**Estimated Complexity:** 2 hours
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

Reuse the `SetupWizardOverlay.vue` shell in read-only "learning" mode for the "How to Use GiljoAI MCP" button (visible after setup is complete). Move the product explainer content into this overlay. Perform a final dead-code sweep and update the handover catalogue.

---

## Context and Background

After setup is complete, the WelcomeView button changes from "Resume Setup" to "How to Use GiljoAI MCP." This button opens the overlay in a read-only mode — no checkboxes, no state changes, no API calls. It's a reference guide explaining the product hierarchy, how agents work, and how slash commands fit in.

The current product explainer content lives in the old setup path. By this point, `StartupQuickStart.vue` has been deleted (0855f) and the overlay is fully functional.

**What 0855c provides:** `SetupWizardOverlay.vue` with a `mode` prop already stubbed — you need to implement `mode="learning"` behavior.

**What 0855f provides:** Full overlay lifecycle working, StartupQuickStart deleted, localStorage references removed. WelcomeView "How to Use" button label already wired (from 0855c).

---

## Technical Details

### Overlay Learning Mode

**File:** `frontend/src/components/setup/SetupWizardOverlay.vue`

Add a `mode` prop (already stubbed in 0855c):
- `mode="setup"` (default) — interactive wizard with state, API calls, navigation
- `mode="learning"` — read-only reference with static content

When `mode="learning"`:
- Title: "How to Use GiljoAI MCP"
- No stepper/progress bar
- No "Next" / "Back" navigation buttons
- Content: scrollable sections (see below)
- Bottom: single "Got it" button (closes overlay, no API calls)
- Close "X" also dismisses

### Learning Content Sections

Organize into collapsible sections or a scrollable layout:

1. **Product Hierarchy** — Product → Project → Job → Agent flow with brief explanations
2. **AI Coding Tools** — How Claude Code, Codex CLI, and Gemini CLI connect via MCP
3. **Slash Commands** — What `/gil_add`, `/gil_get_agents`, and other key commands do
4. **Agent Templates** — How to use agent templates, the Agent Lab, and chain strategies
5. **Dashboard** — Overview of Products, Projects, Tasks pages and what each tracks

Keep content concise — this is a reference card, not documentation. Link to full docs where applicable.

### WelcomeView Integration

**File:** `frontend/src/views/WelcomeView.vue`

The "How to Use GiljoAI MCP" button (already wired in 0855c for label) should:
- Open `SetupWizardOverlay` with `mode="learning"`
- No state changes, no backend calls

### Final Dead-Code Sweep

Grep the entire codebase for:
- `StartupQuickStart` — should have zero hits after 0855f
- `giljo_startup_checklist` — should have zero hits
- `tab: 'startup'` or `tab=startup` — verify no broken references
- Any setup-related `localStorage` keys
- Old 6-step checklist item IDs: `tools`, `connect`, `slash`, `templates`, `context`, `integrations`

Remove any orphaned code found.

### Catalogue Update

**File:** `handovers/handover_catalogue.md`

Add the 0855 series:
- Update the Quick Reference table: extend `0800+` row
- Add 7 entries to the Active Handovers table (or Completed if done by then)

---

## Implementation Plan

### Phase 1: Learning Mode
1. Add `mode` prop to `SetupWizardOverlay.vue`
2. Conditionally hide stepper, navigation, state management when `mode="learning"`
3. Build learning content sections

### Phase 2: Content
1. Write concise reference content for 5 sections
2. Style with collapsible sections or clean scrollable layout
3. Add "Got it" dismiss button

### Phase 3: WelcomeView Wiring
1. Wire "How to Use" button to open overlay in learning mode

### Phase 4: Dead-Code Sweep + Catalogue
1. Grep for all dead references, remove any found
2. Update `handover_catalogue.md` with 0855a-g entries
3. Verify clean build (no import errors, no broken references)

**Recommended Sub-Agents:** documentation-manager (content), ux-designer (layout)

---

## Testing Requirements

**Vitest Component Tests:**
- Learning mode renders without stepper or navigation
- Learning mode shows "Got it" button
- "Got it" closes overlay without API calls
- Setup mode still works (regression)

**Manual Verification:**
- Complete setup → verify "How to Use" button appears → opens learning overlay → dismiss works
- No console errors, no broken imports

---

## Dependencies and Blockers

**Dependencies:** 0855f (overlay lifecycle complete, StartupQuickStart deleted)
**Blockers:** None known.

---

## Success Criteria

- [ ] Learning mode renders correctly with reference content
- [ ] "How to Use GiljoAI MCP" button opens learning overlay
- [ ] "Got it" dismisses without state changes
- [ ] Zero dead references to old setup flow in codebase
- [ ] `handover_catalogue.md` updated with 0855a-g series
- [ ] Clean build, no import errors
- [ ] Vitest tests passing

---

## Rollback Plan

Remove learning mode from overlay, revert WelcomeView button behavior.

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/components/setup/SetupWizardOverlay.vue` | Add `mode="learning"` support |
| `frontend/src/views/WelcomeView.vue` | Wire "How to Use" button |
| `handovers/handover_catalogue.md` | Add 0855a-g entries |
| Various (dead-code sweep) | Remove orphaned references |
| `frontend/tests/` | Add learning mode tests |

---

## Chain Execution Instructions (Orchestrator-Gated v3)

You are session 7 of 7 in the 0855 chain. You are on branch `feature/0855-setup-wizard`.

### Step 1: Read Chain Log
Read `prompts/0855_chain/chain_log.json`
- Check `orchestrator_directives` — if STOP, halt immediately
- Review previous session's `notes_for_next` for any deviations from this handover's assumptions

### Step 2: Mark Session Started
Update your session in chain_log.json: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Follow the Implementation Plan above. Use ux-designer and documentation-manager subagents.

### Step 4: Update Chain Log
Update your session in `prompts/0855_chain/chain_log.json` with:
- `tasks_completed`, `deviations`, `blockers_encountered`
- `notes_for_next`: This is the final session. Write chain_summary in chain_log.json and set final_status to complete.
- `cascading_impacts`: Any changes that affect downstream handovers
- `summary`, `status`: "complete", `completed_at`

### Step 5: STOP
**Do NOT spawn the next terminal.** Commit your chain log update and exit.
