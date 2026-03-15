# Handover 0819a: Project Closeout UI State Management

**Date:** 2026-03-14
**From Agent:** Research/Planning Session
**To Agent:** Next Session (tdd-implementor + ux-designer)
**Priority:** High
**Estimated Complexity:** 3-4 hours
**Status:** Completed
**Edition Scope:** CE

## Task Summary

The CloseoutModal (360 Memory popup) is the decision gate for project lifecycle. After the user clicks "Close Out Project" or "Continue Working" inside this modal, the Jobs tab UI must reflect the new state instead of navigating away or leaving stale buttons visible.

**Current behavior (broken):**
- After "Close Out Project" in modal: page navigates to `/projects` (should stay and show status banner)
- After "Continue Working" in modal: modal closes, no guidance shown (should show guidance text)
- If user navigates back to a completed project: yellow "Close Out Project" button still shows (should show status banner)
- CloseoutModal emits `continue` event but `ProjectTabs.vue` does NOT listen for it

## Context and Background

- CloseoutModal (handover 0361/0498) appears when all agents reach terminal states on the Implementation/Jobs tab
- Two buttons inside the modal: "Continue Working" and "Close Out Project"
- "Close Out Project" calls `POST /api/v1/projects/{id}/archive` -> project becomes `completed` or `terminated`
- "Continue Working" calls `POST /api/v1/projects/{id}/continue-working` -> project goes to `inactive`, agents resume to `waiting`
- The CloseoutModal is the ONE decision point -- UI changes should only trigger from its buttons, not the initial yellow button
- Parallel handover 0819b handles notification clearing (independent, non-blocking)
- Parallel handover 0819c handles replacing "Reopen" with "Review" on the projects list (independent, non-blocking)

## Technical Details

### File: `frontend/src/components/projects/ProjectTabs.vue`

This is the ONLY file that needs modification.

**Key architecture (read before coding):**
- `project` is a **prop** (line 175: `props.project`), accessed as `props.project.status` -- NOT `project.value.status`
- `projectId` is a computed at line 210: `computed(() => props.project?.project_id || props.project?.id || null)`
- `sortedJobs` is a computed from the `useAgentJobs` composable -- contains the list of agent jobs
- `loadProjectData(pid, { fetchProject })` exists at line 322 -- fetches project + jobs data. Pass `{ fetchProject: true }` to refresh the project prop from API
- `showToast` comes from `useToast()` composable (line 161)
- `router` comes from `useRouter()` (line 154)
- Imports are at lines 152-166

**Current code that needs changing:**

1. **Lines 102-114** -- Yellow "Close Out Project" button:
```html
<!-- Close Out Project Button Row (Handover 0361, 0425 - Jobs tab only when all complete) -->
<div v-if="activeTab === 'jobs' && showCloseoutButton" class="action-buttons-row">
  <v-btn
    class="closeout-btn"
    color="yellow-darken-2"
    variant="flat"
    prepend-icon="mdi-check-circle"
    data-testid="close-project-btn"
    @click="openCloseoutModal"
  >
    Close Out Project
  </v-btn>
</div>
```

2. **Lines 140-148** -- CloseoutModal binding (missing `@continue`):
```html
<CloseoutModal
  :show="showCloseoutModal"
  :project-id="project.project_id || project.id"
  :project-name="project.name"
  :product-id="project.product_id"
  @close="showCloseoutModal = false"
  @closeout="handleCloseoutComplete"
/>
```

3. **Lines 305-316** -- `showCloseoutButton` computed (does NOT check project status):
```javascript
const showCloseoutButton = computed(() => {
  const jobs = sortedJobs.value || []
  if (!jobs.length) return false
  const isTerminal = (status) => status === 'complete' || status === 'completed' || status === 'decommissioned'
  const allTerminal = jobs.every((job) => isTerminal(job.status))
  if (!allTerminal) return false
  const orchestrator = jobs.find((job) => job.agent_display_name === 'orchestrator')
  return Boolean(orchestrator && isTerminal(orchestrator.status))
})
```

