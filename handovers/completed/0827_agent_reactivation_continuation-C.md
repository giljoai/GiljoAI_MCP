# 0827 — Agent Reactivation & Continuation

**Edition Scope:** CE
**Priority:** High (post-0826)
**Status:** Complete
**Date:** 2026-03-19
**Origin:** Multi-terminal alpha trial (Codex + Gemini + Claude Code, 2026-03-19). User observed coordination gaps when completed agents receive follow-up messages from peers.

---

## Problem Statement

In multi-terminal mode, agents run in independent terminal sessions coordinated exclusively through the GiljoAI MCP server. When Agent A completes its work and another agent later sends it a message (e.g., "fix the missing subfolder"), there is no mechanism for Agent A to:

1. Signal to the dashboard that it needs attention (status stays green "Complete")
2. Resume work (no `complete → working` state transition exists)
3. Add new steps without destroying its completed TODO history
4. Know that `reactivate_job` exists (no protocol guidance in tool responses)

Additionally, messages between agents display raw UUIDs instead of display names.

**User experience today:** The user must notice the Messages Waiting badge increment, switch terminals, tell the agent to check messages, and the agent has no tooling or instructions to resume. The system works but the experience is rough.

**User experience after this handover:** Dashboard status flips to orange "Needs Input" automatically when a message arrives for a completed agent. User switches terminals, tells agent to read messages. The tool response includes reactivation guidance. Agent calls `reactivate_job`, appends new steps, resumes work. If the message is informational, agent calls `dismiss_reactivation` and returns to complete.

---

## Phases

This handover has four phases. Each is independently deployable. Order matters — Phase B depends on Phase A's WebSocket broadcast pattern, and Phase C depends on Phase B's `reactivate_job` tool.

| Phase | Title | Effort | Dependencies |
|-------|-------|--------|-------------|
| 0827a | Display Name in Messages | Small (1-2 hrs) | None |
| 0827b | Auto-Block on Post-Completion Message | Small (1-2 hrs) | None |
| 0827c | `reactivate_job` + `dismiss_reactivation` Tools | Medium (3-4 hrs) | 0827b |
| 0827d | TODO Append + Duration Accumulation | Medium (3-4 hrs) | 0827c |

---

## Phase 0827a: Display Name in Messages

### Problem

When agents call `receive_messages()`, the `from_agent` field contains a raw UUID:

```
"from agent 45514577-a579-4159-97a2-3eb5de08b06c"
```

Instead of:

```
"from Folder-Creator"
```

### Root Cause

**At send time** (`message_service.py` ~L249): `meta_data` is constructed with only `_from_agent`. The service resolves display names to UUIDs earlier (L197-220) but never saves the display name.

**At receive time** (`message_service.py` ~L1082-1095): reads `meta_data["_from_agent"]` verbatim with no reverse lookup.

### Implementation

**1. Enrich at send time** — In `send_message()`, after resolving sender identity, store the display name alongside the UUID:

```python
# After resolving sender_execution (existing code already does this)
sender_display = sender_execution.agent_display_name if sender_execution else from_agent
meta_data = {
    "_from_agent": from_agent or "orchestrator",
    "_from_display_name": sender_display,  # NEW
}
```

**2. Enrich at receive time (fallback)** — For messages created before this change, batch-resolve UUIDs on read:

```python
# Before the message formatting loop in receive_messages()
sender_ids = {msg.meta_data.get("_from_agent") for msg in pending_messages if msg.meta_data}
uuid_ids = [s for s in sender_ids if s and "-" in s and len(s) == 36]
sender_name_map = {}
if uuid_ids:
    result = await session.execute(
        select(AgentExecution.agent_id, AgentExecution.agent_display_name)
        .where(AgentExecution.agent_id.in_(uuid_ids))
        .where(AgentExecution.tenant_key == tenant_key)  # TENANT ISOLATION
    )
    sender_name_map = {row.agent_id: row.agent_display_name for row in result}
```

**3. Format the response** — Include both UUID and display name:

```python
from_agent_raw = msg.meta_data.get("_from_agent", "") if msg.meta_data else ""
from_display = (msg.meta_data.get("_from_display_name", "") if msg.meta_data else "") \
    or sender_name_map.get(from_agent_raw, from_agent_raw)

messages_list.append({
    "from_agent": from_display or from_agent_raw,  # Display name preferred
    "from_agent_id": from_agent_raw,                # UUID always available
    ...
})
```

