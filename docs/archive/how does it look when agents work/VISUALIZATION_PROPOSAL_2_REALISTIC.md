# Visualization Proposal 2: Realistic Agent Orchestration Interface

**Document Type**: Implementation-Ready UI Proposal
**Created**: 2025-10-22
**Status**: PROPOSED - Based on Actual Backend Capabilities
**Priority**: HIGH - Leverages existing infrastructure

---

## Executive Summary

A practical implementation that leverages your existing `AgentJobManager`, `JobCoordinator`, and `AgentCommunicationQueue` backend with realistic CLI agent capabilities. This proposal focuses on what we can actually build today with Claude Code, Codex, and Gemini CLI agents.

---

## 1. Reality Check: What CLI Agents Can Actually Do

### Current Agent Capabilities
- **Claude Code**: Can read/write files, execute commands, maintain context
- **Codex**: Similar file operations, specialized for code generation
- **Gemini**: File operations, analytical tasks
- **All agents**: Work in separate CLI windows, can't directly receive real-time messages

### The Bridge: Message Queue Pattern
```
User → Orchestrator → AgentCommunicationQueue → Agent polls queue → Agent acts
```

### Realistic Communication Flow
1. User messages orchestrator via UI
2. Orchestrator adds to `AgentCommunicationQueue` (already built!)
3. CLI agents poll queue at task boundaries (via MCP tool)
4. Agents acknowledge and act
5. Agents report progress back via queue

---

## 2. The Practical Three-View System

### View 1: Mission Briefing (What We Can Actually Generate)

**Reality**: Your `ProjectOrchestrator` already has `generate_mission_from_vision()`

```python
# From your codebase
mission = await orchestrator.generate_mission_from_vision(
    vision_content=project.vision,
    condensation_level=0.7  # Your token reduction
)
```

**UI Shows**:
```
┌─────────────────────────────────────────────────┐
│ Mission: E-commerce Platform MVP                │
├─────────────────────────────────────────────────┤
│ Generated from 50KB vision → 5KB mission        │
│                                                  │
│ Phase 1: Database Schema                        │
│ • User authentication tables                    │
│ • Product catalog structure                     │
│ • Order management system                       │
│                                                  │
│ Assigned Agents:                                │
│ [Backend Dev] - Database & API                  │
│ [Frontend Dev] - React components               │
│ [Test Engineer] - Integration tests             │
│                                                  │
│ ┌────────────────────────────────────┐         │
│ │ Start Command (click to copy):     │         │
│ │ /orchestrate execute mission_id_123│         │
│ └────────────────────────────────────┘         │
└─────────────────────────────────────────────────┘
```

---

### View 2: Active Orchestration (Realistic Agent Monitoring)

**What Actually Happens**:
- Agents check queue every 5-10 minutes (between major tasks)
- Agents report status via `job_coordinator.update_job_status()`
- Messages flow through `AgentCommunicationQueue`

```
┌──────────────────────────────────────────────────────────────┐
│ Project: E-commerce MVP | Elapsed: 24 min | Active Agents: 3 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Agent Cards                    │  Orchestrator Chat        │
│                                 │                           │
│  ┌─────────────────────┐       │  YOU: Please prioritize   │
│  │ 🟢 Backend Developer │       │  authentication first     │
│  │ Last Check: 2 min ago│       │                           │
│  │ Queue: 1 pending msg │       │  ORCH: Broadcasting to    │
│  │                      │       │  all agents...            │
│  │ Current Milestone:   │       │                           │
│  │ "Building auth API"  │       │  BACKEND: ACK - shifting  │
│  │                      │       │  to auth module [2m ago]  │
│  │ Files Modified: 12   │       │                           │
│  │ Tests Written: 8     │       │  ┌─────────────────────┐ │
│  └─────────────────────┘       │  │ Message orchestrator  │ │
│                                │  │ to broadcast...       │ │
│  ┌─────────────────────┐       │  └─────────────────────┘ │
│  │ 🟡 Frontend Dev      │       │  [Send to Orchestrator]  │
│  │ Last Check: 5 min ago│       │                           │
│  │ Queue: 0 pending     │       └───────────────────────────┤
│  │                      │                                   │
│  │ Current Milestone:   │       Orchestrator Intelligence:  │
│  │ "Waiting for API"    │       • Auto-assigns tasks        │
│  │                      │       • Manages dependencies      │
│  │ Files Modified: 8    │       • Broadcasts instructions   │
│  │ Components: 5        │       • Synthesizes updates       │
│  └─────────────────────┘       └───────────────────────────┘
```

