# Visualization Proposal 3: Real-Time Agent Orchestration with MCP Message Queue

**Document Type**: Implementation-Ready Proposal Based on AKE-MCP Success
**Created**: 2025-10-22
**Status**: PROPOSED - Proven Pattern from AKE-MCP
**Priority**: HIGH - Achievable real-time coordination

---

## Executive Summary

Based on your successful AKE-MCP implementation, we CAN achieve real-time message acknowledgments and agent coordination. The key is embedding message checking instructions in agent prompts and using MCP tools for queue polling. This works with modern subagent architecture where the main Claude/Codex/Gemini agent manages subagent coordination while checking messages between tasks.

---

## 1. How It Actually Works (Proven in AKE-MCP)

### The Pattern That Worked

```
1. Orchestrator broadcasts: "Focus on authentication"
2. Message queued in AgentCommunicationQueue
3. Agent's prompt instructs: "Check messages between todos"
4. Agent calls MCP tool: check_orchestrator_messages()
5. Agent acknowledges: "Received, shifting to auth"
6. UI polls and shows acknowledgment in real-time
```

### With Modern Subagents (2025)

```
Main Agent (Claude/Codex/Gemini)
    ├── Receives prompt with message-checking instructions
    ├── Spawns subagents for specific tasks
    ├── Between subagent tasks: checks message queue
    ├── Passes relevant messages to subagents
    └── Reports back progress and acknowledgments
```

**Key Insight**: The main agent acts as a message broker for its subagents!

---

## 2. Agent Prompt Engineering (The Secret Sauce)

### Base Agent Prompt Template

```markdown
# Agent: {agent_type}
# Project: {project_id}
# Agent ID: {agent_id}

## Core Mission
{mission_description}

## 📬 CRITICAL: Message Queue Protocol

**YOU MUST CHECK MESSAGES BETWEEN EACH MAJOR TASK**

After completing each todo item or subtask:
1. Call `check_orchestrator_messages(agent_id="{agent_id}")`
2. If messages exist:
   - High priority: Handle immediately
   - Normal: Acknowledge and integrate into workflow
   - Low: Acknowledge and continue current task
3. Always acknowledge with: `acknowledge_message(message_id, "Your response")`
4. Report status: `report_status("Current task: X, Progress: Y%")`

## Todo List
{todo_list}

## Subagent Management
When using subagents:
- Pass relevant messages to subagents in their prompts
- Collect subagent responses
- Report consolidated status back to orchestrator

Remember: CHECK MESSAGES BETWEEN EACH TODO ITEM!
```

---

## 3. MCP Tools for Message Queue (What to Build)

### Tool 1: Check Orchestrator Messages

```python
@mcp_tool
async def check_orchestrator_messages(agent_id: str) -> dict:
    """
    Poll message queue for this agent
    Called by agents between tasks
    """
    queue = AgentCommunicationQueue()
    messages = await queue.poll_messages(
        agent_id=agent_id,
        mark_as_read=False  # Don't mark read until acknowledged
    )

    return {
        "messages": [
            {
                "id": msg.id,
                "from": msg.sender_id,
                "content": msg.content,
                "priority": msg.priority,
                "timestamp": msg.created_at
            }
            for msg in messages
        ],
        "count": len(messages),
        "has_high_priority": any(m.priority == "high" for m in messages)
    }
```

### Tool 2: Acknowledge Message

```python
@mcp_tool
async def acknowledge_message(
    message_id: str,
    agent_id: str,
    response: str = "Acknowledged"
) -> dict:
    """
    Acknowledge receipt and understanding of message
    """
    queue = AgentCommunicationQueue()

    # Mark as read
    await queue.mark_message_read(message_id, agent_id)

    # Send acknowledgment back
    await queue.send_message(
        sender_id=agent_id,
        recipient_id="orchestrator",
        content=f"ACK: {response}",
        parent_message_id=message_id,
        priority="normal"
    )

    return {"status": "acknowledged", "message_id": message_id}
```

### Tool 3: Report Status