### Name Resolution for Completed Agents

Currently `send_message(to_agents=["Folder-Creator"])` resolves display names by querying only active executions (`status IN ("waiting", "working", "blocked")`). A completed agent is invisible by name.

**Change:** Expand the name resolution query to include `"complete"` status unconditionally. This is safe because:
- The user is the scheduler in multi-terminal mode — they decide whether to act on messages
- Auto-blocking (Phase 0827b) provides the dashboard signal
- No sleep-wake automation exists to create ghost deliveries

**File:** `message_service.py` — the status filter in the name resolution query (~L201-202). Add `"complete"` to the allowed statuses list.

### Files Impacted

- `src/giljo_mcp/services/message_service.py` — send enrichment (~L249), receive enrichment (~L1082), name resolution filter (~L201)

### Tests

- Unit: `send_message` stores `_from_display_name` in metadata
- Unit: `receive_messages` returns display name for new messages (via metadata)
- Unit: `receive_messages` returns display name for old messages (via fallback lookup)
- Unit: `send_message(to_agents=["Agent-Name"])` resolves completed agents
- Integration: End-to-end message between two agents verifies display name round-trip

---

## Phase 0827b: Auto-Block on Post-Completion Message

### Problem

When a message arrives for a completed agent, the dashboard shows the Messages Waiting counter incrementing from 0 to 1 — but the Agent Status stays green "Complete." The user must notice the subtle counter change. There is no strong visual signal that the agent needs attention.

### Solution

When a direct message is delivered to an agent in `complete` status, the server automatically transitions the agent to `blocked` status. On the dashboard, this renders as orange **"Needs Input"** with an `mdi-account-question` icon — a strong, unmissable signal.

### Implementation

**In `message_service.py`, within `send_message()`**, after the message is created and committed, check the recipient's status:

```python
# After message creation, check if recipient is completed
if recipient_execution and recipient_execution.status == "complete":
    recipient_execution.status = "blocked"
    recipient_execution.block_reason = (
        f"Received message from {sender_display} while completed"
    )
    await session.flush()

    # Broadcast status change via WebSocket
    await self._broadcast_agent_status_change(
        recipient_execution, tenant_key
    )
```

**WebSocket broadcast** — Use the existing agent status broadcast pattern (check `WebSocketManager` for the event type used by the Jobs tab, likely `agent:status_changed` or similar). The frontend Pinia store should reactively update the Jobs tab row — verify the `allJobsTerminal` computed property in the closeout UI re-evaluates (it should, since `blocked` is not a terminal status).

**Edge case: broadcast messages** — Only trigger auto-block for `direct` message types, not broadcasts. A broadcast "Phase 2 complete" should not flip every completed agent to "Needs Input."

### Guard: Project Closeout State

If the project is already closed out (status `completed` or `terminated`), do NOT auto-block. The message is delivered (it may be informational), but the status stays `complete`. This prevents reactivation against closed projects.

### Files Impacted

- `src/giljo_mcp/services/message_service.py` — post-send status check in `send_message()`

### Tests

- Unit: Direct message to completed agent flips status to `blocked` with reason
- Unit: Direct message to `working` agent does NOT change status
- Unit: Broadcast message to completed agent does NOT change status
- Unit: Direct message to completed agent in a closed project does NOT change status
- Integration: WebSocket event fires on auto-block, frontend row updates

---

## Phase 0827c: `reactivate_job` and `dismiss_reactivation` Tools

### Problem

A completed agent that receives an actionable message has no tool to resume work. A completed agent that receives an informational message has no way to return to complete status.

### Solution: Two New MCP Tools

#### Tool 1: `reactivate_job`

Transitions a blocked (auto-blocked from complete) agent back to `working` status so it can resume.

**Service method** — `OrchestrationService.reactivate_job()`:

