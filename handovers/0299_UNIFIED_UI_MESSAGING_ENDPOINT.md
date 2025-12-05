# Handover 0299: Unified UI Messaging Endpoint

## Status: READY FOR IMPLEMENTATION
## Priority: HIGH
## Type: Backend + Frontend Refactor
## Depends On: 0295 (Messaging Contract)

---

## 1. Problem Statement

The current UI messaging flow is overcomplicated and broken:

**Current broken flow:**
```
UI → api.agentJobs.sendMessage() → /api/agent-jobs/{jobId}/messages
   → AgentJobRepository.get_job_by_job_id() → AgentJobRepository.add_message()
   → WebSocket broadcast → DB write
```

**Issues:**
- 500 errors: `type object 'Job' has no attribute 'job_id'`
- Missing `await` on async calls
- Different endpoints for broadcast vs direct (inconsistent)
- Multiple layers touching messaging (MessageService, AgentMessageQueue, AgentJobRepository)
- Hard to debug and maintain

**What works perfectly:**
- MCP `send_message` tool via `MessageService.send_message()` - tested and confirmed working
- Messages appear correctly in database
- WebSocket events fire properly

---

## 2. Solution: Unified Messaging Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      MessageService                              │
│         (Single source of truth for ALL messaging)              │
│                           ↓                                      │
│              messages table + JSONB mirror + WebSocket          │
└─────────────────────────────────────────────────────────────────┘
                    ↑                           ↑
                    │                           │
        ┌───────────┴───────────┐   ┌──────────┴──────────┐
        │   Remote Agents       │   │   Web UI User       │
        │   (User's laptop)     │   │   (Browser)         │
        │                       │   │                     │
        │   HTTP MCP /mcp       │   │   REST /api/v1/     │
        │   • send_message      │   │   messages/send     │
        │   • receive_messages  │   │                     │
        │   • acknowledge_msg   │   │   from_agent="user" │
        │   • list_messages     │   │   to_agents=[...]   │
        └───────────────────────┘   └─────────────────────┘
```

Both remote agents AND web UI users use the same `MessageService` backend.

---

## 3. Implementation Tasks

### 3.1 Backend: Add `/api/v1/messages/send` endpoint

**File:** `api/endpoints/messages.py`

Add new endpoint:

```python
class MessageSendRequest(BaseModel):
    project_id: str
    to_agents: list[str]  # ["all"] for broadcast, or ["job-id-here"] for direct
    content: str
    message_type: str = "direct"  # "direct" or "broadcast"
    priority: str = "normal"

@router.post("/send", response_model=dict)
async def send_message_from_ui(
    payload: MessageSendRequest,
    current_user: User = Depends(get_current_user),
    tenant_key: str = Depends(get_tenant_key),
):
    """
    Unified endpoint for UI messaging (broadcast and direct).
    Uses the same MessageService that MCP tools use.
    """
    from api.app import state

    message_service = MessageService(state.db_manager, state.tenant_manager)

    result = await message_service.send_message(
        to_agents=payload.to_agents,
        content=payload.content,
        project_id=payload.project_id,
        message_type=payload.message_type,
        priority=payload.priority,
        from_agent="user",
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to send message"))

    return result
```

### 3.2 Frontend: Update api.js

**File:** `frontend/src/services/api.js`

Replace the broken `agentJobs.sendMessage` and `agentJobs.broadcast` with unified call:

```javascript
// In messages object (around line 284)
messages: {
  // ... existing methods ...

  // NEW: Unified send for both broadcast and direct
  send: (projectId, toAgents, content, messageType = 'direct', priority = 'normal') =>
    apiClient.post('/api/v1/messages/send', {
      project_id: projectId,
      to_agents: toAgents,
      content: content,
      message_type: messageType,
      priority: priority,
    }),
},
```

### 3.3 Frontend: Update projectTabs.js

**File:** `frontend/src/stores/projectTabs.js`

Simplify `sendMessage` function (around line 451):

```javascript
async sendMessage(content, recipient) {
  if (!this.currentProject) return

  try {
    // Determine to_agents based on recipient
    let toAgents
    let messageType

    if (recipient === 'broadcast') {
      toAgents = ['all']
      messageType = 'broadcast'
    } else {
      // Find orchestrator job_id
      const orchestratorJob = this.agents.find((a) => a.agent_type === 'orchestrator')
      if (!orchestratorJob) {
        throw new Error('Orchestrator not found')
      }
      toAgents = [orchestratorJob.job_id]
      messageType = 'direct'
    }

    // Use unified endpoint
    const response = await api.messages.send(
      this.currentProject.id,
      toAgents,
      content,
      messageType
    )

    // Add to local messages
    this.addMessage({
      id: response.data.message_id,
      from: 'user',
      to_agent: recipient === 'broadcast' ? null : 'orchestrator',
      content,
      type: messageType,
      timestamp: new Date().toISOString(),
      status: 'sent',
    })

  } catch (err) {
    console.error('Failed to send message:', err)
    throw err
  }
}
```

### 3.4 Remove/Deprecate Old Endpoints

Mark as deprecated (do NOT delete yet):
- `api.agentJobs.sendMessage` in api.js
- `api.agentJobs.broadcast` in api.js
- `/api/agent-jobs/{job_id}/messages` POST endpoint in agent_management.py

---

## 4. Test Plan

### 4.1 Manual Testing

1. **Broadcast from UI:**
   - Click "Broadcast" button in Jobs tab
   - Type message, send
   - Verify: No errors, message appears in message list
   - Verify: Agent can retrieve via `receive_messages` MCP tool

2. **Direct to Orchestrator from UI:**
   - Click "Orchestrator" button in Jobs tab
   - Type message, send
   - Verify: No errors, message delivered to orchestrator
   - Verify: Orchestrator can retrieve via `receive_messages`

3. **MCP still works:**
   - Agent sends message via `send_message` MCP tool
   - Verify: Still works as before

### 4.2 Automated Tests

Create `tests/api/test_unified_message_send.py`:

```python
async def test_send_broadcast_from_ui():
    """UI broadcast uses unified endpoint"""

async def test_send_direct_to_orchestrator():
    """UI direct message to orchestrator uses unified endpoint"""

async def test_unified_endpoint_uses_message_service():
    """Verify endpoint calls MessageService.send_message"""
```

---

## 5. Files to Modify

| File | Change |
|------|--------|
| `api/endpoints/messages.py` | Add `/send` endpoint |
| `frontend/src/services/api.js` | Add `messages.send()`, deprecate old |
| `frontend/src/stores/projectTabs.js` | Use new unified endpoint |
| `frontend/` | Rebuild with `npm run build` |

---

## 6. Acceptance Criteria

1. User can send broadcast messages from UI without errors
2. User can send direct messages to orchestrator from UI without errors
3. Both use the same `/api/v1/messages/send` endpoint
4. `MessageService.send_message()` is the single code path
5. MCP messaging continues to work unchanged
6. All tests pass

---

## 7. Context for New Agent

**Recent commits related to this work:**
- `4eac3e88` - fix: Add missing await for async repository calls
- `e611b2d7` - fix: Restore agent_jobs router
- `0ba1c838` - fix: Unify direct message endpoint
- `e080b7df` - Fix 405 Method Not Allowed error
- `d4090927` - fix: Convert JSON to JSONB columns

**Key files to understand:**
- `src/giljo_mcp/services/message_service.py` - The working MessageService
- `src/giljo_mcp/tools/tool_accessor.py` - How MCP tools call MessageService
- `api/endpoints/messages.py` - Existing message endpoints (add /send here)
- `frontend/src/stores/projectTabs.js` - UI message sending logic

**What works:**
- `MessageService.send_message()` - tested via MCP, works perfectly
- `MessageService.receive_messages()` - tested via MCP, works perfectly
- JSONB columns fixed (JSON → JSONB migration applied)

**What's broken:**
- `/api/agent-jobs/{jobId}/messages` - 500 errors, wrong model references
- UI broadcast and direct messaging - both broken due to above
