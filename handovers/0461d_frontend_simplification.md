# Handover 0461d: Frontend Simplification

**Series**: Handover Simplification Series (0461)
**Color**: Orange (#FF9800)
**Estimated Effort**: 6-8 hours
**Subagents**: `frontend-tester`, `ux-designer`
**Dependencies**: 0461c (need backend endpoint)

---

## Mission Statement

Simplify the frontend to use the new simple handover mechanism. Remove complex succession UI components and update the "Hand Over" action to call the simple-handover endpoint.

**Key Changes**:
- "Hand Over" button calls `/api/agent-jobs/{job_id}/simple-handover`
- Remove `LaunchSuccessorDialog.vue` (no successor to launch)
- Remove `SuccessionTimeline.vue` (no succession chain)
- Remove instance number badges from agent cards
- Handle new `orchestrator:context_reset` WebSocket event

---

## Background

### Current Complex UI

```
Agent Card shows:
- Instance badge (#1, #2, #3...)
- "Hand Over" button → Opens LaunchSuccessorDialog
- LaunchSuccessorDialog → Creates successor, shows launch prompt
- SuccessionTimeline → Shows chain of orchestrator instances
- Status shows "decommissioned" for old instances
```

### New Simple UI

```
Agent Card shows:
- No instance badge (always single agent)
- "Refresh Session" button → Calls simple-handover API
- Shows continuation prompt in clipboard toast
- No succession timeline (no chain)
- No decommissioned status
```

---

## Tasks

### Task 1: Update ActionIcons.vue - Hand Over Action

**File**: `frontend/src/components/StatusBoard/ActionIcons.vue`

Update the `handleHandOver()` method to call the new simple-handover endpoint:

**Current** (lines 72-88 and handler): Opens LaunchSuccessorDialog

**New**: Call API directly and show continuation prompt

```javascript
// In the script section, update the handler:

const handleHandOver = async () => {
  try {
    loadingStates.value.handOver = true

    // Call simple-handover endpoint (Handover 0461d)
    const response = await api.post(`/agent-jobs/${props.job.job_id}/simple-handover`)

    if (response.data.success) {
      // Copy continuation prompt to clipboard
      await navigator.clipboard.writeText(response.data.continuation_prompt)

      // Show success toast
      emit('action', {
        type: 'handOver',
        job: props.job,
        success: true,
        message: 'Session refreshed! Continuation prompt copied to clipboard.'
      })
    } else {
      throw new Error(response.data.error || 'Handover failed')
    }
  } catch (error) {
    emit('action', {
      type: 'handOver',
      job: props.job,
      success: false,
      error: error.message
    })
  } finally {
    loadingStates.value.handOver = false
  }
}
```

**Optional**: Rename the button label from "Hand Over" to "Refresh Session" in the tooltip:

```javascript
// In getActionTooltip():
case 'handOver':
  return 'Refresh Session (reset context)'  // Was: 'Hand Over'
```

### Task 2: Remove LaunchSuccessorDialog.vue

**File**: `frontend/src/components/projects/LaunchSuccessorDialog.vue`

This dialog is no longer needed because:
- No successor agent is created
- Continuation prompt is copied directly to clipboard

**Action**:
1. Remove all imports of `LaunchSuccessorDialog` from parent components
2. Remove the file or mark it as deprecated with a comment at the top

**Files that may import it**:
- `JobsTab.vue`
- `AgentCard.vue`
- `ProjectTabs.vue`

Search and update:
```bash
grep -r "LaunchSuccessorDialog" frontend/src/
```

### Task 3: Remove SuccessionTimeline.vue

**File**: `frontend/src/components/projects/SuccessionTimeline.vue`

This component showed the chain of orchestrator instances. No longer needed.

**Action**:
1. Remove all imports of `SuccessionTimeline` from parent components
2. Remove the file or mark it as deprecated

**Files that may import it**:
- `JobsTab.vue`
- `AgentDetailsModal.vue`

### Task 4: Simplify AgentCard.vue

**File**: `frontend/src/components/AgentCard.vue`

Remove instance number display and decommissioned handling:

1. **Remove instance badge**: Look for `instance_number` display and remove
2. **Remove decommissioned content**: Remove any special handling for `status === 'decommissioned'`
3. **Remove succession chain display**: Remove any `spawned_by` / `succeeded_by` chain visualization

```vue
<!-- REMOVE: Instance badge (example) -->
<v-badge
  v-if="job.instance_number > 1"
  :content="`#${job.instance_number}`"
  color="info"
>
  <!-- ... -->
</v-badge>

<!-- REMOVE: Decommissioned status handling -->
<template v-if="job.status === 'decommissioned'">
  <!-- ... old orchestrator content ... -->
</template>
```

### Task 5: Update agentJobsStore.js - Handle New Event

**File**: `frontend/src/stores/agentJobsStore.js`

Add handler for `orchestrator:context_reset` event:

```javascript
// In the event handlers section:

// Handover 0461d: Handle simple handover context reset
const handleContextReset = (data) => {
  const { agent_id, job_id, old_context_used, new_context_used } = data

  // Find and update the agent
  const agent = agentJobs.value.get(agent_id) || agentJobs.value.get(job_id)
  if (agent) {
    agent.context_used = new_context_used
    // Trigger reactivity
    agentJobs.value.set(agent.agent_id, { ...agent })
  }

  // Optional: Show notification
  console.log(`Context reset for ${agent_id}: ${old_context_used} → ${new_context_used}`)
}

// Export for router
return {
  // ... existing exports ...
  handleContextReset,
}
```

### Task 6: Update websocketEventRouter.js

**File**: `frontend/src/stores/websocketEventRouter.js`

Add routing for the new event:

```javascript
// In the event router:

case 'orchestrator:context_reset':
  agentJobsStore.handleContextReset(data)
  // Optional: Show toast notification
  notificationStore.addNotification({
    type: 'info',
    title: 'Session Refreshed',
    message: `Context reset for orchestrator. Continuation prompt available.`,
  })
  break
```

### Task 7: Simplify JobsTab.vue

**File**: `frontend/src/components/projects/JobsTab.vue`

Remove complex succession logic:

1. **Remove instance_number from card keys**:
   ```javascript
   // OLD: Map key includes instance_number
   :key="`${job.agent_id}-${job.instance_number}`"

   // NEW: Simple key (single card per agent)
   :key="job.agent_id"
   ```

2. **Remove SuccessionTimeline import and usage**

3. **Remove LaunchSuccessorDialog import and usage**

4. **Remove grouping by instance_number** (if any)

### Task 8: Update actionConfig.js

**File**: `frontend/src/utils/actionConfig.js`

Update the handOver action configuration:

```javascript
// Update the handOver action:
handOver: {
  label: 'Refresh Session',  // Was: 'Hand Over'
  icon: 'mdi-refresh',       // Was: 'mdi-hand-wave'
  tooltip: 'Reset context and get continuation prompt',
  availableFor: ['orchestrator'],
  enabledStatuses: ['working', 'blocked'],  // Only active orchestrators
  requiresConfirmation: false,  // No dialog needed now
}
```

### Task 9: Remove/Update Related Tests

**Files**:
- `frontend/src/components/projects/__tests__/LaunchSuccessorDialog.spec.js` - REMOVE
- `frontend/src/components/projects/__tests__/SuccessionTimeline.spec.js` - REMOVE
- `frontend/src/components/projects/__tests__/AgentCardEnhanced.succession.spec.js` - UPDATE
- `frontend/src/stores/agentJobsStore.spec.js` - UPDATE

For each test file:
1. Remove tests for deleted components
2. Add tests for new `orchestrator:context_reset` event handling
3. Update tests that checked `instance_number` behavior

---

## Verification

### Manual Testing

1. **Start dev server**: `cd frontend && npm run dev`
2. **Create project and launch orchestrator**
3. **Click "Refresh Session"** (formerly "Hand Over")
4. **Verify**:
   - API call succeeds
   - Continuation prompt copied to clipboard
   - No dialog shown
   - Context resets (check agent card if displayed)
   - Toast notification appears

### Unit Tests

```bash
cd frontend
npm run test:unit
```

### E2E Tests (if available)

```bash
npm run test:e2e
```

---

## Files Modified Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| `components/StatusBoard/ActionIcons.vue` | UPDATE | ~30 lines |
| `components/projects/LaunchSuccessorDialog.vue` | REMOVE/DEPRECATE | ~0 (mark deprecated) |
| `components/projects/SuccessionTimeline.vue` | REMOVE/DEPRECATE | ~0 (mark deprecated) |
| `components/AgentCard.vue` | SIMPLIFY | ~50 lines |
| `components/projects/JobsTab.vue` | SIMPLIFY | ~30 lines |
| `stores/agentJobsStore.js` | UPDATE | ~20 lines |
| `stores/websocketEventRouter.js` | UPDATE | ~10 lines |
| `utils/actionConfig.js` | UPDATE | ~10 lines |
| Tests | UPDATE/REMOVE | ~100 lines |

**Total**: ~12 files, ~300 lines changed

---

## Success Criteria

- [ ] "Refresh Session" button calls `/api/agent-jobs/{job_id}/simple-handover`
- [ ] Continuation prompt copied to clipboard on success
- [ ] No `LaunchSuccessorDialog` shown
- [ ] No instance number badges on agent cards
- [ ] `orchestrator:context_reset` WebSocket event handled
- [ ] Context resets visually in UI (if displayed)
- [ ] Toast notification shown on handover
- [ ] All unit tests pass
- [ ] No console errors during handover flow

---

## UI Changes Summary

| Before | After |
|--------|-------|
| "Hand Over" button | "Refresh Session" button |
| Opens LaunchSuccessorDialog | Direct API call + clipboard copy |
| Instance badges (#1, #2, #3) | No instance badges |
| SuccessionTimeline component | Removed |
| Multiple agent cards per orchestrator | Single card per orchestrator |
| "decommissioned" status | Not used |

---

## Component Deprecation Strategy

Instead of deleting components immediately:

1. Add deprecation comment at top of file:
   ```vue
   <!--
     DEPRECATED (Handover 0461d): This component is no longer used.
     Simple handover uses direct API call instead of this dialog.
     Will be removed in v4.0.
   -->
   ```

2. Remove imports from parent components
3. Component files remain for rollback safety
4. Delete in future cleanup handover

---

## Rollback

To rollback frontend changes:
```bash
git checkout HEAD -- frontend/src/components/
git checkout HEAD -- frontend/src/stores/
git checkout HEAD -- frontend/src/utils/
```

---

## Next Handover

After 0461d completes, proceed to **0461e: Final Verification & Cleanup**.
