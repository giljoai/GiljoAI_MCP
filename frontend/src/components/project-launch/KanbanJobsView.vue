<template>
  <v-container fluid>
    <!-- Header Section -->
    <v-row class="mb-6">
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between">
          <div>
            <h2 class="text-h5 font-weight-bold">Active Agent Jobs</h2>
            <p class="text-subtitle-2 text-medium-emphasis mt-1">
              Monitor active agents and jobs in real-time ({{ jobs.length }} jobs)
            </p>
          </div>
          <v-btn
            color="primary"
            variant="elevated"
            @click="refreshJobs"
            :loading="refreshing"
            :disabled="refreshing"
          >
            <v-icon start>mdi-refresh</v-icon>
            Refresh
          </v-btn>
        </div>
      </v-col>
    </v-row>

    <!-- Kanban Board Stub -->
    <v-row>
      <v-col cols="12">
        <v-card elevation="1" class="pa-8">
          <div class="text-center">
            <v-icon size="80" color="grey-lighten-1" class="mb-4 d-block">
              mdi-view-column
            </v-icon>

            <h3 class="text-h6 font-weight-bold mb-2">Kanban Board</h3>

            <p class="text-body-1 text-grey mb-4 max-width-500">
              The Kanban board for tracking agent jobs across different statuses is coming in Handover 0066.
            </p>

            <p class="text-body-2 text-grey mb-4">
              <strong>Implemented in:</strong> Handover 0066 - Agent Kanban Dashboard
            </p>

            <!-- Job Summary -->
            <v-divider class="my-6" />

            <h4 class="text-subtitle-1 font-weight-bold mb-4">Current Job Summary</h4>

            <v-row class="mb-6">
              <v-col cols="12" sm="6" md="3">
                <v-card variant="outlined" color="info">
                  <v-card-text class="text-center pa-4">
                    <p class="text-h4 font-weight-bold">{{ stats.total }}</p>
                    <p class="text-subtitle-2 text-grey">Total Jobs</p>
                  </v-card-text>
                </v-card>
              </v-col>

              <v-col cols="12" sm="6" md="3">
                <v-card variant="outlined" color="warning">
                  <v-card-text class="text-center pa-4">
                    <p class="text-h4 font-weight-bold">{{ stats.pending }}</p>
                    <p class="text-subtitle-2 text-grey">Pending</p>
                  </v-card-text>
                </v-card>
              </v-col>

              <v-col cols="12" sm="6" md="3">
                <v-card variant="outlined" color="primary">
                  <v-card-text class="text-center pa-4">
                    <p class="text-h4 font-weight-bold">{{ stats.running }}</p>
                    <p class="text-subtitle-2 text-grey">Running</p>
                  </v-card-text>
                </v-card>
              </v-col>

              <v-col cols="12" sm="6" md="3">
                <v-card variant="outlined" color="success">
                  <v-card-text class="text-center pa-4">
                    <p class="text-h4 font-weight-bold">{{ stats.completed }}</p>
                    <p class="text-subtitle-2 text-grey">Completed</p>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <!-- Jobs List (Temporary Display) -->
            <h4 class="text-subtitle-1 font-weight-bold mb-4 text-left">Jobs Overview</h4>

            <v-data-table
              :items="jobs"
              :headers="jobHeaders"
              :loading="loading"
              density="comfortable"
              class="elevation-1"
            >
              <template v-slot:item.status="{ item }">
                <v-chip :color="getStatusColor(item.status)" size="small">
                  {{ item.status }}
                </v-chip>
              </template>

              <template v-slot:item.created_at="{ item }">
                {{ formatDate(item.created_at) }}
              </template>

              <template v-slot:item.actions="{ item }">
                <v-btn
                  size="small"
                  variant="text"
                  icon
                  @click="showJobDetails(item)"
                  aria-label="View job details"
                >
                  <v-icon>mdi-information</v-icon>
                </v-btn>
              </template>
            </v-data-table>

            <!-- Info Alert -->
            <v-alert
              type="info"
              variant="tonal"
              class="mt-6 mb-0"
            >
              <v-icon start>mdi-lightbulb</v-icon>
              <div>
                <p class="font-weight-bold">Kanban Board Coming Soon</p>
                <p class="text-body-2 mt-1">
                  In Handover 0066, this view will transform into an interactive Kanban board with drag-and-drop
                  job management, real-time status updates, and detailed job monitoring.
                </p>
              </div>
            </v-alert>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Job Details Dialog -->
    <v-dialog v-model="showDetails" max-width="600">
      <v-card v-if="selectedJob">
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="primary">mdi-briefcase</v-icon>
          Job: {{ selectedJob.job_id }}
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-4">
          <v-row>
            <v-col cols="12" sm="6">
              <p class="text-caption text-grey mb-1">Job ID</p>
              <p class="text-body-2 font-weight-bold">{{ selectedJob.job_id }}</p>
            </v-col>

            <v-col cols="12" sm="6">
              <p class="text-caption text-grey mb-1">Status</p>
              <v-chip :color="getStatusColor(selectedJob.status)" size="small">
                {{ selectedJob.status }}
              </v-chip>
            </v-col>

            <v-col cols="12">
              <p class="text-caption text-grey mb-1">Agent</p>
              <p class="text-body-2 font-weight-bold">{{ selectedJob.agent_id }}</p>
            </v-col>

            <v-col cols="12" sm="6">
              <p class="text-caption text-grey mb-1">Created</p>
              <p class="text-body-2">{{ formatDate(selectedJob.created_at) }}</p>
            </v-col>

            <v-col cols="12" sm="6">
              <p class="text-caption text-grey mb-1">Updated</p>
              <p class="text-body-2">{{ formatDate(selectedJob.updated_at) }}</p>
            </v-col>

            <v-col v-if="selectedJob.mission" cols="12">
              <p class="text-caption text-grey mb-1">Mission</p>
              <v-card variant="tonal" class="pa-3">
                <p class="text-body-2">{{ selectedJob.mission }}</p>
              </v-card>
            </v-col>

            <v-col v-if="selectedJob.progress" cols="12">
              <p class="text-caption text-grey mb-2">Progress</p>
              <v-progress-linear
                :model-value="selectedJob.progress"
                striped
                height="6"
              />
              <p class="text-caption text-grey mt-1">{{ selectedJob.progress }}%</p>
            </v-col>
          </v-row>
        </v-card-text>

        <v-divider />

        <v-card-actions>
          <v-spacer />
          <v-btn @click="showDetails = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '@/services/api'
