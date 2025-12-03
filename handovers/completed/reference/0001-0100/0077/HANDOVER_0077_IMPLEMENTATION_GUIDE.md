# Handover 0077: Implementation Guide & File Reference

**Purpose**: Quick reference guide for all Handover 0077 components, their locations, and testing status.

---

## Component Files Overview

### 1. ProjectTabs.vue (Tab Container)
**Location**: `F:/GiljoAI_MCP/frontend/src/components/projects/ProjectTabs.vue`
**Lines**: 305 | **Status**: PRODUCTION READY

**Purpose**: Parent container managing tab navigation between Launch and Jobs views

**Key Features**:
- Manages activeTab state (launch | jobs)
- Switches tab when "Launch jobs" clicked
- Handles all parent events and emits
- Error snackbar display
- WebSocket subscription management

**Props**:
```javascript
props: {
  project: { type: Object, required: true }
}
```

**Emits**:
```javascript
emit('stage-project')
emit('launch-jobs')
emit('cancel-staging')
emit('edit-description')
emit('edit-mission', agentId)
emit('edit-agent-mission', agentId)
emit('launch-agent', agent)
emit('view-details', agent)
emit('view-error', agent)
emit('closeout-project')
emit('send-message', message, recipient)
```

**CSS Classes**:
- `.project-tabs-container` - Root wrapper
- `.tabs-header` - Tab navigation header
- `.tabs-content` - Tab content area

---

### 2. LaunchTab.vue (Staging View)
**Location**: `F:/GiljoAI_MCP/frontend/src/components/projects/LaunchTab.vue`
**Lines**: 568 | **Status**: PRODUCTION READY

**Purpose**: 3-column staging interface for orchestrator mission generation

**Layout**:
```
┌─────────────────────────────────────────┐
│ Left (25%)    │ Middle (35%)  │ Right (40%) │
│ Orchestrator  │ Description   │ Mission     │
│ Card          │ Panel         │ Panel       │
├───────────────┴───────────────┴─────────────┤
│ Agent Cards Row (horizontal scroll)         │
└─────────────────────────────────────────────┘
```

**Key Props**:
```javascript
project: Object (required)
isStaging: Boolean (default: false)
```

**Key Data**:
```javascript
missionText: String           // Orchestrator mission
agents: Array                 // Created agents
stagingInProgress: Boolean    // Loading state
readyToLaunch: Boolean        // Ready to proceed
showCancelDialog: Boolean     // Confirmation dialog
```

**Key Methods**:
- `handleStageProject()` - Triggers orchestrator
- `handleLaunchJobs()` - Launches all agents
- `handleCancelStaging()` - Resets everything
- `getInstanceNumber(agent)` - Calculates I2, I3 numbering

**CSS Classes**:
- `.launch-tab` - Root container
- `.launch-columns` - 3-column grid
- `.orchestrator-card` - Left column
- `.description-panel` - Middle column
- `.mission-panel` - Right column
- `.agent-cards-row` - Bottom row
- `.agent-cards-container` - Horizontal scroll

---

### 3. JobsTab.vue (Implementation View)
**Location**: `F:/GiljoAI_MCP/frontend/src/components/projects/JobsTab.vue`
**Lines**: 465 | **Status**: PRODUCTION READY

**Purpose**: 2-column implementation interface with agent cards and messages

**Layout**:
```
┌──────────────────────────┬───────────────────┐
│ Left (60%)               │ Right (40%)       │
│ ┌──────────────────────┐ │ ┌───────────────┐ │
│ │ Project Header       │ │ │ Message Stream│ │
│ ├──────────────────────┤ │ ├───────────────┤ │
│ │ Agent Cards          │ │ │ Messages      │ │
│ │ (Horizontal Scroll)  │ │ │ (Auto-scroll) │ │
│ │                      │ │ ├───────────────┤ │
│ │                      │ │ │ Message Input │ │
│ │                      │ │ │ (Sticky)      │ │
│ └──────────────────────┘ │ └───────────────┘ │
└──────────────────────────┴───────────────────┘
```

**Key Props**:
```javascript
project: Object (required)
agents: Array (required, default: [])
messages: Array (default: [])
allAgentsComplete: Boolean (default: false)
```

**Key Computed Properties**:
```javascript
sortedAgents      // Agents sorted by priority
```

