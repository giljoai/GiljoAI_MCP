# Handover 0358: WebSocket & UI State Overhaul

**Status**: PENDING
**Date**: 2025-12-19
**Priority**: CRITICAL
**Estimated Effort**: 10-14 hours

---

## Executive Summary

Alpha trial revealed critical WebSocket and UI state synchronization issues that severely impact user experience. The dashboard shows stale data after page refresh, UI buttons disappear unexpectedly, and duplicate orchestrators can be spawned due to missing idempotency checks. This handover documents a comprehensive overhaul of the WebSocket event system, frontend state management, and backend orchestrator spawning logic to ensure production-grade reliability.

**Root Cause**: WebSocket events are ephemeral (not persisted), frontend relies on REST API for initial state, and lacks catch-up mechanism on reconnection. The `allAgentsComplete` computed property drives UI visibility but doesn't persist state across page reloads.

**Impact**:
- Users lose visibility into project progress on page refresh
- "Closeout Project" button disappears after refresh (even when all agents complete)
- Duplicate orchestrators can spawn if user refreshes during staging (CONFIRMED BUG)
- Message counters and agent status appear stale until WebSocket event arrives

---

## Problem Statement

### Issue #4: WebSocket/UI State Regression
**Symptom**: Dashboard shows stale data after page refresh. Agent status, message counters, and progress indicators do not reflect current state until a new WebSocket event arrives.

**Root Cause**:
- Frontend state stored in Pinia stores (`agentJobs.js`, `projects.js`, `messages.js`)
- WebSocket events update state via `updateAgent()` mutations
- Events are NOT persisted - no re-emission on page load
- Initial state fetched via REST API (`/api/projects/{id}/jobs`)
- Race conditions between REST fetch and WebSocket subscription

### Issue #6: "Closeout Project" Button Disappears on Refresh
**Symptom**: When all agents complete, "Closeout Project" button appears. After page refresh, button disappears despite agents still being complete.

**Root Cause**:
```javascript
// frontend/src/components/projects/ProjectTabs.vue line 266-271
const showCloseoutButton = computed(() => {
  if (!store.allAgentsComplete) return false

  const orchestrator = store.sortedAgents?.find((a) => a.agent_type === 'orchestrator')
  return Boolean(orchestrator && orchestrator.status === 'complete')
})
```

The `store.allAgentsComplete` computed property depends on agent status in Pinia store. On page refresh:
1. Store resets to empty state
2. REST API fetches agents
3. If REST response is stale or timing is off, `allAgentsComplete` evaluates false
4. Button never appears until next WebSocket event

### Issue #7: Duplicate Orchestrator on Refresh
**Symptom**: Refreshing page during staging spawns duplicate orchestrator jobs.

**Root Cause**:
```python
# src/giljo_mcp/services/project_service.py line 1689-1739
async def launch_project(self, project_id, user_id=None, launch_config=None, websocket_manager=None):
    # Fetch project
    project = await session.execute(select(Project).where(...))

    # Activate project if not already active
    if project.status != "active":
        activate_result = await self.activate_project(project_id, ...)

    # NO CHECK FOR EXISTING ACTIVE ORCHESTRATOR
    # Directly creates new orchestrator job via ThinClientPromptGenerator
```

The `launch_project()` method does NOT check if an orchestrator already exists for the project. It unconditionally creates a new orchestrator job, leading to duplicates.

---

## Investigation Findings

### Current Architecture

#### WebSocket Event Flow
```
Backend Event → WebSocketManager.broadcast() → All Connected Clients
                                                   ↓
Frontend WebSocket Handler → Pinia Store Mutation → Component Re-render
```

**Events Emitted**:
- `agent:created` - New agent job spawned
- `agent:status_changed` - Agent status updated
- `job:mission_acknowledged` - Agent acknowledged mission
- `message:received` - Message sent to agent
- `message:acknowledged` - Message acknowledged by agent
- `project:updated` - Project status/mission changed

**Problem**: Events are fire-and-forget. No persistence, no replay on reconnect.

#### Frontend State Management

**Stores Involved**:
- `agentJobs.js` - Agent job table state (filters, sorting, agents array)
- `projects.js` - Project lifecycle state
- `messages.js` - Agent messaging state
- `websocket.js` - WebSocket connection management

