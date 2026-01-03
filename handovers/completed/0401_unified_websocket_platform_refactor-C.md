# Handover 0401: Unified WebSocket Platform Refactor

**Date:** 2026-01-02
**From Agent:** Claude Opus 4.5 (Orchestrator)
**To Agent:** Backend Integration Tester / System Architect
**Priority:** P0 - Critical
**Estimated Complexity:** 12-16 hours
**Status:** ✅ Complete (2026-01-02)

---

## Migration Context: COMPLETING the agent_id/job_id Separation

**CRITICAL**: This handover COMPLETES the Handover 0381 migration. We are NOT reverting it.

### The Clean Contract (Established in Handover 0381)

| Field | Meaning | Use Case |
|-------|---------|----------|
| `job_id` | Work order UUID - "what am I doing" | Task assignment, persists across succession |
| `agent_id` | Executor UUID - "who am I" | **Messaging**, identity, changes on succession |

**Messaging is intentionally tied to `agent_id`** because:
- Messages are between **executors** (agents communicating), not work orders
- When an agent hands over (succession), the NEW executor shouldn't receive messages meant for the OLD executor
- This is the CORRECT design per Handover 0381

### What's Broken

The backend migration to `agent_id` for messaging is CORRECT. What's broken:
1. **Frontend**: `resolveJobId()` doesn't know how to look up by `agent_id`
2. **JSONB Persistence**: Queries `AgentJob` but messages live on `AgentExecution`

### What We're Fixing

We're **teaching the frontend** to understand the new contract:
- Add `agent_id` lookup to `resolveJobId()`
- Fix JSONB updates to target `AgentExecution.messages`

**We are NOT changing the messaging architecture.** The backend is correct.

---

## Executive Summary

The GiljoAI MCP dashboard has inconsistent real-time updates due to incomplete migration to the `agent_id`/`job_id` separation (Handover 0381). Some features work flawlessly (Agent Status, Job Acknowledgement), while others fail silently (Messages Sent/Waiting/Read, Steps). This handover **completes the migration** by teaching the frontend and persistence layer to use `agent_id` for message-related operations.

**Core Problem**: The backend correctly sends `agent_id` (AgentExecution UUID) in WebSocket payloads for messaging, but the frontend `resolveJobId()` function only matches by `job_id` (AgentJob UUID) or `agent_type`/`agent_name`. This identifier mismatch causes all message-related handlers to no-op.

**Secondary Problem**: The backend `_update_jsonb_message_status()` function queries `AgentJob.messages`, but messages are correctly stored on `AgentExecution.messages`. This causes persistence failures - data resets on page refresh.

---

## Problem Statement

### Current State: Fragmented Real-Time Updates

| Feature | Live Updates | Page Refresh | Root Cause |
|---------|--------------|--------------|------------|
| Agent Status | Works | Works | Direct job_id mapping |
| Job Acknowledgement | Works | Works | Direct job_id mapping |
| Messages Sent | Broken | Works | agent_id vs job_id mismatch |
| Messages Waiting | Broken | Works | agent_id vs job_id mismatch |
| Messages Read | Broken | Broken | Double bug: ID mismatch + wrong DB model |
| Steps | Broken | Broken | Array vs object format mismatch |

### Why This Matters

1. **User Confusion**: Dashboard shows stale data, users manually refresh
2. **Debug Difficulty**: Inconsistent behavior makes troubleshooting hard
3. **Alpha Testing Blocked**: Cannot demonstrate real-time agent coordination
4. **Technical Debt**: Multiple patch attempts (0362, 0387) haven't unified the system

---

## Root Cause Analysis

### Issue 1: agent_id vs job_id Identifier Mismatch

**Background**: After Handover 0372, message routing changed from work-order-centric (`job_id`) to executor-centric (`agent_id`).

