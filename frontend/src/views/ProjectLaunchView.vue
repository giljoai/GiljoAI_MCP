<template>
  <v-container fluid class="pa-6">
    <!-- Header Section -->
    <v-row class="mb-6">
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between">
          <div>
            <v-btn
              icon
              variant="text"
              size="small"
              @click="goBack"
              class="mb-2"
              aria-label="Go back"
            >
              <v-icon>mdi-arrow-left</v-icon>
            </v-btn>
            <h1 class="text-h3 font-weight-bold">Project Launch</h1>
            <p class="text-subtitle-1 text-medium-emphasis mt-2">
              {{ project?.name || 'Loading...' }}
            </p>
          </div>
          <v-card variant="tonal" color="info" class="pa-4" max-width="200">
            <p class="text-caption text-medium-emphasis mb-1">Project Status</p>
            <v-chip
              size="small"
              :color="getStatusColor(project?.status)"
              label
            >
              {{ project?.status || 'unknown' }}
            </v-chip>
          </v-card>
        </div>
      </v-col>
    </v-row>

    <!-- Loading State -->
    <v-row v-if="loading" class="justify-center py-12">
      <v-col cols="12" class="text-center">
        <v-progress-circular indeterminate color="primary" size="64" />
        <p class="text-subtitle-1 mt-4">Loading project details...</p>
      </v-col>
    </v-row>

    <!-- Error State -->
    <v-row v-else-if="error" class="mb-4">
      <v-col cols="12">
        <v-alert type="error" variant="tonal" closable @click:close="error = null">
          <v-icon start>mdi-alert-circle</v-icon>
          <div>
            <p class="font-weight-bold">Error Loading Project</p>
            <p class="text-body-2">{{ error }}</p>
          </div>
        </v-alert>
      </v-col>
    </v-row>

    <!-- NEW PROJECT TABS COMPONENT (Handover 0077) -->
    <v-row v-else>
      <v-col cols="12">
        <!-- Readonly Badge (for historical projects) -->
        <v-alert
          v-if="isReadOnly"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-4"
        >
          <v-icon start>mdi-eye</v-icon>
          You are viewing this project in read-only mode (historical view).
        </v-alert>

        <ProjectTabs
          :project="project"
          :readonly="isReadOnly"
          @edit-description="handleEditDescription"
          @edit-mission="handleEditMission"
          @edit-agent-mission="handleEditAgentMission"
        />
      </v-col>
    </v-row>

    <!-- Toast Notifications -->
    <v-snackbar v-model="showToast" :timeout="3000" :color="toastColor">
      <v-icon start :color="toastColor">{{ toastIcon }}</v-icon>
      {{ toastMessage }}
      <template v-slot:actions>
        <v-btn variant="text" @click="showToast = false">
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api'
import ProjectTabs from '@/components/projects/ProjectTabs.vue'

/**
 * ProjectLaunchView Component (Updated for Handover 0077 Hybrid Architecture)
 *
 * Uses the new ProjectTabs component which implements:
 * - Launch Tab: 3-column layout (Orchestrator | Description | Mission) + agent cards
 * - Jobs Tab: 2-column layout (Agent cards 60% | Messages 40%)
 * - Agent visual branding (colors, round chat heads, status badges)
 * - Closeout workflow with completion banner
 *
 * Supports both active and historical project viewing:
 * - Active projects: Full editing capabilities
 * - Historical/inactive projects: Read-only mode (query param ?readonly=true)
 *
 * Replaced old LaunchPanelView + KanbanJobsView components.
 */

const route = useRoute()
const router = useRouter()

// Route parameters
const projectId = ref(route.params.projectId)

// State
const project = ref(null)
const loading = ref(true)
const error = ref(null)

// Readonly mode detection (for historical project viewing from Dashboard)
const isReadOnly = computed(() => {
  // Check query param for explicit readonly flag
  if (route.query.readonly === 'true') {
    return true
  }

  // Check if project is inactive (not active status)
  if (project.value && project.value.status !== 'active') {
    return true
  }

  return false
})

// Toast notification state
const showToast = ref(false)
const toastMessage = ref('')
const toastColor = ref('success')
const toastIcon = ref('mdi-check-circle')

/**
 * Fetch project details on component mount
 */
async function fetchProjectDetails() {
  loading.value = true
  error.value = null

  try {
    const response = await api.projects.get(projectId.value)
    project.value = response.data
    console.log('[ProjectLaunchView] Project loaded:', response.data)
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to load project'
    console.error('[ProjectLaunchView] Error loading project:', err)
  } finally {
    loading.value = false
  }
}

/**
 * Handle description editing (triggered from ProjectTabs)
 */
function handleEditDescription() {
  showNotification('Description editing coming soon', 'info', 'mdi-information')
}

/**
 * Handle mission editing (triggered from ProjectTabs)
 */
function handleEditMission(missionData) {
  showNotification('Mission editing coming soon', 'info', 'mdi-information')
  console.log('[ProjectLaunchView] Edit mission:', missionData)
}

/**
 * Handle agent mission editing (triggered from ProjectTabs)
 */
function handleEditAgentMission(agentData) {
  showNotification('Agent mission editing coming soon', 'info', 'mdi-information')
  console.log('[ProjectLaunchView] Edit agent mission:', agentData)
}

/**
 * Show toast notification
 */
function showNotification(message, color = 'success', icon = 'mdi-check-circle') {
  toastMessage.value = message
  toastColor.value = color
  toastIcon.value = icon
  showToast.value = true
}

/**
 * Navigate back to projects
 */
function goBack() {
  router.push({ name: 'Projects' })
}

/**
 * Get status color for chip
 */
function getStatusColor(status) {
  const colors = {
    active: 'success',
    inactive: 'warning',
    completed: 'info',
    cancelled: 'error',
    deleted: 'grey',
  }
  return colors[status] || 'grey'
}

/**
 * Lifecycle hooks
 */
onMounted(() => {
  console.log('[ProjectLaunchView] Component mounted, projectId:', projectId.value)
  fetchProjectDetails()
})
</script>

<style scoped>
/* Container padding */
.pa-6 {
  padding: 1.5rem;
}

/* Status chip styling */
:deep(.v-chip) {
  text-transform: capitalize;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .pa-6 {
    padding: 1rem;
  }

  h1.text-h3 {
    font-size: 1.5rem !important;
  }
}
</style>
