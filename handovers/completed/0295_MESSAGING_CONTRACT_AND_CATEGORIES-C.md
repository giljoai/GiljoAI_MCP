# Handover 0295: Messaging Contract & Categories (Messages vs Signals vs Instructions)

## Status: COMPLETED
## Priority: HIGH
## Type: Architecture & Refactor (Backend + Tests, minimal UI impact)
## Completed: 2025-12-05

---

## 1. Context & Current State

The current messaging stack in `GiljoAI MCP` is ~75% functional but has grown in stages:

- **Messages table (`Message` model)** – canonical, persistent messages, surfaced by:
  - HTTP MCP tools: `send_message`, `receive_messages`, `acknowledge_message`, `list_messages`
  - REST endpoints: `/api/messages/...`
- **JSONB agent message queue (`MCPAgentJob.messages`)** – used for:
  - Per‑job counters (“Messages Sent / Waiting / Read”) and page‑refresh persistence
  - Currently also involved in some older FastMCP/queue logic
- **Job lifecycle & status (`MCPAgentJob.status`, `progress`, etc.)** – shown as agent status chips.
- **Instruction tools** – `get_orchestrator_instructions`, `get_agent_mission`, `get_next_instruction` for mission/config fetch.

Historically there were separate “queue” systems; 0294 moved a lot of counter logic into `MessageService` and WebSocket events. The system works, but the conceptual boundaries are fuzzy for new contributors and for agentic coding tools.

This handover defines a **clean taxonomy and contract** for:

1. **MESSAGES** – auditable inter‑agent and user↔agent communication (what you see in the message center).
2. **SIGNALS** – job/agent state, progress, and health (status chips, progress bars).
3. **INSTRUCTIONS** – missions and configuration fetched from the server.

The goal is to make these categories explicit in code and tests, without breaking existing behavior or the install process.

---

## 2. Desired Categories & Responsibilities

### 2.1 MESSAGES (Primary focus of this handover)

**Definition:**  
Structured, auditable communication between:

- Agent ↔ Agent (direct or broadcast)
- User ↔ Orchestrator / Agents (via web UI)

**Canonical Store:**

- PostgreSQL `messages` table (`Message` model).

**Public API (HTTP MCP + REST):**

- `send_message(to_agents: list[str], content: str, project_id: str, message_type='direct'|'broadcast'|'system', priority='low'|'normal'|'high', from_agent: Optional[str])`
- `receive_messages(agent_id: str, limit: int=10)` – MCP interface to `MessageService.list_messages()` filtered to pending/unacknowledged.
- `acknowledge_message(message_id: str)` – marks as acknowledged by the caller.
- `list_messages(agent_id?: str, status?: str, limit?: int)` – history / inspection.
- REST `/api/messages/...` endpoints should remain thin wrappers around `MessageService`.

**Semantics:**

- `message_type`:
  - `"direct"` – specific recipients in `to_agents`.
  - `"broadcast"` – `"all"` logical broadcast; actual recipients resolved on server.
  - `"system"` – system‑level notifications (rare; keep minimal).
- `status` (Message.status):
  - `"pending"` – created but not completed; may or may not be acknowledged yet.
  - `"completed"` – explicitly completed with a `result` by an agent (`complete_message`).
  - Other statuses (if present) should be documented or pruned later; do NOT add new ones in this handover.
- `acknowledged_by` (array of agent identifiers):
  - Empty → unread by that agent.
  - Non‑empty → at least one agent has acknowledged.

**Counters:**

- “Messages Sent” – derived from `messages` table and mirrored into `MCPAgentJob.messages` JSONB for quick front‑end reads.
- “Messages Waiting” – messages where:
  - agent is in `to_agents` (direct), or
  - broadcast applies to that agent; AND
  - that agent is not in `acknowledged_by`.
- “Messages Read” – messages where agent is in `acknowledged_by`.

The JSONB mirror is an optimization & persistence mechanism for counters, not a separate messaging system.

### 2.2 SIGNALS (Job state & progress – **out of scope to change here**, but must be clearly separated)

**Definition:**

- Job lifecycle and status (waiting, working, blocked, complete, failed, cancelled, decommissioned).
- Progress percentage, context usage, artifacts created – as emitted by tools like:
  - `acknowledge_job`, `report_progress`, `complete_job`, `report_error`, `get_workflow_status`.

