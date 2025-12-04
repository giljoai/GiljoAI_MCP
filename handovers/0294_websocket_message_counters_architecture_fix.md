# Handover 0294: WebSocket Message Counters - Architecture Fix

**Date**: 2025-12-04
**Status**: 🔄 IN PROGRESS (Partial Fix)
**Priority**: CRITICAL - Production blocking
**Supersedes**: Handover 0293 (initialization fix → architecture redesign)

---

## Executive Summary

Handover 0293 fixed WebSocket manager initialization, but testing revealed a **fundamental architecture issue**: We were only emitting ONE event (`message:sent`) for both sender and recipient counters. This session implemented a **two-event architecture** but counters still have issues:

1. ✅ **FIXED**: WebSocket manager initialization order
2. ✅ **FIXED**: Broadcast detection (`to_agents=['all']` now handled correctly)
3. ✅ **IMPLEMENTED**: Two-event WebSocket architecture
4. ❌ **BROKEN**: Counters still showing on orchestrator only (not recipients)
5. ❌ **BROKEN**: Counter persistence on page refresh

---

## Root Cause Analysis

### Original Architecture (WRONG)
```
Message Sent → ONE WebSocket Event (`message:sent`)
               ↓
            Frontend tries to increment BOTH counters from ONE event
               ↓
            "Messages Sent" on sender ✅
            "Messages Waiting" on sender ❌ (should be on recipient!)
```

### New Architecture (CORRECT DESIGN)
```
Message Sent → TWO WebSocket Events:

Event 1: `message:sent` → Broadcast to ALL clients
         ↓
         Frontend increments "Messages Sent" on SENDER agent card

Event 2: `message:received` → Broadcast to ALL clients
         ↓
         Frontend increments "Messages Waiting" on RECIPIENT agent card(s)
```

---

## Implementation Summary

### Backend Changes

#### 1. New WebSocket Event Method
**File**: `api/websocket.py` (lines 1017-1085)

**Created**: `broadcast_message_received()` method

```python
async def broadcast_message_received(
    self,
    message_id: str,
    job_id: str,  # Sender's job_id
    tenant_key: str,
    from_agent: str,
    to_agent_ids: list[str],  # List of recipient job IDs
    message_type: str,
    content_preview: str,
    priority: int,
    timestamp: Optional[datetime] = None,
    project_id: Optional[str] = None,
):
```

**Event Payload**:
```json
{
  "type": "message:received",
  "data": {
    "message_id": "uuid",
    "from_agent": "orchestrator",
    "to_agent_ids": ["job-id-1", "job-id-2", ...],
    "content": "message preview",
    "tenant_key": "tk_xxx",
    "priority": 1,
    "timestamp": "2025-12-04T..."
  }
}
```

#### 2. MessageService Updates
**File**: `src/giljo_mcp/services/message_service.py` (lines 150-202)

**Changes**:
- Now emits TWO events per message (not one)
- Fetches ALL agent job IDs for broadcasts
- Uses provided job IDs for direct messages

```python
# Event 1: Broadcast to SENDER (increments "Messages Sent")
await self._websocket_manager.broadcast_message_sent(
    from_agent=from_agent or "orchestrator",
    to_agent=to_agent_value,  # None for broadcast, job_id for direct
    ...
)

# Event 2: Broadcast to RECIPIENT(S) (increments "Messages Waiting")
if to_agents[0] == 'all':
    # Broadcast: Get ALL agent job IDs
    result = await session.execute(
        select(MCPAgentJob).where(MCPAgentJob.project_id == project.id)
    )
    all_agents = result.scalars().all()
    recipient_job_ids = [agent.job_id for agent in all_agents]
else:
    # Direct message: Use provided IDs
    recipient_job_ids = to_agents

await self._websocket_manager.broadcast_message_received(
    from_agent=from_agent or "orchestrator",
    to_agent_ids=recipient_job_ids,
    ...
)
```

#### 3. Diagnostic Logging Added
**File**: `src/giljo_mcp/services/message_service.py` (lines 144-148, 171, 183, 187, 202)

```python
self._logger.info(f"[WEBSOCKET DEBUG] websocket_manager is {'AVAILABLE' if self._websocket_manager else 'NONE'}")
self._logger.info(f"[WEBSOCKET DEBUG] Successfully broadcast message_sent {message_id}")
self._logger.info(f"[WEBSOCKET DEBUG] Broadcast to all: {len(recipient_job_ids)} recipients")
self._logger.info(f"[WEBSOCKET DEBUG] Direct message to: {recipient_job_ids}")
self._logger.info(f"[WEBSOCKET DEBUG] Successfully broadcast message_received to {len(recipient_job_ids)} recipient(s)")
```