**State Initialization**:
```javascript
// frontend/src/components/projects/JobsTab.vue
onMounted(async () => {
  // 1. Subscribe to WebSocket
  subscribeToProject(props.project.id)

  // 2. Fetch initial state via REST
  const response = await api.get(`/api/projects/${props.project.id}/jobs`)
  store.setAgents(response.data.rows)
})
```

**Race Condition**: WebSocket event may arrive BEFORE REST response completes, causing state to be overwritten by stale REST data.

#### Backend Orchestrator Spawning

**Current Flow** (`launch_project()` in `project_service.py`):
1. Fetch project
2. Activate if not active
3. Fetch user config (field priorities, depth config)
4. Generate orchestrator mission via `ThinClientPromptGenerator`
5. Create `MCPAgentJob` record
6. Emit WebSocket `agent:created` event

**Missing**: Idempotency check to prevent duplicate orchestrators.

---

## Implementation Plan

### Phase 1: Backend - Event Persistence & Catch-Up

**Goal**: Persist WebSocket events to database and provide catch-up mechanism on reconnect.

#### 1.1 Create Event Log Table
```sql
-- migrations/0358_websocket_event_log.sql
CREATE TABLE websocket_event_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_key TEXT NOT NULL,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL, -- 'project', 'agent', 'message'
    entity_id TEXT NOT NULL,
    event_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_tenant_entity (tenant_key, entity_type, entity_id, created_at DESC)
);
```

**Retention Policy**: Keep events for 7 days, auto-purge via scheduled task.

#### 1.2 Update WebSocket Manager
```python
# src/giljo_mcp/websocket/manager.py
class WebSocketManager:
    async def broadcast_agent_created(self, job_id, agent_type, tenant_key, ...):
        # Existing broadcast logic
        await self._broadcast_to_tenant(tenant_key, event_type, data)

        # NEW: Persist event to log
        await self._persist_event(
            tenant_key=tenant_key,
            event_type="agent:created",
            entity_type="agent",
            entity_id=job_id,
            event_data={...}
        )

    async def get_missed_events(self, tenant_key, entity_type, entity_id, since):
        """Fetch events since last seen timestamp for catch-up."""
        # Query websocket_event_log
        # Return events ordered by created_at ASC
```

#### 1.3 Add Catch-Up Endpoint
```python
# api/endpoints/websocket.py
@router.get("/events/catch-up")
async def get_catch_up_events(
    entity_type: str,  # 'project', 'agent'
    entity_id: str,
    since: datetime,
    current_user: User = Depends(get_current_active_user),
):
    """Return missed events since 'since' timestamp."""
    events = await websocket_manager.get_missed_events(
        tenant_key=current_user.tenant_key,
        entity_type=entity_type,
        entity_id=entity_id,
        since=since
    )
    return {"events": events}
```

### Phase 2: Backend - Orchestrator Idempotency

**Goal**: Prevent duplicate orchestrators via "get or create" pattern.

#### 2.1 Add Idempotency Check to `launch_project()`
```python
# src/giljo_mcp/services/project_service.py line 1689
async def launch_project(self, project_id, user_id=None, launch_config=None, websocket_manager=None):
    async with self._get_session() as session:
        # Fetch project
        project = await session.execute(...)

        # NEW: Check for existing active orchestrator
        existing_orchestrator = await session.execute(
            select(MCPAgentJob).where(
                and_(
                    MCPAgentJob.project_id == project_id,
                    MCPAgentJob.agent_type == "orchestrator",
                    MCPAgentJob.status.in_(["preparing", "waiting", "working", "review"]),
                    MCPAgentJob.tenant_key == self.tenant_manager.get_current_tenant()
                )
            )
        ).scalar_one_or_none()

        if existing_orchestrator:
            self._logger.info(f"Orchestrator already exists for project {project_id}: {existing_orchestrator.job_id}")
            return {
                "success": True,
                "data": {
                    "project_id": project_id,
                    "orchestrator_job_id": existing_orchestrator.job_id,
                    "launch_prompt": existing_orchestrator.mission,  # Return existing mission
                    "status": project.status,
                    "message": "Orchestrator already active for this project"
                }
            }

        # Proceed with orchestrator creation...
```

