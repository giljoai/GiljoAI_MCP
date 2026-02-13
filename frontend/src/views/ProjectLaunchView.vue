<template>
  <div class="project-launch-container">
    <!-- Loading State -->
    <v-container v-if="loading" fluid class="pa-6">
      <v-row class="justify-center py-12">
        <v-col cols="12" class="text-center">
          <v-progress-circular indeterminate color="primary" size="64" />
          <p class="text-subtitle-1 mt-4">Loading project details...</p>
        </v-col>
      </v-row>
    </v-container>

    <!-- Error State -->
    <v-container v-else-if="error" fluid class="pa-6">
      <v-row class="mb-4">
        <v-col cols="12">
          <v-alert type="error" variant="tonal" closable @click:close="error = null">
            <div>
              <p class="font-weight-bold">Error Loading Project</p>
              <p class="text-body-2">{{ error }}</p>
            </div>
          </v-alert>
        </v-col>
      </v-row>
    </v-container>

    <!-- Main Content - ProjectTabs handles its own sticky header -->
    <div v-else class="project-content">
      <ProjectTabs
        :project="project"
        :orchestrator="orchestrator"
        @edit-description="handleEditDescription"
        @edit-mission="handleEditMission"
        @edit-agent-mission="handleEditAgentMission"
      />
    </div>

    <!-- Toast Notifications -->
    <v-snackbar v-model="showToast" :timeout="3000" :color="toastColor">
      <v-icon start :color="toastColor">{{ toastIcon }}</v-icon>
      {{ toastMessage }}
      <template v-slot:actions>
        <v-btn variant="text" @click="showToast = false"> Close </v-btn>
      </template>
    </v-snackbar>

    <!-- Edit Project Dialog -->
    <v-dialog v-model="showEditDialog" max-width="800" persistent>
      <v-card v-draggable>
        <v-card-title class="d-flex align-center">
          <span>Edit Project</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" @click="cancelEdit" />
        </v-card-title>

        <v-card-text>
          <!-- Project ID Info -->
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            <div class="text-caption">
              <strong>Project ID:</strong>
              <span class="ml-2" style="font-family: monospace">{{ project?.id }}</span>
            </div>
          </v-alert>

          <!-- Form -->
          <v-form ref="projectForm" v-model="formValid">
            <v-text-field
              v-model="projectData.name"
              label="Project Name"
              :rules="[(v) => !!v || 'Name is required']"
              required
              class="mb-3"
            ></v-text-field>

            <v-textarea
              v-model="projectData.description"
              label="Project Description"
              :rules="[(v) => !!v || 'Description is required']"
              hint="User-written description of what you want to accomplish"
              persistent-hint
              rows="4"
              required
              class="mb-3"
            ></v-textarea>

            <v-textarea
              v-model="projectData.mission"
              label="Orchestrator Mission (Optional)"
              hint="AI-generated mission created by the orchestrator"
              persistent-hint
              rows="3"
              class="mb-3"
            ></v-textarea>

            <v-text-field
              v-model.number="projectData.context_budget"
              label="Context Budget (tokens)"
              type="number"
              :rules="[(v) => v > 0 || 'Must be positive']"
              class="mb-3"
            ></v-text-field>
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="cancelEdit">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :disabled="!formValid" @click="saveProject">
            Update
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
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

// Edit dialog state
const showEditDialog = ref(false)
const formValid = ref(false)
const projectForm = ref(null)
const projectData = ref({
  name: '',
  description: '',
  mission: '',
  context_budget: 150000,
})

async function fetchProjectDetails() {
  loading.value = true
  error.value = null
  try {
    // Step 1: Fetch project first
    const projectResponse = await api.projects.get(projectId.value)
    project.value = projectResponse.data

    // Step 2: Get/create orchestrator BEFORE listing agent jobs
    // CRITICAL: This must complete (including DB commit) before step 3
    // to avoid race condition where orchestrator is missing from agents list
    const orchestratorResponse = await api.projects.getOrchestrator(projectId.value)
    orchestrator.value = orchestratorResponse.data.orchestrator

    // Step 3: NOW fetch agent jobs (orchestrator will be included if auto-created)
    const agentJobsResponse = await api.agentJobs.list(projectId.value)

    // Add the agent jobs to the project object so LaunchTab can display them
    // API returns {jobs: [...], total: N, limit: N, offset: N}
    if (agentJobsResponse.data && agentJobsResponse.data.jobs && Array.isArray(agentJobsResponse.data.jobs)) {
      project.value.agents = agentJobsResponse.data.jobs
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to load project'
  } finally {
    loading.value = false
  }
}

function handleEditDescription() {
  // Populate form with current project data
  projectData.value = {
    name: project.value.name,
    description: project.value.description || '',
    mission: project.value.mission || '',
    context_budget: project.value.context_budget || 150000,
  }
  showEditDialog.value = true
}

function handleEditMission(missionData) {
  if (!project.value) return

  projectData.value = {
    name: project.value.name,
    description: project.value.description || '',
    // Use the latest orchestrator mission text if provided from LaunchTab
    mission: missionData || project.value.mission || '',
    context_budget: project.value.context_budget || 150000,
  }

  showEditDialog.value = true
}

function handleEditAgentMission(agentData) {
  showNotification('Agent mission editing coming soon', 'info', 'mdi-information')
}

async function saveProject() {
  if (!formValid.value) {
    console.warn('Form is not valid')
    return
  }

  try {
    // Update project via API
    const updateData = {
      name: projectData.value.name,
      description: projectData.value.description,
      mission: projectData.value.mission,
      context_budget: projectData.value.context_budget,
    }

    await api.projects.update(projectId.value, updateData)

    // Refresh project data
    await fetchProjectDetails()

    // Close dialog
    showEditDialog.value = false

    // Show success message
    showNotification('Project updated successfully', 'success', 'mdi-check-circle')
  } catch (err) {
    console.error('Failed to update project:', err)
    showNotification(
      err.response?.data?.detail || 'Failed to update project',
      'error',
      'mdi-alert-circle',
    )
  }
}

function cancelEdit() {
  showEditDialog.value = false
  projectData.value = {
    name: '',
    description: '',
    mission: '',
    context_budget: 150000,
  }
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
/* Project Launch Container - Full height layout */
.project-launch-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0; /* Critical for flex overflow */
}

/* Main content area - fills remaining space */
.project-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0; /* Critical for nested flex overflow */
  overflow: hidden; /* Let ProjectTabs handle scrolling */
}
</style>
