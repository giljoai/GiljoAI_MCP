# Handover 0819c: Project Review Modal (Replace Reopen)

**Date:** 2026-03-14
**From Agent:** Research/Planning Session
**To Agent:** Next Session (ux-designer + tdd-implementor)
**Priority:** Medium
**Estimated Complexity:** 6-8 hours
**Status:** Not Started
**Edition Scope:** CE

## Task Summary

Replace the "Reopen" action on `completed` and `terminated` projects with a "Review" action that opens a read-only modal showing the project's full history. Completed projects should remain completed -- the only time to "keep working" is in the CloseoutModal while terminals are still alive.

**Key design decision:** Cancelled projects KEEP "Reopen" because cancelling means "I didn't finish" (may legitimately want to resume). Completed/terminated means "this work is done" and the historical record should have integrity.

## Context and Background

- Reopening a completed project days/weeks later muddies auditable data: 360 Memory, comms, todos, agent history
- A completed project's detail page is already navigable (no status gate), but there's no clean summary view
- The Review modal replaces the need to navigate into staging/implementation tabs on a done project
- The Review modal is purely read-only -- no state changes possible
- All data is available through existing API endpoints -- NO new backend work needed

## Technical Details

### File 1: `frontend/src/components/StatusBadge.vue`

**Current action definitions (lines 175-225):**
```javascript
const actionDefinitions = {
  activate: { value: 'activate', label: 'Activate', icon: 'mdi-play', newStatus: 'active', destructive: false, requiresConfirm: false },
  deactivate: { value: 'deactivate', label: 'Deactivate', icon: 'mdi-pause-circle-outline', newStatus: 'inactive', destructive: false, requiresConfirm: true },
  complete: { value: 'complete', label: 'Complete', icon: 'mdi-check-circle', newStatus: 'completed', destructive: false, requiresConfirm: true },
  cancel: { value: 'cancel', label: 'Cancel', icon: 'mdi-cancel', newStatus: 'cancelled', destructive: true, requiresConfirm: true },
  reopen: { value: 'reopen', label: 'Reopen', icon: 'mdi-restore', newStatus: 'inactive', destructive: false, requiresConfirm: false },
  delete: { value: 'delete', label: 'Delete', icon: 'mdi-delete', newStatus: null, destructive: true, requiresConfirm: true },
}
```

**Current action mapping (lines 228-233):**
```javascript
const actionsByStatus = {
  inactive: ['activate', 'complete', 'cancel'],
  active: ['deactivate', 'complete', 'cancel'],
  completed: ['reopen'],     // <-- CHANGE to ['review']
  cancelled: ['reopen'],     // <-- KEEP as-is
}
// Note: 'terminated' has no entry -- currently no actions available
```

**Changes needed:**
1. Add `review` to `actionDefinitions` (after `reopen`, before `delete`):
```javascript
review: {
  value: 'review',
  label: 'Review',
  icon: 'mdi-eye',
  newStatus: null,    // No state change -- read-only action
  destructive: false,
  requiresConfirm: false,
},
```

2. Update `actionsByStatus`:
```javascript
const actionsByStatus = {
  inactive: ['activate', 'complete', 'cancel'],
  active: ['deactivate', 'complete', 'cancel'],
  completed: ['review'],
  cancelled: ['reopen'],
  terminated: ['review'],
}
```

### File 2: `frontend/src/views/ProjectsView.vue`

**`handleStatusAction` function at line 1297-1338:**

This switch statement handles all StatusBadge action clicks. Add a `review` case.

**Current relevant code:**
```javascript
async function handleStatusAction({ action, projectId }) {
  try {
    switch (action) {
      case 'activate':
        await projectStore.activateProject(projectId)
        break
      // ... other cases ...
      case 'complete': {
        // Opens ManualCloseoutModal
        const projectToClose = projectStore.projectById(projectId)
        closeoutProjectId.value = projectId
        closeoutProjectName.value = projectToClose.name
        showCloseoutModal.value = true
        break
      }
      case 'reopen':
        await projectStore.restoreCompletedProject(projectId)
        break
      // ... etc
    }
  }
}
```

**Add `review` case before the closing of the switch:**
```javascript
case 'review': {
  const projectToReview = projectStore.projectById(projectId)
  reviewProjectId.value = projectId
  reviewProductId.value = projectToReview?.product_id
  showReviewModal.value = true
  break
}
```

**Add reactive state (near the existing closeout modal state, around line 760-770):**
```javascript
const showReviewModal = ref(false)
const reviewProjectId = ref(null)
const reviewProductId = ref(null)
```

**Add component import (near line 730 where ManualCloseoutModal is imported):**
```javascript
import ProjectReviewModal from '@/components/projects/ProjectReviewModal.vue'
```

**Add template binding (near line 713-719 where ManualCloseoutModal is bound):**

