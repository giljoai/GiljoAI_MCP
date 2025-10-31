<template>
  <v-container fluid class="jobs-view pa-6">
    <!-- Loading State -->
    <v-row v-if="loading" class="justify-center py-12">
      <v-col cols="12" class="text-center">
        <v-progress-circular indeterminate color="primary" size="64" />
        <p class="text-subtitle-1 mt-4">Loading active project...</p>
      </v-col>
    </v-row>

    <!-- Error State -->
    <v-row v-else-if="error" class="mb-4">
      <v-col cols="12">
        <v-alert type="error" variant="tonal" prominent>
          <v-icon start size="large">mdi-alert-circle</v-icon>
          <div>
            <p class="font-weight-bold">Error Loading Active Project</p>
            <p class="text-body-2">{{ error }}</p>
          </div>
          <template v-slot:actions>
            <v-btn variant="text" @click="fetchActiveProject">
              Retry
            </v-btn>
          </template>
        </v-alert>
      </v-col>
    </v-row>

    <!-- No Active Project State -->
    <v-row v-else-if="!activeProject" class="justify-center py-12">
      <v-col cols="12" md="8" lg="6" class="text-center">
        <v-img
          :src="theme.global.current.value.dark ? '/icons/Giljo_YW_Face.svg' : '/icons/Giljo_BY_Face.svg'"
          alt="GiljoAI"
          width="120"
          height="120"
          class="mx-auto mb-6"
          style="opacity: 0.4"
        />
        <h2 class="text-h4 font-weight-bold mb-4">No Active Project</h2>
        <p class="text-subtitle-1 text-medium-emphasis mb-6">
          You don't have an active project yet. Activate a project to start tracking agent jobs.
        </p>
        <v-btn
          color="primary"
          size="large"
          prepend-icon="mdi-folder-multiple"
          :to="{ name: 'Projects' }"
        >
          View Projects
        </v-btn>
      </v-col>
    </v-row>

    <!-- Active Project - Dual-Tab Interface (Handover 0077) -->
    <v-row v-else>
      <v-col cols="12">
        <!-- Project Header -->
        <div class="mb-4">
          <div class="d-flex align-center gap-2 mb-2">
            <h1 class="text-h4">Project:</h1>
            <h2 class="project-name">{{ activeProject.name }}</h2>
          </div>
          <p class="text-subtitle-1 text-medium-emphasis">
            Project ID: {{ activeProject.id }}
          </p>
        </div>

        <!-- ProjectTabs Component (Handover 0077) -->
        <ProjectTabs
          :project="activeProject"
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { api } from '@/services/api'
import ProjectTabs from '@/components/projects/ProjectTabs.vue'

/**
 * JobsView Component (Handover 0077 - Hybrid Architecture)
 *
 * Single global /jobs route that:
 * - Automatically loads the active project (leveraging Handover 0050b)
 * - Shows ProjectTabs dual-tab interface (Launch | Jobs)
 * - Displays empty state if no active project exists
 *
 * Benefits:
 * - Clean semantic URL (/jobs = current work)
 * - Leverages Single Active Project constraint
 * - Jobs nav button routes here
 * - Historical projects still accessible via /projects/:id/launch
 */

const router = useRouter()
const theme = useTheme()

// State
const activeProject = ref(null)
const loading = ref(true)
const error = ref(null)

// Toast notification state
const showToast = ref(false)
const toastMessage = ref('')
const toastColor = ref('success')
const toastIcon = ref('mdi-check-circle')

/**
 * Fetch the currently active project
 */
async function fetchActiveProject() {
  loading.value = true
  error.value = null

  try {
    const response = await api.projects.getActive()
    activeProject.value = response.data

    if (activeProject.value) {
      console.log('[JobsView] Active project loaded:', activeProject.value.name)
    } else {
      console.log('[JobsView] No active project found')
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to load active project'
    console.error('[JobsView] Error loading active project:', err)
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
  console.log('[JobsView] Edit mission:', missionData)
}

/**
 * Handle agent mission editing (triggered from ProjectTabs)
 */
function handleEditAgentMission(agentData) {
  showNotification('Agent mission editing coming soon', 'info', 'mdi-information')
  console.log('[JobsView] Edit agent mission:', agentData)
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
 * Lifecycle hooks
 */
onMounted(() => {
  console.log('[JobsView] Component mounted')
  fetchActiveProject()
})
</script>

<style scoped>
/* Project name styling */
.project-name {
  color: #FFC300;
  font-size: 2.125rem;
  font-weight: 400;
}

/* Container padding */
.jobs-view {
  min-height: calc(100vh - 64px);
}

/* Empty state styling */
.text-center v-img {
  filter: grayscale(0.5);
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .jobs-view {
    padding: 1rem;
  }

  h1.text-h3 {
    font-size: 1.5rem !important;
  }

  h2.text-h4 {
    font-size: 1.25rem !important;
  }
}
</style>
