# Handover 0405: Message Counter Fallback & TodoWrite Enforcement

## Status: COMPLETE

**Commit**: `2d62fe34`
**Date**: 2025-01-03

## Problem Statement

Alpha test revealed multiple issues with agent monitoring:
1. **Steps column shows "--"**: Agents not following TodoWrite protocol
2. **Messages Read = 0**: WebSocket acknowledgment events not updating UI counters
3. **Messages Waiting not decrementing**: Same root cause as #2

## Root Cause Analysis

### Issue 2 & 3: Message Counter Sync Gap

**Flow**:
```
Backend: receive_messages() → broadcast_message_acknowledged() ✓
WebSocket: message:acknowledged event emitted ✓
Frontend: handleMessageAcknowledged() → EARLY EXIT at acknowledgedNow === 0
```

The frontend's `handleMessageAcknowledged()` iterates over `previous.messages` looking for matching IDs. If messages aren't in the local array (never received `message:received` event because page wasn't open), `acknowledgedNow = 0` and counters don't update.

### Issue 1: TodoWrite Adherence

Agents have TodoWrite instructions in the full_protocol but sometimes skip them. The analyzer in alpha test didn't include `todo_items` in progress reports.

## Solution

### Phase 1: Frontend Fallback Counter (IMPLEMENTED)

**File**: `frontend/src/stores/agentJobsStore.js`

Added fallback logic when `acknowledgedNow === 0`:
- If payload has valid `message_ids`, update counters based on payload count
- Decrement `messages_waiting_count` by `messageIds.length`
- Increment `messages_read_count` by `messageIds.length`

```javascript
// Handover 0401b/0405: Fallback for sync gap
if (acknowledgedNow === 0) {
  if (messageIds.length > 0) {
    const nextJob = normalizeJob({
      ...previous,
      messages_waiting_count: Math.max(0, (previous.messages_waiting_count || 0) - messageIds.length),
      messages_read_count: (previous.messages_read_count || 0) + messageIds.length,
    })
    jobsById.value = createNextMapWith(jobsById.value, recipientId, nextJob)
  }
  return
}
```

### Phase 3: TodoWrite Enforcement (IMPLEMENTED)

**File**: `src/giljo_mcp/services/orchestration_service.py`

Added MANDATORY WARNING block at the top of `full_protocol` template:
```
## MANDATORY REQUIREMENTS (DO NOT SKIP) - Handover 0405

**FAILURE TO FOLLOW THESE = DASHBOARD SHOWS "--" = TEST FAILURE**

1. **CREATE TodoWrite task list in Phase 1** (BEFORE any implementation)
2. **SYNC every TodoWrite update with report_progress()** including todo_items array
3. **USE agent_id (UUID) for all messaging** - never use agent names
```

## Files Modified

| File | Change |
|------|--------|
| `frontend/src/stores/agentJobsStore.js` | Added fallback counter update in `handleMessageAcknowledged()` |
| `src/giljo_mcp/services/orchestration_service.py` | Added MANDATORY WARNING block to full_protocol template |

## Deferred Items

### Phase 2: UUID Normalization (NOT IMPLEMENTED)

The plan included renaming parameters and adding agent_name lookups:
- `to_agent` → `to_agent_id`
- Add `from_agent_id` as required parameter
- Batch agent_name lookup in message responses

These changes require more extensive refactoring and were deferred to a future handover.

### Test Fixes (DEFERRED)

`tests/test_message_flow.py` has pre-existing failures unrelated to this handover:
- Tests use outdated MessageService API signatures
- Tests don't inject `test_session` for transaction sharing
- Requires test infrastructure changes

## Testing

The committed changes fix the most critical issue (message counter not updating) and strengthen TodoWrite enforcement. Full UUID normalization can be done in a follow-up handover.

## Related Handovers

- **0401b**: Message acknowledgment debug session
- **0372**: Agent routing by agent_id (executor)
- **0387**: Broadcast fan-out implementation
