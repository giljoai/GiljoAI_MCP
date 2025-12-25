# Handover 0379c: Messages + Project State Migration (Launch/ProjectTabs)
 
**Date:** 2025-12-25  
**From Agent:** Roadmap split (Codex)  
**To Agent:** tdd-implementor + frontend-tester  
**Priority:** High  
**Estimated Complexity:** 10–12 hours  
**Status:** Not Started  
 
---
 
## Task Summary
Finish the frontend domain migration by building dedicated stores for:
- Project messages (including counters and per-job associations)
- Project state (mission, staging complete, launch readiness, product/project status)
- System notifications/progress
 
Then refactor Launch + ProjectTabs to consume via composables and remove the legacy `websocketIntegrations.js` routing layer.
 
---
 
## Dependencies
- Requires 0379a (router) and ideally 0379b (agentJobs store) first.
 
---
 
## Files To Create / Refactor
**Create**
- `frontend/src/stores/projectMessagesStore.js`
- `frontend/src/stores/projectStateStore.js`
- `frontend/src/stores/systemStore.js`
- `frontend/src/composables/useProjectMessages.js`
- `frontend/src/composables/useProjectState.js`
 
**Refactor**
- `frontend/src/components/projects/ProjectTabs.vue`
- `frontend/src/components/projects/LaunchTab.vue`
- `frontend/src/stores/projectTabs.js` (reduce to navigation only; move state out)
- `frontend/src/stores/websocketIntegrations.js` (remove after migration)
 
---
 
## Implementation Plan (TDD)
1) **RED tests**:
   - message counters reflect WS events immediately.
   - mission updates and staging complete signals update project state immutably.
2) **GREEN:** implement new stores and composables.
3) **Refactor components** to use composables directly; remove prop mutation and fragile watchers.
4) **Cut over routing**: EVENT_MAP routes message/project/system events into the new stores.
5) Remove `websocketIntegrations.js` once no longer referenced.
 
---
 
## Success Criteria
- Launch/ProjectTabs update in real time without manual refresh.
- No duplicate handlers or competing routers (EVENT_MAP is the only event routing).
- Message counters are correct across tab switches and reconnects.
 
---
 
## Rollback Plan
- Revert LaunchTab.vue/ProjectTabs.vue and keep new stores unused; keep EVENT_MAP mappings for these domains disabled until ready.

---

## Pre-Implementation Notes (from 0379a/b Quality Review)

### P1 Bug Fixed (Commit bf77e6e6)
The subscription lifecycle bug in ProjectTabs.vue has been fixed:
- Component now unsubscribes from old project when `props.project` changes
- Subscribes to new project's WebSocket channel
- No longer misses events when switching projects without unmount

### Patterns to Follow (from agentJobsStore)
1. **Map-based store with immutable updates** - Use `new Map()` on every update
2. **Composable API boundary** - `useProjectMessages()` wraps store + API loading
3. **Reconnect resync** - Register `wsStore.onConnectionChange()` listener to reload on reconnect
4. **EVENT_MAP routing** - Add new event types to `websocketEventRouter.js` EVENT_MAP

### Files to Delete
- `frontend/src/stores/websocketIntegrations.js` - Confirmed no longer used by DefaultLayout.vue after 0379a

### Test Template
- Use `agentJobsStore.spec.js` as template for new store tests (immutability, dedupe, counters)
 