#### 2.2 Add Integration Test
```python
# tests/integration/test_orchestrator_idempotency.py
async def test_launch_project_prevents_duplicate_orchestrators(db_session):
    """Verify launch_project() returns existing orchestrator if active."""
    # 1. Launch project (creates orchestrator)
    result1 = await project_service.launch_project(project_id)
    orchestrator_id_1 = result1["data"]["orchestrator_job_id"]

    # 2. Launch again (should return same orchestrator)
    result2 = await project_service.launch_project(project_id)
    orchestrator_id_2 = result2["data"]["orchestrator_job_id"]

    # 3. Verify same orchestrator returned
    assert orchestrator_id_1 == orchestrator_id_2
    assert result2["data"]["message"] == "Orchestrator already active for this project"

    # 4. Verify only ONE orchestrator in database
    orchestrators = await db_session.execute(
        select(MCPAgentJob).where(
            MCPAgentJob.project_id == project_id,
            MCPAgentJob.agent_type == "orchestrator"
        )
    )
    assert len(orchestrators.all()) == 1
```

### Phase 3: Frontend - State Synchronization Strategy

**Goal**: Implement hybrid approach: REST for initial load, WebSocket for updates, catch-up on reconnect.

#### 3.1 Update WebSocket Composable
```javascript
// frontend/src/composables/useWebSocket.js
export function useWebSocketV2() {
  const store = useWebSocketStore()

  // NEW: Catch-up on reconnect
  async function catchUpEvents(entityType, entityId) {
    const lastSeenTimestamp = localStorage.getItem(`ws_last_seen_${entityType}_${entityId}`)
    if (!lastSeenTimestamp) return

    try {
      const response = await api.get('/api/websocket/events/catch-up', {
        params: {
          entity_type: entityType,
          entity_id: entityId,
          since: lastSeenTimestamp
        }
      })

      // Replay missed events
      response.data.events.forEach(event => {
        store.handleEvent(event.event_type, event.event_data)
      })

      // Update last seen
      localStorage.setItem(`ws_last_seen_${entityType}_${entityId}`, new Date().toISOString())
    } catch (error) {
      console.error('Catch-up failed:', error)
    }
  }

  // Auto catch-up on subscribe
  function subscribe(entityType, entityId) {
    const key = store.subscribe(entityType, entityId)

    // NEW: Trigger catch-up after subscription
    nextTick(() => catchUpEvents(entityType, entityId))

    return key
  }

  return { subscribe, catchUpEvents, ... }
}
```

#### 3.2 Centralize State in Pinia Store
```javascript
// frontend/src/stores/agentJobs.js
export const useAgentJobsStore = defineStore('agentJobs', () => {
  const agents = ref([])

  // NEW: Computed eligibility for closeout (persist in localStorage)
  const closeoutEligible = computed(() => {
    const allComplete = agents.value.every(a => a.status === 'complete')
    const orchestratorComplete = agents.value.find(
      a => a.agent_type === 'orchestrator' && a.status === 'complete'
    )

    const eligible = allComplete && Boolean(orchestratorComplete)

    // Persist to localStorage for page refresh
    localStorage.setItem(
      `closeout_eligible_${currentProjectId.value}`,
      JSON.stringify(eligible)
    )

    return eligible
  })

  // NEW: Initialize from localStorage on mount
  function initializeFromCache(projectId) {
    const cached = localStorage.getItem(`closeout_eligible_${projectId}`)
    if (cached) {
      closeoutEligible.value = JSON.parse(cached)
    }
  }

  return { agents, closeoutEligible, initializeFromCache, ... }
})
```

#### 3.3 Update JobsTab Component
```vue
<!-- frontend/src/components/projects/JobsTab.vue -->
<script setup>
import { onMounted } from 'vue'
import { useAgentJobsStore } from '@/stores/agentJobs'
import { useWebSocketV2 } from '@/composables/useWebSocket'

const store = useAgentJobsStore()
const { subscribe, catchUpEvents } = useWebSocketV2()

onMounted(async () => {
  // 1. Initialize from cache (shows last known state immediately)
  store.initializeFromCache(props.project.id)

  // 2. Subscribe to WebSocket (triggers catch-up automatically)
  subscribe('project', props.project.id)

  // 3. Fetch fresh state via REST (may be redundant after catch-up)
  const response = await api.get(`/api/projects/${props.project.id}/jobs`)
  store.setAgents(response.data.rows)
})
</script>
```

### Phase 4: Testing & Validation

