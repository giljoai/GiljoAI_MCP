# Handover 0406: Reactive Feedback for TodoWrite Compliance

**Date:** 2026-01-03
**From Agent:** Opus 4.5 Research Session
**To Agent:** Next Implementation Agent
**Priority:** Medium
**Estimated Complexity:** 2-3 hours
**Status:** Ready for Implementation

---

## Task Summary

Implement reactive feedback system to correct agents who forget `todo_items` in `report_progress()` calls. Uses two-channel approach: immediate response warnings + queued messages. Architecture-compliant (no push - server only responds to requests).

---

## Context and Background

### Problem Statement
Alpha test revealed analyzer agent called `report_progress()` without `todo_items` array, causing dashboard Steps column to show "--". Handover 0405 added prompt enforcement, but agents may still forget mid-mission.

### Architecture Constraint
**CRITICAL**: MCP Server is PASSIVE (see `handovers/Reference_docs/Workflow PPT to JPG/` slides):
- Agents PULL via HTTP - no push channel exists
- Server cannot "wake up" agents or push reminders
- All feedback must occur via HTTP request/response cycle

### Solution Approach
Two-channel feedback within architecture constraints:
1. **Response Warning**: Return `warnings[]` in `report_progress()` response - agent sees IMMEDIATELY
2. **Message Queue**: Store corrective message in DB - agent sees on next `receive_messages()` call

---

## Technical Details

### Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/services/orchestration_service.py` | Add warnings to `report_progress()` response |
| `src/giljo_mcp/services/orchestration_service.py` | Queue corrective message when `todo_items` missing |
| `src/giljo_mcp/services/orchestration_service.py` | Queue protocol reminder in `acknowledge_job()` |

### Key Code Section: report_progress()

**Location:** `orchestration_service.py` lines 1063-1243

**Current return** (around line 1240):
```python
return {"status": "success", "message": "Progress reported successfully"}
```

**New return with warnings:**
```python
# Check for missing todo_items
warnings = []
todo_items = progress.get("todo_items")
if not isinstance(todo_items, list) or len(todo_items) == 0:
    warnings.append(
        "WARNING: todo_items missing! Dashboard Steps shows '--'. "
        "Include todo_items=[{content, status}] in every report_progress() call."
    )
    # Also queue corrective message for next receive_messages()
    await self._queue_corrective_message(execution.agent_id, job.project_id, tenant_key)

return {
    "status": "success",
    "message": "Progress reported successfully",
    "warnings": warnings,  # Agent sees immediately
}
```

### New Helper Method

```python
async def _queue_corrective_message(
    self, agent_id: str, project_id: str, tenant_key: str
) -> None:
    """Queue corrective message for agent who forgot todo_items."""
    try:
        from src.giljo_mcp.services.message_service import MessageService
        message_service = MessageService(self._db_manager)
        await message_service.send_message(
            to_agents=[agent_id],
            content="CORRECTIVE: Include todo_items in report_progress(). Dashboard cannot update without it.",
            project_id=project_id,
            message_type="system",
            priority="high",
            from_agent="system",
            tenant_key=tenant_key,
        )
    except Exception as e:
        self._logger.warning(f"Failed to queue corrective message: {e}")
```

### acknowledge_job() Enhancement

**Location:** Find `acknowledge_job()` method in `orchestration_service.py`

After setting job status to active, queue initial reminder:
```python
# Queue protocol reminder after status update
await self._queue_protocol_reminder(execution.agent_id, job.project_id, tenant_key)
```

**New helper:**
```python
async def _queue_protocol_reminder(
    self, agent_id: str, project_id: str, tenant_key: str
) -> None:
    """Queue initial protocol reminder when job acknowledged."""
    try:
        from src.giljo_mcp.services.message_service import MessageService
        message_service = MessageService(self._db_manager)
        await message_service.send_message(
            to_agents=[agent_id],
            content="""PROTOCOL REMINDER:
1. Create TodoWrite task list BEFORE implementation
2. Include todo_items=[] in EVERY report_progress() call
3. Dashboard shows "--" without todo_items = TEST FAILURE""",
            project_id=project_id,
            message_type="system",
            priority="high",
            from_agent="system",
            tenant_key=tenant_key,
        )
    except Exception as e:
        self._logger.warning(f"Failed to queue protocol reminder: {e}")
```

---

## Implementation Plan

### Phase 1: Add Response Warnings (30 min)
1. Locate `report_progress()` return statement (~line 1240)
2. Add `warnings` array check before return
3. Return `warnings` in response dict
4. Test: Call `report_progress()` without `todo_items`, verify warning in response

