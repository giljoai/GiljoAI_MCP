# Handover 0077: Launch/Jobs Dual-Tab Interface with Agent Visual Branding

**Status**: Specification (ARCHIVED)
**Date**: 2025-10-30
**Author**: System Architecture
**Priority**: High
**Scope**: Frontend UI redesign for Projects navigation

---

## Executive Summary

Complete redesign of the Projects navigation left-hand pane with a **dual-tab interface** for the project lifecycle:
1. **Launch Tab** - Project staging: Orchestrator builds mission, creates agents, user reviews before launch
2. **Jobs Tab** - Implementation: Active agent work with real-time messaging and coordination

**Implementation Approach**: Two separate Vue components with tab navigation on top for easier maintenance and code organization.

This design leverages the **Single Active Product** and **Single Active Project** architecture (Handover 0050/0050b), simplifying the UI by showing only the currently active project's implementation status.

---

## 1. Architecture Context

### Single Active Constraints
- **One Product Active** per tenant at any time (enforced via database)
- **One Project Active** per product at any time (enforced via database)
- **Simplification**: Jobs pane only shows agents working on THE active project
- **Dashboard Page**: Separate view for historical metrics and completed projects (future scope)

### Tab Structure & Navigation
```
Left-Hand Pane (Projects) - Dual-Tab Interface

┌─────────────────────────────────────────┐
│ [Launch Tab] [Jobs Tab]                 │  <- Tab navigation
├─────────────────────────────────────────┤
│                                         │
│ (Active tab content below)              │
│                                         │
└─────────────────────────────────────────┘

LAUNCH TAB (Always accessible)
├── Project Description Panel (left)
├── Orchestrator Mission Panel (right)
├── Agent Cards (appear as orchestrator creates them)
├── Stage Project Button → Launch jobs Button
└── Cancel Button (reset staging)

JOBS TAB (Active during implementation)
├── Project Header
├── Active Agent Cards (horizontal scroll, sorted by priority)
├── Message Stream (vertical scroll, right side)
├── Message Input (field + To dropdown + Submit)
└── Closeout State (when all agents complete):
    ├── "All agents report complete" banner
    ├── Closeout Project Button (on Orchestrator card)
    └── Summary View (viewable later in Dashboard modal)

User can switch between tabs at any time to review staging or monitor implementation
```

---

## 2. Visual Design Specifications

### 2.1 Agent Color Branding

**Six Preseeded Agent Templates** (from Handover 0041):

| Agent Type | Color Code | Hex Value | Badge ID | Usage |
|-----------|-----------|-----------|----------|-------|
| **Orchestrator** | Tan/Beige | `#D4A574` | `Or` | Primary coordinator |
| **Analyzer** | Red | `#E74C3C` | `An` | Analysis tasks |
| **Implementor** | Blue | `#3498DB` | `Im` | Implementation tasks |
| **Researcher** | Green | `#27AE60` | `Re` | Research tasks |
| **Reviewer** | Purple | `#9B59B6` | `Rv` | Code review tasks |
| **Tester** | Orange | `#E67E22` | `Te` | Testing tasks |

**Color Application**:
- **Agent Card Headers**: Background uses agent color (darkened 10% for depth)
- **Agent Card Frames**: Subtle border using agent color (lightened 20%)
- **Chat Head Badges**: Round dots with agent color background + white text
- **Message Stream**: Chat heads use same colors for visual continuity

**Multiple Agent Instances**:
- If 2+ implementors: First = `Im`, Second = `I2`, Third = `I3`
- Badge color remains the same, only ID changes

**Brand Harmony**:
- Overall UI maintains GiljoAI branding (existing color scheme)
- Agent colors are accents, not dominant page colors
- Should harmonize with Claude Code agent template YAML color choices

### 2.2 Chat Head Design

**Specifications**:
- **Shape**: Perfect circle (not rounded square)
- **Size**: 32px diameter (larger messages), 24px (compact view)
- **Background**: Agent color (from table above)
- **Text**: White, bold, centered (2-letter agent ID)
- **Border**: 2px solid white (for contrast against background)
- **Position**: Left-aligned in message stream

**Badge Examples**:
```
🟤 Or  (Orchestrator - tan background)
🔴 An  (Analyzer - red background)
🔵 Im  (Implementor - blue background)
🔵 I2  (Second Implementor - same blue)
🟢 Re  (Researcher - green background)
🟣 Rv  (Reviewer - purple background)
🟠 Te  (Tester - orange background)
```

### 2.3 Scroll Behavior

**Agent Cards (Horizontal)**:
- Horizontal scrollbar when 4+ agent cards exceed viewport width
- Each card maintains fixed width (280px recommended)
- Compact design to show wealth of information without overwhelming

**Message Stream (Vertical)**:
- Standard vertical scroll (auto-scroll to bottom on new messages)
- Sticky message input at bottom (always visible)
- Infinite scroll for historical messages (load on scroll-up)

