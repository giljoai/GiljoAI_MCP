# Handover LJ-003: Implement Tab – General CLI Mode

**Feature**: Implement tab – multi-terminal General CLI mode (slides 4a–4h)  
**Status**: READY FOR IMPLEMENTATION  
**Priority**: P1 – HIGH  
**Estimated Time**: 2–3 days  
**Depends On**: LJ-000..LJ-002 (contracts, Launch, Claude mode), 0322 Service Layer Compliance  
**Blocks**: LJ-004..LJ-005  
**Tool**: Claude Code CLI (multiple subagents)

---

## Executive Summary

This handover implements the “General CLI mode” of the Implement tab as depicted in deck slides 4a–4h. In this mode, each agent (orchestrator + subagents) has its own CLI terminal prompt, and the user orchestrates the sequence by copying prompts into multiple terminals.

Compared to Claude mode (LJ-002), General mode:
- Shows individual prompts per agent (unique CLI snippets).
- Allows agents to start at different times or wait on others (slides 4e–4g).
- Shares the same status board, broadcast messaging, and history systems as Claude mode.

We must implement this as a first-class mode that cleanly shares components and contracts with Claude mode while providing additional prompt controls.

---

## Problem Statement

Current UI does not:
- Display unique CLI prompts per agent for multi-terminal operation.
- Provide reuse indicators per agent prompt.
- Reflect staggered start/wait states where some agents are working and others are waiting on dependencies.
- Cleanly separate Claude vs General modes under a single Implement tab shell.

We need a test-driven, contract-aligned implementation of General CLI mode with per-agent prompt controls and shared status/messaging infrastructure.

---

## Scope

In scope:
- Implement General CLI mode toggle OFF state for Implement tab:
  - Each agent (orchestrator + subagents) gets a “Run in CLI” prompt button.
  - Prompts are unique per agent and follow a contract defined in LJ-000.
  - Copy-to-clipboard + reuse indicators per agent.
- Mirror status board, messaging, and history behavior from Claude mode:
  - Same status columns and counts.
  - Same message composer + broadcast controls.
  - Same per-agent history panel; only prompt controls differ.
- Model staggered starts/waits (slides 4e–4g) as a combination of status values and visual cues.

Out of scope:
- Changes to Claude mode (reuse components where possible).
- Backend schema changes (these are handled in LJ-004 if needed).

---

## Dependencies

- LJ-000:
  - Contracts for status board, agent prompts, message history.
- LJ-001:
  - Launch → Implement transition and staged state.
- LJ-002:
  - Shared status/messaging components and basic Implement tab shell integration.

---

## Architectural & TDD Requirements

- Strong reuse:
  - General mode should reuse status board and history components from LJ-002.
  - Only prompt-related UI should differ between modes.
- Clear mode separation:
  - Implement tab shell decides which mode component to render based on a simple mode flag (Claude vs General).
- TDD:
  - Tests first for:
    - Prompt uniqueness.
    - Reuse indicators per agent.
    - Staggered start/wait scenarios.
    - Shared status/messaging behavior with Claude mode.
  - No direct testing of internal implementation details; only props, emitted events, and final DOM states.

---

## Recommended Agent Setup (Claude Code CLI Subagents)

- **LJ-003-UX (General CLI UX Agent, primary)**  
  - Designs per-agent prompt controls and staggered state visuals.

- **LJ-003-STATE (State Machine Agent, support)**  
  - Encodes additional state for per-agent prompt usage (e.g., `hasPromptBeenCopied`, `isAgentWaitingOnDependency`).

- **LJ-003-TEST (Test Author Agent, support)**  
  - Writes detailed tests for prompt uniqueness and shared behavior with Claude mode.

---

## Execution Plan

### Step 1 – Design Prompt Controls & Mode Integration

- Extend the Implement tab shell to:
  - Render `ImplementGeneralMode` when General CLI mode is selected (e.g., toggle OFF).
  - Keep `ImplementClaudeMode` from LJ-002 intact.