4. **Lines 570-582** -- `handleCloseoutComplete` (navigates away):
```javascript
function handleCloseoutComplete(closeoutData) {
  const normalized = typeof closeoutData === 'string'
    ? { project_id: closeoutData, sequence_number: 0 }
    : closeoutData || {}
  showToast({ message: `Project closed out successfully (Memory entry #${normalized.sequence_number ?? 0})`, type: 'success' })
  showCloseoutModal.value = false
  router.push('/projects')  // <-- REMOVE THIS
}
```

### Event Flow Gap

```
CloseoutModal.vue defines emits: ['close', 'continue', 'closeout']
ProjectTabs.vue listens:  @close="..."  @closeout="handleCloseoutComplete"
                          @continue is NOT handled <-- GAP TO FIX
```

## Implementation Plan

### Phase 1: Add New Reactive State and Computeds

After line 278 (the `showCloseoutModal` ref), add:

```javascript
const showContinueGuidance = ref(false)

const projectDoneStatus = computed(() => {
  const status = props.project?.status
  if (['completed', 'terminated', 'cancelled'].includes(status)) return status
  return null
})
```

### Phase 2: Update `showCloseoutButton` Computed

Replace the existing computed (lines 305-316) to add project status guard:

```javascript
const showCloseoutButton = computed(() => {
  // Don't show closeout button if project is already in a terminal state
  if (['completed', 'terminated', 'cancelled'].includes(props.project?.status)) return false

  const jobs = sortedJobs.value || []
  if (!jobs.length) return false

  const isTerminal = (status) => status === 'complete' || status === 'completed' || status === 'decommissioned'
  const allTerminal = jobs.every((job) => isTerminal(job.status))
  if (!allTerminal) return false

  const orchestrator = jobs.find((job) => job.agent_display_name === 'orchestrator')
  return Boolean(orchestrator && isTerminal(orchestrator.status))
})
```

### Phase 3: Replace Button Template with Tri-State Area

Replace lines 102-114 with:

```html
<!-- Project Status Area (Jobs tab only) - Handover 0819a -->
<!-- State A: Project is done -> status banner -->
<div v-if="activeTab === 'jobs' && projectDoneStatus" class="action-buttons-row">
  <v-chip
    :color="projectDoneStatus === 'completed' ? 'success' : projectDoneStatus === 'terminated' ? 'warning' : 'grey'"
    variant="flat"
    size="large"
    :prepend-icon="projectDoneStatus === 'cancelled' ? 'mdi-cancel' : 'mdi-check-circle'"
    data-testid="project-done-banner"
  >
    {{ projectDoneStatus === 'completed' ? 'Project Completed and Closed'
       : projectDoneStatus === 'terminated' ? 'Project Terminated'
       : 'Project Cancelled' }}
  </v-chip>
</div>

<!-- State B: All agents terminal, project NOT done -> closeout button -->
<div v-else-if="activeTab === 'jobs' && showCloseoutButton" class="action-buttons-row">
  <v-btn
    class="closeout-btn"
    color="yellow-darken-2"
    variant="flat"
    prepend-icon="mdi-check-circle"
    data-testid="close-project-btn"
    @click="openCloseoutModal"
  >
    Close Out Project
  </v-btn>
</div>

<!-- State C: Continue-working guidance -->
<div v-else-if="activeTab === 'jobs' && showContinueGuidance" class="action-buttons-row">
  <v-chip
    color="info"
    variant="tonal"
    size="large"
    prepend-icon="mdi-information"
    data-testid="continue-guidance"
  >
    Continue working within the agent's terminal session, or use the handover prompt generator next to the orchestrator.
  </v-chip>
</div>
```

### Phase 4: Add `@continue` Handler to CloseoutModal Binding

Replace lines 140-148 with:

```html
<CloseoutModal
  :show="showCloseoutModal"
  :project-id="project.project_id || project.id"
  :project-name="project.name"
  :product-id="project.product_id"
  @close="showCloseoutModal = false"
  @closeout="handleCloseoutComplete"
  @continue="handleContinueWorking"
/>
```

### Phase 5: Modify `handleCloseoutComplete` and Add `handleContinueWorking`

Replace lines 570-582 with:

```javascript
/**
 * Handle project closeout completion (Handover 0819a)
 * Stays on page and refreshes data so status banner appears
 */
