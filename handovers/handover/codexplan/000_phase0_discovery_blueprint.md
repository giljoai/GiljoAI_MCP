# Handover LJ-000: Launch/Implement Discovery & Contracts

**Feature**: Launch / Implement deck alignment & backend contracts  
**Status**: READY FOR IMPLEMENTATION  
**Priority**: P1 – HIGH  
**Estimated Time**: 4–6 hours  
**Depends On**: 0322 Service Layer Compliance (complete), 013A Architecture Status, code_review_nov18  
**Blocks**: LJ-001..LJ-005 (later phases consume these contracts)  
**Tool**: Claude Code CLI (multiple subagents)

---

## Executive Summary

Before changing any UI or backend code, we need a precise, shared blueprint that maps the Launch/Implement deck states to real routes, components, and service endpoints. This handover produces that blueprint plus test-first contracts for the status board, per-agent prompts, mission text, and message history. It also adds low-risk telemetry around legacy orchestrator spawn paths so future phases can safely deprecate them.

This is a planning + contract definition task, executed using strict TDD: we write tests that describe the required shapes and behaviors first, then introduce minimal scaffolding so those tests compile (but still fail on behavior). No user-visible behavior changes are made in this phase.

---

## Problem Statement

The Launch/Implement experience must match the visual specification in `handovers/Launch-Jobs_panels2/Refactor visuals for launch and implementation.pdf`. Today:

- Routing and component responsibilities for Launch vs Implement vs Jobs are implicit and scattered.
- Status and messaging data shapes are inferred from usage, not codified contracts.
- Legacy orchestrator spawn logic (`_spawn_generic_agent`) still exists but is not instrumented, making deprecation risky.

We need a clear map from deck states (1a–1e, 2a–2c, 3a–3i, 4a–4h) to concrete code artifacts + test-locked contracts for all data flowing into the new UI.

---

## Scope

In scope:
- Map existing Launch / Implement / Jobs flows to deck states:
  - Launch tab: slides 1a–1e.
  - Orchestrator “working/finished”: slides 2a–2c.
  - Implement tab (Claude Code CLI mode): slides 3a–3i.
  - Implement tab (General CLI mode): slides 4a–4h.
- Identify all backend and frontend integration points needed for:
  - Status board (per-agent, per-job).
  - Per-agent terminal prompts (Claude mode + General mode).
  - Mission/staging prompt text.
  - Message history (sent/received/ack/broadcast) with pagination/filter.
- Define test-first contracts (schemas, DTOs, or Pydantic models) describing these payloads.
- Add non-invasive structured logging around `_spawn_generic_agent` to detect any legacy usage during later phases.

Out of scope:
- Any visible UI or behavior change.
- Database schema changes.
- New endpoints or service methods (only contract definitions + logging hook).

---

## Current State (from 013A + code_review_nov18)

- Jobs / Agents / Orchestration are ~72–75/100: strong new flow, but legacy spawn paths exist.
- Frontend Projects/Launch/Jobs flows work but are not fully aligned with the new Launch/Implement deck.
- Service-layer discipline is not yet 100% but is the target (see 0322).
- No explicit “status board contract” or “message history contract” exists as a first-class concept.

---

## Objectives

Primary goals:
1. Produce a state map tying each deck slide to:
   - Route.
   - Top-level view component.
   - Key child components and props.
2. Define explicit contracts for:
   - `LaunchImplementStatusBoardPayload`
   - `LaunchImplementAgentPromptPayload`
   - `LaunchImplementMissionPayload`
   - `LaunchImplementMessageHistoryEntry`
3. Add structured telemetry around `_spawn_generic_agent` to detect real-world use.
4. Lock these contracts in via tests written first, without changing external behavior.

Success criteria:
- State map is complete for all deck states (1a–1e, 2a–2c, 3a–3i, 4a–4h).
- Contract tests exist and fail on behavior until later phases implement them.
- Logging for `_spawn_generic_agent` is present, structured, and covered by tests.
- No regressions in existing tests or behavior.

---

## Inputs & References

- Visual spec: `handovers/Launch-Jobs_panels2/Refactor visuals for launch and implementation.pdf`
- Architecture reviews:
  - `handovers/013A_code_review_architecture_status.md`
  - `handovers/code_review_nov18.md`
- Flow & vision:
  - `handovers/start_to_finish_agent_FLOW.md`
  - `handovers/Simple_Vision.md`
- Existing code:
  - Launch/Projects/Jobs views (frontend).
  - Orchestration and agent job services/endpoints (backend).

---

## Architectural & TDD Requirements

- Read `code_review_nov18.md` and `013A_code_review_architecture_status.md` before drafting any contracts.
- Follow Quick Launch TDD discipline:
  - Tests FIRST (Red), then minimal code (Green), then refactor.
  - Tests describe behavior (what fields must exist, how they are shaped), not specific internals.
  - Use descriptive names like `test_status_board_contract_includes_counts_and_statuses`.
  - Target >80% coverage for new contract-related code.
