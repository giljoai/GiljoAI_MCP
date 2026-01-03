# Handover 0406: Reactive Feedback for TodoWrite Compliance

**Date:** 2026-01-03
**Status:** COMPLETE
**Commit:** `18433707`

---

## Summary

Implemented reactive feedback system to warn agents who forget `todo_items` in `report_progress()` calls. Simpler than originally planned - uses response warnings only (no message queue).

---

## Problem Statement

Alpha test revealed analyzer agent called `report_progress()` without `todo_items` array, causing dashboard Steps column to show "--". Handover 0405 added prompt enforcement, but agents may still forget mid-mission.

---

## Solution Implemented

### Original Plan vs Revised Implementation

| Original Plan | What We Implemented |
|---------------|---------------------|
| Response warnings + Message queue | **Response warnings only** (simpler) |
| No rate limiting | **Throttle: 1 warning per 5 min per job** |
| Protocol unchanged | **Protocol announces enforcement** |
| 3 touch points | **1 touch point + protocol** |

### Why Simpler is Better
- Message queue adds complexity without clear benefit
- Response warnings provide immediate feedback in same turn
- Rate limiting prevents spam without message tracking
- Protocol announcement sets expectations upfront

---

## Changes Made

### 1. Response Warnings (`orchestration_service.py` lines 1275-1291)

```python
# Handover 0406: Reactive warning for missing todo_items
warnings = []
todo_items = progress.get("todo_items")
if not isinstance(todo_items, list) or len(todo_items) == 0:
    # Check throttle - only warn once per 5 minutes per job
    if self._can_warn_missing_todos(job_id):
        warnings.append(
            "WARNING: todo_items missing! Dashboard Steps shows '--'. "
            "Include todo_items=[{content, status}] in every report_progress() call."
        )
        self._record_todo_warning(job_id)

return {
    "status": "success",
    "message": "Progress reported successfully",
    "warnings": warnings,
}
```

### 2. Rate Limiting Helpers (`orchestration_service.py` lines 369-392)

```python
# Class attribute
_todo_warning_timestamps: dict[str, datetime] = {}

def _can_warn_missing_todos(self, job_id: str, cooldown_minutes: int = 5) -> bool:
    """Check if we can send a todo_items warning (throttle: 1 per N minutes per job)."""
    last_warning = self._todo_warning_timestamps.get(job_id)
    if not last_warning:
        return True
    elapsed = (datetime.now(timezone.utc) - last_warning).total_seconds()
    return elapsed >= (cooldown_minutes * 60)

def _record_todo_warning(self, job_id: str) -> None:
    """Record that a todo_items warning was sent for this job."""
    self._todo_warning_timestamps[job_id] = datetime.now(timezone.utc)
```

### 3. Protocol Update (`_generate_agent_protocol()` lines 273-277)

```
### BACKEND MONITORING ACTIVE (Handover 0406)
The backend monitors report_progress() calls. If todo_items is missing:
- You will receive a WARNING in the response
- Warnings are throttled (1 per 5 minutes per job)
- Dashboard cannot display your progress without todo_items
```

### 4. Bug Fix (`tool_accessor.py` line 874)

```python
# Before (bug):
return await self._orchestration_service.report_progress(job_id=job_id, progress=progress)

# After (fixed):
return await self._orchestration_service.report_progress(job_id=job_id, progress=progress, tenant_key=tenant_key)
```

---

## Files Modified

| File | Lines Changed | Description |
|------|---------------|-------------|
| `src/giljo_mcp/services/orchestration_service.py` | +52 | Warnings, throttle helpers, protocol |
| `src/giljo_mcp/tools/tool_accessor.py` | +1 | Bug fix: tenant_key forwarding |
| `tests/unit/test_orchestration_service.py` | +218 | 4 new unit tests |

---

## Tests Added

```python
class TestOrchestrationServiceTodoWarnings:
    async def test_report_progress_warns_on_missing_todo_items()
    async def test_report_progress_no_warning_with_todo_items()
    async def test_report_progress_warning_throttled()
    async def test_report_progress_warning_empty_todo_items()
```

All tests passing.

---

## How It Works

```
Agent calls report_progress() without todo_items
    |
    v
Backend detects missing todo_items
    |
    v
Checks throttle (was warning sent < 5 min ago?)
    |
    +-- YES --> No warning (throttled)
    |
    +-- NO --> Returns: {"status": "success", "warnings": ["WARNING: todo_items missing..."]}
                Records timestamp for throttle
    |
    v
Agent sees warning in MCP tool response
    |
    v
Agent self-corrects on next report_progress()
```

---

## Architecture Compliance

This implementation respects the PASSIVE server architecture:
- No push channel needed
- Warning delivered via HTTP response
- Agent sees feedback immediately in same turn
- No message queue complexity

---

## Success Criteria - All Met

- [x] `report_progress()` returns `warnings[]` when `todo_items` missing
- [x] Warnings throttled to 1 per 5 minutes per job
- [x] Protocol announces backend monitoring
- [x] `tenant_key` forwarded correctly in ToolAccessor
- [x] All existing tests pass
- [x] New unit tests for warning behavior

---

## Related Handovers

- **0405**: Message counter fallback (prerequisite)
- **0402**: Agent TODO Items table (storage mechanism)
- **0407**: Message acknowledged counter fix (parallel work, no conflict)

---

## Rollback Plan

If issues arise:
1. Revert commit `18433707`
2. Warnings are additive - removing them won't break existing functionality
3. No database changes to rollback
