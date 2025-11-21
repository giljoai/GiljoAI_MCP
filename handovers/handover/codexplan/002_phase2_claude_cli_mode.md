# Handover LJ-002: Implement Tab – Claude Code CLI Mode

**Feature**: Implement tab – single-terminal Claude Code mode (slides 3a–3i)  
**Status**: READY FOR IMPLEMENTATION  
**Priority**: P1 – HIGH  
**Estimated Time**: 2–3 days  
**Depends On**: LJ-000 (contracts), LJ-001 (Launch tab), 0322 Service Layer Compliance  
**Blocks**: LJ-003..LJ-005 (General CLI mode, backend wiring, regression)  
**Tool**: Claude Code CLI (multiple subagents)

---

## Executive Summary

This handover implements the Implement tab in its Claude Code CLI mode as shown in deck slides 3a–3i. In this mode, the user runs only the orchestrator in a single Claude Code CLI terminal. The UI shows:

- A status board reflecting orchestrator and subagent states (Waiting, Working, Completed).
- A single orchestrator CLI prompt with copy/reuse behavior.
- Message composer + broadcast controls.
- Per-agent message history view, including counts of sent/received/ack/broadcast messages.

All of this must be driven by the contracts defined in LJ-000 and Launch/staging behavior from LJ-001, with strict TDD and service-layer discipline.

---

## Problem Statement

Currently:
- The Implement tab does not fully represent the Claude Code “single-terminal” mode envisioned in slides 3a–3i.
- Status tracking for orchestrator vs subagents is not presented as a cohesive “status board”.
- The messaging UI (broadcasts, per-agent histories) is not aligned with the deck’s visual specification.
- Prompt copy/reuse semantics for orchestrator-only CLI usage are not enforced via tests.

We need a dedicated Claude Code CLI view that:
- Uses data contracts from LJ-000.
- Reacts to staging/launch outcomes from LJ-001.
- Presents a clear, testable state machine for agent statuses and messaging.

---

## Scope

In scope:
- Implement the Implement tab variant when “Claude Code CLI mode” is active:
  - Toggle ON state: only orchestrator has an active CLI prompt.
  - Other agents shown as subagents with inactive CLI buttons.
- Build a status board MVP per slides 3a–3i:
  - Columns: Agent Type, Subagents, Status, Messages Waiting, Messages Sent, Messages Read, Job Read, Job Acknowledged.
  - Rows for orchestrator and each subagent.
- Implement message composer:
  - User can send a message to orchestration system (orchestrator or broadcast).
  - Display of message counts and per-agent history.
- Implement per-agent message history panel:
  - “View this agent’s message history” per slide 3i.
  - Includes sent/received/ack/broadcast entries from LJ-000 contracts.
- Provide orchestrator CLI prompt with:
  - Copy-to-clipboard.
  - Reuse indicator (prompt has been used but can be copied again).

Out of scope:
- General CLI mode (multi-terminal per agent – LJ-003).
- Backend schema changes or new endpoints (wiring uses existing / soon-to-be-added contracts from LJ-004).

---

## Dependencies

- LJ-000:
  - Status board and message history contracts.
  - Telemetry around legacy `_spawn_generic_agent` (no new dependencies on legacy paths).
- LJ-001:
  - Staging flow and Launch Jobs transition.
  - Mission prompt and staged state used to enter Implement tab.
- Backend status/messaging endpoints will be fleshed out in LJ-004; for this handover:
  - Use existing endpoints where possible.
  - If contracts are ahead of implementation, tests should be written and may remain Red until LJ-004.

---

## Architectural & TDD Requirements

- UI must be driven by contract-shaped data, not ad-hoc structures.
- Single source of truth:
  - Implement tab reads a status board + message history structure consistent with LJ-000.
- TDD:
  - Tests first for:
    - State transitions (Waiting → Working → Completed).
    - Prompt copy/reuse behavior.
    - Message composer interactions and history rendering.
  - Behavior-focused: do not assert internal component details; assert observable behavior and props/events.
- Componentization:
  - Avoid turning the Implement tab into a monolith.
  - Extract small, focused components: e.g., `ClaudeModeStatusBoard`, `ClaudeModePromptPanel`, `AgentMessageHistoryPanel`.

---

## Recommended Agent Setup (Claude Code CLI Subagents)

- **LJ-002-UX (Implement Claude UX Agent, primary)**  
  - Designs status board, prompt panel, and history UI.

- **LJ-002-STATE (State Machine Agent, support)**  
  - Encodes status transitions and derives display states.

- **LJ-002-TEST (Test Author Agent, support)**  
  - Writes detailed unit/component tests before implementation.

---

## Execution Plan

### Step 1 – Design Claude Mode View Structure