import websocketService from '@/services/websocket'

/**
 * KanbanJobsView Component
 *
 * Temporary stub implementation for active agent jobs monitoring.
 * Shows job summary statistics and a data table of jobs.
 *
 * Will be replaced with a full Kanban board interface in Handover 0066.
 * Implements WebSocket integration for real-time updates.
 */

const props = defineProps({
  projectId: {
    type: String,
    required: true,
  },
  jobs: {
    type: Array,
    default: () => [],
  },
})

// State
const jobs = ref(props.jobs || [])
const selectedJob = ref(null)
const showDetails = ref(false)
const loading = ref(false)
const refreshing = ref(false)

// Table headers
const jobHeaders = [
  { title: 'Job ID', key: 'job_id', width: '20%' },
  { title: 'Agent ID', key: 'agent_id', width: '25%' },
  { title: 'Status', key: 'status', width: '15%' },
  { title: 'Created', key: 'created_at', width: '25%' },
  { title: 'Actions', key: 'actions', width: '15%', sortable: false },
]

// WebSocket unsubscribe function
let unsubscribeJobUpdate = null

/**
 * Calculate job statistics
 */
const stats = computed(() => {
  const total = jobs.value.length
  const pending = jobs.value.filter((j) => j.status === 'pending').length
  const running = jobs.value.filter((j) => j.status === 'running' || j.status === 'acknowledged').length
  const completed = jobs.value.filter((j) => j.status === 'completed' || j.status === 'failed').length

  return { total, pending, running, completed }
})

/**
 * Fetch jobs for the project
 */
async function fetchJobs() {
  loading.value = true

  try {
    const response = await api.orchestrator.getWorkflowStatus(props.projectId)
    jobs.value = response.data.jobs || []

    console.log('[KanbanJobsView] Jobs fetched:', jobs.value.length)
  } catch (error) {
    console.error('[KanbanJobsView] Error fetching jobs:', error)
  } finally {
    loading.value = false
  }
}

/**
 * Refresh jobs on demand
 */
async function refreshJobs() {
  refreshing.value = true

  try {
    await fetchJobs()
  } finally {
    refreshing.value = false
  }
}

/**
 * Get status color for chip
 */
function getStatusColor(status) {
  const colors = {
    pending: 'warning',
    acknowledged: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'error',
    cancelled: 'grey',
  }

  return colors[status] || 'grey'
}

/**
 * Show job details dialog
 */
function showJobDetails(job) {
  selectedJob.value = job
  showDetails.value = true
}

/**
 * Format date for display
 */
function formatDate(dateString) {
  if (!dateString) return 'N/A'

  try {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  } catch {
    return dateString
  }
}

/**
 * Handle WebSocket job updates
 */
function handleJobUpdate(data) {
  if (data.project_id !== props.projectId) return

  console.log('[KanbanJobsView] Job update received:', data)

  const jobIndex = jobs.value.findIndex((j) => j.job_id === data.job_id)

  if (jobIndex !== -1) {
    // Update existing job
    jobs.value[jobIndex] = { ...jobs.value[jobIndex], ...data }
  } else if (data.job_id) {
    // Add new job
    jobs.value.push(data)
  }
}

/**
 * Lifecycle hooks
 */
onMounted(() => {
  console.log('[KanbanJobsView] Component mounted, projectId:', props.projectId)

  // Fetch initial jobs if not provided
  if (jobs.value.length === 0) {
    fetchJobs()
  }

  // Register WebSocket listener for job updates
  unsubscribeJobUpdate = websocketService.onMessage('job:status_changed', handleJobUpdate)

  console.log('[KanbanJobsView] WebSocket listener registered')
})

onUnmounted(() => {
  console.log('[KanbanJobsView] Component unmounting, cleaning up WebSocket listeners')

  // Clean up WebSocket listener
  if (unsubscribeJobUpdate) {
    unsubscribeJobUpdate()
  }
})
</script>

<style scoped>
/* Container adjustments */
.pa-8 {
  padding: 2rem;
}

/* Max width utility for responsive layout */
.max-width-500 {
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}

/* Center alignment */
.text-center {
  text-align: center;
}

/* Data table styling */
:deep(.v-data-table) {
  background-color: transparent;
}

:deep(.v-data-table-header) {
  background-color: rgba(0, 0, 0, 0.03);
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .pa-8 {
    padding: 1rem;
  }
}
</style>