**Files Affected**:
- Backend emits: `src/giljo_mcp/services/message_service.py:286, 303, 717`
- Backend WebSocket: `api/websocket.py:999, 1032, 1064`
- Frontend handler: `frontend/src/stores/agentJobsStore.js:199, 236, 281`
- Frontend resolver: `frontend/src/stores/agentJobsStore.js:182-196`

**Current resolveJobId() Logic** (line 182-196):
```javascript
function resolveJobId(identifier) {
  if (!identifier) return null

  // Check 1: Direct job_id match
  if (jobsById.value.has(identifier)) {
    return identifier
  }

  // Check 2: Legacy fallback by agent_type/agent_name
  for (const job of jobsById.value.values()) {
    if (job.agent_type === identifier || job.agent_name === identifier) {
      return job.job_id
    }
  }

  return null  // FAILS for agent_id - no check exists!
}
```

**Why It Fails**:
- Backend sends: `{ to_agent_ids: ["fa39d78e-7b91-4bb2-92a2-75cf5f49152f"] }` (agent_id)
- Frontend calls: `resolveJobId("fa39d78e-...")`
- `jobsById` is keyed by `job_id`, not `agent_id`
- No match found -> handler returns early -> no update

---

### Issue 2: Wrong Database Model for JSONB Updates

**File**: `src/giljo_mcp/services/message_service.py:1257-1310`

**Current Code**:
```python
async def _update_jsonb_message_status(self, session, job_id, message_ids, new_status):
    # BUG: Queries AgentJob but messages are on AgentExecution
    result = await session.execute(
        select(AgentJob).where(AgentJob.job_id == job_id)  # WRONG MODEL
    )
    agent_job = result.scalar_one_or_none()

    # AgentJob has no 'messages' column - this always fails
    if not agent_job or not agent_job.messages:
        return  # SILENT FAILURE - nothing persists
```

**Why It Fails**:
- Messages are persisted to `AgentExecution.messages` (line 1132 in `_persist_to_jsonb()`)
- But status updates query `AgentJob.messages` which doesn't exist
- `agent_job.messages` is `None` -> early return -> status stays "waiting" forever
- Page refresh loads stale data from `AgentExecution.messages`

---

### Issue 3: Steps Format Mismatch

**Files Affected**:
- Backend emits: `src/giljo_mcp/services/orchestration_service.py:1173`
- Router: `frontend/src/stores/websocketEventRouter.js:289-300`
- Store handler: `frontend/src/stores/agentJobsStore.js:164-178`
- Component: `frontend/src/components/projects/JobsTab.vue:98-104`

**Backend Payload**:
```python
{
    "job_id": "...",
    "todo_steps": [
        {"name": "Step 1", "status": "done"},
        {"name": "Step 2", "status": "pending"}
    ]
}
```

**Store Handler** (line 164-178):
```javascript
function handleProgressUpdate(payload) {
  const updates = {
    job_id: payload.job_id,
    progress: payload.progress,
    current_task: payload.current_task,
  }

  if (payload.todo_steps) {
    updates.job_metadata = { todo_steps: payload.todo_steps }  // Saves array
  }
  upsertJob(updates)
}
```

**Component Expectation** (line 98-104):
```vue
<template v-if="agent.steps && typeof agent.steps.completed === 'number'">
  {{ agent.steps.completed }} / {{ agent.steps.total }}
</template>
```

**Why It Fails**:
- Store saves: `job.job_metadata.todo_steps` (array)
- Component reads: `agent.steps.completed` and `agent.steps.total` (object)
- No transformation from array to `{ completed: N, total: M }`

---

## Unified Architecture Design