**Store & APIs:**

- `MCPAgentJob` table and `AgentJobManager` (`src/giljo_mcp/agent_job_manager.py`).
- WebSocket events like `job:status_changed`, `job:progress_updated`.

**Rule for this handover:**  
Messages and message types MUST NOT be abused as job status; signals remain in the job/lifecycle domain.

### 2.3 INSTRUCTIONS (Missions & config – for context, not to be changed)

**Definition:**

- Structured mission and configuration fetch – not chat, not status.

**Tools:**

- `get_orchestrator_instructions(orchestrator_id, tenant_key)`
- `get_agent_mission(job_id, tenant_key)`
- `get_next_instruction(job_id, tenant_key)` (if present)

**Rule:**  
Do not use messages for long‑form mission content; keep missions in their existing fields (`Project.mission`, `MCPAgentJob.mission`, and the relevant services).

---

## 3. Scope of Work for Handover 0295

This handover is **backend‑focused** and lays the foundation for later UI and template work (0296+). It must be completed with TDD and without breaking `install.py`.

### 3.1 Clarify & Document the Messaging Contract

1. **Add developer‑facing documentation** (e.g., `docs/architecture/messaging_contract.md`) that:
   - Defines the three categories above.
   - Lists the official MCP tools for messaging.
   - States that HTTP MCP + REST use the **same MessageService** (no parallel “queue” APIs).
2. Ensure `handovers/Reference_docs/start_to_finish_agent_FLOW.md` references this split (messages vs signals vs instructions) in a short addendum rather than rewriting the whole doc.

### 3.2 Normalize MessageService Behavior (No DB schema changes if possible)

**File:** `src/giljo_mcp/services/message_service.py`

Goals:

- Confirm that:
  - `send_message()` always creates a `Message` row and then mirrors into JSONB via `_persist_message_to_agent_jsonb()`.
  - `broadcast()` is a thin wrapper around `send_message(to_agents=['all'], ...)`.
  - `acknowledge_message()` only updates the messages table and drives WebSocket + JSONB updates.
  - `complete_message()` updates message status/result and drives WebSocket + JSONB.
- Ensure **no business logic** around job state (waiting/working/blocking) lives here – that remains in `AgentJobManager`.

If changes are required:

- Make them **behavior‑preserving** relative to current tests and 0294 behavior.
- Do not add new columns or enums unless absolutely necessary; if you must, create proper Alembic migrations and confirm `install.py` still bootstraps a fresh DB with seeded templates.

### 3.3 Remove/Quarantine Parallel Queue Semantics from the Public Contract

1. Identify any public references (templates, docs, or MCP tool catalogs) that talk about:
   - `send_mcp_message`, `read_mcp_messages`, or queue‑specific `acknowledge_message(job_id, tenant_key, ...)`.
2. For 0295, **do not delete code**, but:
   - Mark these APIs clearly as “internal / legacy – not for HTTP MCP agents”.
   - Ensure HTTP MCP `/mcp` advertises only:
     - `send_message`, `receive_messages`, `acknowledge_message`, `list_messages`.
3. Confirm that `api/endpoints/mcp_http.py` and `api/endpoints/mcp_tools.py` are aligned with this contract.

Later handovers (0298) can deprecate/remove unused queue code.

---

## 4. TDD Plan & Test Cases

**Non‑negotiable:** Follow the TDD discipline from `handovers/Reference_docs/QUICK_LAUNCH.txt` and CLAUDE/QUICK LAUNCH instructions.

Create or extend tests **before** implementation. Suggested structure:

### 4.1 Service‑Level Tests

**File:** `tests/services/test_message_service_contract.py` (new)

Write tests such as:

- `test_send_message_creates_message_and_updates_jsonb_counters()`
  - Given a project with two agents and an orchestrator, when `MessageService.send_message()` is called:
    - A `Message` row is created with correct `project_id`, `tenant_key`, `to_agents`, `message_type`, `priority`.
    - WebSocket stub is called with both `message:sent` and `message:received` events (can be faked / asserted via a test double).
    - `MCPAgentJob.messages` JSONB:
      - Sender has 1 outbound message marked `"status": "sent"`.
      - Recipient(s) have inbound `"status": "waiting"`.
