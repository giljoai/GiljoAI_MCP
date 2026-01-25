# Handover 0463: Ghost Agents (Cross-Project Agent Rows / Event Leak)

**Status:** Ready for Implementation  
**Priority:** HIGH (Production UX + Data Isolation Bug)  
**Type:** Bug Fix - Realtime Event Scoping (Backend + Frontend)  
**Estimated Hours:** 6-10 hours  
**Date Created:** 2026-01-25  

---

## Executive Summary

Users intermittently see **“ghost agents”** (agent/job rows that do not belong to the currently viewed project) in the UI. These rows **vanish on refresh or tab navigation**, because the authoritative API reload replaces the local store with the correct project’s job list.

This bug surfaced after the “complex handover/succession model” work (0460/0461 era), because the system began emitting more realtime job events across more projects/jobs in the same tenant — exposing an architectural issue in WebSocket event scoping.

**Root Cause (most likely):**
1. Backend emits `agent:status_changed` as a **tenant-wide broadcast** without `project_id`.
2. Frontend routes that event into the per-project Agent Jobs store (`upsertJob`) even when the job is **not part of the active project**.
3. Without `project_id`, the frontend cannot reliably filter the event, so it materializes as a ghost row until the next API reload.

**Why this is product-critical:** it is a **cross-project data leak inside a tenant** (not cross-tenant, but still a serious isolation failure) and produces confusing, non-deterministic UI behavior — not commercialization-ready.

---

## Validate the Handover Number (0463)

`HANDOVER_CATALOGUE.md` was last updated on **2026-01-22** and does not list newer 0460+ items. The repo already contains:
- `handovers/0462_ghost_agent_avatar_fix.md`

Therefore the next available, consistent number for this new issue is **0463**.

---

## Symptoms (User-Facing)

Observed behaviors (confirmed in UI report + code inspection):
- A project page shows an agent/job row whose ID does not belong to the project (example: `a594875c-...`).
- The row disappears after:
  - browser refresh, or
  - navigating between tabs/views that triggers `loadJobs(projectId)` and `setJobs(...)`.
- The ghost row often appears during active orchestration or when other projects in the tenant are running.

---

## Historical Context (Aligning with 0460/0461/0440 Narrative)

Your reported chain-of-events aligns with the architecture:
- 0460 introduced a more complex orchestration/succession model → more jobs/executions → more realtime events → more opportunities for mis-scoped routing to become visible.
- Several fixes addressed duplicates and “?? avatars” (see 0462), but **this ghost-row issue is distinct**: it is about **project scoping** of events, not only identity-field completeness.
- 0440 (taxonomy) was a simplification/organization feature and is not causally related to agent/job event routing. It didn’t introduce the realtime routing architecture (that originated in the 0379 series).

In short: 0440 wasn’t the cause; the “monster” era increased event volume and made a pre-existing scoping flaw observable.

---

## Technical Root Cause Analysis

### Finding 1: Backend sends `agent:status_changed` without `project_id`

In `api/websocket.py`, `broadcast_job_status_update(...)` builds:
```py
message_data = {
  "job_id": job_id,
  "agent_display_name": agent_display_name,
  "old_status": old_status,
  "status": new_status,
  "tenant_key": tenant_key,
  "updated_at": ...,
}
```
and broadcasts to tenant via `broadcast_event_to_tenant(...)`.

This means every client in the tenant receives job status updates for every job, regardless of which project view is open, and the client cannot filter by project because the event does not carry `project_id`.

### Finding 2: Frontend routes `agent:status_changed` into the Agent Jobs store unconditionally

In `frontend/src/stores/websocketEventRouter.js`:
- `defaultShouldRoute(...)` enforces tenant isolation only; it does not enforce project isolation.
- The event map routes:
  - `'agent:status_changed': { store: 'agentJobs', action: 'handleStatusChanged' }`

In `frontend/src/stores/agentJobsStore.js`:
- `handleStatusChanged(payload)` calls `upsertJob(payload)`.
- `upsertJob(...)` is explicitly designed to create new entries when it cannot find an existing one.

So a `status_changed` event for a job not present in the current project’s store creates a new “row”.

### Finding 3: Why it disappears on refresh/navigation

Project pages call `loadJobs(projectId)` and then `setJobs(jobs)` which replaces the entire map with server-provided jobs for that project. Any locally-created “ghost row” (not returned by the API for this project) disappears.

---

## Proposed Fix (Production-Grade / Commercialization-Ready)

This fix should be treated as a correctness + isolation hardening change.

### Design Goals

1. **Project-scoped realtime**: a project UI should only reflect events from its project.
2. **Defense-in-depth**:
   - Backend should not leak cross-project events to unrelated clients.
   - Frontend should still protect itself (filter/drop mismatched events).
3. **Backwards compatibility**: avoid breaking existing clients during rollout.

### Plan Overview (2-Layer Fix)

#### Layer A (Backend, required): include `project_id` in job status events

