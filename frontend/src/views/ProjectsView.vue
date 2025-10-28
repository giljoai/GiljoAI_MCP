<template>
  <v-container>
    <!-- Header -->\n    <v-row align="center" class="mb-4">
      <v-col>
        <h1 class="text-h4">Project Management</h1>
        <p class="text-subtitle-1 text-medium-emphasis">
          Manage orchestration projects for: <strong>{{ activeProduct?.name || 'No Active Product' }}</strong>
        </p>
      </v-col>
      <v-col cols="auto">
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="showCreateDialog = true"
          :disabled="!activeProduct"
          aria-label="Create new project"
        >
          New Project
        </v-btn>
      </v-col>
    </v-row>

    <!-- No Active Product Alert -->
    <v-alert
      v-if="!activeProduct"
      type="info"
      variant="tonal"
      class="ma-4"
      closable
    >
      No active product selected. Please activate a product to view and manage its projects.
    </v-alert>

    <!-- Stats Cards -->
    <v-row v-if="activeProduct" class="mb-4">
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon size="32" color="primary" class="mr-3">mdi-folder-multiple</v-icon>
              <div>
                <div class="text-caption">Total Projects</div>
                <div class="text-h5">{{ filteredProjects.length }}</div>
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
                <div class="text-h5">{{ statusCounts.active }}</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon size="32" color="warning" class="mr-3">mdi-pause-circle</v-icon>
              <div>
                <div class="text-caption">Paused</div>
                <div class="text-h5">{{ statusCounts.paused }}</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon size="32" color="info" class="mr-3">mdi-clipboard-check</v-icon>
              <div>
                <div class="text-caption">Completed</div>
                <div class="text-h5">{{ statusCounts.completed }}</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filters & Search Section -->
    <v-card v-if="activeProduct" class="mb-4">
      <v-card-text class="pb-2">
        <!-- Search Bar -->
        <v-row align="center" class="mb-4">
          <v-col>
            <v-text-field
              v-model="searchQuery"
              prepend-inner-icon="mdi-magnify"
              label="Search Projects..."
              single-line
              hide-details
              density="compact"
              variant="outlined"
              clearable
              aria-label="Search projects by name"
            ></v-text-field>
          </v-col>
          <v-col cols="auto">
            <v-btn
              variant="outlined"
              prepend-icon="mdi-delete-restore"
              :text="deletedCount > 0 ? `View Deleted (${deletedCount})` : 'View Deleted'"
              @click="showDeletedDialog = true"
              :disabled="deletedCount === 0"
              aria-label="View deleted projects"
            >
            </v-btn>
          </v-col>
        </v-row>

        <!-- Status Filter Chips -->
        <div class="d-flex gap-2 flex-wrap">
          <v-chip
            v-for="status in filterOptions"
            :key="status.value"
            :color="filterStatus === status.value ? 'primary' : 'default'"
            :variant="filterStatus === status.value ? 'tonal' : 'outlined'"
            @click="filterStatus = status.value"
            :aria-label="`Filter by ${status.label}`"
            class="cursor-pointer"
          >
            {{ status.label }} ({{ status.count }})
          </v-chip>
        </div>
      </v-card-text>
    </v-card>

    <!-- Projects Table -->
    <v-card v-if="activeProduct">
      <v-data-table
        :headers="headers"
        :items="sortedProjects"
        :loading="loading"
        :items-per-page="itemsPerPage"
        :page="currentPage"
        @update:page="currentPage = $event"
        :sort-by="sortConfig"
        @update:sort-by="sortConfig = $event"
        class="elevation-0"
        item-key="id"
      >
        <!-- Name Column with ID -->
        <template v-slot:item.name="{ item }">
          <div class="py-2">
            <div class="font-weight-bold text-body-2">{{ item.name }}</div>
            <div class="text-caption text-medium-emphasis" style="font-family: monospace">
              Project ID: {{ item.id }}
            </div>
          </div>
        </template>

        <!-- Status Column with Badge -->
        <template v-slot:item.status="{ item }">
          <StatusBadge
            :status="item.status"
            :project-id="item.id"
            @action="handleStatusAction"
          />
        </template>

        <!-- Product Column -->
        <template v-slot:item.product="{ item }">
          <span class="text-caption">
            {{ activeProduct?.name || '—' }}
          </span>
        </template>

        <!-- Agents Column -->
        <template v-slot:item.agents="{ item }">
          <v-chip size="small" variant="outlined">
            {{ item.agent_count || 0 }}
          </v-chip>
        </template>

        <!-- Created Date Column -->
        <template v-slot:item.created="{ item }">
          {{ formatDateShort(item.created_at) }}
        </template>

        <!-- Completed Date Column -->
        <template v-slot:item.completed="{ item }">
          {{
            item.status === 'completed' || item.status === 'cancelled'
              ? formatDateShort(item.completed_at || item.updated_at)
              : '—'
          }}
        </template>

        <!-- Actions Column -->
        <template v-slot:item.actions="{ item }">
          <v-menu>
            <template v-slot:activator="{ props }">
              <v-btn
                icon="mdi-dots-vertical"
                size="small"
                variant="text"
                v-bind="props"
                aria-label="Project actions"
              ></v-btn>
            </template>

            <v-list density="compact" min-width="150">
              <v-list-item
                @click="viewProject(item)"
                prepend-icon="mdi-eye"
                title="View Details"
              ></v-list-item>
              <v-list-item
                @click="editProject(item)"
                prepend-icon="mdi-pencil"
                title="Edit Project"
              ></v-list-item>
              <v-divider class="my-1" />
              <v-list-item
                @click="confirmDelete(item)"
                prepend-icon="mdi-delete"
                title="Delete Project"
              ></v-list-item>
            </v-list>
          </v-menu>
        </template>

        <!-- No data state -->
        <template v-slot:no-data>
          <div class="text-center py-8">
            <v-icon size="48" color="medium-emphasis" class="mb-4">mdi-folder-open</v-icon>
            <p class="text-body-2 text-medium-emphasis">No projects found</p>
            <v-btn
              size="small"
              color="primary"
              @click="showCreateDialog = true"
              class="mt-4"
            >
              Create First Project
            </v-btn>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="showCreateDialog" max-width="800" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <span>{{ editingProject ? 'Edit Project' : 'Create New Project' }}</span>
          <v-spacer />
          <v-btn
            icon="mdi-close"
            variant="text"
            @click="cancelEdit"
            aria-label="Close dialog"
          />
        </v-card-title>

        <v-card-text>
          <!-- Success Alert -->
          <v-alert
            v-if="createdProjectId"
            type="success"
            variant="tonal"
            density="compact"
            class="mb-4"
            closable
          >
            <div class="text-body-2 mb-1">Project created successfully!</div>
            <div class="text-caption">
              <strong>Project ID:</strong>
              <span class="ml-2" style="font-family: monospace">{{ createdProjectId }}</span>
            </div>
          </v-alert>

          <!-- Project ID Info Alert -->
          <v-alert v-if="editingProject" type="info" variant="tonal" density="compact" class="mb-4">
            <div class="text-caption">
              <strong>Project ID:</strong>
              <span class="ml-2" style="font-family: monospace">{{ editingProject.id }}</span>
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
              aria-label="Project name"
            ></v-text-field>

            <v-textarea
              v-model="projectData.mission"
              label="Mission Statement"
              :rules="[(v) => !!v || 'Mission is required']"
              rows="4"
              required
              class="mb-3"
              aria-label="Mission statement"
            ></v-textarea>

            <v-text-field
              v-model.number="projectData.context_budget"
              label="Context Budget (tokens)"
              type="number"
              :rules="[(v) => v > 0 || 'Must be positive']"
              class="mb-3"
              aria-label="Context budget"
            ></v-text-field>

            <v-select
              v-model="projectData.status"
              label="Status"
              :items="statusOptions"
              class="mb-3"
              aria-label="Project status"
            ></v-select>
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="cancelEdit">Cancel</v-btn>
          <v-btn
            color="primary"
            variant="flat"
            :disabled="!formValid"
            @click="saveProject"
          >
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
            aria-label="Close dialog"
          />
        </v-card-title>

        <v-card-text>
          Are you sure you want to delete project <strong>"{{ projectToDelete?.name }}"</strong>?
          This action cannot be undone.
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showDeleteDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="flat" @click="deleteProject">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Deleted Projects Modal -->
    <v-dialog v-model="showDeletedDialog" max-width="800" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <span>Deleted Projects ({{ deletedProjects.length }})</span>
          <v-spacer />
          <v-btn
            icon="mdi-close"
            variant="text"
            @click="showDeletedDialog = false"
            aria-label="Close dialog"
          />
        </v-card-title>

        <v-card-text>
          <v-list v-if="deletedProjects.length > 0" class="border rounded">
            <v-list-item
              v-for="(project, index) in deletedProjects"
              :key="project.id"
            >
              <template v-slot:prepend>
                <v-icon icon="mdi-folder-minus"></v-icon>
              </template>

              <div class="flex-grow-1">
                <div class="font-weight-bold">{{ project.name }}</div>
                <div class="text-caption text-medium-emphasis">
                  {{ project.id }}
                </div>
              </div>

              <template v-slot:append>
                <v-btn
                  icon="mdi-restore"
                  size="small"
                  variant="text"
                  @click="restoreFromDelete(project)"
                  title="Restore project"
                  aria-label="Restore deleted project"
                ></v-btn>
              </template>

              <v-divider v-if="index < deletedProjects.length - 1" class="my-2" />
            </v-list-item>
          </v-list>

          <div v-else class="text-center py-8 text-medium-emphasis">
            <v-icon size="48" class="mb-4">mdi-folder-open</v-icon>
            <p>No deleted projects</p>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showDeletedDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projects'
