# Technical Debt Summary - GiljoAI MCP

**Created**: 2025-10-22
**Purpose**: Track implementation gaps between documented handovers and actual codebase state
**Priority**: HIGH - User-facing features missing despite backend readiness

---

## Executive Summary

Multiple handover projects show as "Not Started" in documentation but are actually complete, while others marked "Complete" have no implementation. This creates confusion and hides critical gaps in user-facing features.

**Key Finding**: Backend orchestration is 90% complete but users cannot see or control it through the UI.

---

## 1. Documentation vs Reality Mismatches

### Completed But Documented as "Not Started"

| Handover | Title | Actual Status | Evidence |
|----------|-------|---------------|----------|
| **0019** | Agent Job Management | ✅ COMPLETE | `AgentJobManager`, `JobCoordinator`, `AgentCommunicationQueue` exist with 90%+ test coverage |
| **0020** | Orchestrator Enhancement | ✅ COMPLETE | `ProjectOrchestrator` (915 lines), context prioritization working |
| **0023** | Password Reset PIN | ✅ COMPLETE | Recovery PIN system implemented, tests passing |
| **0024** | Two-Layout Auth Pattern | ✅ COMPLETE | `AuthLayout.vue`, `DefaultLayout.vue` exist and working |
| **0025-0029** | Admin Settings Refactor | ✅ COMPLETE | All tabs redesigned, tests exist |

### Marked "Complete" But Not Implemented

| Handover | Title | Actual Status | Missing Components |
|----------|-------|---------------|-------------------|
| **0037-0038** | MCP Slash Commands | ❌ NOT DONE | No `.claude/commands/`, no slash command handlers |

---

## 2. Critical Implementation Gaps

### Gap 1: Dashboard Agent Monitoring (Handover 0021)
**Status**: NOT IMPLEMENTED
**Impact**: HIGH - Users cannot see agent activities
**Effort**: 2-3 days

**What Exists**:
- ✅ Backend: Complete agent job system with WebSocket events
- ✅ API: 13 REST endpoints for agent jobs
- ✅ WebSocket: Events for `job:status_changed`, `job:completed`, `job:failed`

**What's Missing**:
- ❌ `AgentMonitor.vue` component
- ❌ `AgentJobCard.vue` component
- ❌ Real-time job status updates in UI
- ❌ Message flow visualization
- ❌ Token usage tracking display
- ❌ Agent control buttons (terminate, message)

**Current Dashboard Has**:
```
frontend/src/components/
├── dashboard/
│   ├── DashboardView.vue (basic stats only)
│   ├── SubAgentTree.vue (hierarchy view)
│   └── SubAgentTimelineHorizontal.vue (timeline)
└── messages/
    └── MessagesView.vue (basic message list)
```

**Needs Integration With**:
- Existing `MessagesView.vue` component
- WebSocket connection for real-time updates
- Agent job lifecycle management

---

### Gap 2: MCP Slash Commands (Handover 0038)
**Status**: NOT IMPLEMENTED despite completion docs
**Impact**: MEDIUM - Power users cannot automate workflows
**Effort**: 1-2 days

**What Should Exist**:
```
.claude/
├── commands/
│   ├── project-setup.md
│   ├── agent-spawn.md
│   └── workflow-run.md
└── agents/ (this exists)
```

**Integration Points**:
- MCP tool registration
- Command parsing
- Workflow automation triggers

---

## 3. Component Harmonization Needs

### Current Component Structure

**Dashboard Components** (`frontend/src/components/dashboard/`):
- `DashboardView.vue` - Main dashboard container
- `SubAgentTree.vue` - Agent hierarchy visualization
- `SubAgentTimelineHorizontal.vue` - Timeline view
- Basic statistics cards (Projects, Agents, Messages, Tasks)

**Message Components** (`frontend/src/components/messages/`):
- `MessagesView.vue` - Message list and viewing
- Basic message filtering
- No agent job context

### Harmonization Requirements

1. **Unified Agent Job View**:
   - Dashboard needs to show active agent jobs
   - Messages need to be linked to agent jobs
   - Both should share WebSocket connection for updates

2. **Shared State Management**:
   - Agent jobs state should be accessible by both dashboard and messages
   - Consider Vuex/Pinia store for agent job management
   - Real-time updates should flow to all components

3. **Visual Consistency**:
   - Agent job cards in dashboard
   - Agent indicators in message view
   - Consistent status colors and icons

---

## 4. Implementation Roadmap

### Phase 1: Foundation (1 day)
- [ ] Create shared agent job store (Vuex/Pinia)
- [ ] Establish WebSocket connection manager
- [ ] Define agent job data models in frontend

### Phase 2: Dashboard Integration (2 days)
- [ ] Create `AgentMonitor.vue` component
- [ ] Create `AgentJobCard.vue` component
- [ ] Integrate with existing `DashboardView.vue`
- [ ] Connect WebSocket events to UI updates

### Phase 3: Message Integration (1 day)
- [ ] Link messages to agent jobs in `MessagesView.vue`
- [ ] Add agent job context to message display
- [ ] Show agent type and status with messages

### Phase 4: MCP Slash Commands (1-2 days)
- [ ] Create `.claude/commands/` directory structure
- [ ] Implement command handlers
- [ ] Test workflow automation

### Phase 5: Testing & Polish (1 day)
- [ ] Integration tests for agent monitoring
- [ ] WebSocket event testing
- [ ] UI/UX polish and accessibility

