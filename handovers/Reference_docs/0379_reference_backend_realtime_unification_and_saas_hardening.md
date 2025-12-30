# 0379 Reference: Backend Real‑Time Unification & SaaS Hardening
 
**Date:** 2025-12-25  
**From Agent:** codex (GPT-5.2) – deep code review session  
**To Agent:** Reference document for the 0379 series (especially 0379d + 0379e)  
**Priority:** Reference (read-only)  
**Status:** Superseded by `handovers/0379_universal_reactive_state_architecture.md` (merged)  
 
**How to use this doc:**
- Read `handovers/0379_universal_reactive_state_architecture.md` first (master roadmap).
- Execute work via `handovers/0379d_backend_event_contract_and_broadcast_unification.md` and `handovers/0379e_saas_broker_and_loopback_elimination.md`.
- Use this file as deeper backend context, rationale, and gotcha list.
 
## Goals (Backend)
- One canonical event contract (envelope + naming) for every UI update.
- One canonical broadcast path (no duplicate emit loops).
- Zero hardcoded loopback dependency (`localhost:7272`) for in-process publishers.
- SaaS-ready pub/sub (multi-worker/multi-instance) without future rewrite.
 
## Roadmap Mapping
- **0379d**: event contract + broadcaster unification (shape + naming + delegation).
- **0379e**: broker + loopback elimination (LISTEN/NOTIFY baseline; optional Redis).
 
---
 
## 1) What This Reference Covers
The current “real-time” layer is fragmented across multiple event schemas and multiple broadcast codepaths (direct WS, EventBus listener, and an HTTP loopback `/api/v1/ws-bridge`). This directly causes intermittent UI updates and “needs manual refresh” regressions when new UI elements are added.  
Deliver a single, production-grade real-time architecture that is stable on a single LAN server **and** scales cleanly to SaaS (multi-worker/multi-instance) without rework.
 
---
 
## 2) Context & Background (User-Observed Symptoms)
User reports: dashboards often don’t refresh without manual page refresh; adding new status indicators/buttons/cards frequently “breaks real-time.” This strongly indicates:
- No single canonical event contract (type + schema + payload shape).
- No single canonical broadcast path.
- Missing resync logic after reconnect / missed events.
- Hosting mode incompatibilities (multi-worker / multi-instance).
 
This handover is explicitly **not** “postpone anything” — it builds the architecture needed for SaaS now while keeping single-server LAN installs simple.
 
---
 
## 3) Current Architecture (What Exists Today)
### Backend
- WebSocket endpoint: `api/app.py` → `@app.websocket("/ws/{client_id}")` (`create_app/websocket_endpoint`, approx `api/app.py:492`).
- Connection manager: `api/websocket.py` (`WebSocketManager`), plus compatibility shim `api/websocket_manager.py` (`ConnectionInfo`).
- EventBus pattern (in-memory): `api/event_bus.py`, with bridge listener: `api/websocket_event_listener.py`.
- HTTP event bridge endpoint (loopback): `api/endpoints/websocket_bridge.py` (`POST /api/v1/ws-bridge/emit`).
- Services sometimes broadcast directly via `websocket_manager` (MessageService, OrchestrationService), but other key flows use the loopback bridge (`src/giljo_mcp/services/project_service.py`).
 
### Frontend
- Central WS client: `frontend/src/stores/websocket.js` (Pinia store; reconnect, ping, payload normalization, subscriptions).
- Integrations router: `frontend/src/stores/websocketIntegrations.js` (dispatches events to other stores and window events).
- Connection established at app init: `frontend/src/layouts/DefaultLayout.vue` (calls `wsStore.connect()` after user load).
- Subscriptions used in some views: e.g. `frontend/src/components/projects/ProjectTabs.vue` subscribes to project events.
 
---
 
## 4) Findings (Root Causes of Instability)
### A) Fragmented event schemas + ad-hoc payload shaping
You currently have *at least* three “schemas” in play:
1) **Canonical envelope pattern** (type/timestamp/schema_version/data) in `api/websocket.py` (`broadcast_to_tenant`, ~`api/websocket.py:137`).
2) **EventFactory** canonical models in `api/events/schemas.py` (e.g. `EventFactory.project_mission_updated`, ~`api/events/schemas.py:328`).
3) **ws-bridge flattened payload** (top-level keys merged for frontend convenience) in `api/endpoints/websocket_bridge.py` (`emit_websocket_event`, ~`api/endpoints/websocket_bridge.py:42`).
 
Result: every time a new UI feature is added, it’s easy to listen for the “wrong” event type/shape, and updates silently stop.
 
### B) Multiple broadcast codepaths (not unified)
Broadcast logic is duplicated across:
- `api/websocket.py` (WebSocketManager methods)
- `api/dependencies/websocket.py` (WebSocketDependency repeats broadcast logic)
- `api/websocket_event_listener.py` (manual iteration + send)
- `api/endpoints/websocket_bridge.py` (manual iteration + send)
 
