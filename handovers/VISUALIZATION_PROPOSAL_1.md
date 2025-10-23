# Visualization Proposal 1: Three-Phase Project Execution Interface

**Document Type**: UI/UX Proposal
**Created**: 2025-10-22
**Status**: PROPOSED
**Priority**: HIGH - Core user interaction model

---

## Executive Summary

A three-phase project execution interface that guides users from mission planning through active execution to completion, with real-time agent monitoring and inter-agent communication visibility.

---

## 1. Three-Phase Workflow

### Phase 1: Mission Planning View
**Triggered by**: Project activation
**Purpose**: Review and approve the orchestrator's mission plan before execution

**User Experience**:
1. Orchestrator automatically generates mission from project vision
2. User reviews mission summary (with option to see full details)
3. User reviews selected agents and their assigned jobs
4. User can optionally edit mission or agent assignments
5. User clicks "Accept & Start" to get CLI command
6. User copies command and pastes in coding agent CLI

**Interface Elements**:
- Mission display panel (collapsible for full/summary view)
- Agent selection grid showing planned agents
- Edit buttons for mission and agent modifications
- Prominent "Copy CLI Command" button with one-click copy

---

### Phase 2: Active Execution View
**Triggered by**: User executing CLI command
**Purpose**: Monitor agent progress, see inter-agent communication, intervene if needed

**User Experience**:
1. Interface automatically transitions to execution view
2. Agent cards appear as agents spawn
3. Cards dynamically reorder based on status
4. User watches real-time progress
5. User can message agents if intervention needed
6. User sees agent-to-agent communication

**Interface Layout**:
```
┌─────────────────────────────────────────────────────────┐
│ Project: [Name]  Status: EXECUTING  Mission: [Summary] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Agent Cards (70%)              │  Group Chat (30%)    │
│                                 │                      │
│  ┌──────────┐ ┌──────────┐    │  [Backend]: Ready    │
│  │ Agent 1  │ │ Agent 2  │    │  [Frontend]: ACK     │
│  └──────────┘ └──────────┘    │  [You]: Focus auth   │
│                                │                      │
│  ┌──────────┐ ┌──────────┐    │  ┌─────────────┐    │
│  │ Agent 3  │ │ Agent 4  │    │  │ Message...  │    │
│  └──────────┘ └──────────┘    │  └─────────────┘    │
│                                │  Send to: [All ▼]   │
└─────────────────────────────────────────────────────────┘
```

**Agent Card Dynamic Sorting**:
- **Top**: Agents needing user input (red indicator)
- **Middle**: Active agents (sorted by most recent update)
- **Bottom**: Paused or completed agents

---

### Phase 3: Project Summary View
**Triggered by**: All agents complete their missions
**Purpose**: Review what was accomplished

**User Experience**:
1. Automatic transition when all agents finish
2. Mission completion summary
3. List of accomplished tasks
4. Agent performance metrics
5. Option to download report

---

## 2. Agent Card Detailed Design

### Visual Structure
```
┌───────────────────────────────────┐
│ [🟢] Frontend Developer           │  <- Status indicator (pulsing when active)
├───────────────────────────────────┤
│ Messages: [📬 12] [✓ 10] [● 2]   │  <- Total/Read/Unread
├───────────────────────────────────┤
│ Current: Building components      │  <- Current task
│ Progress: [3/5] ██████░░░░ 60%   │  <- Todo progress
├───────────────────────────────────┤
│ ✓ Environment setup              │
│ ✓ Install dependencies           │  <- Completed tasks
│ ✓ Create base components         │
│ ➤ Building user dashboard        │  <- Current task (highlighted)
│ ○ Write unit tests               │  <- Pending tasks
└───────────────────────────────────┘
```

### Status Indicators
- 🟢 **Green pulsing**: Actively working
- 🟡 **Yellow static**: Waiting for response
- 🔴 **Red pulsing**: Needs user input
- ⏸️ **Gray**: Paused
- ✅ **Green check**: Completed

### Message Indicators (Inside Card)
- 📬 Total messages received
- ✓ Messages read/processed
- ● Unread messages (highlighted if > 0)

---

## 3. Group Chat Panel Design

### Features
- Real-time message display
- Agent-to-agent communication visible
- User can message all agents or specific ones
- Orchestrator as message relay
- Color-coded by sender

### Message Format
```
┌─────────────────────────┐
│ Backend Agent  10:32 AM │
│ Database schema ready   │
│ for review             │
└─────────────────────────┘

┌─────────────────────────┐
│ Frontend Agent 10:33 AM │
│ Acknowledged, updating  │
│ API interfaces         │
└─────────────────────────┘

          ┌─────────────────────────┐
          │ You           10:34 AM │
          │ Please prioritize auth  │
          │ module first           │
          └─────────────────────────┘
```

