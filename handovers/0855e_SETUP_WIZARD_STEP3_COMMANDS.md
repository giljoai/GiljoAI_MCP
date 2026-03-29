# Handover 0855e: Setup Wizard — Step 3 (Install Commands & Agents)

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

Build the Step 3 UI: per-tool bootstrap prompt display with copy functionality, and a mini-checklist that auto-updates via WebSocket as slash commands and agent templates are fetched. This step bridges "connected" to "ready to work."

---

## Context and Background

After the user's AI tool is connected (Step 2), they need to paste a bootstrap prompt into their tool's terminal. This prompt tells the tool to fetch slash commands and agent templates from GiljoAI MCP. The wizard shows the prompt text and monitors via WebSocket for confirmation that the tool has fetched both resources.

The bootstrap prompt content already exists in the integrations tab. Reuse that logic — do not duplicate.

**What 0855b provides:** WebSocket events `setup:commands_installed` (`{tenant_key, user_id, tool_name, command_count}`) emitted from `api/endpoints/downloads.py` `get_bootstrap_prompt` (line ~440), and `setup:agents_downloaded` (`{tenant_key, user_id, agent_count}`) emitted from `download_agent_templates` (line ~167).

**What 0855c provides:** `SetupWizardOverlay.vue` shell with stepper. User store `updateSetupState()`.

**What 0855d provides:** Step 2 component with connected tool list (which tools showed "Connected"). This list determines which tool panels to show in Step 3.

**Bootstrap prompt source:** Check `api/endpoints/downloads.py` `get_bootstrap_prompt` (lines 440-559) for the backend-generated prompt. On the frontend, check `frontend/src/components/settings/integrations/McpIntegrationCard.vue` for how the prompt is currently displayed/copied.

---

## Technical Details

### New Component: `frontend/src/components/setup/SetupStep3Commands.vue`

**Layout per connected tool:**
1. **Bootstrap Prompt Block**
   - Copyable text area with the consolidated bootstrap prompt (Path B)
   - Instruction: "Paste this into your [tool name] terminal and press Enter"
   - "Copy to Clipboard" button (brand yellow outline)

2. **Auto-Updating Mini-Checklist**
   - `○ Slash commands installed` → flips to `● Slash commands installed` (green) on `setup:commands_installed` event
   - `○ Agents downloaded` → flips to `● Agents downloaded` (green) on `setup:agents_downloaded` event
   - Checkmark uses `mdi-check-circle` icon in `#6bcf7f`

3. **Post-Slash-Commands Display**
   - After slash commands installed: show `/gil_get_agents` command block
   - Persistent — survives tab switches (state in component, backed by WebSocket events)
   - Note: "Tip: Select 'Use default model for all' on first import for fastest setup"

4. **Codex-Specific Flow**
   - Two-step nature: skills installed first, then `$gil-get-agents` command
   - Show both steps sequentially with appropriate labels

**Bottom Navigation:**
- "Next" button: enabled when >= 1 tool shows both checkmarks green
- "Skip — I'll do this later" link (muted text) — advances to Step 4 without blocking

### Bootstrap Prompt Source

Find the existing bootstrap prompt generation logic. Likely in:
- `frontend/src/components/settings/integrations/McpIntegrationCard.vue`
- Or `frontend/src/components/settings/StartupQuickStart.vue` (the checklist actions)

Extract or import the prompt text. Do NOT hardcode a copy.

### WebSocket Subscriptions

Subscribe to:
- `setup:commands_installed` — match `event.data.tool_name` to connected tools
- `setup:agents_downloaded` — match `event.data.user_id` to current user

Update reactive state per tool:
```javascript
const toolStatus = reactive({
  claude_code: { commands: false, agents: false },
  codex_cli: { commands: false, agents: false },
  gemini_cli: { commands: false, agents: false },
})
```

---

## Implementation Plan

### Phase 1: Bootstrap Prompt Display
1. Locate existing bootstrap prompt content
2. Build `SetupStep3Commands.vue` with per-tool prompt blocks
3. Implement copy-to-clipboard

### Phase 2: Mini-Checklist with WebSocket
1. Build checklist UI with reactive state
2. Subscribe to `setup:commands_installed` and `setup:agents_downloaded` events
3. Wire checkmark transitions (gray → green with subtle animation)

### Phase 3: Post-Install Display
1. Show `/gil_get_agents` command after slash commands confirmed
2. Add Codex-specific two-step flow
3. Implement "Skip" link

### Phase 4: Integration + Tests
1. Wire Step 3 into `SetupWizardOverlay.vue` stepper
2. Write Vitest component tests

**Recommended Sub-Agents:** ux-designer (UI), tdd-implementor (tests)

---

## Testing Requirements

**Vitest Component Tests:**
- Renders bootstrap prompt for each connected tool
- Copy button copies correct text
- Checklist starts unchecked
- Mock WebSocket event flips slash command checkmark
- Mock WebSocket event flips agent download checkmark
- "Next" disabled until both checkmarks green (at least 1 tool)
- "Skip" link advances to Step 4
- `/gil_get_agents` block appears after slash commands installed

---

## Dependencies and Blockers

**Dependencies:**
- 0855b (WebSocket events `setup:commands_installed`, `setup:agents_downloaded`)
- 0855c (overlay shell and stepper)
- 0855d (Step 2 provides connected tool list)

**Blockers:** Need to locate bootstrap prompt source (Phase 1 research).

---

## Success Criteria

- [ ] Bootstrap prompt displayed per connected tool
- [ ] Copy-to-clipboard works for prompt blocks
- [ ] Mini-checklist auto-updates via WebSocket events
- [ ] `/gil_get_agents` appears after slash commands installed
- [ ] "Next" enables on both checkmarks green
- [ ] "Skip" link works for users who want to defer
- [ ] Codex two-step flow handled correctly
- [ ] Vitest tests passing

---

## Rollback Plan

Delete `SetupStep3Commands.vue` and revert stepper wiring in overlay.

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/components/setup/SetupStep3Commands.vue` | **New** — Step 3 UI |
| `frontend/src/components/setup/SetupWizardOverlay.vue` | Wire Step 3 into stepper |
| `frontend/tests/` | New spec file |

---

## Chain Execution Instructions (Orchestrator-Gated v3)

You are session 5 of 7 in the 0855 chain. You are on branch `feature/0855-setup-wizard`.

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
- `notes_for_next`: Include how the checklist state is exposed, what events the component emits on completion. 0855f wires all 4 steps together end-to-end.
- `cascading_impacts`: Any changes that affect downstream handovers
- `summary`, `status`: "complete", `completed_at`

### Step 5: STOP
**Do NOT spawn the next terminal.** Commit your chain log update and exit.
