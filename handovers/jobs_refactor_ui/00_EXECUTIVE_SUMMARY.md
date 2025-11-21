# Jobs Page UI Refactor - Executive Summary

**Document ID**: jobs_refactor_ui
**Created**: 2025-11-21
**Status**: Planning Phase
**Priority**: High

---

## Overview

This document outlines a complete visual and functional refactor of the GiljoAI Jobs/Launch page, transitioning from a single-page panel layout to a sophisticated tabbed interface with dual operational modes, real-time agent status tracking, and comprehensive message queue visualization.

---

## Strategic Goals

1. **Simplify User Workflow**: Guide users through staging → launching → monitoring in a clear, tab-based progression
2. **Support Two CLI Modes**: Enable both Claude Code CLI (subagent mode) and General CLI (multi-terminal mode)
3. **Enhance Visibility**: Provide real-time status tracking with message queue visibility
4. **Improve User Control**: Allow users to monitor, message, and coordinate agents effectively
5. **Future-Proof Design**: Build extensible components for future enhancements

---

## Current State (What We're Moving Away From)

**Page 1 of PDF - Old Design:**

```
┌─────────────────────────────────────────────────────────┐
│  [Launch] [Implementation] Tabs                         │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌─────────────────┐  ┌────────────┐│
│  │ STAGE        │  │ PROJECT         │  │ ORCHESTRATOR│
│  │ PROJECT      │  │ DESCRIPTION     │  │ MISSION    ││
│  │              │  │                 │  │            ││
│  │ [Button]     │  │ (static text)   │  │ (appears   ││
│  │              │  │                 │  │  later)    ││
│  └──────────────┘  └─────────────────┘  └────────────┘│
│                                                         │
│  Agent Team (1 AGENT)                                  │
│  ┌─────────────────────┐                               │
│  │  [Or] Orchestrator  │                               │
│  │  No mission assigned│                               │
│  │  [EDIT MISSION]     │                               │
│  └─────────────────────┘                               │
└─────────────────────────────────────────────────────────┘
```

**Problems:**
- Single-page layout becomes cluttered
- No clear workflow progression
- Limited agent status visibility
- No message queue visibility
- No support for different CLI modes
- Static, non-interactive interface

---

## New Design (What We're Moving Toward)

### Tab-Based Architecture

**Two Main Tabs:**
1. **Launch Tab** - Project staging and agent assignment
2. **Implementation Tab** - Agent execution and monitoring (STATUS BOARD)

### Launch Tab Features

