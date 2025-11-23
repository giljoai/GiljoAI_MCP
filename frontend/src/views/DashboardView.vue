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

    <!-- Agent Monitoring Section (Dashboard Agent Monitoring UI) -->
    <v-row class="mt-6">
      <v-col cols="12">
        <AgentMonitoring />
      </v-col>
    </v-row>

    <!-- Historical Projects Section (Handover 0077 - Dashboard Integration) -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card elevation="2">
          <v-card-title class="d-flex align-center justify-space-between">
            <div>
              <v-icon left color="primary">mdi-history</v-icon>
              Historical Projects
            </div>
            <v-chip color="info" size="small" variant="outlined"> Coming Soon </v-chip>
          </v-card-title>

          <v-card-subtitle class="text-medium-emphasis mt-2">
            View completed, cancelled, and archived projects with full job history and agent
            interactions
          </v-card-subtitle>

          <v-divider class="my-4" />

          <!-- Placeholder: Filters & Search -->
          <v-card-text>
            <v-row dense class="mb-4">
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="historicalProjectsSearch"
                  prepend-inner-icon="mdi-magnify"
                  label="Search projects..."
                  variant="outlined"
                  density="compact"
                  disabled
                  hint="Search by name, description, or ID"
                  persistent-hint
                />
              </v-col>
              <v-col cols="12" md="3">
                <v-select
                  v-model="historicalProjectsStatus"
                  :items="projectStatusOptions"
                  label="Filter by status"
                  variant="outlined"
                  density="compact"
                  disabled
                  hint="Filter completed, cancelled, etc."
                  persistent-hint
                />
              </v-col>
              <v-col cols="12" md="3">
                <v-select
                  v-model="historicalProjectsDateRange"
                  :items="dateRangeOptions"
                  label="Date range"
                  variant="outlined"
                  density="compact"
                  disabled
                  hint="Last 7 days, 30 days, etc."
                  persistent-hint
                />
              </v-col>
              <v-col cols="12" md="2" class="d-flex align-center">
                <v-btn color="primary" variant="outlined" block disabled>
                  <v-icon left>mdi-filter</v-icon>
                  Apply Filters
                </v-btn>
              </v-col>
            </v-row>

            <!-- Placeholder: Historical Project Cards -->
            <v-row v-if="historicalProjects.length === 0">
              <v-col cols="12">
                <v-alert type="info" variant="tonal" prominent class="text-center">
                  <v-icon size="64" class="mb-4">mdi-folder-open-outline</v-icon>
                  <div class="text-h6 mb-2">No Historical Projects Yet</div>
                  <div class="text-body-2">
                    Complete your first project to see historical data here. You'll be able to:
                  </div>
                  <v-list density="compact" class="bg-transparent mt-4">
                    <v-list-item>
                      <template v-slot:prepend>
                        <v-icon color="primary">mdi-chart-timeline-variant</v-icon>
                      </template>
                      <v-list-item-title
                        >View full project timeline and agent activity</v-list-item-title
                      >
                    </v-list-item>
                    <v-list-item>
                      <template v-slot:prepend>
                        <v-icon color="primary">mdi-message-text</v-icon>
                      </template>
                      <v-list-item-title
                        >Review all agent messages and communications</v-list-item-title
                      >
                    </v-list-item>
                    <v-list-item>
                      <template v-slot:prepend>
                        <v-icon color="primary">mdi-chart-bar</v-icon>
                      </template>
                      <v-list-item-title
                        >Analyze token usage and performance metrics</v-list-item-title
                      >
                    </v-list-item>
                    <v-list-item>
                      <template v-slot:prepend>
                        <v-icon color="primary">mdi-file-document-multiple</v-icon>
                      </template>
                      <v-list-item-title>Export project summaries and reports</v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-alert>
              </v-col>
            </v-row>

            <!-- Placeholder: Project Cards Grid (commented out - for future implementation) -->
            <!--
            <v-row v-else>
              <v-col
                v-for="project in historicalProjects"
                :key="project.id"
                cols="12"
                md="6"
                lg="4"
              >
                <v-card elevation="1" hover>
                  <v-card-title class="d-flex align-center justify-space-between">
                    <span class="text-truncate">{{ project.name }}</span>
                    <v-chip
                      :color="getProjectStatusColor(project.status)"
                      size="small"
                      label
                    >
                      {{ project.status }}
                    </v-chip>
                  </v-card-title>

                  <v-card-subtitle class="text-caption">
                    {{ formatProjectDate(project) }}
                  </v-card-subtitle>

                  <v-divider />

                  <v-card-text>
                    <v-row dense>
                      <v-col cols="6">
                        <div class="text-caption text-medium-emphasis">Agents</div>
                        <div class="text-body-2 font-weight-bold">
                          <v-icon size="small" color="primary">mdi-account-multiple</v-icon>
                          {{ project.agent_count }}
                        </div>
                      </v-col>
                      <v-col cols="6">
                        <div class="text-caption text-medium-emphasis">Messages</div>
                        <div class="text-body-2 font-weight-bold">
                          <v-icon size="small" color="warning">mdi-message-text</v-icon>
                          {{ project.message_count }}
                        </div>
                      </v-col>
                      <v-col cols="6">
                        <div class="text-caption text-medium-emphasis">Duration</div>
                        <div class="text-body-2 font-weight-bold">
                          <v-icon size="small" color="info">mdi-clock-outline</v-icon>
                          {{ formatDuration(project) }}
                        </div>
                      </v-col>
                      <v-col cols="6">
                        <div class="text-caption text-medium-emphasis">Tokens</div>
                        <div class="text-body-2 font-weight-bold">
                          <v-icon size="small" color="success">mdi-alpha-t-circle</v-icon>
                          {{ formatTokens(project.context_used) }}
                        </div>
                      </v-col>
                    </v-row>

                    <v-divider class="my-3" />

                    <div class="text-caption text-medium-emphasis mb-2">Quick Stats:</div>
                    <v-chip-group>
                      <v-chip size="x-small" variant="outlined">
                        <v-icon left size="x-small">mdi-check-circle</v-icon>
                        {{ project.completed_tasks }} tasks
                      </v-chip>
                      <v-chip size="x-small" variant="outlined">
                        <v-icon left size="x-small">mdi-clock</v-icon>
                        {{ project.avg_response_time }}ms avg
                      </v-chip>
                    </v-chip-group>
                  </v-card-text>

                  <v-card-actions>
                    <v-btn
                      color="primary"
                      variant="outlined"
                      block
                      :to="`/projects/${project.id}/launch?readonly=true`"
                    >
                      <v-icon left>mdi-eye</v-icon>
                      View Full Details
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-col>
            </v-row>
            -->

            <!-- Pagination (placeholder for future) -->
            <!--
            <v-row v-if="historicalProjects.length > 0" class="mt-4">
              <v-col cols="12" class="d-flex justify-center">
                <v-pagination
                  v-model="historicalProjectsPage"
                  :length="historicalProjectsTotalPages"
                  :total-visible="7"
                  disabled
                />
              </v-col>
            </v-row>
            -->
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import AppAlert from '@/components/ui/AppAlert.vue'
import AgentMonitoring from '@/components/dashboard/AgentMonitoring.vue'
import { useTheme } from 'vuetify'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projects'
import { useTaskStore } from '@/stores/tasks'

