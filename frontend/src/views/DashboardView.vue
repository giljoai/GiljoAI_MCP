<template>
  <v-container fluid>
    <!-- Setup Banner (shown when database not configured) -->
    <v-alert
      v-if="setupStatus.requires_setup"
      type="warning"
      prominent
      closable
      class="mb-4"
      @click:close="dismissSetupBanner"
    >
      <v-alert-title class="text-h6">
        <v-icon left>mdi-database-alert</v-icon>
        Database Setup Required
      </v-alert-title>
      <div>
        The database is not configured. Please complete the setup process to use all features.
      </div>
      <v-btn color="white" variant="outlined" class="mt-3" @click="navigateToSetup">
        <v-icon left>mdi-cog</v-icon>
        Go to Setup Wizard
      </v-btn>
    </v-alert>

    <!-- LAN Setup Complete Banner -->
    <v-alert
      v-if="showLanWelcome"
      type="success"
      prominent
      closable
      class="mb-4"
      @click:close="dismissLanWelcome"
    >
      <v-alert-title class="text-h6">
        <v-icon left>mdi-check-circle</v-icon>
        Application Now Configured for LAN Access
      </v-alert-title>
      <div class="mb-3">
        <p class="mb-2">
          <strong>Congratulations!</strong> GiljoAI MCP is now accessible over your local network.
        </p>
        <p class="mb-2">
          <strong>Server URL:</strong> <code>http://{{ serverIp }}:{{ serverPort }}</code>
        </p>
        <p class="text-body-2">
          Download the comprehensive setup and testing guide to verify network connectivity and
          troubleshoot any issues.
        </p>
      </div>
      <v-btn color="white" variant="outlined" @click="downloadLanGuide">
        <v-icon left>mdi-download</v-icon>
        Download LAN Setup & Testing Guide
      </v-btn>
    </v-alert>

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
            <v-img
              :src="
                theme.global.current.value.dark
                  ? '/icons/Giljo_YW_Face.svg'
                  : '/icons/Giljo_BY_Face.svg'
              "
              alt="Active Agents"
              width="48"
              height="48"
              class="mx-auto"
            ></v-img>
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
            <AgentMetrics :project-id="selectedProject" :metrics="agentMetrics" />
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
              <v-list-item v-for="activity in recentActivities" :key="activity.id">
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
import { useTheme } from 'vuetify'
import { useRouter } from 'vue-router'
import { useAgentStore } from '@/stores/agents'
import { useProjectStore } from '@/stores/projects'
import { useMessageStore } from '@/stores/messages'
import { useTaskStore } from '@/stores/tasks'
import SubAgentTimelineHorizontal from '@/components/SubAgentTimelineHorizontal.vue'
import SubAgentTree from '@/components/SubAgentTree.vue'
import AgentMetrics from '@/components/AgentMetrics.vue'
import { formatDistanceToNow } from 'date-fns'
import websocketService from '@/services/websocket'
import api from '@/services/api'
import setupService from '@/services/setupService'

const theme = useTheme()
const router = useRouter()

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
const setupStatus = ref({
  setup_mode: false,
  setup_complete: true,
  database_configured: true,
  database_connected: true,
  requires_setup: false,
})
const showLanWelcome = ref(false)
const serverIp = ref('localhost')
const serverPort = ref(7272)

// Stats
const stats = computed(() => ({
  projects: projectStore.projects?.length || 0,
  activeAgents: agentStore.activeAgents?.length || 0,
  messages: messageStore.messages?.length || 0,
  tasks: taskStore.tasks?.length || 0,
}))

// Recent activities
const recentActivities = computed(() => {
  const activities = []

  // Add agent activities
  agentStore.agentTimeline.slice(0, 5).forEach((event) => {
    activities.push({
      id: event.id,
      type: event.type,
      title: `${event.agent_name} ${event.type}`,
      timestamp: event.timestamp,
    })
  })

  return activities.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 10)
})

// Performance metrics
const performance = ref({
  avgResponseTime: 45,
  successRate: 98.5,
  tokenUsage: 125000,
  activeSessions: 3,
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
    warning: 'warning',
  }
  return colors[type] || 'info'
}