**Realistic Agent Card Features**:
- **Last Check**: When agent last polled the queue (not real-time!)
- **Queue Status**: Messages waiting for next poll
- **Current Milestone**: High-level task (not granular steps)
- **Work Metrics**: Files changed, tests written (pulled from git)

---

## 3. How Message Queue Actually Works

### Backend Reality (You Already Have This!)

```python
# From your agent_communication_queue.py
async def send_message(
    sender_id: str,
    recipient_id: str,  # Can be "orchestrator" or "broadcast"
    content: str,
    priority: str = "normal"
)

async def poll_messages(
    agent_id: str,
    mark_as_read: bool = True
) -> List[Message]
```

### CLI Agent Implementation (MCP Tool)

```python
# New MCP tool for agents: check_orchestrator_queue.py
@tool
async def check_orchestrator_queue():
    """Check for new instructions from orchestrator"""
    messages = await queue.poll_messages(
        agent_id=current_agent_id,
        mark_as_read=True
    )
    return messages

# In agent's workflow (Claude/Codex/Gemini)
# Every 5-10 minutes or at task boundaries:
messages = check_orchestrator_queue()
if messages:
    process_new_instructions(messages)
```

### User Interaction Pattern

```
User Types: "All agents focus on authentication first"
     ↓
Orchestrator Receives & Interprets
     ↓
Orchestrator Broadcasts:
{
  "directive": "PRIORITY_CHANGE",
  "target": "authentication",
  "agents": ["backend", "frontend", "test"]
}
     ↓
Agents Poll (within 5-10 min) & Acknowledge
     ↓
UI Updates with Acknowledgments
```

---

## 4. Realistic Status Updates

### What Agents Can Report (via MCP tool)

```python
@tool
async def report_milestone(milestone: str, metrics: dict):
    """Report major milestone to orchestrator"""
    await job_coordinator.update_job_status(
        job_id=current_job_id,
        status="active",
        metadata={
            "milestone": milestone,
            "metrics": metrics,
            "timestamp": datetime.now()
        }
    )

# Agent uses this every 10-15 minutes:
report_milestone(
    "Completed user authentication module",
    {
        "files_created": 5,
        "files_modified": 3,
        "tests_passed": 12,
        "coverage": 85
    }
)
```

### What UI Shows (Realistic Updates)

```
Timeline View (Actual events, not imaginary):
─────────────────────────────────────────────────
10:00 AM | Project Started
10:02 AM | Backend Agent: Acknowledged mission
10:15 AM | Backend Agent: Database schema complete
10:18 AM | Frontend Agent: Acknowledged mission
10:25 AM | Frontend Agent: Waiting for API endpoints
10:30 AM | You: "Backend, please share API docs"
10:32 AM | Orchestrator: Relayed message to Backend
10:38 AM | Backend Agent: Posted API docs to shared
10:45 AM | Frontend Agent: Retrieved API docs
```

---

## 5. The Orchestrator as Intelligent Mediator

### What Orchestrator Actually Does

```python
class ProjectOrchestrator:  # You have this!

    async def handle_user_message(self, message: str):
        """Process user message and route appropriately"""

        # Interpret intent
        if "all agents" in message.lower():
            return await self.broadcast_to_all_agents(message)

        # Smart routing
        if "backend" in message or "api" in message:
            return await self.route_to_agent("backend_dev", message)

        # Dependency management
        if "waiting for" in message:
            return await self.resolve_dependency_block(message)

        # Default: Ask orchestrator to handle
        return await self.synthesize_and_distribute(message)
```

