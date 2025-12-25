# Handover 0379e: SaaS Broker (Pub/Sub) + Loopback Elimination
 
**Date:** 2025-12-25  
**From Agent:** Roadmap split (Codex)  
**To Agent:** system-architect + tdd-implementor  
**Priority:** Critical  
**Estimated Complexity:** 8–10 hours (baseline), + time for hardening  
**Status:** Not Started  
 
---
 
## Task Summary
Remove the last “hosted flakiness” root causes and make the platform SaaS-ready:
1) Stop using hardcoded loopback POSTs to `/api/v1/ws-bridge/emit` for in-process publishers.
2) Introduce a broker abstraction so multi-worker/multi-instance deployments work without sticky sessions.
 
Baseline broker recommendation: PostgreSQL LISTEN/NOTIFY (no new infra). Optional: Redis pub/sub for high scale.
 
---
 
## Dependencies
- Best done after 0379d (canonical event contract + broadcaster).
 
---
 
## Files To Create / Modify
**Create**
- `api/broker/base.py` (WebSocketEventBroker interface)
- `api/broker/in_memory.py` (default for LAN/WAN single server)
- `api/broker/postgres_notify.py` (LISTEN/NOTIFY)
- `api/broker/__init__.py` (factory + config)
 
**Modify**
- `api/startup/core_services.py` (start broker; subscribe in each worker)
- `api/app.py` (shutdown broker cleanly)
- Replace loopback emitters (search `ws-bridge/emit`) with broker publish or direct manager injection:
  - `src/giljo_mcp/services/project_service.py` and any other hardcoded loopback usage.
 
---
 
## Implementation Plan (TDD)
1) **RED tests**:
   - in-memory broker publish/subscribe delivers to handler.
   - Postgres broker serializes/deserializes events and calls handler (unit-level with mocked DB connection is acceptable initially).
2) **GREEN:** integrate broker into app startup and make WebSocketManager publish/subscribe.
3) Replace loopback POST usage for in-process services with broker publish or injected broadcaster.
 
---
 
## Success Criteria
- No in-process code relies on `http://localhost:7272` loopback to emit WebSocket events.
- Multi-worker deployments are viable (each worker receives broker events and broadcasts to its local sockets).
- Default remains “simple”: LAN/WAN single server uses in-memory broker with zero extra configuration.
 
---
 
## Rollback Plan
- Feature-flag broker type (default `in_memory`); reverting is a config change, not a code revert.
 