const getActivityIcon = (type) => {
  const icons = {
    spawn: 'mdi-rocket-launch',
    complete: 'mdi-check-circle',
    error: 'mdi-alert-circle',
    warning: 'mdi-alert',
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

const checkSetupStatus = async () => {
  try {
    const status = await setupService.checkStatus()
    setupStatus.value = status
  } catch (error) {
    console.error('Failed to check setup status:', error)
    // If setup check fails, assume setup is not required (avoid blocking UI)
    setupStatus.value.requires_setup = false
  }
}

const dismissSetupBanner = () => {
  // Hide banner temporarily (will reappear on page reload if still needed)
  setupStatus.value.requires_setup = false
}

const navigateToSetup = () => {
  router.push('/setup/database')
}

const refreshData = async () => {
  // Check setup status first
  await checkSetupStatus()

  // Only fetch data if setup is complete
  if (!setupStatus.value.requires_setup) {
    await Promise.all([
      projectStore.fetchProjects(),
      agentStore.fetchAgents(),
      messageStore.fetchMessages(),
      taskStore.fetchTasks(),
    ])

    if (selectedProject.value) {
      await agentStore.fetchAgentTree(selectedProject.value)
      await loadMetrics()
    }
  }
}

// WebSocket handlers
const handleRealtimeUpdate = (data) => {
  // Update stats in real-time
  performance.value.activeSessions = data.activeSessions || performance.value.activeSessions
}

// LAN Welcome Banner
const dismissLanWelcome = () => {
  showLanWelcome.value = false
  localStorage.removeItem('giljo_lan_setup_complete')
}

const downloadLanGuide = () => {
  // Read the guide content from docs/LAN_SETUP_GUIDE.md (already created)
  // Or generate it dynamically with current config values
  const guideContent = generateLanGuide()

  const blob = new Blob([guideContent], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'LAN_SETUP_GUIDE.md'
  link.click()
  URL.revokeObjectURL(url)
}

const generateLanGuide = () => {
  return `# GiljoAI MCP - LAN/Server Mode Setup Guide

**Network Configuration Complete**

This guide helps you verify and troubleshoot network connectivity for GiljoAI MCP in Server/LAN mode.

---

## Your Configuration

**Server URL:** http://${serverIp.value}:${serverPort.value}
**Mode:** Server/LAN
**Status:** Services restarted and ready

---

## Quick Network Tests

### From Another Device on Your Network:

**1. Ping Test (Basic Connectivity)**
\`\`\`bash
ping ${serverIp.value}
\`\`\`
Expected: Reply from ${serverIp.value}

**2. API Health Check**
\`\`\`bash
curl http://${serverIp.value}:${serverPort.value}/health
\`\`\`
Expected: {"status": "ok"}

**3. Browser Access**
Open: http://${serverIp.value}:7274

---

## Troubleshooting

**If ping works but API doesn't:**
- Verify firewall allows port ${serverPort.value}
- Check API server is running
- Confirm services restarted after configuration

**If nothing works:**
- Both devices must be on same network
- Check router's AP Isolation is disabled
- Verify firewall on both server and client

---

For complete troubleshooting guide, see: docs/LAN_SETUP_GUIDE.md

**Generated:** ${new Date().toLocaleString()}
`
}

// Lifecycle
onMounted(async () => {
  // Check for LAN setup completion flag
  const lanSetupComplete = localStorage.getItem('giljo_lan_setup_complete')
  if (lanSetupComplete === 'true') {
    showLanWelcome.value = true

    // Fetch server IP and port from config
    try {
      const response = await fetch(`${setupService.baseURL}/api/v1/config`)
      if (response.ok) {
        const config = await response.json()
        if (config.server?.ip) {
          serverIp.value = config.server.ip
        }
        if (config.services?.api?.port) {
          serverPort.value = config.services.api.port
        }
      }
    } catch (error) {
      console.warn('[DASHBOARD] Could not fetch server config:', error)
    }
  }

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
