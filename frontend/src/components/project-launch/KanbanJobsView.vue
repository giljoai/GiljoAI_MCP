<template>
  <div class="kanban-jobs-view">
    <!-- Header Section -->
    <v-row class="mb-6">
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between">
          <div>
            <h2 class="text-h5 font-weight-bold">Active Agent Jobs</h2>
            <p class="text-subtitle-2 text-medium-emphasis mt-1">
              Monitor agents across 4 columns: Pending, Active, Completed, and Blocked
            </p>
          </div>
          <v-btn
            color="primary"
            variant="elevated"
            @click="refreshJobs"
            :loading="refreshing"
            :disabled="refreshing || loading"
          >
            <v-icon start>mdi-refresh</v-icon>
            Refresh
          </v-btn>
        </div>
      </v-col>
    </v-row>

    <!-- Kanban Board -->
    <v-row>
      <v-col cols="12">
        <!-- Loading State -->
        <div v-if="loading" class="d-flex align-center justify-center" style="height: 400px">
          <div class="text-center">
            <v-progress-circular indeterminate color="primary" size="48" class="mb-4" />
            <p class="text-subtitle-2">Loading jobs...</p>
          </div>
        </div>

        <!-- Kanban Board Grid -->
        <v-row v-else class="kanban-board">
          <v-col v-for="column in kanbanColumns" :key="column.status" cols="12" sm="6" md="3" class="kanban-col">
            <kanban-column
              :status="column.status"
              :jobs="column.jobs"
              :title="column.title"
              :description="column.description"
              @view-job-details="openJobDetails"
              @open-messages="openMessagePanel"
            />
          </v-col>
        </v-row>
      </v-col>
    </v-row>

    <!-- Message Thread Panel (Right Drawer) -->
    <message-thread-panel
      v-model="messagePanelOpen"
      :job="selectedJob"
      :column-status="selectedJob?.status"
      @message-sent="onMessageSent"
    />

    <!-- Job Details Dialog -->
    <v-dialog v-model="jobDetailsOpen" max-width="600">
      <v-card v-if="selectedJob">
        <!-- Dialog Header -->
        <v-card-title class="d-flex align-center bg-surface pa-4">
          <v-icon class="mr-3" :color="getJobStatusColor(selectedJob.status)">
            {{ getJobStatusIcon(selectedJob.status) }}
          </v-icon>
          <div class="flex-grow-1">
            <p class="text-h6 font-weight-bold mb-0">Job Details</p>
            <p class="text-caption text-grey">{{ selectedJob.job_id }}</p>
          </div>
          <v-btn icon size="small" variant="text" @click="jobDetailsOpen = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-divider />

        <!-- Dialog Content -->
        <v-card-text class="pa-6">
          <v-row>
            <!-- Agent Info -->
            <v-col cols="12" sm="6">
              <p class="text-caption text-grey mb-1">Agent</p>
              <div class="d-flex align-center gap-2 mb-3">
                <v-icon :color="getAgentTypeColor(selectedJob.agent_type)">
                  {{ getAgentTypeIcon(selectedJob.agent_type) }}
                </v-icon>
                <div>
                  <p class="text-subtitle-2 font-weight-bold mb-0">
                    {{ selectedJob.agent_name || selectedJob.agent_id }}
                  </p>
                  <p class="text-caption text-grey">{{ selectedJob.agent_type }}</p>
                </div>
              </div>
            </v-col>

            <!-- Mode Info -->
            <v-col cols="12" sm="6">
              <p class="text-caption text-grey mb-1">Mode</p>
              <v-chip
                v-if="selectedJob.mode"
                size="small"
                :color="getModeBadgeColor(selectedJob.mode)"
                text-color="white"
              >
                {{ selectedJob.mode }}
              </v-chip>
            </v-col>

            <!-- Status -->
            <v-col cols="12" sm="6">
              <p class="text-caption text-grey mb-1">Status</p>
              <v-chip
                size="small"
                :color="getJobStatusColor(selectedJob.status)"
                text-color="white"
              >
                {{ formatStatus(selectedJob.status) }}
              </v-chip>
            </v-col>

            <!-- Created Time -->
            <v-col cols="12" sm="6">
              <p class="text-caption text-grey mb-1">Created</p>
              <p class="text-body-2">{{ formatDate(selectedJob.created_at) }}</p>
            </v-col>

            <!-- Mission -->
            <v-col cols="12">
              <p class="text-caption text-grey mb-2">Mission</p>
              <v-card variant="tonal" class="pa-3">
                <p class="text-body-2 mb-0 white-space-pre-wrap">
                  {{ selectedJob.mission }}
                </p>
              </v-card>
            </v-col>

            <!-- Progress (Active jobs only) -->
            <v-col v-if="selectedJob.status === 'active' && selectedJob.progress !== undefined" cols="12">
              <p class="text-caption text-grey mb-2">Progress</p>
              <v-progress-linear
                :model-value="selectedJob.progress"
                color="primary"
                height="6"
                rounded
              />
              <p class="text-caption text-grey mt-1">{{ selectedJob.progress }}% Complete</p>
            </v-col>

            <!-- Message Counts -->
            <v-col cols="12">
              <p class="text-caption text-grey mb-2">Messages</p>
              <div class="d-flex flex-wrap gap-2">
                <v-chip
                  v-if="unreadCount > 0"
                  size="small"
                  color="error"
                  text-color="white"
                >
                  <v-icon start size="x-small">mdi-message-badge</v-icon>
                  {{ unreadCount }} Unread
                </v-chip>

                <v-chip
                  v-if="acknowledgedCount > 0"
                  size="small"
                  color="success"
                  text-color="white"
                >
                  <v-icon start size="x-small">mdi-check-all</v-icon>
                  {{ acknowledgedCount }} Read
                </v-chip>

                <v-chip
                  v-if="sentCount > 0"
                  size="small"
                  color="grey-darken-2"
                  text-color="white"
                >
                  <v-icon start size="x-small">mdi-send</v-icon>
                  {{ sentCount }} Sent
                </v-chip>

                <p v-if="totalMessageCount === 0" class="text-caption text-grey">
                  No messages yet
                </p>
              </div>
            </v-col>
          </v-row>
        </v-card-text>

        <v-divider />

        <!-- Dialog Actions -->
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn variant="text" @click="jobDetailsOpen = false">Close</v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            @click="openMessagePanel; jobDetailsOpen = false"
          >
            <v-icon start>mdi-message</v-icon>
            View Messages
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Error Alert -->
    <v-alert
      v-if="error"
      type="error"
      variant="tonal"
      class="mt-4"
      closable
      @click:close="error = null"
    >
      <v-icon start>mdi-alert-circle</v-icon>
      {{ error }}
    </v-alert>
  </div>
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { api } from '@/services/api'
import websocketService from '@/services/websocket'
import { KanbanColumn, JobCard, MessageThreadPanel } from '@/components/kanban'

