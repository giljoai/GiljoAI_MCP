---
**⚠️ ARCHIVED: SUPERSEDED BY 0243 SERIES (2025-11-27)**

This handover has been **archived** as its objectives were accomplished through the 0243 Nicepage GUI Redesign series:
- 0243a-f: Complete Nicepage conversion with pixel-perfect design match
- JobsTab dynamic status fix (0243c)
- Agent action buttons implemented (0243d)
- Message center tab fix (0243e)
- 27+ E2E tests added (0243f)

**Original Status**: Was deferred to 0515, but 0243 series accomplished the core goals.
**Archive Reason**: Superseded by more comprehensive implementation in 0243 series.

---

**⚠️ CRITICAL UPDATE (2025-11-12): DEFERRED TO HANDOVER 0515**

This handover has been **reorganized** into the 0500 series remediation project:

**New Scope**: Part of Handover 0515 - Frontend Consolidation (Jobs Tab UI)
**Parent Project**: Projectplan_500.md
**Status**: Deferred until after critical remediation (Handovers 0500-0514 complete)

**Reason**: The refactoring (Handovers 0120-0130) left 23 critical implementation gaps that must be fixed BEFORE proceeding with UI harmonization. Jobs tab needs functional foundation first. See:
- **Investigation Reports**: Products, Projects, Settings, Orchestration breakage
- **Master Plan**: `handovers/Projectplan_500.md`
- **New Handover**: `handovers/0515_frontend_consolidation.md` (includes Jobs tab harmonization)

**Original scope below** (preserved for historical reference):

---

**Handover ID:** 0114
**Title:** Jobs Tab UI/UX Harmonization with Visual Design Spec
**Date:** 2025-01-07
**Status:** Deferred - See Handover 0515
**Priority:** High (after 0500-0514)
**Complexity:** Medium
**Estimated Effort:** 2 weeks
**Related Handovers:**
- 0113 (Unified Agent State System)
- 0073 (Static Agent Grid)
- 0107 (Agent Monitoring & Cancellation)
- 0105 (Claude Code Subagent Toggle)
- 0109 (Execution Prompt Dialog)

**Design Reference:** `F:\GiljoAI_MCP\handovers\Launch-Jobs_panels version 2.pdf`

---

## 1. Executive Summary

### Current State
The Jobs tab has a basic implementation with:
- Agent cards displayed horizontally with scroll functionality
- "Use Claude Code Subagents" toggle (Handover 0105)
- Basic status badges (waiting, working, complete, failed, blocked)
- Message Center panel on the right side
- "Launch Agent" buttons for waiting agents
- Execution prompt dialog (Handover 0109)

### Desired State
Full implementation per PDF design specification (9 slides) with:
- Dual-mode operation: "Staging" vs "Jobs" tabs
- Orchestrator-specific UI with comprehensive status tracking
- 3-column layout: Jobs | Orchestrator | Message Center
- Advanced styling with gradients, shadows, and visual hierarchy
- Real-time progress indicators and contextual actions
- Harmonized with Overall Theme Concept

## 2. Visual Design Specifications

### 2.1 Page Structure (Slide 1)
**THREE TABS** at top of page:
1. **Staging** - Pre-launch configuration
2. **Jobs** - Active job monitoring
3. **Message Center** - Communication hub

### 2.2 Overall Theme Concept (Slide 2)
- **Color Palette:**
  - Primary: Teal gradient (`#00BFA5` to `#00695C`)
  - Accent: Orange (`#FF6F00`)
  - Background: Light gray (`#F5F5F5`)
  - Cards: White with subtle shadows

- **Typography:**
  - Headers: Bold, 18-20px
  - Body: Regular, 14-16px
  - Status text: Semi-bold, 14px

- **Visual Effects:**
  - Rounded corners (8px for cards, 4px for buttons)
  - Drop shadows for depth
  - Gradient overlays for headers
  - Smooth transitions (300ms ease)

### 2.3 Staging Tab (Slide 3-4)

