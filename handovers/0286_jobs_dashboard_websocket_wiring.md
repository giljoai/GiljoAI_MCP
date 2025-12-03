# Handover 0286: Jobs Dashboard WebSocket Wiring

## Status: PENDING
## Priority: HIGH
## Type: Bug Fix / Feature Completion

---

## Problem Statement

The Jobs dashboard at `/projects/{id}?tab=jobs` displays message counts and agent statuses, but these are **NOT updating in real-time** due to WebSocket event name mismatches between backend and frontend.

**Current State:**
- Dashboard shows: Messages Sent, Messages Waiting, Messages Read columns
- Agent status cards with status indicators
- Data loads on initial page load but **does not refresh dynamically**

**Root Cause:**
Backend emits different event names than frontend expects:

| What | Backend Emits | Frontend Listens For |
|------|---------------|---------------------|
| Message sent | `agent_job:message` | `message:sent` |
| New message | `agent_communication:message_sent` | `message:new` |
| Message ack | `agent_communication:message_acknowledged` | `message:acknowledged` |
| Status change | `agent_job:status_update` | `agent:status_changed` |

---

## Scope

### Files to Modify

**Backend (choose ONE approach):**
- `api/websocket.py` - Change event type names to match frontend expectations

**OR Frontend (alternative approach):**
- `frontend/src/components/projects/JobsTab.vue` - Change listeners to match backend event names

**Recommended: Backend changes** - Frontend event names are more semantic and match the documentation.

---

## Implementation Plan

### Phase 1: Audit Current State

1. Document all WebSocket event emissions in `api/websocket.py`
2. Document all WebSocket listeners in `JobsTab.vue`
3. Create mapping table of mismatches

### Phase 2: Fix Event Names (Backend)

Update `api/websocket.py` methods:

```python
# broadcast_job_message (line ~878)
# Change: "agent_job:message" -> "message:new"

# broadcast_agent_job_status_changed (line ~807-815)
# Change: "agent_job:status_update" -> "agent:status_changed"
# Change: "agent_job:acknowledged" -> "agent:status_changed" (with status in payload)
# Change: "agent_job:completed" -> "agent:status_changed"
# Change: "agent_job:failed" -> "agent:status_changed"

# broadcast_message_sent (line ~985)
# Change: "agent_communication:message_sent" -> "message:sent"

# broadcast_message_acknowledged (line ~1048)
# Change: "agent_communication:message_acknowledged" -> "message:acknowledged"
```

### Phase 3: Verify Payload Compatibility

Ensure event payloads match what frontend handlers expect:

**JobsTab.vue handlers expect:**
- `handleMessageSent(data)` - needs `data.job_id`, `data.message_id`, `data.tenant_key`
- `handleNewMessage(data)` - needs `data.job_id`, `data.message`, `data.tenant_key`
- `handleStatusUpdate(data)` - needs `data.job_id`, `data.status`, `data.tenant_key`
- `handleMessageAcknowledged(data)` - needs `data.job_id`, `data.message_id`, `data.tenant_key`

### Phase 4: Test Real-Time Updates

1. Open Jobs dashboard
2. Send message via MCP tool
3. Verify message count updates without refresh
4. Change agent status via MCP tool
5. Verify status badge updates without refresh

---

## Acceptance Criteria

- [ ] Message counts update in real-time when messages are sent
- [ ] Message counts update when messages are acknowledged
- [ ] Agent status badges update when status changes
- [ ] No page refresh required for any dashboard column updates
- [ ] Multi-tenant isolation preserved (events only go to correct tenant)

---

## Technical Notes

### WebSocket Manager Methods to Update

Located in `api/websocket.py`:

1. `broadcast_job_message()` - line ~852
2. `broadcast_agent_job_status_changed()` - line ~780
3. `broadcast_message_sent()` - line ~970
4. `broadcast_message_acknowledged()` - line ~1030

### Frontend Handlers

Located in `frontend/src/components/projects/JobsTab.vue`:

1. `handleMessageSent()` - line ~766
2. `handleNewMessage()` - line ~820
3. `handleStatusUpdate()` - line ~(find)
4. `handleMessageAcknowledged()` - line ~(find)

---

## Dependencies

- None (self-contained fix)

## Related Handovers

- 0130e: Inter-agent messaging (noted this issue but didn't fix)
- 0233: Job read/acknowledged indicators
- 0287: Launch button staging complete signal (depends on this)

---

## Estimated Effort

- Backend changes: 1-2 hours
- Testing: 1 hour
- Total: 2-3 hours

---

## Notes

This is foundational work - once WebSocket events are properly wired, many other real-time features will start working correctly including the Launch button fix in Handover 0287.