/**
 * KanbanJobsView Component
 *
 * Displays a 4-column Kanban board for agent job monitoring.
 * Integrated as Tab 2 of ProjectLaunchView.
 *
 * Features:
 * - 4 display-only columns: Pending, Active, Completed, Blocked
 * - Real-time WebSocket updates for job status
 * - Message thread panel for developer-agent communication
 * - Job details dialog with mission and progress info
 * - Three message count badges per job: unread, acknowledged, sent
 *
 * Column Statuses:
 * - pending: Jobs created, waiting for agent to start
 * - active: Jobs in progress (agent working)
 * - completed: Jobs finished successfully
 * - blocked: Jobs failed OR waiting for feedback
 *
 * Agents navigate themselves via MCP tools (no drag-drop).
 */

const props = defineProps({
  projectId: {
    type: String,
    required: true,
  },
})

// State
const jobs = ref([])
const selectedJob = ref(null)
const jobDetailsOpen = ref(false)
const messagePanelOpen = ref(false)
const loading = ref(false)
const refreshing = ref(false)
const error = ref(null)

// WebSocket unsubscribe function
let unsubscribeJobUpdate = null

/**
 * Kanban columns configuration
 */
const kanbanColumns = computed(() => {
  const pending = jobs.value.filter((j) => j.status === 'pending')
  const active = jobs.value.filter((j) => j.status === 'active')
  const completed = jobs.value.filter((j) => j.status === 'completed')
  const blocked = jobs.value.filter((j) => j.status === 'blocked')

  return [
    {
      status: 'pending',
      title: 'Pending',
      description: 'Waiting to start',
      jobs: pending,
    },
    {
      status: 'active',
      title: 'Active',
      description: 'In progress',
      jobs: active,
    },
    {
      status: 'completed',
      title: 'Completed',
      description: 'Successfully finished',
      jobs: completed,
    },
    {
      status: 'blocked',
      title: 'Blocked',
      description: 'Failed or needs feedback',
      jobs: blocked,
    },
  ]
})

/**
 * Message count calculations for selected job
 */
const unreadCount = computed(() => {
  if (!selectedJob.value?.messages || !Array.isArray(selectedJob.value.messages)) return 0
  return selectedJob.value.messages.filter((m) => m.status === 'pending').length
})

const acknowledgedCount = computed(() => {
  if (!selectedJob.value?.messages || !Array.isArray(selectedJob.value.messages)) return 0
  return selectedJob.value.messages.filter((m) => m.status === 'acknowledged').length
})