### Frontend Changes

#### 1. New Event Handler
**File**: `frontend/src/components/projects/JobsTab.vue` (lines 838-878)

**Created**: `handleMessageReceived()` function

```javascript
const handleMessageReceived = (data) => {
  // Multi-tenant isolation check
  if (!currentTenantKey.value || data.tenant_key !== currentTenantKey.value) {
    return
  }

  console.log('[JobsTab] Message received event:', data)

  // data.to_agent_ids contains array of recipient job IDs
  const recipientJobIds = data.to_agent_ids || []

  recipientJobIds.forEach((recipientJobId) => {
    const recipientAgent = props.agents.find(
      (a) =>
        a.job_id === recipientJobId ||
        a.id === recipientJobId ||
        a.agent_id === recipientJobId
    )

    if (recipientAgent) {
      if (!recipientAgent.messages) recipientAgent.messages = []
      recipientAgent.messages.push({
        id: data.message_id,
        from: data.from_agent,
        direction: 'inbound',
        status: 'waiting',  // "Messages Waiting" counter
        text: data.content || data.content_preview || data.message || '',
        priority: data.priority || 'medium',
        timestamp: data.timestamp || new Date().toISOString(),
      })

      console.log(
        `[JobsTab] Added WAITING message to ${recipientAgent.agent_type} (recipient)`
      )
    }
  })
}
```

#### 2. Event Listener Registration
**File**: `frontend/src/components/projects/JobsTab.vue` (lines 933-947)

```javascript
onMounted(() => {
  on('agent:status_changed', handleStatusUpdate)
  on('message:sent', handleMessageSent)
  on('message:received', handleMessageReceived)  // NEW
  on('message:acknowledged', handleMessageAcknowledged)
  on('message:new', handleNewMessage)
})

onUnmounted(() => {
  off('agent:status_changed', handleStatusUpdate)
  off('message:sent', handleMessageSent)
  off('message:received', handleMessageReceived)  // NEW
  off('message:acknowledged', handleMessageAcknowledged)
  off('message:new', handleNewMessage)
})
```

---

## Files Modified

### Backend (3 files)
1. ✅ `api/websocket.py` - Added `broadcast_message_received()` method
2. ✅ `src/giljo_mcp/services/message_service.py` - Two-event emission logic
3. ✅ `api/app.py` - WebSocketManager initialization order (from 0293)

### Frontend (1 file)
1. ✅ `frontend/src/components/projects/JobsTab.vue` - New `message:received` handler

---

## Testing Results

### User Test 1: Broadcast Message
**Command**: `send_message(to_agents=["all"], content="broadcast test message")`

**Expected Behavior**:
- "Messages Sent" counter increments on ORCHESTRATOR card
- "Messages Waiting" counter increments on ALL agent cards (5 agents)

**Actual Behavior**:
- ❌ Counters still showing on orchestrator only
- ❌ Not showing on recipient agents

### User Test 2: Direct Message
**Command**: `send_message(to_agents=["b1c7300e-b090-4d52-9704-725b9ec2b319"], content="Direct message test")`

**Expected Behavior**:
- "Messages Sent" counter increments on ORCHESTRATOR card
- "Messages Waiting" counter increments on DOCUMENTATION SPECIALIST card

**Actual Behavior**:
- ❌ Counters still showing on orchestrator only
- ❌ Not showing on Documentation Specialist

### User Test 3: Counter Persistence
**Action**: Refresh page

**Expected Behavior**:
- Counters should persist (loaded from database)

**Actual Behavior**:
- ❌ Counters reset to 0

---

## Remaining Issues

### Issue 1: Counters Not Appearing on Recipients
**Problem**: `message:received` events are being broadcast, but frontend is not incrementing counters on recipient agents.

**Possible Causes**:
1. **Agent matching logic** - Frontend may not be finding agents by `job_id`
2. **Event not reaching frontend** - WebSocket broadcast may not be working
3. **Frontend reactive update** - Vue reactivity may not be triggering

