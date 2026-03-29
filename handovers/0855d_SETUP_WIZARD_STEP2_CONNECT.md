# Handover 0855d: Setup Wizard — Step 2 (Connect to GiljoAI)

**Date:** 2026-03-28
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** ux-designer + tdd-implementor
**Priority:** High
**Estimated Complexity:** 5 hours
**Status:** Not Started
**Series:** 0855a-g (Setup Wizard Redesign)
**Spec:** `handovers/SETUP_WIZARD_REDESIGN.md`

---

## Read First (MANDATORY)

1. `handovers/HANDOVER_INSTRUCTIONS.md` — coding standards, TDD protocol, quality gates
2. `handovers/Reference_docs/QUICK_LAUNCH.txt` — project bootstrap
3. `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md` — agent flow context
4. `handovers/SETUP_WIZARD_REDESIGN.md` — full spec for the wizard redesign
5. `frontend/design-system-sample.html` — brand design system reference

**Search before you build.** Use Serena `find_symbol` / `get_symbols_overview` to check if functionality already exists.

**Brand tokens:** See 0855c handover for the complete design token table. Use those exact values.

---

## Task Summary

Build the Step 2 UI inside the setup wizard overlay: inline MCP configuration per selected tool, API key generation with reuse detection, platform-specific config display, and live WebSocket connection status indicators. This is the heaviest frontend step — it refactors `AiToolConfigWizard.vue` into reusable logic and adds real-time feedback.

---

## Context and Background

The existing `AiToolConfigWizard.vue` (368 lines) renders as a modal dialog with tool selection radio buttons. For the wizard, we need the same config generation logic but rendered **inline** within the overlay, with per-tool tabs (not radio selection — tools were already chosen in Step 1), and live connection status driven by `setup:tool_connected` WebSocket events.

**Important:** Strip OpenClaw from the wizard. Leave `AiToolConfigWizard.vue` standalone modal untouched — only extract shared logic.

**What 0855a provides:** `GET /api/v1/auth/api-keys/active` — returns `[{id, key_prefix, created_at, is_active, expires_at}]` for active keys. `PATCH /api/v1/auth/me/setup-state` — updates `setup_step_completed` to 2 on Next.

**What 0855b provides:** WebSocket event `setup:tool_connected` with `{tenant_key, user_id, tool_name, connected_at}` — emitted from `api/endpoints/mcp_http.py` `handle_initialize` when a tool connects.

**What 0855c provides:** `SetupWizardOverlay.vue` shell with 4-step stepper, `mode` prop, slot/conditional for step content. User store `updateSetupState(payload)` action.

**Existing code:** `AiToolConfigWizard.vue` (368 lines) has tool selection radio buttons (line ~50), server IP detection, platform-specific command generation, copy-to-clipboard. Extract the generation functions into a composable.

---

## Technical Details

### New Component: `frontend/src/components/setup/SetupStep2Connect.vue`

**Layout:**
- Header: "Connect your tools to GiljoAI MCP"
- Per-tool tabs (if multiple tools selected in Step 1). Single tool = no tabs, just content.
- Each tool panel:
  1. **Server URL** — pre-filled from `window.location`, editable field
  2. **API Key Status** — check `GET /api-keys/active` (from 0855a):
     - If active key exists: show key prefix, "Key already generated" green badge
     - If no key: "Generate API Key" button → calls existing `POST /api-keys` endpoint
  3. **Configuration Display** — rendered inline (not modal):
     - Platform toggle: PowerShell / Linux (auto-detect, allow override)
     - Claude Code: `claude mcp add` command with server URL + API key
     - Codex CLI: environment variable + `codex --mcp-config` command
     - Gemini CLI: HTTPS environment variable + config command + yellow cert warning
     - "Copy to clipboard" button for each block
  4. **Connection Status Indicator:**
     - Default: `○ Not connected` (gray `#8f97b7`)
     - On `setup:tool_connected` event matching this tool: `● Connected` (green `#6bcf7f`)
     - Instruction text: "After pasting the config and restarting your tool, ask it to run a GiljoAI health check."
- Bottom: "Next" button — enabled when >= 1 tool shows "Connected"

### Refactoring AiToolConfigWizard.vue

Extract shared logic into a composable or utility:

**Option A (preferred): Composable `frontend/src/composables/useMcpConfig.js`**
- `generateClaudeConfig(serverUrl, apiKey)` → returns command string
- `generateCodexConfig(serverUrl, apiKey)` → returns env var + command
- `generateGeminiConfig(serverUrl, apiKey)` → returns env var + command + cert warning
- `detectPlatform()` → returns "powershell" or "unix"

Both `AiToolConfigWizard.vue` (standalone modal) and `SetupStep2Connect.vue` (wizard inline) import from the composable. Do NOT duplicate config generation logic.

### WebSocket Integration

**File:** `frontend/src/stores/websocket.js` (or equivalent)

- Subscribe to `setup:tool_connected` events
- Match `event.data.tool_name` to the tools displayed in Step 2
- Update reactive state per tool: `connectionStatus[tool_name] = "connected"`
- The overlay watches this reactive state for visual updates

### API Key Flow

```
1. Component mounts → GET /api-keys/active
2. If active keys exist → display key prefix, show config immediately
3. If no keys → show "Generate API Key" button
4. User clicks → POST /api-keys → display new key + config
5. Note: plaintext key shown only once! Warn user to copy config now.
```

### Cascading Analysis

- `AiToolConfigWizard.vue` — refactored to use shared composable, standalone modal behavior preserved
- WebSocket store — additive subscription, no existing behavior changed

---

## Implementation Plan

### Phase 1: Composable Extraction
1. Create `useMcpConfig.js` composable with config generation functions
2. Refactor `AiToolConfigWizard.vue` to use the composable (behavior must remain identical)
3. Verify existing modal still works

### Phase 2: Step 2 Component
1. Build `SetupStep2Connect.vue` with per-tool tabs, config display, copy buttons
2. Wire API key check + generation flow
3. Wire platform toggle

### Phase 3: WebSocket Connection Status
1. Subscribe to `setup:tool_connected` events in the component
2. Build connection status indicator with reactive updates
3. Wire "Next" button enable/disable logic

### Phase 4: Integration + Tests
1. Wire Step 2 into `SetupWizardOverlay.vue` stepper
2. Write Vitest component tests

**Recommended Sub-Agents:** ux-designer (UI layout), tdd-implementor (tests)

---

## Testing Requirements

**Vitest Component Tests:**
- Renders correct tabs for selected tools
- Single tool: no tab bar
- API key check: shows "already generated" or "generate" button
- Config generation matches expected format per tool per platform
- Connection status updates on mock WebSocket event
- "Next" disabled until >= 1 tool connected
- Copy-to-clipboard button works

**Integration Tests:**
- Composable refactor: existing `AiToolConfigWizard.vue` behavior unchanged

---

## Dependencies and Blockers

**Dependencies:**
- 0855a (API key active endpoint, setup state PATCH)
- 0855b (WebSocket `setup:tool_connected` event)
- 0855c (overlay shell and stepper framework)

**Blockers:** None known.

---

## Success Criteria

- [ ] Config generation logic extracted to shared composable
- [ ] Existing `AiToolConfigWizard.vue` modal still works (regression)
- [ ] Step 2 renders inline per-tool configuration with tabs
- [ ] API key reuse detection works (no duplicate key generation)
- [ ] Connection status updates in real-time via WebSocket
- [ ] "Next" enables on >= 1 connected tool
- [ ] OpenClaw stripped from wizard (not from standalone modal)
- [ ] Vitest tests passing

---

## Rollback Plan

Delete `SetupStep2Connect.vue` and `useMcpConfig.js`. Revert `AiToolConfigWizard.vue` if refactored.

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/components/setup/SetupStep2Connect.vue` | **New** — Step 2 inline config |
| `frontend/src/composables/useMcpConfig.js` | **New** — shared config generation |
| `frontend/src/components/AiToolConfigWizard.vue` | Refactor to use composable |
| `frontend/src/stores/websocket.js` | Subscribe to setup events |
| `frontend/src/components/setup/SetupWizardOverlay.vue` | Wire Step 2 into stepper |
| `frontend/tests/` | New spec files |

---

## Chain Execution Instructions (Orchestrator-Gated v3)

You are session 4 of 7 in the 0855 chain. You are on branch `feature/0855-setup-wizard`.

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
- `notes_for_next`: Include composable function signatures, how connected tools list is exposed, WebSocket subscription pattern used. 0855e needs to know which tools showed Connected.
- `cascading_impacts`: Any changes that affect downstream handovers
- `summary`, `status`: "complete", `completed_at`

### Step 5: STOP
**Do NOT spawn the next terminal.** Commit your chain log update and exit.
