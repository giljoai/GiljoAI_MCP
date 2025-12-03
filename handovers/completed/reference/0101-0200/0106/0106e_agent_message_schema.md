# Handover 0106e: Agent Communication Message Schema (Reference)

**Date**: 2025-11-05
**Status**: 📚 REFERENCE SCHEMA PROJECT
**Priority**: Medium (Documentation)
**Estimated Complexity**: 1-2 hours

---

## Purpose

Define formal schema for all agent-to-agent and orchestrator-to-agent message types. Currently described informally in Handover 0107, needs formalization with JSON schemas and validation.

---

## Scope

### Message Types to Document

**Command Messages** (Orchestrator → Agent):
- `cancel` - Request agent stop work gracefully
- `pause` - Request agent pause and wait
- `resume` - Resume paused agent
- `priority_change` - Adjust agent focus/priority
- `guidance` - Orchestrator provides guidance for blocked agent

**Status Messages** (Agent → Orchestrator):
- `progress_report` - Regular check-in with progress
- `milestone_completed` - Major phase completed
- `blocked` - Agent needs help/guidance
- `question` - Agent has question for orchestrator
- `warning` - Agent encountered non-blocking issue

**Coordination Messages** (Agent ↔ Agent):
- `request_data` - Agent needs data from peer
- `provide_data` - Agent provides requested data
- `handoff` - Agent handing work to peer
- `conflict` - Agents need orchestrator mediation

**System Messages** (Backend → Agent):
- `health_check` - Verify agent responsive
- `context_warning` - Approaching context limit
- `succession_notice` - Orchestrator succession occurring

---

## Schema Format

For each message type, define:

### Message Structure

```typescript
interface BaseMessage {
  id: string;                    // Unique message ID (UUID)
  type: string;                  // Message type (cancel, pause, etc.)
  from_agent: string;            // Sender agent ID
  to_agent: string;              // Recipient agent ID
  priority: "low" | "medium" | "high" | "critical";
  timestamp: string;             // ISO 8601
  tenant_key: string;            // Multi-tenant isolation
  acknowledged: boolean;         // Has recipient read this?
  acknowledged_at?: string;      // When read (ISO 8601)
}

interface CancelMessage extends BaseMessage {
  type: "cancel";
  data: {
    reason: string;              // Why cancellation requested
    deadline?: string;           // When to stop by (ISO 8601)
    cleanup_required: boolean;   // Should agent cleanup before exit?
  };
}
```

---

## Message Type Specifications

### 1. **cancel** (Command)

**Purpose**: Request agent stop work gracefully

**Schema**:
```json
{
  "id": "msg-abc123",
  "type": "cancel",
  "from_agent": "orchestrator-xyz",
  "to_agent": "implementer-def456",
  "priority": "critical",
  "timestamp": "2025-11-05T14:30:00Z",
  "tenant_key": "tenant-123",
  "acknowledged": false,
  "data": {
    "reason": "User requested cancellation",
    "deadline": "2025-11-05T14:35:00Z",
    "cleanup_required": true
  }
}
```

**Agent Response**:
Agent should:
1. Acknowledge message: `acknowledge_message(message_id)`
2. Stop current work
3. If `cleanup_required=true`: cleanup resources, save state
4. Call `complete_job(result={"status": "cancelled", "reason": data.reason})`
5. Exit

**Timeout**: If agent doesn't respond in 5 minutes, user can force-stop

---

### 2. **pause** (Command)

**Purpose**: Request agent pause work and wait

**Schema**:
```json
{
  "id": "msg-def456",
  "type": "pause",
  "from_agent": "orchestrator-xyz",
  "to_agent": "implementer-def456",
  "priority": "high",
  "timestamp": "2025-11-05T14:30:00Z",
  "tenant_key": "tenant-123",
  "acknowledged": false,
  "data": {
    "reason": "Waiting for frontend agent to complete dependency",
    "expected_resume_time": "2025-11-05T15:00:00Z"
  }
}
```

**Agent Response**:
1. Acknowledge message
2. Finish current atomic operation
3. Save state
4. Enter wait loop (check for `resume` message every 30 seconds)
5. When `resume` received: Continue work

---

### 3. **progress_report** (Status)

**Purpose**: Agent reports progress to orchestrator

**Schema**:
```json
{
  "id": "msg-ghi789",
  "type": "progress_report",
  "from_agent": "implementer-def456",
  "to_agent": "orchestrator-xyz",
  "priority": "medium",
  "timestamp": "2025-11-05T14:30:00Z",
  "tenant_key": "tenant-123",
  "acknowledged": false,
  "data": {
    "task": "Implementing authentication endpoints",
    "percent_complete": 45,
    "todos_completed": 3,
    "todos_remaining": 5,
    "context_tokens_estimate": 12000,
    "blockers": [],
    "next_milestone": "Complete password hashing implementation"
  }
}
```

**Orchestrator Response**:
- Acknowledge message
- Update internal tracking
- If blockers present: Send guidance message

---

### 4. **blocked** (Status)

**Purpose**: Agent needs help from orchestrator

**Schema**:
```json
{
  "id": "msg-jkl012",
  "type": "blocked",
  "from_agent": "implementer-def456",
  "to_agent": "orchestrator-xyz",
  "priority": "high",
  "timestamp": "2025-11-05T14:30:00Z",
  "tenant_key": "tenant-123",
  "acknowledged": false,
  "data": {
    "blocker_type": "decision_needed",
    "description": "Unsure whether to use JWT or session-based auth",
    "options": [
      "JWT with RS256 (recommended by security best practices)",
      "Session-based with Redis (simpler implementation)"
    ],
    "context": "User requirements don't specify, both have trade-offs",
    "waiting_for": "orchestrator_decision"
  }
}
```

