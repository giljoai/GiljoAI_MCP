# Handover 0086: Stage Project WebSocket Visualization Integration

**Date**: 2025-11-02
**Status**: Ready for Implementation
**Priority**: High
**Complexity**: Medium
**Related**: Handover 0079 (Orchestrator Prompt Generation), Handover 0020 (Orchestrator Enhancement), Handover 0019 (Agent Job Management)

---

## Executive Summary

Implements real-time dashboard visualization for the "Stage Project" workflow. Currently, when the orchestrator generates missions and selects agents via MCP tools (called from Claude Code/Codex/Gemini CLI), the GiljoAI dashboard never receives updates - mission panels stay empty and agent cards never appear. This handover adds WebSocket event emission to MCP tools and frontend listeners to enable real-time UI updates while preserving the manual CLI workflow.

**Problem**: Orchestrator works externally → MCP tools update database → Dashboard stays empty
**Solution**: MCP tools emit WebSocket events → Frontend listens → Dashboard updates in real-time
**Impact**: Users see mission plans and agent assignments populate as orchestrator works

---

## Problem Statement

### The Gap Discovered

**What EXISTS:**
- ✅ Backend: `/api/orchestration/launch` endpoint (full orchestration)
- ✅ Backend: MCP tools `update_project_mission()` and `create_agent_job_external()`
- ✅ Frontend: Mission panel + Agent cards in LaunchTab.vue
- ✅ Infrastructure: WebSocket system (websocket_manager.py)

**What's MISSING:**
- ❌ WebSocket events when MCP tools update database
- ❌ Frontend listeners for mission/agent updates
- ❌ Real-time UI updates when orchestrator reports back

### Current Broken Flow

```
1. User clicks "Stage Project" button
2. Orchestrator prompt copied to clipboard (2000-line instructions)
3. User pastes into Claude Code terminal
4. Orchestrator executes externally:
   a. Calls get_product(), get_vision(), get_context() (context discovery)
   b. Generates condensed mission via MissionPlanner
   c. Selects agents via AgentSelector
   d. Calls update_project_mission(project_id, mission) ✅ Database updated
   e. Calls create_agent_job_external(project_id, agent_type) ✅ Database updated
5. ❌ Frontend NEVER knows this happened
6. ❌ Mission panel stays empty
7. ❌ Agent cards never appear
8. ❌ "Stage Project" button never transitions to "Launch Jobs"
```

### The Vision (Simple_Vision.md lines 186-196)

From the product vision:

> "The first thing the orchestrator does is builds out the mission which populates in the screen for the user to see and review and continues to assign agents, based on the active agent templates in the application."

> "The Mission field in the Project launch window populates with the mission and Agent cards start showing up which the orchestrator has started selecting. The user reviews everything and can choose to cancel or to proceed."

**Expected flow**: User sees mission + agents populate in real-time as orchestrator works externally.

---

## Solution Design

### Architecture Decision: Preserve Manual CLI Workflow + Add Real-Time Visualization

**Principles:**
1. ✅ **No workflow changes** - Orchestrator still runs in external CLI tools (Claude Code, Codex, Gemini)
2. ✅ **MCP tools unchanged** - Only add WebSocket emission (non-breaking)
3. ✅ **Frontend enhancement** - Add listeners for real-time updates
4. ✅ **Backward compatible** - WebSocket events are additive

### WebSocket Event Flow

```
External CLI Tool (Claude Code)
    ↓
Orchestrator calls MCP tools
    ↓
update_project_mission(project_id, mission)
    ├─→ Database: UPDATE mcp_projects SET mission = ...
    └─→ WebSocket: EMIT project:mission_updated
            ↓
    Frontend LaunchTab.vue listener
            ↓
    Mission panel populates (real-time)
    ↓
create_agent_job_external(project_id, agent_type)
    ├─→ Database: INSERT INTO mcp_agent_jobs
    └─→ WebSocket: EMIT agent:created
            ↓
    Frontend LaunchTab.vue listener
            ↓
    Agent card appears (real-time)
```

---

## Implementation Details

### Phase 1: Backend - MCP Tool WebSocket Emission

#### File 1: `src/giljo_mcp/tools/project.py`

**Location**: `update_project_mission()` function (line 316+)

**Add WebSocket emission after database update:**