import { useProductStore } from '@/stores/products'
import { useAgentStore } from '@/stores/agents'
import StatusBadge from '@/components/StatusBadge.vue'
import { formatStatus } from '@/utils/formatters'

// Router
const router = useRouter()

// Stores
const projectStore = useProjectStore()
const productStore = useProductStore()
const agentStore = useAgentStore()

// Reactive state
const searchQuery = ref('')
const filterStatus = ref('all')
const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const showDeletedDialog = ref(false)
const formValid = ref(false)
const editingProject = ref(null)
const projectToDelete = ref(null)
const createdProjectId = ref(null)
const currentPage = ref(1)
const itemsPerPage = ref(10)

// Sort configuration
const sortConfig = ref([{ key: 'created_at', order: 'desc' }])

// Form data
const projectData = ref({
  name: '',
  mission: '',
  context_budget: 150000,
  status: 'inactive',
})

// Status options
const statusOptions = ['active', 'inactive', 'paused', 'completed', 'cancelled']

// Filter options computed
const filterOptions = computed(() => {
  const counts = statusCounts.value
  return [
    { label: 'All', value: 'all', count: filteredBySearch.value.length },
    { label: 'Active', value: 'active', count: counts.active },
    { label: 'Inactive', value: 'inactive', count: counts.inactive },
    { label: 'Paused', value: 'paused', count: counts.paused },
    { label: 'Completed', value: 'completed', count: counts.completed },
    { label: 'Cancelled', value: 'cancelled', count: counts.cancelled },
  ]
})

