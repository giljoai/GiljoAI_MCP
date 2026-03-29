# Handover 0855c: Setup Wizard — Overlay Shell + Step 1 (Tool Selection)

**Date:** 2026-03-28
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** ux-designer + tdd-implementor
**Priority:** High
**Estimated Complexity:** 4 hours
**Status:** Not Started
**Series:** 0855a-g (Setup Wizard Redesign)
**Spec:** `handovers/SETUP_WIZARD_REDESIGN.md`

---

## Read First (MANDATORY)

1. `handovers/HANDOVER_INSTRUCTIONS.md` — coding standards, TDD protocol, quality gates
2. `handovers/Reference_docs/QUICK_LAUNCH.txt` — project bootstrap
3. `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md` — agent flow context
4. `handovers/SETUP_WIZARD_REDESIGN.md` — full spec for the wizard redesign
5. `frontend/design-system-sample.html` — brand design system reference (open in browser)

**Search before you build.** Use Serena `find_symbol` / `get_symbols_overview` to check if functionality already exists. Extend existing composables/stores — don't create new ones unless justified.

---

## Task Summary

Build the `SetupWizardOverlay.vue` component — a full-screen overlay with a 4-step stepper framework and the Step 1 tool selection UI. Wire it into WelcomeView with auto-launch on first login, resume behavior, and "Do this later" dismiss. This is the visual heart of the redesign.

---

## Context and Background

The current setup flow navigates to My Settings > Startup Tab, showing a product explainer. The redesign replaces this with a full-screen overlay that sits on top of the Welcome page. Users see the dashboard dimmed behind the overlay, creating a focused but non-disruptive onboarding experience.

Step 1 asks users which AI coding tools they use (Claude Code, Codex CLI, Gemini CLI — no OpenClaw). Multi-select cards with brand-compliant styling.

**Depends on:** 0855a — which adds to the User model: `setup_complete` (Boolean, default false), `setup_selected_tools` (JSONB array), `setup_step_completed` (Integer, 0-4). API: `PATCH /api/auth/me/setup-state` to update these fields. `GET /api/auth/me` returns them in the user response.

**Existing code you'll touch:**
- `frontend/src/views/WelcomeView.vue` (~296 lines): Has `isChecklistComplete` computed using `localStorage.getItem('giljo_startup_checklist_v1')` (line ~108), `showTutorialCta` computed (line ~227), `handleTutorialCta` function (line ~235). Replace all of this with overlay-based logic.
- `frontend/src/stores/user.js` (or similar Pinia store): Check how `currentUser` is exposed. The new setup fields come from `GET /me` — ensure the store doesn't filter them out.

---

## Technical Details

### New Component: `frontend/src/components/setup/SetupWizardOverlay.vue`

**Structure:**
- Full viewport overlay (`position: fixed; inset: 0; z-index: 2000`)
- Semi-transparent backdrop (`rgba(14, 28, 45, 0.85)`) — dashboard visible behind
- Centered content panel (max-width ~800px, `background: #182739`, `border-radius: 16px`)
- Top: "Setup GiljoAI MCP" title + "X" close button (dismiss = "Do this later")
- Below title: horizontal 4-step progress bar with brand gradient fill
- Main area: active step content (slot or conditional rendering)
- Bottom: navigation buttons (Back / Next / Skip)

**Step Progress Bar:**
- 4 labeled steps: "Choose Tools" → "Connect" → "Install" → "Launch"
- Active step: brand yellow `#ffc300` label + filled circle
- Completed steps: green `#6bcf7f` checkmark
- Future steps: muted `#8f97b7` label + empty circle
- Fill bar between steps: `linear-gradient(45deg, #ffd93d, #6bcf7f)` for completed portion

**Step 1 UI — "Which AI coding tool(s) do you use?"**
- Three selectable cards in a row (responsive: stack on mobile)
- Each card: `#1e3147` background, `smooth-border` class, `border-radius: 12px`
  - Tool icon/logo (use `mdi-*` icons or inline SVG)
  - Tool name (bold, `#e1e1e1`)
  - Provider subtitle ("by Anthropic", "by OpenAI", "by Google")
  - Selected state: `#ffc300` border accent via `--smooth-border-color`, subtle yellow glow (`box-shadow`)
  - Unselected state: default `#315074` border
- Multi-select toggle (click to select/deselect)
- Below cards: "Don't have one yet? Learn more" link (muted text, opens external links)
- "Next" button: disabled until >= 1 tool selected. Brand yellow primary CTA.
- On Next: call `PATCH /api/auth/me/setup-state` with `setup_selected_tools` and `setup_step_completed: 1`

**Props for future use:**
- `mode` prop: `"setup"` (default, interactive) or `"learning"` (read-only, for 0855g)

### WelcomeView Changes

**File:** `frontend/src/views/WelcomeView.vue`

- Import and render `SetupWizardOverlay`
- Auto-launch: on mount, if `user.setup_complete === false`, show overlay
- CTA button logic:
  - `setup_complete === false && setup_step_completed === 0` → "Begin Setup" (yellow primary)
  - `setup_complete === false && setup_step_completed > 0` → "Resume Setup" (yellow primary)
  - `setup_complete === true` → "How to Use GiljoAI MCP" (outlined secondary)