```python
from api.websocket_manager import websocket_manager
from datetime import datetime

async def update_project_mission(project_id: int, mission: str) -> Dict[str, Any]:
    """
    Update the mission field for a project.

    Args:
        project_id: ID of the project to update
        mission: New mission text

    Returns:
        Dict with success status and updated project data
    """
    session = SessionLocal()
    try:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            return {"success": False, "error": "Project not found"}

        # Update mission
        project.mission = mission
        session.commit()

        # 🆕 NEW: Emit WebSocket event for real-time UI update
        await websocket_manager.broadcast_to_tenant(
            project.tenant_key,
            {
                'type': 'project:mission_updated',
                'project_id': project_id,
                'mission': mission,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

        return {
            "success": True,
            "project_id": project_id,
            "mission": mission
        }
    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()
```

**Why this works:**
- `websocket_manager` is a singleton (already initialized in API server)
- `broadcast_to_tenant()` ensures multi-tenant isolation
- Event only sent to users in same tenant as project

#### File 2: `src/giljo_mcp/tools/agent_coordination_external.py`

**Location**: `create_agent_job_external()` function (line 324+)

**Add WebSocket emission after agent creation:**

```python
from api.websocket_manager import websocket_manager
from datetime import datetime

async def create_agent_job_external(
    project_id: int,
    agent_type: str,
    priority: int = 5
) -> Dict[str, Any]:
    """
    Create an agent job for external CLI tool execution.

    Args:
        project_id: ID of the project
        agent_type: Type of agent (orchestrator, implementer, etc.)
        priority: Job priority (1-10)

    Returns:
        Dict with success status and agent job data
    """
    session = SessionLocal()
    try:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            return {"success": False, "error": "Project not found"}

        # Create agent job
        agent_job = AgentJob(
            project_id=project_id,
            tenant_key=project.tenant_key,
            agent_type=agent_type,
            status='waiting',
            priority=priority,
            created_at=datetime.utcnow()
        )
        session.add(agent_job)
        session.commit()

        # Serialize agent data
        agent_data = {
            'id': agent_job.id,
            'agent_type': agent_type,
            'status': 'waiting',
            'priority': priority,
            'created_at': agent_job.created_at.isoformat()
        }

        # 🆕 NEW: Emit WebSocket event for real-time UI update
        await websocket_manager.broadcast_to_tenant(
            project.tenant_key,
            {
                'type': 'agent:created',
                'project_id': project_id,
                'agent': agent_data,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

        return {
            "success": True,
            "agent_job_id": agent_job.id,
            "agent": agent_data
        }
    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()
```

---

### Phase 2: Frontend - WebSocket Listeners

#### File 3: `frontend/src/components/projects/LaunchTab.vue`

**Location**: `onMounted()` lifecycle hook

**Add WebSocket listeners for real-time updates:**

```javascript
import { onMounted, onUnmounted } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'

// Inside setup()
const { socket } = useWebSocket()

onMounted(() => {
  // Listen for mission updates
  socket.on('project:mission_updated', handleMissionUpdate)

  // Listen for agent creation
  socket.on('agent:created', handleAgentCreated)
})

onUnmounted(() => {
  // Clean up listeners
  socket.off('project:mission_updated', handleMissionUpdate)
  socket.off('agent:created', handleAgentCreated)
})

// Handler for mission updates
const handleMissionUpdate = (data) => {
  console.log('Mission update received:', data)

  // Verify this event is for the current project
  if (data.project_id !== props.project.id) return

  // Update mission text (reactive)
  missionText.value = data.mission

  // Update UI state
  stagingInProgress.value = false
  readyToLaunch.value = true

  // Show success notification
  notify({
    type: 'success',
    title: 'Mission Generated',
    message: 'Orchestrator has generated the project mission'
  })
}

// Handler for agent creation
const handleAgentCreated = (data) => {
  console.log('Agent created:', data)

  // Verify this event is for the current project
  if (data.project_id !== props.project.id) return

  // Add agent to list (reactive)
  agents.value.push(data.agent)

  // Update token budget counter
  updateTokenBudget()

  // Show notification
  notify({
    type: 'info',
    title: 'Agent Selected',
    message: `${data.agent.agent_type} agent assigned to project`
  })
}

// Helper: Update token budget based on mission + agent count
const updateTokenBudget = () => {
  const missionTokens = estimateTokens(missionText.value)
  const agentTokens = agents.value.length * 2000 // Estimate 2K tokens per agent
  tokenBudget.value = missionTokens + agentTokens
}

const estimateTokens = (text) => {
  // Rough estimate: 1 token ≈ 4 characters
  return Math.ceil(text.length / 4)
}
```