// Table headers
const headers = [
  { title: 'Name', key: 'name', sortable: true, width: '25%' },
  { title: 'Status', key: 'status', sortable: true, width: '12%' },
  { title: 'Product', key: 'product', sortable: false, width: '15%' },
  { title: 'Agents', key: 'agents', sortable: false, width: '10%', align: 'center' },
  { title: 'Created', key: 'created_at', sortable: true, width: '15%' },
  { title: 'Completed', key: 'completed', sortable: false, width: '15%' },
  { title: 'Actions', key: 'actions', sortable: false, width: '8%', align: 'end' },
]

// Computed properties
const activeProduct = computed(() => productStore.activeProduct)
const projects = computed(() => projectStore.projects)
const loading = computed(() => projectStore.loading)

// Filter projects by active product
const activeProductProjects = computed(() => {
  if (!activeProduct.value) return []
  return projects.value.filter((p) => p.product_id === activeProduct.value.id && !p.deleted_at)
})

// Filter by search query
const filteredBySearch = computed(() => {
  if (!searchQuery.value) return activeProductProjects.value

  const query = searchQuery.value.toLowerCase()
  return activeProductProjects.value.filter(
    (p) =>
      p.name.toLowerCase().includes(query) ||
      p.mission?.toLowerCase().includes(query) ||
      p.id.toLowerCase().includes(query)
  )
})

