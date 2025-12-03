---
Handover 0073: Static Agent Grid with Enhanced Messaging
Date: 2025-10-30
Status: READY FOR IMPLEMENTATION
Priority: CRITICAL
Type: UI/UX Recalibration
Duration: 92-108 hours (5 weeks)
---

# Project 0073: Static Agent Grid with Enhanced Messaging

## Executive Summary

This project recalibrates the current Kanban board implementation into a static agent card grid with enhanced messaging capabilities, addressing critical gaps identified in Project 0067 while providing a superior user experience for multi-terminal AI orchestration.

**Key Transformation**: Replace 4-column Kanban with responsive agent grid + unified message center.

**Critical Problems Solved**:
- CODEX/GEMINI copy prompt buttons (P0 gap from 0067)
- Broadcast to ALL agents capability (P0 gap)
- Project closeout workflow (P0 gap)
- Message center location and visibility
- Terminal-based orchestration clarity

---

## Problem Statement

### Current Situation
The investigation in Project 0067 revealed that the implemented Kanban board deviates significantly from the original vision:

1. **Missing Multi-Tool Support**: No copy prompt buttons for CODEX/GEMINI terminals
2. **No Broadcast Messaging**: Can only message agents individually
3. **No Project Closeout**: Missing structured completion workflow
4. **Wrong Mental Model**: Kanban implies automated progression; reality is manual orchestration
5. **Message Isolation**: Messages in per-agent drawers, not unified view

### User's Actual Workflow
```
Developer → Opens multiple terminals (Claude/Codex/Gemini)
         → Copies specific prompts for each agent
         → Monitors all agents simultaneously
         → Sends broadcast instructions
         → Orchestrates manually via prompts
         → Closes project with git operations
```

The Kanban board doesn't support this workflow. A static grid with status badges does.

---

## Objectives

### Primary Objectives
1. **Enable Multi-Tool Orchestration**: Separate copy prompts for Claude/Codex/Gemini
2. **Unify Messaging**: Single chronological feed for all agents
3. **Simplify Status Tracking**: Status badges instead of column movement
4. **Implement Project Closeout**: Structured workflow for project completion
5. **Improve Responsiveness**: Dynamic grid layout for all screen sizes

### Success Criteria
- ✅ All agents visible simultaneously with clear status
- ✅ Copy prompts work for Claude Code, Codex, and Gemini
- ✅ Broadcast messages reach all agents
- ✅ Project closeout guides through git operations
- ✅ Mobile-friendly responsive layout

---

## User Experience Design

### Grid Layout Specification

#### Responsive Breakpoints
```
Desktop (≥1200px):  [Card][Card][Card][Card]
Tablet (768-1199px): [Card][Card][Card]
Mobile (600-767px):  [Card][Card]
Small (<600px):      [Card]
```

#### Card Dimensions
- Desktop: 280px × 360px fixed
- Tablet/Mobile: Fluid width, fixed height
- Spacing: 16px gap between cards
- No drag-and-drop (static positioning)

### Agent Status States (7 Total)

| Status | Color | Icon | Description | Progress | MCP Tool |
|--------|-------|------|-------------|----------|----------|
| **Waiting** | Grey | ⏳ | Ready to launch | Hidden | `set_agent_status --waiting` |
| **Preparing** | Light Blue | 🔄 | Loading context | Spinner | `set_agent_status --preparing` |
| **Working** | Primary Blue | ⚙️ | Executing tasks (testing for test agents) | 0-100% | `set_agent_status --working --progress=N` |
| **Review** | Purple | 👁️ | Under review | Hidden | `set_agent_status --review` |
| **Complete** | Green | ✅ | Mission done | Hidden | `set_agent_status --complete` |
| **Failed** | Red | ❌ | Error occurred | Error count | `set_agent_status --failed --reason="error"` |
| **Blocked** | Dark Red | 🚫 | Waiting for input | Reason text | `set_agent_status --blocked --reason="need X"`|

**Note**: "Working" status encompasses all active work including testing. Test agents show "Working" when running tests.

### Orchestrator Card (Special)

