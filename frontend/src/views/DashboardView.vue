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
    <v-card variant="flat" class="mb-4 pa-4 stats-wrapper smooth-border">
      <!-- Projects -->
      <div class="text-caption text-medium-emphasis mb-2">Projects</div>
      <div class="stats-grid mb-4">
        <v-card v-for="s in projectStatCards" :key="s.label" variant="flat" class="stat-card smooth-border">
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
        <v-card v-for="s in taskStatCards" :key="s.label" variant="flat" class="stat-card smooth-border">
          <div class="stat-card-inner">
            <div class="stat-icon-box">
              <v-icon size="20" color="yellow-darken-2">{{ s.icon }}</v-icon>
            </div>
            <span class="stat-label">{{ s.label }}</span>
            <span class="stat-value">{{ s.value }}</span>
          </div>
        </v-card>
      </div>

      <!-- Execution Modes -->
      <div class="text-caption text-medium-emphasis mb-2">Execution Modes</div>
      <div class="stats-grid mb-4">
        <v-card v-for="s in executionModeCards" :key="s.label" variant="flat" class="stat-card smooth-border">
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

      <!-- Server (always global) -->
      <div class="text-caption text-medium-emphasis mb-2">Server</div>
      <div class="stats-grid">
        <v-card v-for="s in serverStatCards" :key="s.label" variant="flat" class="stat-card smooth-border">
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
        <v-card variant="flat" class="chart-card smooth-border pa-4">
          <DonutChart
            title="Status Distribution"
            :chart-data="statusChartData"
          />
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="flat" class="chart-card smooth-border pa-4">
          <DonutChart
            title="Taxonomy Distribution"
            :chart-data="taxonomyChartData"
          />
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="flat" class="chart-card smooth-border pa-4">
          <DonutChart
            title="Agent Role Distribution"
            :chart-data="agentRoleChartData"
          />
        </v-card>
      </v-col>
    </v-row>

    <!-- Recent Activity Lists (stacked) -->
    <v-card variant="flat" class="activity-card smooth-border pa-4 mb-4">
      <div class="text-caption text-medium-emphasis mb-2">Recently Completed Projects</div>
      <RecentProjectsList :projects="dashboardData.recent_projects" />
    </v-card>

    <v-card variant="flat" class="activity-card smooth-border pa-4 mb-4">
      <div class="text-caption text-medium-emphasis mb-2">Recent 360 Memories</div>
      <RecentMemoriesList :memories="dashboardData.recent_memories" />
    </v-card>

    <v-card variant="flat" class="activity-card smooth-border pa-4">
      <div class="text-caption text-medium-emphasis mb-2">Recent Git Commits (from 360 Memory)</div>
      <div v-if="recentCommits.length === 0" class="text-caption text-medium-emphasis pa-2">No commits captured in 360 memory yet</div>
      <v-list v-else density="compact" class="bg-transparent recent-list">
        <v-list-item v-for="(c, i) in recentCommits" :key="i" class="px-0">
          <template #prepend>
            <v-icon size="16" color="yellow-darken-2" class="mr-2">mdi-source-commit</v-icon>
          </template>
          <v-list-item-title class="text-body-2">{{ c.message }}</v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            <span style="font-family: monospace; color: var(--color-accent-primary)">{{ c.sha?.substring(0, 8) }}</span>
            <span v-if="c.author" class="mx-2">|</span>
            <span v-if="c.author">{{ c.author }}</span>
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>
    </v-card>

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
  agent_role_dist: [],
  recent_projects: [],
  recent_memories: [],
  task_status_dist: {},
  execution_mode_dist: {},
})

// Server stats (always global)
const apiCallCount = ref(0)
const mcpCallCount = ref(0)
const agentsSpawned = ref(0)
const recentCommits = ref([])