**Key Methods**:
- `getInstanceNumber(agent)` - Gets I2, I3 numbering
- `isOrchestratorAgent(agent)` - Checks if orchestrator
- `handleLaunchAgent(agent)` - Launches agent
- `handleViewDetails(agent)` - Shows agent details
- `handleViewError(agent)` - Shows error details
- `handleCloseoutProject()` - Triggers closeout
- `handleSendMessage(message, recipient)` - Sends message
- `scrollAgentsLeft()` - Scrolls agent cards left
- `scrollAgentsRight()` - Scrolls agent cards right
- `handleAgentsKeydown(event)` - Keyboard navigation

**Agent Sorting Priority**:
```javascript
failed: 1        // Highest priority
blocked: 2
waiting: 3
working: 4
complete: 5      // Lowest priority
```

**CSS Classes**:
- `.jobs-tab` - Root container
- `.jobs-tab__complete-banner` - Green completion banner
- `.jobs-tab__row` - Main 2-column grid
- `.jobs-tab__left-column` - Agent cards column
- `.jobs-tab__right-column` - Message column
- `.jobs-tab__project-header` - Project info
- `.jobs-tab__agents-scroll` - Horizontal scroll container
- `.jobs-tab__agents-grid` - Agent card flex container
- `.jobs-tab__agent-card` - Individual agent card
- `.jobs-tab__scroll-indicators` - Scroll buttons
- `.jobs-tab__messages-panel` - Message container
- `.jobs-tab__message-stream` - Message list
- `.jobs-tab__message-input` - Input area

---

### 4. AgentCardEnhanced.vue (Agent Card Component)
**Location**: `F:/GiljoAI_MCP/frontend/src/components/projects/AgentCardEnhanced.vue`
**Lines**: 340+ | **Status**: PRODUCTION READY

**Purpose**: Reusable agent card displaying different states based on context

**Props**:
```javascript
agent: Object (required)
mode: String (default: 'jobs', validator: ['launch', 'jobs'])
instanceNumber: Number (default: 1)
isOrchestrator: Boolean (default: false)
showCloseoutButton: Boolean (default: false)
```

**Card States**:
1. **Waiting** - Ready to launch
   - Status: Gray "Waiting" badge
   - Button: Yellow "Launch Agent"
   - Content: Mission text

2. **Working** - Currently active
   - Status: Blue "Working" badge
   - Progress bar (0-100%)
   - Current task display
   - Button: "Details"

3. **Complete** - Finished
   - Status: Gold "Complete" badge
   - Instance badge (I2, I3)
   - No action button

4. **Failed/Blocked** - Error state
   - Status: Purple/Orange badge
   - Error alert with message
   - Button: "View Error"
   - Glow effect (orange border)

**CSS Classes**:
- `.agent-card-enhanced` - Root card
- `.agent-card__header` - Colored header
- `.agent-card__body` - Card content
- `.status-badge` - Status indicator
- `.message-badges` - Message counts
- `.scrollable-content` - Mission/task area
- `.priority-card` - Glow effect for errors

---

### 5. ChatHeadBadge.vue (Chat Head Component)
**Location**: `F:/GiljoAI_MCP/frontend/src/components/projects/ChatHeadBadge.vue`
**Lines**: 180 | **Status**: NEEDS FIX (size validator)

**Purpose**: Circular badge displaying agent identification

**Props**:
```javascript
agentType: String (required)
  // Valid: orchestrator, analyzer, implementor, researcher, reviewer, tester
instanceNumber: Number (default: 1)
size: String (default: 'default')
  // Current validator accepts: 'default', 'compact'
  // Needs to also accept: 'small'
```

**Badge Features**:
- Perfect circle (border-radius: 50%)
- Agent-specific color background
- 2px white border
- White bold text, centered
- Sizes:
  - default: 32px
  - compact: 24px
  - small: (currently invalid, needs fix)
- Badge IDs:
  - Instance 1: Or, An, Im, Re, Rv, Te
  - Instance 2+: O2, A2, I2, R2, Rv2, T2
- Hover effect: Scale 1.05, increased shadow

**CSS Classes**:
- `.chat-head-badge` - Root
- `.chat-head-badge--default` - 32px size
- `.chat-head-badge--compact` - 24px size
- `.chat-head-badge--orchestrator` - Tan color
- `.chat-head-badge--analyzer` - Red color
- `.chat-head-badge--implementor` - Blue color
- `.chat-head-badge--researcher` - Green color
- `.chat-head-badge--reviewer` - Purple color
- `.chat-head-badge--tester` - Orange color