const sentCount = computed(() => {
  if (!selectedJob.value?.messages || !Array.isArray(selectedJob.value.messages)) return 0
  return selectedJob.value.messages.filter((m) => m.from === 'developer').length
})

const totalMessageCount = computed(() => {
  return unreadCount.value + acknowledgedCount.value + sentCount.value
})

/**
 * Agent type icon and color mapping
 */
const agentTypeMap = {
  orchestrator: { icon: 'mdi-brain', color: 'purple' },
  analyzer: { icon: 'mdi-magnify', color: 'blue' },
  implementer: { icon: 'mdi-code-braces', color: 'green' },
  tester: { icon: 'mdi-test-tube', color: 'orange' },
  'ux-designer': { icon: 'mdi-palette', color: 'pink' },
  backend: { icon: 'mdi-server', color: 'teal' },
  frontend: { icon: 'mdi-monitor', color: 'indigo' },
}

/**
 * Fetch Kanban board data
 */
async function fetchJobs() {
  loading.value = true
  error.value = null

  try {
    const response = await api.agentJobs.getKanbanBoard(props.projectId)
    jobs.value = response.data.jobs || []

    console.log('[KanbanJobsView] Jobs fetched:', jobs.value.length)
  } catch (err) {
    console.error('[KanbanJobsView] Error fetching jobs:', err)
    error.value = 'Failed to load jobs. Please try refreshing.'
    jobs.value = []
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
 * Open job details dialog
 */
function openJobDetails(job) {
  selectedJob.value = job
  jobDetailsOpen.value = true
}

/**
 * Open message thread panel
 */
function openMessagePanel(job) {
  if (typeof job === 'string') {
    // Called with job_id
    const foundJob = jobs.value.flatMap((col) => col).find((j) => j.job_id === job)
    if (foundJob) {
      selectedJob.value = foundJob
    }
  } else {
    // Called with job object
    selectedJob.value = job
  }
  messagePanelOpen.value = true
}

/**
 * Handle message sent
 */
function onMessageSent(message) {
  if (selectedJob.value) {
    if (!selectedJob.value.messages) {
      selectedJob.value.messages = []
    }
    selectedJob.value.messages.push(message)
    console.log('[KanbanJobsView] Message sent:', message.content.substring(0, 50))
  }
}

/**
 * Get status icon for job
 */
function getJobStatusIcon(status) {
  const icons = {
    pending: 'mdi-clock-outline',
    active: 'mdi-play-circle',
    completed: 'mdi-check-circle',
    blocked: 'mdi-alert-circle',
  }
  return icons[status] || 'mdi-help-circle'
}

/**
 * Get status color for job
 */
function getJobStatusColor(status) {
  const colors = {
    pending: 'grey',
    active: 'primary',
    completed: 'success',
    blocked: 'error',
  }
  return colors[status] || 'grey'
}

/**
 * Get agent type icon
 */
function getAgentTypeIcon(agentType) {
  const typeKey = agentType?.toLowerCase() || 'implementer'
  return agentTypeMap[typeKey]?.icon || 'mdi-robot'
}

/**
 * Get agent type color
 */
function getAgentTypeColor(agentType) {
  const typeKey = agentType?.toLowerCase() || 'implementer'
  return agentTypeMap[typeKey]?.color || 'grey'
}

/**
 * Get mode badge color
 */
function getModeBadgeColor(mode) {
  const colors = {
    claude: 'deep-purple',
    codex: 'blue',
    gemini: 'light-blue',
  }
  return colors[mode?.toLowerCase()] || 'grey'
}

/**
 * Format status text
 */
function formatStatus(status) {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

/**
 * Format date for display
 */
function formatDate(dateString) {
  if (!dateString) return 'Unknown'

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

  console.log('[KanbanJobsView] Job update received:', data.job_id, data.status)

  const jobIndex = jobs.value.findIndex((j) => j.job_id === data.job_id)

  if (jobIndex !== -1) {
    // Update existing job
    jobs.value[jobIndex] = { ...jobs.value[jobIndex], ...data }

    // Update selected job if it's the one being viewed
    if (selectedJob.value?.job_id === data.job_id) {
      selectedJob.value = { ...selectedJob.value, ...data }
    }
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

  // Fetch initial jobs
  fetchJobs()

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
.kanban-jobs-view {
  width: 100%;
  height: 100%;
}

.kanban-board {
  gap: 1.5rem;
}

.kanban-col {
  display: flex;
  flex-direction: column;
}

/* Responsive adjustments */
@media (max-width: 960px) {
  .kanban-board {
    gap: 1rem;
  }
}

@media (max-width: 600px) {
  .kanban-col {
    margin-bottom: 1rem;
  }
}

/* White space pre-wrap for mission display */
.white-space-pre-wrap {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
