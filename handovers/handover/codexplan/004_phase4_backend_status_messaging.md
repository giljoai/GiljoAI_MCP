# Handover LJ-004: Backend Status & Messaging Wiring

**Feature**: Service-layer status board + message history for Launch/Implement  
**Status**: READY FOR IMPLEMENTATION  
**Priority**: P1 – HIGH  
**Estimated Time**: 2–4 days  
**Depends On**: LJ-000..LJ-003, 0322 Service Layer Compliance, 0324 Service Layer Test Refinement  
**Blocks**: LJ-005 (regression & template hardening)  
**Tool**: Claude Code CLI (multiple subagents)

---

## Executive Summary

LJ-002 and LJ-003 define and consume contracts for status boards, agent prompts, and message histories on the frontend. This handover delivers the corresponding backend wiring:

- Extend agent/job status enums and persistence to express Waiting / Working / Completed / Ack / Read counts.
- Provide service-layer methods and FastAPI endpoints that return contract-shaped payloads for:
  - Status board (per project/launch).
  - Per-agent prompts (Claude + General mode).
  - Message history (sent/received/ack/broadcast) with pagination and tenant scoping.
- Add structured telemetry around any legacy spawn paths used during these flows.

All changes must follow the service-layer pattern established in 0322 and tested/refined in 0324, with strict TDD.

---

## Problem Statement

Currently:
- Status and messaging information is sourced via existing job/agent tables and services, but:
  - Not all states needed by the deck (e.g., “Message Read”, “Job Acknowledged”) are exposed in a consolidated, contract-aligned way.
  - There is no dedicated status board endpoint for Launch/Implement.
  - Message history is not surfaced as a first-class, paginated, tenant-scoped API for UI consumption.
- Legacy orchestrator paths still exist; without telemetry, we cannot safely remove them.

We need a coherent backend surface that:
- Respects service-layer discipline and multi-tenancy.
- Provides contract-aligned payloads for LJ-002 and LJ-003.
- Is fully covered by tests written first.

---

## Scope

In scope:
- Status representation:
  - Confirm/enhance status enums for agents/jobs (Waiting, Working, Completed, etc.).
  - Add derived counts for:
    - Messages waiting.
    - Messages sent.
    - Messages read.
    - Job read.
    - Job acknowledged.
- Service methods:
  - `get_launch_implement_status_board(tenant_key, project_id, ...)`
  - `get_launch_implement_agent_prompts(tenant_key, project_id, mode)`
  - `get_launch_implement_message_history(tenant_key, project_id, agent_id, pagination, filters)`
- API endpoints:
  - Thin FastAPI endpoints calling the above service methods.
- Telemetry:
  - Structured logging for any `_spawn_generic_agent` usage during these flows.

Out of scope:
- Non-Launch/Implement usage of these services (existing behavior must not regress).
- New queueing or messaging infrastructure; reuse existing message/job/agent tables and repositories.

---

## Dependencies

- LJ-000:
  - Contracts for status board, prompts, message history.
- LJ-002, LJ-003:
  - UI components expecting data in those shapes.
- 0322, 0324:
  - Service layer patterns and test infrastructure improvements.

---

## Architectural & TDD Requirements

- Service-layer only:
  - Status and history logic must live in services (e.g., `OrchestrationService`, `MessageService`, `AgentJobManager`) and repositories.
  - FastAPI endpoints must be thin request/response translators.
- Multi-tenancy:
  - All queries must filter by `tenant_key` as described in 013A and 0322.
- TDD:
  - Write failing service-level tests first (Red).
  - Then write failing API integration tests.
  - Implement minimal code to pass tests (Green), then refactor.
  - Target >80% coverage for new service methods.

---

## Recommended Agent Setup (Claude Code CLI Subagents)

- **LJ-004-SVC (Service Implementor Agent, primary)**  
  - Implements service methods and coordinates repositories.

- **LJ-004-API (API Integration Agent, support)**  
  - Adds/updates FastAPI endpoints and ensures correct dependency wiring.

- **LJ-004-TEST (Backend Tester Agent, support)**  
  - Designs tests (unit + integration) per Quick Launch spec.

---

## Execution Plan

### Step 1 – Analyze Existing Status & Messaging Models

- Locate:
  - Agent/job models and enums (e.g., job status, agent state).
  - Messaging models and repositories (message direction, type, timestamps, ack).
  - Existing orchestration and message APIs under `api/endpoints`.