- Service layer only:
  - Contracts should line up with service-layer responses, not raw ORM models.
  - No new logic in FastAPI endpoints; later phases will wire services to these contracts.

---

## Recommended Agent Setup (Claude Code CLI Subagents)

- **LJ-000-ARCH (Architect Agent, primary)**  
  - Reads handovers + deck.  
  - Owns the state map and contract design.

- **LJ-000-FE (Frontend Mapping Agent)**  
  - Walks Vue routes and components.  
  - Maps deck slides to concrete components/props.

- **LJ-000-BE (Backend Mapping Agent)**  
  - Walks orchestration and job services/endpoints.  
  - Identifies candidate data sources for status board and history.

Agents work in parallel with their own context windows, then merge results into this handover and a shared contract file.

---

## Execution Plan

### Step 1 – Read & Align (LJ-000-ARCH)
- Read the deck and all listed handovers.
- Produce a short narrative:
  - Where Launch/Implement fits in `start_to_finish_agent_FLOW.md`.
  - Which deck states are “Launch tab only” vs “Implement tab only”.

### Step 2 – Map Views & Routes (LJ-000-FE)
- Locate:
  - Launch/Projects views (e.g., `ProjectLaunchView.vue` and related tabs/components).
  - Jobs/agents status views (Jobs tab, message boards).
- For each deck slide (1a–1e, 2a–2c, 3a–3i, 4a–4h), record:
  - Route/path.
  - Primary Vue component.
  - Key reactive state fields and props.
- Save as `handovers/handover/codexplan/000_state_map_launch_implement.md`.

### Step 3 – Map Backend Contracts (LJ-000-BE)
- Identify relevant services/endpoints:
  - Orchestration service(s).
  - Agent job/status endpoints.
  - Messaging endpoints.
- Draft candidate Pydantic models (or equivalent typed shapes) for:
  - Status board rows (agent type, status, counts).
  - Agent prompts (label, CLI text, reuse flags).
  - Mission payload (project, mission text, tenant_key).
  - Message history entries (direction, type, timestamps, ack flags).
- Ensure every contract includes `tenant_key` or is scoped via a tenant-aware service.

### Step 4 – Add Legacy Spawn Telemetry
- In `src/giljo_mcp/orchestrator.py` (or equivalent):
  - Add structured logging around `_spawn_generic_agent`, including:
    - `tenant_key`
    - `role`
    - `has_template` flag
  - Do not change control flow or outcomes.

---

## TDD Specifications (Tests to Write First)

### Contract Tests

**File**: `tests/unit/contracts/test_launch_implement_status_contracts.py` (NEW)

Suggested tests:
- `test_status_board_contract_includes_required_fields`
  - Asserts that the status board payload exposes agent id, agent type, status, messages_sent, messages_read, job_read_count, ack_count.
- `test_status_board_contract_includes_tenant_key_for_multi_tenancy`
  - Ensures tenant scoping is explicit or documented.

**File**: `tests/unit/contracts/test_launch_implement_message_history_contracts.py` (NEW)

Suggested tests:
- `test_message_history_contract_includes_sent_received_ack_broadcast`
- `test_message_history_contract_supports_pagination_and_filtering`

### Telemetry Test

**File**: `tests/unit/orchestrator/test_legacy_spawn_logging.py` (NEW)

Suggested test:
- `test_legacy_spawn_logging_includes_role_and_tenant_key`
  - Uses a stubbed orchestrator instance; asserts logger is called with structured fields when `_spawn_generic_agent` executes.

All tests are written before any concrete implementation of the contracts beyond simple class or schema stubs.

---

## Files to Create / Modify

New:
- `handovers/handover/codexplan/000_state_map_launch_implement.md`
- `tests/unit/contracts/test_launch_implement_status_contracts.py`
- `tests/unit/contracts/test_launch_implement_message_history_contracts.py`
- `tests/unit/orchestrator/test_legacy_spawn_logging.py`

Modified:
- `src/giljo_mcp/orchestrator.py` (logging only, no behavior change)
- Optional: a shared `schemas/launch_implement.py` or similar contract module (if patterns in 013A suggest a location).

---

## Success Criteria & Completion Checklist

Must-have:
- [ ] State map exists and covers all deck states (1a–1e, 2a–2c, 3a–3i, 4a–4h).
- [ ] Contract tests for status board and message history are present and failing (Red) before implementation.
- [ ] Telemetry test for `_spawn_generic_agent` exists and passes once logging is wired.
- [ ] No existing tests fail due to these changes.

Nice-to-have:
- [ ] Contract module documented with docstrings referencing this handover.
- [ ] Quick diagram (plantuml or markdown) describing data flow Launch → Implement → Orchestrator.

This handover is complete when all “Must-have” items are satisfied and the contract files and tests are ready to be consumed by LJ-001..LJ-005.