Follow the same pattern as the existing ManualCloseoutModal binding:
```html
<!-- Existing pattern to follow: -->
<ManualCloseoutModal
  :show="showCloseoutModal"
  :project-id="closeoutProjectId"
  :project-name="closeoutProjectName"
  @close="handleCloseoutClose"
  @completed="handleCloseoutComplete"
/>

<!-- Add below it: -->
<ProjectReviewModal
  :show="showReviewModal"
  :project-id="reviewProjectId"
  :product-id="reviewProductId"
  @close="showReviewModal = false; reviewProjectId = null; reviewProductId = null"
/>
```

### File 3 (NEW): `frontend/src/components/projects/ProjectReviewModal.vue`

New component. Read-only modal displaying project summary.

**Existing API endpoints to use (no new backend needed):**

| Data | API Call | api.js Line | Notes |
|------|----------|-------------|-------|
| Project details | `api.projects.get(projectId)` | ~line 255 | Returns `{ data: { name, description, status, mission, created_at, completed_at, ... } }` |
| Agent jobs | `api.agentJobs.list(projectId)` | line 456 | Maps to `GET /api/agent-jobs/?project_id=projectId`. Returns array of jobs with `agent_display_name`, `status`, `agent_role` |
| Job messages | `api.agentJobs.messages(jobId)` | line 469 | Maps to `GET /api/agent-jobs/{jobId}/messages`. Alternative: `api.messages.list({ job_id: jobId })` (line 298) |
| 360 Memory | `api.products.getMemoryEntries(productId, { project_id: projectId })` | line 238 | Returns `{ data: { entries: [...] } }` (same call used by CloseoutModal) |

**Component structure:**