```python
@mcp_tool
async def report_status(
    agent_id: str,
    current_task: str,
    progress_percent: int,
    details: dict = None
) -> dict:
    """
    Report current status to orchestrator
    Called after each todo item completion
    """
    job_manager = AgentJobManager()

    # Update job status
    await job_manager.update_job_status(
        agent_id=agent_id,
        status="active",
        metadata={
            "current_task": current_task,
            "progress": progress_percent,
            "details": details or {},
            "last_update": datetime.now().isoformat()
        }
    )

    # Also send as message for real-time display
    queue = AgentCommunicationQueue()
    await queue.send_message(
        sender_id=agent_id,
        recipient_id="orchestrator",
        content=f"Status: {current_task} ({progress_percent}%)",
        priority="low"
    )

    return {"status": "reported"}
```

---

## 4. Real-Time UI Updates (What Users See)

### Live Agent Cards

```
┌─────────────────────────────────────┐
│ 🟢 Backend Developer                │
│ Agent ID: backend_dev_123           │
├─────────────────────────────────────┤
│ Messages: 📬 15 | ✓ 14 | ● 1       │
├─────────────────────────────────────┤
│ Last Check: 30 seconds ago ✅       │  <- Real-time!
│ Status: "Working on auth module"    │
├─────────────────────────────────────┤
│ Todo Progress: [4/8] ████░░░░ 50%   │
│                                      │
│ ✓ Setup database                    │
│ ✓ Create user model                 │
│ ✓ Build auth endpoints              │
│ ✓ Add JWT middleware               │
│ ➤ Writing auth tests                │  <- Current
│ ○ Documentation                     │
│ ○ Integration tests                 │
│ ○ Security audit                    │
└─────────────────────────────────────┘
```

### Real-Time Message Flow

```
10:30:15 | YOU: "All agents prioritize authentication"
10:30:16 | Orchestrator: "Broadcasting to all agents..."
10:30:28 | Backend: "ACK: Shifting to auth module"         <- 12 sec
10:30:45 | Frontend: "ACK: Pausing UI, waiting for auth"  <- 29 sec
10:31:02 | Database: "ACK: Creating auth tables first"    <- 46 sec
10:31:15 | Backend: "Status: Auth endpoints 50% complete"
10:32:00 | Backend: "Status: Auth endpoints complete"
10:32:05 | Backend: "Handoff: Auth API ready for Frontend"
10:32:18 | Frontend: "ACK: Received API specs, resuming"
```

