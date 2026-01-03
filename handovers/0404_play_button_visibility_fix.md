# Handover 0404: Play Button Visibility Fix

**Date:** 2026-01-02
**From Agent:** Orchestrator Session
**To Agent:** N/A (Complete)
**Priority:** Medium
**Estimated Complexity:** 15 minutes
**Status:** Complete

---

## Task Summary

Fix the play button (arrow icon) showing on all agents instead of only the orchestrator when in `claude_code_cli` mode.

**Symptom:** When navigating to the IMPLEMENT tab after staging completes, all agents showed the play button until a manual browser refresh.

---

## Root Cause

**File:** `frontend/src/components/projects/ProjectTabs.vue`

There was a disconnect between two execution_mode sources:

1. **Line 222:** Local `executionMode` ref - updated by `handleExecutionModeChanged()`
2. **Line 91:** JobsTab received `props.project` - never updated after initial load

When the user toggled execution mode or staging completed:
- The local ref was updated correctly
- But `props.project.execution_mode` remained stale
- JobsTab read the stale value, showing wrong button visibility

---

## Solution

Created a computed property that merges the updated `executionMode` ref into the project object:

```javascript
const projectWithUpdatedMode = computed(() => ({
  ...props.project,
  execution_mode: executionMode.value,
}))
```

Then passed this computed to JobsTab instead of the stale prop:

```vue
<JobsTab :project="projectWithUpdatedMode" ...>
```

---

## Files Modified

| File | Changes |
|------|---------|
| `frontend/src/components/projects/ProjectTabs.vue` | Added computed property, updated JobsTab binding |

---

## Testing

1. Set execution mode to `claude_code_cli` in LaunchTab
2. Run staging to completion
3. Navigate to IMPLEMENT tab
4. Verify: Only orchestrator shows play button
5. Other agents should show no play button
6. No manual refresh needed

---

## Related

- Handover 0335: execution-mode-changed event
- Handover 0379: WebSocket routing refactor (when regression was introduced)

---

## Progress Updates

### 2026-01-02 - Complete
**Status:** Fixed
**Commit:** (pending)
**Root Cause:** Props not synced with local ref after event handler update
