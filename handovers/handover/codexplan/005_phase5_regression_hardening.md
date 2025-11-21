# Handover LJ-005: Regression & Template Hardening

**Feature**: End-to-end validation of Launch/Implement UX & backend wiring  
**Status**: READY FOR IMPLEMENTATION  
**Priority**: P2 – MEDIUM (quality + safety)  
**Estimated Time**: 2–3 days  
**Depends On**: LJ-000..LJ-004, 0310 Integration Testing & Validation, 0324 Service Layer Test Refinement  
**Blocks**: None (final validation handover for this series)  
**Tool**: Claude Code CLI (multiple subagents)

---

## Executive Summary

This handover validates the complete Launch/Implement experience end-to-end:

- Launch tab (LJ-001) staging and prompt flows.
- Implement tab Claude mode (LJ-002) and General mode (LJ-003).
- Backend status and message history wiring (LJ-004).

We will add integration/E2E tests, regression checks, and documentation so Launch/Implement becomes a stable, reusable visualization template for the product. The approach mirrors 0310 (Integration Testing & Validation) and 0324 (Service Layer Test Refinement): tests first, behavior-centric, with performance and multi-tenant safety in mind.

---

## Problem Statement

After implementing the previous handovers:
- Launch and Implement tabs will have new state machines, modes, and data flows.
- Backend services will provide new status/history endpoints.
- Existing projects/products/settings UI may be impacted by changes in shared components or stores.

Without targeted integration testing and regression coverage:
- We risk subtle breakages in related views.
- We lack confidence to treat the new Launch/Implement UI as a “template visualization” for other products.

We need a dedicated validation phase, executed with TDD, that promotes the Launch/Implement flow from “feature implemented” to “template-grade, regression-protected”.

---

## Scope

In scope:
- Integration and E2E tests for:
  - Full Launch → Implement (Claude mode) happy path.
  - Full Launch → Implement (General mode) happy path.
  - Failure scenarios: clipboard blocked, status API error, message history error.
  - Multi-tenant isolation for status/history.
- Cross-view regression checks:
  - Projects view.
  - Products view.
  - Settings views (User/System) where shared components or stores are used.
- Telemetry verification:
  - Confirm that legacy `_spawn_generic_agent` is not used in standard Launch/Implement flows.
- Documentation updates:
  - Short description of the Launch/Implement template.
  - Instructions for reusing it in new products.

Out of scope:
- New features or UX expansion beyond the current spec.
- Deep performance tuning (basic checks only).

---

## Dependencies

- Previous handovers LJ-000..LJ-004 are implemented and unit-tested.
- Baseline integration frameworks are available (see 0310).
- Service layer tests from 0324 are passing (so unit infrastructure is stable).

---

## Architectural & TDD Requirements

- Follow 0310-style integration testing:
  - Focus on realistic workflows rather than synthetic unit scenarios.
  - Use existing fixtures and APIs as a real client would.
- Behavior-first tests:
  - Assert user-observable outcomes (UI states, responses) rather than internal method calls.
- Multi-tenant:
  - Integration tests must verify that tenant A cannot see tenant B’s jobs, agents, or messages.
- Performance:
  - Basic timing checks to ensure status/history endpoints and Launch/Implement flows remain responsive.

---

## Recommended Agent Setup (Claude Code CLI Subagents)

- **LJ-005-E2E (E2E Tester Agent, primary)**  
  - Designs and implements end-to-end tests and flows.

- **LJ-005-REG (Regression Agent, support)**  
  - Runs and interprets cross-view regression checks.

- **LJ-005-DOC (Documentation Agent, support)**  
  - Updates handovers and README-style docs with final template description.

---

## Execution Plan

### Step 1 – Define Test Scenarios

Happy paths:
- HP1: Launch → Stage project → Launch Jobs → Implement (Claude mode) → orchestrator and subagents complete mission with correct statuses and histories.
- HP2: Launch → Stage project → Launch Jobs → Implement (General mode) → multi-terminal prompts used; statuses/histories correct.

Failure paths:
- FP1: Clipboard API blocked/throws error when copying prompts.
- FP2: Status board endpoint fails (e.g., 500); UI error state.
- FP3: Message history endpoint returns error; history panel behavior.

Multi-tenant:
- MT1: Tenant A’s Launch/Implement flows do not surface Tenant B’s agents, messages, or jobs.

### Step 2 – Write Integration/E2E Tests (Red)

**File**: `tests/integration/test_launch_implement_e2e.py` (NEW)

Suggested tests:
- `test_launch_to_implement_claude_mode_happy_path`
- `test_launch_to_implement_general_mode_happy_path`
- `test_launch_implement_flow_isolated_per_tenant`

Each test should:
- Use API client/fixtures to set up a product, project, and agents.
- Call Launch/Stage/Launch Jobs endpoints.
- Fetch status board and message history.
- Assert that:
  - Status board and histories match expected states after orchestrator/subagents run.
  - No cross-tenant leaks.

**File**: `tests/integration/test_launch_implement_failure_paths.py` (NEW)

Suggested tests:
- `test_claude_mode_handles_clipboard_failure_gracefully` (if simulated via frontend harness or backend assumption).
- `test_status_board_endpoint_failure_results_in_clear_error_state`
- `test_message_history_endpoint_failure_results_in_clear_error_state`

### Step 3 – Cross-View Regression Checks

If an automated UI/E2E harness exists:
- Add checks or scripted flows for Projects/Products/Settings verifying key screens still render and basic actions work.

If not:
- Add backend-level regression tests where Launch/Implement-related changes may affect shared services.
- Document a manual regression checklist if required.

### Step 4 – Telemetry Verification

- Add a simple test or script to:
  - Simulate standard Launch/Implement flows.
  - Inspect logs/metrics to confirm that `_spawn_generic_agent` is not invoked.
- If it is invoked, document and open a follow-up handover for decommissioning.

### Step 5 – Documentation & Template Hardening

- Update:
  - `handovers/handover/codexplan/launch_implementation_ui_refactor_plan.md` with a short “Execution status” note.
  - Any relevant `README` or architecture docs with:
    - A brief description of the Launch/Implement template.
    - When to choose Claude vs General mode.
    - How status/history data is wired from backend to frontend.

---

## TDD Specifications (Tests to Write First)

Integration tests must be written before:
- Any additional glue code for Launch/Implement is added.
- Any changes to endpoints in response to failure scenarios.

All tests should follow Quick Launch conventions:
- Descriptive names (e.g., `test_launch_to_implement_claude_mode_happy_path`).
- Behavior-driven assertions, not internal details.

---

## Files to Create / Modify

New:
- `tests/integration/test_launch_implement_e2e.py`
- `tests/integration/test_launch_implement_failure_paths.py`

Modified:
- Any necessary helper fixtures or conftest modules for test setup.
- Optionally, documentation files under `handovers/` and `docs/`.

---

## Success Criteria & Completion Checklist

Must-have:
- [ ] Happy path tests for Claude and General modes pass.
- [ ] Failure path tests for clipboard and API failures pass (UI/behavior degrades gracefully).
- [ ] Multi-tenant isolation for Launch/Implement flows verified at integration level.
- [ ] No regressions detected in Projects/Products/Settings flows.
- [ ] Telemetry confirms `_spawn_generic_agent` is not used in standard Launch/Implement flows.

Nice-to-have:
- [ ] Basic performance expectations captured (e.g., status board responses under a reasonable threshold).
- [ ] Documentation clearly marks Launch/Implement as a reusable template and references these tests.

When LJ-005 is complete, the Launch/Implement refactor is fully validated and ready to be treated as a product template visualization, backed by tests and documentation.

