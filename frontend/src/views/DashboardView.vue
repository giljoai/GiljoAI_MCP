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
        <h1 class="text-h4 mb-2">Dashboard</h1>
      </v-col>
    </v-row>

    <!-- Product Selector -->
    <ProductSelector
      :products="productStore.products"
      :selected-product-id="selectedProductId"
      class="mb-4"
      @select="onProductSelect"
    />

    <!-- Stats -->
    <v-card variant="flat" class="mb-4 pa-4 stats-wrapper">
      <!-- Projects -->
      <div class="text-caption text-medium-emphasis mb-2">Projects</div>
      <div class="stats-grid mb-4">
        <v-card v-for="s in projectStatCards" :key="s.label" variant="outlined" class="stat-card">
          <div class="stat-card-inner">
            <div class="stat-icon-box">
              <v-icon size="20" color="yellow-darken-2">{{ s.icon }}</v-icon>
            </div>
            <span class="stat-label">{{ s.label }}</span>
            <span class="stat-value">{{ s.value }}</span>
          </div>
        </v-card>
      </div>

      <!-- Tasks -->
      <div class="text-caption text-medium-emphasis mb-2">Tasks</div>
      <div class="stats-grid mb-4">
        <v-card v-for="s in taskStatCards" :key="s.label" variant="outlined" class="stat-card">
          <div class="stat-card-inner">
            <div class="stat-icon-box">
              <v-icon size="20" color="yellow-darken-2">{{ s.icon }}</v-icon>
            </div>
            <span class="stat-label">{{ s.label }}</span>
            <span class="stat-value">{{ s.value }}</span>
          </div>
        </v-card>
      </div>

      <!-- Server (always global) -->
      <div class="text-caption text-medium-emphasis mb-2">Server</div>
      <div class="stats-grid">
        <v-card v-for="s in serverStatCards" :key="s.label" variant="outlined" class="stat-card">
          <div class="stat-card-inner">
            <div class="stat-icon-box">
              <img v-if="s.img" :src="s.img" :alt="s.label" class="stat-custom-icon" />
              <v-icon v-else size="20" color="yellow-darken-2">{{ s.icon }}</v-icon>
            </div>
            <span class="stat-label">{{ s.label }}</span>
            <span class="stat-value">{{ s.value }}</span>
          </div>
        </v-card>
      </div>
    </v-card>

    <!-- Donut Charts -->
    <v-row class="mb-4">
      <v-col cols="12" md="4">
        <v-card variant="flat" class="chart-card pa-4">
          <DonutChart
            title="Status Distribution"
            :chart-data="statusChartData"
          />
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="flat" class="chart-card pa-4">
          <DonutChart
            title="Taxonomy Distribution"
            :chart-data="taxonomyChartData"
          />
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="flat" class="chart-card pa-4">
          <DonutChart
            title="Agent Role Distribution"
            :chart-data="agentRoleChartData"
          />
        </v-card>
      </v-col>
    </v-row>

    <!-- Recent Activity Lists -->
    <v-row>
      <v-col cols="12" md="6">
        <v-card variant="flat" class="activity-card pa-4">
          <div class="text-caption text-medium-emphasis mb-2">Recent Projects</div>
          <RecentProjectsList :projects="dashboardData.recent_projects" />
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card variant="flat" class="activity-card pa-4">
          <div class="text-caption text-medium-emphasis mb-2">Recent 360 Memories</div>
          <RecentMemoriesList :memories="dashboardData.recent_memories" />
        </v-card>
      </v-col>
    </v-row>

  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import AppAlert from '@/components/ui/AppAlert.vue'
import ProductSelector from '@/components/dashboard/ProductSelector.vue'
import DonutChart from '@/components/dashboard/DonutChart.vue'
import RecentProjectsList from '@/components/dashboard/RecentProjectsList.vue'
import RecentMemoriesList from '@/components/dashboard/RecentMemoriesList.vue'
import { useRouter } from 'vue-router'
import { useProductStore } from '@/stores/products'

