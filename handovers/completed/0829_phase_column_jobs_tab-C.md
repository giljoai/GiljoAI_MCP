# 0829 — Phase Column & Sort Order in Jobs Tab

**Edition Scope:** CE
**Priority:** Low (polish, non-blocking)
**Status:** COMPLETE (2026-03-20, `4af6dad5`)
**Date:** 2026-03-20
**Origin:** Multi-terminal alpha trial UX observation. The "Proposed Execution Order" bar above the Jobs table shows phase ordering, but the table itself is unsorted and has no phase indicator per row.

---

## Problem

The Jobs tab shows agents in an arbitrary order that doesn't match the execution order displayed directly above it. Users must mentally cross-reference the "Proposed Execution Order" bar (`Start Orchestrator · Phase 1 folder-creator · Phase 2 file-creator`) with the unsorted table rows. In a 5-6 agent project, this becomes confusing.

---

## Solution

Two changes, both frontend-only:

### 1. Add "Phase" Column

Add a narrow column to the Jobs table between the play button and "Agent Name" column.

**Column header:** `Phase`

**Cell content:** A small pill badge matching the existing execution order bar style:

| Agent Role | Badge | Notes |
|-----------|-------|-------|
| Orchestrator | `—` | Dash, not a phase number. Always first. |
| Phase 1 agents | `P1` | |
| Phase 2 agents | `P2` | All agents in the same phase show the same badge |
| Phase 3 agents | `P3` | |
| Unphased agents | `—` | Fallback if phase field is null |

**Badge styling:** Reuse the existing pill badge style from the execution order bar (compact, colored). Keep it small — this is a narrow column. Suggested: `font-size: 0.75rem`, `padding: 2px 8px`, `border-radius: 10px`, background color matching the phase color already used in the execution order bar.

### 2. Sort Table by Phase Order

Sort the Jobs table rows by phase, ascending. Within the same phase, preserve existing order (creation order or agent name alpha — whichever is current).

**Sort key:** `phase` field on the job model (added by 0411a). Orchestrator (phase 0 or null with role "orchestrator") always sorts first.

**Sort logic:**
```javascript
// Orchestrator first, then by phase number, then by creation order
jobs.sort((a, b) => {
    const phaseA = a.role === 'orchestrator' ? -1 : (a.phase ?? 999);
    const phaseB = b.role === 'orchestrator' ? -1 : (b.phase ?? 999);
    if (phaseA !== phaseB) return phaseA - phaseB;
    return 0; // preserve existing order within same phase
});
```

**Note:** Check how the `phase` field is exposed. 0411a added it — verify it's included in the API response (`JobResponse` model) and available in the Pinia store. If it's only used for the execution order bar rendering and not passed to the table data, it may need to be threaded through.

---

## Files Impacted

- `frontend/src/components/JobsTab.vue` — Add Phase column to table headers and row template, add sort logic to the computed property that feeds the table

That's it. One file. No backend changes. No migration. No new dependencies.

---

## Edge Cases

- **No phases assigned:** If staging didn't assign phases (older projects, or single-agent projects), all agents show `—` and sort order is unchanged.
- **Phase data only on job, not execution:** Verify which model carries the `phase` field. If it's on `AgentJob` but the table iterates `AgentExecution`, the join/lookup needs to be correct. 0411a's implementation will clarify this.

---

## Tests

- Frontend: Table rows render in phase order (Orchestrator → P1 → P2 → P3)
- Frontend: Phase badge shows correct value per row
- Frontend: Unphased agents show `—` and sort last
- Frontend: Multiple agents in same phase all show same badge (e.g., three P2 agents)

---

## Success Criteria

- [ ] Jobs table sorted by phase order, orchestrator always first
- [ ] "Phase" column visible with compact pill badges
- [ ] Visual alignment with existing execution order bar styling
- [ ] No regression on existing Jobs tab functionality (status, duration, steps, messages, actions)

---

## Rollback

Remove the Phase column and sort logic from `JobsTab.vue`. Table reverts to previous ordering.

---

## Implementation Summary

**Status:** Completed | **Date:** 2026-03-20

### What Was Built
- **Phase column**: Narrow column before "Agent Name" with compact pill badges (P1, P2, etc.)
- **Phase sort**: `phaseSortedAgents` computed wraps store's `sortedAgents` — orchestrator first, then ascending phase, unphased last
- **Badge styling**: Colored pills (0.75rem, 10px border-radius), 6-color palette
- **Test**: 1 test verifying sort order + badge content for all agent types

### Key Files Modified
- `frontend/src/components/projects/JobsTab.vue` — Phase column header, phase-cell TD, `phaseSortedAgents` computed, `getPhaseColor` helper, CSS
- `frontend/tests/unit/components/projects/JobsTab.0829.spec.js` — New test file (1 test, passing)

### Design Decisions
- Sort applied as local computed in JobsTab rather than modifying shared `agentJobsStore.sortedJobs`
- Orchestrator always shows `—` (never a phase number), matching execution order bar
- Phase colors: fixed palette indexed by `(phase - 1) % 6`
