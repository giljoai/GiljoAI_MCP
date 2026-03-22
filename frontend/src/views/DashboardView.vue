<template>
  <v-container fluid>
    <!-- Setup Banner (shown when database not configured) -->
    <AppAlert
      v-if="setupStatus.requires_setup"
      type="warning"
      prominent
      closable
      class="mb-4"
      @click:close="dismissSetupBanner"
    >
      <template v-slot:title>
        <v-icon left>mdi-database-alert</v-icon>
        Database Setup Required
      </template>
      <div>
        The database is not configured. Please complete the setup process to use all features.
      </div>
      <v-btn color="white" variant="outlined" class="mt-3" @click="navigateToSetup">
        <v-icon left>mdi-cog</v-icon>
        Go to Setup Wizard
      </v-btn>
    </AppAlert>

    <!-- LAN Setup Complete Banner -->
    <AppAlert
      v-if="showLanWelcome"
      type="success"
      prominent
      closable
      class="mb-4"
      @click:close="dismissLanWelcome"
    >
      <template v-slot:title>
        <v-icon left>mdi-check-circle</v-icon>
        Application Now Configured for LAN Access
      </template>
      <div class="mb-3">
        <p class="mb-2">
          <strong>Congratulations!</strong> GiljoAI MCP is now accessible over your local network.
        </p>
        <p class="mb-2">
          <strong>Server URL:</strong> <code>{{ serverProtocol }}://{{ serverIp }}:{{ serverPort }}</code>
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
    </AppAlert>

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
            <v-icon size="48" color="info">mdi-clipboard-check</v-icon>
            <div class="text-h6 mt-2">Tasks</div>
            <div class="text-h4">{{ stats.tasks }}</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card elevation="2">
          <v-card-text class="text-center">
            <v-icon size="48" color="success">mdi-api</v-icon>
            <div class="text-h6 mt-2">API Calls</div>
            <div class="text-h4">{{ apiCallCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card elevation="2">
          <v-card-text class="text-center">
            <v-icon size="48" color="warning">mdi-lan</v-icon>
            <div class="text-h6 mt-2">MCP Calls</div>
            <div class="text-h4">{{ mcpCallCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card elevation="2">
          <v-card-text class="text-center">
            <v-icon size="48" color="purple">mdi-account-multiple</v-icon>
            <div class="text-h6 mt-2">Agents Spawned</div>
            <div class="text-h4">{{ stats.total_agents_spawned }}</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card elevation="2">
          <v-card-text class="text-center">
            <v-icon size="48" color="deep-purple">mdi-check-all</v-icon>
            <div class="text-h6 mt-2">Jobs Done</div>
            <div class="text-h4">{{ stats.total_jobs_completed }}</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card elevation="2">
          <v-card-text class="text-center">
            <v-icon size="48" color="teal">mdi-flag-checkered</v-icon>
            <div class="text-h6 mt-2">Projects Finished</div>
            <div class="text-h4">{{ stats.projects_finished }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import AppAlert from '@/components/ui/AppAlert.vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projects'
import { useTaskStore } from '@/stores/tasks'

import api from '@/services/api'
import setupService from '@/services/setupService'

const router = useRouter()

// Stores
const projectStore = useProjectStore()
const taskStore = useTaskStore()

// Reactive data
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
const serverProtocol = computed(() => window.location.protocol === 'https:' ? 'https' : 'http')

// Stats
const stats = computed(() => ({
  projects: systemStats.value.total_projects || 0,
  tasks: systemStats.value.total_tasks || 0,
  total_agents_spawned: systemStats.value.total_agents_spawned || 0,
  total_jobs_completed: systemStats.value.total_jobs_completed || 0,
  projects_finished: systemStats.value.projects_finished || 0,
}))

const apiCallCount = ref(0)
const mcpCallCount = ref(0)

let fetchInterval = null

const fetchCallCounts = async () => {
  try {
    const response = await api.stats.getCallCounts()
    if (response.data) {
      apiCallCount.value = response.data.total_api_calls
      mcpCallCount.value = response.data.total_mcp_calls
    }
  } catch (error) {
    console.error('Failed to fetch call counts:', error)
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

const systemStats = ref({
  total_projects: 0,
  active_projects: 0,
  completed_projects: 0,
  total_agents: 0,
  active_agents: 0,
  total_messages: 0,
  pending_messages: 0,
  total_tasks: 0,
  completed_tasks: 0,
  average_context_usage: 0,
  peak_context_usage: 0,
  database_size_mb: 0,
  uptime_seconds: 0,
  total_agents_spawned: 0,
  total_jobs_completed: 0,
  projects_finished: 0,
})

const refreshData = async () => {
  // Check setup status first
  await checkSetupStatus()

  // Only fetch data if setup is complete
  if (!setupStatus.value.requires_setup) {
    await Promise.all([
      projectStore.fetchProjects(),
      taskStore.fetchTasks(),
      api.stats.getSystem().then((response) => {
        systemStats.value = response.data
      }),
    ])
  }
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

**Server URL:** ${serverProtocol.value}://${serverIp.value}:${serverPort.value}
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
curl ${serverProtocol.value}://${serverIp.value}:${serverPort.value}/health
\`\`\`
Expected: {"status": "ok"}

**3. Browser Access**
Open: ${serverProtocol.value}://${serverIp.value}:7274

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

  // Fetch call counts and set up interval
  fetchCallCounts()
  fetchInterval = setInterval(fetchCallCounts, 5000)

  onUnmounted(() => {
    if (fetchInterval) {
      clearInterval(fetchInterval)
    }
  })
})
</script>