### Phase 2: Queue Corrective Message (30 min)
1. Add `_queue_corrective_message()` helper method
2. Call from `report_progress()` when `todo_items` missing
3. Test: Call `report_progress()` without `todo_items`, verify message queued
4. Test: Call `receive_messages()`, verify corrective message received

### Phase 3: Acknowledge Job Reminder (30 min)
1. Locate `acknowledge_job()` method
2. Add `_queue_protocol_reminder()` helper method
3. Call after status update to "active"
4. Test: Acknowledge job, call `receive_messages()`, verify reminder received

### Phase 4: Integration Testing (1 hour)
1. Full flow: Spawn agent -> acknowledge -> report without todo_items -> verify both warnings
2. Verify message counters update correctly (related to 0405)
3. Verify no duplicate messages on repeated forgetful calls

---

## Testing Requirements

### Unit Tests
```python
# tests/services/test_orchestration_service.py

async def test_report_progress_warns_on_missing_todo_items():
    """report_progress() returns warning when todo_items missing."""
    result = await service.report_progress(
        job_id="test-job",
        progress={"percent": 50, "message": "Half done"},  # No todo_items!
        tenant_key="test-tenant"
    )
    assert result["status"] == "success"
    assert len(result["warnings"]) == 1
    assert "todo_items missing" in result["warnings"][0]

async def test_report_progress_no_warning_with_todo_items():
    """report_progress() has no warning when todo_items present."""
    result = await service.report_progress(
        job_id="test-job",
        progress={
            "mode": "todo",
            "todo_items": [{"content": "Task 1", "status": "completed"}]
        },
        tenant_key="test-tenant"
    )
    assert result["status"] == "success"
    assert result.get("warnings", []) == []

async def test_acknowledge_job_queues_reminder():
    """acknowledge_job() queues protocol reminder message."""
    # Acknowledge job
    await service.acknowledge_job(job_id="test-job", agent_id="test-agent", tenant_key="test-tenant")
    # Check message was queued
    messages = await message_service.receive_messages(agent_id="test-agent", tenant_key="test-tenant")
    assert any("PROTOCOL REMINDER" in m["content"] for m in messages)
```

### Manual Testing
1. Start backend, open dashboard
2. Spawn test agent via MCP
3. Call `acknowledge_job()` - verify message queued
4. Call `report_progress()` without `todo_items` - check response for `warnings`
5. Call `receive_messages()` - verify corrective message received

---

## Success Criteria

- [ ] `report_progress()` returns `warnings` array when `todo_items` missing
- [ ] Corrective message queued when `todo_items` missing
- [ ] Protocol reminder queued when job acknowledged
- [ ] No warnings when `todo_items` properly included
- [ ] All existing tests still pass
- [ ] Message counters update correctly (no regression from 0405)

---

## Dependencies

- **0405 Complete**: Message counter fallback (already committed)
- **0402 Complete**: Agent TODO Items table (storage mechanism)
- **MessageService**: Must support `send_message()` with `from_agent="system"`

---

## Rollback Plan

If issues arise:
1. Revert `orchestration_service.py` changes
2. Warnings are additive - removing them won't break existing functionality
3. Queued messages can be ignored by agents (non-breaking)

---

## Related Resources

- **Plan file**: `C:\Users\giljo\.claude\plans\vast-hopping-brooks.md` (Phase 4 section)
- **Session memory**: `session_0406_reactive_feedback_research.md` (Serena memory)
- **Architecture slides**: `handovers/Reference_docs/Workflow PPT to JPG/Slide2-4.JPG`
- **0405 handover**: `handovers/0405_message_counter_fallback_todowrite_enforcement.md`

---

## Agent Flow Diagram

```
Agent calls acknowledge_job()
  <- Server queues "PROTOCOL REMINDER" message
  <- Response: {"status": "success"}

Agent calls receive_messages() (Phase 1 Step 3 of protocol)
  <- Gets: "PROTOCOL REMINDER: Create TodoWrite..."

Agent calls report_progress() WITHOUT todo_items
  <- IMMEDIATE Response: {"status": "success", "warnings": ["todo_items missing..."]}
  <- Server queues "CORRECTIVE" message

Agent calls receive_messages() later
  <- Gets: "CORRECTIVE: Include todo_items..."
  <- Agent corrects behavior on next report_progress()
```

---

**Recommended Agent:** `tdd-implementor` (straightforward service enhancement with clear test requirements)