### Orchestrator's Realistic Capabilities

1. **Message Interpretation**: Understands intent and routes
2. **Dependency Resolution**: Knows who's blocked on what
3. **Task Prioritization**: Can reorder agent work queues
4. **Status Synthesis**: Combines agent reports into summary
5. **Broadcast Management**: Efficiently distributes info

---

## 6. Practical Implementation Steps

### Phase 1: Core Infrastructure (1 week)
1. Create MCP tools for queue polling
2. Build WebSocket bridge to AgentCommunicationQueue
3. Set up orchestrator message handler

### Phase 2: Basic UI (1 week)
1. Mission view (readonly display)
2. Agent status cards (poll-based updates)
3. Orchestrator chat interface

### Phase 3: Integration (3-4 days)
1. Connect UI to existing JobCoordinator
2. Wire up WebSocket events
3. Test with real CLI agents

### Phase 4: Polish (3-4 days)
1. Add timeline view
2. Improve message formatting
3. Add metrics visualization

---

## 7. What This Gives Users

### Realistic Expectations
- **Not real-time** but "checkpoint-based" (every 5-10 min)
- **Not direct agent control** but orchestrator-mediated
- **Not micro-management** but milestone tracking
- **Not instant response** but queued instructions

### Actual Value
- **Visibility**: See what agents are working on
- **Influence**: Redirect effort via orchestrator
- **Coordination**: Orchestrator handles dependencies
- **Progress**: Track completion at milestone level
- **Intervention**: Queue priority messages

---

## 8. Example User Session

```
10:00 - User starts project, copies CLI command
10:01 - Pastes in Claude Code: "/orchestrate execute mission_123"
10:02 - UI shows: "Backend Agent checked in"
10:05 - UI shows: "Frontend Agent checked in"
10:15 - Backend card: "Milestone: Database schema complete"
10:20 - Frontend card: "Status: Waiting for API"
10:21 - User messages: "Orchestrator, tell backend to prioritize API"
10:22 - Orchestrator: "Message queued for Backend"
10:28 - Backend: "ACK - Switching to API development"
10:45 - Backend: "Milestone: API endpoints complete"
10:46 - Orchestrator: "Notified Frontend that API is ready"
10:50 - Frontend: "Proceeding with component development"
```

---

## 9. Technical Architecture

### Components That Exist (Backend)
- ✅ `AgentJobManager` - Manages job lifecycle
- ✅ `JobCoordinator` - Coordinates multiple agents
- ✅ `AgentCommunicationQueue` - Message queue system
- ✅ `ProjectOrchestrator` - High-level coordination

### Components to Build (Frontend)
- 🔨 `OrchestratorChat.vue` - User ↔ Orchestrator interface
- 🔨 `AgentStatusCard.vue` - Poll-based status display
- 🔨 `MissionView.vue` - Display generated mission
- 🔨 `TimelineView.vue` - Historical event log

### Components to Build (MCP Tools)
- 🔨 `check_orchestrator_queue` - Agents poll for messages
- 🔨 `report_milestone` - Agents report major progress
- 🔨 `request_clarification` - Agents ask for help

---

## 10. Why This Will Actually Work

1. **Uses existing infrastructure**: AgentCommunicationQueue is built
2. **Respects agent limitations**: CLI agents can't receive push messages
3. **Leverages orchestrator**: Already built to coordinate
4. **Realistic timing**: 5-10 minute update cycles match agent work patterns
5. **Clear value prop**: Visibility + influence without micromanagement

---

## Conclusion

This isn't a "dream" interface - it's what we can build with your existing backend and real CLI agent capabilities. The key insight: **The orchestrator is the bridge** between async CLI agents and user desires, using the message queue for coordination rather than trying to achieve impossible real-time control.