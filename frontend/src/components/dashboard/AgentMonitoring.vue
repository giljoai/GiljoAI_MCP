<template>
  <v-container fluid class="agent-monitoring">
    <!-- Header -->
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between mb-4">
          <div>
            <h2 class="text-h5">Agent Monitoring</h2>
            <p class="text-body-2 text-medium-emphasis mt-1">
              Real-time status of AI agents coordinating your projects
            </p>
          </div>
          <div class="d-flex align-center gap-3">
            <!-- WebSocket Connection Status -->
            <v-chip :color="wsStore.isConnected ? 'success' : 'error'" size="small" variant="flat">
              <v-icon left size="small">
                {{ wsStore.isConnected ? 'mdi-wifi' : 'mdi-wifi-off' }}
              </v-icon>
              {{ wsStore.isConnected ? 'Live' : 'Disconnected' }}
            </v-chip>

            <!-- Active Agent Count -->
            <v-chip color="primary" size="small" variant="outlined">
              <v-icon left size="small">mdi-account-multiple</v-icon>
              {{ activeAgentCount }} Active
            </v-chip>

            <!-- Refresh Button -->
            <v-btn
              icon="mdi-refresh"
              size="small"
              variant="text"
              @click="refreshAgents"
              :loading="loading"
              aria-label="Refresh agent list"
            />
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Filter Tabs -->
    <v-row v-if="agents.length > 0">
      <v-col cols="12">
        <v-tabs v-model="activeTab" color="primary" density="compact">
          <v-tab value="all"> All ({{ agents.length }}) </v-tab>
          <v-tab value="working"> Working ({{ workingAgents.length }}) </v-tab>
          <v-tab value="waiting"> Waiting ({{ waitingAgents.length }}) </v-tab>
          <v-tab value="completed"> Completed ({{ completedAgents.length }}) </v-tab>
          <v-tab value="failed"> Failed ({{ failedAgents.length }}) </v-tab>
        </v-tabs>
      </v-col>
    </v-row>

    <!-- Agent Cards Grid -->
    <v-row>
      <v-col v-for="agent in filteredAgents" :key="agent.job_id" cols="12" sm="6" md="4" lg="3">
        <AgentCard :agent="agent" mode="jobs" @view-details="viewAgentDetails" />
      </v-col>

      <!-- Empty State -->
      <v-col v-if="agents.length === 0 && !loading" cols="12">
        <v-alert type="info" variant="tonal" prominent class="text-center">
          <v-icon size="64" class="mb-4">mdi-robot-outline</v-icon>
          <div class="text-h6 mb-2">No Active Agents</div>
          <div class="text-body-2">
            Launch a project to spawn AI agents. Agents will appear here in real-time.
          </div>
          <v-btn color="primary" variant="outlined" class="mt-4" @click="navigateToProjects">
            <v-icon left>mdi-rocket-launch</v-icon>
            Go to Projects
          </v-btn>
        </v-alert>
      </v-col>

      <!-- Loading State -->
      <v-col v-if="loading && agents.length === 0" cols="12">
        <div class="text-center py-8">
          <v-progress-circular indeterminate color="primary" size="64" />
          <div class="text-body-1 mt-4">Loading agents...</div>
        </div>
      </v-col>

      <!-- No Results for Filter -->
      <v-col v-if="!loading && agents.length > 0 && filteredAgents.length === 0" cols="12">
        <v-alert type="info" variant="tonal" class="text-center">
          <div class="text-body-1">No agents found with status: {{ activeTab }}</div>
        </v-alert>
      </v-col>
    </v-row>

    <!-- Cancel Confirmation Dialog -->
    <v-dialog v-model="showCancelDialog" max-width="500">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon left color="warning">mdi-alert</v-icon>
          Cancel Agent Job
        </v-card-title>
        <v-card-text>
          <p class="mb-3">Are you sure you want to cancel this agent job?</p>
          <v-alert type="info" density="compact" variant="tonal" class="mb-3">
            <div class="text-caption">
              <strong>Agent:</strong> {{ agentToCancelType }}<br />
              <strong>ID:</strong> {{ agentToCancelId }}
            </div>
          </v-alert>
          <p class="text-body-2 text-medium-emphasis">
            This action cannot be undone. The agent will stop its current task.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="grey" variant="text" @click="showCancelDialog = false">
            Keep Working
          </v-btn>
          <v-btn color="warning" variant="flat" @click="confirmCancelAgent" :loading="cancelling">
            <v-icon left>mdi-cancel</v-icon>
            Cancel Agent
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useWebSocketStore } from '@/stores/websocket'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'
import AgentCard from '@/components/AgentCard.vue'

