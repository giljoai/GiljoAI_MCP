# Handover 0960: Orchestrator Auto Check-in Interval Slider

**Edition Scope:** CE
**Date:** 2026-04-06
**Priority:** Medium
**Estimated Effort:** 2-4 hours
**Status:** Not Started

---

## Task Summary

Replace the current auto check-in button group (30s, 60s, 90s) with a slider control using minute-based intervals: 5, 10, 15, 20, 30, 40, 60 minutes. The layout becomes a single row: "Orchestrator auto check-in {toggle on/off} {slider}". Backend column changes from seconds to minutes. Protocol injection updated to match.

## Context / Background

Handover 0904 introduced the auto check-in feature with a v-btn-toggle offering three second-based intervals (30, 60, 90 seconds). User feedback: the intervals are too short and the button group takes too much space. The desired UX is a compact slider with meaningful minute-based intervals that scales from 5 to 60 minutes.

The auto check-in feature injects a polling instruction into the orchestrator's protocol during multi-terminal implementation mode. The orchestrator periodically calls `get_workflow_status` to check on spawned agents.

## Current State (What Exists)

### Frontend
- `AutoCheckinControls.vue`: Standalone component with v-switch toggle + v-btn-toggle (30/60/90 seconds)
- `JobsTab.vue`: Parent that manages persistence via `api.projects.update()`
- Props: `enabled` (Boolean), `interval` (Number, seconds)
- Emits: `toggle-checkin`, `change-interval`

### Backend
- `Project.auto_checkin_enabled` (Boolean, default false)
- `Project.auto_checkin_interval` (Integer, default 60, comment says "seconds (30, 60, or 90)")
- Protocol injection in `chapters_reference.py` and `protocol_builder.py` reads these fields and injects polling instructions into orchestrator prompt

### Storage
- Column: `projects.auto_checkin_interval` (Integer, server_default 60)
- No migration needed if we reuse the column (just change the unit interpretation)

## Implementation Plan

### Phase 1: Backend (column semantics + validation)

1. **Change column semantics from seconds to minutes.** Update `Project.auto_checkin_interval`:
   - Default: `60` seconds -> `10` minutes
   - Server default: `text("10")`
   - Comment: "Auto check-in interval in minutes (5, 10, 15, 20, 30, 40, 60)"
   - Requires incremental migration with idempotency guard to convert existing rows: `UPDATE projects SET auto_checkin_interval = GREATEST(5, auto_checkin_interval / 60) WHERE auto_checkin_interval > 60`

2. **Validate accepted values in ProjectService.** The update path in `project_service.py` should validate `auto_checkin_interval` is one of `[5, 10, 15, 20, 30, 40, 60]`. Reject invalid values with `ValidationError`.

3. **Update protocol injection.** In `chapters_reference.py` and `protocol_builder.py`, the interval is read from the project and injected into the orchestrator's polling instruction. Change the unit from seconds to minutes in the generated prompt text.

### Phase 2: Frontend (slider component)

1. **Replace v-btn-toggle with v-slider in `AutoCheckinControls.vue`:**
   - Vuetify `v-slider` with `tick-labels` and `step` snapping to the defined intervals
   - Since the intervals are non-linear (5, 10, 15, 20, 30, 40, 60), use a mapped index slider: slider value 0-6 maps to the interval array
   - Display the current value as "{N} min" label
   - Compact single-row layout: label | toggle | slider

2. **Update layout to single row:**
   - Current: label on left, toggle on right, interval buttons below (shown only when enabled)
   - New: "Orchestrator auto check-in" label, toggle switch, slider (slider visible only when enabled, same row or wrapping gracefully)

3. **Update props and emits:** `interval` prop changes from seconds to minutes. No new props needed.

4. **Update `JobsTab.vue`:** The `autoCheckinInterval` ref default changes from `60` (seconds) to `10` (minutes). The watchers and API calls remain the same (they pass the value through to `api.projects.update`).

### Phase 3: Migration

1. **Incremental Alembic migration** with idempotency guard:
   - Convert existing `auto_checkin_interval` values from seconds to minutes (divide by 60, floor to nearest valid step, minimum 5)
   - Update server_default from 60 to 10
   - Follow migration protocol from HANDOVER_INSTRUCTIONS.md

## Affected Files

| File | Change |
|------|--------|
| `src/giljo_mcp/models/projects.py` | Column default + comment |
| `src/giljo_mcp/services/project_service.py` | Validation for accepted interval values |
| `src/giljo_mcp/services/protocol_sections/chapters_reference.py` | Seconds to minutes in prompt text |
| `src/giljo_mcp/services/protocol_builder.py` | Seconds to minutes in prompt text |
| `frontend/src/components/projects/AutoCheckinControls.vue` | Replace v-btn-toggle with v-slider |
| `frontend/src/components/projects/JobsTab.vue` | Default interval value |
| `migrations/versions/` | New incremental migration |

## Acceptance Criteria

1. Toggle on/off works as before
2. Slider snaps to exactly: 5, 10, 15, 20, 30, 40, 60 minutes
3. Selected interval persists to DB and survives page reload
4. Protocol injection shows correct minute-based interval in orchestrator prompt
5. Existing projects with old second-based values are migrated correctly
6. Slider is disabled/hidden when toggle is off
7. No visual regression on the Jobs tab implementation panel

## Quality Gates

- No new files created (modify existing components)
- No commented-out code
- Exception-based error handling for validation
- Migration includes idempotency guard
- Design tokens used for styling (no hardcoded hex values)
- Smooth borders on any rounded elements (smooth-border class)