This guarantees drift and inconsistent tenant filtering/shape rules.
 
### C) HTTP loopback `/api/v1/ws-bridge` used where in-process broadcast should be possible
Example: mission updates broadcast via loopback POST to `http://localhost:7272/api/v1/ws-bridge/emit` (`src/giljo_mcp/services/project_service.py:_broadcast_mission_update`, ~`src/giljo_mcp/services/project_service.py:2602`).
 
Failure modes:
- Wrong host/port in hosted/proxy installs.
- Extra network hop and timeout.
- Breaks under multi-worker routing (request can land on a worker with zero sockets).
 
### D) Not SaaS-ready (multi-worker/multi-instance will be flaky by design)
Connections and event routing are in-memory per process. With `uvicorn --workers > 1` (`api/run_api.py` supports it), broadcasts can miss clients connected to a different worker.
 
For SaaS, you need a shared pub/sub (Redis or Postgres LISTEN/NOTIFY) so any instance can publish and all instances can broadcast to their local sockets.
 
### E) Concurrency hazards in send loops
Many loops do `for client_id, ws in active_connections.items(): await ws.send_json(...)`.
If another coroutine mutates the dict during awaits, you risk runtime errors and partial sends. This is a real instability class under load.
 
### F) Frontend subscription fragility + no reconnect resync
- Subscriptions are stored as boolean keys, not reference-counted (`frontend/src/stores/websocket.js`), so one component unmount can unsubscribe for others.
- There is no “resync after reconnect” mechanism, so missed events leave UI stale until manual refresh.
 
### G) Event name drift (colon vs underscore) and dead integration hooks
`frontend/src/stores/websocketIntegrations.js` listens to `agent_update` (underscore), but backend emits `agent:update` (colon) from `api/websocket.py` (`broadcast_agent_update`, ~`api/websocket.py:622`). This is a concrete mismatch that causes silent non-updates for any code relying on that integration hook.
 
### H) Documentation drift (dev guide vs implementation reality)
Docs say “Always use dependency injection + EventFactory; never construct events manually” (`docs/developer_guides/websocket_events_guide.md`), but key broadcast paths still manually shape payloads and bypass EventFactory (ws-bridge, event listener).
 
---
 
## 5) Recommendation: Target Architecture (Single Server + SaaS)
### Principle 1: One canonical event contract
Adopt **one** envelope format everywhere:
```json
{ "type": "event:name", "timestamp": "...", "schema_version": "1.0", "data": { ... } }
```
Use `api/events/schemas.py` (EventFactory + Pydantic models) as the only way to construct events.
 
### Principle 2: One canonical broadcast implementation
All broadcasts must go through one component that:
- snapshots connections safely before awaiting
- enforces tenant isolation
- optionally supports “project-scoped” fanout (via subscriptions)
- centralizes error handling and disconnection cleanup
 
Recommendation: consolidate into `api/websocket.py:WebSocketManager` and make other layers call it (dependency, ws-bridge, event listener should delegate).
 
### Principle 3: Remove loopback bridge for in-process code; replace with injection
In-process services should accept `websocket_manager` and broadcast directly. The HTTP bridge should be used **only** for truly external publishers (if any remain), and must be secured.
 
### Principle 4: SaaS-ready pub/sub abstraction now (no postponement)
Add a `WebSocketEventBroker` interface with at least:
- `InMemoryBroker` (default for single-server LAN)
- `PostgresNotifyBroker` (LISTEN/NOTIFY; no new infra)
- `RedisPubSubBroker` (optional for high scale)
 
Flow:
1) Any part of the app “publishes” a WebSocket event to the broker.
2) Each server instance subscribes and broadcasts the event to its local WebSocket clients.
 
This avoids “single worker only” constraints and prevents future rewrite.
 
### Principle 5: WebSockets are an incremental layer; reconnect must resync from REST
On reconnect, frontend must refetch authoritative state (projects/jobs/agents/messages counters) so missed events don’t require manual refresh.
 
---
 
## 6) Technical Work Items (Files to Touch)
### Backend (core)
- `api/websocket.py`: make broadcasting concurrency-safe; unify event sending; remove duplicate ad-hoc event methods where possible.
- `api/events/schemas.py`: expand EventFactory to cover currently ad-hoc events (message counters, job/agent status, etc.).
- `api/dependencies/websocket.py`: delegate to WebSocketManager (or remove duplication).
- `api/websocket_event_listener.py`: stop manually sending; delegate to WebSocketManager + EventFactory.
- `api/endpoints/websocket_bridge.py`: either (A) remove for in-process use, or (B) secure + delegate to broker.
- `api/app.py`: remove `state.connections` duplication or make it a view of WebSocketManager.
 
### Backend (services that currently loopback)
- `src/giljo_mcp/services/project_service.py`: inject `websocket_manager` (or broker) instead of POSTing to localhost.
- Any other service still hardcoding ws-bridge loopback URLs (search for `ws-bridge/emit`).
 