```
┌─────────────────────────────────────────────────────────────────┐
│  Project: {project_name}                                        │
│  Project ID: {full_UUID}                                        │
│  ┌─────────┬──────────────┐                                    │
│  │ Launch  │ Implementation│  ← Tab Navigation                 │
│  └─────────┴──────────────┘                                    │
│                                                                 │
│  [Stage project]                    Status: Waiting/Working/    │
│                                            Completed!           │
│  ┌──────────────┬────────────────────┬─────────────────┐      │
│  │ Project      │ Orchestrator       │ Default agent   │      │
│  │ Description  │ Generated Mission  │                 │      │
│  │              │                    │  [Or] Orchestr. │      │
│  │ (editable)   │ (populated after   │                 │      │
│  │ [✎]          │  staging)          │  Agent Team     │      │
│  │              │ (scrollable)       │  [An] Analyzer  │      │
│  │ (scrollable) │                    │  [Im] Implement │      │
│  │              │                    │  [Te] Tester    │      │
│  │              │                    │  (with info/    │      │
│  │              │                    │   edit icons)   │      │
│  └──────────────┴────────────────────┴─────────────────┘      │
│                                                                 │
│                                    [Launch Jobs] ← Activates    │
│                                                   after staging │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Tab - STATUS BOARD

**Two Operational Modes:**

#### Mode 1: Claude Code CLI Mode (Red Banner)
- **One terminal** - Only orchestrator needs prompt
- Other agents are **subagents** within Claude Code CLI
- Simplified user experience for Claude Code users

#### Mode 2: General CLI Mode (Green Banner)
- **Individual terminals** - Each agent needs separate prompt
- Supports multi-terminal workflows
- Full manual control

**Status Board Table:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Claude Subagents: [●] ON (Claude Code CLI) / OFF (General)    │
├─────────────────────────────────────────────────────────────────┤
│ Agent  │Agent    │Agent   │Job  │Job  │Msgs│Msgs│Msgs│Actions │
│ Type   │ID       │Status  │Read │Ack  │Sent│Wait│Read│        │
├────────┼─────────┼────────┼─────┼─────┼────┼────┼────┼────────┤
│[Or]Orch│{uuid}   │Working │ ✓   │ ✓   │ 4  │ 1  │    │▶ 🗂 ℹ │
│[An]Anal│{uuid}   │Waiting │     │     │    │ 1  │    │▶ 🗂 ℹ │
│[Im]Impl│{uuid}   │Waiting │     │     │    │ 1  │    │▶ 🗂 ℹ │
│[Te]Test│{uuid}   │Waiting │     │     │    │ 1  │    │▶ 🗂 ℹ │
└─────────────────────────────────────────────────────────────────┘
│                                                                 │
│  [Message Orchestrator ▼] [Broadcast] [Message field] [➤Send] │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Functional Changes

### 1. Workflow Progression

**Old:** Single-page, unclear progression
**New:** Clear three-stage workflow

1. **Stage** (Launch Tab) - Define project and generate missions
2. **Launch** (Launch Tab → Implementation Tab) - Activate jobs
3. **Monitor** (Implementation Tab) - Track and coordinate agents

### 2. Agent Status Tracking

**New statuses required (NOT in current code):**
- `Waiting.` - Agent has mission but not started
- `Working.` - Agent is actively processing
- `Working...` - Agent is in extended processing
- `Completed!` - Agent finished successfully

### 3. Message Queue Visibility

**New features:**
- **Messages Sent** - Count of messages agent has sent
- **Messages Waiting** - Count of unread messages for agent
- **Messages Read** - Count of messages agent has read
- **Job Read** - Checkmark when agent reads job assignment
- **Job Acknowledged** - Checkmark when agent acknowledges job

### 4. CLI Mode Toggle

**Claude Code CLI Mode (Toggle ON):**
- Single prompt for orchestrator only
- Subagents managed internally by Claude Code
- Simpler UX for Claude Code users

**General CLI Mode (Toggle OFF):**
- Individual prompts for each agent
- Each agent runs in separate terminal
- Full manual control

### 5. Interactive Elements

**Launch Tab:**
- Edit icon for Project Description
- Info icons for agent templates (read-only view)
- Edit icons for agent missions (editable)
- Stage project button (copies prompt)
- Launch Jobs button (activates after staging)

**Implementation Tab:**
- Play button (copies agent-specific prompt)
- Refresh/sync icon (re-copy prompt)
- Message folder icon (view message history)
- Info icon (view agent template)
- Message dropdown (select recipient)
- Broadcast button (send to all agents)
- Send button (send message)

---

## Technical Requirements Summary

### Frontend (Vue 3 + Vuetify)

**New Components Needed:**
1. `TabNavigation.vue` - Launch/Implementation tabs
2. `LaunchPanel.vue` - Three-column launch layout
3. `StatusBoard.vue` - Agent status table
4. `AgentRow.vue` - Individual agent row in status board
5. `MessageQueue.vue` - Message sending interface
6. `CLIModeToggle.vue` - Toggle between CLI modes
7. `AgentStatusBadge.vue` - Status indicator component

**Modified Components:**
- `ProjectView.vue` - Main container for new tab system
- `AgentCard.vue` - Update for new Launch tab display
- `JobManagement.vue` - Integrate with new status board

### Backend (FastAPI)

**New API Endpoints:**
```
POST   /api/projects/{project_id}/stage
POST   /api/projects/{project_id}/launch-jobs
GET    /api/agents/{agent_id}/messages
POST   /api/agents/{agent_id}/messages
POST   /api/agents/broadcast
GET    /api/agents/{agent_id}/prompt
PATCH  /api/agents/{agent_id}/status
```

**New Database Fields:**
```sql
-- mcp_agent_jobs table additions
job_read BOOLEAN DEFAULT FALSE
job_acknowledged BOOLEAN DEFAULT FALSE
messages_sent INTEGER DEFAULT 0
messages_waiting INTEGER DEFAULT 0
messages_read INTEGER DEFAULT 0

