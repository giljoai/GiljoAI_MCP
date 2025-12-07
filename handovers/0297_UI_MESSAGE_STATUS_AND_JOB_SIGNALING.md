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
- A lightweight **Steps** indicator per job showing how far an agent is through its own TODO/plan (e.g., `3/5`).

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

- **Messages** → counters and message center (including narrative plan/progress).
- **Signals** → job status chips, numeric progress/steps, and acknowledgment.

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

### 3.4 Steps Column (Numeric TODO / Plan Progress)

**Status: NOT STARTED**

We want a simple, non-intrusive visual indicator of how far an agent is through its own plan or TODO list, without turning the dashboard into a full checklist UI.

**Column name (UI label):** `Steps`  
**Placement:** In the Jobs/Implementation table:

- Swap the order of the existing **Agent Status** and **Job Acknowledged** columns so the left-to-right order becomes:
  - `Agent Type`, `Agent ID`, `Job Acknowledged`, `Agent Status`, `Steps`, `Messages Sent`, `Messages Waiting`, `Messages Read`, `Actions`.
- Insert the new **Steps** column between **Agent Status** and **Messages Sent**.

**Signal source:** `report_progress(job_id, progress)` MCP tool (no new endpoint, no new WebSocket event type).

We repurpose `report_progress` for **numeric milestone/TODO tracking** while keeping narrative detail in the message hub:

- When an agent creates or updates its plan, it MAY call:

  ```jsonc
  {
    "mode": "todo",
    "total_steps": 5,
    "completed_steps": 3,
    "current_step": "Writing tests for edge cases"
  }
  ```

- Backend behavior (OrchestrationService.report_progress):
  - Continue to route progress via the existing MessageService / WebSocket machinery (no new event types).
  - Persist the latest `total_steps`, `completed_steps`, and `current_step` for each job in the existing progress/message structures (e.g., in the JSONB message mirror used for counters).

- UI behavior for the **Steps** column:
  - If the latest progress payload for a job has `mode == "todo"` and both `total_steps` and `completed_steps`:
    - Display `completed_steps/total_steps` (e.g., `3/5`) and optionally a small progress bar.
  - If no TODO-style progress has been reported for a job:
    - Display an em dash (`—`) or leave the cell empty (no guessing or derived values).

**Narrative plan and after-action details** are intentionally kept out of `report_progress` to avoid token bloat and schema complexity:

- Agents should send their full TODO list / plan via `send_message(..., message_type="plan")`.
- During execution, agents can send narrative updates via `send_message(..., message_type="progress" | "note")`.
- Completion summaries and lessons learned belong in `complete_job(job_id, result)` (e.g., `summary`, `deliverables`, `tests`, `lessons_learned` fields).

The **Steps** column is only a numeric front-door into that richer history; the detailed view will be provided by the Message Audit Modal (Handover 0331).

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
   - Read `mission_acknowledged_at` and any persisted `steps` metadata (if present) from the jobs endpoint / JSONB progress mirror.
   - Initialize local state for Job Acknowledged and Steps per job.
2. On WebSocket events (must **reuse existing infrastructure**):
   - `job:mission_acknowledged` → set Job Acknowledged = true for that job.
   - Existing progress/message-related events (e.g., `progress`, `message:new` / `message:sent` / `message:received` as wired by 0297a) → update the Steps count when a new `report_progress(..., mode="todo")` payload arrives for that job.
   - All new listeners must be registered through `websocketIntegrations.js` and existing stores; **do not introduce any new WebSocket event types or protocols**.
3. Display:
   - Checkmark in Job Acknowledged column based on `mission_acknowledged_at`.
   - `completed_steps/total_steps` in the new **Steps** column when TODO-style progress exists; otherwise, an em dash (`—`). Column layout must remain responsive and not regress the current dashboard behavior.

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

- **Dashboard is currently working and MUST NOT be broken.**
  - All changes must be incremental and fully covered by tests.
  - Column reorder + new **Steps** column must preserve existing behavior for status, acknowledgment, and message counters.
- **Do not refactor messaging semantics here** – that's covered by 0295.
- **Do not introduce new WebSocket event types or a new WebSocket “methodology”.**
  - All real-time updates must flow through the existing WebSocket pipeline and `websocketIntegrations.js`.
  - It is acceptable to add new listeners/handlers for existing event types.
- Respect `install.py` and existing tests:
  - No DB schema changes expected in this handover (`mission_acknowledged_at` already exists).
  - Any additional persisted progress metadata for Steps must reuse existing JSONB/message structures, not a new table.

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
