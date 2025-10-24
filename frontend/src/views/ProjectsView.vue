<template>
  <v-container>
    <!-- Header -->
    <v-row align="center" class="mb-4">
      <v-col>
        <h1 class="text-h4">Project Management</h1>
        <p class="text-subtitle-1 text-medium-emphasis">
          Manage orchestration projects and their configurations
        </p>
      </v-col>
      <v-col cols="auto">
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="showCreateDialog = true"
          aria-label="Create new project"
        >
          New Project
        </v-btn>
      </v-col>
    </v-row>

    <!-- Stats Cards -->
    <v-row class="mb-4">
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon size="32" color="primary" class="mr-3">mdi-folder-multiple</v-icon>
              <div>
                <div class="text-caption">Total Projects</div>
                <div class="text-h5">{{ projects.length }}</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon size="32" color="success" class="mr-3">mdi-check-circle</v-icon>
              <div>
                <div class="text-caption">Active</div>
                <div class="text-h5">{{ activeCount }}</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text>
            <div class="d-flex align-center">
              <div style="width: 35px; height: 35px; margin-right: 12px">
                <v-img
                  :src="
                    theme.global.current.value.dark
                      ? '/icons/Giljo_YW_Face.svg'
                      : '/icons/Giljo_BY_Face.svg'
                  "
                  alt="Total Agents"
                  width="35"
                  height="35"
                ></v-img>
              </div>
              <div>
                <div class="text-caption">Total Agents</div>
                <div class="text-h5">{{ totalAgents }}</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon size="32" color="warning" class="mr-3">mdi-clipboard-check</v-icon>
              <div>
                <div class="text-caption">Active Tasks</div>
                <div class="text-h5">{{ activeTasks }}</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Projects Table -->
    <v-card>
      <v-card-title>
        <v-row align="center">
          <v-col>
            <span>Projects</span>
          </v-col>
          <v-col cols="auto">
            <v-text-field
              v-model="search"
              prepend-inner-icon="mdi-magnify"
              label="Search projects..."
              single-line
              hide-details
              density="compact"
              variant="outlined"
              clearable
            ></v-text-field>
          </v-col>
        </v-row>
      </v-card-title>

      <v-data-table
        :headers="headers"
        :items="filteredProjects"
        :search="search"
        :loading="loading"
        :items-per-page="10"
        class="elevation-0"
      >
        <!-- Name Column with UUID -->
        <template v-slot:item.name="{ item }">
          <div>
            <div class="text-body-1">{{ item.name }}</div>
            <div
              class="text-caption text-medium-emphasis"
              style="font-family: monospace; font-size: 0.7rem"
            >
              Project ID: {{ item.id }}
            </div>
          </div>
        </template>

        <!-- Status Column -->
        <template v-slot:item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" variant="tonal" size="small">
            {{ formatStatus(item.status) }}
          </v-chip>
        </template>

        <!-- Agents Column -->
        <template v-slot:item.agents="{ item }">
          <v-chip size="small" variant="outlined">
            <template v-slot:prepend>
              <v-img
                :src="
                  theme.global.current.value.dark
                    ? '/icons/Giljo_YW_Face.svg'
                    : '/icons/Giljo_BY_Face.svg'
                "
                alt="Agents"
                width="16"
                height="16"
                class="mr-1"
              ></v-img>
            </template>
            {{ item.agent_count || 0 }}
          </v-chip>
        </template>

        <!-- Context Usage -->
        <template v-slot:item.context="{ item }">
          <v-progress-linear
            :model-value="getContextUsage(item)"
            :color="getContextColor(item)"
            height="20"
            rounded
          >
            <template v-slot:default>
              <span class="text-caption">
                {{ formatNumber(item.context_used || 0) }} /
                {{ formatNumber(item.context_budget || 0) }}
              </span>
            </template>
          </v-progress-linear>
        </template>

        <!-- Created Date -->
        <template v-slot:item.created="{ item }">
          {{ formatDate(item.created_at) }}
        </template>

        <!-- Actions Column -->
        <template v-slot:item.actions="{ item }">
          <v-btn
            icon="mdi-eye"
            size="small"
            variant="text"
            @click="viewProject(item)"
            title="View Details"
            aria-label="View project details"
          ></v-btn>
          <v-btn
            icon="mdi-pencil"
            size="small"
            variant="text"
            @click="editProject(item)"
            title="Edit Project"
            aria-label="Edit project"
          ></v-btn>
          <v-btn
            v-if="item.status === 'active'"
            icon="mdi-stop"
            size="small"
            variant="text"
            color="warning"
            @click="closeProject(item)"
            title="Close Project"
            aria-label="Close project"
          ></v-btn>
          <v-btn
            v-else
            icon="mdi-play"
            size="small"
            variant="text"
            color="success"
            @click="activateProject(item)"
            title="Activate Project"
            aria-label="Activate project"
          ></v-btn>
          <v-btn
            icon="mdi-delete"
            size="small"
            variant="text"
            color="error"
            @click="confirmDelete(item)"
            title="Delete Project"
            aria-label="Delete project"
          ></v-btn>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="showCreateDialog" max-width="800" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <span>{{ editingProject ? 'Edit Project' : 'Create New Project' }}</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" @click="cancelEdit" aria-label="Close" />
        </v-card-title>
        <v-card-text>
          <!-- Show UUID for newly created project -->
          <v-alert
            v-if="createdProjectId"
            type="success"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            <div class="text-body-2 mb-1">Project created successfully!</div>
            <div class="text-caption">
              <strong>Project ID:</strong>
              <span class="ml-2" style="font-family: monospace">{{ createdProjectId }}</span>
            </div>
          </v-alert>

          <!-- Show Project ID when editing -->
          <v-alert v-if="editingProject" type="info" variant="tonal" density="compact" class="mb-4">
            <div class="text-caption">
              <strong>Project ID:</strong>
              <span class="ml-2" style="font-family: monospace">{{ editingProject.id }}</span>
            </div>
          </v-alert>

          <v-form ref="projectForm" v-model="formValid">
            <v-text-field
              v-model="projectData.name"
              label="Project Name"
              :rules="[(v) => !!v || 'Name is required']"
              required
              class="mb-3"
            ></v-text-field>

            <v-textarea
              v-model="projectData.mission"
              label="Mission Statement"
              :rules="[(v) => !!v || 'Mission is required']"
              rows="4"
              required
              class="mb-3"
            ></v-textarea>

            <v-text-field
              v-model.number="projectData.context_budget"
              label="Context Budget (tokens)"
              type="number"
              :rules="[(v) => v > 0 || 'Must be positive']"
              class="mb-3"
            ></v-text-field>

            <v-select
              v-model="projectData.status"
              label="Status"
              :items="['active', 'inactive', 'completed']"
              class="mb-3"
            ></v-select>

          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="cancelEdit">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :disabled="!formValid" @click="saveProject">
            {{ editingProject ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="400" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <span>Confirm Delete</span>
          <v-spacer />
          <v-btn
            icon="mdi-close"
            variant="text"
            @click="showDeleteDialog = false"
            aria-label="Close"
          />
        </v-card-title>
        <v-card-text>
          Are you sure you want to delete project "{{ projectToDelete?.name }}"? This action cannot
          be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showDeleteDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="flat" @click="deleteProject">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Close Project Dialog -->
    <v-dialog v-model="showCloseDialog" max-width="500" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <span>Close Project</span>
          <v-spacer />
          <v-btn
            icon="mdi-close"
            variant="text"
            @click="showCloseDialog = false"
            aria-label="Close"
          />
        </v-card-title>
        <v-card-text>
          <p class="mb-3">Closing project "{{ projectToClose?.name }}"</p>
          <v-textarea
            v-model="closeSummary"
            label="Completion Summary"
            rows="3"
            required
          ></v-textarea>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showCloseDialog = false">Cancel</v-btn>
          <v-btn color="warning" variant="flat" @click="confirmClose">Close Project</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { useProjectStore } from '@/stores/projects'
import { useAgentStore } from '@/stores/agents'
import { useTaskStore } from '@/stores/tasks'
import { formatDate, formatNumber, formatStatus } from '@/utils/formatters'

const theme = useTheme()

// Router
const router = useRouter()

// Stores
const projectStore = useProjectStore()
const agentStore = useAgentStore()
const taskStore = useTaskStore()

// Reactive state
const search = ref('')
const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const showCloseDialog = ref(false)
const formValid = ref(false)
const editingProject = ref(null)
const projectToDelete = ref(null)
const projectToClose = ref(null)
const closeSummary = ref('')
const createdProjectId = ref(null)

// Form data
const projectData = ref({
  name: '',
  mission: '',
  context_budget: 150000,
  status: 'inactive',
})

// Table headers
const headers = [
  { title: 'Name', key: 'name', sortable: true },
  { title: 'Status', key: 'status', sortable: true },
  { title: 'Agents', key: 'agents', sortable: false },
  { title: 'Context Usage', key: 'context', sortable: false },
  { title: 'Created', key: 'created', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
]

// Computed properties
const projects = computed(() => projectStore.projects)
const loading = computed(() => projectStore.loading)

const filteredProjects = computed(() => {
  if (!search.value) return projects.value

  const searchLower = search.value.toLowerCase()
  return projects.value.filter(
    (project) =>
      project.name.toLowerCase().includes(searchLower) ||
      project.mission?.toLowerCase().includes(searchLower) ||
      project.status.toLowerCase().includes(searchLower),
  )
})

const activeCount = computed(() => projects.value.filter((p) => p.status === 'active').length)

const totalAgents = computed(() => agentStore.agents.length)

const activeTasks = computed(() => taskStore.inProgressTasks.length + taskStore.pendingTasks.length)

// Methods
function getStatusColor(status) {
  const colors = {
    active: 'success',
    inactive: 'grey',
    completed: 'info',
    archived: 'warning',
  }
  return colors[status] || 'default'
}

function getContextUsage(project) {
  if (!project.context_budget) return 0
  return (project.context_used / project.context_budget) * 100
}

function getContextColor(project) {
  const usage = getContextUsage(project)
  if (usage > 90) return 'error'
  if (usage > 70) return 'warning'
  return 'success'
}

function viewProject(project) {
  router.push(`/projects/${project.id}`)
}

function editProject(project) {
  editingProject.value = project
  createdProjectId.value = null
  projectData.value = {
    name: project.name,
    mission: project.mission,
    context_budget: project.context_budget || 150000,
    status: project.status,
  }
  showCreateDialog.value = true
}

function activateProject(project) {
  projectStore.updateProject(project.id, { status: 'active' })
}

function closeProject(project) {
  projectToClose.value = project
  closeSummary.value = ''
  showCloseDialog.value = true
}

async function confirmClose() {
  if (projectToClose.value && closeSummary.value) {
    try {
      await projectStore.updateProject(projectToClose.value.id, {
        status: 'completed',
        summary: closeSummary.value,
      })
      showCloseDialog.value = false
      projectToClose.value = null
      closeSummary.value = ''
    } catch (error) {
      console.error('Failed to close project:', error)
    }
  }
}

function confirmDelete(project) {
  projectToDelete.value = project
  showDeleteDialog.value = true
}

async function deleteProject() {
  if (projectToDelete.value) {
    try {
      await projectStore.deleteProject(projectToDelete.value.id)
      showDeleteDialog.value = false
      projectToDelete.value = null
    } catch (error) {
      console.error('Failed to delete project:', error)
    }
  }
}

function cancelEdit() {
  showCreateDialog.value = false
  editingProject.value = null
  createdProjectId.value = null
  resetForm()
}

function resetForm() {
  projectData.value = {
    name: '',
    mission: '',
    context_budget: 150000,
    status: 'inactive',
  }
}

async function saveProject() {
  if (!formValid.value) {
    console.warn('Form is not valid')
    return
  }

  console.log('Saving project with data:', projectData.value)

  try {
    if (editingProject.value) {
      // Update existing project
      console.log('Updating project:', editingProject.value.id)

      // Only send fields that the API supports for updates
      const updateData = {
        name: projectData.value.name,
        mission: projectData.value.mission,
        status: projectData.value.status,
      }

      await projectStore.updateProject(editingProject.value.id, updateData)

      // Refresh the project list to show updated data
      await projectStore.fetchProjects()

      showCreateDialog.value = false
      editingProject.value = null
      createdProjectId.value = null
      resetForm()
    } else {
      // Create new project - send all fields
      console.log('Creating new project')
      const result = await projectStore.createProject(projectData.value)
      console.log('Project created successfully:', result)

      // Show the UUID in the dialog
      createdProjectId.value = result.id

      // Keep the dialog open to show the UUID
      // User can close it manually after noting the UUID
    }
  } catch (error) {
    console.error('Failed to save project:', error)
    console.error('Error details:', error.response?.data || error.message)
    // Show error to user
    alert(`Failed to save project: ${error.response?.data?.error || error.message}`)
  }
}

// Lifecycle
onMounted(async () => {
  // Load initial data
  await Promise.all([
    projectStore.fetchProjects(),
    agentStore.fetchAgents(),
    taskStore.fetchTasks(),
  ])
})
</script>