- Define per-agent prompt UI:
  - Button or icon to copy prompt text.
  - Label with agent name/type.
  - Reuse indicator (e.g., icon or text) once copied.

### Step 2 – Write Tests (Red)

**File**: `frontend/tests/unit/components/ImplementGeneralMode.spec.ts` (NEW)

Suggested tests:
- `test_general_mode_renders_prompt_button_for_each_agent`
- `test_each_agent_prompt_is_unique_and_contains_agent_identifier`
- `test_copying_agent_prompt_sets_reuse_indicator_for_that_agent_only`
- `test_status_board_stays_in_sync_in_general_mode`
- `test_broadcast_message_updates_history_for_all_agents`
- `test_staggered_start_scenario_shows_some_agents_waiting_and_others_working`

Behavior to assert:
- Number of prompt buttons equals number of agents in the status payload.
- Each prompt button copies a distinct CLI snippet with agent-specific info.
- Reuse indicator is per-agent, not global.
- Status board and history behave identically to Claude mode when given the same underlying data.

### Step 3 – Implement Components (Green)

- Implement `ImplementGeneralMode.vue`:
  - Accepts the same status board and history data as Claude mode.
  - Renders per-agent prompt buttons and reuse indicators.
  - Delegates status/histories to shared components from LJ-002.
- Implement per-agent prompt logic:
  - Build CLI prompt strings using an agent prompt contract from LJ-000 (e.g., `LaunchImplementAgentPromptPayload`).
  - Use shared clipboard utility for copy.
  - Track `hasPromptBeenCopied` per agent in reactive state or store.

### Step 4 – Share Components with Claude Mode

- Ensure that:
  - Status board and history remain shared between Claude and General modes.
  - Only prompt panel components differ (Claude vs per-agent).
- Refactor any duplicated logic from LJ-002 into shared composables or helpers.

### Step 5 – Refactor & Polish

- Improve UX around staggered starts:
  - Visual cues (e.g., “Waiting on X” label) based on status fields.
- Confirm that the toggle between modes preserves context (e.g., agent selection, history scroll position) where appropriate.

---

## TDD Specifications (Tests to Write First)

In addition to the main General mode tests:

**File**: `frontend/tests/unit/components/ImplementModeToggle.spec.ts` (NEW or updated)

Suggested tests:
- `test_switching_between_claude_and_general_modes_preserves_status_board_state`
- `test_mode_toggle_does_not_reset_message_history`

Tests must be written before implementing mode toggling logic or shared state behavior.

---

## Files to Create / Modify

New:
- `frontend/src/components/launch/ImplementGeneralMode.vue`
- `frontend/tests/unit/components/ImplementGeneralMode.spec.ts`
- `frontend/tests/unit/components/ImplementModeToggle.spec.ts` (if not present)

Modified:
- Implement tab shell (the component that chooses between Claude vs General mode).
- Any shared composables/helpers used for prompts or status calculations.

No new backend code should be introduced in this handover; it only consumes data based on LJ-000 contracts.

---

## Success Criteria & Completion Checklist

Must-have:
- [ ] General CLI mode matches slides 4a–4h in behavior and primary layout.
- [ ] Each agent has a unique CLI prompt and reuse indicator.
- [ ] Status board and history behave identically to Claude mode with the same underlying data.
- [ ] Staggered start/wait behavior is visibly represented.
- [ ] All new tests for General mode, mode toggle, and prompt behavior are passing with >80% coverage for new logic.

Nice-to-have:
- [ ] Documentation snippet showing when to choose Claude vs General mode for different workflows.
- [ ] Additional tests for edge cases (e.g., no agents, error states) if time permits.

Completion of LJ-003 provides a fully functional, test-backed General CLI mode, setting the stage for backend enhancements and regression coverage in LJ-004 and LJ-005.

