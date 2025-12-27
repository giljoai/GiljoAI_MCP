# Handover 0379b: Agent/Job Domain Migration (Map Store + Jobs UI)
 
**Date:** 2025-12-25  
**From Agent:** Roadmap split (Codex)  
**To Agent:** tdd-implementor + frontend-tester  
**Priority:** High  
**Estimated Complexity:** 10–12 hours  
**Status:** Completed (Map Store + Jobs UI)  
 
---
 
## Task Summary
Migrate agent/job state to a map-based store with immutable updates, then refactor Jobs UI to consume it via composables (no props mutation, no array-scan getters).
 
---
 
## Dependencies
- Requires 0379a (event router + safe subscriptions) merged first.
 
---
 
## Files To Create / Refactor
**Create**
- `frontend/src/stores/agentJobsStore.js` (Map<job_id, job>)
- `frontend/src/composables/useAgentJobs.js`
 
**Refactor**
- `frontend/src/components/projects/JobsTab.vue` (stop mutating props; use composable/store)
- `frontend/src/stores/agents.js` (remove module-level WS auto-init; either delete or convert to thin wrapper)
 
---
 
## Implementation Plan (TDD)
1) **RED tests** for `agentJobsStore`:
   - create → update → status change produces new object references (immutability).
   - duplicate `agent:created` doesn’t create duplicates.
   - message counter updates behave correctly for `message:sent`, `message:received`, `message:acknowledged`.
2) **GREEN:** implement store + composable.
3) **Refactor JobsTab.vue** to only read from composable, and to dispatch user actions to APIs/stores (no direct mutations).
4) **Wire events** through `websocketEventRouter.js` EVENT_MAP for the agent/job domain.
 
---
 
## Testing Requirements
**Unit**
- `agentJobsStore.spec.js` (immutability, counters, dedupe)
 
**Manual**
1) Stage project, ensure agent cards appear without refresh.
2) Switch tabs repeatedly; confirm no duplicate updates and counters stay correct.
 
---
 
## Success Criteria
- Jobs UI updates in real time without relying on prop mutation.
- No duplicate WS handlers registered via store imports.
- Job/agent updates are O(1) by ID (no array scanning as the primary path).
 
---
 
## Rollback Plan
- Revert JobsTab.vue changes and keep the new store/composable dormant; router mapping can be disabled for this domain if needed.

---

## Implementation Summary (Completed)

### Delivered (0379b scope)
- **Map-based domain store (O(1) by `job_id`)**: Added `frontend/src/stores/agentJobsStore.js` (`Map<job_id, job>` + immutable updates) with WebSocket handlers for `agent:*`, message counters, and mission acknowledgment.
- **Composable API boundary**: Added `frontend/src/composables/useAgentJobs.js` (`loadJobs(projectId)` → `api.agentJobs.list()` → `agentJobsStore.setJobs()`), exposing `sortedJobs` + `jobCount`.
- **Jobs UI migrated off props mutation**: Refactored `frontend/src/components/projects/JobsTab.vue` to use `useAgentJobs()` as the source of truth; removed direct WebSocket handler registration and added reconnect resync via `wsStore.onConnectionChange`.
- **Parent wiring simplified**: Updated `frontend/src/components/projects/ProjectTabs.vue` to stop passing `agents/messages/allAgentsComplete` props into JobsTab (JobsTab now owns loading).
- **Router wiring for agent/job domain**: Updated `frontend/src/stores/websocketEventRouter.js` to route `agent:*`, `message:*`, and `job:mission_acknowledged` into the new domain store while preserving legacy `agents` store updates for backward compatibility.

### Tests Added / Updated (TDD)
- Added: `frontend/src/stores/agentJobsStore.spec.js` (immutability, dedupe, message counters)
- Updated: `frontend/src/stores/websocketEventRouter.spec.js` (EVENT_MAP routes agent/job domain events via injected `storeRegistry`)

### Tests Run (Targeted)
- `cd frontend && npm run test:run -- src/stores/agentJobsStore.spec.js src/stores/websocket.spec.js src/stores/websocketEventRouter.spec.js tests/unit/stores/products.websocket.spec.js` (pass)
- `cd frontend && npm run build` (pass)

### Known Issues / Follow-ups
- Full `cd frontend && npm run test:run` currently fails due to unrelated pre-existing test failures in the repo (not introduced by 0379b).
- `frontend/src/stores/agentJobs.js` is still used by other orchestration components; 0379b only migrates the Jobs tab path (future phases can converge stores or deprecate the legacy one).
 