**BUG #1 (NEEDS FIX)**:
Current validator on line 27 rejects size="small":
```javascript
// WRONG - only accepts 'default' or 'compact'
validator: (value) => ['default', 'compact'].includes(value)

// FIX - also accept 'small'
validator: (value) => ['default', 'small', 'compact'].includes(value)
```

---

### 6. MessageStream.vue (Message Display)
**Location**: `F:/GiljoAI_MCP/frontend/src/components/projects/MessageStream.vue`
**Lines**: 420+ | **Status**: NEEDS FIX (DOM mocking)

**Purpose**: Vertical scrolling message feed with auto-scroll

**Props**:
```javascript
messages: Array (required, default: [])
projectId: String (required)
autoScroll: Boolean (default: true)
loading: Boolean (default: false)
```

**Message Structure**:
```javascript
{
  id: String              // Unique ID
  from: String            // 'agent' | 'developer'
  from_agent: String      // Agent type (for chat head)
  to_agent: String | null // Recipient (null = broadcast)
  type: String            // 'agent' | 'broadcast' | 'user'
  content: String         // Message text
  timestamp: String       // ISO timestamp
  instance_number: Number // For I2, I3 badges
  status: String          // 'pending' | 'acknowledged'
}
```

**Key Features**:
- Auto-scroll to bottom on new messages
- Manual scroll override
- "Scroll to bottom" button with unread count
- Chat head badges for agent messages
- User avatar for user messages
- Relative timestamps ("2 min ago")
- Full timestamps on hover
- Empty state with helpful message
- Loading skeleton loaders
- Custom scrollbar styling
- Keyboard navigation (Home, End, PageUp, PageDown)

**CSS Classes**:
- `.message-stream` - Root container
- `.message-stream__header` - Header "Messages"
- `.message-stream__container` - Scrollable area
- `.message-stream__list` - Message list
- `.message-stream__message` - Individual message
- `.message-stream__chat-head` - Agent badge
- `.message-stream__user-icon` - User avatar
- `.message-stream__content` - Message content
- `.message-stream__routing` - "To [Agent]:" text
- `.message-stream__text` - Message body
- `.message-stream__timestamp` - Relative time
- `.message-stream__scroll-button` - Scroll indicator

**BUG #2 (NEEDS FIX)**:
Line 307 throws "container.scrollTo is not a function" in tests:
```javascript
// Line 307 - causes JSDOM error
container.scrollTo({
  top: container.scrollHeight,
  behavior: smooth ? 'smooth' : 'auto'
})

// FIX - add to test setup
Element.prototype.scrollTo = vi.fn()
window.scrollTo = vi.fn()
```

---

### 7. MessageInput.vue (Message Input Component)
**Location**: `F:/GiljoAI_MCP/frontend/src/components/projects/MessageInput.vue`
**Lines**: 240+ | **Status**: PRODUCTION READY

**Purpose**: Sticky message input at bottom of message stream

**Layout**:
```
┌──────────────────────────────────────────────────┐
│ [User Icon] [Textarea] [To ▼] [<Submit]          │
└──────────────────────────────────────────────────┘
```

**Props**:
```javascript
disabled: Boolean (default: false)
```

**Key Features**:
- User icon (left side)
- Auto-expanding textarea (1-8 rows)
- "To" dropdown (Orchestrator, Broadcast)
- Submit button (chevron-left icon)
- Keyboard shortcuts:
  - Enter to send
  - Shift+Enter for newline
- Disabled state support
- Mobile-responsive layout

**Emits**:
```javascript
emit('send', message, recipient)
```

**CSS Classes**:
- `.message-input` - Root
- `.message-input--disabled` - Disabled state
- `.message-input__container` - Flex container
- `.message-input__user-icon` - Left icon
- `.message-input__textarea` - Text input
- `.message-input__recipient` - To dropdown
- `.message-input__submit` - Submit button

---

### 8. LaunchPromptIcons.vue (Tool Icons)
**Location**: `F:/GiljoAI_MCP/frontend/src/components/projects/LaunchPromptIcons.vue`
**Lines**: 195+ | **Status**: PRODUCTION READY

**Purpose**: Display clickable icons for MCP tool integration (Claude Code, Codex, Gemini)