// Status chart colors — harmonized with StatusBadge.vue
const statusColors = {
  active: '#ffffff', /* design-token-exempt: chart color — $color-surface */
  inactive: '#9e9e9e', /* design-token-exempt: chart color — $color-text-muted */
  completed: '#4caf50', /* design-token-exempt: chart color — $color-status-success */
  cancelled: '#c6298c', /* design-token-exempt: chart color — $color-status-failed */
  terminated: '#f44336', /* design-token-exempt: chart color — $color-status-error */
  staged: '#ffc107', /* design-token-exempt: chart color — closest $color-brand-yellow */
}

// Fallback color for agents without a configured background_color
const defaultAgentColor = '#9e9e9e' /* design-token-exempt: chart color — $color-text-muted */

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

const executionModeCards = computed(() => {
  const dist = dashboardData.value.execution_mode_dist || {}
  return [
    { icon: 'mdi-monitor-multiple', label: 'Multi-Terminal', value: dist.multi_terminal || 0 },
    { img: '/claude_pix.svg', label: 'Claude Subagent', value: dist.claude_code_cli || 0 },
    { img: '/codex_logo.svg', label: 'Codex Subagent', value: dist.codex_cli || 0 },
    { img: '/gemini-icon.svg', label: 'Gemini Subagent', value: dist.gemini_cli || 0 },
  ]
})

// Chart data computed properties
const statusChartData = computed(() => {
  const dist = dashboardData.value.project_status_dist || {}
  const labels = []
  const values = []
  const colors = []

  for (const [status, count] of Object.entries(dist)) {
    if (count > 0 && status !== 'deleted') {
      labels.push(status.charAt(0).toUpperCase() + status.slice(1))
      values.push(count)
      colors.push(statusColors[status] || '#9e9e9e') /* design-token-exempt: chart color — $color-text-muted */
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
      colors.push(item.color || '#9e9e9e') /* design-token-exempt: chart color — $color-text-muted */
    }
  }

  return { labels, values, colors }
})

const agentRoleChartData = computed(() => {
  const dist = dashboardData.value.agent_role_dist || []
  const labels = []
  const values = []
  const colors = []
  const allZero = dist.length > 0 && dist.every((item) => !item.count)

  for (const item of dist) {
    labels.push(item.label || 'Unknown')
    // Show equal slices when no agent has been used yet
    values.push(allZero ? 1 : item.count || 0)
    colors.push(item.color || defaultAgentColor)
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
        agent_role_dist: response.data.agent_role_dist || [],
        recent_projects: response.data.recent_projects || [],
        recent_memories: response.data.recent_memories || [],
        task_status_dist: response.data.task_status_dist || {},
        execution_mode_dist: response.data.execution_mode_dist || {},
      }
      // Extract git commits from 360 memory entries
      const commits = []
      for (const mem of (response.data.recent_memories || [])) {
        if (mem.git_commits && Array.isArray(mem.git_commits)) {
          commits.push(...mem.git_commits)
        }
      }
      recentCommits.value = commits.slice(0, 10)
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
})

onUnmounted(() => {
  if (fetchInterval) {
    clearInterval(fetchInterval)
  }
})
</script>

<style scoped lang="scss">
@use '../styles/variables' as *;
@use '../styles/design-tokens' as *;

.stats-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.stats-wrapper {
  background: $color-background-primary !important;
  border-radius: $border-radius-rounded !important;
}

.stat-card {
  flex: 0 0 auto;
  border-radius: $border-radius-default !important;
  background: $elevation-raised !important;
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
  border-radius: $border-radius-default;
  background: transparent;
  border: none !important;
  box-shadow: inset 0 0 0 2px $med-blue;
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
  color: $color-status-waiting;
  margin-left: auto;
  padding-left: 8px;
}

.stat-custom-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.chart-card {
  background: $elevation-raised !important;
  border-radius: $border-radius-rounded !important;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.activity-card {
  background: $elevation-raised !important;
  border-radius: $border-radius-rounded !important;
}
</style>