#### Pre-Launch State
**Left Panel - Jobs List:**
- Agent cards in vertical list
- Each card shows: Name, Type, Status ("Ready")
- Light teal background for ready agents
- "Configure" button on each card

**Center Panel - Orchestrator:**
- Large card with "Orchestrator Configuration"
- Mission statement text area (editable)
- Token count indicator
- "Auto-generate Mission" button
- "Validate Configuration" button

**Right Panel - Message Center:**
- Empty state: "No messages yet"
- Ready to receive pre-launch validations

#### Launch Ready State
**Visual Changes:**
- All agent cards show green checkmarks
- Orchestrator card has "Ready to Launch" banner
- Large "LAUNCH PROJECT" button appears (orange, prominent)
- Message Center shows validation confirmations

### 2.4 Jobs Tab - Active State (Slides 5-7)

#### Layout Structure
**Left Panel (40% width) - Agent Jobs:**
- Vertical scrollable list of agent cards
- Each card contains:
  - Agent name and type
  - Status badge (colored by state)
  - Progress bar (if working)
  - Last activity timestamp
  - Action buttons (contextual)

**Center Panel (35% width) - Orchestrator:**
- **Header Section:**
  - "Orchestrator" title with status indicator
  - Project name and ID
  - Elapsed time counter

- **Status Section:**
  - Current phase indicator
  - Progress visualization (circular or linear)
  - Token usage meter
  - Active agent count

- **Activity Feed:**
  - Real-time log of orchestrator decisions
  - Agent spawn events
  - Coordination messages
  - Phase transitions

**Right Panel (25% width) - Message Center:**
- Tab selector: All | Urgent | Errors | Info
- Message list with:
  - Sender avatar/icon
  - Message preview
  - Timestamp
  - Read/unread indicator
- Message count badges on tabs

#### Agent Status States (Slide 6)
**Visual Treatment per State:**

1. **Waiting** (Light Blue)
   - Pulsing border animation
   - "Waiting for orchestrator" text
   - No action buttons

2. **Working** (Green)
   - Animated progress bar
   - "Working on: [task]" text
   - "View Details" button

3. **Complete** (Dark Green)
   - Checkmark icon
   - "Completed at [time]" text
   - "View Results" button

4. **Failed** (Red)
   - Error icon
   - Error message preview
   - "Retry" and "View Error" buttons

5. **Blocked** (Orange)
   - Warning icon
   - Blocking reason
   - "Resolve" button

6. **Cancelled** (Gray)
   - Strikethrough effect
   - "Cancelled by [user/system]" text
   - "View Reason" button

### 2.5 Project Completion State (Slide 8)

**Victory Screen Elements:**
- Large success banner across top
- Confetti animation (optional)
- Summary statistics:
  - Total agents used
  - Tasks completed
  - Time elapsed
  - Tokens consumed

**Orchestrator Panel:**
- "Project Complete" badge
- Final summary generated
- "Generate Report" button
- "Archive Project" button

**Agent Cards:**
- All showing complete/cancelled states
- Dimmed appearance
- Results accessible via buttons

### 2.6 Message Center Details (Slide 9)

**Message Types & Styling:**
1. **Error Messages** (Red accent)
   - Red icon
   - Bold title
   - Stack trace collapsible

2. **Warnings** (Orange accent)
   - Orange icon
   - Medium weight title
   - Suggestion text included

3. **Info Messages** (Blue accent)
   - Blue icon
   - Regular weight
   - Contextual information

4. **Success Messages** (Green accent)
   - Green checkmark
   - Completion confirmations
   - Result summaries

**Interactive Features:**
- Click to expand full message
- "Mark as Read" on hover
- "Reply" button for bidirectional messages
- "Clear All" for bulk operations

## 3. Technical Implementation Requirements

### 3.1 Component Architecture