import api from '@/services/api'
import setupService from '@/services/setupService'

const router = useRouter()

// Stores
const productStore = useProductStore()

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

// Product selection
const selectedProductId = ref(null)

// Dashboard data from consolidated endpoint
const dashboardData = ref({
  project_status_dist: {},
  taxonomy_dist: [],
  agent_role_dist: {},
  recent_projects: [],
  recent_memories: [],
  task_status_dist: {},
})

// Server stats (always global)
const apiCallCount = ref(0)
const mcpCallCount = ref(0)
const agentsSpawned = ref(0)

// Status chart colors
const statusColors = {
  active: '#4caf50',
  inactive: '#9e9e9e',
  completed: '#2196f3',
  cancelled: '#ff9800',
  terminated: '#f44336',
  staged: '#ffc107',
}

// Agent role colors
const agentRoleColors = {
  orchestrator: '#FFD700',
  implementer: '#4caf50',
  tester: '#2196f3',
  analyzer: '#9c27b0',
  documenter: '#ff9800',
  reviewer: '#00bcd4',
}

// Fallback palette for unknown roles
const fallbackColors = ['#e91e63', '#795548', '#607d8b', '#8bc34a', '#ff5722', '#3f51b5']

// Computed stat cards
const projectStatCards = computed(() => {
  const dist = dashboardData.value.project_status_dist || {}
  const total = Object.values(dist).reduce((a, b) => a + b, 0)
  return [
    { icon: 'mdi-folder-open-outline', label: 'Projects', value: total },
    { icon: 'mdi-play-circle-outline', label: 'Active', value: dist.active || 0 },
    { icon: 'mdi-pause-circle-outline', label: 'Inactive', value: dist.inactive || 0 },
    { icon: 'mdi-rocket-launch-outline', label: 'Staged', value: dist.staged || 0 },
    { icon: 'mdi-check-circle-outline', label: 'Finished', value: dist.completed || 0 },
    { icon: 'mdi-close-circle-outline', label: 'Cancelled', value: dist.cancelled || 0 },
    { icon: 'mdi-stop-circle-outline', label: 'Terminated', value: dist.terminated || 0 },
  ]
})

const taskStatCards = computed(() => {
  const dist = dashboardData.value.task_status_dist || {}
  const total = Object.values(dist).reduce((a, b) => a + b, 0)
  return [
    { icon: 'mdi-clipboard-text-outline', label: 'Tasks', value: total },
    { icon: 'mdi-clipboard-clock-outline', label: 'Open', value: dist.open || 0 },
    { icon: 'mdi-clipboard-check-outline', label: 'Completed', value: dist.completed || 0 },
    { icon: 'mdi-clipboard-play-outline', label: 'In Progress', value: dist.in_progress || 0 },
    { icon: 'mdi-clipboard-remove-outline', label: 'Blocked', value: dist.blocked || 0 },
  ]
})

const serverStatCards = computed(() => [
  { icon: 'mdi-swap-horizontal', label: 'API Calls', value: apiCallCount.value },
  { img: '/logo-mcp.svg', label: 'MCP Calls', value: mcpCallCount.value },
  { img: '/giljo_YW_Face.svg', label: 'Agents Spawned', value: agentsSpawned.value },
])

// Chart data computed properties
const statusChartData = computed(() => {
  const dist = dashboardData.value.project_status_dist || {}
  const labels = []
  const values = []
  const colors = []

  for (const [status, count] of Object.entries(dist)) {
    if (count > 0) {
      labels.push(status.charAt(0).toUpperCase() + status.slice(1))
      values.push(count)
      colors.push(statusColors[status] || '#9e9e9e')
    }
  }

  return { labels, values, colors }
})