```
┌─────────────────────────────────┐
│ 🧠 ORCHESTRATOR                 │ ← Purple gradient header
│ Status: Context Management &     │ ← Always this status
│         Project Coordination     │
│                                  │
│ Mission Summary:                 │
│ Building e-commerce platform...  │ ← Truncated mission
│                                  │
│ ┌──────────────────────────────┐│
│ │ Copy Prompt (Claude Code) 📋 ││ ← Claude-specific
│ └──────────────────────────────┘│
│ ┌──────────────────────────────┐│
│ │ Copy Prompt (Codex/Gemini) 📋││ ← Universal prompt
│ └──────────────────────────────┘│
│                                  │
│ Messages: 0 unread               │
└─────────────────────────────────┘
```

### Standard Agent Card

```
┌─────────────────────────────────┐
│ Backend Agent         [Codex]   │ ← Name + Tool badge
│ ⚙️ Working           Progress: 47%│ ← Status + Progress
│                                  │
│ Job Description:                 │
│ Implementing REST API endpoints  │ ← Specific task
│ for user authentication...       │
│                                  │
│ Current: Adding validation       │ ← Current subtask
│ ▓▓▓▓▓▓▓░░░░░░░░ 47%             │ ← Progress bar
│                                  │
│ ┌──────────────────────────────┐│
│ │     Copy Prompt 📋            ││ ← Single button
│ └──────────────────────────────┘│
│                                  │
│ 💬 View Messages (3 unread)  ▼   │ ← Expands accordion
└─────────────────────────────────┘
```

### Message Center Design (MCP Messages)

#### Layout (Right Panel, 30% Width)
```
┌─────────────────────────────────┐
│ MCP MESSAGE CENTER               │ ← Clarified as MCP
│ ┌──────────────────────────────┐│
│ │Filter: All ▼  Type: All ▼    ││ ← Filters
│ │Search: _____________ 🔍       ││
│ └──────────────────────────────┘│
├─────────────────────────────────┤
│                                  │
│ ┌──────────────────────────────┐│
│ │🤖 Backend Agent    10:32 AM   ││ ← Agent MCP message
│ │[MCP] Starting API             ││ ← MCP prefix
│ │implementation for auth        ││
│ │                 📢 BROADCAST  ││ ← Broadcast badge
│ └──────────────────────────────┘│
│                                  │
│         ┌─────────────────────┐ │
│         │ Developer  10:35 AM │ ││ ← Dev MCP message
│         │ [MCP] Please add    │ ││
│         │ input validation   ✓✓│ ││ ← Read receipt
│         └─────────────────────┘ │
│                                  │
│ ┌──────────────────────────────┐│
│ │🤖 Testing Agent    10:36 AM   ││
│ │Tests ready to run when API   ││
│ │implementation is complete     ││
│ └──────────────────────────────┘│
│                                  │
├─────────────────────────────────┤
│ Send to: ● Specific ○ Broadcast ││ ← Send mode
│ ┌──────────────────────────────┐│
│ │Select agent... ▼              ││ ← Agent selector
│ └──────────────────────────────┘│
│ ┌──────────────────────────────┐│
│ │Type message...                ││ ← Message input
│ │                                ││
│ └──────────────────────────────┘│
│ [         Send Message          ]│ ← Send button
└─────────────────────────────────┘
```

### Accordion Message Expansion

When "View Messages" clicked on agent card:

```
┌─────────────────────────────────┐
│ Backend Agent         [X] Close │ ← Expanded to 600px
│ ⚙️ Working           Progress: 47%│
│                                  │
│ Job Description:                 │
│ Implementing REST API endpoints  │
│                                  │
├─────────────────────────────────┤
│ MESSAGES (Last 10)               │ ← Message section
│                                  │
│ Developer: Add validation   3m   │
│   Backend: Starting now     2m   │
│ Developer: Include tests    1m   │
│   Backend: Will do          30s  │
│                                  │
│ [View All in Message Center →]  │
│                                  │
│ Quick Reply:                     │
│ [Type message...         ] [Send]│
└─────────────────────────────────┘
```

### Project Closeout Flow

#### Trigger: All Agents Complete
```
┌─────────────────────────────────┐
│ 🧠 ORCHESTRATOR                 │
│ Status: Ready for Closeout ✓    │ ← Status change
│                                  │
│ All agents have completed their  │
│ missions. You may continue work  │
│ or close the project.           │
│                                  │
│ To continue: Chat with the       │
│ orchestrator in its terminal     │
│                                  │
│ ┌──────────────────────────────┐│
│ │    🏁 Close Project          ││ ← New button appears
│ └──────────────────────────────┘│
└─────────────────────────────────┘
```