#### 4.1 E2E Test Scenarios
```javascript
// frontend/tests/e2e/websocket-state-persistence.spec.js

test('agent status persists across page refresh', async ({ page }) => {
  // 1. Stage project (creates orchestrator)
  await page.click('[data-testid="stage-project-btn"]')
  await page.waitForSelector('[data-testid="agent-row"][data-agent-type="orchestrator"]')

  // 2. Verify orchestrator status is "preparing"
  const status1 = await page.textContent('[data-testid="agent-row"][data-agent-type="orchestrator"] [data-testid="status-chip"]')
  expect(status1).toBe('Preparing')

  // 3. Refresh page
  await page.reload()

  // 4. Verify orchestrator STILL shows "preparing" after refresh
  await page.waitForSelector('[data-testid="agent-row"][data-agent-type="orchestrator"]')
  const status2 = await page.textContent('[data-testid="agent-row"][data-agent-type="orchestrator"] [data-testid="status-chip"]')
  expect(status2).toBe('Preparing')
})

test('closeout button persists when all agents complete', async ({ page }) => {
  // 1. Complete all agents (mock via API)
  await mockCompleteAllAgents(page)

  // 2. Verify "Closeout Project" button visible
  await page.waitForSelector('[data-testid="closeout-project-btn"]')

  // 3. Refresh page
  await page.reload()

  // 4. Verify button STILL visible after refresh
  await page.waitForSelector('[data-testid="closeout-project-btn"]', { timeout: 5000 })
})

test('duplicate orchestrator prevention', async ({ page }) => {
  // 1. Stage project (creates orchestrator 1)
  await page.click('[data-testid="stage-project-btn"]')
  await page.waitForSelector('[data-testid="agent-row"][data-agent-type="orchestrator"]')
  const orchestratorId1 = await page.getAttribute('[data-testid="agent-row"][data-agent-type="orchestrator"]', 'data-job-id')

  // 2. Refresh page (simulates user refresh during staging)
  await page.reload()

  // 3. Click "Stage Project" AGAIN
  await page.click('[data-testid="stage-project-btn"]')
  await page.waitForTimeout(2000)  // Wait for potential duplicate creation

  // 4. Verify ONLY ONE orchestrator exists
  const orchestratorRows = await page.locator('[data-testid="agent-row"][data-agent-type="orchestrator"]').count()
  expect(orchestratorRows).toBe(1)

  // 5. Verify same orchestrator ID returned
  const orchestratorId2 = await page.getAttribute('[data-testid="agent-row"][data-agent-type="orchestrator"]', 'data-job-id')
  expect(orchestratorId1).toBe(orchestratorId2)
})
```

#### 4.2 Unit Tests

**Backend**:
- `test_websocket_event_persistence()` - Verify events saved to `websocket_event_log`
- `test_catch_up_endpoint()` - Verify catch-up returns events since timestamp
- `test_orchestrator_idempotency()` - Verify no duplicate orchestrators (Phase 2.2)

**Frontend**:
- `test_catch_up_on_reconnect()` - Verify composable fetches missed events
- `test_localStorage_persistence()` - Verify closeout eligibility persisted
- `test_store_initialization_from_cache()` - Verify store loads from localStorage

---

## Files to Modify

### Backend
| File | Changes |
|------|---------|
| `migrations/0358_websocket_event_log.sql` | Create event log table |
| `src/giljo_mcp/models/websocket.py` | Add `WebSocketEventLog` model |
| `src/giljo_mcp/websocket/manager.py` | Add `_persist_event()`, `get_missed_events()` |
| `api/endpoints/websocket.py` | Add `/events/catch-up` endpoint |
| `src/giljo_mcp/services/project_service.py` | Add orchestrator idempotency check (line 1720) |

### Frontend
| File | Changes |
|------|---------|
| `frontend/src/composables/useWebSocket.js` | Add `catchUpEvents()` function |
| `frontend/src/stores/agentJobs.js` | Add `closeoutEligible` computed, localStorage persistence |
| `frontend/src/stores/websocket.js` | Update `handleEvent()` to record last seen timestamp |
| `frontend/src/components/projects/JobsTab.vue` | Update onMounted to initialize from cache |
| `frontend/src/components/projects/ProjectTabs.vue` | Read closeout eligibility from store (not computed) |

### Tests
| File | Changes |
|------|---------|
| `tests/integration/test_orchestrator_idempotency.py` | NEW: Test duplicate prevention |
| `tests/websocket/test_event_persistence.py` | NEW: Test event log CRUD |
| `tests/api/test_catch_up_endpoint.py` | NEW: Test catch-up endpoint |
| `frontend/tests/e2e/websocket-state-persistence.spec.js` | NEW: E2E tests (3 scenarios) |
| `frontend/tests/unit/composables/useWebSocket.spec.js` | Update for catch-up logic |
| `frontend/tests/unit/stores/agentJobs.spec.js` | Test localStorage persistence |