// Filter by status
const filteredProjects = computed(() => {
  if (filterStatus.value === 'all') return filteredBySearch.value
  return filteredBySearch.value.filter((p) => p.status === filterStatus.value)
})

// Sort projects
const sortedProjects = computed(() => {
  const sorted = [...filteredProjects.value]

  if (sortConfig.value && sortConfig.value.length > 0) {
    const { key, order } = sortConfig.value[0]
    const isAsc = order === 'asc'

    sorted.sort((a, b) => {
      let aVal = a[key]
      let bVal = b[key]

      if (!aVal) aVal = ''
      if (!bVal) bVal = ''

      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase()
        bVal = bVal.toLowerCase()
      }

      if (aVal < bVal) return isAsc ? -1 : 1
      if (aVal > bVal) return isAsc ? 1 : -1
      return 0
    })
  }

  return sorted
})

// Count projects by status
const statusCounts = computed(() => {
  return {
    active: activeProductProjects.value.filter((p) => p.status === 'active').length,
    inactive: activeProductProjects.value.filter((p) => p.status === 'inactive').length,
    paused: activeProductProjects.value.filter((p) => p.status === 'paused').length,
    completed: activeProductProjects.value.filter((p) => p.status === 'completed').length,
    cancelled: activeProductProjects.value.filter((p) => p.status === 'cancelled').length,
  }
})

// Deleted projects
const deletedProjects = computed(() => {
  if (!activeProduct.value) return []
  return projects.value.filter((p) => p.product_id === activeProduct.value.id && p.deleted_at)
})

const deletedCount = computed(() => deletedProjects.value.length)

// Format date short (MM/DD or MM/DD/YY)
function formatDateShort(dateStr) {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  const today = new Date()
  const isCurrentYear = date.getFullYear() === today.getFullYear()

  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  if (isCurrentYear) {
    return `${month}/${day}`
  }

  const year = String(date.getFullYear()).slice(-2)
  return `${month}/${day}/${year}`
}

// Methods
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

async function restoreFromDelete(project) {
  try {
    await projectStore.restoreProject(project.id)
    showDeletedDialog.value = false
  } catch (error) {
    console.error('Failed to restore project:', error)
  }
}

async function handleStatusAction({ action, projectId }) {
  try {
    switch (action) {
      case 'activate':
        await projectStore.activateProject(projectId)
        break
      case 'pause':
        await projectStore.pauseProject(projectId)
        break
      case 'complete':
        await projectStore.completeProject(projectId)
        break
      case 'cancel':
        await projectStore.cancelProject(projectId)
        break
      case 'restore':
        await projectStore.restoreProject(projectId)
        break
      case 'delete':
        const project = projectStore.projectById(projectId)
        if (project) {
          confirmDelete(project)
        }
        break
    }
  } catch (error) {
    console.error('Failed to perform action:', error)
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

  try {
    if (editingProject.value) {
      // Update existing project
      const updateData = {
        name: projectData.value.name,
        mission: projectData.value.mission,
        status: projectData.value.status,
      }

      await projectStore.updateProject(editingProject.value.id, updateData)
      await projectStore.fetchProjects()

      showCreateDialog.value = false
      editingProject.value = null
      createdProjectId.value = null
      resetForm()
    } else {
      // Create new project
      const createData = {
        ...projectData.value,
        product_id: activeProduct.value?.id,
      }

      const result = await projectStore.createProject(createData)
      createdProjectId.value = result.id

      await projectStore.fetchProjects()

      // Reset form but keep dialog open to show success
      resetForm()
      setTimeout(() => {
        showCreateDialog.value = false
        createdProjectId.value = null
      }, 2000)
    }
  } catch (error) {
    console.error('Failed to save project:', error)
    alert(`Failed to save project: ${error.response?.data?.error || error.message}`)
  }
}

// Lifecycle
onMounted(async () => {
  try {
    await Promise.all([
      productStore.fetchProducts(),
      productStore.fetchActiveProduct(),
      projectStore.fetchProjects(),
      agentStore.fetchAgents(),
    ])
  } catch (error) {
    console.error('Failed to load data:', error)
  }
})
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}

.gap-2 {
  gap: 0.5rem;
}

.border {
  border: 1px solid rgba(0, 0, 0, 0.12);
}

.rounded {
  border-radius: 4px;
}
</style>