#### Closeout Modal
```
┌─────────────────────────────────────┐
│ Project Closeout                     │
├─────────────────────────────────────┤
│ Complete these steps to close:       │
│                                       │
│ ☐ Review all agent work              │
│ ☐ Run final tests                    │
│ ☐ Commit all changes                 │
│ ☐ Push to remote repository          │
│ ☐ Update documentation               │
│ ☐ Close agent terminals              │
│                                       │
│ Copy this closeout prompt:           │
│ ┌───────────────────────────────────┐│
│ │# Project closeout commands       ││
│ │git add .                          ││
│ │git commit -m "Project complete"  ││
│ │git push origin main               ││
│ │orchestrator document-project     ││
│ │orchestrator close-agents         ││
│ └───────────────────────────────┘   │
│                                       │
│ [Copy Closeout Prompt]               │
│                                       │
│ ☐ I have executed the closeout      │
│                                       │
│ [Cancel]    [Complete Project]       │
└─────────────────────────────────────┘
```

---

## MCP Tool Specifications for Status Management

### New MCP Tools Required

```python
# src/giljo_mcp/tools/agent_status.py

class SetAgentStatusTool(MCPTool):
    """MCP tool for agents to update their own status."""

    name = "set_agent_status"
    description = "Update agent status in the orchestration grid"

    async def execute(
        self,
        status: Literal["waiting", "preparing", "working", "review", "complete", "failed", "blocked"],
        progress: Optional[int] = None,
        reason: Optional[str] = None,
        current_task: Optional[str] = None
    ) -> dict:
        """
        Update agent status via MCP.

        Args:
            status: New status to set
            progress: Progress percentage (0-100) for working status
            reason: Reason for failure or block
            current_task: Description of current task (for working status)
        """
        # Implementation to update database and broadcast via WebSocket

class SendMCPMessageTool(MCPTool):
    """MCP tool for sending messages to orchestrator or other agents."""

    name = "send_mcp_message"
    description = "Send MCP message to orchestrator or broadcast"

    async def execute(
        self,
        content: str,
        target: Literal["orchestrator", "broadcast", "agent"],
        agent_id: Optional[str] = None
    ) -> dict:
        """
        Send MCP message through the message center.

        Args:
            content: Message content
            target: Send to orchestrator, broadcast to all, or specific agent
            agent_id: Target agent ID (if target="agent")
        """
        # Implementation to add message to queue

class ReadMCPMessagesTool(MCPTool):
    """MCP tool for agents to read their messages."""

    name = "read_mcp_messages"
    description = "Read MCP messages from the message queue"

    async def execute(
        self,
        unread_only: bool = True,
        limit: int = 10
    ) -> List[dict]:
        """
        Read MCP messages for current agent.

        Args:
            unread_only: Only return unread messages
            limit: Maximum number of messages to return
        """
        # Implementation to fetch messages from queue
```

### MCP Tool Usage Examples

```bash
# Agent setting status when starting work
mcp set_agent_status --status=preparing

# Agent updating progress
mcp set_agent_status --status=working --progress=45 --current_task="Implementing user authentication"

# Agent marking complete
mcp set_agent_status --status=complete

# Agent reporting failure
mcp set_agent_status --status=failed --reason="Database connection timeout"

# Agent sending message to orchestrator
mcp send_mcp_message --target=orchestrator --content="Need clarification on API structure"

# Agent broadcasting to all
mcp send_mcp_message --target=broadcast --content="Authentication module ready for integration"

# Agent reading messages
mcp read_mcp_messages --unread_only
```

---

## Technical Architecture

### Component Structure

```
OrchestrationView.vue (NEW - Main Container)
├── AgentCardGrid.vue (NEW - Replaces KanbanJobsView)
│   ├── OrchestratorCard.vue (NEW - Special orchestrator card)
│   └── AgentCard.vue (NEW - Standard agent cards)
│       └── MessageAccordion.vue (NEW - Expandable messages)
│
├── MessageCenterPanel.vue (NEW - Replaces MessageThreadPanel)
│   ├── MessageFilter.vue (NEW - Filter controls)
│   ├── MessageFeed.vue (NEW - Chronological feed)
│   └── MessageCompose.vue (NEW - Send interface)
│
├── ProjectSummaryPanel.vue (NEW - Bottom panel)
└── CloseoutModal.vue (NEW - Closeout workflow)
```