---

## 5. Technical Decisions Needed

### Question 1: State Management
**Options**:
- Use Vuex (if already in project)
- Add Pinia (modern Vue state management)
- Keep local component state with event bus

### Question 2: WebSocket Architecture
**Options**:
- Single WebSocket connection shared across components
- Multiple connections per component
- WebSocket manager service

### Question 3: Dashboard Layout
**Options**:
- Replace current basic stats with agent job cards
- Add new tab for agent monitoring
- Split screen with stats + active jobs

### Question 4: Message-Agent Relationship
**Options**:
- Messages as children of agent jobs
- Messages with agent job tags
- Separate views linked by job ID

---

## 6. Risk Assessment

### High Risk
- **User Blindness**: Users cannot see what agents are doing (Gap 1)
- **No Automation**: Power users cannot create workflows (Gap 2)

### Medium Risk
- **Documentation Confusion**: Mismatch between docs and reality
- **Component Coupling**: Dashboard and messages need careful integration

### Low Risk
- **Backend Stability**: Agent job system is well-tested (90%+ coverage)
- **API Completeness**: All needed endpoints exist

---

## 7. Success Metrics

1. **Visibility**: Users can see all active agent jobs in real-time
2. **Control**: Users can message and terminate agent jobs from UI
3. **Integration**: Messages show agent context
4. **Automation**: Slash commands enable 3-step workflows
5. **Performance**: Real-time updates with <100ms latency

---

## 8. Next Steps

1. **Immediate**: Review this document and make architectural decisions
2. **Day 1**: Set up state management and WebSocket infrastructure
3. **Day 2-3**: Implement dashboard agent monitoring
4. **Day 4**: Integrate with message view
5. **Day 5-6**: Add MCP slash commands
6. **Day 7**: Testing and polish

---

## Appendix: File Locations

### Backend (Working)
- `src/giljo_mcp/agent_job_manager.py` - Job lifecycle
- `src/giljo_mcp/job_coordinator.py` - Job coordination
- `src/giljo_mcp/agent_communication_queue.py` - Messaging
- `api/endpoints/agent_jobs.py` - REST API
- `api/websocket/events.py` - WebSocket events

### Frontend (Needs Work)
- `frontend/src/components/dashboard/` - Dashboard components
- `frontend/src/components/messages/` - Message components
- `frontend/src/stores/` - State management (if exists)
- `frontend/src/services/websocket.js` - WebSocket service

### Missing
- `frontend/src/components/agents/` - Agent monitoring components
- `.claude/commands/` - MCP slash commands
---

## 9. UI Architecture Technical Debt

### Issue: Nested `<v-window>` Components Theme Inheritance

**Date Added**: 2025-10-24
**Priority**: MEDIUM
**Effort**: 2-3 days

**Problem**:
Multiple pages use nested `<v-window>` components which fail to inherit theme correctly from parent. When user toggles dark/light mode, nested windows remain in default theme (light), causing theme inconsistencies.

**Affected Components**:
- `frontend/src/views/UserSettings.vue` - Main tabs contain sub-tabs (Templates tab)
- `frontend/src/views/DashboardView.vue` - Main tabs contain sub-tabs (Timeline/Hierarchy/Metrics)
- Any future components with nested `<v-window>` structures

**Current Workaround** (Applied):
- Explicitly pass `:theme="theme.global.name.value"` prop to all nested `<v-window>` components
- Quick fix but doesn't solve architectural issue

**Root Cause**:
Vuetify's `<v-window>` component doesn't properly propagate theme to nested instances. This is a known Vuetify limitation with double-nested windows.

**Proper Solution** (Tech Debt to Address):
**Option C: Flatten nested window architecture**

Replace nested `<v-window>` with one of:

1. **Route-based rendering** (Recommended):
   ```
   /settings → UserSettings.vue (main tabs)
   /settings/templates → TemplateManager.vue (full page)
   /settings/api → ApiSettings.vue (full page)
   ```
   - Single-level tabs at each route
   - Clean URL structure
   - No nesting issues
   - Better deep linking

2. **Conditional rendering with v-show**:
   ```vue
   <v-card v-show="activeSubTab === 'timeline'">...</v-card>
   <v-card v-show="activeSubTab === 'hierarchy'">...</v-card>
   ```
   - No `<v-window>` nesting
   - All content in DOM (may impact performance)
   - Simpler state management

3. **Component-based rendering**:
   ```vue
   <component :is="currentSubTabComponent" />
   ```
   - Dynamic component loading
   - Clean separation
   - Better code organization

**Benefits of Flattening**:
- Eliminates theme inheritance issues
- Improves performance (no nested reactivity)
- Cleaner component structure
- Better accessibility (simpler DOM)
- Easier to maintain

**Implementation Roadmap**:
1. **Audit**: Identify all nested `<v-window>` instances (2-3 components)
2. **Design**: Choose flattening strategy per component (route vs v-show)
3. **Refactor**: Update components one-by-one
4. **Test**: Ensure theme switching works correctly
5. **Remove**: Delete `:theme` workaround props

**Risk**: LOW - Changes are localized to specific components
**Testing**: Theme toggle on all affected pages in both light/dark modes


### add agent core behaviour context free txt field.
this field should be used to tune the agent philosophy and behaviour , and should be injected into the agent templates.

Cuch as Read, Comitt, code test yadda yaddda.