**Orchestrator Response**:
Send `guidance` message with decision

---

### 5. **guidance** (Command)

**Purpose**: Orchestrator provides guidance to blocked agent

**Schema**:
```json
{
  "id": "msg-mno345",
  "type": "guidance",
  "from_agent": "orchestrator-xyz",
  "to_agent": "implementer-def456",
  "priority": "high",
  "timestamp": "2025-11-05T14:35:00Z",
  "tenant_key": "tenant-123",
  "acknowledged": false,
  "data": {
    "in_response_to": "msg-jkl012",
    "decision": "Use JWT with RS256",
    "reasoning": "Better scalability, stateless, aligns with microservices architecture",
    "additional_instructions": "Implement token refresh logic, 15-minute access tokens, 7-day refresh tokens"
  }
}
```

**Agent Response**:
1. Acknowledge message
2. Implement guidance
3. Send `progress_report` when unblocked

---

## Message Queue Storage

**Database Table**: `agent_messages` (likely already exists)

**Schema**:
```sql
CREATE TABLE agent_messages (
    id VARCHAR(36) PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    from_agent VARCHAR(255) NOT NULL,
    to_agent VARCHAR(255) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    tenant_key VARCHAR(36) NOT NULL,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP WITH TIME ZONE NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_agent_messages_to_agent ON agent_messages(to_agent);
CREATE INDEX idx_agent_messages_tenant ON agent_messages(tenant_key);
CREATE INDEX idx_agent_messages_acknowledged ON agent_messages(acknowledged);
```

---

## MCP Tool Integration

### Sending Messages

```python
@mcp_tool(name="send_message")
async def send_message(
    to_agent: str,
    message: dict,  # Must match schema for message.type
    priority: str = "medium",
    tenant_key: str = None
) -> dict:
    """
    Send message to another agent.

    Validates message against schema for message.type before sending.
    """
    # Validate message schema
    validate_message_schema(message)

    # Store in database
    msg_id = await store_message(...)

    # Broadcast via WebSocket if recipient online
    await broadcast_websocket_event({
        "event": "agent:message_received",
        "to_agent": to_agent,
        "message_id": msg_id
    })

    return {"success": True, "message_id": msg_id}
```

### Receiving Messages

```python
@mcp_tool(name="receive_messages")
async def receive_messages(
    agent_id: str,
    limit: int = 10,
    tenant_key: str = None
) -> dict:
    """
    Retrieve unacknowledged messages for agent.
    """
    messages = await get_unacknowledged_messages(agent_id, limit, tenant_key)

    return {
        "success": True,
        "messages": messages,
        "count": len(messages)
    }
```

---

## Validation & Testing

### Schema Validation

**Backend** (Python with Pydantic):
```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class BaseMsgSchema(BaseModel):
    id: str
    type: str
    from_agent: str
    to_agent: str
    priority: Literal["low", "medium", "high", "critical"]
    timestamp: str
    tenant_key: str
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None

class CancelMsgData(BaseModel):
    reason: str
    deadline: Optional[str] = None
    cleanup_required: bool = True

class CancelMsg(BaseMsgSchema):
    type: Literal["cancel"]
    data: CancelMsgData

# Validate before sending
msg = CancelMsg(**msg_dict)  # Raises ValidationError if invalid
```

**Frontend** (TypeScript):
```typescript
import { z } from 'zod';

const BaseMsgSchema = z.object({
  id: z.string().uuid(),
  type: z.string(),
  from_agent: z.string(),
  to_agent: z.string(),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
  timestamp: z.string().datetime(),
  tenant_key: z.string(),
  acknowledged: z.boolean(),
  acknowledged_at: z.string().datetime().optional()
});

const CancelMsgSchema = BaseMsgSchema.extend({
  type: z.literal('cancel'),
  data: z.object({
    reason: z.string(),
    deadline: z.string().datetime().optional(),
    cleanup_required: z.boolean()
  })
});

// Validate received message
const msg = CancelMsgSchema.parse(receivedData);
```

---

## Testing Checklist

### For Each Message Type

- [ ] Schema validation (valid messages pass)
- [ ] Schema validation (invalid messages rejected)
- [ ] Message storage in database
- [ ] Message retrieval via `receive_messages()`
- [ ] Multi-tenant isolation (can't read other tenant's messages)
- [ ] Acknowledgment tracking
- [ ] WebSocket broadcast on new message
- [ ] Frontend handler processes message correctly

---

## Success Criteria

- [ ] All message types documented with schemas
- [ ] JSON/TypeScript schemas defined
- [ ] Pydantic models created for backend validation
- [ ] Zod schemas created for frontend validation
- [ ] MCP tools updated to validate messages
- [ ] Testing checklist completed
- [ ] Examples provided for each message type
- [ ] Integration with 0107 verified

---

## Output Location

**Primary**: `docs/reference/AGENT_MESSAGE_SCHEMA.md`

**Secondary**:
- `src/giljo_mcp/schemas/messages.py` (Pydantic models)
- `frontend/src/types/messages.ts` (TypeScript types)

---

## Dependencies

**Related Handovers**:
- 0107 (Agent monitoring - uses these messages)
- 0106 (Template instructions - agents must follow schema)
- Agent Job Management (message queue implementation)

---

## Notes

**Version**: 1.0 (Schema Project)
**Last Updated**: 2025-11-05
**Author**: System Architect
**Status**: Not started - Schema definition required

**Estimated Effort**:
- Schema documentation: 1 hour
- Pydantic model creation: 30 minutes
- TypeScript type creation: 30 minutes
- Testing: 30 minutes
- **Total: 2-3 hours**

**Priority**: Medium (important for robustness, but not blocking MVP)

**Note**: Can start with subset of messages (cancel, progress_report, blocked, guidance) and expand later.