```python
async def reactivate_job(
    self, job_id: str, tenant_key: str, reason: str = ""
) -> ReactivationResponse:
    # 1. Find execution — must be in "blocked" status
    #    (agent was auto-blocked by 0827b when message arrived)
    execution = await self._find_execution(
        job_id, tenant_key, allowed_statuses=["blocked"]
    )
    if not execution:
        raise ResourceNotFoundError(
            "Job not found or not in blocked status. "
            "Only auto-blocked (post-completion) agents can reactivate."
        )

    # 2. Check project is not closed out
    project = await self._get_project_for_job(job_id, tenant_key)
    if project.status in ("completed", "terminated"):
        raise ProjectStateError(
            "Cannot reactivate — project is already closed out."
        )

    # 3. Calculate and store accumulated working duration
    if execution.completed_at and execution.started_at:
        elapsed = (execution.completed_at - execution.started_at).total_seconds()
        current_accumulated = execution.accumulated_duration_seconds or 0.0
        execution.accumulated_duration_seconds = current_accumulated + elapsed

    # 4. Transition execution: blocked -> working
    execution.status = "working"
    execution.completed_at = None  # Clear for new duration segment
    execution.started_at = datetime.now(UTC)  # New segment start
    execution.block_reason = None

    # 5. Transition job: completed -> active
    job = await self._find_job(job_id, tenant_key)
    if job.status == "completed":
        job.status = "active"
        job.completed_at = None

    # 6. Increment reactivation counter
    reactivation_count = (execution.reactivation_count or 0) + 1
    execution.reactivation_count = reactivation_count

    # 7. Log and broadcast
    logger.info(f"Job {job_id} reactivated (#{reactivation_count}): {reason}")
    await self._broadcast("agent:status_changed", {...})

    # 8. Return with guidance
    return ReactivationResponse(
        status="reactivated",
        job_id=job_id,
        reactivation_count=reactivation_count,
        instruction=(
            "You have been reactivated. Follow these steps:\n"
            "1. Review the message(s) that triggered reactivation.\n"
            "2. Call report_progress with todo_append to ADD new steps "
            "(do NOT replace your existing completed steps).\n"
            "3. Do the work, reporting progress as normal.\n"
            "4. Call complete_job() when finished."
        )
    )
```

**Note on `started_at` reset:** We clear `completed_at` and set a new `started_at` for the new working segment. The previous working time is preserved in `accumulated_duration_seconds`. The frontend duration calculation becomes: `accumulated_duration_seconds + (now - started_at)` for in-progress agents, or `accumulated_duration_seconds + (completed_at - started_at)` for completed agents. See Phase 0827d for frontend changes.

#### Tool 2: `dismiss_reactivation`

For informational messages that don't require action. Returns the agent to `complete` status.

**Service method** — `OrchestrationService.dismiss_reactivation()`:

```python
async def dismiss_reactivation(
    self, job_id: str, tenant_key: str, reason: str = ""
) -> DismissResponse:
    # 1. Find execution — must be in "blocked" status
    execution = await self._find_execution(
        job_id, tenant_key, allowed_statuses=["blocked"]
    )
    if not execution:
        raise ResourceNotFoundError(
            "Job not found or not in blocked status."
        )

    # 2. Return to complete (restore previous state)
    execution.status = "complete"
    execution.block_reason = None
    # Do NOT touch completed_at, started_at, or progress — 
    # agent was never actually reactivated

    # 3. Restore job status if it was completed
    job = await self._find_job(job_id, tenant_key)
    if job.status == "active":
        # Only restore if no OTHER executions are still active
        other_active = await self._has_active_executions(job_id, tenant_key, exclude=execution.id)
        if not other_active:
            job.status = "completed"

    # 4. Broadcast
    await self._broadcast("agent:status_changed", {...})

    return DismissResponse(
        status="dismissed",
        job_id=job_id,
        instruction="Message acknowledged. No action needed. You remain in complete status."
    )
```

#### Protocol Guidance via `receive_messages` Response

When a `blocked` agent (one that was auto-blocked from complete) calls `receive_messages`, append reactivation guidance to the response payload:

```python
# In receive_messages(), after building the messages list
if caller_execution and caller_execution.status == "blocked":
    response["_reactivation_guidance"] = {
        "your_status": "blocked",
        "your_job_id": caller_execution.job_id,
        "instruction": (
            "You were in COMPLETE status and received a message. "
            "Review the message(s) above, then choose ONE action:\n"
            "- If action is needed: call reactivate_job("
            f"job_id=\"{caller_execution.job_id}\", "
            "reason=\"brief reason\")\n"
            "- If no action needed: call dismiss_reactivation("
            f"job_id=\"{caller_execution.job_id}\", "
            "reason=\"informational only\")"
        )
    }
```