```
JobsView.vue (Parent)
├── StagingTab.vue
│   ├── AgentConfigList.vue
│   ├── OrchestratorConfig.vue
│   └── LaunchControls.vue
├── JobsTab.vue
│   ├── AgentJobsList.vue
│   │   └── AgentJobCard.vue
│   ├── OrchestratorPanel.vue
│   │   ├── OrchestratorStatus.vue
│   │   └── ActivityFeed.vue
│   └── MessageCenter.vue
│       ├── MessageTabs.vue
│       └── MessageList.vue
└── CompletionOverlay.vue
```

### 3.2 State Management

**Vuex Store Modules:**
```javascript
// stores/jobs.js
{
  staging: {
    agents: [],
    orchestratorConfig: {},
    validationStatus: {},
    launchReady: false
  },
  active: {
    agents: Map(), // agent_id -> agent state
    orchestrator: {
      status: '',
      phase: '',
      tokensUsed: 0,
      startTime: null,
      activity: []
    },
    messages: {
      all: [],
      unreadCount: 0,
      filters: {}
    }
  },
  completion: {
    isComplete: false,
    summary: {},
    stats: {}
  }
}
```

### 3.3 WebSocket Events

**Required Event Subscriptions:**
```javascript
// Real-time updates
socket.on('agent_status_change', updateAgentCard)
socket.on('orchestrator_update', updateOrchestratorPanel)
socket.on('new_message', addToMessageCenter)
socket.on('project_complete', showCompletionScreen)
socket.on('progress_update', updateProgressBars)
socket.on('token_usage', updateTokenMeters)
```

### 3.4 API Endpoints

**New/Modified Endpoints:**
```python
# Staging endpoints
GET  /api/projects/{id}/staging/status
POST /api/projects/{id}/staging/validate
POST /api/projects/{id}/staging/configure-agent
POST /api/projects/{id}/staging/auto-generate-mission

# Active job endpoints
GET  /api/projects/{id}/jobs/summary
GET  /api/projects/{id}/orchestrator/activity
POST /api/projects/{id}/jobs/{job_id}/action
GET  /api/projects/{id}/completion/report

# Message endpoints
GET  /api/messages?project_id={id}&type={type}
POST /api/messages/{id}/mark-read
POST /api/messages/mark-all-read
```

### 3.5 Styling Framework

**Vuetify Theming:**
```javascript
// vuetify.config.js
theme: {
  themes: {
    light: {
      primary: '#00BFA5',
      secondary: '#00695C',
      accent: '#FF6F00',
      error: '#F44336',
      warning: '#FF9800',
      info: '#2196F3',
      success: '#4CAF50',
      background: '#F5F5F5'
    }
  }
}
```

**Custom CSS Classes:**
```scss
// styles/jobs.scss
.agent-card {
  &--waiting { border-left: 4px solid #2196F3; }
  &--working { border-left: 4px solid #4CAF50; }
  &--complete { border-left: 4px solid #00695C; }
  &--failed { border-left: 4px solid #F44336; }
  &--blocked { border-left: 4px solid #FF9800; }

  &__progress {
    background: linear-gradient(90deg, #00BFA5 0%, #00695C 100%);
  }
}

.orchestrator-panel {
  background: linear-gradient(135deg, #00BFA5 0%, #00695C 100%);

  &__meter {
    stroke: #FF6F00;
    stroke-dasharray: var(--progress) 100;
  }
}
```

### 3.6 Animations & Transitions

```javascript
// animations.js
export const animations = {
  pulseWaiting: {
    animation: 'pulse 2s ease-in-out infinite'
  },
  slideInAgent: {
    animation: 'slideInLeft 0.3s ease-out'
  },
  fadeInMessage: {
    animation: 'fadeIn 0.2s ease-out'
  },
  progressBar: {
    transition: 'width 0.5s ease-out'
  },
  statusChange: {
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
  }
}
```

## 4. Implementation Plan

### Phase 1: Component Structure (Week 1)
1. Create component hierarchy per architecture
2. Set up Vuex store modules
3. Implement routing between tabs
4. Basic layout with panels