**Debugging Steps**:
1. Check backend logs for `[WEBSOCKET DEBUG] Successfully broadcast message_received to X recipient(s)`
2. Check frontend console for `[JobsTab] Message received event:` logs
3. Check if `to_agent_ids` array is populated correctly
4. Verify agent matching logic is finding the correct agents

### Issue 2: Counter Persistence
**Problem**: Counters disappear on page refresh.

**Root Cause**: Counters are stored in `agent.messages` array (in-memory Vue reactive state), not persisted to database.

**Solution Required**:
- Option A: Load messages from database on page load and populate counters
- Option B: Store counter values directly in `MCPAgentJob` model fields
- Option C: Compute counters from database query on page load

---

## MCP Tool Verification

**User's Agent Usage** (Confirmed Correct):
```javascript
// Broadcast
send_message(to_agents: ["all"], content: "...", project_id: "...", message_type: "broadcast")

// Direct
send_message(to_agents: ["job-id"], content: "...", project_id: "...", message_type: "direct")
```

✅ **MCP tool signature is correct** - matches backend implementation.

---

## Architecture Notes

### Message Flow
```
User/Agent → MCP send_message() → MessageService.send_message()
                                   ↓
                          Two WebSocket broadcasts:
                                   ↓
                    ┌──────────────┴──────────────┐
                    ↓                              ↓
          broadcast_message_sent()    broadcast_message_received()
          (to ALL clients)             (to ALL clients)
                    ↓                              ↓
          Frontend: handleMessageSent  Frontend: handleMessageReceived
          (increment sender counter)   (increment recipient counter)
```

### Key Design Decisions
1. **Broadcast to ALL clients** - Both events are broadcast tenant-wide, frontend filters by agent
2. **Job ID matching** - Recipients identified by `job_id` field
3. **Array of recipients** - `to_agent_ids` supports both broadcast (multiple) and direct (single)
4. **Multi-tenant isolation** - All events include `tenant_key` for frontend validation

---

## Next Steps for Fresh Agent

### Priority 1: Debug Why Counters Not Showing on Recipients
1. **Check backend logs** - Look for `[WEBSOCKET DEBUG]` entries when sending messages
2. **Check frontend console** - Look for `[JobsTab] Message received event:` logs
3. **Verify WebSocket broadcast** - Ensure `message:received` events are reaching frontend
4. **Debug agent matching** - Add console logs in `handleMessageReceived()` to see if agents are found
5. **Check Vue reactivity** - Verify `recipientAgent.messages.push()` triggers counter update

### Priority 2: Implement Counter Persistence
1. **Decision**: Choose persistence strategy (A, B, or C above)
2. **Implementation**: Store counters or load from database on page refresh
3. **Testing**: Verify counters persist across page reloads

### Priority 3: Clean Up Diagnostic Logging
Once working, remove or reduce `[WEBSOCKET DEBUG]` logging verbosity.

---

## Success Criteria

All criteria must be met:

- [ ] Broadcast message: "Messages Sent" increments on ORCHESTRATOR
- [ ] Broadcast message: "Messages Waiting" increments on ALL agent cards (5 agents)
- [ ] Direct message: "Messages Sent" increments on ORCHESTRATOR
- [ ] Direct message: "Messages Waiting" increments on SPECIFIC recipient agent
- [ ] Counters persist across page refresh
- [ ] Backend logs show both `broadcast_message_sent` and `broadcast_message_received`
- [ ] Frontend console shows `[JobsTab] Message received event:` logs
- [ ] No errors in backend or frontend logs

---

## Reference Materials

### Related Handovers
- **0292**: Initial diagnostic analysis
- **0293**: WebSocket manager initialization fix (superseded by this handover)

### Key Files to Understand
1. `api/websocket.py` - WebSocketManager with broadcast methods
2. `src/giljo_mcp/services/message_service.py` - Message sending logic
3. `frontend/src/components/projects/JobsTab.vue` - Counter display and event handling
4. `handovers/Reference_docs/giljoai workflow.pdf` - Architecture diagram

### User Feedback (Critical Context)
> "messages are not persistent, they still show up only for orchestrator both messages sent and messages waiting"

This confirms:
1. Events ARE being received (counters showing on orchestrator)
2. Events are NOT reaching recipients (counters not showing on other agents)
3. Persistence is broken (counters disappear on refresh)

---

*Handover created: 2025-12-04*
*Last updated: 2025-12-04*
*Status: READY FOR FRESH AGENT TAKEOVER*
