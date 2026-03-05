# Diagnostic: WebSocket Staging Updates Arrive as Burst Instead of Incremental

**Type**: Investigation / Bug Report
**Priority**: MEDIUM
**Context**: Discovered during 0700 series regression testing
**Affects**: Staging workflow UI experience

---

## Problem Description

During the staging workflow, the UI shows all updates at once (burst) instead of incrementally as each step completes:

**Expected behavior:**
1. Orchestrator reads context → mission text appears in UI
2. Orchestrator discovers agents → agent list appears
3. Orchestrator creates job 1 → first agent card appears in JobsTab
4. Orchestrator creates job 2 → second agent card appears
5. Each step is visible to the user as it happens

**Actual behavior:**
1. User sees nothing for a period
2. Then ALL content appears simultaneously — mission, agent cards, everything at once
3. It appears as if the orchestrator did nothing, then everything materialized

This suggests the WebSocket events are either batched, debounced, or only fired after a transaction boundary rather than after each individual operation.

---

## Investigation Areas

### Area 1: Backend — When are WebSocket events emitted?

Check the orchestration service and staging workflow for broadcast timing:

**Files to examine:**
- `src/giljo_mcp/services/orchestration_service.py` — Look for `broadcast_to_tenant()` or `websocket_manager.broadcast` calls. Are they inside a single `async with session` block that only commits at the end?
- `api/websocket.py` — WebSocket manager implementation. Is there any batching/debouncing logic?
- `src/giljo_mcp/services/agent_job_manager.py` — When jobs are created, are WebSocket events emitted per-job or after all jobs are created?
- `src/giljo_mcp/tools/agent_job_status.py` — MCP tool that orchestrators call to create/update jobs. Does it emit events?

**Key questions:**
- Is there a single DB transaction wrapping all staging operations, with WebSocket events only firing after `commit()`?
- Are events emitted inside the transaction (before commit) or after?
- Is `broadcast_to_tenant()` called after each job creation, or only once at the end?

### Area 2: Frontend — How does the UI react to WebSocket events?

**Files to examine:**
- `frontend/src/composables/useWebSocket.js` or similar — WebSocket connection handler
- `frontend/src/components/projects/JobsTab.vue` — How does it receive and render job updates?
- `frontend/src/components/projects/ProjectTabs.vue` — Parent component, may control refresh logic
- `frontend/src/stores/` — Any Pinia stores that buffer WebSocket events?

**Key questions:**
- Does the frontend debounce incoming WebSocket messages?
- Is there a `setTimeout` or `requestAnimationFrame` batching incoming updates?
- Does the frontend re-fetch the full job list on any WebSocket event (poll-on-push pattern) vs applying the delta directly?
- If it re-fetches, is the fetch debounced?

### Area 3: The Staging Orchestrator Flow

**Files to examine:**
- `src/giljo_mcp/thin_prompt_generator.py` — `_build_staging_prompt()` — What tasks does the staging prompt tell the orchestrator to do?
- `src/giljo_mcp/tools/tool_accessor.py` — `acknowledge_job()`, `create_agent_job()` or similar MCP tools the orchestrator calls during staging

**Key question:**
- Does the orchestrator call one MCP tool per agent (which would trigger one event per agent), or does it batch-create all jobs in a single MCP call?

### Area 4: Transaction Boundaries

The most likely root cause. Check if:
```python
# PROBLEMATIC: Single transaction, events fire after commit
async with session.begin():
    create_job_1()  # No event yet
    create_job_2()  # No event yet
    create_job_3()  # No event yet
# All events fire here after commit → BURST

# BETTER: Event per operation
create_job_1()
await session.commit()  # Event fires → card appears
create_job_2()
await session.commit()  # Event fires → card appears
```

---

## Diagnostic Steps

1. **Add console.log to frontend WebSocket handler** — Log timestamp + event type for every incoming message. This tells us if the backend is sending events incrementally or in a burst.

2. **Add logging to backend broadcast** — In `websocket_manager.broadcast_to_tenant()`, log timestamp + event_type + data summary. This tells us if the backend is emitting events as they happen.

3. **Compare timestamps** — If backend logs show events spread over 5-10 seconds but frontend shows them all arriving within 100ms, the issue is transport buffering. If backend logs also show all events within 100ms, the issue is transaction batching.

4. **Check the MCP tool call pattern** — During staging, does the orchestrator make multiple sequential MCP calls (one per job), or a single call that creates all jobs? Check the MCP request logs.

---

## Expected Findings

Most likely cause (ranked by probability):
1. **Transaction batching** — All jobs created in one DB transaction, WebSocket events only fire after commit
2. **Frontend debounce** — WebSocket handler debounces updates to avoid flicker, but debounce window is too large
3. **Poll-on-push with debounce** — Frontend receives WS event, triggers API fetch, fetch is debounced
4. **MCP batch call** — Orchestrator creates all jobs in one MCP tool call

---

## Deliverables

1. Root cause identification (which area is responsible)
2. Recommended fix approach
3. If the fix is simple (< 20 lines), implement it
4. If complex, write a handover spec

---

## Rules
- This is INVESTIGATION first, fix second
- Do NOT refactor WebSocket infrastructure — just find the timing issue
- Add diagnostic logging, test, then remove it
- If you find the root cause, propose the minimal fix