- Compare with LJ-000 contracts to identify:
  - Fields that already exist.
  - Derived values that need to be computed.

### Step 2 – Write Service-Level Tests (Red)

**File**: `tests/services/test_launch_implement_status_service.py` (NEW)

Suggested tests:
- `test_status_board_includes_all_agents_for_project_and_tenant`
- `test_status_board_counts_messages_waiting_sent_read_per_agent`
- `test_status_board_includes_job_read_and_ack_counts`
- `test_status_board_respects_tenant_isolation`

**File**: `tests/services/test_launch_implement_message_history_service.py` (NEW)

Suggested tests:
- `test_message_history_returns_sent_received_ack_broadcast_entries`
- `test_message_history_applies_pagination_and_ordering`
- `test_message_history_filters_by_agent_and_project`

Tests should:
- Use existing fixtures (db_session, tenant, project, agents, jobs).
- Populate messages/jobs with representative data.
- Assert on contract-shaped outputs, not internal query details.

### Step 3 – Implement Service Methods (Green)

- Add/extend service classes (example names):
  - `LaunchImplementStatusService` or methods on `OrchestrationService`.
  - `LaunchImplementMessageHistoryService` or methods on `MessageService`.
- Implement:
  - Aggregation queries that compute per-agent counts for board fields.
  - History fetch methods using existing message tables and filters.
- Ensure:
  - All queries are tenant-scoped.
  - Derived values (counts, statuses) match LJ-000 contracts.

### Step 4 – Write API Integration Tests (Red)

**File**: `tests/api/test_launch_implement_status_api.py` (NEW)

Suggested tests:
- `test_status_board_endpoint_returns_contract_shape_and_agent_rows`
- `test_status_board_endpoint_respects_tenant_isolation`

**File**: `tests/api/test_launch_implement_message_history_api.py` (NEW)

Suggested tests:
- `test_message_history_endpoint_returns_paginated_entries`
- `test_message_history_endpoint_filters_by_agent`

Use `httpx`/FastAPI test client, existing fixtures, and assert on JSON shapes.

### Step 5 – Implement API Endpoints (Green)

- Add endpoints under a logical path, e.g.:
  - `GET /api/v1/launch/{project_id}/status-board`
  - `GET /api/v1/launch/{project_id}/agents/{agent_id}/history`
- Each endpoint:
  - Uses dependency injection for services.
  - Retrieves current `tenant_key` from dependencies.
  - Calls service methods and returns contract-shaped responses.
  - Handles errors via domain-specific exceptions or HTTP 4xx/5xx.

### Step 6 – Telemetry for Legacy Spawn

- Ensure `_spawn_generic_agent` logging from LJ-000 includes context about whether newly added status board / history services are used in those flows.
- Optionally add a lightweight counter or metric (within existing logging framework) for how often legacy paths are triggered.

---

## TDD Specifications (Tests to Write First)

At minimum:
- Service tests for status board and message history as defined above.
- API tests for the new endpoints.

All tests must be present and failing before writing the actual implementations.

---

## Files to Create / Modify

New:
- `src/giljo_mcp/services/launch_implement_status_service.py` (or equivalent).
- `tests/services/test_launch_implement_status_service.py`
- `tests/services/test_launch_implement_message_history_service.py`
- `tests/api/test_launch_implement_status_api.py`
- `tests/api/test_launch_implement_message_history_api.py`

Modified:
- Existing orchestration/message service classes as needed to share helpers.
- `api/endpoints/...` modules to add new endpoints.
- Optional: `src/giljo_mcp/repositories/...` for any query helpers, following repository patterns.

---

## Success Criteria & Completion Checklist

Must-have:
- [ ] Service methods provide contract-aligned status board and message history for Launch/Implement.
- [ ] All new service tests pass with >80% coverage on new code.
- [ ] New API endpoints return correct shapes and respect tenant isolation.
- [ ] No regressions in existing job/agent/messaging APIs.
- [ ] Telemetry for `_spawn_generic_agent` is present and validated in tests.

Nice-to-have:
- [ ] Performance characteristics measured (e.g., basic benchmarks in tests).
- [ ] Small doc update in `docs/` or handovers summarizing new endpoints and payloads.

LJ-004 is complete when frontend modes (LJ-002, LJ-003) can rely solely on the new service-layer APIs for status and message history, and all tests (unit + integration) are green.