**Why this works:**
- WebSocket listeners are scoped to component lifecycle
- `onUnmounted()` cleanup prevents memory leaks
- `data.project_id` check ensures events only update correct project
- Reactive values (`missionText.value`, `agents.value`) trigger UI updates automatically

---

### Phase 3: Fix Store Bug

#### File 4: `frontend/src/stores/projectTabs.js`

**Location**: `stageProject()` function (lines 161-186)

**Current bug:**
```javascript
// ❌ WRONG - These fields don't exist in response
this.orchestratorMission = response.data.prompt
this.agents = response.data.agents || []
```

**Fix:**
```javascript
async stageProject(projectId) {
  try {
    const response = await api.prompts.staging(projectId)

    if (!response.data?.prompt) {
      throw new Error('Invalid response from staging endpoint')
    }

    // Copy orchestrator prompt to clipboard
    await navigator.clipboard.writeText(response.data.prompt)

    // Update state
    this.stagingInProgress = true
    this.stagedProjectId = projectId

    // ✅ FIXED: Don't expect mission/agents from endpoint
    // Mission and agents will populate via WebSocket events
    // when orchestrator calls MCP tools externally

    return { success: true }
  } catch (error) {
    console.error('Stage project error:', error)
    return { success: false, error: error.message }
  }
}
```

**Why this fix is needed:**
- `/api/orchestration/launch` endpoint only returns `{ prompt: "..." }`
- Mission and agents don't exist yet (orchestrator hasn't run)
- They populate later via WebSocket when orchestrator calls MCP tools

---

## Serena Integration Considerations

### Future Enhancement: Serena Agent Detection

**Location**: `src/giljo_mcp/agent_selector.py`

**Potential addition** (not in this handover scope):

```python
def select_agents_for_mission(mission: str, tenant_key: str) -> List[str]:
    """Select agents based on mission requirements"""

    # Get active templates
    templates = get_active_templates(tenant_key)

    # Check if Serena is enabled
    settings = get_tenant_settings(tenant_key)
    if settings.serena_enabled:
        # Add Serena agent with appropriate tools
        templates.append({
            'agent_type': 'serena',
            'description': 'Code navigation and symbol manipulation',
            'tools': ['find_symbol', 'replace_symbol', 'search_pattern']
        })

    # Existing selection logic...
    return selected_agents
```

**Why defer this:**
- Serena integration is a separate feature
- This handover focuses on visualization only
- Can be added later via separate handover

---

## Testing Strategy

### Manual Testing Flow

**Setup:**
1. Fresh project created in dashboard
2. Project activated (status = 'active')
3. WebSocket connection established (check browser DevTools Network tab)

**Test Sequence:**

1. **Click "Stage Project" button**
   - ✅ Verify prompt copied to clipboard
   - ✅ Verify console shows "Staging in progress..."
   - ✅ Verify button shows loading state

2. **Paste prompt into Claude Code terminal**
   - ✅ Verify orchestrator starts execution
   - ✅ Verify MCP connection established (Claude Code shows "Connected to GiljoAI MCP")

3. **Orchestrator calls `update_project_mission()`**
   - ✅ Verify mission text appears in dashboard Mission panel (< 2 sec latency)
   - ✅ Verify "Stage Project" button transitions to "Launch Jobs"
   - ✅ Verify notification: "Mission Generated"
   - ✅ Verify token counter updates

4. **Orchestrator calls `create_agent_job_external()` (multiple times)**
   - ✅ Verify agent cards appear in real-time as each agent is created
   - ✅ Verify agent status shows "waiting"
   - ✅ Verify token counter increases with each agent
   - ✅ Verify notifications: "Agent Selected" for each agent

5. **Multi-tenant isolation test**
   - ✅ Open two browser sessions (different tenants)
   - ✅ Stage project in Tenant A
   - ✅ Verify Tenant B dashboard does NOT update
   - ✅ Verify WebSocket events are tenant-scoped