Update `agent:status_changed` to always include `project_id`.

Implementation options:
- **Preferred**: change the broadcaster call sites (e.g., in `OrchestrationService`) to pass `project_id` directly into `broadcast_job_status_update`.
- **Fallback**: if only `job_id` is available at broadcast time, look up `project_id` from the DB (by job_id) before emitting.

Also include stable identity fields when available (optional but recommended):
- `agent_id`
- `execution_id`
- `instance_number`

Why: consistent payloads reduce UI edge cases and prevent “incomplete row” formation in future changes.

#### Layer B (Backend, ideal): broadcast to project subscribers, not the whole tenant

Your WebSocket manager already supports entity subscriptions (`subscribe('project', projectId)`), but `broadcast_event_to_tenant` ignores subscriptions.

Add a new method (recommended):
- `broadcast_event_to_entity_subscribers(entity_type, entity_id, tenant_key, event, exclude_client=None)`
  - sends the canonical tenant envelope, but only to clients subscribed to `${entity_type}:${entity_id}`

Then, for job status events:
- broadcast `agent:status_changed` only to subscribers of `project:{project_id}`

This reduces bandwidth and prevents cross-project UI artifacts by construction.

#### Layer C (Frontend, required): project-aware routing filter

Enhance `defaultShouldRoute(...)` in `frontend/src/stores/websocketEventRouter.js`:
- Determine current active project id from `useProjectTabsStore().currentProject`
- If `payload.project_id` exists and active project exists:
  - route only if they match
- If `payload.project_id` is missing:
  - for project-scoped job events (including `agent:status_changed`), **drop** or **quarantine** the event (log/debug counter), because it cannot be safely associated with the active project.

This is defense-in-depth: even if a backend misconfiguration occurs, the UI won’t materialize ghost rows.

---

## Detailed Task Breakdown (TDD-Oriented)

### Backend Tasks

1. **Add project_id to `agent:status_changed` payload**
   - Update `api/websocket.py` `broadcast_job_status_update(...)` to accept/attach `project_id`.
   - Update call sites to provide correct project_id.
   - Add regression tests asserting emitted payload includes `project_id`.

2. **Implement project-scoped broadcast (recommended)**
   - Add `broadcast_event_to_entity_subscribers(...)` to the websocket manager.
   - Use it for job status updates (project scope).
   - Add tests:
     - client subscribed to project A does not receive project B job status changes.

3. **Keep backward compatibility**
   - During rollout, optionally emit both:
     - tenant-wide event (legacy) AND
     - project-scoped event (new),
     for a short migration window, then remove legacy.
   - Alternatively: keep tenant-wide but rely on frontend filter (less ideal).

### Frontend Tasks

4. **Project-aware routing filter**
   - Update `defaultShouldRoute` logic to enforce project match when payload has project_id and there is a current project.
   - Add unit tests in `frontend/src/stores/websocketEventRouter.spec.js`:
     - routes matching tenant+project
     - drops mismatched project
     - drops missing-project-id for `agent:status_changed` while in project view

5. **Hardening in agentJobsStore (optional)**
   - Consider a strict mode: refuse to `upsertJob` from status-only events unless the job already exists in the project store.
   - This is optional if backend+router fixes are correct, but it’s a strong additional safety net.

---

## Acceptance Criteria (Must-Haves)

1. Open Project A in tenant X, while Project B has active jobs:
   - no new agents from Project B appear in Project A’s agent/job lists.
2. Status chips and progress still update in real-time for jobs in the active project.
3. No regression in 0462 “?? avatar” behavior:
   - identity fields remain intact in early progress/ack events.
4. Tests:
   - backend tests cover `project_id` inclusion + scoping behavior
   - frontend tests cover routing filter behavior

---

## Risks & Mitigations

- **Risk:** existing clients rely on tenant-wide status broadcasts.
  - **Mitigation:** dual-emit for a deprecation window, or deploy frontend filter first, then backend scoping.
- **Risk:** some events genuinely lack project_id at source.
  - **Mitigation:** DB lookup at broadcast time (bounded, cached, or via service-layer injection).

---

## Key Files (Expected Touchpoints)

Backend:
- `api/websocket.py` (status update broadcast + new scoped broadcast helper)
- `src/giljo_mcp/services/orchestration_service.py` (ensure project_id available at emit time)
- `tests/` (new regression tests)

Frontend:
- `frontend/src/stores/websocketEventRouter.js` (project-aware filter)
- `frontend/src/stores/websocketEventRouter.spec.js` (tests)
- `frontend/src/stores/projectTabs.js` (already provides currentProject; use as source of truth)

---

## Notes / Relationship to Existing Handovers

- **0462** addresses “?? avatar” (identity field race / store overwrites).  
  0463 is complementary: it addresses **cross-project ghost rows** via event scoping.
- This issue became visible during the 0460 complexity phase, and remained after simplification (0461), because the underlying event scoping was never made project-safe.

