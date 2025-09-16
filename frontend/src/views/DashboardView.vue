<template>
  <v-container fluid>
    <!-- Header -->
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Dashboard</h1>
      </v-col>
    </v-row>
    
    <!-- Stats Cards -->
    <v-row>
      <v-col cols="12" sm="6" md="3">
        <v-card elevation="2">
          <v-card-text class="text-center">
            <v-icon size="48" color="primary">mdi-folder-multiple</v-icon>
            <div class="text-h6 mt-2">Projects</div>
            <div class="text-h4">{{ stats.projects }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card elevation="2">
          <v-card-text class="text-center">
            <v-icon size="48" color="success">mdi-robot</v-icon>
            <div class="text-h6 mt-2">Active Agents</div>
            <div class="text-h4">{{ stats.activeAgents }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card elevation="2">
          <v-card-text class="text-center">
            <v-icon size="48" color="warning">mdi-message-text</v-icon>
            <div class="text-h6 mt-2">Messages</div>
            <div class="text-h4">{{ stats.messages }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card elevation="2">
          <v-card-text class="text-center">
            <v-icon size="48" color="info">mdi-clipboard-check</v-icon>
            <div class="text-h6 mt-2">Tasks</div>
            <div class="text-h4">{{ stats.tasks }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Agent Visualizations -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-tabs v-model="activeTab" color="primary">
          <v-tab value="timeline">
            <v-icon left>mdi-timeline-text</v-icon>
            Timeline View
          </v-tab>
          <v-tab value="tree">
            <v-icon left>mdi-file-tree</v-icon>
            Hierarchy View
          </v-tab>
          <v-tab value="metrics">
            <v-icon left>mdi-chart-line</v-icon>
            Metrics
          </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
          <!-- Timeline Tab -->
          <v-window-item value="timeline">
            <SubAgentTimelineHorizontal
              :project-id="selectedProject"
              :auto-refresh="true"
              @agent-selected="handleAgentSelected"
              @export-requested="handleExport"
            />
          </v-window-item>

          <!-- Tree Tab -->
          <v-window-item value="tree">
            <SubAgentTree
              :project-id="selectedProject"
              :expand-level="2"
              @node-selected="handleNodeSelected"
              @context-menu="handleContextMenu"
            />
          </v-window-item>

          <!-- Metrics Tab -->
          <v-window-item value="metrics">
            <AgentMetrics
              :project-id="selectedProject"
              :metrics="agentMetrics"
            />
          </v-window-item>
        </v-window>
      </v-col>
    </v-row>

    <!-- Recent Activity -->
    <v-row class="mt-4">
      <v-col cols="12" md="6">
        <v-card elevation="2">
          <v-card-title>
            <v-icon left color="primary">mdi-history</v-icon>
            Recent Activity
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item
                v-for="activity in recentActivities"
                :key="activity.id"
              >
                <template v-slot:prepend>
                  <v-icon :color="getActivityColor(activity.type)" size="small">
                    {{ getActivityIcon(activity.type) }}
                  </v-icon>
                </template>
                <v-list-item-title>{{ activity.title }}</v-list-item-title>
                <v-list-item-subtitle>{{ formatTime(activity.timestamp) }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card elevation="2">
          <v-card-title>
            <v-icon left color="primary">mdi-speedometer</v-icon>
            Performance
          </v-card-title>
          <v-card-text>
            <v-row dense>
              <v-col cols="6">
                <div class="text-caption">Avg Response Time</div>
                <div class="text-h6">{{ performance.avgResponseTime }}ms</div>
              </v-col>
              <v-col cols="6">
                <div class="text-caption">Success Rate</div>
                <div class="text-h6">{{ performance.successRate }}%</div>
              </v-col>
              <v-col cols="6">
                <div class="text-caption">Token Usage</div>
                <div class="text-h6">{{ formatTokens(performance.tokenUsage) }}</div>
              </v-col>
              <v-col cols="6">
                <div class="text-caption">Active Sessions</div>
                <div class="text-h6">{{ performance.activeSessions }}</div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAgentStore } from '@/stores/agents'
import { useProjectStore } from '@/stores/projects'
import { useMessageStore } from '@/stores/messages'
import { useTaskStore } from '@/stores/tasks'
import SubAgentTimelineHorizontal from '@/components/SubAgentTimelineHorizontal.vue'
import SubAgentTree from '@/components/SubAgentTree.vue'
import AgentMetrics from '@/components/AgentMetrics.vue'
import { formatDistanceToNow } from 'date-fns'
import websocketService from '@/services/websocket'

// Stores
const agentStore = useAgentStore()
const projectStore = useProjectStore()
const messageStore = useMessageStore()
const taskStore = useTaskStore()

// Reactive data
const activeTab = ref('timeline')
const selectedProject = ref(null)
const agentMetrics = ref(null)
const refreshInterval = ref(null)

// Stats
const stats = computed(() => ({
  projects: projectStore.projects?.length || 0,
  activeAgents: agentStore.activeAgents?.length || 0,
  messages: messageStore.messages?.length || 0,
  tasks: taskStore.tasks?.length || 0
}))

// Recent activities
const recentActivities = computed(() => {
  const activities = []
  
  // Add agent activities
  agentStore.agentTimeline.slice(0, 5).forEach(event => {
    activities.push({
      id: event.id,
      type: event.type,
      title: `${event.agent_name} ${event.type}`,
      timestamp: event.timestamp
    })
  })

  return activities.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 10)
})

// Performance metrics
const performance = ref({
  avgResponseTime: 45,
  successRate: 98.5,
  tokenUsage: 125000,
  activeSessions: 3
})

// Methods
const handleAgentSelected = (agent) => {
  console.log('Agent selected:', agent)
}

const handleNodeSelected = (node) => {
  console.log('Node selected:', node)
}

const handleContextMenu = ({ node, event }) => {
  console.log('Context menu for node:', node)
}

const handleExport = (format) => {
  console.log('Export requested:', format)
}

const getActivityColor = (type) => {
  const colors = {
    spawn: 'success',
    complete: 'grey',
    error: 'error',
    warning: 'warning'
  }
  return colors[type] || 'info'
}

const getActivityIcon = (type) => {
  const icons = {
    spawn: 'mdi-rocket-launch',
    complete: 'mdi-check-circle',
    error: 'mdi-alert-circle',
    warning: 'mdi-alert'
  }
  return icons[type] || 'mdi-information'
}

const formatTime = (timestamp) => {
  return formatDistanceToNow(new Date(timestamp), { addSuffix: true })
}

const formatTokens = (tokens) => {
  if (tokens > 1000000) {
    return `${(tokens / 1000000).toFixed(1)}M`
  }
  if (tokens > 1000) {
    return `${(tokens / 1000).toFixed(1)}K`
  }
  return tokens.toString()
}

const loadMetrics = async () => {
  if (selectedProject.value) {
    agentMetrics.value = await agentStore.fetchAgentMetrics(selectedProject.value)
  }
}

const refreshData = async () => {
  await Promise.all([
    projectStore.fetchProjects(),
    agentStore.fetchAgents(),
    messageStore.fetchMessages(),
    taskStore.fetchTasks()
  ])
  
  if (selectedProject.value) {
    await agentStore.fetchAgentTree(selectedProject.value)
    await loadMetrics()
  }
}

// WebSocket handlers
const handleRealtimeUpdate = (data) => {
  // Update stats in real-time
  performance.value.activeSessions = data.activeSessions || performance.value.activeSessions
}

// Lifecycle
onMounted(async () => {
  await refreshData()

  // Set up refresh interval
  refreshInterval.value = setInterval(refreshData, 30000)

  // Set up WebSocket listeners
  const unsubscribe = websocketService.onMessage('stats:update', handleRealtimeUpdate)

  // Select first project if available
  if (projectStore.projects.length > 0) {
    selectedProject.value = projectStore.projects[0].id
    await loadMetrics()
  }

  onUnmounted(() => {
    if (refreshInterval.value) {
      clearInterval(refreshInterval.value)
    }
    unsubscribe()
  })
})
</script>