```vue
<template>
  <v-dialog
    :model-value="show"
    :fullscreen="isMobile"
    :max-width="isMobile ? undefined : '1000'"
    persistent
    role="dialog"
    aria-labelledby="review-modal-title"
    data-testid="review-modal"
    @keydown.esc="$emit('close')"
  >
    <v-card>
      <!-- Header -->
      <v-card-title id="review-modal-title" class="bg-primary text-white pa-4">
        <div class="d-flex align-center justify-space-between">
          <div class="d-flex align-center">
            <v-icon icon="mdi-eye" size="large" class="mr-2" />
            <span class="text-h6">Project Review: {{ projectData?.name }}</span>
          </div>
          <v-btn icon variant="text" color="white" aria-label="Close modal" @click="$emit('close')">
            <v-icon icon="mdi-close" />
          </v-btn>
        </div>
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-4" style="max-height: 70vh; overflow-y: auto;">
        <v-progress-linear v-if="loading" indeterminate color="primary" />
        <v-alert v-if="error" type="error" class="mb-4">{{ error }}</v-alert>

        <template v-if="projectData && !loading">
          <!-- Section 1: Project Overview -->
          <div class="mb-6">
            <h3 class="text-h6 mb-2">Overview</h3>
            <v-chip :color="statusColor" variant="flat" size="small" class="mr-2">{{ projectData.status }}</v-chip>
            <span class="text-caption text-medium-emphasis">
              Created {{ formatDate(projectData.created_at) }}
              <template v-if="projectData.completed_at"> | Completed {{ formatDate(projectData.completed_at) }}</template>
            </span>
            <p class="mt-2">{{ projectData.description || 'No description provided.' }}</p>
          </div>

          <!-- Section 2: Mission -->
          <div v-if="projectData.mission" class="mb-6">
            <h3 class="text-h6 mb-2">Mission</h3>
            <v-card variant="outlined" class="pa-3">
              <pre class="text-body-2" style="white-space: pre-wrap;">{{ missionText }}</pre>
            </v-card>
          </div>

          <!-- Section 3: Agent Roster -->
          <div v-if="agents.length" class="mb-6">
            <h3 class="text-h6 mb-2">Agents ({{ agents.length }})</h3>
            <v-table density="compact">
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Role</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="agent in agents" :key="agent.id">
                  <td>{{ agent.agent_display_name }}</td>
                  <td>{{ agent.agent_role || '-' }}</td>
                  <td><v-chip :color="agentStatusColor(agent.status)" size="x-small" variant="flat">{{ agent.status }}</v-chip></td>
                </tr>
              </tbody>
            </v-table>
          </div>

          <!-- Section 4: Agent Details (expandable, lazy-loaded messages) -->
          <div v-if="agents.length" class="mb-6">
            <h3 class="text-h6 mb-2">Agent Details</h3>
            <v-expansion-panels variant="accordion">
              <v-expansion-panel
                v-for="agent in agents"
                :key="agent.id"
                @group:selected="loadAgentMessages(agent)"
              >
                <v-expansion-panel-title>
                  {{ agent.agent_display_name }} - {{ agent.status }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-progress-linear v-if="agentMessages[agent.id]?.loading" indeterminate />
                  <div v-else-if="agentMessages[agent.id]?.messages?.length">
                    <div v-for="msg in agentMessages[agent.id].messages" :key="msg.id" class="mb-2 pa-2 rounded" style="background: rgba(0,0,0,0.03);">
                      <div class="d-flex justify-space-between">
                        <span class="text-caption font-weight-bold">{{ msg.from }}</span>
                        <span class="text-caption text-medium-emphasis">{{ formatDate(msg.created_at) }}</span>
                      </div>
                      <v-chip v-if="msg.direction" size="x-small" :color="msg.direction === 'outbound' ? 'primary' : 'default'" class="mr-1">{{ msg.direction }}</v-chip>
                      <p class="text-body-2 mt-1">{{ truncate(msg.content, 300) }}</p>
                    </div>
                  </div>
                  <p v-else class="text-caption text-medium-emphasis">No messages recorded.</p>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>

          <!-- Section 5: 360 Memory -->
          <div v-if="memoryEntries.length" class="mb-6">
            <h3 class="text-h6 mb-2">360 Memory ({{ memoryEntries.length }} entries)</h3>
            <v-expansion-panels variant="accordion">
              <v-expansion-panel v-for="(entry, i) in memoryEntries" :key="i">
                <v-expansion-panel-title>
                  #{{ entry.sequence_number ?? i + 1 }} - {{ entry.title || 'Memory Entry' }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <pre class="text-body-2" style="white-space: pre-wrap;">{{ entry.content || entry.summary || JSON.stringify(entry, null, 2) }}</pre>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>
        </template>
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="elevated" color="primary" @click="$emit('close')" data-testid="review-close-btn">
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useDisplay } from 'vuetify'
import api from '@/services/api'

const props = defineProps({
  show: { type: Boolean, required: true },
  projectId: { type: String, default: null },
  productId: { type: String, default: null },
})

defineEmits(['close'])

const { mobile } = useDisplay()
const isMobile = computed(() => mobile.value)

const loading = ref(false)
const error = ref(null)
const projectData = ref(null)
const agents = ref([])
const memoryEntries = ref([])
const agentMessages = reactive({})  // { [jobId]: { loading, messages } }

// Watch for modal open
watch(() => props.show, (open) => {
  if (open && props.projectId) {
    loadReviewData()
  } else {
    resetState()
  }
})

async function loadReviewData() {
  loading.value = true
  error.value = null
  try {
    // Fetch project, jobs, and memory in parallel
    const [projectRes, jobsRes, memoryRes] = await Promise.all([
      api.projects.get(props.projectId),
      api.agentJobs.list(props.projectId),
      props.productId ? api.products.getMemoryEntries(props.productId, { project_id: props.projectId, limit: 20 }) : Promise.resolve({ data: { entries: [] } }),
    ])
    projectData.value = projectRes.data
    // JobListResponse shape: { jobs: [...], total, limit, offset }
    agents.value = jobsRes.data?.jobs || []
    memoryEntries.value = memoryRes.data?.entries || []
  } catch (err) {
    console.error('[ProjectReviewModal] Failed to load:', err)
    error.value = err.response?.data?.message || err.message || 'Failed to load project data'
  } finally {
    loading.value = false
  }
}

async function loadAgentMessages(agent) {
  const jobId = agent.id
  if (agentMessages[jobId]) return  // Already loaded
  agentMessages[jobId] = { loading: true, messages: [] }
  try {
    const res = await api.agentJobs.messages(jobId)
    // Response shape: { data: { messages: [...] } } -- each msg has: id, from, content, created_at, direction, message_type
    agentMessages[jobId] = { loading: false, messages: (res.data?.messages || []).slice(0, 20) }
  } catch {
    agentMessages[jobId] = { loading: false, messages: [] }
  }
}

function resetState() {
  projectData.value = null
  agents.value = []
  memoryEntries.value = []
  Object.keys(agentMessages).forEach((k) => delete agentMessages[k])
  error.value = null
}

const missionText = computed(() => {
  const m = projectData.value?.mission
  if (!m) return ''
  if (typeof m === 'string') return m
  return m.mission_statement || m.objective || JSON.stringify(m, null, 2)
})

const statusColor = computed(() => {
  const s = projectData.value?.status
  if (s === 'completed') return 'success'
  if (s === 'terminated') return 'warning'
  if (s === 'cancelled') return 'grey'
  return 'primary'
})

function agentStatusColor(status) {
  if (status === 'complete' || status === 'completed') return 'success'
  if (status === 'decommissioned') return 'grey'
  if (status === 'working') return 'primary'
  if (status === 'waiting') return 'info'
  return 'default'
}

function formatDate(ts) {
  if (!ts) return 'Unknown'
  try {
    return new Date(ts).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch { return ts }
}

function truncate(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
}
</script>
```

