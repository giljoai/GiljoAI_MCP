# Handover 0297: UI Message Status & Job Signaling Alignment

## Status: READY FOR IMPLEMENTATION  
## Priority: HIGH  
## Type: Frontend + API Integration  
## Depends On: 0295 (Messaging contract), 0296 (Template behavior)

---

## 1. Goal

Make the **Jobs/Implementation dashboard** accurately and consistently display:

- **Messages Sent / Waiting / Read** per agent card.
- **Job status** (waiting, working, blocked, complete, failed, cancelled, decommissioned).
- **Job read / job acknowledged** flags derived from messaging behavior.

All of this must be driven by:

- The **messages contract** (0295) for message counters.
- The **job lifecycle/signaling** APIs for status chips.

No UI component should have to guess based on mixed signals.

---

## 2. Current State (as of 0294)

- Backend now emits:
  - `message:sent` events for sender counters.
  - `message:received` events for recipient counters.
  - Message data is mirrored into `MCPAgentJob.messages` JSONB for persistence.
- Handover 0294 fixed major WebSocket architecture issues, but some UI issues remain:
  - Counters may still appear only on orchestrator cards.
  - “Job read” / “Job acknowledged” columns aren’t fully wired.
  - Some data is recomputed on the client even though the server now persists it.

We want to complete this work with a clear separation:

- **Messages** → counters and message center.
- **Signals** → job status chips and progress.

---

## 3. Required Behavior

### 3.1 Message Counters (Per Agent Card)

For each visible agent/job on the Implementation tab:

- **Messages Sent**:
  - Count of outbound messages this agent has sent (from JSONB mirror OR computed from `messages` table).
- **Messages Waiting**:
  - Count of inbound messages for this agent that are:
    - Addressed to this agent or to “all” (broadcast), and
    - Not yet acknowledged by this agent.
- **Messages Read**:
  - Count of inbound messages this agent has acknowledged.

Initial values should be derived from persisted JSONB state on load; live updates should be driven by WebSocket events.

### 3.2 Job Read / Job Acknowledged Columns

Define semantics (tie to 0295/0296 behavior):

- **Job Read**:
  - `True` when the current agent has **zero** pending messages in “Messages Waiting”.
  - `False` when there is at least one unacknowledged message for that job.
- **Job Acknowledged**:
  - `True` when the agent has acknowledged at least one message for this job.
  - May be displayed as a boolean or as a timestamp of last acknowledgment.

These columns should **not** inspect low‑level message internals – they should rely on a simple derived state from counters and acknowledgments.

### 3.3 Job Status (Signals)

Job status chips should continue to reflect:

- `waiting`, `working`, `blocked`, `complete`, `failed`, `cancelled`, `decommissioned`.

Driven by:

- WebSocket events from `AgentJobManager` (`job:status_changed`, `job:progress_updated`).

No messaging fields should be used to infer status.

---

## 4. Files to Update

### 4.1 Backend: API for Initial Counters

**Likely files:**

- `src/giljo_mcp/services/orchestration_service.py`
- `src/giljo_mcp/services/project_service.py`
- `src/giljo_mcp/services/message_service.py` (JSONB persistence already present)
- `api/endpoints/projects/jobs.py` or equivalent jobs endpoint

Tasks:

1. Ensure that job list endpoints used by the Jobs tab:
   - Include per‑job message counters derived from `MCPAgentJob.messages` JSONB.
   - Or at least expose the raw `messages` JSONB so the UI can compute counters consistently.
2. Make sure values are tenant‑scoped and project‑scoped correctly (multi‑tenant safe).

### 4.2 Backend: WebSocket Events

**Files:**

- `api/websocket.py`
- `api/websocket_event_listener.py`
- `api/websocket_service.py`

Ensure:

- `broadcast_message_sent` and `broadcast_message_received` events:
  - Provide enough information for the front‑end to update counters for the correct agent/job.
  - Are **consistent** with the JSONB persistence logic in `MessageService._persist_message_to_agent_jsonb`.
- `broadcast_message_acknowledged` events:
  - Update “Messages Waiting” and “Messages Read” counters for relevant agents.
  - Allow the UI to recalc the “Job Read / Job Acknowledged” columns.

### 4.3 Frontend: Stores & Components

**Files:**

- `frontend/src/stores/agentStore.ts` or equivalent (e.g. `useAgentData.js`)
- `frontend/src/views/jobs/JobsTab.vue` (or equivalent Jobs view)
- Any composables around WebSocket events (`useWebSocket.js`)

Tasks:

1. On initial load:
   - Read counters (or raw JSONB) from the jobs endpoint.
   - Initialize local state for messages sent/waiting/read per job.
2. On WebSocket events:
   - `message:sent` → increment “Messages Sent” for sender job.
   - `message:received` → increment “Messages Waiting” for each recipient job.
   - `message:acknowledged` → decrement “Messages Waiting” and increment “Messages Read” for that job.
3. Derive “Job Read” and “Job Acknowledged” columns purely from these counters.

---

## 5. TDD Plan

### 5.1 Backend Tests

**Files:**

- `tests/api/test_jobs_endpoint_message_counters.py`
- `tests/websocket/test_message_counter_events.py`

Suggested tests:

- `test_jobs_endpoint_includes_message_counters_per_job()`
  - Create a project with several jobs and messages.
  - Call the jobs listing endpoint.
  - Assert counters reflect the underlying `MCPAgentJob.messages` JSONB.
- `test_websocket_events_update_counters_correctly()`
  - Use a WebSocket test client to:
    - Simulate `message:sent`, `message:received`, `message:acknowledged`.
    - Assert that client‑side state (or a mock handler) would derive correct counters.

### 5.2 Frontend Tests

**Files:**

- `frontend/tests/unit/JobsTabMessageCounters.spec.ts` (or `.js`)

Tests:

- `renders_initial_counters_from_api_payload()`
- `updates_counters_on_message_sent_and_received_events()`
- `updates_job_read_and_job_acknowledged_based_on_counters()`

Follow Vue test patterns already used in the repo; keep tests focused on behavior, not implementation details.

---

## 6. Constraints

- **Do not refactor messaging semantics here** – that’s covered by 0295.
- **Do not introduce new WebSocket event types** unless strictly necessary; prefer using the existing `message:sent`, `message:received`, `message:acknowledged`, `job:status_changed`, `job:progress_updated`.
- Respect `install.py` and existing tests:
  - No DB schema changes expected in this handover.

---

## 7. Acceptance Criteria

1. On a clean install, with a staged project and spawned agents:
   - The Jobs tab displays correct “Messages Sent / Waiting / Read” for each agent.
   - “Job Read / Job Acknowledged” columns behave as defined.
2. WebSocket updates keep the UI in sync without requiring page refresh.
3. All new backend and frontend tests pass.