### Phase 2: Staging Tab (Days 3-4)
1. Agent configuration cards
2. Orchestrator configuration panel
3. Validation logic
4. Launch readiness checks
5. Auto-generate mission feature

### Phase 3: Jobs Tab - Core (Days 5-7)
1. Agent job cards with all states
2. Real-time status updates
3. Progress indicators
4. Action buttons per state
5. WebSocket integration

### Phase 4: Orchestrator Panel (Days 8-9)
1. Status visualization
2. Activity feed
3. Token usage meter
4. Phase progression
5. Real-time updates

### Phase 5: Message Center (Days 10-11)
1. Message categorization
2. Tab filtering
3. Read/unread states
4. Bulk operations
5. Real-time message arrival

### Phase 6: Visual Polish (Days 12-13)
1. Apply color palette
2. Implement gradients and shadows
3. Add animations and transitions
4. Responsive design adjustments
5. Cross-browser testing

### Phase 7: Completion State (Day 14)
1. Victory screen
2. Summary statistics
3. Report generation
4. Project archival
5. User feedback collection

## 5. Testing Requirements

### 5.1 Unit Tests
- Component isolation tests
- Store mutation tests
- Action handler tests
- Computed property tests

### 5.2 Integration Tests
- Tab navigation flow
- WebSocket event handling
- API endpoint integration
- State synchronization

### 5.3 E2E Tests
- Complete project lifecycle
- Error handling scenarios
- Message filtering
- Agent state transitions

### 5.4 Visual Regression Tests
- Screenshot comparisons with design spec
- Responsive breakpoints
- Animation smoothness
- Color accuracy

## 6. Success Criteria

1. **Pixel-Perfect Design Match**
   - Implementation matches PDF specification
   - All 9 slides represented in UI

2. **Real-time Performance**
   - Updates within 100ms of WebSocket event
   - Smooth animations (60 fps)
   - No UI blocking during updates

3. **State Consistency**
   - Agent states always synchronized
   - Message counts accurate
   - Progress indicators precise

4. **User Experience**
   - Intuitive tab navigation
   - Clear visual hierarchy
   - Responsive to user actions
   - Accessible (WCAG 2.1 AA)

5. **Code Quality**
   - 90% test coverage
   - Component reusability
   - Clear documentation
   - Performance optimized

## 7. Dependencies and Risks

### Dependencies
- Completion of Handover 0113 (Unified Agent State System)
- WebSocket infrastructure stable
- API endpoints implemented
- Vuetify 3.x features

### Risks
1. **Performance with Many Agents**
   - Mitigation: Virtual scrolling for large lists

2. **WebSocket Connection Loss**
   - Mitigation: Reconnection logic with state recovery

3. **Design Complexity**
   - Mitigation: Incremental implementation with user feedback

4. **State Synchronization**
   - Mitigation: Single source of truth in Vuex

## 8. Post-Implementation

### Documentation
1. User guide for new UI
2. Component API documentation
3. State management guide
4. Troubleshooting guide

### Monitoring
1. Error tracking for UI exceptions
2. Performance metrics (render times)
3. User interaction analytics
4. WebSocket connection stability

### Future Enhancements
1. Drag-and-drop agent reordering
2. Custom theme configuration
3. Keyboard shortcuts
4. Export functionality for reports
5. Mobile responsive design

---

## Appendix A: Design Reference

The complete visual design specification is available in:
`F:\GiljoAI_MCP\handovers\Launch-Jobs_panels version 2.pdf`

This PDF contains 9 slides with detailed mockups and annotations for each UI state.

## Appendix B: Related Handovers

- **0113**: Unified Agent State System - Provides state management foundation
- **0073**: Static Agent Grid - Original grid concept (evolved to list view)
- **0107**: Agent Monitoring & Cancellation - Cancel functionality integration
- **0105**: Claude Code Subagent Toggle - Toggle feature already implemented
- **0109**: Execution Prompt Dialog - Dialog system in place

---

**End of Handover 0114**