import { formatDistanceToNow } from 'date-fns'
import { useWebSocketStore } from '@/stores/websocket'
import api from '@/services/api'
import setupService from '@/services/setupService'

const theme = useTheme()
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
    const response = await api.get('/api/v1/stats/call-counts')
    if (response.data) {
      apiCallCount.value = response.data.total_api_calls
      mcpCallCount.value = response.data.total_mcp_calls
    }
  } catch (error) {
    console.error('Failed to fetch call counts:', error)
  }
}

// Historical Projects (Handover 0077 - Dashboard Integration)
// Placeholder state - will be populated when project completion workflow is fully tested
const historicalProjects = ref([])
const historicalProjectsSearch = ref('')
const historicalProjectsStatus = ref('all')
const historicalProjectsDateRange = ref('all')
const historicalProjectsPage = ref(1)
const historicalProjectsTotalPages = ref(1)

// Filter options for historical projects
const projectStatusOptions = [
  { title: 'All Statuses', value: 'all' },
  { title: 'Completed', value: 'completed' },
  { title: 'Cancelled', value: 'cancelled' },
  { title: 'Archived', value: 'archived' },
]

const dateRangeOptions = [
  { title: 'All Time', value: 'all' },
  { title: 'Last 7 Days', value: '7d' },
  { title: 'Last 30 Days', value: '30d' },
  { title: 'Last 3 Months', value: '3m' },
  { title: 'Last Year', value: '1y' },
]