---

## 4. Technical Implementation

### Required WebSocket Events

```javascript
// Mission planning events
'mission:generated'        // Mission ready for review
'mission:edited'           // User modified mission
'agents:selected'          // Agents chosen for mission

// Execution events
'agent:spawned'           // New agent created
'agent:task_update'       // Agent moved to new todo item
'agent:status_change'     // Working/paused/needs_input
'agent:progress'          // Todo list progress update
'agent:message_sent'      // Inter-agent communication
'agent:message_received'  // Message delivered to agent
'agent:completed'         // Agent finished all tasks

// Project events
'project:phase_change'    // Planning→Executing→Complete
'project:completed'       // All agents done
```

### State Management Structure

```javascript
{
  project: {
    id: 'uuid',
    name: 'Project Name',
    phase: 'planning|executing|complete',
    mission: 'Mission text...',
    missionDetails: 'Full mission...' // Optional expanded view
  },

  agents: [
    {
      id: 'agent_1',
      type: 'Frontend Developer',
      status: 'active|paused|needs_input|complete',
      currentTask: 'Building components',
      todoList: [
        { task: 'Setup env', status: 'complete' },
        { task: 'Build components', status: 'active' },
        { task: 'Write tests', status: 'pending' }
      ],
      messages: {
        total: 12,
        read: 10,
        unread: 2
      },
      lastUpdate: '2025-10-22T10:30:00Z'
    }
  ],

  messages: [
    {
      id: 'msg_1',
      sender: 'Backend Agent',
      content: 'Database ready',
      timestamp: '2025-10-22T10:32:00Z',
      recipients: ['all']
    }
  ],

  cliCommand: {
    phase1: '/orchestrate start-mission project_id',
    copied: false
  }
}
```

### Vue Components to Build

```
frontend/src/components/project-execution/
├── ProjectExecutionView.vue          # Main container
├── MissionPlanningPanel.vue          # Phase 1
├── AgentExecutionGrid.vue            # Phase 2 left side
├── AgentExecutionCard.vue            # Individual agent card
├── GroupChatPanel.vue                # Phase 2 right side
├── ProjectSummaryView.vue            # Phase 3
└── services/
    ├── agentWebSocket.js             # WebSocket management
    └── projectExecutionStore.js      # Vuex/Pinia store
```

---

## 5. User Interaction Flows

### Starting a Project
1. User activates project from project list
2. System shows "Generating mission..." spinner
3. Mission planning view appears
4. User reviews and clicks "Accept & Start"
5. Copy button shows "Copied!" confirmation
6. User pastes in CLI and executes

### During Execution
1. Agent cards appear as they spawn
2. Cards auto-sort by priority (needs input → active → complete)
3. User can click any agent card for details
4. User can type message and select recipients
5. Messages appear in real-time in chat panel

### Handling Agent Issues
1. Agent card turns red and moves to top
2. User sees "Needs Input" indicator
3. User can message the specific agent
4. Agent acknowledges and continues

---

## 6. Responsive Design Considerations

### Desktop (>1200px)
- Full layout as shown
- Agent cards 2 per row
- Chat panel on right

### Tablet (768-1200px)
- Agent cards stack to 1 per row
- Chat panel becomes collapsible drawer

### Mobile (<768px)
- Tab interface: Agents | Chat
- Single column layout
- Swipe between tabs

---

## 7. Naming Conventions

### Interface Names (Options)
- **Mission Control** (recommended - clear purpose)
- Project Command Center
- Execution Dashboard
- Agent Orchestra

### Phase Names
- **Planning** → **Executing** → **Complete**
- Mission Setup → Active Work → Summary

### Button Labels
- Phase 1: "Accept Mission & Start"
- Phase 2: "Mission in Progress" (status)
- Phase 3: "View Full Report"

---

## 8. Future Enhancements (Not in V1)

- Token usage tracking per agent
- Cost estimation before execution
- Agent performance analytics
- Mission templates library
- Pause/resume mission capability
- Agent skill matching optimization

---

## 9. Success Metrics

1. **User Understanding**: Users know what agents are doing at all times
2. **Intervention Capability**: Users can message agents within 2 clicks
3. **Progress Visibility**: Todo completion visible without clicking into cards
4. **Communication Clarity**: All agent messages visible in single panel
5. **Workflow Efficiency**: 3 clicks from project activation to execution

---

## 10. Next Steps

1. Review and approve this proposal
2. Create mockups/wireframes
3. Build component shells
4. Implement WebSocket infrastructure
5. Connect to backend agent job system
6. User testing and iteration