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
 