/**
 * Fetch historical projects from the backend
 *
 * FUTURE IMPLEMENTATION NOTES:
 * ============================
 *
 * 1. API Endpoint to create (or enhance existing):
 *    GET /api/v1/projects/historical
 *    Query params: status, search, date_range, page, limit
 *
 * 2. Response should include:
 *    - id, name, description, status
 *    - created_at, completed_at, cancelled_at
 *    - agent_count, message_count, context_used
 *    - duration (calculated from created_at to completed_at)
 *    - project_summary (from closeout process)
 *    - performance_metrics (avg_response_time, success_rate, etc.)
 *
 * 3. Frontend filtering:
 *    - Search by project name, description, or ID
 *    - Filter by status (completed, cancelled, archived)
 *    - Filter by date range (last 7 days, 30 days, etc.)
 *    - Pagination (10-20 projects per page)
 *
 * 4. Each project card should show:
 *    - Project name + status badge
 *    - Completion/cancellation date
 *    - Agent count, message count
 *    - Token usage (context_used)
 *    - Duration (time from start to completion)
 *    - Quick stats (tasks completed, avg response time)
 *    - "View Full Details" button → /projects/{id}/launch?readonly=true
 *
 * 5. The readonly project view should display:
 *    - Full Launch Tab (mission, agent cards) - view only
 *    - Full Jobs Tab (agent cards, message stream) - view only
 *    - All data preserved as it was during the project
 *    - Timeline of agent activity
 *    - Exportable project summary
 *
 * 6. Additional features to consider:
 *    - Export project data (JSON, PDF summary)
 *    - Compare multiple projects (side-by-side analysis)
 *    - Agent performance analytics across projects
 *    - Token usage trends and optimization suggestions
 *    - Search within project messages
 *
 * 7. Database considerations:
 *    - Projects with status='completed' or 'cancelled' are historical
 *    - Preserve all agent records, messages, and metadata
 *    - Optional: Archive old projects to separate table after 6-12 months
 *    - Implement soft delete (deleted_at) for user cleanup
 *
 * 8. Performance optimization:
 *    - Lazy load project details (summary on card, full data on click)
 *    - Paginate results (don't load all historical projects at once)
 *    - Cache frequently accessed projects
 *    - Consider separate historical_projects view in database
 */
async function fetchHistoricalProjects() {
  // PLACEHOLDER: Uncomment when ready to implement
  /*
  try {
    const response = await api.projects.list({
      status: historicalProjectsStatus.value === 'all' ? undefined : historicalProjectsStatus.value,
      search: historicalProjectsSearch.value || undefined,
      date_range: historicalProjectsDateRange.value === 'all' ? undefined : historicalProjectsDateRange.value,
      page: historicalProjectsPage.value,
      limit: 12,
      // Only fetch completed/cancelled projects
      historical: true,
    })

    historicalProjects.value = response.data.projects || []
    historicalProjectsTotalPages.value = Math.ceil(response.data.total / 12)
  } catch (error) {
    console.error('[Dashboard] Failed to fetch historical projects:', error)
    historicalProjects.value = []
  }
  */

  // For now, keep empty array until project completion workflow is tested
  historicalProjects.value = []
  console.log(
    '[Dashboard] Historical Projects placeholder - awaiting implementation after job testing',
  )
}

// Methods

const formatTokens = (tokens) => {
  if (tokens > 1000000) {
    return `${(tokens / 1000000).toFixed(1)}M`
  }
  if (tokens > 1000) {
    return `${(tokens / 1000).toFixed(1)}K`
  }
  return tokens.toString()
}

// Helper functions for Historical Projects (for future use)
const getProjectStatusColor = (status) => {
  const colors = {
    completed: 'success',
    cancelled: 'warning',
    archived: 'grey',
    failed: 'error',
  }
  return colors[status] || 'info'
}

const formatProjectDate = (project) => {
  if (project.completed_at) {
    return `Completed ${formatDistanceToNow(new Date(project.completed_at), { addSuffix: true })}`
  }
  if (project.cancelled_at) {
    return `Cancelled ${formatDistanceToNow(new Date(project.cancelled_at), { addSuffix: true })}`
  }
  return `Created ${formatDistanceToNow(new Date(project.created_at), { addSuffix: true })}`
}

const formatDuration = (project) => {
  if (!project.completed_at && !project.cancelled_at) {
    return 'In progress'
  }

  const endDate = new Date(project.completed_at || project.cancelled_at)
  const startDate = new Date(project.created_at)
  const durationMs = endDate - startDate

  const hours = Math.floor(durationMs / (1000 * 60 * 60))
  const minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60))

  if (hours > 24) {
    const days = Math.floor(hours / 24)
    return `${days}d ${hours % 24}h`
  }

  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }

  return `${minutes}m`
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
      api.get('/api/v1/stats/system').then((response) => {
        systemStats.value = response.data
      }),
    ])
  }
}

// WebSocket handlers
const handleRealtimeUpdate = (data) => {
  // Update stats in real-time if needed
  console.log('WebSocket update:', data)
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

  // Fetch call counts and set up interval
  fetchCallCounts()
  fetchInterval = setInterval(fetchCallCounts, 5000)

  // Set up WebSocket listeners for real-time updates
  const wsStore = useWebSocketStore()
  const unsubscribe = wsStore.on('stats:update', handleRealtimeUpdate)

  onUnmounted(() => {
    unsubscribe()
    if (fetchInterval) {
      clearInterval(fetchInterval)
    }
  })
})
</script>
