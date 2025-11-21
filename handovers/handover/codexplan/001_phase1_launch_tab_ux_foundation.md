# Handover LJ-001: Launch Tab UX Foundation

**Feature**: Launch tab staged states (1a–1e) with staging flow & clipboard prompt  
**Status**: READY FOR IMPLEMENTATION  
**Priority**: P1 – HIGH  
**Estimated Time**: 1–2 days  
**Depends On**: LJ-000 (state map & contracts), 0322 Service Layer Compliance  
**Blocks**: LJ-002..LJ-005 (Implement tab phases)  
**Tool**: Claude Code CLI (multiple subagents)

---

## Executive Summary

This handover brings the Launch tab into alignment with deck slides 1a–1e by implementing a clear, testable state machine: pre-staging empty, orchestrator ready, staging “working”, and mission-filled with Launch Jobs enabled. It also ensures that the Implement tab is navigable but clearly inactive until staging completes, matching the “Launch faded” behavior in slide 1c.

We will implement the “Stage project” action through existing service-layer patterns, copy the orchestrator start prompt to the clipboard, and surface a reuse indicator once copied—all under strict TDD discipline.

---

## Problem Statement

Today the Launch tab:
- Does not explicitly represent all deck states (1a–1e).
- Does not clearly separate pre-staging vs staging vs staged states in a way that is easy to test.
- Does not fully encode the copy-to-clipboard + reuse behavior for the orchestrator start prompt.
- Does not strongly signal that the Implement tab is inactive before staging.

We need a predictable, observable state machine and a test-locked UX that matches the visual spec.

---

## Scope

In scope:
- Implement Launch tab visual and behavioral states corresponding to slides 1a–1e:
  - 1a: Pre-staging (project not staged; Implement tab empty).
  - 1b: Tabs navigable, Implement layout empty; no agents/activation buttons.
  - 1c: Implement tab faded/inactive with “Please Stage Project First” messaging.
  - 1d: Stage button ready; orchestrator is the default agent.
  - 1e: User presses “Stage project”, receives a CLI prompt, and pastes into Claude Code CLI.
- Implement “Stage project” action that:
  - Calls an existing service-layer method (`ProjectService` / orchestration service) to create a staged mission.
  - Copies the start prompt to the clipboard via a testable utility.
  - Sets a “reuse” indicator showing the prompt has been used (but re-copy is allowed).
- Drive an “Implement tab inactive” flag based on staged status.

Out of scope:
- Implement tab detailed UI/content (LJ-002, LJ-003).
- Any new backend endpoints or schema changes (reuse existing services identified in LJ-000).

---

## Dependencies

- LJ-000:
  - Provides the mapping from deck slides to existing views/routes.
  - Provides contracts for mission payloads and staged status fields.
- Existing services:
  - Project/Launch/Orchestrator-related service classes and endpoints identified in LJ-000.

---

## Architectural & TDD Requirements

- Reuse existing service-layer patterns:
  - Do not embed DB or complex logic in the Launch view.
  - Use existing service factories/dependencies to trigger staging.
- Apply TDD (Quick Launch discipline):
  - Define the Launch state machine via tests first.
  - Tests assert behavior: visible states, enabled/disabled buttons, clipboard effects—not component internals.
  - Coverage target for new tests: >80%.
- Keep the view decomposable:
  - If the Launch view grows, extract focused child components (e.g., `LaunchStagePanel`, `StageProjectButton`) instead of adding inline complexity.

---

## Recommended Agent Setup (Claude Code CLI Subagents)

- **LJ-001-UX (Launch UX Agent, primary)**  
  - Owns the UI state machine design and component implementation.

- **LJ-001-SVC (Service Integration Agent, support)**  
  - Ensures that staging uses existing services/endpoints and respects `tenant_key`.

- **LJ-001-TEST (Test Author Agent, support)**  
  - Designs and implements behavior-centric tests and fixtures.

---

## Execution Plan

### Step 1 – Define Launch State Machine (on paper)