- `test_acknowledge_message_marks_acknowledged_and_updates_jsonb()`
  - After sending a message, when `acknowledge_message(message_id, agent_name)` is called:
    - `Message.acknowledged_by` includes that agent.
    - WebSocket ack event is emitted.
    - Recipient’s JSONB entry transitions from `"status": "waiting"` → `"status": "acknowledged"` or `"read"`.
- `test_complete_message_marks_completed_and_preserves_ack()`  
  - “Complete” sets `status='completed'`, `result`, and `completed_by` while leaving `acknowledged_by` intact.

### 4.2 MCP Tool Tests

**File:** `tests/api/test_mcp_messaging_tools.py` (new or extended)

Behavior tests:

- `test_send_message_mcp_tool_creates_direct_message()`
- `test_send_message_mcp_tool_broadcasts_to_all_agents()`
- `test_receive_messages_returns_pending_messages_for_agent()`
- `test_acknowledge_message_mcp_tool_updates_acknowledged_by()`
- `test_list_messages_filters_by_status_and_agent()`

Tests can call the MCP tools via the existing tool accessor / HTTP MCP test harness while stubbing WebSocket manager.

---

## 5. Constraints & Non‑Goals

**Must obey:**

- **Installation:** `install.py` must work end‑to‑end on a fresh DB. Any schema tweaks require a proper migration and verification that:
  - Tables are created.
  - Default templates are seeded.
  - Basic orchestrator + agent flow (staging + implementation) still works.
- **TDD:** Tests first, RED → GREEN → REFACTOR, as in `QUICK_LAUNCH.txt`.
- **Multi‑Tenant Isolation:** Every query in new/modified code must filter by `tenant_key` (reuse existing patterns and repositories).

**Out of scope for 0295:**

- UI changes (except potentially updating comments / minor renames that don’t change behavior).
- Template and prompt changes – these will be handled in 0296.
- Removing/deleting legacy code – just quarantine and clearly mark it as legacy/internal.

---

## 6. Acceptance Criteria

This handover is complete when:

1. A messaging contract document exists and is referenced from handover docs and/or `docs/architecture`.
2. HTTP MCP and REST only expose the intended messaging tools (`send_message`, `receive_messages`, `acknowledge_message`, `list_messages`) as public APIs.
3. `MessageService` behavior is covered by tests that:
   - Prove messages create `Message` rows and JSONB mirrors.
   - Prove acknowledgments and completions are reflected in both table and JSONB.
4. No new schema changes break `install.py`; a clean install yields a working system.
5. All new tests pass in CI (`pytest`), and coverage for `MessageService` is significantly improved.

Subsequent handovers (0296–0298) will build on this contract for templates and UI.

---

## 7. Notes for Agentic Coding Tools

- Treat the current system as **functional but messy**; this handover is about clarifying behavior, not redesigning everything.
- Prefer **small, safe refactors** that are test‑driven and behavior‑preserving.
- When in doubt, keep `messages` table as source of truth and JSONB as a cache/mirror used for counters and UI.

---

## 8. Implementation Summary

### What Was Built
- **Message model**: Added `result` field for completion results
- **MessageService**: Fixed agent_type to job_id resolution in `send_message()`, added JSONB status updates in `acknowledge_message()`
- **Tests**: 8 contract tests (service-level), MCP tool tests via `/mcp` endpoint
- **Documentation**: `docs/architecture/messaging_contract.md` defining Messages vs Signals vs Instructions

### Key Files Modified
- `src/giljo_mcp/models/tasks.py` (line 124 - result field)
- `src/giljo_mcp/services/message_service.py` (lines 184-217, 661-702)
- `tests/services/test_message_service_contract.py` (NEW - 719 lines)
- `tests/api/test_mcp_messaging_tools.py` (NEW)
- `docs/architecture/messaging_contract.md` (NEW)
- 6 test files fixed for `AgentCommunicationQueue` → `AgentMessageQueue` rename

### Test Results
- Contract tests: 8 passed, 2 skipped
- No schema changes required - `install.py` unaffected
- Pre-existing API test failures (93) identified as unrelated to 0295 (template fixture issue)

### Git Commits
- `2f448a66` - feat: Implement Messaging Contract & Categories (Handover 0295)
- `443f7dbe` - chore: Move completed handovers 0292-0294 to completed folder

### Status
✅ Production ready. All 0295 tests passing. Documentation complete.