const taxonomyChartData = computed(() => {
  const dist = dashboardData.value.taxonomy_dist || []
  const labels = []
  const values = []
  const colors = []

  for (const item of dist) {
    if (item.count > 0) {
      labels.push(item.label || 'Untyped')
      values.push(item.count)
      colors.push(item.color || '#9e9e9e')
    }
  }

  return { labels, values, colors }
})

const agentRoleChartData = computed(() => {
  const dist = dashboardData.value.agent_role_dist || {}
  const labels = []
  const values = []
  const colors = []
  let fallbackIdx = 0

  for (const [role, count] of Object.entries(dist)) {
    if (count > 0) {
      labels.push(role.charAt(0).toUpperCase() + role.slice(1))
      values.push(count)
      const knownColor = agentRoleColors[role.toLowerCase()]
      if (knownColor) {
        colors.push(knownColor)
      } else {
        colors.push(fallbackColors[fallbackIdx % fallbackColors.length])
        fallbackIdx++
      }
    }
  }

  return { labels, values, colors }
})

// Data fetching
const fetchDashboardData = async () => {
  try {
    const response = await api.stats.getDashboard(selectedProductId.value)
    if (response.data) {
      dashboardData.value = {
        project_status_dist: response.data.project_status_dist || {},
        taxonomy_dist: response.data.taxonomy_dist || [],
        agent_role_dist: response.data.agent_role_dist || {},
        recent_projects: response.data.recent_projects || [],
        recent_memories: response.data.recent_memories || [],
        task_status_dist: response.data.task_status_dist || {},
      }
    }
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  }
}

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

const fetchSystemStats = async () => {
  try {
    const response = await api.stats.getSystem()
    if (response.data) {
      agentsSpawned.value = response.data.total_agents_spawned || 0
    }
  } catch (error) {
    console.error('Failed to fetch system stats:', error)
  }
}

const onProductSelect = (productId) => {
  selectedProductId.value = productId
}

// Watch product selection to refetch dashboard data
watch(selectedProductId, fetchDashboardData, { immediate: true })

let fetchInterval = null

const checkSetupStatus = async () => {
  try {
    const status = await setupService.checkStatus()
    setupStatus.value = status
  } catch (error) {
    console.error('Failed to check setup status:', error)
    setupStatus.value.requires_setup = false
  }
}

const dismissSetupBanner = () => {
  setupStatus.value.requires_setup = false
}

const navigateToSetup = () => {
  router.push('/setup/database')
}

// LAN Welcome Banner
const dismissLanWelcome = () => {
  showLanWelcome.value = false
  localStorage.removeItem('giljo_lan_setup_complete')
}

const downloadLanGuide = () => {
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

  await checkSetupStatus()

  if (!setupStatus.value.requires_setup) {
    // Fetch products for selector
    await productStore.fetchProducts()

    // Fetch server-level stats (always global)
    await Promise.all([
      fetchCallCounts(),
      fetchSystemStats(),
    ])
  }

  // Set up periodic refresh for server stats
  fetchInterval = setInterval(() => {
    fetchCallCounts()
    fetchSystemStats()
  }, 5000)

  onUnmounted(() => {
    if (fetchInterval) {
      clearInterval(fetchInterval)
    }
  })
})
</script>

<style scoped>
.stats-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.stats-wrapper {
  background: #0d1117 !important;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px !important;
}

.stat-card {
  flex: 0 0 auto;
  border-radius: 8px !important;
  background: #161b22 !important;
  border-color: rgba(255, 255, 255, 0.1) !important;
}

.stat-card-inner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
}

.stat-icon-box {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: rgba(255, 215, 0, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-label {
  font-size: 0.8125rem;
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
}

.stat-value {
  font-size: 1.1rem;
  font-weight: 700;
  color: rgb(255, 215, 0);
  margin-left: auto;
  padding-left: 8px;
}

.stat-custom-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.chart-card {
  background: #0d1117 !important;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px !important;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.activity-card {
  background: #0d1117 !important;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px !important;
}
</style>