This is the passive orchestrator pattern — the server enriches the response with the right context at the right time. No new protocol chapter. No settings. The guidance appears only when the situation calls for it.

#### MCP Tool Definitions

Add to `_build_agent_coordination_tools()`:

```python
{
    "name": "reactivate_job",
    "description": (
        "Resume work on a completed job after receiving a follow-up message. "
        "Only works when status is 'blocked' (auto-set when a message arrives "
        "for a completed agent). After reactivating, use report_progress with "
        "todo_append to add new steps — do not overwrite completed steps."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job ID to reactivate"},
            "reason": {"type": "string", "description": "Why reactivating (e.g., 'fix request from Orchestrator')"}
        },
        "required": ["job_id"]
    }
}
```

```python
{
    "name": "dismiss_reactivation",
    "description": (
        "Acknowledge a post-completion message without resuming work. "
        "Returns you to complete status. Use when the message is informational "
        "and no action is required."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job ID to dismiss"},
            "reason": {"type": "string", "description": "Why no action needed (e.g., 'FYI message only')"}
        },
        "required": ["job_id"]
    }
}
```

### Database Migration (Alembic)

**New columns on `AgentExecution`:**

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `accumulated_duration_seconds` | `Float` | `0.0` | Stores total working time across reactivation cycles |
| `reactivation_count` | `Integer` | `0` | Tracks how many times the agent has been reactivated |

These are nullable with defaults so the migration is additive and non-breaking for existing data.

### Files Impacted

- `src/giljo_mcp/services/orchestration_service.py` — new `reactivate_job()` and `dismiss_reactivation()` methods
- `src/giljo_mcp/services/message_service.py` — `_reactivation_guidance` in `receive_messages()` response
- `src/giljo_mcp/tools/tool_accessor.py` — delegation for both new tools
- `api/endpoints/mcp_http.py` — tool definitions, schema params, handler registration
- `src/giljo_mcp/models/agent_identity.py` — new columns on `AgentExecution`
- Alembic migration — `accumulated_duration_seconds`, `reactivation_count`

### Tests

- Unit: `reactivate_job` transitions `blocked → working`, sets `accumulated_duration_seconds`
- Unit: `reactivate_job` on non-blocked agent raises `ResourceNotFoundError`
- Unit: `reactivate_job` on closed project raises `ProjectStateError`
- Unit: `reactivate_job` increments `reactivation_count`
- Unit: `dismiss_reactivation` transitions `blocked → complete`
- Unit: `dismiss_reactivation` on non-blocked agent raises error
- Unit: `receive_messages` for blocked agent includes `_reactivation_guidance`
- Unit: `receive_messages` for working agent does NOT include guidance
- Integration: Full cycle — complete → auto-block → reactivate → work → complete

---

## Phase 0827d: TODO Append + Duration Display

### Problem 1: TODO Overwrite

Current `report_progress()` does DELETE-all then INSERT-all on `AgentTodoItem` rows. If a reactivated agent reports 2 new steps, its 5 previously completed steps are destroyed.

### Solution: `todo_append` Parameter

Add a `todo_append` parameter to `report_progress` that preserves existing rows and appends new ones.

**Implementation in `orchestration_service.py` `report_progress()` (~L1499-1525):**