### Frontend
- `frontend/src/stores/websocket.js`: implement reference-counted subscriptions; add “connected/reconnected → resync” hooks.
- `frontend/src/stores/websocketIntegrations.js`: fix event name mismatches (`agent_update` vs `agent:update`) and remove dead handlers.
- `frontend/src/config/api.js` + app bootstrap: ensure runtime-config initialization is actually invoked so WS URL is correct in hosted/SaaS mode.
 
---
 
## 7) Implementation Plan (Phases)
### Phase 1: Contract + broadcast unification (must happen first)
1) Define canonical event envelope + enforce EventFactory usage.
2) Refactor ws-bridge + event listener to delegate to one broadcaster.
3) Add strict payload validation tests for 5–10 top events (mission updated, agent created, agent update, message:sent/received/ack).
 
**Exit criteria:** One event shape across all sources; frontend only needs one normalization path.
 
### Phase 2: Remove in-process loopback and fix concurrency
1) Inject websocket_manager/broker into services; remove localhost POST usage.
2) Snapshot `active_connections` and `entity_subscribers` before await loops; add send timeouts.
3) Ensure tenant-scoped broadcast is always used (no accidental cross-tenant sends).
 
**Exit criteria:** No loopback required for core flows; no send-loop mutation hazards.
 
### Phase 3: Frontend resync + subscription correctness
1) Add subscription refcounting so shared subscriptions can’t be dropped accidentally.
2) Add reconnect resync: on reconnect, refetch critical state.
3) Ensure event names match and are documented.
 
**Exit criteria:** UI never requires manual refresh after transient disconnect or missed events.
 
### Phase 4: SaaS pub/sub broker (no postponement)
1) Implement broker abstraction + Postgres LISTEN/NOTIFY baseline.
2) Add optional Redis pub/sub implementation (feature-flagged).
3) Validate multi-worker + multi-instance delivery in tests.
 
**Exit criteria:** Works with `--workers > 1` and multiple instances without sticky sessions.
 
---
 
## 8) Testing Requirements
### Unit tests (backend)
- EventFactory: payload validation for each event type.
- WebSocketManager: broadcast_to_tenant snapshots + per-tenant isolation.
- Broker: publish/subscribe behavior for Postgres/Redis implementations.
 
### Integration tests (backend)
- Start FastAPI, connect 2 WS clients (same tenant) + 1 other-tenant client; assert correct fanout.
- Run with `--workers 2` (or two app instances) once broker exists; assert delivery regardless of which instance processes the publish.
 
### Frontend tests
- Subscription refcount tests: two subscribers, one unmounts, subscription remains.
- Reconnect resync tests: simulate disconnect/reconnect, assert stores refetch and UI updates.
 
### Manual test procedure (must be in handover completion notes)
1) Open 2 browsers to same project; stage project; confirm mission + agent cards appear on both without refresh.
2) Kill network briefly / restart server; confirm reconnect triggers state resync without refresh.
3) (SaaS) Run 2 workers/instances; confirm events still reach connected clients.
 
---
 
## 9) Dependencies & Blockers
### Decisions needed
- Broker baseline: Postgres LISTEN/NOTIFY vs Redis-only vs both.
- Canonical event naming convention (colon-delimited recommended).
 
### Current repo blockers observed during analysis
- `pytest -k websocket` currently has collection errors and coverage gating issues, and `tests/websocket` has failing mission tracking tests (schema drift). These must be addressed or isolated so new realtime tests can run reliably.
 
---
 
## 10) Success Criteria (Definition of Done)
- No manual refresh required for dashboards after:
  - staging/launch events
  - agent status updates
  - message counters
  - transient disconnect/reconnect
- Single-server LAN installs “just work” with zero extra dependencies.
- SaaS mode supports multi-worker/multi-instance without flakiness.
- One documented event contract; one broadcast path; no duplicate ad-hoc emitters.
- Tests cover event contract + tenant isolation + reconnect resync.
 
---
 
## 11) Rollback Plan
- Feature-flag new broker path; keep old direct in-memory path available during transition.
- Keep frontend payload normalization for both nested and flat payloads until all emitters are unified, then remove legacy normalization.
- If broker introduces instability, revert to single-process in-memory broadcasting while keeping contract unification (safe rollback).
 
---
 
## 12) Additional Resources
- Existing related handovers:
  - `handovers/0362_websocket_message_counter_fixes.md` (complete/merge into this effort)
  - `handovers/0379_universal_reactive_state_architecture.md` (broader state architecture alignment)
- Docs:
  - `docs/developer_guides/websocket_events_guide.md`
  - `docs/architecture/websocket_event_bus.md`
- Key code references:
  - WebSocket endpoint: `api/app.py` (`create_app/websocket_endpoint`)
  - Manager: `api/websocket.py`
  - ws-bridge: `api/endpoints/websocket_bridge.py`
  - Mission update loopback: `src/giljo_mcp/services/project_service.py` (`_broadcast_mission_update`)