### Data Flow

```
User Action → Component → Pinia Store → API Call → WebSocket Update
                                      ↓
                            Database Update → Broadcast to All Clients
```

### State Management (Pinia)

```javascript
// stores/orchestration.js
export const useOrchestrationStore = defineStore('orchestration', {
  state: () => ({
    agents: [],
    messages: [],
    expandedAgentId: null,
    messageFilters: {
      agentIds: [],
      messageType: 'all',
      dateRange: null
    },
    projectSummary: null,
    canCloseProject: false
  }),

  getters: {
    filteredMessages: (state) => {
      // Apply filters to messages
    },
    agentsByStatus: (state) => {
      // Group agents by status for display
    },
    orchestrator: (state) => {
      // Get orchestrator from agents
    }
  },

  actions: {
    async broadcastMessage(content) {
      // Send to all agents
    },
    async generatePrompt(agentId, tool) {
      // Generate copy prompt
    },
    async initiateCloseout() {
      // Start closeout workflow
    }
  }
})
```

---

## Backend Implementation

### Database Schema Updates

```sql
-- Migration: 0073_01_expand_agent_statuses.sql

-- Drop old constraint
ALTER TABLE mcp_agent_jobs
DROP CONSTRAINT IF EXISTS ck_mcp_agent_job_status;

-- Add new constraint with 7 states (testing removed - working encompasses all active tasks)
ALTER TABLE mcp_agent_jobs
ADD CONSTRAINT ck_mcp_agent_job_status
CHECK (status IN (
  'waiting', 'preparing', 'working',
  'review', 'complete', 'failed', 'blocked'
));

-- Add progress tracking
ALTER TABLE mcp_agent_jobs
ADD COLUMN progress INTEGER DEFAULT 0
CHECK (progress >= 0 AND progress <= 100);

-- Add block reason
ALTER TABLE mcp_agent_jobs
ADD COLUMN block_reason TEXT;

-- Add current task description
ALTER TABLE mcp_agent_jobs
ADD COLUMN current_task TEXT;

-- Add estimated completion
ALTER TABLE mcp_agent_jobs
ADD COLUMN estimated_completion TIMESTAMP WITH TIME ZONE;
```

```sql
-- Migration: 0073_02_project_closeout.sql

ALTER TABLE projects
ADD COLUMN orchestrator_summary TEXT;

ALTER TABLE projects
ADD COLUMN closeout_prompt TEXT;

ALTER TABLE projects
ADD COLUMN closeout_executed_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE projects
ADD COLUMN closeout_checklist JSONB DEFAULT '[]'::jsonb;
```

### API Endpoints

#### Prompt Generation
```python
# api/endpoints/prompts.py

@router.get("/api/prompts/orchestrator/{tool}")
async def get_orchestrator_prompt(
    tool: Literal["claude-code", "codex-gemini"],
    project_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """Generate orchestrator prompt for specified tool."""

    project = await get_project(db, project_id, current_user.tenant_id)

    if tool == "claude-code":
        prompt = f"""
cd {project.path}
claude-code orchestrate \\
  --project-id={project.id} \\
  --mission="{project.mission_summary}" \\
  --agents={len(project.agents)}
"""
    else:  # codex-gemini
        prompt = f"""
cd {project.path}
export PROJECT_ID={project.id}
export MISSION="{project.mission_summary}"
export AGENTS={len(project.agents)}

# For Codex:
# codex orchestrate

# For Gemini:
# gemini orchestrate
"""

    return {
        "prompt": prompt,
        "tool": tool,
        "instructions": "Copy this prompt to your terminal"
    }

@router.get("/api/prompts/agent/{agent_id}")
async def get_agent_prompt(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """Generate universal agent prompt."""

    agent = await get_agent_job(db, agent_id, current_user.tenant_id)

    prompt = f"""
# Agent: {agent.name}
# Type: {agent.type}
# Mission: {agent.mission}

cd {agent.project.path}
export AGENT_ID={agent.id}
export AGENT_TYPE={agent.type}
export PROJECT_ID={agent.project_id}

# Execute agent mission
{agent.type.lower()}-agent execute --mission-file=.missions/{agent.id}.md
"""

    return {
        "prompt": prompt,
        "agent_name": agent.name,
        "instructions": "Copy to any terminal (Claude/Codex/Gemini)"
    }
```