```python
# NEW parameter
async def report_progress(
    self, job_id, progress=None, tenant_key=None,
    todo_items=None,
    todo_append: list[dict] | None = None,  # NEW
):
    ...
    if todo_append is not None:
        # DO NOT delete existing items
        # Find the current max sequence number
        max_seq_result = await session.execute(
            select(func.max(AgentTodoItem.sequence))
            .where(AgentTodoItem.job_id == job.id)
            .where(AgentTodoItem.tenant_key == tenant_key)
        )
        max_seq = max_seq_result.scalar() or -1

        # Insert only the new items
        for i, item in enumerate(todo_append):
            new_todo = AgentTodoItem(
                job_id=job.id,
                tenant_key=tenant_key,
                content=item["content"],
                status=item.get("status", "pending"),
                sequence=max_seq + 1 + i,
            )
            session.add(new_todo)

        # Update JSONB summary counts
        total_result = await session.execute(
            select(func.count(AgentTodoItem.id))
            .where(AgentTodoItem.job_id == job.id)
            .where(AgentTodoItem.tenant_key == tenant_key)
        )
        completed_result = await session.execute(
            select(func.count(AgentTodoItem.id))
            .where(AgentTodoItem.job_id == job.id)
            .where(AgentTodoItem.tenant_key == tenant_key)
            .where(AgentTodoItem.status == "completed")
        )

        job.job_metadata = {
            **(job.job_metadata or {}),
            "todo_steps": {
                "total_steps": total_result.scalar(),
                "completed_steps": completed_result.scalar(),
                "skipped_steps": 0,  # recalculate if needed
                "current_step": max_seq + 2,  # next pending
            }
        }

    elif todo_items is not None:
        # EXISTING behavior — full replace (unchanged)
        ...
```

**Tool schema update** — Add `todo_append` to the `report_progress` schema in `_build_agent_coordination_tools()`:

```python
"todo_append": {
    "type": "array",
    "description": "Steps to APPEND to existing TODO list. Use instead of todo_items when adding work to a reactivated job. Existing completed steps are preserved.",
    "items": {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Step description"},
            "status": {"type": "string", "enum": ["pending", "in_progress"], "default": "pending"}
        },
        "required": ["content"]
    }
}
```

**Schema params allowlist** — Add `"todo_append"` to `_TOOL_SCHEMA_PARAMS["report_progress"]`.

### Problem 2: Duration Display

Duration is computed on the frontend as `completed_at - started_at`. After reactivation, `started_at` resets but the previous working time is lost from the display.

### Solution: Accumulated Duration on Frontend

**Backend** — The `accumulated_duration_seconds` column (added in Phase 0827c migration) is populated by `reactivate_job()` and included in the `JobResponse` model.

**Add to `JobResponse`** (in `api/endpoints/agent_jobs/models.py`):

```python
accumulated_duration_seconds: float = 0.0
reactivation_count: int = 0
```

**Frontend** — Update `formatDuration()` logic in `JobsTab.vue` (~L544-574):

```javascript
// Current: completed_at - started_at
// New: accumulated + current segment
const accumulated = job.accumulated_duration_seconds || 0;

if (job.completed_at && job.started_at) {
    // Completed: accumulated + final segment
    const segment = (new Date(job.completed_at) - new Date(job.started_at)) / 1000;
    return formatDuration(accumulated + segment);
} else if (job.started_at) {
    // In progress: accumulated + live elapsed
    const segment = (now.value - new Date(job.started_at)) / 1000;
    return formatDuration(accumulated + segment);
} else {
    return formatDuration(accumulated);
}
```

**Optional: Reactivation badge** — If `reactivation_count > 0`, show a small badge or tooltip on the agent row indicating how many times it was reactivated. Not blocking — cosmetic enhancement.

### Files Impacted

- `src/giljo_mcp/services/orchestration_service.py` — `report_progress()` append logic
- `api/endpoints/mcp_http.py` — `todo_append` in schema params allowlist
- `src/giljo_mcp/tools/tool_accessor.py` — pass-through for `todo_append`
- `api/endpoints/agent_jobs/models.py` — `JobResponse` fields
- `frontend/src/components/JobsTab.vue` — duration calculation (~L544-574)

### Tests

- Unit: `report_progress(todo_append=[...])` preserves existing completed items
- Unit: `report_progress(todo_append=[...])` assigns correct sequence numbers
- Unit: `report_progress(todo_append=[...])` updates JSONB summary counts
- Unit: `report_progress(todo_items=[...])` still does full replace (no regression)
- Unit: `JobResponse` includes `accumulated_duration_seconds` and `reactivation_count`
- Frontend: Duration displays `accumulated + segment` correctly for reactivated agents

---

## Full Lifecycle Example