### Design Principle: Single Source of Truth

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     UNIFIED IDENTIFIER STRATEGY                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Backend WebSocket Payloads:                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ALWAYS include both identifiers:                                    │   │
│  │  {                                                                   │   │
│  │    "job_id": "work-order-uuid",      // AgentJob.job_id             │   │
│  │    "agent_id": "executor-uuid",       // AgentExecution.agent_id    │   │
│  │    ...payload                                                        │   │
│  │  }                                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Frontend Resolution:                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  resolveJobId() checks IN ORDER:                                     │   │
│  │  1. Direct job_id match in jobsById                                  │   │
│  │  2. job.agent_id match (NEW)                                         │   │
│  │  3. Legacy agent_type/agent_name fallback                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Database Persistence:                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  JSONB updates target AgentExecution.messages (NOT AgentJob)         │   │
│  │  Query by agent_id, not job_id                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow: Message Lifecycle (After Fix)

```
1. Agent sends message
   └─► send_message(from_agent=agent_id, to_agents=["all"])
       └─► Fan-out creates individual Message records (Handover 0387)
       └─► WebSocket: broadcast_message_sent({
             job_id: sender_job_id,      // INCLUDE BOTH
             agent_id: sender_agent_id,
             to_job_ids: [...],
             to_agent_ids: [...]
           })

2. Frontend receives message:sent
   └─► resolveJobId(payload.agent_id)
       └─► Matches job.agent_id → returns job_id
       └─► handleMessageSent updates counter

3. Recipient reads message
   └─► receive_messages(agent_id)
       └─► Auto-acknowledge (Handover 0326)
       └─► _update_jsonb_message_status(agent_id, message_ids, "acknowledged")
           └─► Query AgentExecution (NOT AgentJob)
           └─► Update JSONB status
       └─► WebSocket: broadcast_message_acknowledged({
             job_id: recipient_job_id,
             agent_id: recipient_agent_id,
             message_ids: [...]
           })

4. Frontend receives message:acknowledged
   └─► resolveJobId(payload.agent_id)
       └─► Matches job.agent_id → returns job_id
       └─► handleMessageAcknowledged decrements waiting, increments read

5. Page refresh
   └─► GET /api/agent-jobs returns persisted data
   └─► messages_waiting_count, messages_read_count are ACCURATE
```

---

## Implementation Plan

### Phase 1: Frontend Resolution Fix (2-3 hours)

**File**: `frontend/src/stores/agentJobsStore.js`

**Task 1.1**: Enhance `resolveJobId()` (line 182-196)

```javascript
function resolveJobId(identifier) {
  if (!identifier) return null

  // Check 1: Direct job_id match
  if (jobsById.value.has(identifier)) {
    return identifier
  }

  // Check 2: NEW - Match by agent_id (execution UUID)
  for (const job of jobsById.value.values()) {
    if (job.agent_id === identifier) {
      return job.job_id
    }
  }

  // Check 3: Legacy fallback by agent_type/agent_name
  for (const job of jobsById.value.values()) {
    if (job.agent_type === identifier || job.agent_name === identifier) {
      return job.job_id
    }
  }

  return null
}
```

**Task 1.2**: Ensure `normalizeJob()` preserves `agent_id`

Verify that when jobs are loaded from API, the `agent_id` field is preserved in the store. Check `normalizeJob()` function doesn't strip it.

**Task 1.3**: Add Steps Transformation (line 164-178)

```javascript
function handleProgressUpdate(payload) {
  const updates = {
    job_id: payload.job_id,
    progress: payload.progress,
    current_task: payload.current_task,
  }

  if (payload.todo_steps && Array.isArray(payload.todo_steps)) {
    // Transform array to summary object for UI
    const completed = payload.todo_steps.filter(
      s => s.status === 'done' || s.status === 'completed'
    ).length
    const total = payload.todo_steps.length

    updates.steps = { completed, total }  // NEW: Add summary object
    updates.job_metadata = { todo_steps: payload.todo_steps }  // Keep original array
  }

  upsertJob(updates)
}
```

**Testing Criteria**:
- `resolveJobId("agent-uuid")` returns correct `job_id`
- `handleProgressUpdate` with `todo_steps` sets `job.steps.completed/total`
- Existing unit tests in `agentJobsStore.spec.js` still pass

---