#### Broadcast Messaging
```python
# api/endpoints/agent_jobs.py (ADD)

@router.post("/api/agent-jobs/broadcast")
async def broadcast_message(
    request: BroadcastMessageRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
) -> BroadcastMessageResponse:
    """Send message to ALL agents in project."""

    # Get all agents in project
    agents = await db.execute(
        select(MCPAgentJob)
        .filter(
            MCPAgentJob.project_id == request.project_id,
            MCPAgentJob.tenant_id == current_user.tenant_id
        )
    )

    broadcast_id = str(uuid.uuid4())
    message_ids = []

    for agent in agents:
        # Add message to each agent's queue
        message = {
            "id": str(uuid.uuid4()),
            "broadcast_id": broadcast_id,
            "content": request.content,
            "from": "developer",
            "to": agent.id,
            "timestamp": datetime.utcnow().isoformat(),
            "is_broadcast": True
        }

        # Update agent's message array
        agent.messages = agent.messages or []
        agent.messages.append(message)
        message_ids.append(message["id"])

    await db.commit()

    # WebSocket broadcast
    await websocket_service.broadcast_event(
        "message:broadcast",
        {
            "broadcast_id": broadcast_id,
            "project_id": request.project_id,
            "content": request.content,
            "job_ids": [a.id for a in agents],
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    return BroadcastMessageResponse(
        broadcast_id=broadcast_id,
        message_ids=message_ids,
        agent_count=len(agents)
    )
```

#### Project Closeout
```python
# api/endpoints/projects.py (ADD)

@router.get("/api/projects/{project_id}/can-close")
async def check_can_close(
    project_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """Check if all agents complete and project can close."""

    agents = await db.execute(
        select(MCPAgentJob)
        .filter(
            MCPAgentJob.project_id == project_id,
            MCPAgentJob.tenant_id == current_user.tenant_id
        )
    )

    statuses = [agent.status for agent in agents]
    can_close = all(status in ['complete', 'failed'] for status in statuses)

    if can_close:
        # Generate orchestrator summary
        summary = await generate_project_summary(project_id, db)

        # Store summary
        project.orchestrator_summary = summary
        await db.commit()

    return {
        "can_close": can_close,
        "summary": summary if can_close else None,
        "agent_statuses": {
            "complete": statuses.count('complete'),
            "failed": statuses.count('failed'),
            "active": len(statuses) - statuses.count('complete') - statuses.count('failed')
        }
    }

@router.post("/api/projects/{project_id}/generate-closeout")
async def generate_closeout_prompt(
    project_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """Generate closeout prompt for orchestrator."""

    project = await get_project(db, project_id, current_user.tenant_id)

    closeout_prompt = f"""
#!/bin/bash
# Project Closeout: {project.name}
# Generated: {datetime.now().isoformat()}

cd {project.path}

# 1. Check final status
git status

# 2. Stage all changes
git add .

# 3. Commit with summary
git commit -m "Project complete: {project.name}

{project.orchestrator_summary}

Agents completed: {len([a for a in project.agents if a.status == 'complete'])}
Total duration: {project.duration}
"

# 4. Push to remote
git push origin {project.branch or 'main'}

# 5. Generate documentation
echo "{project.orchestrator_summary}" > PROJECT_SUMMARY.md

# 6. Close all agent terminals
orchestrator close-agents --project-id={project.id}

# 7. Mark project complete
orchestrator complete-project --project-id={project.id}

echo "Project closeout complete!"
"""

    # Store the closeout prompt
    project.closeout_prompt = closeout_prompt
    await db.commit()

    return {
        "prompt": closeout_prompt,
        "checklist": [
            "Review all agent work",
            "Run final tests",
            "Commit all changes",
            "Push to remote repository",
            "Update documentation",
            "Close agent terminals"
        ]
    }

@router.post("/api/projects/{project_id}/complete")
async def complete_project(
    project_id: str,
    request: CompleteProjectRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """Mark project as completed and retire agents."""

    if not request.confirm_closeout:
        raise HTTPException(400, "Must confirm closeout execution")

    project = await get_project(db, project_id, current_user.tenant_id)

    # Mark project as completed
    project.status = 'completed'
    project.closeout_executed_at = datetime.utcnow()

    # Retire all agents
    agents = await db.execute(
        select(MCPAgentJob)
        .filter(
            MCPAgentJob.project_id == project_id,
            MCPAgentJob.tenant_id == current_user.tenant_id
        )
    )

    for agent in agents:
        agent.retired_at = datetime.utcnow()

    await db.commit()

    # WebSocket notification
    await websocket_service.broadcast_event(
        "project:completed",
        {
            "project_id": project_id,
            "completed_at": project.closeout_executed_at.isoformat(),
            "agent_count": len(agents)
        }
    )

    return {
        "success": True,
        "completed_at": project.closeout_executed_at.isoformat(),
        "retired_agents": len(agents)
    }
```

