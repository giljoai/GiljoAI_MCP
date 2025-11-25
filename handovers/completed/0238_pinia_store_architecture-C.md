# Handover 0238: Pinia Store Architecture

**Status**: Ready for Implementation
**Priority**: High
**Estimated Effort**: 3-4 hours
**Dependencies**: Handover 0226 (Backend API Extensions), existing websocket.js store
**Part of**: Visual Refactor Series (0225-0239)

---

## Objective

Define production-grade Pinia store architecture for Jobs/Implement tabs state management, following Vue 3 Composition API best practices and TDD principles. **Zero duplicate WebSocket handling** - leverage existing 700-line `websocket.js` store.

---

## TDD Approach

### Test-First Development Order

1. **Write failing store tests FIRST** (behavior-focused)
   - Test actions update state correctly
   - Test getters compute correctly
   - Test store integrates with WebSocket events (mocked)
   - Descriptive names: `test_agent_jobs_store_updates_when_websocket_event_received`

2. **Implement minimal store code** to pass tests

3. **Write failing integration tests** (WebSocket → Store → Component)

4. **Refactor** for clarity without breaking tests

**Key Principle**: Write tests that describe WHAT the code should do, not HOW it does it.

**Example Test Structure**:

```javascript
// tests/unit/stores/agentJobs.spec.js

import { setActivePinia, createPinia } from 'pinia'
import { useAgentJobsStore } from '@/stores/agentJobs'

describe('useAgentJobsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should initialize with empty agents array', () => {
    const store = useAgentJobsStore()
    expect(store.agents).toEqual([])
    expect(store.selectedAgent).toBeNull()
  })

  it('should update agent when updateAgent action called', () => {
    const store = useAgentJobsStore()

    // Add initial agent
    store.agents = [
      { job_id: 'agent-1', status: 'working', progress: 50 }
    ]

    // Update agent via action
    store.updateAgent({
      job_id: 'agent-1',
      status: 'complete',
      progress: 100
    })

    // Verify state updated
    expect(store.agents[0].status).toBe('complete')
    expect(store.agents[0].progress).toBe(100)
  })

  it('should filter agents by status', () => {
    const store = useAgentJobsStore()
    store.agents = [
      { job_id: 'agent-1', status: 'working', health_status: 'healthy' },
      { job_id: 'agent-2', status: 'complete', health_status: 'healthy' },
      { job_id: 'agent-3', status: 'working', health_status: 'warning' },
    ]

    store.filterByStatus(['working'])

    const filtered = store.filteredAgents
    expect(filtered).toHaveLength(2)
    expect(filtered.every(a => a.status === 'working')).toBe(true)
  })

  it('should compute filtered and sorted agents correctly', () => {
    const store = useAgentJobsStore()
    store.agents = [
      { job_id: 'agent-1', status: 'working', last_progress_at: '2025-11-21T10:00:00Z' },
      { job_id: 'agent-2', status: 'complete', last_progress_at: '2025-11-21T11:00:00Z' },
      { job_id: 'agent-3', status: 'working', last_progress_at: '2025-11-21T09:00:00Z' },
    ]

    store.tableFilters.status = ['working']
    store.tableSortBy = 'last_progress_at'
    store.tableSortOrder = 'desc'

    const sorted = store.sortedAgents
    expect(sorted).toHaveLength(2)
    expect(sorted[0].job_id).toBe('agent-1') // Most recent first
    expect(sorted[1].job_id).toBe('agent-3')
  })
})
```

---

## Current State Analysis

### Existing WebSocket Store (`frontend/src/stores/websocket.js`)

**Production-Grade Infrastructure** (700 lines):

- ✅ **Connection Management**: Auto-reconnection with exponential backoff
- ✅ **Message Queue**: Offline message queuing (max 100 messages)
- ✅ **Subscription Tracking**: Centralized subscription registry
- ✅ **Event Handlers**: Map-based event handler registration (`on()`, `off()`)
- ✅ **Heartbeat**: 30-second ping/pong mechanism
- ✅ **Toast Notifications**: Auto-notification on disconnect/reconnect
- ✅ **Stats & Debug**: Connection stats, event history, debug mode

**Key API**:

```javascript
// Connection
await connect({ token: authToken })
disconnect()

// Subscriptions
subscribe('project', projectId)  // Returns subscription key
unsubscribe('project', projectId)

// Event handlers
const unsub = on('job:table_update', (data) => {
  console.log('Table update received', data)
})
unsub()  // Remove handler

// Connection state
isConnected
isConnecting
isReconnecting
```

**DO NOT DUPLICATE THIS**. The new stores will consume WebSocket events via composables in components, NOT in stores.

### Existing Stores (Integration Points)

**`products.js`**: Product state management, active product tracking
**`projects.js`**: Project state, active project tracking
**`user.js`**: Current user, authentication state
**`settings.js`**: User preferences, system settings

**Pattern to Follow**: State-only stores, composables handle side effects.

---

## Implementation Plan

### Store 1: `agentJobsStore` (Jobs Tab State)

**File**: `frontend/src/stores/agentJobs.js`

**Purpose**: Manage agent jobs table state (filtering, sorting, selection) and job data cache.

**State**:

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAgentJobsStore = defineStore('agentJobs', () => {
  // ============================================
  // STATE
  // ============================================

  // Job data cache (fetched from /api/agent-jobs/table-view)
  const agents = ref([])  // Array of TableRowData

  // Selected agent for detail panel
  const selectedAgent = ref(null)  // job_id

  // Table UI state
  const tableFilters = ref({
    status: [],          // ['working', 'waiting']
    health_status: [],   // ['warning', 'critical']
    agent_type: [],      // ['orchestrator', 'implementer']
    has_unread: null,    // boolean | null
  })

  const tableSortBy = ref('last_progress_at')  // Column to sort by
  const tableSortOrder = ref('desc')           // 'asc' | 'desc'
  const tableLoading = ref(false)

  // Pagination
  const tableLimit = ref(50)
  const tableOffset = ref(0)
  const tableTotal = ref(0)

  // ============================================
  // GETTERS
  // ============================================

  // Get agent by job_id
  const agentById = computed(() => (jobId) => {
    return agents.value.find(a => a.job_id === jobId)
  })

  // Apply filters to agents
  const filteredAgents = computed(() => {
    let filtered = [...agents.value]

    // Filter by status
    if (tableFilters.value.status.length > 0) {
      filtered = filtered.filter(a => tableFilters.value.status.includes(a.status))
    }

    // Filter by health status
    if (tableFilters.value.health_status.length > 0) {
      filtered = filtered.filter(a =>
        tableFilters.value.health_status.includes(a.health_status)
      )
    }

    // Filter by agent type
    if (tableFilters.value.agent_type.length > 0) {
      filtered = filtered.filter(a =>
        tableFilters.value.agent_type.includes(a.agent_type)
      )
    }

    // Filter by unread messages
    if (tableFilters.value.has_unread !== null) {
      if (tableFilters.value.has_unread) {
        filtered = filtered.filter(a => a.unread_count > 0)
      } else {
        filtered = filtered.filter(a => a.unread_count === 0)
      }
    }

    return filtered
  })

  // Apply sorting to filtered agents
  const sortedAgents = computed(() => {
    const sorted = [...filteredAgents.value]

    const sortKey = tableSortBy.value
    const order = tableSortOrder.value

    sorted.sort((a, b) => {
      let aVal = a[sortKey]
      let bVal = b[sortKey]

      // Handle nulls (always sort to end)
      if (aVal === null && bVal === null) return 0
      if (aVal === null) return 1
      if (bVal === null) return -1

      // String comparison
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase()
        bVal = bVal.toLowerCase()
      }

      if (order === 'asc') {
        return aVal > bVal ? 1 : aVal < bVal ? -1 : 0
      } else {
        return aVal < bVal ? 1 : aVal > bVal ? -1 : 0
      }
    })

    return sorted
  })

  // Count agents by status
  const statusCounts = computed(() => {
    const counts = {}
    agents.value.forEach(agent => {
      counts[agent.status] = (counts[agent.status] || 0) + 1
    })
    return counts
  })

  // Count agents with warnings
  const warningCount = computed(() => {
    return agents.value.filter(a =>
      a.health_status === 'warning' ||
      a.health_status === 'critical' ||
      a.is_stale
    ).length
  })

  // ============================================
  // ACTIONS
  // ============================================

  /**
   * Load agents from API
   */
  async function loadAgents(projectId, filters = {}) {
    tableLoading.value = true

    try {
      const params = new URLSearchParams({
        project_id: projectId,
        sort_by: tableSortBy.value,
        sort_order: tableSortOrder.value,
        limit: tableLimit.value,
        offset: tableOffset.value,
      })

      // Add filters
      if (tableFilters.value.status.length > 0) {
        tableFilters.value.status.forEach(s => params.append('status', s))
      }
      if (tableFilters.value.health_status.length > 0) {
        tableFilters.value.health_status.forEach(h => params.append('health_status', h))
      }
      if (tableFilters.value.agent_type.length > 0) {
        tableFilters.value.agent_type.forEach(t => params.append('agent_type', t))
      }
      if (tableFilters.value.has_unread !== null) {
        params.append('has_unread', tableFilters.value.has_unread)
      }

      const response = await fetch(`/api/agent-jobs/table-view?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to load agents: ${response.statusText}`)
      }

      const data = await response.json()

      agents.value = data.rows
      tableTotal.value = data.total
    } catch (error) {
      console.error('Failed to load agents:', error)
      throw error
    } finally {
      tableLoading.value = false
    }
  }

  /**
   * Update single agent (called from WebSocket event)
   */
  function updateAgent(updates) {
    const index = agents.value.findIndex(a => a.job_id === updates.job_id)

    if (index !== -1) {
      // Update existing agent (merge updates)
      agents.value[index] = {
        ...agents.value[index],
        ...updates
      }
    } else {
      // Add new agent if not found (agent just created)
      agents.value.unshift(updates)
    }
  }

  /**
   * Remove agent (called when agent decommissioned)
   */
  function removeAgent(jobId) {
    agents.value = agents.value.filter(a => a.job_id !== jobId)

    // Clear selection if removed agent was selected
    if (selectedAgent.value === jobId) {
      selectedAgent.value = null
    }
  }

  /**
   * Select agent for detail panel
   */
  function selectAgent(jobId) {
    selectedAgent.value = jobId
  }

  /**
   * Clear filters
   */
  function clearFilters() {
    tableFilters.value = {
      status: [],
      health_status: [],
      agent_type: [],
      has_unread: null,
    }
  }

  /**
   * Set sort column and order
   */
  function setSorting(column, order) {
    tableSortBy.value = column
    tableSortOrder.value = order
  }

  /**
   * Reset store state
   */
  function $reset() {
    agents.value = []
    selectedAgent.value = null
    tableFilters.value = {
      status: [],
      health_status: [],
      agent_type: [],
      has_unread: null,
    }
    tableSortBy.value = 'last_progress_at'
    tableSortOrder.value = 'desc'
    tableLoading.value = false
    tableLimit.value = 50
    tableOffset.value = 0
    tableTotal.value = 0
  }

  // ============================================
  // RETURN STORE API
  // ============================================

  return {
    // State
    agents,
    selectedAgent,
    tableFilters,
    tableSortBy,
    tableSortOrder,
    tableLoading,
    tableLimit,
    tableOffset,
    tableTotal,

    // Getters
    agentById,
    filteredAgents,
    sortedAgents,
    statusCounts,
    warningCount,

    // Actions
    loadAgents,
    updateAgent,
    removeAgent,
    selectAgent,
    clearFilters,
    setSorting,
    $reset,
  }
})
```

### Store 2: `projectJobsStore` (Implement Tab State)

**File**: `frontend/src/stores/projectJobs.js`

**Purpose**: Manage project-level job orchestration state (staging, launch, mission updates).

**State**:

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useProjectJobsStore = defineStore('projectJobs', () => {
  // ============================================
  // STATE
  // ============================================

  // Current project context
  const currentProjectId = ref(null)

  // Project description
  const projectDescription = ref('')

  // Orchestrator mission (editable during staging)
  const orchestratorMission = ref('')
  const missionDirty = ref(false)  // Track unsaved changes

  // Staging state
  const stagingStatus = ref(null)  // null | 'staging' | 'ready' | 'cancelled'
  const stagingStartedAt = ref(null)

  // Launch state
  const launchComplete = ref(false)
  const launchError = ref(null)

  // ============================================
  // GETTERS
  // ============================================

  const isStaging = computed(() => stagingStatus.value === 'staging')
  const isLaunchReady = computed(() => stagingStatus.value === 'ready')
  const canLaunch = computed(() =>
    isLaunchReady.value && !launchComplete.value && !launchError.value
  )

  const hasStagingError = computed(() => stagingStatus.value === 'cancelled')

  // ============================================
  // ACTIONS
  // ============================================

  /**
   * Load project data from API
   */
  async function loadProjectData(projectId) {
    try {
      const response = await fetch(`/api/projects/${projectId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to load project: ${response.statusText}`)
      }

      const project = await response.json()

      currentProjectId.value = projectId
      projectDescription.value = project.description || ''

      // Initialize mission from project metadata
      if (project.orchestrator_mission) {
        orchestratorMission.value = project.orchestrator_mission
      }

      stagingStatus.value = project.staging_status || null

      return project
    } catch (error) {
      console.error('Failed to load project data:', error)
      throw error
    }
  }

  /**
   * Update orchestrator mission (during staging)
   */
  function updateMission(newMission) {
    orchestratorMission.value = newMission
    missionDirty.value = true
  }

  /**
   * Save mission to backend
   */
  async function saveMission() {
    if (!currentProjectId.value) return

    try {
      const response = await fetch(
        `/api/projects/${currentProjectId.value}/mission`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          },
          body: JSON.stringify({
            mission: orchestratorMission.value
          })
        }
      )

      if (!response.ok) {
        throw new Error(`Failed to save mission: ${response.statusText}`)
      }

      missionDirty.value = false
    } catch (error) {
      console.error('Failed to save mission:', error)
      throw error
    }
  }

  /**
   * Update staging status (called from WebSocket event)
   */
  function updateStagingStatus(status, startedAt = null) {
    stagingStatus.value = status

    if (startedAt) {
      stagingStartedAt.value = startedAt
    }

    // Reset launch state when re-staging
    if (status === 'staging') {
      launchComplete.value = false
      launchError.value = null
    }
  }

  /**
   * Mark launch as complete
   */
  function markLaunchComplete() {
    launchComplete.value = true
    stagingStatus.value = null
  }

  /**
   * Set launch error
   */
  function setLaunchError(error) {
    launchError.value = error
    launchComplete.value = false
  }

  /**
   * Reset store state
   */
  function $reset() {
    currentProjectId.value = null
    projectDescription.value = ''
    orchestratorMission.value = ''
    missionDirty.value = false
    stagingStatus.value = null
    stagingStartedAt.value = null
    launchComplete.value = false
    launchError.value = null
  }

  // ============================================
  // RETURN STORE API
  // ============================================

  return {
    // State
    currentProjectId,
    projectDescription,
    orchestratorMission,
    missionDirty,
    stagingStatus,
    stagingStartedAt,
    launchComplete,
    launchError,

    // Getters
    isStaging,
    isLaunchReady,
    canLaunch,
    hasStagingError,

    // Actions
    loadProjectData,
    updateMission,
    saveMission,
    updateStagingStatus,
    markLaunchComplete,
    setLaunchError,
    $reset,
  }
})
```

### Integration Pattern: WebSocket Events → Store Updates (In Components)

**DO NOT**: Create WebSocket handling in stores
**DO**: Use WebSocket composable in components to update stores

**Example Component Integration** (`StatusBoardTable.vue`):

```vue
<script setup>
import { onMounted, onUnmounted, watch } from 'vue'
import { useAgentJobsStore } from '@/stores/agentJobs'
import { useWebSocketStore } from '@/stores/websocket'
import { useProjectsStore } from '@/stores/projects'

const agentStore = useAgentJobsStore()
const wsStore = useWebSocketStore()
const projectStore = useProjectsStore()

let unsubscribeHandlers = []

onMounted(async () => {
  const projectId = projectStore.activeProject?.project_id

  if (!projectId) {
    console.warn('No active project')
    return
  }

  // Load initial data
  await agentStore.loadAgents(projectId)

  // Subscribe to project events
  wsStore.subscribe('project', projectId)

  // Register event handlers
  const unsub1 = wsStore.on('job:table_update', (data) => {
    console.log('Table update received', data)

    if (data.updates && Array.isArray(data.updates)) {
      data.updates.forEach(update => {
        agentStore.updateAgent(update)
      })
    }
  })

  const unsub2 = wsStore.on('job:created', (data) => {
    console.log('Job created', data)
    // Reload table or add new row
    agentStore.loadAgents(projectId)
  })

  const unsub3 = wsStore.on('job:decommissioned', (data) => {
    console.log('Job decommissioned', data)
    agentStore.removeAgent(data.job_id)
  })

  unsubscribeHandlers = [unsub1, unsub2, unsub3]
})

onUnmounted(() => {
  // Clean up event handlers
  unsubscribeHandlers.forEach(unsub => unsub())

  // Unsubscribe from project (optional - depends on navigation pattern)
  const projectId = projectStore.activeProject?.project_id
  if (projectId) {
    wsStore.unsubscribe('project', projectId)
  }
})
</script>

<template>
  <v-data-table
    :items="agentStore.sortedAgents"
    :loading="agentStore.tableLoading"
    @update:sort-by="(col) => agentStore.setSorting(col, 'desc')"
  >
    <!-- Table columns -->
  </v-data-table>
</template>
```

---

## Testing Criteria

### 1. Store Unit Tests

**Coverage Target**: >90% for each store

**Test Files**:
- `tests/unit/stores/agentJobs.spec.js`
- `tests/unit/stores/projectJobs.spec.js`

**Test Categories**:

1. **State Initialization**
   - Verify default state values
   - Verify store can be instantiated multiple times

2. **Actions**
   - Test each action modifies state correctly
   - Test actions with various inputs (edge cases)
   - Test async actions handle errors

3. **Getters**
   - Test computed properties return correct values
   - Test getter reactivity (state changes → getter updates)
   - Test filtering/sorting logic

4. **Store Reset**
   - Test `$reset()` clears all state

### 2. Integration Tests (Component + Store + WebSocket)

**Test File**: `tests/integration/websocket-store-integration.spec.js`

**Test Scenarios**:

```javascript
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { useWebSocketStore } from '@/stores/websocket'
import { useAgentJobsStore } from '@/stores/agentJobs'
import StatusBoardTable from '@/components/StatusBoardTable.vue'

describe('WebSocket → Store → Component Integration', () => {
  let wsStore
  let agentStore

  beforeEach(() => {
    setActivePinia(createPinia())
    wsStore = useWebSocketStore()
    agentStore = useAgentJobsStore()
  })

  it('should update table when job:table_update event received', async () => {
    // Mount component
    const wrapper = mount(StatusBoardTable)

    // Simulate WebSocket event
    wsStore.send({
      type: 'job:table_update',
      updates: [
        { job_id: 'agent-1', status: 'complete', progress: 100 }
      ]
    })

    // Verify store updated
    await wrapper.vm.$nextTick()
    expect(agentStore.agentById('agent-1').status).toBe('complete')

    // Verify component re-rendered
    expect(wrapper.html()).toContain('complete')
  })
})
```

---

## Success Criteria

- ✅ `agentJobsStore` created with state, getters, actions
- ✅ `projectJobsStore` created with staging/launch state management
- ✅ **No WebSocket code in stores** (only in components)
- ✅ Store unit tests pass (>90% coverage)
- ✅ Integration tests verify WebSocket → Store → Component flow
- ✅ Stores integrate with existing `websocket.js` store (no duplication)
- ✅ Getters compute efficiently (reactive, minimal re-computation)
- ✅ Actions follow single-responsibility principle
- ✅ TypeScript-friendly (or JSDoc annotations for autocomplete)

---

## Next Steps

→ **Handover 0239**: Deployment Strategy & Feature Flag
- Backend feature flag endpoint
- Frontend conditional rendering (old vs new UI)
- 3-phase rollout plan
- Rollback procedure

---

## References

- **Existing WebSocket Store**: `frontend/src/stores/websocket.js:1-700`
- **Pinia Best Practices**: [Pinia Docs - Composition API Stores](https://pinia.vuejs.org/core-concepts/#composition-stores)
- **TDD Principles**: `handovers/code_review_nov18.md` (behavior-focused testing)
- **Service Layer Pattern**: `handovers/013A_code_review_architecture_status.md`
- **Backend API**: Handover 0226 (table view endpoint)
- **Component Integration**: Handover 0228 (StatusBoardTable component)