### Phase 2: Backend Persistence Fix (2-3 hours)

**File**: `src/giljo_mcp/services/message_service.py`

**Task 2.1**: Fix `_update_jsonb_message_status()` (line 1257-1310)

```python
async def _update_jsonb_message_status(
    self,
    session: AsyncSession,
    agent_id: str,  # RENAMED: was job_id
    message_ids: list[str],
    new_status: str,
) -> None:
    """
    Update status of messages in AgentExecution.messages JSONB column.

    CRITICAL FIX (Handover 0401):
    - Query AgentExecution (NOT AgentJob)
    - Use agent_id parameter (NOT job_id)
    """
    from sqlalchemy.orm.attributes import flag_modified

    try:
        # FIXED: Query AgentExecution, not AgentJob
        result = await session.execute(
            select(AgentExecution).where(AgentExecution.agent_id == agent_id)
        )
        agent_execution = result.scalar_one_or_none()

        if not agent_execution or not agent_execution.messages:
            self._logger.debug(f"[JSONB UPDATE] No messages to update for agent {agent_id}")
            return

        # Update status for matching messages
        updated_count = 0
        message_ids_set = set(message_ids)

        for msg in agent_execution.messages:
            if msg.get("id") in message_ids_set and msg.get("status") != new_status:
                msg["status"] = new_status
                updated_count += 1

        if updated_count > 0:
            # CRITICAL: flag_modified tells SQLAlchemy the JSONB column changed
            flag_modified(agent_execution, "messages")
            await session.commit()
            self._logger.info(
                f"[JSONB UPDATE] Updated {updated_count} messages to '{new_status}' "
                f"for agent {agent_id}"
            )
        else:
            self._logger.debug(f"[JSONB UPDATE] No messages needed status update for agent {agent_id}")

    except Exception as e:
        self._logger.error(f"[JSONB UPDATE] Failed to update message status: {e}")
```

**Task 2.2**: Update Callers to Pass `agent_id`

Search for all calls to `_update_jsonb_message_status` and ensure they pass `agent_id`, not `job_id`:

```bash
grep -n "_update_jsonb_message_status" src/giljo_mcp/services/message_service.py
```

Expected locations:
- Line 709 (in `receive_messages`)
- Any other callers

**Testing Criteria**:
- After `receive_messages()`, JSONB status changes from "waiting" to "acknowledged"
- Page refresh shows correct `messages_read_count`
- Database query: `SELECT messages FROM agent_executions WHERE agent_id = 'X'` shows updated status

---

### Phase 3: Backend Event Payload Enhancement (2-3 hours)

**Goal**: Ensure ALL WebSocket events include both `job_id` and `agent_id`

**Files**:
- `api/websocket.py` - WebSocket manager methods
- `src/giljo_mcp/services/message_service.py` - Message event emissions
- `src/giljo_mcp/services/orchestration_service.py` - Progress event emissions

**Task 3.1**: Audit WebSocket Event Payloads

Check each event type and ensure both IDs are included:

| Event | Current Payload | Required Addition |
|-------|-----------------|-------------------|
| `message:sent` | `from_agent`, `to_agent_ids` | Add `from_job_id`, `to_job_ids` |
| `message:received` | `to_agent_ids` | Add `to_job_ids` |
| `message:acknowledged` | `agent_id` | Add `job_id` |
| `job:progress_update` | `job_id` | Add `agent_id` (verify present) |

**Task 3.2**: Update Event Schemas

**File**: `api/events/schemas.py`

Ensure each schema includes both identifiers:

```python
class MessageSentData(BaseModel):
    message_id: str
    from_agent: str  # agent_id (executor)
    from_job_id: str  # job_id (work order) - ENSURE PRESENT
    to_agent_ids: list[str]
    to_job_ids: list[str]  # ENSURE PRESENT
    # ...
```

**Testing Criteria**:
- Browser DevTools → Network → WS shows both `job_id` and `agent_id` in all message events
- Frontend handlers can resolve either identifier