States (recommended):
- `idle_empty` – project not ready to stage; Launch button inactive or hidden.
- `idle_ready` – project ready to stage; Stage button visible/active.
- `staging` – Stage button pressed; spinner visible; awaiting mission.
- `staged` – mission created; Launch Jobs enabled; prompt available for copy.

For each state, define:
- Deck slide mapping (1a, 1b, 1c, 1d, 1e).
- Visible elements (labels, buttons, info text).
- Allowed user actions (what buttons are enabled).

### Step 2 – Write Tests (Red)

**File**: `frontend/tests/unit/views/LaunchTabView.spec.ts` (NEW or updated)

Suggested tests:
- `test_launch_tab_renders_idle_empty_state_before_project_is_ready`
- `test_launch_tab_shows_orchestrator_ready_state_before_staging`
- `test_stage_project_triggers_service_call_and_shows_spinner`
- `test_stage_project_enables_launch_jobs_after_success`
- `test_stage_project_copies_prompt_to_clipboard_and_sets_reuse_flag`
- `test_implement_tab_is_faded_and_inactive_before_staging`

Tests should:
- Mock/stub service-layer calls to staging (not raw HTTP).
- Spy on a shared clipboard utility (e.g., `clipboard.copy(text)`).
- Assert on:
  - Button enablement.
  - Spinner presence during `staging`.
  - Text/labels aligned to the deck.

### Step 3 – Implement Minimal UI & Wiring (Green)

Frontend:
- Update Launch tab view (e.g., `ProjectLaunchView.vue` or equivalent) to:
  - Compute the state (`idle_empty`, `idle_ready`, `staging`, `staged`) from project/staging data.
  - Render the correct section of UI for each state.
  - Invoke a `stageProject()` action that:
    - Calls an injected service method.
    - Awaits mission/staged status.
    - Updates the state to `staged`.
    - Feeds the CLI prompt into the clipboard utility and set `hasPromptBeenCopied` flag.

Service integration:
- Reuse existing `ProjectService` or orchestrator service methods.
- Ensure any API calls:
  - Include `tenant_key`.
  - Return mission/staged status consistent with LJ-000 contracts.

### Step 4 – Refactor & Polish

- If needed, extract:
  - `LaunchStatePanel` – responsible for rendering states 1a–1e.
  - `StageProjectButton` – handles staging call + clipboard copy.
- Ensure text copy and icons match the deck’s visual language where it adds clarity.

---

## TDD Specifications (Tests to Write First)

In addition to the main view tests:

**File**: `frontend/tests/unit/utils/clipboard.spec.ts` (NEW)

Suggested tests:
- `test_clipboard_copy_is_called_with_launch_prompt_text`
- `test_clipboard_copy_failure_shows_user_friendly_error` (if error UX exists)

All of these tests must be written before implementing the clipboard utility or Launch tab behavior changes.

---

## Files to Create / Modify

New:
- `frontend/tests/unit/views/LaunchTabView.spec.ts` (or analogous existing test file extended with new cases).
- `frontend/tests/unit/utils/clipboard.spec.ts` (if not present).

Modified:
- Launch tab view (likely `frontend/src/views/ProjectLaunchView.vue` and/or related components).
- Any store/service wrapper used to call staging endpoints.

No backend schema or endpoint changes are expected in this handover.

---

## Success Criteria & Completion Checklist

Must-have:
- [ ] Launch tab states behave as in slides 1a–1e (verified via tests).
- [ ] Implement tab is clearly inactive/faded before staging completes.
- [ ] “Stage project” triggers service-layer staging, shows spinner, and enables Launch Jobs.
- [ ] CLI prompt is copied to the clipboard and reuse indicator is set.
- [ ] All new tests for Launch tab and clipboard utilities are passing.
- [ ] No new service-layer violations introduced (endpoint handlers remain thin).

Nice-to-have:
- [ ] Launch state machine documented (small diagram or markdown table) in this file or a linked doc.
- [ ] Additional small tests verifying that UI gracefully handles staging failure (if that case is supported).

Completion of LJ-001 unlocks the Implement tab work in LJ-002 and LJ-003.