**Note**: Acknowledgments happen within 30-60 seconds (agent's check interval)

---

## 5. WebSocket Bridge for UI Updates

### Backend WebSocket Events

```python
# In api/websocket/events.py

async def broadcast_message_event(message: Message):
    """Broadcast when message is sent"""
    await websocket_manager.broadcast({
        "event": "message:sent",
        "data": {
            "from": message.sender_id,
            "to": message.recipient_id,
            "content": message.content,
            "priority": message.priority,
            "timestamp": message.created_at
        }
    })

async def broadcast_acknowledgment(message_id: str, agent_id: str, response: str):
    """Broadcast when message is acknowledged"""
    await websocket_manager.broadcast({
        "event": "message:acknowledged",
        "data": {
            "message_id": message_id,
            "agent_id": agent_id,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    })

async def broadcast_status_update(agent_id: str, status: dict):
    """Broadcast agent status updates"""
    await websocket_manager.broadcast({
        "event": "agent:status",
        "data": {
            "agent_id": agent_id,
            "current_task": status["current_task"],
            "progress": status["progress"],
            "last_check": datetime.now().isoformat()
        }
    })
```

---

## 6. Orchestrator Intelligence Layer

### Smart Message Routing

```python
class ProjectOrchestrator:

    async def handle_user_message(self, message: str) -> dict:
        """
        Interpret user intent and route appropriately
        """

        # Parse intent
        if "all agents" in message.lower():
            # Broadcast to everyone
            await self.broadcast_to_all(message, priority="high")
            return {"action": "broadcast", "recipients": "all"}

        # Detect urgency
        priority = "high" if any(word in message.lower()
            for word in ["urgent", "immediately", "now", "asap"]) else "normal"

        # Smart routing based on content
        if "auth" in message or "login" in message:
            await self.send_to_agent("backend_dev", message, priority)

        if "ui" in message or "frontend" in message:
            await self.send_to_agent("frontend_dev", message, priority)

        # Handle dependencies
        if "waiting" in message or "blocked" in message:
            await self.resolve_dependency(message)

        return {"action": "routed", "priority": priority}
```

---

## 7. Timeline Comparison: AKE-MCP vs GiljoAI

| Aspect | AKE-MCP (What Worked) | GiljoAI (What We'll Build) |
|--------|----------------------|---------------------------|
| **Message Queue** | ✅ Had MessageQueue class | ✅ Have AgentCommunicationQueue |
| **Polling Mechanism** | ✅ Agents polled every 30s | 🔨 Add MCP tools for polling |
| **Acknowledgments** | ✅ Real-time ACKs | 🔨 Will work same way |
| **Broadcast** | ✅ Orchestrator broadcast | ✅ Already have broadcast |
| **UI Updates** | ✅ WebSocket events | ✅ Have WebSocket infrastructure |
| **Agent Prompts** | ✅ Hardcoded check instructions | 🔨 Add to prompt template |

**Implementation Effort**: 1-2 weeks (most infrastructure exists!)

---

## 8. User Experience: What This Enables

### Realistic Scenarios

**Scenario 1: Mid-flight Course Correction**
```
User sees Frontend struggling with API
User: "Backend, please provide OpenAPI spec to Frontend"
Backend (within 45s): "ACK: Generating OpenAPI spec"
Backend (2 min later): "Status: Spec posted to shared context"
Frontend (30s later): "ACK: Retrieved spec, resuming development"
```

**Scenario 2: Coordinated Pivot**
```
User: "All agents: Client wants mobile-first, adjust your work"
Backend (30s): "ACK: Prioritizing mobile API endpoints"
Frontend (45s): "ACK: Switching to responsive design"
Database (50s): "ACK: Optimizing for mobile data patterns"
Tester (55s): "ACK: Updating test suite for mobile"
```

**Scenario 3: Dependency Resolution**
```
Frontend: "Status: Blocked - need user auth endpoints"
Orchestrator: "Routing dependency to Backend"
Backend (30s): "ACK: Expediting auth endpoints"
Backend (5 min): "Status: Auth endpoints complete"
Orchestrator: "Frontend, auth endpoints ready"
Frontend (30s): "ACK: Resuming development"
```

---

## 9. Implementation Roadmap

### Week 1: Core Infrastructure
- [ ] Day 1-2: Create MCP tools (check_messages, acknowledge, report_status)
- [ ] Day 3: Update agent prompt templates with message checking
- [ ] Day 4: WebSocket event broadcasting
- [ ] Day 5: Test with single agent

### Week 2: Full Integration
- [ ] Day 6-7: Multi-agent testing
- [ ] Day 8: UI components (real-time cards)
- [ ] Day 9: Message flow visualization
- [ ] Day 10: Integration testing

---

## 10. Why This Will Work

1. **Proven Pattern**: AKE-MCP demonstrated this works
2. **Infrastructure Ready**: AgentCommunicationQueue exists
3. **Simple Implementation**: Just MCP tools + prompt instructions
4. **Subagent Compatible**: Main agent handles message broker role
5. **Real Value**: True visibility and control, not pretend real-time

The key insight: **We don't need push notifications to agents**. Regular polling (30-60 seconds) with prompt-embedded instructions gives users the real-time feel they want while respecting how CLI agents actually work.

---

## Conclusion

This isn't theoretical - you've already proven it works in AKE-MCP. With modern subagents, it's even better because the main agent can coordinate message distribution to its subagents. Users get real-time acknowledgments, agents stay coordinated, and the orchestrator maintains control.

**Next Step**: Implement the three MCP tools and update agent prompts. Everything else is already built!