async function handleCloseoutComplete() {
  showCloseoutModal.value = false
  showToast({ message: 'Project closed out successfully', type: 'success' })
  // Refresh project data to pick up new completed/terminated status
  await loadProjectData(projectId.value, { fetchProject: true })
}

/**
 * Handle continue working from CloseoutModal (Handover 0819a)
 * Shows guidance text, refreshes agent statuses
 */
async function handleContinueWorking() {
  showCloseoutModal.value = false
  showContinueGuidance.value = true
  showToast({ message: 'Project resumed - agents ready for work', type: 'success' })
  await loadProjectData(projectId.value, { fetchProject: true })
}
```

### Phase 6: Guidance Auto-Dismiss Watcher

Add a watcher (after the existing watchers, around line 415) to dismiss guidance when orchestrator resumes working:

```javascript
// Auto-dismiss continue-working guidance when orchestrator starts working (Handover 0819a)
watch(sortedJobs, (jobs) => {
  if (showContinueGuidance.value && jobs?.length) {
    const orchestrator = jobs.find((j) => j.agent_display_name === 'orchestrator')
    if (orchestrator && orchestrator.status === 'working') {
      showContinueGuidance.value = false
    }
  }
})
```

## Testing Requirements

### Unit Tests (Vitest)

Write tests in `frontend/tests/components/projects/ProjectTabs.closeout.test.js`:

1. `test_closeout_button_hidden_when_project_completed` - mount with `project.status = 'completed'`, verify `showCloseoutButton` is false
2. `test_closeout_button_hidden_when_project_terminated` - same for `'terminated'`
3. `test_closeout_button_hidden_when_project_cancelled` - same for `'cancelled'`
4. `test_done_banner_shows_completed_text` - mount with `project.status = 'completed'`, verify `[data-testid="project-done-banner"]` renders with text "Project Completed and Closed"
5. `test_done_banner_shows_terminated_text` - same for `'terminated'`, text "Project Terminated"
6. `test_done_banner_shows_cancelled_text` - same for `'cancelled'`, text "Project Cancelled"
7. `test_continue_guidance_shows_after_continue_working` - trigger `@continue` event, verify `[data-testid="continue-guidance"]` renders
8. `test_closeout_stays_on_page` - trigger `@closeout` event, verify `router.push` was NOT called

### Manual Testing

1. Open a project with all agents complete -> yellow button visible
2. Click "Close Out Project" -> CloseoutModal opens with 360 Memory
3. Click "Close Out Project" in modal -> modal closes, yellow button gone, green "Project Completed and Closed" chip visible, page does NOT navigate away
4. Navigate to `/projects` and back to the project -> banner still shows
5. Repeat flow but click "Continue Working" -> guidance text appears, yellow button gone
6. Start orchestrator working again -> guidance text disappears

## Success Criteria

- CloseoutModal "Close Out" -> stays on page, status banner replaces button
- CloseoutModal "Continue Working" -> guidance text replaces button, auto-dismisses when orchestrator works
- Direct navigation to done project -> status banner shows immediately
- No regressions to existing closeout flow

## Dependencies

- None (standalone, single-file change)

## Rollback Plan

Revert changes to `ProjectTabs.vue`. No backend, no database, no migration.

## Implementation Summary

### What Was Built
- Tri-state status area on Jobs tab: done banner, closeout button, continue guidance
- `projectDoneStatus` computed guards against showing closeout button for terminal projects
- `handleCloseoutComplete` stays on page, refreshes data to show banner
- `handleContinueWorking` shows guidance chip, refreshes agent statuses
- Auto-dismiss watcher clears guidance when orchestrator resumes working
- `@continue` event wired from CloseoutModal

### Files Modified
- `frontend/src/components/projects/ProjectTabs.vue` (all 6 phases)
- `frontend/tests/components/projects/ProjectTabs.closeout.spec.js` (new, 8 tests)

### Tests
8/8 passing: button hidden for completed/terminated/cancelled, banner text for each, continue guidance shows, closeout stays on page.