- Decide on component structure, for example:
  - `ImplementClaudeMode.vue` (top-level mode wrapper).
  - `ClaudeModeStatusBoard.vue` (status rows + counts).
  - `ClaudeModePromptPanel.vue` (orchestrator CLI prompt + copy/reuse).
  - `AgentMessageHistoryPanel.vue` (per-agent history).
- Map deck slides 3a–3i to:
  - Specific combinations of status values and message counts.
  - UI affordances (what’s clickable, what’s disabled).

### Step 2 – Write Tests (Red)

**File**: `frontend/tests/unit/components/ImplementClaudeMode.spec.ts` (NEW)

Suggested tests:
- `test_claude_mode_shows_single_orchestrator_prompt_and_disables_other_agent_buttons`
- `test_status_board_renders_rows_for_all_agents_with_correct_counts`
- `test_status_transitions_from_waiting_to_working_to_completed_are_reflected_in_status_board`
- `test_copying_orchestrator_prompt_sets_reuse_indicator_but_allows_recopy`
- `test_message_composer_sends_broadcast_and_updates_counts`
- `test_selecting_agent_shows_message_history_panel`

Behavior to assert:
- Only orchestrator has an active CLI prompt in Claude mode.
- Subagent “run” buttons are disabled/hidden but appear in the board.
- Status cells update according to provided status data.
- History panel shows entries with correct direction/type labels.

If appropriate, also add:

**File**: `frontend/tests/unit/components/ClaudeModeStatusBoard.spec.ts` (NEW)

- Focused tests on row rendering, counts, and conditional styling.

### Step 3 – Implement Components (Green)

- Implement `ImplementClaudeMode` to:
  - Receive props or store-derived data following `LaunchImplementStatusBoardPayload` and message history contracts.
  - Render status board and prompt panel.
  - Handle selection of an agent to view history.
- Implement `ClaudeModePromptPanel` to:
  - Display orchestrator CLI prompt text.
  - Use shared clipboard utility to copy text.
  - Track a `hasPromptBeenCopied` flag to drive reuse indicator.
- Implement `AgentMessageHistoryPanel` to:
  - Render history entries with direction/type (sent, received, broadcast, ack).
  - Show ordering and basic grouping, as depicted in slide 3i.

### Step 4 – Wire Into Implement Tab Shell

- Integrate `ImplementClaudeMode` into the existing Implement tab container:
  - Mode selection: when “Claude Code CLI mode” is ON, show this mode; otherwise, General mode (LJ-003).
  - Use existing route/tab structure; do not introduce new routes unless required by design.

### Step 5 – Refactor & Polish

- Ensure styling matches deck intent using existing design tokens and patterns.
- Simplify derived state calculations into a small, testable helper/composable if they grow complex.

---

## TDD Specifications (Tests to Write First)

In addition to the high-level component tests:

**File**: `frontend/tests/unit/components/AgentMessageHistoryPanel.spec.ts` (NEW)

Suggested tests:
- `test_history_panel_groups_entries_by_agent_and_sorts_by_time`
- `test_history_panel_shows_ack_indicator_when_message_is_acknowledged`

All of these tests must be present and failing before implementing or wiring the corresponding components.

---

## Files to Create / Modify

New:
- `frontend/src/components/launch/ImplementClaudeMode.vue` (or equivalent folder by convention).
- `frontend/src/components/launch/ClaudeModeStatusBoard.vue`
- `frontend/src/components/launch/ClaudeModePromptPanel.vue`
- `frontend/src/components/launch/AgentMessageHistoryPanel.vue`
- `frontend/tests/unit/components/ImplementClaudeMode.spec.ts`
- `frontend/tests/unit/components/ClaudeModeStatusBoard.spec.ts`
- `frontend/tests/unit/components/AgentMessageHistoryPanel.spec.ts`

Modified:
- Implement tab shell view (likely `frontend/src/components/projects/JobsTab.vue` or a similar container).
- Any mode switch/toggle component controlling Claude vs General CLI modes.

No backend changes should be required in this handover beyond consuming existing contracts; if some data is missing, tests should document the gap and be addressed in LJ-004.

---

## Success Criteria & Completion Checklist

Must-have:
- [ ] Implement tab Claude mode matches slides 3a–3i in behavior and primary layout.
- [ ] Only the orchestrator has an active CLI prompt; other agent buttons are inactive.
- [ ] Status board shows correct rows and counts based on contract-shaped data.
- [ ] Message composer & history panel behave per spec; broadcasts and acks are visible.
- [ ] All new component tests are passing with >80% coverage for new UI logic.

Nice-to-have:
- [ ] Small UX details from the deck (e.g., subtle text labels) are mirrored where they clarify state.
- [ ] Dedicated README or design note for Implement Claude mode under `frontend/src/components/launch/`.

LJ-002 is complete when the Claude Code CLI mode is fully implemented, tested, and ready to share the Implement tab shell with LJ-003’s General CLI mode.

