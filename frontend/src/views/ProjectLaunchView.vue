<template>
  <div class="project-launch-container">
    <!-- Loading State -->
    <v-container v-if="loading" fluid class="pa-6">
      <v-row class="justify-center py-12">
        <v-col cols="12" class="text-center">
          <v-progress-circular indeterminate color="primary" size="64" />
          <p class="text-body-large mt-4">Loading project details...</p>
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
              <p class="text-body-medium">{{ error }}</p>
            </div>
          </v-alert>
        </v-col>
      </v-row>
    </v-container>

    <!-- Main Content - ProjectTabs handles its own sticky header -->
    <div v-else class="project-content">
      <ProjectTabs
        v-if="project"
        :project="project"
        :orchestrator="orchestrator"
        :chain-ctx="chainCtx"
        @edit-description="handleEditDescription"
        @project-updated="fetchProjectDetails"
      />
    </div>

    <!-- Edit Project Dialog -->
    <v-dialog v-model="showEditDialog" max-width="800" persistent scrollable>
      <v-card v-draggable class="smooth-border">
        <div class="dlg-header">
          <span class="dlg-title">Edit Project</span>
          <v-btn icon variant="text" class="dlg-close" @click="cancelEdit">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>

        <v-card-text>
          <!-- Project ID Info -->
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            <div class="text-body-small">
              <strong>Project ID:</strong>
              <span class="ml-2 font-mono">{{ project?.id }}</span>
            </div>
          </v-alert>

          <!-- Form -->
          <v-form ref="projectForm" v-model="formValid">
            <v-text-field
              v-model="projectData.name"
              label="Project Name"
              :rules="[(v) => !!v || 'Project name is required']"
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

          </v-form>
        </v-card-text>

        <div class="dlg-footer">
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="cancelEdit">Cancel</v-btn>
          <v-btn color="primary" variant="flat" @click="saveProject">
            Update
          </v-btn>
        </div>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { useProjectStore } from '@/stores/projects'
import { useChainContext } from '@/composables/useChainContext'
import { api } from '@/services/api'
import ProjectTabs from '@/components/projects/ProjectTabs.vue'

const route = useRoute()
const projectId = ref(route.params.projectId)
const orchestrator = ref(null)
const loading = ref(true)
const error = ref(null)

const { showToast } = useToast()
const projectStore = useProjectStore()

// FE-6174b: conditional multi-project layer. chainCtx is null unless the route
// carries ?run=<id>; when null the view renders the byte-identical solo path.
const { chainCtx } = useChainContext()

// FE-3007a: the project entity is read STORE-FIRST (single owner, keyed by id).
// No local copy and no per-field whitelist patch — the store updates reactively
// on WS events (full-refetch-on-event), so the view follows automatically.
const project = computed(() => projectStore.projectById(projectId.value))

// Edit dialog state
const showEditDialog = ref(false)
const formValid = ref(false)
const projectForm = ref(null)
const projectData = ref({
  name: '',
  description: '',
  mission: '',
})

async function fetchProjectDetails({ spinner = true } = {}) {
  // FE-6174b: on a chain tab switch the project is already store-resident (the
  // chain context warmed projectStore), so refetch QUIETLY — keep ProjectTabs
  // mounted instead of flashing the full-screen spinner on every tab click.
  if (spinner) loading.value = true
  error.value = null
  try {
    // Step 1: Fetch the project ONCE into the store (the single owner). The
    // ProjectTabs lifecycle no longer re-fetches on initial mount, so this is
    // the only project GET on page open.
    await projectStore.fetchProject(projectId.value)
    if (!project.value) {
      throw new Error(projectStore.error || 'Project not found')
    }

    // Step 2: Get/create orchestrator BEFORE the lifecycle lists agent jobs.
    // CRITICAL: this must complete (including DB commit) before the agent-jobs
    // list runs, to avoid a race where the orchestrator is missing from it.
    // Agent jobs themselves are loaded once by the ProjectTabs lifecycle via
    // the agent-jobs store — we no longer fetch them here (kills the
    // double-fetch).
    const orchestratorResponse = await api.projects.getOrchestrator(projectId.value)
    orchestrator.value = orchestratorResponse.data.orchestrator
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
  }
  showEditDialog.value = true
}

async function saveProject() {
  // Validate ON CLICK instead of relying on a silently-disabled Update button.
  // Description is required and Vuetify shows its required error only after the
  // field is touched, so clearing Description on an edit left Update dead with no
  // visible reason (perf-findings 2026-06-11, same class as the project-create
  // fix). validate() surfaces "Description is required" on the field.
  if (typeof projectForm.value?.validate === 'function') {
    const { valid } = await projectForm.value.validate()
    if (!valid) return
  }

  try {
    // Update project via API
    const updateData = {
      name: projectData.value.name,
      description: projectData.value.description,
      mission: projectData.value.mission,
    }

    // FE-3007a: write through the store (single write path). updateProject
    // upserts the entity into byId, so the store-backed `project` computed
    // reflects the edit reactively — no manual refetch needed.
    await projectStore.updateProject(projectId.value, updateData)

    // Close dialog
    showEditDialog.value = false

    // Show success message
    showNotification('Project updated successfully', 'success')
  } catch (err) {
    console.error('Failed to update project:', err)
    showNotification(
      err.response?.data?.detail || 'Failed to update project',
      'error',
    )
  }
}

function cancelEdit() {
  showEditDialog.value = false
  projectData.value = {
    name: '',
    description: '',
    mission: '',
  }
}

function showNotification(message, color = 'success') {
  const colorToType = { success: 'success', error: 'error', info: 'info', warning: 'warning' }
  showToast({ message, type: colorToType[color] || 'info' })
}

// FE-6174b: the chain tab strip navigates between projects on the SAME route
// (/projects/:projectId?run=...). The router reuses this view instance on a
// param-only change, so refetch the newly-viewed project when projectId changes.
watch(
  () => route.params.projectId,
  (newPid) => {
    if (newPid && newPid !== projectId.value) {
      projectId.value = newPid
      // Quiet refetch when the project is already in the store (warm chain tab
      // switch) — avoids the spinner unmount/remount of ProjectTabs.
      const warm = Boolean(projectStore.projectById(newPid))
      fetchProjectDetails({ spinner: !warm })
    }
  },
)

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