---

## 3. Launch Panel State (Staging)

### 3.1 Purpose
- **Staging area** where orchestrator prepares the project mission
- User reviews orchestrator's plan before launching agents
- Orchestrator creates agent instances dynamically based on project needs
- User can edit missions, cancel staging, or proceed to launch

### 3.2 Layout (3-Column Design)

**Left Column: Orchestrator Card**
- Agent name: "Orchestrator" (tan/beige header)
- Agent ID: Xxxxxxxxxxxx
- Project Title + Project ID
- Other project card information
- **Stage Project Button** (initial state)
- **Cancel Button** (deletes all agents, mission, resets staging)

**Middle Column: Project Description Panel**
- Header: "Project Description"
- Content: Human-written project description from database
- Vertical scrollbar for long content
- **Edit Button** (bottom right)

**Right Column: Orchestrator Mission Panel**
- Header: "Orchestrator Mission"
- Content: Mission generated by orchestrator after "Stage Project" triggered
- Vertical scrollbar for long content
- **Edit Button** (bottom right)

### 3.3 Agent Cards Section (Bottom Row)

**Dynamic Agent Creation**:
- Agents appear as orchestrator creates them (max 8 types, unlimited agents)
- Horizontal scrollbar when agents exceed viewport width
- Each agent card shows:
  - **Colored Header**: Agent type determines color (Analyzer=red, Implementer=blue, etc.)
  - **Agent ID**: Xxxxxxxxxxxx
  - **Role**: Agent's assigned role/responsibility
  - **Vertical Scrollbar**: For long role descriptions
  - **Edit Mission Button**: Allows user to modify agent's mission

**Agent Types** (from PDF):
- Orchestrator (tan/beige)
- Analyzer (red)
- Implementer (blue)
- Reviewer (purple)
- Tester (yellow/gold)
- Documenter (green)

### 3.4 Launch Workflow

**Step 1: Initial State**
- User sees empty Launch Panel
- Orchestrator card shows "Stage Project" button
- Project Description is visible (populated from database)
- Orchestrator Mission is empty

**Step 2: Staging**
- User clicks "Stage Project"
- Orchestrator builds mission (appears in right panel)
- Orchestrator creates agent instances (cards appear in bottom row)
- Each agent has pre-defined mission
- "Stage Project" button disappears

**Step 3: Review & Edit**
- User reviews orchestrator mission
- User reviews agent missions
- User can click "Edit" on any mission to modify
- User can click "Cancel" to reset entire staging

**Step 4: Launch**
- When orchestrator completes staging, **"Launch jobs" button** appears (yellow/gold)
- Button replaces "Stage Project" location
- User clicks "Launch jobs" → Transitions to Jobs Panel State
- "Cancel" button remains available

### 3.5 Cancel Behavior
- **Red "Cancel" button** available throughout staging
- Clicking Cancel:
  - Deletes all created agents
  - Deletes orchestrator mission
  - Resets staging completely
  - Returns to initial state (Stage Project button reappears)

---

## 4. Jobs Panel State (Implementation)

### 4.1 Layout Structure

**Two-Column Design**:
- **Left Column (60%)**: Agent cards + Project header
- **Right Column (40%)**: Message stream + Message input

**Project Header** (top of left column):
- Project: {TITLE}
- Project ID: xxxxxxxx

### 4.2 Agent Cards Section (Left Column)

**Layout**:
- Horizontal row of agent cards (scrollable)
- Cards arranged with **priority sorting** (see 4.3)
- Vertical scrollbar within each card for long content
- Each card shows different content based on status

