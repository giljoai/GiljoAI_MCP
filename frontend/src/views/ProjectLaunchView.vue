<template>
  <v-container fluid class="pa-6">
    <!-- Header Section (matches JobsView) -->
    <v-row class="mb-4" v-if="!loading && !error">
      <v-col cols="12">
        <div class="mb-4">
          <div class="d-flex align-center gap-2 mb-2">
            <h1 class="text-h4">Project:</h1>
            <h2 class="project-name">{{ project?.name || 'Loading...' }}</h2>
          </div>
          <p class="text-subtitle-1 text-medium-emphasis">
            Project ID: {{ project?.id || 'N/A' }}
          </p>
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

    <!-- PROJECT TABS COMPONENT (same as JobsView) -->
    <v-row v-else>
      <v-col cols="12">
        <ProjectTabs
          :project="project"
          :orchestrator="orchestrator"
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
import { useRoute } from 'vue-router'
import { api } from '@/services/api'
import ProjectTabs from '@/components/projects/ProjectTabs.vue'

const route = useRoute()
const projectId = ref(route.params.projectId)
const project = ref(null)
const orchestrator = ref(null)
const loading = ref(true)
const error = ref(null)

const showToast = ref(false)
const toastMessage = ref('')
const toastColor = ref('success')
const toastIcon = ref('mdi-check-circle')

async function fetchProjectDetails() {
  loading.value = true
  error.value = null
  try {
    // Fetch project and orchestrator in parallel
    const [projectResponse, orchestratorResponse] = await Promise.all([
      api.projects.get(projectId.value),
      api.projects.getOrchestrator(projectId.value)
    ])
    
    project.value = projectResponse.data
    orchestrator.value = orchestratorResponse.data.orchestrator
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to load project'
  } finally {
    loading.value = false
  }
}

function handleEditDescription() {
  showNotification('Description editing coming soon', 'info', 'mdi-information')
}

function handleEditMission(missionData) {
  showNotification('Mission editing coming soon', 'info', 'mdi-information')
}

function handleEditAgentMission(agentData) {
  showNotification('Agent mission editing coming soon', 'info', 'mdi-information')
}

function showNotification(message, color = 'success', icon = 'mdi-check-circle') {
  toastMessage.value = message
  toastColor.value = color
  toastIcon.value = icon
  showToast.value = true
}

onMounted(() => {
  fetchProjectDetails()
})
</script>

<style scoped>
/* Project name styling (matches JobsView) */
.project-name {
  color: #FFC300;
  font-size: 2.125rem;
  font-weight: 400;
}

@media (max-width: 600px) {
  h1.text-h4 {
    font-size: 1.5rem !important;
  }
}
</style>
