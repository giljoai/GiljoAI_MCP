# Handover 0407: Message Acknowledged Counter Fix

**Date:** 2026-01-03
**From Agent:** Opus 4.5 Implementation Session
**Priority:** High
**Status:** Complete

---

## Problem Statement

During alpha testing, the analyzer agent called `receive_messages()` twice, but the dashboard showed:
- Messages Waiting: 1 (not decrementing)
- Messages Read: 0 (not incrementing)

Backend logs confirmed the `message:acknowledged` WebSocket event was broadcast, but frontend logs showed NO `handleMessageAcknowledged` calls.

---

## Root Cause Analysis

Two issues were identified:

### Issue 1: Job ID Resolution Failure

The `handleMessageAcknowledged` function tried to resolve the job using:
```javascript
const recipientId = resolveJobId(payload?.agent_id || payload?.job_id)
```

But the backend sends `agent_id` (executor UUID like `ddc75c89-f908-4a6c-bf3d-5771c10c0d15`) which may not be directly mapped in the frontend store. The `resolveJobId` function would return `null`, causing silent early exit.

### Issue 2: Missing Fallback (Handover 0405 Incomplete)

Even if job resolution succeeded, the function had this pattern:
```javascript
if (acknowledgedNow === 0) return  // Early exit with no fallback!
```

This means if messages weren't tracked locally (page wasn't open when `message:received` was sent), counters wouldn't update.

---

## Fix Applied

### 1. Multiple Job ID Resolution Strategies

Now tries three resolution paths:
```javascript
const recipientId = resolveJobId(payload?.agent_id)
  || resolveJobId(payload?.job_id)
  || resolveJobId(payload?.from_job_id)
```

### 2. Fallback Counter Update (Handover 0405)

Added fallback when messages aren't in local array:
```javascript
if (acknowledgedNow === 0 && messageIds.length > 0) {
  // Fallback: Use message count from payload
  const nextJob = normalizeJob({
    ...previous,
    messages_waiting_count: Math.max(0, (previous.messages_waiting_count || 0) - messageIds.length),
    messages_read_count: (previous.messages_read_count || 0) + messageIds.length,
  })
  jobsById.value = createNextMapWith(jobsById.value, recipientId, nextJob)
  return
}
```

### 3. Debug Logging

Added `console.debug` statements to track:
- WebSocket router receiving `message:acknowledged` events
- Job ID resolution attempts and failures
- Fallback counter updates being applied

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/src/stores/agentJobsStore.js` | Fixed `handleMessageAcknowledged` with multiple resolution + fallback |
| `frontend/src/stores/websocketEventRouter.js` | Added debug logging for `message:acknowledged` handler |

---

## Testing

To verify the fix:

1. Start backend and frontend in dev mode
2. Open browser console (F12) with "Verbose" logging enabled
3. Spawn an agent and send it a message
4. Have the agent call `receive_messages()` via MCP
5. Watch console for:
   - `[websocketEventRouter] message:acknowledged received` - Event arrived
   - `[agentJobsStore] handleMessageAcknowledged: Using fallback counter update` - Fallback applied
6. Verify dashboard shows:
   - Messages Waiting: 0 (decremented)
   - Messages Read: 1 (incremented)

---

## Related Handovers

- **0405**: Message Counter Fallback & TodoWrite Enforcement (partial - fallback was documented but not implemented)
- **0406**: Reactive Feedback for TodoWrite Compliance (ready for implementation)
- **0401**: Unified WebSocket Platform Refactor (event structure documentation)

---

## Notes

- Debug logging uses `console.debug` which only shows with "Verbose" console filter enabled
- The `from_job_id` resolution is a safety net for backward compatibility with older event formats
- If resolution still fails, debug logs will show available job IDs for diagnosis