6. **Network interruption test**
   - ✅ Disconnect network mid-staging
   - ✅ Verify graceful reconnection when network restores
   - ✅ Verify missed events are NOT duplicated

7. **Error handling test**
   - ✅ Orchestrator fails mid-execution
   - ✅ Verify partial results (mission + some agents) still display
   - ✅ Verify no UI crash

### Edge Cases

**Large Mission Text:**
- Mission > 10,000 characters
- Verify UI doesn't freeze
- Verify token budget warning appears if budget > 150K tokens

**Many Agents:**
- 10+ agents selected
- Verify all agent cards render
- Verify scroll behavior works
- Verify token budget warning

**Concurrent Users:**
- 2+ users on same tenant staging different projects
- Verify events route to correct project tabs
- Verify no cross-project contamination

**Old Data:**
- User refreshes page after staging
- Verify mission + agents load from database (not just WebSocket)
- Verify state consistency

---

## Files Modified

### Backend Files

**File**: `src/giljo_mcp/tools/project.py`
- **Line 316+**: Add WebSocket emission in `update_project_mission()`
- **Imports**: Add `from api.websocket_manager import websocket_manager`
- **Changes**: ~10 lines added

**File**: `src/giljo_mcp/tools/agent_coordination_external.py`
- **Line 324+**: Add WebSocket emission in `create_agent_job_external()`
- **Imports**: Add `from api.websocket_manager import websocket_manager`
- **Changes**: ~15 lines added

### Frontend Files

**File**: `frontend/src/components/projects/LaunchTab.vue`
- **Section**: `onMounted()` lifecycle hook
- **Changes**: Add WebSocket listeners for `project:mission_updated` and `agent:created`
- **Functions**: Add `handleMissionUpdate()`, `handleAgentCreated()`, `updateTokenBudget()`
- **Changes**: ~60 lines added

**File**: `frontend/src/stores/projectTabs.js`
- **Lines 161-186**: Fix `stageProject()` field assignment bug
- **Changes**: Remove incorrect field assignments, add comments
- **Changes**: ~5 lines modified

---

## Backward Compatibility

✅ **No breaking changes:**
- MCP tools signatures unchanged (only add WebSocket emission)
- WebSocket events are additive (non-listening clients unaffected)
- Manual CLI workflow preserved
- Existing `/api/orchestration/launch` endpoint untouched
- Database schema unchanged

✅ **Graceful degradation:**
- If WebSocket disconnected → Data still saved to database
- If frontend not listening → Orchestrator still works
- If user refreshes page → Data loads from database

✅ **Multi-tenant isolation preserved:**
- `broadcast_to_tenant()` ensures tenant scoping
- No cross-tenant event leakage

---

## Success Criteria

After implementation, the following must be true:

- [x] Mission panel populates when orchestrator calls `update_project_mission()`
- [x] Agent cards appear when orchestrator calls `create_agent_job_external()`
- [x] UI updates happen in real-time (< 2 second latency)
- [x] "Stage Project" button transitions to "Launch Jobs" when mission ready
- [x] Token budget counter updates correctly as agents are added
- [x] Multi-tenant WebSocket isolation maintained (no cross-tenant events)
- [x] Manual CLI workflow unchanged (no user-facing workflow changes)
- [x] Browser console shows WebSocket events (for debugging)
- [x] Notifications appear for mission/agent updates
- [x] Page refresh loads mission + agents from database (state persistence)

---

## Related Handovers

- **Handover 0079**: Orchestrator Prompt Generation System (generates 2000-line prompt)
- **Handover 0020**: Orchestrator Enhancement (70% token reduction via MissionPlanner)
- **Handover 0019**: Agent Job Management System (agent lifecycle management)
- **Handover 0069**: Native MCP Integration (Claude Code, Codex, Gemini CLI)
- **Simple_Vision.md**: Product vision (lines 186-196, 337-340)

---

## Next Steps

### Implementation Order

1. **Backend WebSocket emission** (Phase 1)
   - Implement `project.py` WebSocket event
   - Implement `agent_coordination_external.py` WebSocket event
   - Test with Postman/manual MCP calls

2. **Frontend WebSocket listeners** (Phase 2)
   - Add listeners in LaunchTab.vue
   - Add handler functions
   - Test with mock WebSocket events