**Features**:
- 3 tool icons (Claude Code, Codex, Gemini)
- Tool-specific colors:
  - Claude Code: Orange (#E67E22)
  - Codex: Purple (#9B59B6)
  - Gemini: Blue (#3498DB)
- Click to copy MCP command to clipboard
- Toast notification shows copied command
- Keyboard accessible (Enter/Space)
- Hover effects

**Tools Configuration**:
```javascript
{
  claudeCode: {
    name: 'Claude Code',
    icon: 'mdi-code-braces-box',
    color: '#E67E22',
    command: 'claude-code mcp add'
  },
  codex: {
    name: 'Codex CLI',
    icon: 'mdi-application-brackets',
    color: '#9B59B6',
    command: 'codex mcp add'
  },
  gemini: {
    name: 'Gemini CLI',
    icon: 'mdi-star-four-points',
    color: '#3498DB',
    command: 'gemini mcp add'
  }
}
```

**CSS Classes**:
- `.launch-prompt-icons` - Container
- `.launch-prompt-icon` - Individual icon
- `.launch-prompt-icon--claudeCode` - Claude Code styling
- `.launch-prompt-icon--codex` - Codex styling
- `.launch-prompt-icon--gemini` - Gemini styling
- `.launch-prompt-icon__label` - Icon label text

---

## Configuration Files

### agentColors.js (Color Configuration)
**Location**: `F:/GiljoAI_MCP/frontend/src/config/agentColors.js`
**Lines**: 160+ | **Status**: PRODUCTION READY

**Purpose**: Centralized agent color configuration

**Exported Objects**:
```javascript
AGENT_COLORS = {
  orchestrator: { hex: '#D4A574', badge: 'Or', ... },
  analyzer: { hex: '#E74C3C', badge: 'An', ... },
  implementor: { hex: '#3498DB', badge: 'Im', ... },
  researcher: { hex: '#27AE60', badge: 'Re', ... },
  reviewer: { hex: '#9B59B6', badge: 'Rv', ... },
  tester: { hex: '#E67E22', badge: 'Te', ... }
}

AGENT_STATUS_COLORS = {
  waiting: { color: '#90A4AE', label: 'Waiting' },
  working: { color: '#3498DB', label: 'Working' },
  complete: { color: '#FFC300', label: 'Complete' },
  failure: { color: '#C6298C', label: 'Failure' },
  blocked: { color: '#E67E22', label: 'Blocked' }
}

LAUNCH_PROMPT_TOOLS = {
  claudeCode: { ... },
  codex: { ... },
  gemini: { ... }
}
```

**Exported Functions**:
```javascript
getAgentColor(agentType)      // Get color object
getAgentBadgeId(type, num)    // Get badge ID (Or, I2, I3)
darkenColor(hex, percent)     // Darken for headers
lightenColor(hex, percent)    // Lighten for borders
getAllAgentColors()           // Get all colors as array
```

---

## Store Files

### projectTabs.js (State Management)
**Location**: `F:/GiljoAI_MCP/frontend/src/stores/projectTabs.js`
**Lines**: 380+ | **Status**: PRODUCTION READY

**Purpose**: Pinia store managing project tabs state

**State**:
```javascript
{
  activeTab: 'launch',              // 'launch' | 'jobs'
  currentProject: null,             // Active project object
  agents: [],                       // Agent list
  orchestratorMission: '',          // Mission text
  messages: [],                     // Message list
  isStaging: false,                 // Staging flag
  isLaunched: false,                // Launched flag
  loading: false,
  error: null
}
```

**Getters**:
```javascript
isLaunchTab             // activeTab === 'launch'
isJobsTab              // activeTab === 'jobs'
sortedAgents           // Agents sorted by priority
orchestrator           // Find orchestrator agent
agentsByStatus(status) // Filter by status
agentCount             // Total agents
agentInstances         // Group by type
unreadMessages         // Filter pending
unreadCount            // Count pending
messagesByAgent(id)    // Filter by agent
allAgentsComplete      // All status === 'complete'
readyToLaunch          // Can launch
```

**Actions**:
```javascript
// Tab Navigation
switchTab(tabName)

// Project Management
setProject(project)
clearProject()

// Staging Workflow
stageProject()         // Call orchestrator
launchJobs()          // Launch agents, auto-switch
cancelStaging()       // Reset everything
resetStaging()        // Local reset

// Mission Management
setMission(mission)
updateMission(text)

// Agent Management
addAgent(agent)
updateAgent(id, updates)
removeAgent(id)
clearAgents()
acknowledgeAgent(id)  // Mark active
completeAgent(id)
failAgent(id, error)

// Message Management
addMessage(message)
sendMessage(content, recipient)
acknowledgeMessage(id)

// Closeout
closeoutProject()

// WebSocket Handlers
handleAgentUpdate(data)
handleMessageUpdate(data)
handleProjectUpdate(data)
```

---

## Style Files

### agent-colors.scss (Color Variables)
**Location**: `F:/GiljoAI_MCP/frontend/src/styles/agent-colors.scss`

**CSS Variables**:
```scss
:root {
  --agent-orchestrator-primary: #D4A574;
  --agent-orchestrator-dark: #B8905E;
  --agent-orchestrator-light: #E5C9A3;

  --agent-analyzer-primary: #E74C3C;
  --agent-analyzer-dark: #C0392B;
  --agent-analyzer-light: #F1948A;

  // ... (and 4 more agents)
}
```

---

## Test Files

### JobsTab.spec.js (Component Tests)
**Location**: `F:/GiljoAI_MCP/frontend/src/components/projects/JobsTab.spec.js`
**Tests**: 98 passing | **Status**: ALL PASSING

**Test Categories**:
- Component Rendering (7 tests)
- Agent Sorting Priority (5 tests)
- Instance Number Calculation (3 tests)
- Orchestrator Detection (2 tests)
- Event Emissions (6 tests)
- Message Handling (4 tests)
- Layout and Responsive Design (4 tests)
- Scroll Indicators (1 test)

### JobsTab.a11y.spec.js (Accessibility Tests)
**Location**: `F:/GiljoAI_MCP/frontend/src/components/projects/JobsTab.a11y.spec.js`
**Tests**: 28 passing | **Status**: ALL PASSING

**Test Categories**:
- ARIA Labels and Roles (7 tests)
- Keyboard Navigation (7 tests)
- Focus Management (3 tests)
- Screen Reader Support (3 tests)
- Error Message Accessibility (3 tests)
- Semantic HTML Structure (5 tests)
- And more...

### JobsTab.integration.spec.js (Integration Tests)
**Location**: `F:/GiljoAI_MCP/frontend/src/components/projects/JobsTab.integration.spec.js`
**Tests**: 3 failing | **Status**: NEEDS DOM MOCKING FIX

**Issues**:
- container.scrollTo() not available in JSDOM
- Needs Element.prototype.scrollTo = vi.fn() in setup

---

## Color Reference

### Agent Colors (Exact Hex Codes)
```
Orchestrator: #D4A574  (Tan/Beige)
Analyzer:     #E74C3C  (Red)
Implementor:  #3498DB  (Blue)
Researcher:   #27AE60  (Green)
Reviewer:     #9B59B6  (Purple)
Tester:       #E67E22  (Orange)
```

### Status Badge Colors
```
Waiting:  #90A4AE  (Gray)
Working:  #3498DB  (Blue)
Complete: #FFC300  (Gold)
Failure:  #C6298C  (Magenta/Purple)
Blocked:  #E67E22  (Orange)
```

### Tool Icon Colors
```
Claude Code: #E67E22  (Orange)
Codex:       #9B59B6  (Purple)
Gemini:      #3498DB  (Blue)
```

---

## Known Issues & Fixes

### Issue 1: ChatHeadBadge size="small"
**File**: `frontend/src/components/projects/ChatHeadBadge.vue` line 27
**Fix**: Add 'small' to validator array

### Issue 2: MessageStream scrollTo()
**File**: `frontend/src/components/projects/MessageStream.vue` line 307
**Fix**: Mock in test setup or use scrollBy()

### Issue 3: v-skeleton-loader
**File**: `frontend/src/components/projects/MessageStream.vue` line 49
**Fix**: Check Vuetify import or use fallback

---

## Quick Commands

```bash
# Run all component tests
cd F:/GiljoAI_MCP/frontend
npm test -- --run src/components/projects

# Run only JobsTab tests
npm test -- --run JobsTab.spec.js

# Run only accessibility tests
npm test -- --run JobsTab.a11y.spec.js

# Run dev server
npm run dev

# Build for production
npm run build
```

---

**Generated**: October 30, 2025
**Version**: 1.0