### WebSocket Events

```python
# api/websocket_events.py

# New event types
BROADCAST_MESSAGE = "message:broadcast"
PROJECT_CLOSEOUT_READY = "project:closeout_ready"
PROJECT_COMPLETED = "project:completed"
AGENT_STATUS_CHANGED = "agent:status_changed"

# Event payloads
BroadcastMessageEvent = {
    "event": BROADCAST_MESSAGE,
    "data": {
        "broadcast_id": str,
        "project_id": str,
        "content": str,
        "from": str,
        "timestamp": str,
        "job_ids": List[str]
    }
}

ProjectCloseoutReadyEvent = {
    "event": PROJECT_CLOSEOUT_READY,
    "data": {
        "project_id": str,
        "summary": str,
        "can_close": bool,
        "agent_statuses": dict
    }
}

AgentStatusChangedEvent = {
    "event": AGENT_STATUS_CHANGED,
    "data": {
        "job_id": str,
        "old_status": str,
        "new_status": str,
        "progress": Optional[int],
        "current_task": Optional[str]
    }
}
```

---

## Frontend Implementation

### Vue Components

#### AgentCardGrid.vue
```vue
<template>
  <div class="agent-grid-container">
    <!-- Orchestrator Card (always first) -->
    <orchestrator-card
      v-if="orchestrator"
      :orchestrator="orchestrator"
      :project="project"
      :unread-count="getUnreadCount(orchestrator.id)"
      @copy-prompt="handleCopyPrompt"
      @expand-messages="expandAgent(orchestrator.id)"
      @close-project="initiateCloseout"
    />

    <!-- Agent Cards Grid -->
    <div class="agent-grid">
      <agent-card
        v-for="agent in sortedAgents"
        :key="agent.id"
        :agent="agent"
        :is-expanded="expandedAgentId === agent.id"
        :unread-count="getUnreadCount(agent.id)"
        @copy-prompt="handleCopyPrompt"
        @toggle-messages="toggleAgentMessages(agent.id)"
        @send-quick-reply="sendQuickReply"
      />
    </div>

    <!-- Project Summary Panel (bottom) -->
    <project-summary-panel
      v-if="showSummaryPanel"
      :project="project"
      :agents="agents"
      :summary="projectSummary"
      @close-project="initiateCloseout"
    />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useOrchestrationStore } from '@/stores/orchestration'

const store = useOrchestrationStore()

const expandedAgentId = ref(null)

const sortedAgents = computed(() => {
  // Sort by status priority
  const statusOrder = {
    'failed': 0,
    'blocked': 1,
    'working': 2,
    'testing': 3,
    'review': 4,
    'preparing': 5,
    'waiting': 6,
    'complete': 7
  }

  return [...store.agents]
    .filter(a => !a.is_orchestrator)
    .sort((a, b) => statusOrder[a.status] - statusOrder[b.status])
})

const orchestrator = computed(() =>
  store.agents.find(a => a.is_orchestrator)
)

const toggleAgentMessages = (agentId) => {
  expandedAgentId.value =
    expandedAgentId.value === agentId ? null : agentId
}
</script>

<style scoped>
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  padding: 16px;
}

/* Responsive breakpoints */
@media (max-width: 600px) {
  .agent-grid {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 601px) and (max-width: 767px) {
  .agent-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 768px) and (max-width: 1199px) {
  .agent-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 1200px) {
  .agent-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
</style>
```