---

## Testing Strategy

### Test-Driven Development (TDD)

**Phase 1 - Backend Event Persistence**:
1. Write tests for `WebSocketEventLog` model CRUD
2. Write tests for `_persist_event()` method
3. Write tests for `get_missed_events()` query
4. Implement until tests pass

**Phase 2 - Orchestrator Idempotency**:
1. Write failing test `test_launch_project_prevents_duplicate_orchestrators`
2. Add idempotency check to `launch_project()`
3. Verify test passes

**Phase 3 - Frontend State**:
1. Write unit tests for `catchUpEvents()` composable
2. Write unit tests for localStorage persistence in store
3. Implement until tests pass
4. Write E2E tests for page refresh scenarios
5. Verify E2E tests pass

### Manual Testing Checklist

- [ ] Stage project → Refresh page → Verify orchestrator status persists
- [ ] Complete all agents → Verify closeout button appears
- [ ] Refresh page → Verify closeout button STILL visible
- [ ] Send message → Refresh page → Verify message counters correct
- [ ] Stage project → Refresh mid-staging → Verify NO duplicate orchestrator
- [ ] Disconnect WebSocket → Reconnect → Verify catch-up events replayed
- [ ] Multiple browser tabs → Verify state syncs across tabs

---

## Success Criteria

### Functional Requirements
- ✅ Agent status persists across page refresh
- ✅ "Closeout Project" button visibility persists across page refresh
- ✅ Message counters reflect accurate state after refresh
- ✅ No duplicate orchestrators can be spawned (idempotency enforced)
- ✅ WebSocket reconnect triggers catch-up of missed events
- ✅ State synchronizes across multiple browser tabs

### Performance Requirements
- ✅ Catch-up query completes in <500ms (indexed by tenant_key + entity_id)
- ✅ Event log retention purge runs daily without blocking
- ✅ localStorage operations don't block UI rendering

### Test Coverage
- ✅ Backend: >80% coverage for event persistence and idempotency
- ✅ Frontend: >80% coverage for composable and store logic
- ✅ E2E: 3 critical scenarios passing (status persistence, closeout button, duplicate prevention)

---

## Rollout Plan

### Phase 1 (Hours 1-4): Backend Foundation
- Implement event log table and model
- Add persistence to WebSocketManager
- Add catch-up endpoint
- Write and pass backend tests

### Phase 2 (Hours 5-7): Orchestrator Idempotency
- Add idempotency check to `launch_project()`
- Write and pass integration tests
- Manual verification: no duplicates on refresh

### Phase 3 (Hours 8-11): Frontend State Refactor
- Implement catch-up in composable
- Add localStorage persistence to store
- Update JobsTab component
- Write and pass unit tests

### Phase 4 (Hours 12-14): E2E Testing & Validation
- Write E2E tests for page refresh scenarios
- Manual testing checklist
- Bug fixes and refinements
- Documentation updates

---

## Risks & Mitigation

### Risk 1: Event Log Table Grows Unbounded
**Mitigation**: 7-day retention policy with auto-purge scheduled task. Monitor table size in production.

### Risk 2: Catch-Up Overwhelms Client on Long Disconnection
**Mitigation**: Limit catch-up to last 1000 events. If more than 1000 missed, force full REST refresh.

### Risk 3: localStorage Quota Exceeded
**Mitigation**: Store only lightweight eligibility flags (JSON booleans), not full agent arrays. Clear old projects from cache after 30 days.

### Risk 4: Race Condition Between Catch-Up and REST Fetch
**Mitigation**: Order operations: 1) Initialize from cache (instant), 2) Catch-up (fast), 3) REST fetch (slowest). Use versioning/timestamps to detect stale REST responses.

---

## Related Handovers

- **0362**: WebSocket Message Counter Fixes - Fixed sender self-notification and race conditions
- **0243c**: JobsTab Dynamic Status Fix - Replaced hardcoded "Waiting." with dynamic binding
- **0359**: Agent Template Loading Fixes - Fixed job_id routing issues
- **0292**: Initial WebSocket UI Regressions Investigation

---

## Appendix: Architecture Diagrams

