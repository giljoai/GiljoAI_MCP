# Handover 0379d: Backend Event Contract + Broadcast Unification
 
**Date:** 2025-12-25  
**From Agent:** Roadmap split (Codex)  
**To Agent:** system-architect + tdd-implementor  
**Priority:** Critical  
**Estimated Complexity:** 8–12 hours  
**Status:** Not Started  
 
---
 
## Task Summary
Make backend WebSocket emission **one system**:
- One canonical event envelope (`{type,timestamp,schema_version,data}`).
- One canonical broadcaster (delegate everything to `api/websocket.py:WebSocketManager`).
- Eliminate ad-hoc emit loops in ws-bridge/event listener/dependency layer.
- Fix event name drift (`agent_update` vs `agent:update`, etc.) using explicit aliasing during migration.
 
---
 
## Dependencies
- Can be started in parallel with frontend work, but must preserve backward compatibility until 0379a–c are complete.
 
---
 
## Files To Modify
- `api/websocket.py` (canonical broadcaster; concurrency-safe snapshots; tenant isolation)
- `api/events/schemas.py` (EventFactory becomes the only event constructor)
- `api/dependencies/websocket.py` (delegate to WebSocketManager; remove duplicated send loops)
- `api/websocket_event_listener.py` (delegate; stop manual send loops)
- `api/endpoints/websocket_bridge.py` (delegate; stop flattening-by-hand if frontend no longer needs it)
 
---
 
## Implementation Plan (TDD)
1) **RED tests** (backend):
   - event envelope shape for key events (mission updated, agent created, message:sent/received/ack).
   - tenant isolation: tenant A never receives tenant B events.
   - legacy aliasing: when enabled, both old and new names are emitted during migration.
2) **GREEN:** refactor broadcasters to call one canonical method.
3) **REFACTOR:** remove duplicate codepaths and enforce EventFactory usage.
 
---
 
## Success Criteria
- There is exactly one “send loop” implementation for tenant broadcasts.
- Event payload shapes are consistent regardless of source (no ws-bridge flattening hacks needed long-term).
- Event naming convention is stable and documented; legacy alias window is explicit.
 
---
 
## Rollback Plan
- Keep aliasing enabled and fallback emit paths behind a feature flag while transitioning; revert to previous broadcast path by toggling configuration if needed.

---

## Critical Findings (from 0379a/b Quality Review)

### P0: Tenant Guard Fail-Open Risk
**Location:** `frontend/src/stores/websocketEventRouter.js:22-35`

The router currently allows events through when `tenant_key` is missing (for backward compatibility).
```javascript
if (!currentTenantKey) return true  // Bypass when user not loaded
if (payload?.tenant_key && ...) return false  // Only checks if present
return true  // Missing tenant_key = allowed
```

**Required Fix:**
- Backend MUST always include `tenant_key` on all tenant-scoped events
- Once backend contract is enforced, frontend can switch to fail-closed for tenant-scoped event types
- Add explicit list of "tenant-scoped" event types that require `tenant_key`

### P1: Agent/Job Identifier Ambiguity
**Location:** `frontend/src/stores/agentJobsStore.js:155-170`

`resolveJobId()` falls back to `agent_type`/`agent_name` when `job_id` is not found in the Map:
```javascript
// Legacy fallback: from_agent may be agent_type (e.g., "orchestrator")
for (const job of jobsById.value.values()) {
  if (job.agent_type === identifier || job.agent_name === identifier) {
    return job.job_id
  }
}
```

**Risk:** Multiple agents can share a type (e.g., 3 "implementer" agents). Message counters could be misattributed.

**Required Fix:**
- Backend should always send `from_job_id` / `to_job_ids` (not `from_agent` / `to_agent_ids` with type names)
- Fallback to agent_type should only apply to `orchestrator` (always unique per project)

### P2: Router Event Ordering
**Location:** `frontend/src/stores/websocketEventRouter.js:369`

Router dispatches events concurrently (no queue). If handlers become async and depend on strict ordering, races are possible.

**Consideration:** If any domain requires ordering (e.g., mission update before agent spawn), consider adding a serialization queue for those event types.

### Tests to Add (Backend)
1. All tenant-scoped events include `tenant_key` in payload
2. All message events include `from_job_id` / `to_job_ids` (not type names)
3. Event envelope shape validation for key events
 
