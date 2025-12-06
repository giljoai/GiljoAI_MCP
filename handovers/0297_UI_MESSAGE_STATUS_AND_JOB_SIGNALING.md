# Handover 0297: UI Message Status & Job Signaling Alignment

## Status: IN PROGRESS (0297a complete)
## Priority: HIGH
## Type: Frontend + API Integration
## Depends On: 0295 (Messaging contract), 0296 (Template behavior)

---

## 1. Goal

Make the **Jobs/Implementation dashboard** accurately and consistently display:

- **Messages Sent / Waiting / Read** per agent card.
- **Job status** (waiting, working, blocked, complete, failed, cancelled, decommissioned).
- **Job Acknowledged** indicator showing when an agent has received its mission.

All of this must be driven by:

- The **messages contract** (0295) for message counters.
- The **job lifecycle/signaling** APIs for status chips and acknowledgment.

No UI component should have to guess based on mixed signals.

---

## 2. Current State (as of 0297a)

- Backend now emits:
  - `message:sent` events for sender counters.
  - `message:received` events for recipient counters.
  - `job:mission_acknowledged` events when agent fetches its mission.
  - Message data is mirrored into `MCPAgentJob.messages` JSONB for persistence.
- Handover 0297a fixed real-time message counter updates via global WebSocket handlers.
- Remaining work:
  - "Job Acknowledged" column not fully wired to UI.
  - Tests not yet written.

We maintain a clear separation:

- **Messages** → counters and message center.
- **Signals** → job status chips, progress, and acknowledgment.

---

## 3. Required Behavior

### 3.1 Message Counters (Per Agent Card)

**Status: COMPLETE (0297a)**

For each visible agent/job on the Implementation tab:

- **Messages Sent**:
  - Count of outbound messages this agent has sent (from JSONB mirror OR computed from `messages` table).
- **Messages Waiting**:
  - Count of inbound messages for this agent that are:
    - Addressed to this agent or to "all" (broadcast), and
    - Not yet acknowledged by this agent.
- **Messages Read**:
  - Count of inbound messages this agent has acknowledged.

Initial values should be derived from persisted JSONB state on load; live updates should be driven by WebSocket events.

### 3.2 Job Acknowledged Column

**Status: NOT STARTED**

The "Job Acknowledged" column indicates whether an agent has received its mission from the orchestrator.

**Semantics:**
- **Job Acknowledged = True**: Agent has called `get_agent_mission()` or `acknowledge_job()` MCP tool
- **Job Acknowledged = False**: Agent has not yet fetched its mission (job is waiting to be picked up)

**Database field:** `MCPAgentJob.mission_acknowledged_at` (nullable DateTime)
- `NULL` = not acknowledged
- Timestamp = when agent first fetched its mission

**WebSocket event:** `job:mission_acknowledged`
- Emitted when `get_agent_mission()` is called for the first time
- Payload: `{ job_id, mission_acknowledged_at, timestamp }`

**UI Display:**
- Checkmark (✓) when `mission_acknowledged_at` is not null
- Empty or dash (-) when null

This is **job lifecycle signaling**, completely separate from the messaging system.

### 3.3 Job Status (Signals)

Job status chips should continue to reflect:

- `waiting`, `working`, `blocked`, `complete`, `failed`, `cancelled`, `decommissioned`.

Driven by:

- WebSocket events from `AgentJobManager` (`job:status_changed`, `job:progress_updated`).

No messaging fields should be used to infer status.

---

## 4. Files to Update

### 4.1 Backend: API for Initial Data

**Likely files:**

- `api/endpoints/projects/jobs.py` or equivalent jobs endpoint

Tasks:

1. Ensure job list endpoints include `mission_acknowledged_at` field in response.
2. Ensure per-job message counters are derived from `MCPAgentJob.messages` JSONB.
3. Make sure values are tenant-scoped and project-scoped correctly (multi-tenant safe).

### 4.2 Backend: WebSocket Events

**Status: COMPLETE**

**Files:**

- `api/websocket.py`
- `api/websocket_event_listener.py`
- `api/websocket_service.py`

Already implemented:

- `broadcast_message_sent` and `broadcast_message_received` events for message counters.
- `job:mission_acknowledged` event emitted from `get_agent_mission()` MCP tool.

### 4.3 Frontend: Stores & Components

**Files:**

- `frontend/src/stores/projectTabs.js` (message handlers added in 0297a)
- `frontend/src/stores/websocketIntegrations.js` (global listeners added in 0297a)
- `frontend/src/components/projects/JobsTab.vue`
- `frontend/src/components/StatusBoard/JobReadAckIndicators.vue` (if exists)

Tasks:

1. On initial load:
   - Read `mission_acknowledged_at` from jobs endpoint.
   - Initialize local state for Job Acknowledged per job.
2. On WebSocket events:
   - `job:mission_acknowledged` → set Job Acknowledged = true for that job.
3. Display checkmark in Job Acknowledged column based on `mission_acknowledged_at`.

---

## 5. TDD Plan

### 5.1 Backend Tests

**Files:**

- `tests/api/test_jobs_endpoint_message_counters.py`
- `tests/websocket/test_job_acknowledged_events.py`

Suggested tests:

- `test_jobs_endpoint_includes_mission_acknowledged_at()`
  - Create a project with several jobs.
  - Call `get_agent_mission()` for some jobs.
  - Call the jobs listing endpoint.
  - Assert `mission_acknowledged_at` is set for acknowledged jobs, null for others.
- `test_get_agent_mission_emits_websocket_event()`
  - Call `get_agent_mission()` for a job.
  - Assert `job:mission_acknowledged` WebSocket event is emitted.
- `test_get_agent_mission_idempotent()`
  - Call `get_agent_mission()` twice for same job.
  - Assert timestamp doesn't change on second call.

### 5.2 Frontend Tests

**Files:**

- `frontend/tests/unit/JobsTabAcknowledged.spec.js`

Tests:

- `renders_job_acknowledged_checkmark_when_mission_acknowledged_at_set()`
- `renders_empty_when_mission_acknowledged_at_null()`
- `updates_job_acknowledged_on_websocket_event()`

Follow Vue test patterns already used in the repo; keep tests focused on behavior, not implementation details.

---

## 6. Constraints

- **Do not refactor messaging semantics here** – that's covered by 0295.
- **Do not introduce new WebSocket event types** unless strictly necessary; prefer using existing events.
- Respect `install.py` and existing tests:
  - No DB schema changes expected in this handover (`mission_acknowledged_at` already exists).

---

## 7. Acceptance Criteria

1. On a clean install, with a staged project and spawned agents:
   - The Jobs tab displays correct "Messages Sent / Waiting / Read" for each agent.
   - "Job Acknowledged" column shows checkmark when agent has fetched its mission.
2. WebSocket updates keep the UI in sync without requiring page refresh.
3. All new backend and frontend tests pass.

---

## 8. Completed Sub-Handovers

### 0297a: Real-time Message Counter WebSocket Fix

**Status:** COMPLETE (commit bef0f509)

Fixed real-time message counter updates via global WebSocket handlers in `websocketIntegrations.js`. See `0297a_SESSION_REALTIME_MESSAGE_COUNTERS.md` for details.

---

## 9. Remaining Work

| Task | Status | Priority |
|------|--------|----------|
| Job Acknowledged column in UI | NOT STARTED | HIGH |
| Backend tests for `mission_acknowledged_at` | NOT STARTED | MEDIUM |
| Frontend tests for Job Acknowledged | NOT STARTED | MEDIUM |
| Verify initial load counters from API | NEEDS VERIFICATION | LOW |
