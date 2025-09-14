<template>
  <v-container>
    <!-- Header -->
    <v-row align="center" class="mb-4">
      <v-col>
        <h1 class="text-h4">Agent Monitoring</h1>
        <p class="text-subtitle-1 text-medium-emphasis">
          Monitor agent health, status, and performance in real-time
        </p>
      </v-col>
      <v-col cols="auto">
        <v-btn
          color="primary"
          prepend-icon="mdi-robot-happy"
          @click="refreshAgents"
          :loading="loading"
        >
          Refresh Status
        </v-btn>
      </v-col>
    </v-row>

    <!-- Filter Chips -->
    <v-row class="mb-4">
      <v-col>
        <v-chip-group v-model="statusFilter" multiple filter>
          <v-chip value="all" color="primary">All</v-chip>
          <v-chip value="active" color="success">Active</v-chip>
          <v-chip value="working" color="warning">Working</v-chip>
          <v-chip value="idle" color="info">Idle</v-chip>
          <v-chip value="error" color="error">Error</v-chip>
          <v-chip value="decommissioned" color="grey">Decommissioned</v-chip>
        </v-chip-group>
      </v-col>
    </v-row>

    <!-- Agent Cards Grid -->
    <v-row>
      <v-col
        v-for="agent in filteredAgents"
        :key="agent.id"
        cols="12"
        sm="6"
        md="4"
        lg="3"
      >
        <v-card
          :color="getAgentCardColor(agent)"
          variant="tonal"
          class="h-100"
        >
          <!-- Agent Header -->
          <v-card-title>
            <v-row align="center" no-gutters>
              <v-col>
                <div class="d-flex align-center">
                  <v-avatar
                    :color="getStatusColor(agent.status)"
                    size="32"
                    class="mr-2"
                  >
                    <v-icon size="20">mdi-robot</v-icon>
                  </v-avatar>
                  <div>
                    <div class="text-h6">{{ agent.name }}</div>
                    <div class="text-caption">{{ formatAgentRole(agent.role) }}</div>
                  </div>
                </div>
              </v-col>
              <v-col cols="auto">
                <v-icon
                  :color="getStatusColor(agent.status)"
                  size="12"
                  class="status-indicator"
                >
                  mdi-circle
                </v-icon>
              </v-col>
            </v-row>
          </v-card-title>

          <v-card-text>
            <!-- Status -->
            <div class="mb-3">
              <div class="text-caption text-medium-emphasis">Status</div>
              <v-chip
                :color="getStatusColor(agent.status)"
                size="small"
                variant="flat"
              >
                {{ formatStatus(agent.status) }}
              </v-chip>
            </div>

            <!-- Current Job -->
            <div class="mb-3" v-if="agent.current_job">
              <div class="text-caption text-medium-emphasis">Current Job</div>
              <div class="text-body-2">{{ agent.current_job.type }}</div>
              <v-progress-linear
                :model-value="agent.current_job.progress || 0"
                color="primary"
                height="4"
                rounded
                class="mt-1"
              ></v-progress-linear>
            </div>

            <!-- Context Usage -->
            <div class="mb-3">
              <div class="text-caption text-medium-emphasis">Context Usage</div>
              <v-progress-linear
                :model-value="getContextUsagePercent(agent)"
                :color="getContextUsageColor(agent)"
                height="20"
                rounded
              >
                <template v-slot:default>
                  <span class="text-caption">
                    {{ formatNumber(agent.context_used || 0) }}
                  </span>
                </template>
              </v-progress-linear>
            </div>

            <!-- Health Metrics -->
            <div class="mb-3" v-if="agentHealth[agent.id]">
              <div class="text-caption text-medium-emphasis mb-1">Health Metrics</div>
              <v-row dense>
                <v-col cols="6">
                  <div class="text-caption">CPU</div>
                  <div class="text-body-2 font-weight-bold">
                    {{ agentHealth[agent.id].cpu || 0 }}%
                  </div>
                </v-col>
                <v-col cols="6">
                  <div class="text-caption">Memory</div>
                  <div class="text-body-2 font-weight-bold">
                    {{ agentHealth[agent.id].memory || 0 }}%
                  </div>
                </v-col>
              </v-row>
            </div>

            <!-- Messages -->
            <div class="mb-2">
              <div class="text-caption text-medium-emphasis">Messages</div>
              <v-row dense>
                <v-col cols="6">
                  <v-chip size="x-small" variant="outlined">
                    <v-icon start size="x-small">mdi-inbox</v-icon>
                    {{ agent.messages_received || 0 }}
                  </v-chip>
                </v-col>
                <v-col cols="6">
                  <v-chip size="x-small" variant="outlined">
                    <v-icon start size="x-small">mdi-send</v-icon>
                    {{ agent.messages_sent || 0 }}
                  </v-chip>
                </v-col>
              </v-row>
            </div>

            <!-- Last Active -->
            <div>
              <div class="text-caption text-medium-emphasis">Last Active</div>
              <div class="text-caption">{{ formatRelativeTime(agent.last_active) }}</div>
            </div>
          </v-card-text>

          <!-- Actions -->
          <v-card-actions>
            <v-btn
              size="small"
              variant="text"
              @click="viewAgentDetails(agent)"
            >
              Details
            </v-btn>
            <v-spacer></v-spacer>
            <v-btn
              v-if="agent.status !== 'decommissioned'"
              size="small"
              variant="text"
              color="warning"
              @click="decommissionAgent(agent)"
            >
              Decommission
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Empty State -->
    <v-row v-if="filteredAgents.length === 0 && !loading">
      <v-col>
        <v-card>
          <v-card-text class="text-center py-8">
            <v-icon size="64" color="grey">mdi-robot-off</v-icon>
            <p class="text-h6 mt-4">No agents found</p>
            <p class="text-body-2 text-medium-emphasis">
              {{ statusFilter.length ? 'Try adjusting your filters' : 'No agents are currently active' }}
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Agent Details Dialog -->
    <v-dialog v-model="showDetailsDialog" max-width="800">
      <v-card v-if="selectedAgent">
        <v-card-title>
          <v-row align="center">
            <v-col>
              Agent Details: {{ selectedAgent.name }}
            </v-col>
            <v-col cols="auto">
              <v-chip
                :color="getStatusColor(selectedAgent.status)"
                size="small"
              >
                {{ formatStatus(selectedAgent.status) }}
              </v-chip>
            </v-col>
          </v-row>
        </v-card-title>
        
        <v-card-text>
          <v-row>
            <v-col cols="12" md="6">
              <div class="text-overline mb-2">General Information</div>
              <v-list density="compact">
                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon>mdi-identifier</v-icon>
                  </template>
                  <v-list-item-title>ID</v-list-item-title>
                  <v-list-item-subtitle>{{ selectedAgent.id }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon>mdi-account-badge</v-icon>
                  </template>
                  <v-list-item-title>Role</v-list-item-title>
                  <v-list-item-subtitle>{{ formatAgentRole(selectedAgent.role) }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon>mdi-folder</v-icon>
                  </template>
                  <v-list-item-title>Project</v-list-item-title>
                  <v-list-item-subtitle>{{ selectedAgent.project_name || 'N/A' }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>
            
            <v-col cols="12" md="6">
              <div class="text-overline mb-2">Performance Metrics</div>
              <v-list density="compact">
                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon>mdi-message-processing</v-icon>
                  </template>
                  <v-list-item-title>Messages Processed</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ selectedAgent.messages_received + selectedAgent.messages_sent }}
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon>mdi-clipboard-check</v-icon>
                  </template>
                  <v-list-item-title>Tasks Completed</v-list-item-title>
                  <v-list-item-subtitle>{{ selectedAgent.tasks_completed || 0 }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon>mdi-timer</v-icon>
                  </template>
                  <v-list-item-title>Uptime</v-list-item-title>
                  <v-list-item-subtitle>{{ formatUptime(selectedAgent.created_at) }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>
          </v-row>

          <!-- Current Mission -->
          <div v-if="selectedAgent.mission" class="mt-4">
            <div class="text-overline mb-2">Current Mission</div>
            <v-card variant="outlined">
              <v-card-text>
                {{ selectedAgent.mission }}
              </v-card-text>
            </v-card>
          </div>

          <!-- Recent Activity Log -->
          <div class="mt-4">
            <div class="text-overline mb-2">Recent Activity</div>
            <v-timeline density="compact" side="end">
              <v-timeline-item
                v-for="(activity, index) in getRecentActivity(selectedAgent)"
                :key="index"
                :dot-color="activity.color"
                size="x-small"
              >
                <div class="text-caption">{{ formatDate(activity.timestamp) }}</div>
                <div class="text-body-2">{{ activity.description }}</div>
              </v-timeline-item>
            </v-timeline>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showDetailsDialog = false">Close</v-btn>
          <v-btn
            v-if="selectedAgent.status !== 'decommissioned'"
            color="warning"
            variant="flat"
            @click="decommissionAgent(selectedAgent)"
          >
            Decommission
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAgentStore } from '@/stores/agents'
import { useWebSocketStore } from '@/stores/websocket'
import { 
  formatDate, 
  formatRelativeTime, 
  formatNumber, 
  formatStatus,
  formatAgentRole 
} from '@/utils/formatters'
import { AGENT_STATUS, REFRESH_INTERVALS } from '@/utils/constants'

// Stores
const agentStore = useAgentStore()
const wsStore = useWebSocketStore()

// Reactive state
const statusFilter = ref(['all'])
const showDetailsDialog = ref(false)
const selectedAgent = ref(null)
const refreshInterval = ref(null)

// Computed properties
const agents = computed(() => agentStore.agents)
const loading = computed(() => agentStore.loading)
const agentHealth = computed(() => agentStore.healthData)

const filteredAgents = computed(() => {
  if (statusFilter.value.includes('all')) {
    return agents.value
  }
  
  return agents.value.filter(agent => 
    statusFilter.value.includes(agent.status)
  )
})

// Methods
function getStatusColor(status) {
  const colors = {
    active: 'success',
    working: 'warning',
    idle: 'info',
    error: 'error',
    inactive: 'grey',
    decommissioned: 'grey'
  }
  return colors[status] || 'default'
}

function getAgentCardColor(agent) {
  if (agent.status === 'error') return 'error'
  if (agent.status === 'working') return 'warning'
  return undefined
}

function getContextUsagePercent(agent) {
  if (!agent.context_budget) return 0
  return (agent.context_used / agent.context_budget) * 100
}

function getContextUsageColor(agent) {
  const usage = getContextUsagePercent(agent)
  if (usage > 90) return 'error'
  if (usage > 70) return 'warning'
  return 'success'
}

function formatUptime(createdAt) {
  if (!createdAt) return 'N/A'
  
  const created = new Date(createdAt)
  const now = new Date()
  const diff = now - created
  
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
  
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

function getRecentActivity(agent) {
  // Mock activity data - in real app, this would come from the backend
  return [
    {
      timestamp: new Date(),
      description: 'Status changed to ' + agent.status,
      color: getStatusColor(agent.status)
    },
    {
      timestamp: new Date(Date.now() - 3600000),
      description: 'Completed task: Data analysis',
      color: 'success'
    },
    {
      timestamp: new Date(Date.now() - 7200000),
      description: 'Started new job: Implementation',
      color: 'info'
    }
  ]
}

async function refreshAgents() {
  await agentStore.fetchAgents()
  
  // Fetch health data for each active agent
  const activeAgents = agents.value.filter(a => a.status === 'active')
  await Promise.all(
    activeAgents.map(agent => agentStore.fetchAgentHealth(agent.id))
  )
}

function viewAgentDetails(agent) {
  selectedAgent.value = agent
  showDetailsDialog.value = true
}

async function decommissionAgent(agent) {
  if (confirm(`Are you sure you want to decommission agent "${agent.name}"?`)) {
    try {
      await agentStore.decommissionAgent(agent.id, 'User requested decommission')
      if (showDetailsDialog.value) {
        showDetailsDialog.value = false
      }
    } catch (error) {
      console.error('Failed to decommission agent:', error)
    }
  }
}

// WebSocket subscriptions
function subscribeToUpdates() {
  wsStore.subscribe('agent:status', (data) => {
    agentStore.updateAgentStatus(data.agentId, data.status)
  })
}

// Lifecycle
onMounted(async () => {
  await refreshAgents()
  
  // Set up auto-refresh
  refreshInterval.value = setInterval(refreshAgents, REFRESH_INTERVALS.AGENT_HEALTH)
  
  // Subscribe to WebSocket updates
  subscribeToUpdates()
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})
</script>

<style scoped>
.status-indicator {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
  100% {
    opacity: 1;
  }
}
</style>