3. **Fix store bug** (Phase 3)
   - Update `projectTabs.js` stageProject()
   - Remove incorrect field assignments
   - Test staging workflow end-to-end

4. **Manual testing** (Phase 4)
   - Test full staging flow with Claude Code
   - Test multi-tenant isolation
   - Test error scenarios
   - Test network interruption

5. **Documentation updates** (Phase 5 - if needed)
   - Update user guide if UI behavior changes significantly
   - Add WebSocket event documentation for developers

---

## Rollback Plan

**If issues arise:**

1. **Backend rollback**: Remove WebSocket emission lines
   - MCP tools still work (just no real-time updates)
   - Users must manually refresh dashboard

2. **Frontend rollback**: Remove WebSocket listeners
   - Dashboard shows static state until refresh
   - No crash risk (listeners are additive)

3. **Store rollback**: Revert `projectTabs.js` changes
   - Staging still works (prompt copied to clipboard)
   - Just restores original bug (harmless)

**Zero risk:**
- No database schema changes
- No API signature changes
- No breaking changes to MCP protocol
- Manual workflow always functional

---

## Architecture Benefits

### User Experience
- ✅ **Real-time visibility**: See orchestrator work in real-time
- ✅ **Confidence building**: Mission + agents appear as orchestrator works
- ✅ **No manual refresh**: Dashboard auto-updates via WebSocket
- ✅ **Clear progress**: Visual feedback (mission populated, agents appearing)

### Technical Quality
- ✅ **Event-driven**: Clean separation between MCP tools and UI updates
- ✅ **Multi-tenant isolation**: `broadcast_to_tenant()` ensures security
- ✅ **Scalable**: WebSocket handles 100+ concurrent users efficiently
- ✅ **Maintainable**: Minimal code changes (~90 lines total)

### Developer Experience
- ✅ **Preserves manual workflow**: No changes to CLI tool usage
- ✅ **Backward compatible**: Non-breaking changes only
- ✅ **Easy to test**: WebSocket events easy to mock/simulate
- ✅ **Observable**: Browser DevTools shows WebSocket traffic

### Business Impact
- ✅ **Fulfills vision**: Implements Simple_Vision.md specification
- ✅ **Professional UX**: Real-time updates match modern app expectations
- ✅ **Reduces confusion**: Users no longer wonder "is it working?"
- ✅ **Supports documentation**: Easy to create screenshots/videos of staging flow

---

## Security Considerations

**Multi-Tenant Isolation:**
- ✅ `websocket_manager.broadcast_to_tenant()` enforces tenant boundaries
- ✅ `data.project_id` check in frontend prevents cross-project updates
- ✅ No PII in WebSocket events (only IDs and status)

**Authentication:**
- ✅ WebSocket connection requires valid JWT token
- ✅ Tenant key derived from authenticated user
- ✅ MCP tools already enforce tenant isolation in database queries

**Rate Limiting:**
- ✅ WebSocket events are append-only (no delete/modify)
- ✅ Orchestrator generates finite number of events (1 mission + N agents)
- ✅ No user input in WebSocket payload (XSS safe)

---

## Performance Considerations

**WebSocket Overhead:**
- Mission update: ~1-5 KB per event (mission text)
- Agent creation: ~500 bytes per event
- Total staging flow: ~10-20 KB for typical project (1 mission + 6 agents)

**Database Impact:**
- Zero additional queries (WebSocket emission happens after DB write)
- No N+1 query risk
- No transaction blocking

**Frontend Rendering:**
- Reactive framework handles incremental updates efficiently
- Agent cards render as they arrive (no batch wait)
- Token counter recalculates on each agent (< 1ms computation)

---

## Summary

Handover 0086 implements real-time dashboard visualization for the "Stage Project" workflow by adding WebSocket event emission to MCP tools and frontend listeners. This enables users to see mission plans and agent assignments populate in real-time as the orchestrator works in external CLI tools (Claude Code, Codex, Gemini CLI), fulfilling the product vision from Simple_Vision.md.

**Impact**: Transforms "Stage Project" from a black-box operation (paste prompt → wait → manually refresh) into a transparent, real-time process (paste prompt → watch mission appear → watch agents populate → review → launch). Users gain confidence and visibility without workflow changes.

**Implementation effort**: ~90 lines of code across 4 files, zero breaking changes, zero database migrations, backward compatible.

**Status**: Ready for implementation.