```
Timeline:
1. Folder-Creator starts working                    → Status: Working, Steps: 0/5
2. Folder-Creator completes steps, calls complete_job → Status: Complete, Steps: 5/5, Duration: 2m 55s
3. File-Creator sends "fix /alpha subfolder"         → Status: Needs Input, Steps: 5/5, Messages: 1
4. User switches terminal: "check your messages"
5. Agent calls receive_messages()                    → Response includes _reactivation_guidance
6. Agent reads message, decides action needed
7. Agent calls reactivate_job(reason="fix request")  → Status: Working, Duration: 2m 55s (accumulated)
8. Agent calls report_progress(todo_append=[...])    → Steps: 5/7
9. Agent does work, reports 6/7, 7/7                 → Duration: 2m 55s + live elapsed
10. Agent calls complete_job()                       → Status: Complete, Steps: 7/7, Duration: 4m 25s

Alternative at step 6:
6b. Agent reads message, decides it's FYI only
7b. Agent calls dismiss_reactivation(reason="info")  → Status: Complete, Steps: 5/5 (unchanged)
```

---

## Installation Flow Impact

**Alembic migration required.** Two new nullable columns on `AgentExecution`:
- `accumulated_duration_seconds FLOAT DEFAULT 0.0`
- `reactivation_count INTEGER DEFAULT 0`

Both are additive with defaults. No impact on `install.py` first-run flow. Existing data unaffected — agents that have never been reactivated will have `0.0` and `0` respectively.

---

## What This Handover Does NOT Include

- **Sleep-wake polling** — Covered by existing Agent Lab tip (paste-into-project-description pattern). Separate concern.
- **Settings UI for polling intervals** — Not needed since polling is prompt-based, not system-based.
- **State machine enforcement** — No formal transition validator added. The `reactivate_job` and `dismiss_reactivation` methods enforce their own preconditions (`allowed_statuses=["blocked"]`). A full state machine is deferred as scope creep.
- **Reactivation ceiling** — The `reactivation_count` is tracked and logged but not enforced. If needed, a guard can be added later (e.g., max 5 reactivations per job).

---

## Rollback Plan

Each phase is independently reversible:
- **0827a:** Remove `_from_display_name` from metadata construction and response formatting. Messages revert to UUID display.
- **0827b:** Remove the post-send status check. Messages still deliver; dashboard just won't auto-signal.
- **0827c:** Remove tools from MCP catalog. Remove service methods. Migration rollback: drop the two new columns.
- **0827d:** Remove `todo_append` parameter. Revert frontend duration calculation. `report_progress` reverts to full-replace behavior.

---

## Success Criteria

- [x] Messages display sender name, not UUID
- [x] Dashboard auto-transitions to "Needs Input" (orange) when a completed agent receives a direct message
- [x] Agent can call `reactivate_job` and resume work with appended steps
- [x] Agent can call `dismiss_reactivation` to return to complete for FYI messages
- [x] Duration accurately reflects cumulative working time, excluding idle gaps
- [x] Steps display shows appended count (e.g., 5/7 after adding 2 steps to 5/5)
- [x] Project closeout button disappears when an agent reactivates
- [x] Reactivation against a closed project returns a clear error
- [x] All existing tests still pass (no regression)

---

## Completion Summary

**Completed:** 2026-03-19
**All 4 phases implemented across 7 commits:**

| Phase | Commit | Description |
|-------|--------|-------------|
| 0827a | `75f619ec`, `bcd2eed6` | Display name resolution in messages (send enrichment + receive fallback + tests) |
| 0827b | `79671b36`, `f27a379f` | Auto-block completed agents on post-completion direct message + tests |
| 0827c | `167d46fe`, `9d730e62` | `reactivate_job` + `dismiss_reactivation` MCP tools + service methods + tests |
| 0827d | `cc404b08` | `todo_append` parameter + `accumulated_duration_seconds` + frontend duration display |

**Key changes:**
- `message_service.py`: `_from_display_name` enrichment at send time, batch UUID resolution at receive time, auto-block for completed recipients, `_reactivation_guidance` in receive response
- `orchestration_service.py`: `reactivate_job()` and `dismiss_reactivation()` service methods, `todo_append` in `report_progress()`
- `tools/tool_accessor.py`: Pass-throughs for both new tools + `todo_append`
- `api/endpoints/mcp_http.py`: Tool definitions, schema params, handlers
- `models/agent_identity.py`: `accumulated_duration_seconds` + `reactivation_count` columns
- `frontend/src/components/projects/JobsTab.vue`: Duration calculation with accumulated time