// Composables
const router = useRouter()
const wsStore = useWebSocketStore()
const toast = useToast()

// State
const agents = ref([])
const loading = ref(false)
const activeTab = ref('all')
const showCancelDialog = ref(false)
const agentToCancel = ref(null)
const cancelling = ref(false)

// Computed properties
const activeAgentCount = computed(() => {
  return agents.value.filter(
    (a) => a.status === 'working' || a.status === 'waiting' || a.status === 'cancelling',
  ).length
})

const workingAgents = computed(() =>
  agents.value.filter((a) => a.status === 'working' || a.status === 'cancelling'),
)

const waitingAgents = computed(() => agents.value.filter((a) => a.status === 'waiting'))

const completedAgents = computed(() => agents.value.filter((a) => a.status === 'completed'))

const failedAgents = computed(() => agents.value.filter((a) => a.status === 'failed'))

const filteredAgents = computed(() => {
  if (activeTab.value === 'all') return agents.value
  if (activeTab.value === 'working') return workingAgents.value
  if (activeTab.value === 'waiting') return waitingAgents.value
  if (activeTab.value === 'completed') return completedAgents.value
  if (activeTab.value === 'failed') return failedAgents.value
  return agents.value
})

const agentToCancelType = computed(() =>
  agentToCancel.value ? agentToCancel.value.agent_type : '',
)

const agentToCancelId = computed(() =>
  agentToCancel.value ? agentToCancel.value.job_id.substring(0, 8) : '',
)

// Methods
async function fetchAgents() {
  loading.value = true
  try {
    // Fetch all agent jobs (across all projects)
    const response = await api.agentJobs.list()
    agents.value = response.data || []
  } catch (error) {
    console.error('[AgentMonitoring] Failed to fetch agents:', error)
    toast.error('Failed to load agent data')
    agents.value = []
  } finally {
    loading.value = false
  }
}

async function refreshAgents() {
  await fetchAgents()
  toast.success('Agent list refreshed')
}

function viewAgentDetails(agent) {
  // Navigate to project's Jobs tab to view full agent details
  if (agent.project_id) {
    router.push({
      path: `/projects/${agent.project_id}/launch`,
      query: { tab: 'jobs', agent: agent.job_id },
    })
  } else {
    toast.info('No project associated with this agent')
  }
}

function handleCancelAgent(agent) {
  agentToCancel.value = agent
  showCancelDialog.value = true
}

async function confirmCancelAgent() {
  if (!agentToCancel.value) return

  cancelling.value = true
  try {
    await api.agentJobs.terminate(agentToCancel.value.job_id, 'User cancelled from dashboard')

    // Update local state optimistically
    const agentIndex = agents.value.findIndex((a) => a.job_id === agentToCancel.value.job_id)
    if (agentIndex !== -1) {
      agents.value[agentIndex].status = 'cancelling'
    }

    toast.success('Agent cancellation initiated')
    showCancelDialog.value = false
    agentToCancel.value = null
  } catch (error) {
    console.error('[AgentMonitoring] Failed to cancel agent:', error)
    toast.error('Failed to cancel agent: ' + (error.response?.data?.detail || error.message))
  } finally {
    cancelling.value = false
  }
}

function viewMessages(agent) {
  // Navigate to Messages view filtered by agent
  router.push({
    path: '/messages',
    query: { agent: agent.job_id },
  })
}