**Note:** The template above is a starting point. The implementing agent should:
1. Verify the API call signatures match `frontend/src/services/api.js`
2. Test the `v-expansion-panel` `@group:selected` event for lazy loading (may need `@click` on the title instead)
3. Add ARIA labels for accessibility per project conventions
4. Use Vuetify theme variables, not hardcoded colors

## Implementation Plan

### Phase 1: StatusBadge Changes (Small)
- Add `review` action definition
- Update `actionsByStatus` for `completed` and `terminated`
- Test: badge clicks now emit `review` for completed/terminated projects

### Phase 2: ProjectReviewModal Component (Large)
- Create `frontend/src/components/projects/ProjectReviewModal.vue`
- Follow the component structure above
- Verify all API calls work with real project data
- Handle edge cases: no mission, no agents, no memory entries

### Phase 3: Wire into ProjectsView (Small)
- Add import, reactive state, template binding
- Add `review` case to `handleStatusAction`
- Test: clicking "Review" on a completed project opens the modal

### Phase 4: Testing
- Write unit tests
- Manual end-to-end testing

## Testing Requirements

### Unit Tests (Vitest)

Write in `frontend/tests/components/projects/ProjectReviewModal.test.js`:

1. `test_completed_project_shows_review_action` - mount StatusBadge with `status='completed'`, verify 'Review' action visible, not 'Reopen'
2. `test_terminated_project_shows_review_action` - same for `status='terminated'`
3. `test_cancelled_project_keeps_reopen` - mount StatusBadge with `status='cancelled'`, verify 'Reopen' still shown
4. `test_review_modal_renders_project_overview` - mount modal with mock project data, verify name/description/status displayed
5. `test_review_modal_renders_agent_roster` - mount with mock agents, verify table rows
6. `test_review_modal_renders_memory_entries` - mount with mock memory entries, verify expansion panels
7. `test_review_modal_is_read_only` - verify no buttons that modify state (no activate, reopen, delete, etc.)
8. `test_review_modal_close_emits_event` - click close button, verify `close` event emitted
9. `test_review_modal_fetches_data_on_open` - mock API, set `show=true`, verify 3 API calls made in parallel

### Manual Testing

1. Complete a project via CloseoutModal
2. Go to `/projects` -> find the completed project
3. Click status badge -> "Review" action appears (NOT "Reopen")
4. Click "Review" -> modal opens with project summary
5. Verify sections: overview, mission, agent roster, 360 memory
6. Expand an agent row -> messages lazy-load
7. Close modal -> project stays completed, no state change
8. Repeat for a terminated project
9. Verify cancelled projects still have "Reopen"

## Success Criteria

- `completed` projects: "Review" replaces "Reopen" in StatusBadge
- `terminated` projects: "Review" action available (previously no actions at all)
- `cancelled` projects: "Reopen" preserved unchanged
- Review modal is fully read-only -- no edit/action buttons
- Modal shows: project overview, mission, agent roster, per-agent messages (lazy), 360 Memory
- No new backend endpoints needed
- All data fetched from existing APIs

## Dependencies

- 0819a and 0819b are parallel, not blocking
- No backend changes, no database changes

## Rollback Plan

Delete `ProjectReviewModal.vue`, revert `StatusBadge.vue` and `ProjectsView.vue`. No backend changes to revert.

## Progress Updates

### 2026-03-15 - Implementation Session
**Status:** Completed

**Work Done:**
- Phase 1: Added `review` action definition to StatusBadge.vue, updated `actionsByStatus` for `completed` (review) and `terminated` (review), kept `cancelled` (reopen)
- Phase 2: Created `ProjectReviewModal.vue` with verified API calls and response shapes:
  - `api.agentJobs.list(projectId)` - response: `{ jobs, total, limit, offset }`
  - `api.agentJobs.messages(jobId)` - response: `{ job_id, agent_id, messages }` with `msg.from` and `msg.direction`
  - `api.products.getMemoryEntries(productId, params)` - response: `{ success, entries, total_count }`
- Phase 3: Wired modal into ProjectsView.vue (import, reactive state, template, handleStatusAction case)
- Phase 4: 19 tests passing covering rendering, data loading, response shapes, read-only verification, close events, StatusBadge action mapping

**Files Modified:**
- `frontend/src/components/StatusBadge.vue` (added review action, updated actionsByStatus)
- `frontend/src/views/ProjectsView.vue` (import, state, template, switch case)

**Files Created:**
- `frontend/src/components/projects/ProjectReviewModal.vue` (new read-only modal)
- `frontend/tests/components/projects/ProjectReviewModal.spec.js` (19 tests)

**Test Results:** 19 passed, 0 failed. Existing state-transition tests (65) still pass.
