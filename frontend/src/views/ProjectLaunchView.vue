<template>
  <v-container fluid class="pa-6">
    <!-- Header Section -->
    <v-row class="mb-6">
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between">
          <div>
            <v-btn
              icon
              variant="text"
              size="small"
              @click="goBack"
              class="mb-2"
              aria-label="Go back"
            >
              <v-icon>mdi-arrow-left</v-icon>
            </v-btn>
            <h1 class="text-h3 font-weight-bold">Project Launch</h1>
            <p class="text-subtitle-1 text-medium-emphasis mt-2">
              {{ project?.name || 'Loading...' }}
            </p>
          </div>
          <v-card variant="tonal" color="info" class="pa-4" max-width="200">
            <p class="text-caption text-medium-emphasis mb-1">Project Status</p>
            <v-chip
              size="small"
              :color="getStatusColor(project?.status)"
              label
            >
              {{ project?.status || 'unknown' }}
            </v-chip>
          </v-card>
        </div>
      </v-col>
    </v-row>

    <!-- Loading State -->
    <v-row v-if="loading" class="justify-center py-12">
      <v-col cols="12" class="text-center">
        <v-progress-circular indeterminate color="primary" size="64" />
        <p class="text-subtitle-1 mt-4">Loading project details...</p>
      </v-col>
    </v-row>

    <!-- Error State -->
    <v-row v-else-if="error" class="mb-4">
      <v-col cols="12">
        <v-alert type="error" variant="tonal" closable @click:close="error = null">
          <v-icon start>mdi-alert-circle</v-icon>
          <div>
            <p class="font-weight-bold">Error Loading Project</p>
            <p class="text-body-2">{{ error }}</p>
          </div>
        </v-alert>
      </v-col>
    </v-row>

    <!-- Tabs Section -->
    <v-row v-else>
      <v-col cols="12">
        <v-tabs
          v-model="activeTab"
          bg-color="surface"
          class="mb-4"
          density="compact"
        >
          <v-tab
            value="launch"
            :prepend-icon="`mdi-file-document`"
            aria-label="Launch Panel"
          >
            Launch Panel
          </v-tab>
          <v-tab
            value="jobs"
            :prepend-icon="`mdi-view-column`"
            :disabled="!jobsLaunched"
            aria-label="Active Jobs (Kanban Board)"
          >
            Active Jobs (Kanban)
            <v-chip
              v-if="jobsLaunched"
              size="small"
              color="primary"
              label
              class="ml-2"
            >
              {{ projectJobs.length }}
            </v-chip>
          </v-tab>
        </v-tabs>

        <!-- Tab Window -->
        <v-window v-model="activeTab" class="mt-4">
          <!-- Tab 1: Launch Panel -->
          <v-window-item value="launch">
            <launch-panel-view
              :project="project"
              :mission="mission"
              :agents="selectedAgents"
              :loading-mission="loadingMission"
              :launching="launching"
              :can-accept="canAcceptMission"
              @save-description="handleSaveDescription"
              @copy-prompt="handleCopyPrompt"
              @accept-mission="handleAcceptMission"
            />
          </v-window-item>

          <!-- Tab 2: Active Jobs (Kanban Board) -->
          <v-window-item value="jobs">
            <kanban-jobs-view
              v-if="jobsLaunched"
              :project-id="projectId"
              :jobs="projectJobs"
            />
          </v-window-item>
        </v-window>
      </v-col>
    </v-row>

    <!-- Toast Notifications -->
    <v-snackbar v-model="showToast" :timeout="3000" :color="toastColor">
      <v-icon start :color="toastColor">{{ toastIcon }}</v-icon>
      {{ toastMessage }}
      <template v-slot:actions>
        <v-btn variant="text" @click="showToast = false">
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api'
import websocketService from '@/services/websocket'
import LaunchPanelView from '@/components/project-launch/LaunchPanelView.vue'
import KanbanJobsView from '@/components/project-launch/KanbanJobsView.vue'

/**
 * ProjectLaunchView Component
 *
 * Two-tab interface for launching projects:
 * Tab 1 - Launch Panel: Shows orchestrator prompt, generated mission, and selected agents
 * Tab 2 - Active Jobs: Kanban board for tracking agent jobs (implemented in 0066)
 *
 * Production-grade with comprehensive error handling, loading states, and WebSocket integration.
 */

const route = useRoute()
const router = useRouter()

// Route parameters
const projectId = ref(route.params.projectId)

// State
const project = ref(null)
const mission = ref('')
const selectedAgents = ref([])
const projectJobs = ref([])
const activeTab = ref('launch')
const jobsLaunched = ref(false)

// Loading states
const loading = ref(true)
const loadingMission = ref(false)
const launching = ref(false)
const savingDescription = ref(false)
const error = ref(null)

// Toast notification state
const showToast = ref(false)
const toastMessage = ref('')
const toastColor = ref('success')
const toastIcon = ref('mdi-check-circle')

// WebSocket unsubscribe functions
let unsubscribeProgress = null
let unsubscribeMission = null

/**
 * Computed properties
 */
const canAcceptMission = computed(() => {
  return mission.value && selectedAgents.value.length > 0 && !launching.value
})

/**
 * Fetch project details on component mount
 */
async function fetchProjectDetails() {
  loading.value = true
  error.value = null

  try {
    const response = await api.projects.get(projectId.value)
    project.value = response.data

    // Pre-populate mission from backend if available
    if (response.data.mission) {
      mission.value = response.data.mission
    }

    console.log('[ProjectLaunchView] Project loaded:', response.data)
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to load project'
    console.error('[ProjectLaunchView] Error loading project:', err)
  } finally {
    loading.value = false
  }
}

/**
 * Handle project description save
 */