-- New table: agent_messages
CREATE TABLE agent_messages (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES mcp_projects(id),
    from_agent_id UUID REFERENCES mcp_agent_jobs(id),
    to_agent_id UUID REFERENCES mcp_agent_jobs(id),
    message_type VARCHAR(20), -- 'direct', 'broadcast'
    content TEXT,
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    read_at TIMESTAMP
);
```

### WebSocket Events

**New real-time events:**
```javascript
'agent:status_changed'
'agent:job_read'
'agent:job_acknowledged'
'agent:message_sent'
'agent:message_received'
'project:stage_completed'
'project:jobs_launched'
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- Create tab navigation structure
- Build Launch tab layout (three columns)
- Implement "Stage project" workflow
- Backend: Add staging endpoint

### Phase 2: Status Board (Week 2)
- Build Implementation tab structure
- Create status board table component
- Implement CLI mode toggle
- Add agent status tracking
- Backend: New status fields and endpoints

### Phase 3: Message Queue (Week 3)
- Build message sending interface
- Implement message history viewing
- Add broadcast functionality
- Backend: Message queue system

### Phase 4: Agent Launch (Week 4)
- Implement "Launch Jobs" button
- Build prompt copying mechanism (both modes)
- Add real-time status updates
- WebSocket integration

### Phase 5: Polish & Testing (Week 5)
- UI/UX refinements
- Error handling
- End-to-end testing
- Documentation

---

## Success Metrics

1. **User Experience**
   - Reduced clicks to launch agents (from 5+ to 2-3)
   - Clear visual progression through workflow
   - Real-time status visibility without page refresh

2. **Technical**
   - <100ms response time for status updates
   - WebSocket connection stability >99%
   - Support for 10+ concurrent agents

3. **Functionality**
   - Both CLI modes working correctly
   - Message queue with <1s delivery time
   - Accurate agent status tracking

---

## Risk Mitigation

**Risk 1: Breaking existing functionality**
- **Mitigation**: Feature flag to toggle between old/new UI
- **Testing**: Comprehensive regression testing

**Risk 2: WebSocket performance with many agents**
- **Mitigation**: Implement message batching, debouncing
- **Testing**: Load testing with 20+ agents

**Risk 3: User confusion with two CLI modes**
- **Mitigation**: Clear labels, help tooltips, documentation
- **Testing**: User acceptance testing

---

## Next Steps

1. Review this executive summary with stakeholders
2. Deep dive into component-level specifications (see detailed docs)
3. Create UI mockups/prototypes in Figma
4. Set up feature branch: `feature/jobs-page-refactor`
5. Begin Phase 1 implementation

---

## Related Documents

- `01_DESIGN_COMPARISON.md` - Detailed current vs. new design analysis
- `02_COMPONENT_BREAKDOWN.md` - Component-level specifications
- `03_DATA_FLOW.md` - State management and data flow
- `04_API_SPECIFICATIONS.md` - Backend API changes
- `05_IMPLEMENTATION_ROADMAP.md` - Detailed phase breakdown
- `06_TESTING_STRATEGY.md` - Testing approach and scenarios

---

**Document Version**: 1.0
**Last Updated**: 2025-11-21
