# Handover 0297a: Real-time Message Counter WebSocket Fix (SESSION COMPLETE)

## Status: COMPLETE
## Priority: HIGH
## Type: Frontend + Backend Integration
## Parent: 0297 (UI Message Status & Job Signaling)
## Commit: bef0f509

---

## 1. Problem Solved

**Issue:** "Messages Waiting" counter did not update via WebSocket when orchestrator sent broadcast message during staging. User had to refresh page to see updated counters.

**Symptom:** User stages project, orchestrator sends `STAGING_COMPLETE` broadcast, but the message counters on agent cards don't update until page refresh.

---

## 2. Root Cause

The `message:sent` and `message:received` WebSocket events were only handled in `JobsTab.vue`. When user was on `LaunchTab` during staging, **no listener was active** to update counters.

The backend was correctly emitting events - the frontend just wasn't listening globally.

---

## 3. Solution Implemented

**Pattern:** Global WebSocket handlers in `websocketIntegrations.js` that update `projectTabsStore` regardless of which tab is active.

### Files Modified

| File | Changes |
|------|---------|
| `frontend/src/stores/projectTabs.js` | Added `handleMessageSent()` and `handleMessageReceived()` methods |
| `frontend/src/stores/websocketIntegrations.js` | Added import for `useProjectTabsStore`, updated `message:sent` handler, added `message:received` handler |
| `src/giljo_mcp/services/orchestration_service.py` | Added `message_service` parameter for WebSocket-enabled messaging |
| `src/giljo_mcp/tools/tool_accessor.py` | Pass `MessageService` to `OrchestrationService` |
| `api/websocket.py` | Minor cleanup (removed debug logging) |

### Code Changes Summary

**projectTabs.js - New handlers:**
```javascript
handleMessageSent(data) {
  // Verify project match
  // Find sender agent, add outbound message record
  // Mark stagingComplete on first broadcast
}

handleMessageReceived(data) {
  // Verify project match
  // For each recipient, add inbound message record with status: 'waiting'
  // Mark stagingComplete on first message
}
```

**websocketIntegrations.js - Global listeners:**
```javascript
wsStore.on('message:sent', (data) => {
  const projectTabsStore = useProjectTabsStore()
  projectTabsStore.handleMessageSent(payload)
})

wsStore.on('message:received', (data) => {
  const projectTabsStore = useProjectTabsStore()
  projectTabsStore.handleMessageReceived(payload)
})
```

---

## 4. What This Completes from 0297

| 0297 Section | Status |
|--------------|--------|
| 3.1 Message Counters (Per Agent Card) | COMPLETE - Real-time updates work |
| 4.2 Backend: WebSocket Events | COMPLETE - Events emit correctly |
| 4.3 Frontend: Stores & Components | COMPLETE - Global handlers added |
| Acceptance Criteria #2 (WebSocket sync without refresh) | COMPLETE |

---

## 5. What Remains from 0297

| 0297 Section | Status |
|--------------|--------|
| 3.2 Job Read / Job Acknowledged Columns | NOT STARTED |
| 5.1 Backend Tests | NOT STARTED |
| 5.2 Frontend Tests | NOT STARTED |
| Acceptance Criteria #1 (initial load counters) | NEEDS VERIFICATION |
| Acceptance Criteria #3 (tests pass) | NOT STARTED |

---

## 6. Testing Performed

1. Fresh project staged via UI
2. Orchestrator ran staging workflow
3. Sent `STAGING_COMPLETE` broadcast via MCP `send_message` tool
4. Verified message counters updated in real-time on LaunchTab
5. Verified counters persist correctly when switching to JobsTab

---

## 7. Architecture Notes

**WebSocket Event Flow:**
```
Backend: MessageService.send_message()
    ↓
    WebSocketManager.broadcast_message_sent()
    WebSocketManager.broadcast_message_received()
    ↓
Frontend: websocketIntegrations.js listeners
    ↓
    projectTabsStore.handleMessageSent/Received()
    ↓
    Vue reactivity updates UI
```

**Key Insight:** The pattern follows existing architecture - `agent_update`, `project_update`, etc. all route through `websocketIntegrations.js` to update stores. Message events now follow the same pattern.

---

## 8. Files for Next Agent to Review

- `frontend/src/stores/projectTabs.js` (lines 574-660) - New handlers
- `frontend/src/stores/websocketIntegrations.js` (lines 211-246) - Global listeners
- `handovers/completed/0297_UI_MESSAGE_STATUS_AND_JOB_SIGNALING-C.md` - Parent handover (archived)
- `handovers/0334_HTTP_ONLY_MCP_CONSOLIDATION.md` - Steps column fix (remaining from 0297)

---

## 9. Commit Reference

```
bef0f509 fix: Real-time message counter updates via global WebSocket handlers
```