#### AgentCard.vue
```vue
<template>
  <v-card
    class="agent-card"
    :class="{
      'expanded': isExpanded,
      'status-' + agent.status
    }"
    :elevation="2"
  >
    <!-- Header -->
    <v-card-title class="d-flex justify-space-between">
      <div class="agent-name">
        {{ agent.name }}
      </div>
      <v-chip
        size="small"
        :color="getToolColor(agent.tool_type)"
      >
        {{ agent.tool_type || 'Universal' }}
      </v-chip>
    </v-card-title>

    <!-- Status Badge -->
    <div class="status-section">
      <v-chip
        :color="getStatusColor(agent.status)"
        :prepend-icon="getStatusIcon(agent.status)"
      >
        {{ getStatusLabel(agent.status) }}
      </v-chip>

      <!-- Progress (if working/testing) -->
      <v-progress-linear
        v-if="showProgress"
        :model-value="agent.progress || 0"
        :color="getStatusColor(agent.status)"
        height="20"
        class="mt-2"
      >
        {{ agent.progress }}%
      </v-progress-linear>
    </div>

    <!-- Job Description -->
    <v-card-text>
      <div class="job-description">
        <strong>Job:</strong> {{ agent.job_description }}
      </div>

      <div v-if="agent.current_task" class="current-task">
        <strong>Current:</strong> {{ agent.current_task }}
      </div>

      <div v-if="agent.block_reason" class="block-reason">
        <v-alert type="warning" density="compact">
          Blocked: {{ agent.block_reason }}
        </v-alert>
      </div>
    </v-card-text>

    <!-- Actions -->
    <v-card-actions>
      <v-btn
        variant="outlined"
        color="primary"
        @click="$emit('copy-prompt', agent.id)"
      >
        <v-icon left>mdi-content-copy</v-icon>
        Copy Prompt
      </v-btn>
    </v-card-actions>

    <!-- Message Section -->
    <div class="message-section">
      <v-btn
        variant="text"
        @click="$emit('toggle-messages')"
        class="message-toggle"
      >
        <v-icon left>mdi-message</v-icon>
        View Messages
        <v-badge
          v-if="unreadCount > 0"
          :content="unreadCount"
          color="error"
          inline
        />
        <v-icon right>
          {{ isExpanded ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
        </v-icon>
      </v-btn>

      <!-- Expanded Messages (Accordion) -->
      <v-expand-transition>
        <div v-if="isExpanded" class="expanded-messages">
          <message-accordion
            :agent-id="agent.id"
            :messages="agentMessages"
            @send-reply="sendQuickReply"
            @view-all="viewInMessageCenter"
          />
        </div>
      </v-expand-transition>
    </div>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  agent: Object,
  isExpanded: Boolean,
  unreadCount: Number
})

const emit = defineEmits([
  'copy-prompt',
  'toggle-messages',
  'send-quick-reply'
])

const showProgress = computed(() =>
  ['working', 'testing'].includes(props.agent.status)
)

const getStatusColor = (status) => {
  const colors = {
    'waiting': 'grey',
    'preparing': 'light-blue',
    'working': 'primary',
    'testing': 'orange',
    'review': 'purple',
    'complete': 'success',
    'failed': 'error',
    'blocked': 'deep-orange-darken-4'
  }
  return colors[status] || 'grey'
}

const getStatusIcon = (status) => {
  const icons = {
    'waiting': 'mdi-clock-outline',
    'preparing': 'mdi-loading',
    'working': 'mdi-cog',
    'testing': 'mdi-test-tube',
    'review': 'mdi-eye',
    'complete': 'mdi-check-circle',
    'failed': 'mdi-alert-circle',
    'blocked': 'mdi-block-helper'
  }
  return icons[status] || 'mdi-help-circle'
}
</script>

<style scoped>
.agent-card {
  width: 280px;
  min-height: 360px;
  transition: all 0.3s ease;
  border-left: 8px solid;
}

.agent-card.expanded {
  min-height: 600px;
}

/* Status-based border colors */
.agent-card.status-waiting { border-left-color: #9e9e9e; }
.agent-card.status-preparing { border-left-color: #03a9f4; }
.agent-card.status-working { border-left-color: #2196f3; }
.agent-card.status-testing { border-left-color: #ff9800; }
.agent-card.status-review { border-left-color: #9c27b0; }
.agent-card.status-complete { border-left-color: #4caf50; }
.agent-card.status-failed { border-left-color: #f44336; }
.agent-card.status-blocked { border-left-color: #bf360c; }
</style>
```