### Before: Ephemeral WebSocket Events
```
┌─────────────────────────────────────────────────────────────────────┐
│                       BACKEND (Python/FastAPI)                       │
├─────────────────────────────────────────────────────────────────────┤
│  Orchestrator Spawned                                                │
│       ↓                                                              │
│  WebSocketManager.broadcast_agent_created()                          │
│       ↓                                                              │
│  Fire-and-forget event to connected clients                          │
│  (NO persistence, NO replay on reconnect)                            │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                       FRONTEND (Vue 3/Pinia)                         │
├─────────────────────────────────────────────────────────────────────┤
│  WebSocket Handler → store.updateAgent()                             │
│       ↓                                                              │
│  State updated in memory (agentJobs store)                           │
│  (LOST on page refresh - NO persistence)                             │
└─────────────────────────────────────────────────────────────────────┘
```

### After: Persistent Events with Catch-Up
```
┌─────────────────────────────────────────────────────────────────────┐
│                       BACKEND (Python/FastAPI)                       │
├─────────────────────────────────────────────────────────────────────┤
│  Orchestrator Spawned                                                │
│       ↓                                                              │
│  WebSocketManager.broadcast_agent_created()                          │
│       ├─→ Broadcast to connected clients (real-time)                 │
│       └─→ _persist_event() → websocket_event_log table               │
│                                                                      │
│  NEW: /api/websocket/events/catch-up endpoint                        │
│       ├─→ Query events since timestamp                               │
│       └─→ Return missed events for replay                            │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                       FRONTEND (Vue 3/Pinia)                         │
├─────────────────────────────────────────────────────────────────────┤
│  On Mount / Reconnect:                                               │
│    1. Initialize from localStorage (instant visibility)              │
│    2. Subscribe to WebSocket                                         │
│    3. Call catchUpEvents() → fetch missed events                     │
│    4. Replay events → store.updateAgent()                            │
│    5. Fetch fresh state via REST (fallback)                          │
│                                                                      │
│  Closeout Eligibility:                                               │
│    - Computed from agent statuses                                    │
│    - Persisted to localStorage on change                             │
│    - Restored on page refresh                                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Commit Message Template

```
feat(0358): Implement WebSocket state persistence and orchestrator idempotency

- Add websocket_event_log table for event persistence (7-day retention)
- Add /api/websocket/events/catch-up endpoint for missed event replay
- Add orchestrator idempotency check in launch_project() (prevents duplicates)
- Add catchUpEvents() to useWebSocket composable
- Add localStorage persistence for closeout eligibility
- Add E2E tests for page refresh scenarios

Fixes:
- Issue #4: Dashboard shows stale data after page refresh
- Issue #6: "Closeout Project" button disappears on refresh
- Issue #7: Duplicate orchestrator spawned on refresh

Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## ⚠️ DEVELOPER DISCUSSION REQUIRED

**Before implementing this handover, discuss the following with the developer:**

### Options to Review

1. **Event Persistence Strategy**
   - Option A: New `websocket_event_log` table with 7-day retention (proposed)
   - Option B: Redis-based event queue with TTL
   - Option C: No persistence, rely on REST API for initial state
   - **Trade-offs**: Storage vs complexity vs real-time accuracy

2. **State Synchronization Approach**
   - Option A: Centralized Pinia store (proposed)
   - Option B: Component-level state with shared composables
   - Option C: Hybrid (store for critical state, local for UI-only)
   - **Trade-offs**: Consistency vs performance vs complexity

3. **Orchestrator Idempotency**
   - Option A: Check for existing active orchestrator in `launch_project()` (proposed)
   - Option B: Database unique constraint on (project_id, status='active')
   - Option C: Frontend-only prevention (disable button if orchestrator exists)
   - **Trade-offs**: Safety vs simplicity vs user experience

4. **Scope Decision**
   - Full overhaul (10-14 hours) vs surgical fix (3-4 hours)?
   - Can we ship quick fix for duplicate orchestrator bug first?

### Questions for Developer

- [ ] Is 7-day event retention acceptable? Too long? Too short?
- [ ] Should we implement WebSocket reconnection with exponential backoff?
- [ ] Are there other pages affected by stale state issues?
- [ ] Can we phase this: Bug fix first, then full overhaul?

### Alpha Trial Reference

Review agent feedback for real-world context:
- Dashboard showed documenter "working" then reverted to "Waiting" on focus change
- Closeout button appeared then disappeared on refresh
- Each refresh spawned a new orchestrator instance

### Session Context

This handover originated from the **Alpha Trial Remediation Session** (2025-12-19).
See: `handovers/alpha_trial_remediation_roadmap.md` for full context and prioritization rationale.
