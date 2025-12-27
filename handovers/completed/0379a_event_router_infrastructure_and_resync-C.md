# Handover 0379a: Event Router Infrastructure + Reconnect Resync
 
**Date:** 2025-12-25  
**From Agent:** Roadmap split (Codex)  
**To Agent:** tdd-implementor + frontend-tester  
**Priority:** High  
**Estimated Complexity:** 10–12 hours  
**Status:** Completed (Foundation Landed)  
 
---
 
## Task Summary
Create the **frontend infrastructure** that makes WebSocket updates reliable and maintainable:
- Central event routing (single EVENT_MAP).
- No module-import side effects (no auto WS handler registration in stores).
- Reconnect resync hook (missed WS events never require manual refresh).
- Subscription refcounting (one component unmount can’t unsubscribe others).
 
This phase should be safe to land early: minimal/no component refactors beyond wiring the router and fixing the WebSocket store subscription semantics.
 
---
 
## Why This Matters
Today, handler registration is scattered and often runs at import time. This creates duplicate handlers and inconsistent UI updates after tab switches. Also, reconnect currently does not refetch state, so the UI can remain stale until a full page refresh.
 
---
 
## Files To Create / Modify
**Create**
- `frontend/src/stores/websocketEventRouter.js` (central router + EVENT_MAP)
- `frontend/src/stores/immutableHelpers.js` (small helpers used by map-based stores)
 
**Modify**
- `frontend/src/stores/websocket.js` (subscription refcount + reconnect resync trigger hooks)
- `frontend/src/layouts/DefaultLayout.vue` (initialize the router once after WS connect)
 
**Do not refactor JobsTab/LaunchTab yet** (that is 0379b/0379c).
 
---
 
## Implementation Plan (TDD)
1) **RED:** Add unit tests for:
   - `subscribe()` reference counting (2 subscribers → 1 unsubscribe keeps subscription active).
   - `resubscribeAll()` sends only active subscriptions.
   - Router routing: given a payload with `{ type, data }`, it normalizes and calls the configured store action once.
2) **GREEN:** Implement:
   - `websocket.js`: replace boolean subscription map with `Map<key, count>` (or `{count, ...}`), only send “unsubscribe” when count hits zero.
   - `websocketEventRouter.js`: expose `initWebsocketEventRouter()` that:
     - registers handlers from EVENT_MAP once
     - normalizes payloads
     - supports a reconnect callback hook (even if it only calls existing store fetches for now)
3) **REFACTOR:** Keep router API minimal and explicit. No global side effects at module import.
 
---
 
## Testing Requirements
**Frontend unit tests**
- `test_websocket_subscriptions_refcount()` (behavior: shared subscription not dropped)
- `test_event_router_normalizes_and_routes()` (behavior: one handler called once)
 
**Manual smoke**
1) Start app, open/close tabs repeatedly.
2) Confirm handler duplication does not occur (no repeated side effects per event).
3) Force WS disconnect/reconnect; verify resync triggers at least a messages refresh.
 
---
 
## Success Criteria
- Reconnect triggers a resync path (even if partial initially).
- Subscriptions are safe for shared usage across components.
- Router is initialized once and becomes the single place to wire WS event handling (future phases will migrate domains into map-stores).
 
---
 
## Rollback Plan
- Revert only `DefaultLayout.vue` wiring and `websocket.js` refcount changes if needed; keep router file (unused) without affecting runtime.

---

## Implementation Summary (Completed)

### Delivered (0379a scope)
- **Central router**: Added `frontend/src/stores/websocketEventRouter.js` with a single routing path (`EVENT_MAP`) and payload normalization (`{ type, data }` vs flat payloads).
- **No store import side-effects (partial, targeted)**: Removed auto WebSocket handler registration from `frontend/src/stores/agents.js`, `frontend/src/stores/messages.js`, and `frontend/src/stores/products.js` (handlers now route via the central router).
- **Reconnect resync hook**: Router supports `onReconnectResync`; `frontend/src/layouts/DefaultLayout.vue` wires this to `messageStore.fetchMessages()` after a reconnect.
- **Subscription refcounting**: Updated `frontend/src/stores/websocket.js` to refcount subscriptions (only send `unsubscribe` when the last subscriber leaves) and `resubscribeAll()` to only re-send active subscriptions.
- **Removed polling**: `frontend/src/layouts/DefaultLayout.vue` no longer polls messages every 10 seconds (realtime + reconnect resync replaces it).
- **Immutable helpers (prep for map-stores)**: Added `frontend/src/stores/immutableHelpers.js` (generic Map/object immutable helpers).

### Tenant Isolation Guard (Router-Level)
- Router uses the current user tenant (`useUserStore().currentUser.tenant_key`) and will **drop** events whose payload contains a different `tenant_key`.
- For backward compatibility, events with no `tenant_key` are still routed (Phase 4 will harden backend contract to always include `tenant_key`).

### Files Changed / Added
- Added: `frontend/src/stores/websocketEventRouter.js`
- Added: `frontend/src/stores/immutableHelpers.js`
- Modified: `frontend/src/stores/websocket.js`
- Modified: `frontend/src/layouts/DefaultLayout.vue`
- Modified: `frontend/src/stores/agents.js`
- Modified: `frontend/src/stores/messages.js`
- Modified: `frontend/src/stores/products.js`
- Added tests: `frontend/src/stores/websocket.spec.js`, `frontend/src/stores/websocketEventRouter.spec.js`
- Updated tests: `frontend/tests/unit/stores/products.websocket.spec.js`

### Tests Run (Targeted)
- `cd frontend && npm run test:run -- src/stores/websocket.spec.js` (pass)
- `cd frontend && npm run test:run -- src/stores/websocketEventRouter.spec.js` (pass)
- `cd frontend && npm run test:run -- tests/unit/stores/products.websocket.spec.js` (pass)
- `cd frontend && npm run build` (pass)

### Known Issues / Follow-ups
- Full `cd frontend && npm run test:run` currently fails due to unrelated pre-existing test failures in the repo (not introduced by 0379a).
- `frontend/src/stores/websocketIntegrations.js` still exists but is no longer used by `DefaultLayout.vue` (kept as rollback reference; can be removed later).
- Some components/stores still register `wsStore.on(...)` directly (outside 0379a scope); 0379b/0379c will continue consolidating domain handling into router + map-based stores.
 
