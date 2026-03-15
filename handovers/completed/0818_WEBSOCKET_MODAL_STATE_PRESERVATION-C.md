# Handover 0818: WebSocket Modal State Preservation

**Date:** 2026-03-14
**Priority:** Medium
**Estimated Complexity:** 6-9 hours
**Status:** Completed
**Edition Scope:** CE

## Completion Summary

**Completed:** 2026-03-15
**Commits:** `d0bcbccb` (Phase 1+2: deep equality + debounced batching), `1ae57033` (Phase 3 tests), `a8fde2d4` (Phase 3: snapshot pattern), `0082cd0c` (12 additional tests)
**Result:** All 3 phases implemented. Modal state preserved during WebSocket updates. Deep equality reduces unnecessary re-renders, debounced batching for counter events, snapshot pattern for MessageAuditModal + AgentJobModal.

---

## Task Summary

WebSocket events cause Vue modals on the Jobs tab to lose user interaction state. When agents send progress updates or messages while a user has expanded content in a modal (message details, job plans), the modal flickers, collapses expanded items, and resets scroll position. This makes reading agent messages during active orchestration sessions frustrating.

## Root Cause

`agentJobsStore.upsertJob()` creates a new `Map` reference for `jobsById` on every WebSocket update (line ~178). This triggers the full reactivity cascade:

```
WebSocket event -> upsertJob() -> new Map ref -> sortedJobs recomputes
-> JobsTab re-renders -> modal props get new object references
-> modal watchers fire -> fetchMessages() / loading states -> UI resets
```

High-frequency events (`message:sent`, `job:progress_update`) fire dozens of times per minute during active orchestration, making the problem very visible.

## Affected Components

| Component | File | What Resets |
|-----------|------|-------------|
| MessageAuditModal | `frontend/src/components/projects/MessageAuditModal.vue` | `expandedMessages` Set collapses, loading flash during re-fetch |
| AgentJobModal | `frontend/src/components/projects/AgentJobModal.vue` | Plan/TODO tab refreshes, scroll position lost |
| AgentDetailsModal | `frontend/src/components/projects/AgentDetailsModal.vue` | Minor (fetches once on open, less affected) |

## Implementation Plan

Three independent phases, each deployable separately. Each phase independently improves UX.

### Phase 1: Enhanced Equality Check in upsertJob (1-2 hours)

**File:** `frontend/src/stores/agentJobsStore.js`

Replace the existing `JSON.stringify` equality check with deep equality (`lodash-es/isEqual` or equivalent). Skip creating a new Map reference when the incoming patch produces an identical normalized job object.

**Expected impact:** ~30% reduction in unnecessary re-renders (redundant WebSocket payloads that carry no actual data change).

**Tests:**
- Unit test: `upsertJob` with identical data does not trigger reactivity (jobsById reference unchanged)
- Unit test: `upsertJob` with changed data still triggers reactivity

### Phase 2: Debounced Store Updates for Minor Events (3-4 hours)

**File:** `frontend/src/stores/agentJobsStore.js`

Batch rapid-fire WebSocket updates with a ~300ms debounce window. Merge pending patches per unique key, then flush once as a single Map replacement.

**Critical:** Status changes (`agent:status_changed`) must flush immediately via `flushPendingUpdates.flush()` -- do NOT debounce lifecycle transitions. Only debounce counter/progress events (`message:sent`, `message:received`, `message:acknowledged`, `job:progress_update`).

**Expected impact:** ~60-70% reduction in re-renders during active sessions.

**Tests:**
- Unit test: 3 rapid `upsertJob` calls within 300ms produce exactly 1 Map reference change
- Unit test: `handleStatusChanged` flushes immediately (no debounce delay)
- Unit test: debounced updates merge correctly (last value wins per field)

### Phase 3: Modal State Snapshot on Open (2-3 hours)

**Files:**
- `frontend/src/components/projects/MessageAuditModal.vue`
- `frontend/src/components/projects/AgentJobModal.vue`
- `frontend/src/components/projects/JobsTab.vue`

Each modal takes a shallow clone of the agent prop on open, disconnecting from live store reactivity while visible. Local UI state (`expandedMessages`, scroll position, active tab) is preserved across WebSocket updates. State resets only on explicit user close.

**Pattern:**
```javascript
const agentSnapshot = shallowRef(null)

watch(() => props.show, (visible) => {
  if (visible) {
    agentSnapshot.value = { ...toRaw(props.agent) }
    // fetch data using snapshot
  } else {
    // reset local state on close
  }
})
```

**Trade-off:** Modal shows data as of open time. User closes and reopens to see latest. Acceptable for read-only message viewing and plan inspection.

**Tests:**
- Component test: expanded messages persist when `props.agent` reference changes
- Component test: closing modal resets expanded state
- Component test: reopening modal fetches fresh data

## Key Files

| File | Changes |
|------|---------|
| `frontend/src/stores/agentJobsStore.js` | Phase 1 + 2: equality check, debounce logic |
| `frontend/src/components/projects/MessageAuditModal.vue` | Phase 3: snapshot pattern |
| `frontend/src/components/projects/AgentJobModal.vue` | Phase 3: snapshot pattern |
| `frontend/src/components/projects/JobsTab.vue` | Phase 3: minor prop adjustments if needed |

## Dependencies

- `lodash-es` (likely already installed -- verify before adding)

## Success Criteria

- User can expand messages in MessageAuditModal while agents are actively sending updates -- expanded state persists
- User can read Plan/TODO items in AgentJobModal without scroll jumps during `job:progress_update` events
- Status changes (agent lifecycle) still reflect immediately on the Jobs tab cards
- All existing frontend tests pass
- New tests cover the three phases

## Rollback Plan

Each phase is independent. Revert the specific commit for the phase that causes issues. No database changes, no backend changes, no migration impact.

## Recommended Sub-Agent

`tdd-implementor` for Phase 1+2 (store logic with unit tests), `frontend-tester` for Phase 3 validation.