- Remove or update references to the old `giljo_startup_checklist_v1` localStorage logic

### User Store Changes

**File:** `frontend/src/stores/user.js` (or similar Pinia store)

- Ensure `setup_complete`, `setup_selected_tools`, `setup_step_completed` are exposed from the user object returned by `GET /me`
- Add action: `updateSetupState(payload)` → calls `PATCH /me/setup-state`

### Brand Compliance (Design Tokens — use these exact values)

Per `design-system-sample.html` and CLAUDE.md:

| Token | Value | Usage |
|-------|-------|-------|
| Page background | `#0e1c2d` | Behind dimmed overlay backdrop |
| Card surface | `#182739` | Overlay panel background |
| Elevated surface | `#1e3147` | Tool selection cards, step content cards |
| Border color | `#315074` | Card borders, dividers |
| Brand yellow | `#ffc300` | Primary CTAs, selected state accents |
| Brand yellow hover | `#ffed4e` | Button hover state |
| Brand gradient | `linear-gradient(45deg, #ffd93d, #6bcf7f)` | Progress bar fill |
| Primary text | `#e1e1e1` | Headings, body text |
| Secondary text | `#8f97b7` | Subtitles, captions, hints |
| Success green | `#6bcf7f` | Connected indicators, completed steps |
| Danger pink | `#c6298c` | Error states |
| Card radius | `12px` | Cards, panels |
| Button radius | `8px` | Buttons, inputs |
| Font body | `Roboto, "Segoe UI", system-ui, sans-serif` | All text |
| Font mono | `"Roboto Mono", "Courier New", monospace` | Code, tokens |

**CRITICAL:** Never use CSS `border` on rounded elements. Use the global `smooth-border` class from `main.scss` (applies `box-shadow: inset`). Variants: `.smooth-border` (1px), `.smooth-border-2` (2px), `.smooth-border-accent` (2px brand yellow). Custom: `style="--smooth-border-color: #hex"`.

**Buttons:** Primary = `#ffc300` bg + `#0e1c2d` text + `600` weight. Secondary = transparent bg + `#ffc300` text + `2px #ffc300` border. Use Vuetify `color="primary"` and `variant="flat"` / `variant="outlined"` which map to these.

**Transitions:** 250ms ease-out for state changes. Selected card animation: subtle yellow glow via `box-shadow: 0 0 12px rgba(255, 195, 0, 0.15)`.

---

## Implementation Plan

### Phase 1: Overlay Shell
1. Create `frontend/src/components/setup/` directory
2. Build `SetupWizardOverlay.vue` with overlay backdrop, content panel, close button
3. Build the 4-step progress bar (hardcoded labels, dynamic active/completed state)
4. Wire stepper state to `setup_step_completed` prop

### Phase 2: Step 1 Tool Selection
1. Build 3 tool selection cards with multi-select toggle
2. Wire selected state to local ref, sync with `setup_selected_tools`
3. Implement "Next" button with API call to update setup state

### Phase 3: WelcomeView Integration
1. Import overlay, add conditional rendering based on user store
2. Implement auto-launch on mount
3. Implement CTA button label logic
4. Write Vitest component tests

### Phase 4: Store Integration
1. Add `updateSetupState` action to user store
2. Wire overlay to read/write store state

**Recommended Sub-Agents:** ux-designer (visual implementation), tdd-implementor (component tests)

---

## Testing Requirements

**Vitest Component Tests:**
- Overlay renders when `setup_complete === false`
- Overlay hidden when `setup_complete === true`
- Tool cards toggle selection on click
- "Next" disabled when no tools selected, enabled when >= 1 selected
- Progress bar shows correct active step
- Close button emits dismiss event
- CTA button label changes based on setup state

---

## Dependencies and Blockers

**Dependencies:** 0855a (backend fields and PATCH endpoint must exist)
**Blockers:** None known.

---

## Success Criteria

- [ ] Overlay renders full-screen over WelcomeView
- [ ] 4-step progress bar with correct visual states
- [ ] 3 tool selection cards with multi-select toggle
- [ ] "Next" button calls backend, advances to Step 2 placeholder
- [ ] Auto-launch on first login works
- [ ] "Do this later" dismiss works, "Resume Setup" reappears
- [ ] Brand-compliant colors, smooth-border, typography
- [ ] Vitest component tests passing

---

## Rollback Plan

Delete `frontend/src/components/setup/SetupWizardOverlay.vue` and revert WelcomeView changes.

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/components/setup/SetupWizardOverlay.vue` | **New** — overlay shell + Step 1 |
| `frontend/src/views/WelcomeView.vue` | Import overlay, auto-launch, CTA labels |
| `frontend/src/stores/user.js` | Expose setup fields, add updateSetupState action |
| `frontend/tests/` | New spec file for overlay component |

---

## Chain Execution Instructions (Orchestrator-Gated v3)

You are session 3 of 7 in the 0855 chain. You are on branch `feature/0855-setup-wizard`.

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
- `notes_for_next`: Include exact component name, prop interface, emit events, store action signatures. 0855d builds Step 2 inside your overlay.
- `cascading_impacts`: Any changes that affect downstream handovers
- `summary`, `status`: "complete", `completed_at`

### Step 5: STOP
**Do NOT spawn the next terminal.** Commit your chain log update and exit.
