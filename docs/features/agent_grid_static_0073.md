# Static Agent Grid with Enhanced Messaging (Handover 0073)

Status: Canonical UI
Date: 2025-10-29
Supersedes: 0062 (Launch Panel tab pattern), 0066 (Kanban dashboard)

---

## Overview

Handover 0073 introduces the Static Agent Grid as the canonical orchestration UI, replacing the two‑tab Launch/Jobs pattern (0062) and the Kanban dashboard concept (0066). The grid provides a stable, low‑latency, and predictable view of agents, their roles, and messaging status, with a focus on clarity and throughput rather than drag‑and‑drop state changes.

## Why Static Grid over Kanban

- Predictable layout for multi‑terminal workflows
- Lower cognitive load for coordination
- Clear separation between visualization (grid) and control (explicit actions)
- Better alignment with WebSocket event streams and tenant scoping

## Key Features

- Fixed grid of agent roles with status and counters
- Enhanced messaging area with activity summaries
- WebSocket‑driven updates (standardized events and DI)
- Integrated controls for spawning, messaging, and progress updates
- Multi‑tenant filtering, project‑scoped broadcasts

## Events and Integration

- Use `api/dependencies/websocket.py` (DI) and `api/events/schemas.py` (EventFactory)
- Typical events: `project:mission_updated`, `agent:created`, `agent:status_changed`
- See: developer_guides/websocket_events_guide.md

## Supersession Notes

- 0062 (Project Launch Panel) — Grid supersedes the “Active Jobs” tab concept
- 0066 (Agent Kanban Dashboard) — Grid supersedes Kanban board visualization
- Reference: handovers/completed/harmonized/0073_SUPERSEDES_0062_0066-C.md

## Related Documentation

- features/projects_view_v2.md — Project management UI (complements grid)
- STAGE_PROJECT_FEATURE.md — Staging workflow (pairs with grid for execution)
- developer_guides/websocket_events_guide.md — Event DI and schema usage

---

Last Updated: 2025-11-02
Maintainer: Documentation Manager Agent