function navigateToProjects() {
  router.push('/projects')
}

// WebSocket event handlers
function handleAgentStatusChange(data) {
  console.log('[AgentMonitoring] Agent status changed:', data)

  // Find and update the agent in our list
  const agentIndex = agents.value.findIndex((a) => a.job_id === data.job_id)

  if (agentIndex !== -1) {
    // Update existing agent
    agents.value[agentIndex] = {
      ...agents.value[agentIndex],
      ...data,
      last_heartbeat: new Date().toISOString(),
    }
  } else {
    // New agent appeared - add it
    agents.value.push({
      ...data,
      last_heartbeat: new Date().toISOString(),
    })
  }
}

function handleAgentCompleted(data) {
  console.log('[AgentMonitoring] Agent completed:', data)

  const agentIndex = agents.value.findIndex((a) => a.job_id === data.job_id)
  if (agentIndex !== -1) {
    agents.value[agentIndex].status = 'completed'
    agents.value[agentIndex].progress = 100
    agents.value[agentIndex].last_heartbeat = new Date().toISOString()
  }

  toast.success(`Agent ${data.agent_type} completed successfully`)
}

function handleAgentFailed(data) {
  console.log('[AgentMonitoring] Agent failed:', data)

  const agentIndex = agents.value.findIndex((a) => a.job_id === data.job_id)
  if (agentIndex !== -1) {
    agents.value[agentIndex].status = 'failed'
    agents.value[agentIndex].failure_reason = data.failure_reason || 'Unknown error'
    agents.value[agentIndex].last_heartbeat = new Date().toISOString()
  }

  toast.error(`Agent ${data.agent_type} failed: ${data.failure_reason || 'Unknown error'}`)
}

function handleAgentProgress(data) {
  console.log('[AgentMonitoring] Agent progress update:', data)

  const agentIndex = agents.value.findIndex((a) => a.job_id === data.job_id)
  if (agentIndex !== -1) {
    agents.value[agentIndex].progress = data.progress
    agents.value[agentIndex].current_task = data.current_task
    agents.value[agentIndex].last_heartbeat = new Date().toISOString()
  }
}

function handleAgentCancelled(data) {
  console.log('[AgentMonitoring] Agent cancelled:', data)

  const agentIndex = agents.value.findIndex((a) => a.job_id === data.job_id)
  if (agentIndex !== -1) {
    agents.value[agentIndex].status = 'cancelled'
    agents.value[agentIndex].last_heartbeat = new Date().toISOString()
  }

  toast.info(`Agent ${data.agent_type} was cancelled`)
}

// Lifecycle hooks
onMounted(async () => {
  // Initial fetch
  await fetchAgents()

  // Set up WebSocket listeners
  // Based on backend WebSocket events from api/websocket.py
  wsStore.on('agent:status_changed', handleAgentStatusChange)
  wsStore.on('agent:completed', handleAgentCompleted)
  wsStore.on('agent:failed', handleAgentFailed)
  wsStore.on('agent:progress', handleAgentProgress)
  wsStore.on('agent:cancelled', handleAgentCancelled)
  wsStore.on('job:status_changed', handleAgentStatusChange) // Alias event

  console.log('[AgentMonitoring] WebSocket listeners registered')
})

onUnmounted(() => {
  // Clean up WebSocket listeners
  wsStore.off('agent:status_changed', handleAgentStatusChange)
  wsStore.off('agent:completed', handleAgentCompleted)
  wsStore.off('agent:failed', handleAgentFailed)
  wsStore.off('agent:progress', handleAgentProgress)
  wsStore.off('agent:cancelled', handleAgentCancelled)
  wsStore.off('job:status_changed', handleAgentStatusChange)

  console.log('[AgentMonitoring] WebSocket listeners removed')
})
</script>

<style scoped>
.agent-monitoring {
  min-height: 400px;
}

.gap-3 {
  gap: 12px;
}
</style>