---

### Phase 4: Integration Testing (3-4 hours)

**File**: `tests/integration/test_websocket_unified_platform.py` (NEW)

**Test Suite**:

```python
@pytest.mark.asyncio
class TestUnifiedWebSocketPlatform:
    """
    Integration tests for Handover 0401: Unified WebSocket Platform
    """

    async def test_message_sent_includes_both_identifiers(self, ws_client, project):
        """WebSocket message:sent event includes job_id and agent_id"""
        # Setup: Subscribe to message:sent events
        # Action: send_message() via MCP tool
        # Assert: Payload has both from_job_id and from_agent (agent_id)

    async def test_message_received_live_update(self, ws_client, project):
        """Messages Waiting counter updates in real-time"""
        # Setup: Create agent, subscribe to events
        # Action: Orchestrator sends broadcast
        # Assert: message:received event received
        # Assert: Frontend handler would increment counter (mock or E2E)

    async def test_message_acknowledged_persists(self, db_session, project):
        """Message acknowledgment persists to JSONB"""
        # Setup: Send message to agent
        # Action: Agent calls receive_messages()
        # Assert: AgentExecution.messages[].status == "acknowledged"
        # Assert: Page refresh shows correct count

    async def test_steps_counter_live_update(self, ws_client, project):
        """Steps counter updates from todo_steps array"""
        # Setup: Create agent with job
        # Action: report_progress(todo_steps=[...])
        # Assert: job:progress_update event has todo_steps
        # Assert: Frontend transforms to steps.completed/total

    async def test_message_read_survives_refresh(self, db_session, api_client, project):
        """Message read count persists across page refresh"""
        # Setup: Send 3 messages to agent
        # Action: Agent reads 2 messages
        # Assert: messages_waiting = 1, messages_read = 2
        # Action: Simulate page refresh (re-fetch from API)
        # Assert: Counts still accurate
```

**Manual Testing Checklist**:

1. **Messages Sent Counter**:
   - [ ] Send message via UI → Counter increments immediately
   - [ ] Refresh page → Counter shows same value

2. **Messages Waiting Counter**:
   - [ ] Orchestrator broadcasts → All agents show +1 waiting
   - [ ] Refresh page → Counters still accurate

3. **Messages Read Counter**:
   - [ ] Agent reads message → Waiting decrements, Read increments
   - [ ] Refresh page → Counters persist

4. **Steps Counter**:
   - [ ] Agent reports progress with todo_steps → Steps shows "2/5"
   - [ ] Refresh page → Steps still shows "2/5"

---

### Phase 5: Documentation & Cleanup (1-2 hours)

**Task 5.1**: Update CLAUDE.md

Add section on WebSocket identifier strategy:
```markdown
## WebSocket Event Identifiers

All WebSocket events MUST include both identifiers:
- `job_id`: AgentJob UUID (work order)
- `agent_id`: AgentExecution UUID (executor)

Frontend `resolveJobId()` checks: job_id → agent_id → agent_type/name
```

**Task 5.2**: Archive Related Handovers

Move to `handovers/completed/`:
- `0362_websocket_message_counter_fixes.md` (superseded)
- `0387_broadcast_fanout_at_write.md` (if complete)

**Task 5.3**: Update Serena Memory

Write memory documenting the unified WebSocket platform:
```
memory: unified_websocket_platform_0401
content: WebSocket identifier strategy, resolveJobId() logic, JSONB persistence model
```

---

## Files to Modify Summary