---

## Migration Strategy

### Phase 1: Parallel Development (Week 1-3)
- Build new components alongside existing Kanban
- Use feature flag: `ENABLE_AGENT_GRID`
- Test with select tenants

### Phase 2: Staged Rollout (Week 4)
- Enable for 10% of tenants
- Monitor performance and feedback
- Fix identified issues

### Phase 3: Full Migration (Week 5)
- Enable for all tenants
- Deprecate Kanban components
- Update documentation

### Data Migration
```python
# Status mapping
STATUS_MAP = {
    'pending': 'waiting',
    'active': 'working',
    'completed': 'complete',
    # Others remain the same
}

# Run migration
UPDATE mcp_agent_jobs
SET status = CASE
    WHEN status = 'pending' THEN 'waiting'
    WHEN status = 'active' THEN 'working'
    WHEN status = 'completed' THEN 'complete'
    ELSE status
END;
```

---

## Testing Strategy

### Unit Tests
- Test all 8 status states rendering
- Test responsive grid breakpoints
- Test message filtering
- Test accordion expansion
- Test prompt generation

### Integration Tests
- Test full orchestration workflow
- Test broadcast messaging
- Test project closeout
- Test WebSocket updates

### E2E Tests
```javascript
// Launch project → Copy prompts → Send messages → Close project
describe('Orchestration Workflow', () => {
  it('completes full project lifecycle', async () => {
    // 1. Launch project
    await launchProject()

    // 2. Verify agent grid appears
    expect(await page.$$('.agent-card')).toHaveLength(7) // 6 agents + orchestrator

    // 3. Copy orchestrator prompts
    await copyOrchestratorPrompts()

    // 4. Send broadcast message
    await broadcastToAllAgents('Start implementation')

    // 5. Complete all agents
    await completeAllAgents()

    // 6. Execute closeout
    await executeProjectCloseout()

    // 7. Verify project completed
    expect(await getProjectStatus()).toBe('completed')
  })
})
```

### Performance Metrics
- Grid render: <100ms for 7 cards
- Message feed: 60fps scrolling
- WebSocket latency: <50ms
- Memory usage: <100MB

---

## Risk Mitigation

| Risk | Mitigation | Fallback |
|------|------------|----------|
| Users expect Kanban | Onboarding tooltip, documentation | Add "Classic View" toggle |
| Message overwhelm | Strong filtering, search | Per-agent thread option |
| State complexity | Pinia store, clear ownership | Simplify to single expanded |
| Performance issues | Virtual scroll, pagination | Disable real-time updates |

---

## Success Criteria

### Functional
- ✅ All 6 gaps from 0067 addressed
- ✅ Multi-tool prompts working
- ✅ Broadcast messaging functional
- ✅ Project closeout complete
- ✅ Responsive on all devices

### Performance
- ✅ Lighthouse score >90
- ✅ 60fps animations
- ✅ <3s initial load

### Quality
- ✅ 85%+ test coverage
- ✅ WCAG 2.1 AA compliant
- ✅ Zero critical bugs

---

## Timeline

```
Week 1: Backend Foundation (24-28h)
  - Database migrations
  - Prompt generation
  - Broadcast endpoint
  - Closeout service

Week 2: Frontend Core (16-18h)
  - AgentCard components
  - Grid layout
  - Status system

Week 3: Integration (16-18h)
  - Message center
  - WebSocket events
  - State management

Week 4: Testing & Polish (20-24h)
  - Unit tests
  - Integration tests
  - UI polish
  - Beta rollout

Week 5: Migration & Launch (16-20h)
  - Data migration
  - Full rollout
  - Documentation
  - Cleanup
```

**Total: 92-108 hours**

---

## Conclusion

Project 0073 transforms the Kanban implementation into a superior agent grid system that:

1. **Solves all P0 gaps** from investigation 0067
2. **Matches user mental model** of terminal-based orchestration
3. **Simplifies implementation** by removing column complexity
4. **Improves mobile UX** with responsive grid
5. **Enables multi-tool workflows** with proper prompt support

The implementation is technically simpler than the current Kanban while providing better functionality and user experience.

**Recommendation**: PROCEED with implementation following the 5-week timeline.

---

**End of Handover 0073**