async function handleSaveDescription(description) {
  savingDescription.value = true
  error.value = null

  try {
    await api.projects.update(projectId.value, {
      description: description,
    })

    showNotification('Project description saved successfully', 'success', 'mdi-check-circle')
    console.log('[ProjectLaunchView] Description saved')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to save description'
    showNotification('Failed to save description', 'error', 'mdi-alert-circle')
    console.error('[ProjectLaunchView] Error saving description:', err)
  } finally {
    savingDescription.value = false
  }
}

/**
 * Handle orchestrator prompt copy to clipboard
 */
async function handleCopyPrompt() {
  try {
    const prompt = generateOrchestratorPrompt()
    await navigator.clipboard.writeText(prompt)
    showNotification('Orchestrator prompt copied to clipboard', 'success', 'mdi-content-copy')
    console.log('[ProjectLaunchView] Prompt copied')
  } catch (err) {
    showNotification('Failed to copy prompt', 'error', 'mdi-alert-circle')
    console.error('[ProjectLaunchView] Error copying prompt:', err)
  }
}

/**
 * Generate orchestrator prompt for manual copying
 */
function generateOrchestratorPrompt() {
  return `You are the Orchestrator for Project ID: ${projectId.value}.

Project Name: ${project.value?.name || 'Unknown'}
Project Description: ${project.value?.description || project.value?.mission || 'No description'}

Your tasks:
1. Use available MCP tools to retrieve complete project context
2. Analyze the project requirements and constraints
3. Generate a detailed mission plan with specific objectives
4. Select optimal agents from available pool
5. Create coordinated workflow for agent execution

Respond with:
- Complete mission statement
- Selected agents (maximum 6)
- Workflow structure (waterfall or parallel)
- Token budget estimate`
}

/**
 * Handle mission acceptance and job creation
 */
async function handleAcceptMission() {
  launching.value = true
  error.value = null

  try {
    // Create agent jobs
    const response = await api.orchestrator.launchProject({
      project_id: projectId.value,
      mission: mission.value,
      agents: selectedAgents.value.map((agent) => agent.id),
    })

    console.log('[ProjectLaunchView] Mission accepted, jobs created:', response.data)

    // Mark jobs as launched
    jobsLaunched.value = true
    projectJobs.value = response.data.jobs || []

    // Switch to jobs tab
    activeTab.value = 'jobs'

    showNotification('Mission accepted and jobs created successfully!', 'success', 'mdi-rocket-launch')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to accept mission'
    showNotification('Failed to accept mission', 'error', 'mdi-alert-circle')
    console.error('[ProjectLaunchView] Error accepting mission:', err)
  } finally {
    launching.value = false
  }
}

/**
 * Show toast notification
 */
function showNotification(message, color = 'success', icon = 'mdi-check-circle') {
  toastMessage.value = message
  toastColor.value = color
  toastIcon.value = icon
  showToast.value = true
}

/**
 * Navigate back to projects
 */
function goBack() {
  router.push({ name: 'Projects' })
}

/**
 * Get status color for chip
 */
function getStatusColor(status) {
  const colors = {
    active: 'success',
    inactive: 'warning',
    completed: 'info',
    cancelled: 'error',
    deleted: 'grey',
  }
  return colors[status] || 'grey'
}

/**
 * Handle WebSocket mission updates
 */
function handleMissionUpdate(data) {
  if (data.project_id !== projectId.value) return

  console.log('[ProjectLaunchView] Mission update received:', data)

  if (data.mission) {
    mission.value = data.mission
  }

  if (data.agents && Array.isArray(data.agents)) {
    selectedAgents.value = data.agents
  }

  loadingMission.value = false
}

/**
 * Handle WebSocket orchestrator progress
 */
function handleOrchestratorProgress(data) {
  if (data.project_id !== projectId.value) return

  console.log('[ProjectLaunchView] Orchestrator progress:', data)

  if (data.stage === 'mission_generated') {
    mission.value = data.mission || mission.value
    loadingMission.value = false
  }

  if (data.stage === 'agents_selected' && data.agents) {
    selectedAgents.value = data.agents
  }

  if (data.stage === 'jobs_created' && data.jobs) {
    projectJobs.value = data.jobs
    jobsLaunched.value = true
  }

  if (data.error) {
    error.value = data.error
    showNotification(`Orchestrator error: ${data.error}`, 'error', 'mdi-alert-circle')
  }
}

/**
 * Lifecycle hooks
 */
onMounted(() => {
  console.log('[ProjectLaunchView] Component mounted, projectId:', projectId.value)

  // Fetch project details
  fetchProjectDetails()

  // Register WebSocket listeners for real-time updates
  unsubscribeProgress = websocketService.onMessage('orchestrator:progress', handleOrchestratorProgress)
  unsubscribeMission = websocketService.onMessage('orchestrator:mission', handleMissionUpdate)

  console.log('[ProjectLaunchView] WebSocket listeners registered')
})

onUnmounted(() => {
  console.log('[ProjectLaunchView] Component unmounting, cleaning up WebSocket listeners')

  // Clean up WebSocket listeners
  if (unsubscribeProgress) {
    unsubscribeProgress()
  }
  if (unsubscribeMission) {
    unsubscribeMission()
  }
})
</script>

<style scoped>
/* Container padding */
.pa-6 {
  padding: 1.5rem;
}

/* Status chip styling */
:deep(.v-chip) {
  text-transform: capitalize;
}

/* Tab spacing */
:deep(.v-tabs) {
  border-bottom: 2px solid rgba(0, 0, 0, 0.12);
}

/* Window item padding */
:deep(.v-window-item) {
  padding: 1.5rem 0;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .pa-6 {
    padding: 1rem;
  }

  h1.text-h3 {
    font-size: 1.5rem !important;
  }
}
</style>