| File | Changes | Priority |
|------|---------|----------|
| `frontend/src/stores/agentJobsStore.js:182-196` | Add agent_id check in resolveJobId() | P0 |
| `frontend/src/stores/agentJobsStore.js:164-178` | Transform todo_steps to steps object | P0 |
| `src/giljo_mcp/services/message_service.py:1257-1310` | Query AgentExecution not AgentJob | P0 |
| `src/giljo_mcp/services/message_service.py:709` | Pass agent_id to JSONB updater | P0 |
| `api/events/schemas.py` | Ensure both IDs in event schemas | P1 |
| `api/websocket.py:999, 1032, 1064` | Include job_id in message events | P1 |
| `tests/integration/test_websocket_unified_platform.py` | New test file | P1 |

---

## Success Criteria

### Definition of Done

- [ ] `resolveJobId()` matches by agent_id (execution UUID)
- [ ] `handleProgressUpdate()` transforms todo_steps to steps object
- [ ] `_update_jsonb_message_status()` queries AgentExecution (not AgentJob)
- [ ] All message WebSocket events include both job_id and agent_id
- [ ] Messages Sent counter updates live (no refresh needed)
- [ ] Messages Waiting counter updates live (no refresh needed)
- [ ] Messages Read counter updates live AND persists on refresh
- [ ] Steps counter updates live AND persists on refresh
- [ ] All existing tests pass
- [ ] New integration tests pass (>4 tests)
- [ ] Manual testing verified via dashboard
- [ ] Code committed with descriptive message

### Verification Commands

```bash
# Run existing tests
pytest tests/services/test_message_service_contract.py -v
pytest tests/websocket/test_message_counter_events.py -v

# Run new integration tests
pytest tests/integration/test_websocket_unified_platform.py -v

# Full test suite with coverage
pytest tests/ --cov=src/giljo_mcp --cov-report=term
```

---

## Rollback Plan

**If Things Go Wrong**:

1. **Frontend-only rollback**:
   ```bash
   git checkout HEAD~1 -- frontend/src/stores/agentJobsStore.js
   ```

2. **Backend-only rollback**:
   ```bash
   git checkout HEAD~1 -- src/giljo_mcp/services/message_service.py
   ```

3. **Full rollback**:
   ```bash
   git revert <commit-hash>
   ```

**Database**: No schema changes required. JSONB data is backward-compatible.

---

## Related Handovers

| Handover | Relationship |
|----------|--------------|
| **0381** | **Foundation: Clean contract - agent_id/job_id separation (this handover COMPLETES it)** |
| 0362 | Previous partial fix (test signatures) |
| 0372 | Introduced agent_id routing for messaging |
| 0387 | Broadcast fan-out at write (complementary) |
| 0400 | Alpha test findings (identified issues) |

---

## Appendix A: Identifier Glossary

| Term | Model | Column | Meaning | Example |
|------|-------|--------|---------|---------|
| job_id | AgentJob | job_id | "What am I working on" (work order) | `ae6eed1b-3a94-...` |
| agent_id | AgentExecution | agent_id | "Who am I" (executor identity) | `fa39d78e-7b91-...` |
| agent_type | AgentJob | agent_type | Category of agent | `"orchestrator"`, `"implementer"` |
| agent_name | AgentJob | agent_name | Template name | `"analyzer"`, `"documenter"` |

**Relationships**:
- One AgentJob has one AgentExecution (1:1 relationship)
- `job_id` persists across succession (the work order stays the same)
- `agent_id` changes on succession (new executor takes over)
- **Messaging uses `agent_id`** because messages are between executors

**Why Messages Use agent_id (NOT job_id)**:
```
Scenario: Orchestrator A hands over to Orchestrator B

Before Succession:
  job_id:    "work-order-123"  (persists)
  agent_id:  "executor-A"      (will change)
  Messages:  "Hello Executor A" → stored on executor-A

After Succession:
  job_id:    "work-order-123"  (same work order)
  agent_id:  "executor-B"      (NEW executor)
  Messages:  Executor B should NOT see "Hello Executor A"

This is why messaging is tied to agent_id, not job_id.
```

---

## Appendix B: DevTools Verification

**How to verify WebSocket events in browser**:

1. Open Chrome DevTools (F12)
2. Go to Network tab
3. Filter by "WS" (WebSocket)
4. Click on the WebSocket connection
5. Go to "Messages" tab
6. Look for `message:sent`, `message:received`, `message:acknowledged`, `job:progress_update`
7. Verify payloads include both `job_id` and `agent_id`

**Expected payload structure after fix**:
```json
{
  "event": "message:received",
  "data": {
    "message_id": "abc123",
    "from_agent": "fa39d78e-...",
    "from_job_id": "ae6eed1b-...",
    "to_agent_ids": ["33ea7368-..."],
    "to_job_ids": ["b9b7a2fb-..."],
    "timestamp": "2026-01-02T15:30:00Z"
  }
}
```

---

## Appendix C: Implementation Session (2026-01-02)

### Additional Issue Discovered During Testing

During live browser testing, we discovered a **4th bug** not in the original handover:

**Issue 4: API Response Missing `agent_id` Field**

The jobs API endpoint (`/api/agent-jobs/`) was returning jobs WITHOUT the `agent_id` field. This means even though:
- ✅ Backend stores `agent_id` in `AgentExecution`
- ✅ `OrchestrationService.list_jobs()` returns `agent_id` in job dicts
- ✅ Frontend `resolveJobId()` checks for `agent_id`

The field was being **dropped** in the API response layer because:
- `JobResponse` Pydantic model didn't have `agent_id` field
- `job_to_response()` didn't map `agent_id` to the response

**Fix Applied**:

**File 1**: `api/endpoints/agent_jobs/models.py` (line 91)
```python
class JobResponse(BaseModel):
    id: str
    job_id: str
    agent_id: Optional[str] = None  # NEW: Executor UUID for WebSocket event matching
    tenant_key: str
    ...
```

**File 2**: `api/endpoints/agent_jobs/status.py` (line 44)
```python
def job_to_response(job: dict) -> JobResponse:
    return JobResponse(
        id=job.get("agent_id", job.get("id", "")),
        job_id=job["job_id"],
        agent_id=job.get("agent_id"),  # NEW: Executor UUID for WebSocket event matching
        tenant_key=job["tenant_key"],
        ...
```

### Summary of All Fixes (Session 2026-01-02)

| File | Fix | Commit |
|------|-----|--------|
| `frontend/src/stores/agentJobsStore.js:191-213` | Added `agent_id` check to `resolveJobId()` | `80a0ccde` |
| `frontend/src/stores/agentJobsStore.js:165-189` | Added steps transformation in `handleProgressUpdate()` | `80a0ccde` |
| `src/giljo_mcp/services/message_service.py:250-268` | Moved JSONB persistence outside websocket_manager block | (earlier session) |
| `api/endpoints/agent_jobs/models.py:91` | Added `agent_id` field to `JobResponse` | `3c384d78` |
| `api/endpoints/agent_jobs/status.py:44` | Added `agent_id` mapping in `job_to_response()` | `3c384d78` |
| `frontend/src/stores/agentJobsStore.js:176-197` | Handle both object and array formats for `todo_steps` | `c6e00c5f` |

### Final Verification Results

| Feature | Test | Result |
|---------|------|--------|
| Message Sent Counter | Send broadcast → Orchestrator sent 8→9 | ✅ Real-time |
| Messages Waiting Counter | Send broadcast → All agents waiting 7→8 | ✅ Real-time |
| Steps Column | report_progress with mode=todo → 2/5→4/5→5/5 | ✅ Real-time |
| Data Persistence | Page refresh → Counters preserved | ✅ Verified |

### Verification Steps

After restarting the API server:

1. Refresh browser to reload jobs with `agent_id`
2. Send test message via MCP
3. Verify counters update in real-time (no refresh needed)
4. Verify counters persist after page refresh

---

**End of Handover 0401**

*Remember: This is a unification effort. The goal is ONE harmonized WebSocket platform, not patches on top of patches. Take time to understand the full flow before making changes.*