**Card Design**:
- Width: 280px (recommended)
- Header: Colored background matching agent type
- Body: Dark blue/teal background (#2C5F77 approximate)
- Gap: 12px between cards

**Agent Card States:**

**1. Waiting State (Ready to Launch)**
```
┌──────────────────────────┐
│ Analyzer (Red Header)    │
├──────────────────────────┤
│ Agent ID: Xxxxxxxxxxxx   │
│ Status: {Waiting}        │
│ Message badges and       │
│ other info               │
│ ┌──────────────────────┐ │
│ │                      │ │  <- Scrollbar
│ └──────────────────────┘ │
│ ┌──────────────────────┐ │
│ │  Launch Agent        │ │  <- Yellow button
│ └──────────────────────┘ │
└──────────────────────────┘
```

**2. Working State**
```
┌──────────────────────────┐
│ Implementer (Blue Hdr)   │
├──────────────────────────┤
│ Agent ID: Xxxxxxxxxxxx   │
│ Status: {Working}        │
│ Message badges and other │
│ info, like todo list etc.│
│ (may be undefined yet)   │
│ ┌──────────────────────┐ │
│ │  Details             │ │  <- Button
│ └──────────────────────┘ │
└──────────────────────────┘
```

**3. Complete State**
```
┌──────────────────────────┐
│ Implementer 2 (Blue Hdr) │
├──────────────────────────┤
│ Agent ID: Xxxxxxxxxxxx   │
│ Status: {Complete}       │
│ Message badges and       │
│ other info               │
│ ┌──────────────────────┐ │
│ │                      │ │  <- Scrollbar
│ └──────────────────────┘ │
│                          │
│   Complete (Yellow)      │  <- Yellow text/badge
│   I2 (Badge)             │  <- Multiple instance indicator
└──────────────────────────┘
```

**4. Failure/Blocked State**
```
┌──────────────────────────┐
│ Agent Name (Color Hdr)   │
├──────────────────────────┤
│ Agent ID: Xxxxxxxxxxxx   │
│ Status: {Error}          │
│ Message badges           │
│ ┌──────────────────────┐ │
│ │                      │ │
│ └──────────────────────┘ │
│ ┌──────────────────────┐ │
│ │  Failure (Magenta)   │ │  <- Status badge
│ └──────────────────────┘ │
│ ┌──────────────────────┐ │
│ │  Blocked (Orange)    │ │  <- Status badge
│ └──────────────────────┘ │
└──────────────────────────┘
```

**Orchestrator Card - Special Features**:
- Includes **Launch Prompt Icons** (see 4.4)
- Shows "Closeout Project" button when all agents complete (see Section 6)

### 4.3 Agent Card Sorting Priority

**Dynamic Reordering** (most important at top):
1. **Failed/Blocked** - Agents with errors (require immediate attention)
2. **Ready to Launch** - Agents waiting to start (show "Launch Agent" button)
3. **Working** - Agents currently active
4. **Complete** - Finished agents (move to bottom)

**Multiple Instances**:
- Second instance of same agent type: Badge shows "I2"
- Third instance: "I3"
- Color remains the same, only ID changes

### 4.4 Launch Prompt Icons (Orchestrator Card Only)

**Icons** (square badges with rounded corners):
- **Claude Code**: Orange square icon
- **Codex/Gemini**: Purple/white square icon

**Explanation** (from PDF):
"Each agent requires its own Terminal window and agentic AI tool started. Claude Code uses subagents, and does not require individual terminal windows per agent but can still be used this way"

**Icon Purpose**:
- Visual indicator of which AI tool to launch in terminal
- User clicks icon → Opens corresponding CLI tool
- Creates audit log via MCP message archive

### 4.5 Message Stream Section (Right Column)

**Layout**:
- Vertical message feed (chronological, oldest at top, newest at bottom)
- Auto-scroll to bottom on new messages
- Each message shows:
  - **Round Colored Chat Head**: 2-letter badge (An, Or, Im, I2)
  - **Message Routing**: "To Implementor:", "To orchestor:", "Broadcast"
  - **Message Content**: Text content
  - **User Icon**: User messages show generic user avatar at bottom

**Message Routing Display** (from PDF examples):
```
An  To Implementor: Ipsum Lorem
An  To orchestor: Ipsum Lorem
Or  Broadcast Ipsum Lorem
Im  To Orchestrator: Acknowledged
Or  To Orchestrator: Tell Implementor 2 to change xyzxyzxyz
Or  To Implementor 2: Ipsum Lorem xyz
I2  To Orchestrator: Acknowledged
```

**Visual Design**:
- Messages float against darker blue background
- User messages show avatar icon (generic user silhouette)
- Vertical scrollbar for long message history

### 4.6 Message Input Section (Right Column Bottom)

**Layout** (sticky at bottom):
```
┌────────────────────────────────────────────────┐
│ [User Icon] [Message text...    ] [To ▼] [<]  │
└────────────────────────────────────────────────┘
```

**Components (LEFT to RIGHT)**:
1. **User Icon**: Generic user avatar (left-most)
2. **Message Input Field**: Text area (expands vertically)
3. **To Dropdown**: Recipient selector (right side)
4. **Submit Button**: `<` chevron icon (right-most)

**To Dropdown Options**:
- **Orchestrator** (default)
- **Broadcast** (send to all agents)
- *(Future)* Individual agent selection

**Key Difference from Original Spec**:
- To dropdown is on the RIGHT, not the left
- User icon precedes the input field

---

## 5. Project Closeout State (Completion)

### 5.1 Trigger Condition
- All agents report status: {Complete}
- System detects all agent jobs in "completed" state
- Green banner appears: **"All agents report complete"**

### 5.2 Visual Changes

**Orchestrator Card Transformation**:
```
┌──────────────────────────┐
│ Orchestrator (Tan Header)│
├──────────────────────────┤
│ Agent ID: Xxxxxxxxxxxx   │
│ Status: {Waiting}        │  <- Orchestrator waits for closeout
│ Message badges and info  │
│ ┌──────────────────────┐ │
│ │                      │ │
│ └──────────────────────┘ │
│ ┌──────────────────────┐ │
│ │  Closeout Project    │ │  <- Green button appears
│ └──────────────────────┘ │
└──────────────────────────┘
```

**Other Agent Cards**:
- All show Status: {Complete}
- "Complete" badge in yellow text
- Multiple instances show badge (I2, I3, etc.)

**Green Banner**:
- Appears at top of agent card area
- Text: "All agents report complete"
- Background: Green (#27AE60 or similar)
- Spans full width of left column

### 5.3 Closeout Workflow

**Step 1: Automatic Detection**
- System monitors agent job completion
- When last agent completes → Trigger closeout state
- Green banner appears
- "Closeout Project" button appears on Orchestrator card

**Step 2: User Action**
- User clicks "Closeout Project" button
- Panel switches to **summary view**

**Step 3: Summary View**
- Shows project completion summary
- Metrics: Time elapsed, agents used, tasks completed
- Final status of each agent
- Links to generated artifacts/documentation
- Option to return to Dashboard

**Step 4: Dashboard Integration**
- Same summary view accessible later in **/dashboard modal**
- Historical record of completed project
- Searchable and filterable

### 5.4 State After Closeout
- Project status changes to "completed" in database
- Project becomes inactive (Single Active Project constraint)
- User can select/create new project
- Completed project data retained for dashboard viewing

---

## 6. Technical Implementation

### 6.1 Frontend Components (Vue 3)

**New Files**:
```
frontend/src/components/projects/
├── ProjectTabs.vue             # Parent container with tab navigation
├── LaunchTab.vue               # Launch tab content (staging workflow)
├── JobsTab.vue                 # Jobs tab content (implementation + closeout)
├── AgentCard.vue               # Individual agent card (reused across tabs)
├── MessageStream.vue           # Message feed component (Jobs tab)
├── MessageInput.vue            # Input + TO dropdown + submit (Jobs tab)
├── ChatHeadBadge.vue           # Reusable round badge component
└── LaunchPromptIcons.vue       # Claude Code / Codex/Gemini icons
```

**Styling**:
```
frontend/src/styles/
├── agent-colors.scss           # Agent color variables
├── launch-panel.scss           # Launch panel specific styles
├── jobs-panel.scss             # Jobs panel specific styles
└── closeout-panel.scss         # Closeout panel specific styles
```

### 6.2 State Management

**Active Tab Tracking**:
```javascript
// Pinia store: stores/projectTabs.js
{
  state: {
    activeTab: 'launch',        // 'launch' | 'jobs'
    project: null,
    agents: [],
    orchestratorMission: '',
    messages: [],
    allAgentsComplete: false,
    isStaging: false,           // Orchestrator building mission
    isLaunched: false           // Jobs started
  },

  actions: {
    switchTab(tabName) {
      this.activeTab = tabName  // 'launch' or 'jobs'
    },

    stageProject() {
      this.isStaging = true
      // Orchestrator builds mission & creates agents
    },

    launchJobs() {
      this.isLaunched = true
      this.activeTab = 'jobs'   // Auto-switch to Jobs tab
    },

    completeAgent(agentId) {
      // Check if all agents complete
      if (this.checkAllComplete()) {
        this.allAgentsComplete = true
      }
    },

    closeoutProject() {
      // Summary view (within Jobs tab)
      // Project status → completed
    },

    resetStaging() {
      // Delete agents, reset mission
      this.isStaging = false
      this.agents = []
      this.orchestratorMission = ''
      this.activeTab = 'launch'
    }
  }
}
```

**Benefits of Dual-Tab Approach**:
- ✅ Easier code maintenance (separate components)
- ✅ User can review Launch tab during implementation
- ✅ Simpler state management (no complex state machine)
- ✅ Better performance (only active tab rendered)

### 5.2 Agent Color Configuration

**Option 1: Hardcoded Constants** (recommended for stability)
```javascript
// frontend/src/config/agentColors.js
export const AGENT_COLORS = {
  orchestrator: { hex: '#D4A574', badge: 'Or', name: 'Orchestrator' },
  analyzer: { hex: '#E74C3C', badge: 'An', name: 'Analyzer' },
  implementor: { hex: '#3498DB', badge: 'Im', name: 'Implementor' },
  researcher: { hex: '#27AE60', badge: 'Re', name: 'Researcher' },
  reviewer: { hex: '#9B59B6', badge: 'Rv', name: 'Reviewer' },
  tester: { hex: '#E67E22', badge: 'Te', name: 'Tester' }
}
```

**Option 2: Database-Driven** (future enhancement)
- Store colors in `agent_templates` table
- Sync with Claude Code YAML template colors
- Allow admin customization via Templates tab

### 5.3 WebSocket Events

**New Events** (add to `api/websocket_handler.py`):
```python
# Agent job status updates
job:agent_started       # When agent begins work
job:agent_message       # When agent sends message
job:agent_completed     # When agent finishes task
job:agent_failed        # When agent encounters error

# UI updates
ui:agent_card_update    # Update agent card status
ui:message_added        # New message in stream
```

### 5.4 API Endpoints

**New Endpoints** (add to `api/endpoints/agent_jobs.py`):
```python
POST   /api/jobs/message          # Send message to agent(s)
GET    /api/jobs/{id}/messages    # Get message history
GET    /api/jobs/active/cards     # Get agent card data
PATCH  /api/jobs/{id}/broadcast   # Broadcast message to all agents
```

### 5.5 State Management (Pinia)

**New Store**: `frontend/src/stores/jobsPane.js`
```javascript
// State
{
  activeTab: 'launch',          // 'launch' | 'implementation'
  agentCards: [],               // Array of active agent card data
  messages: [],                 // Message stream
  messageInput: '',             // Current input text
  selectedRecipient: 'orchestrator'  // 'orchestrator' | 'broadcast'
}

// Actions
switchTab(tabName)
loadAgentCards()
loadMessages()
sendMessage({ recipient, content })
updateAgentCard({ agentId, status, progress })
addMessage({ agentId, content, type })
```

---

## 6. Implementation Phases

### Phase 1: Core UI Structure (Week 1)
- [x] Create tab container component
- [x] Implement Launch tab (reuse existing project view)
- [x] Create empty Implementation tab shell
- [x] Add tab switching logic
- [x] Write unit tests

### Phase 2: Agent Cards (Week 1-2)
- [ ] Design AgentCard.vue component
- [ ] Implement horizontal scroll container
- [ ] Add expand/collapse functionality
- [ ] Connect to WebSocket for real-time updates
- [ ] Add agent color theming

### Phase 3: Message Stream (Week 2)
- [ ] Design MessageStream.vue component
- [ ] Implement ChatHeadBadge.vue (round badges)
- [ ] Add message type rendering (agent/user/system/MCP)
- [ ] Implement vertical scroll + auto-scroll
- [ ] Add timestamp formatting

### Phase 4: Message Input (Week 2-3)
- [ ] Design MessageInput.vue component
- [ ] Implement TO dropdown (orchestrator/broadcast)
- [ ] Add submit button with keyboard shortcut
- [ ] Connect to backend API
- [ ] Add validation and error handling

### Phase 5: WebSocket Integration (Week 3)
- [ ] Add new WebSocket events to backend
- [ ] Connect frontend to WebSocket for real-time updates
- [ ] Test agent card updates
- [ ] Test message stream updates
- [ ] Add reconnection logic

### Phase 6: Polish & Testing (Week 3-4)
- [ ] Responsive design testing
- [ ] Accessibility audit (ARIA labels, keyboard navigation)
- [ ] Performance optimization (message virtualization)
- [ ] Cross-browser testing
- [ ] User acceptance testing

---

## 7. Success Criteria

### 7.1 Functional Requirements
- ✅ User can switch between Launch and Implementation tabs seamlessly
- ✅ Agent cards display with correct colors matching agent type
- ✅ Chat head badges are round with correct 2-letter IDs
- ✅ Multiple instances of same agent type show I2, I3, etc.
- ✅ Message stream shows chronological agent communication
- ✅ User can send messages to orchestrator or broadcast to all
- ✅ Real-time updates via WebSocket (no manual refresh)

### 7.2 Visual Requirements
- ✅ Agent colors match specification (tan/red/blue/green/purple/orange)
- ✅ Overall UI maintains GiljoAI branding
- ✅ Horizontal scroll works smoothly for agent cards
- ✅ Vertical scroll works smoothly for message stream
- ✅ Message input sticky at bottom (always visible)
- ✅ Compact design maximizes information density

### 7.3 Performance Requirements
- ✅ Tab switching <100ms (no noticeable lag)
- ✅ Message rendering <50ms per message
- ✅ WebSocket latency <200ms for updates
- ✅ Smooth scrolling (60fps minimum)
- ✅ Memory efficient (virtualized rendering for 1000+ messages)

---

## 8. Design Mockups (Textual Representation)

### State 1: Launch Panel (Staging - Initial)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PROJECT LAUNCH PANEL                                                        │
├────────────────────┬────────────────────────────┬────────────────────────────┤
│ Orchestrator       │  Project Description       │  Orchestrator Mission      │
│ (Tan Header)       │                            │                            │
│ ┌────────────────┐ │  Project description as    │  Mission appears here as   │
│ │ Agent ID:      │ │  written by the developer  │  Orchestrator builds the   │
│ │ Xxxxxxxxxxxx   │ │  (Human written content    │  project mission after     │
│ │                │ │  from the project entry in │  the Lunch Prompt is       │
│ │ Project {Title}│ │  the database)             │  triggered.                │
│ │ Project ID: xx │ │                            │                            │
│ │ Other project  │ │                            │                            │
│ │ card info      │ │  [Scroll]                  │  [Scroll]                  │
│ │                │ │                            │                            │
│ └────────────────┘ │  [Edit]                    │  [Edit]                    │
│                    │                            │                            │
│ [Stage Project]    │                            │                            │
│ [Cancel]           │                            │                            │
└────────────────────┴────────────────────────────┴────────────────────────────┘
```

### State 1b: Launch Panel (After Staging - Agents Created)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PROJECT LAUNCH PANEL                          [Scroll bar →]                │
├────────────────────┬────────────────────────────┬────────────────────────────┤
│ Orchestrator       │  Project Description       │  Orchestrator Mission      │
│ (Tan Header)       │  [Content visible]         │  [Mission now visible]     │
│ [Content as above] │  [Edit]                    │  [Edit]                    │
│                    │                            │                            │
│ [Launch jobs]      │                            │                            │
│ (Yellow button)    │                            │                            │
│ [Cancel]           │                            │                            │
└────────────────────┴────────────────────────────┴────────────────────────────┘
│                                                                               │
│ ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────┐│
│ │ Analyzer   │  │Implementer │  │ Reviewer   │  │  Tester    │  │Document││
│ │ (Red Hdr)  │  │ (Blue Hdr) │  │(Purple Hdr)│  │(Yellow Hdr)│  │(Grn Hdr)││
│ │Agent ID: xx│  │Agent ID: xx│  │Agent ID: xx│  │Agent ID: xx│  │Agent:xx ││
│ │Role: ...   │  │Role: ...   │  │Role: ...   │  │Role: ...   │  │Role: ...││
│ │[Scroll]    │  │[Scroll]    │  │[Scroll]    │  │[Scroll]    │  │[Scroll] ││
│ │            │  │            │  │            │  │            │  │         ││
│ │[Edit Mssn] │  │[Edit Mssn] │  │[Edit Mssn] │  │[Edit Mssn] │  │[Edit Msn││
│ └────────────┘  └────────────┘  └────────────┘  └────────────┘  └─────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### State 2: Jobs Panel (Implementation)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PROJECT JOB PANEL                                  [Scroll bar]             │
├──────────────────────────────────────────┬──────────────────────────────────┤
│ Project: {TITLE}                         │  Messages                        │
│ Project ID: xxxxxxxx                     │  [Scroll]                        │
│                                          │                                  │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ │  An  To Implementor: Ipsum Lorem │
│ │Orchestr  │ │ Analyzer │ │Implement │ │  An  To orchestor: Ipsum Lorem   │
│ │(Tan Hdr) │ │ (Red Hdr)│ │(Blue Hdr)│ │  Or  Broadcast Ipsum Lorem       │
│ │Agent:xx  │ │Agent: xx │ │Agent: xx │ │  Im  To Orchestrator: Ack...     │
│ │Status:   │ │Status:   │ │Status:   │ │  Or  To Orchestrator: Tell       │
│ │{Waiting} │ │{Waiting} │ │{Working} │ │      Implementor 2 to change...  │
│ │Msg badge │ │Msg badge │ │Msg badge │ │  Or  To Implementor 2: Ipsum...  │
│ │          │ │          │ │todo list │ │  I2  To Orchestrator: Ack...     │
│ │[Icons]   │ │          │ │          │ │                                  │
│ │🟧Claude  │ │[Launch   │ │[Details] │ │  [User avatar]                   │
│ │  Code    │ │ Agent]   │ │          │ │                                  │
│ │🟪Codex/  │ │(Yellow)  │ │          │ │                                  │
│ │  Gemini  │ │          │ │          │ │                                  │
│ └──────────┘ └──────────┘ └──────────┘ │                                  │
│                                          │ ┌──────────────────────────────┐ │
│ ┌──────────┐                            │ │👤 [Type...] [To▼] [<Submit] │ │
│ │Implem. 2 │                            │ └──────────────────────────────┘ │
│ │(Blue Hdr)│                            │                                  │
│ │Agent: xx │     [< Agent Priority →]   │                                  │
│ │Status:   │     Ready → Working →      │                                  │
│ │{Complete}│     Complete (bottom)      │                                  │
│ │Complete  │     Failed/Blocked (top)   │                                  │
│ │I2 badge  │                            │                                  │
│ └──────────┘                            │                                  │
└──────────────────────────────────────────┴──────────────────────────────────┘
```

### State 3: Closeout Panel (Completion)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PROJECT JOB PANEL                                  [Scroll bar]             │
├──────────────────────────────────────────┬──────────────────────────────────┤
│ Project: {TITLE}                         │  Messages                        │
│ Project ID: xxxxxxxx                     │  [Scroll continues...]           │
│                                          │                                  │
│ ┌──────────────────────────────────────┐│                                  │
│ │  All agents report complete (Green)  ││                                  │
│ └──────────────────────────────────────┘│                                  │
│                                          │                                  │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ │                                  │
│ │Orchestr  │ │ Analyzer │ │Implement │ │                                  │
│ │(Tan Hdr) │ │ (Red Hdr)│ │(Blue Hdr)│ │                                  │
│ │Agent:xx  │ │Agent: xx │ │Agent: xx │ │                                  │
│ │Status:   │ │Status:   │ │Status:   │ │                                  │
│ │{Waiting} │ │{Complete}│ │{Complete}│ │                                  │
│ │          │ │          │ │          │ │                                  │
│ │[Closeout │ │Complete  │ │Complete  │ │                                  │
│ │ Project] │ │ (Yellow) │ │ (Yellow) │ │                                  │
│ │ (Green)  │ │          │ │          │ │                                  │
│ └──────────┘ └──────────┘ └──────────┘ │                                  │
│                                          │                                  │
│ ┌──────────┐                            │                                  │
│ │Implem. 2 │                            │                                  │
│ │(Blue Hdr)│                            │                                  │
│ │Status:   │                            │                                  │
│ │{Complete}│                            │                                  │
│ │Complete  │                            │                                  │
│ │I2 badge  │                            │                                  │
│ └──────────┘                            │                                  │
│                                          │                                  │
│ [User clicks Closeout → Summary View]   │                                  │
└──────────────────────────────────────────┴──────────────────────────────────┘
```

---

## 9. Future Enhancements (Out of Scope)

- **Dashboard Page**: Historical metrics, completed projects, agent performance
- **Agent Selection in TO**: Send to specific agent (not just orchestrator/broadcast)
- **Message Attachments**: Upload files to agents
- **Voice Input**: Speech-to-text for message input
- **Agent Performance Metrics**: Token usage, response time charts
- **Message Search**: Full-text search across message history
- **Export Transcript**: Download conversation as markdown/PDF

---

## 10. Key Corrections from PDF Review

### Critical Architecture Decision
- ✅ **Dual-tab interface** - Two separate components for easier maintenance
- ✅ **Launch Tab**: Always accessible, shows staging workflow
- ✅ **Jobs Tab**: Shows implementation (includes closeout state when complete)
- ✅ **Tab switching**: User can freely switch between tabs to review or monitor

### Launch Panel Corrections
- ✅ **3-column layout**: Orchestrator card (left) + Project Description (middle) + Orchestrator Mission (right)
- ✅ **Staging workflow**: Stage Project → Orchestrator creates agents → Launch jobs button appears
- ✅ **Cancel button**: Deletes all agents, mission, resets completely
- ✅ **Agent cards in bottom row**: Appear dynamically as orchestrator creates them

### Jobs Panel Corrections
- ✅ **2-column layout**: Agent cards + Project header (left 60%) | Messages + Input (right 40%)
- ✅ **Agent sorting priority**: Failed/Blocked → Ready → Working → Complete
- ✅ **Launch Prompt Icons**: Claude Code (orange), Codex/Gemini (purple) on Orchestrator card only
- ✅ **Message routing display**: "To Implementor:", "To orchestor:", "Broadcast"
- ✅ **Message input layout**: User icon (left) → Input field → To dropdown (right) → Submit (<)

### Visual Design Corrections
- ✅ **Agent card backgrounds**: Dark blue/teal body, colored headers only
- ✅ **Status badges**: Waiting, Working, Complete (yellow), Failure (magenta), Blocked (orange)
- ✅ **Chat heads**: Round colored badges with 2-letter IDs (An, Or, Im, I2) ✓ (correctly captured initially)
- ✅ **Multiple instances**: I2, I3 badges (same color, different ID)

### Closeout Workflow Corrections
- ✅ **Green banner**: "All agents report complete" appears when all done
- ✅ **Closeout button**: Appears on Orchestrator card (green button)
- ✅ **Summary view**: Switches panel to completion summary
- ✅ **Dashboard integration**: Same summary accessible later in /dashboard modal

## 11. Questions & Decisions

### Resolved
- ✅ **Panel Structure**: Dual-tab interface (Launch Tab + Jobs Tab)
- ✅ **Tab Navigation**: User can freely switch between tabs
- ✅ **Closeout Location**: Within Jobs tab (not separate state/tab)
- ✅ **Agent Colors**: Hardcoded to match preseeded templates
- ✅ **Chat Head Shape**: Round dots (not squares)
- ✅ **Badge IDs**: 2-letter abbreviations (Or, An, Im, etc.)
- ✅ **Multiple Agents**: Numeric suffix (Im, I2, I3)
- ✅ **Message Controls**: TO dropdown (right side) + submit button (<)
- ✅ **Message Input Layout**: User icon → Input → To dropdown → Submit (left to right)

### Open Questions
1. **Agent Color Source**: Hardcoded constants or database-driven? (Recommend: Start hardcoded, migrate to DB later)
2. **Message Virtualization**: Implement now or wait for performance issues? (Recommend: Implement now for 1000+ message support)
3. **Markdown Rendering**: Allow full markdown in messages or plain text only? (Recommend: Full markdown for rich formatting)
4. **Mobile Responsiveness**: Optimize for mobile or desktop-only? (Recommend: Desktop-first, mobile-friendly scrolling)
5. **Launch Prompt Icon Behavior**: Click to copy command or open terminal directly? (Recommend: Copy command to clipboard + show confirmation)

---

## 11. Testing Strategy

### Unit Tests
- Component rendering (all Vue components)
- Agent color mapping logic
- Badge ID generation (including I2, I3 numbering)
- Message formatting and timestamps

### Integration Tests
- Tab switching preserves state
- WebSocket message handling
- API endpoint communication
- Message send/receive flow

### Visual Regression Tests
- Agent card color accuracy (screenshot comparison)
- Chat head badge rendering (round shape, correct colors)
- Scroll behavior (horizontal + vertical)
- Responsive layout (different viewport sizes)

### User Acceptance Tests
- Can user understand agent roles by color alone?
- Is message stream readable and scannable?
- Are controls (TO dropdown, submit) intuitive?
- Does real-time update feel responsive?

---

## 12. Documentation Updates Required

- [ ] Update `docs/FRONTEND_GUIDE.md` with new components
- [ ] Add agent color specification to `docs/DESIGN_SYSTEM.md`
- [ ] Update `docs/API_REFERENCE.md` with new endpoints
- [ ] Create `docs/JOBS_PANE_USER_GUIDE.md` for end users
- [ ] Update `README.md` with new UI screenshots

---

## 13. Dependencies

**External Libraries**:
- **Vue 3**: Core framework (already installed)
- **Vuetify 3**: UI components (already installed)
- **vue-markdown-render**: Markdown rendering in messages (new)
- **vue-virtual-scroller**: Message stream virtualization (new)

**Internal Dependencies**:
- Handover 0050: Single Active Product (database constraints)
- Handover 0050b: Single Active Project (database constraints)
- Handover 0041: Agent Template Management (agent color data)
- Existing WebSocket infrastructure (extend with new events)

---

## 14. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Performance with 1000+ messages** | Medium | Implement virtual scrolling from start |
| **Agent color consistency** | Low | Use centralized color config |
| **WebSocket reconnection issues** | Medium | Add robust reconnection logic + error UI |
| **Mobile UX degradation** | Low | Focus on desktop-first, ensure scrolling works on mobile |
| **Browser compatibility** | Low | Test on Chrome, Firefox, Safari, Edge |

---

## 15. Sign-Off

**Product Owner**: _________________
**Lead Developer**: _________________
**QA Lead**: _________________
**Date**: _________________

---

## Appendix A: Agent Color Palette (CSS Variables)

```css
/* frontend/src/styles/agent-colors.scss */
:root {
  /* Orchestrator - Tan/Beige */
  --agent-orchestrator-primary: #D4A574;
  --agent-orchestrator-dark: #B8905E;
  --agent-orchestrator-light: #E5C9A3;

  /* Analyzer - Red */
  --agent-analyzer-primary: #E74C3C;
  --agent-analyzer-dark: #C0392B;
  --agent-analyzer-light: #F1948A;

  /* Implementor - Blue */
  --agent-implementor-primary: #3498DB;
  --agent-implementor-dark: #2980B9;
  --agent-implementor-light: #85C1E9;

  /* Researcher - Green */
  --agent-researcher-primary: #27AE60;
  --agent-researcher-dark: #229954;
  --agent-researcher-light: #7DCEA0;

  /* Reviewer - Purple */
  --agent-reviewer-primary: #9B59B6;
  --agent-reviewer-dark: #8E44AD;
  --agent-reviewer-light: #C39BD3;

  /* Tester - Orange */
  --agent-tester-primary: #E67E22;
  --agent-tester-dark: #D35400;
  --agent-tester-light: #F0B27A;
}
```

---

## Appendix B: Message Type Specifications

| Type | Icon | Background | Text Color | Example |
|------|------|------------|------------|---------|
| **Agent Message** | Agent badge | White | Dark gray | "Starting analysis phase..." |
| **User Message** | 👤 | Light blue (#E3F2FD) | Dark blue | "Please add error handling" |
| **System Message** | ⚙️ | Light gray (#F5F5F5) | Gray | "Agent job started" |
| **MCP Tool Call** | 🛠️ | Light yellow (#FFF9C4) | Dark gray | `edit_file(path="...")` |
| **Error Message** | ⚠️ | Light red (#FFEBEE) | Dark red | "Connection timeout" |

---

**End of Handover 0077**
