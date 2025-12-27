<template>
  <v-container>
    <!-- Header -->
    <v-row align="center" class="mb-4">
      <v-col>
        <h1 class="text-h4">Project Management</h1>
        <p class="text-subtitle-1 text-medium-emphasis">
          Manage orchestration projects for:
          <strong style="color: #ffc300">{{ activeProduct?.name || 'No Active Product' }}</strong>
        </p>
      </v-col>
    </v-row>

    <!-- No Active Product Alert -->
    <v-alert v-if="!activeProduct" type="info" variant="tonal" class="ma-4" closable>
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
              <v-icon size="32" color="grey" class="mr-3">mdi-stop-circle-outline</v-icon>
              <div>
                <div class="text-caption">Inactive</div>
                <div class="text-h5">{{ statusCounts.inactive }}</div>
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
        </v-row>

        <!-- Status Filter Chips -->
        <div class="d-flex gap-2 flex-wrap align-center">
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
      <!-- Project List Header Bar -->
      <v-card-title class="d-flex align-center justify-space-between px-4 py-3 border-b">
        <span class="text-h6">Project List</span>

        <div class="d-flex align-center ga-2">
          <!-- Launch Project Button (only when exactly 1 active project) -->
          <v-btn
            v-if="hasActiveProject"
            color="#ffc300"
            variant="flat"
            prepend-icon="mdi-rocket-launch"
            @click="launchProject(activeProject.id)"
            :title="isWorking(activeProject) ? 'View running jobs' : 'Launch active project'"
          >
            {{ isWorking(activeProject) ? 'Working' : 'Launch Project' }}
          </v-btn>

          <v-divider v-if="hasActiveProject" vertical class="mx-1" style="height: 24px" />

          <!-- New Project Button -->
          <v-btn
            color="primary"
            variant="flat"
            prepend-icon="mdi-plus"
            @click="showCreateDialog = true"
            :disabled="!activeProduct"
            aria-label="Create new project"
          >
            New Project
          </v-btn>

          <!-- Deleted Projects Button -->
          <v-btn
            variant="outlined"
            prepend-icon="mdi-delete-restore"
            @click="showDeletedDialog = true"
            :disabled="deletedCount === 0"
            aria-label="View deleted projects"
          >
            Deleted ({{ deletedCount }})
          </v-btn>

          <v-divider vertical class="mx-1" style="height: 24px" />

          <!-- Date Format Toggle -->
          <v-btn
            variant="outlined"
            @click="toggleDateLocale"
            :title="`Switch to ${dateLocale === 'US' ? 'EU' : 'US'} date format`"
            prepend-icon="mdi-calendar"
          >
            {{ dateLocale }} Format
          </v-btn>
        </div>
      </v-card-title>

      <!-- Scrollable Table Container -->
      <div class="project-list-container">
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
          fixed-header
          :item-props="() => ({ 'data-testid': 'project-card' })"
          @click:row="handleRowClick"
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
            <v-chip
              :color="getStatusColor(normalizeStatus(item.status))"
              size="small"
              variant="tonal"
              data-testid="project-status"
            >
              {{ normalizeStatus(item.status) }}
            </v-chip>
          </template>

          <!-- Product Column -->
          <template v-slot:item.product="{ item }">
            <span class="text-caption">
              {{ activeProduct?.name || '—' }}
            </span>
          </template>

          <!-- Staged Column -->
          <template v-slot:item.staged="{ item }">
            <v-chip
              :color="isProjectStaged(item) ? 'success' : 'default'"
              size="small"
              variant="tonal"
            >
              {{ isProjectStaged(item) ? 'Yes' : 'No' }}
            </v-chip>
          </template>

          <!-- Created Date Column -->
          <template v-slot:item.created_at="{ item }">
            {{ formatDateShort(item.created_at) }}
          </template>

          <!-- Completed Date Column -->
          <template v-slot:item.completed_at="{ item }">
            <div class="text-center">
              {{
                item.status === 'completed' || item.status === 'cancelled'
                  ? formatDateShort(item.completed_at || item.updated_at)
                  : '—'
              }}
            </div>
          </template>

          <!-- Actions Column (StatusBadge only) -->
          <template v-slot:item.actions="{ item }">
            <div class="d-flex align-center justify-center">
              <StatusBadge
                :status="normalizeStatus(item.status)"
                :project-id="item.id"
                @action="handleStatusAction"
              />
            </div>
          </template>

          <!-- Menu Column (separate) -->
          <template v-slot:item.menu="{ item }">
            <div class="d-flex align-center justify-center">
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
            </div>
          </template>

          <!-- No data state -->
          <template v-slot:no-data>
            <div class="text-center py-8">
              <v-icon size="48" color="medium-emphasis" class="mb-4">mdi-folder-open</v-icon>
              <p class="text-body-2 text-medium-emphasis">No projects found</p>
              <v-btn size="small" color="primary" @click="showCreateDialog = true" class="mt-4">
                Create First Project
              </v-btn>
            </div>
          </template>
        </v-data-table>
      </div>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="showCreateDialog" max-width="800" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <span>{{ editingProject ? 'Edit Project' : 'Create New Project' }}</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" @click="cancelEdit" aria-label="Close dialog" />
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
              v-model="projectData.description"
              label="Project Description"
              :rules="[(v) => !!v || 'Description is required']"
              hint="Human-written description of what you want to accomplish. This will be shown to the orchestrator."
              persistent-hint
              rows="4"
              required
              class="mb-3"
              aria-label="Project description"
            ></v-textarea>

            <v-textarea
              v-model="projectData.mission"
              label="Orchestrator Generated Mission"
              readonly
              variant="outlined"
              rows="4"
              class="mb-3"
              hint="Auto-generated during staging. Clear to regenerate on next staging."
              persistent-hint
              :placeholder="
                projectData.mission ? '' : 'Mission will be generated when you stage this project'
              "
              aria-label="Orchestrator generated mission"
            >
              <template #append>
                <v-menu>
                  <template #activator="{ props }">
                    <v-btn
                      icon="mdi-dots-vertical"
                      v-bind="props"
                      size="small"
                      variant="text"
                      aria-label="Mission actions"
                    />
                  </template>
                  <v-list>
                    <v-list-item @click="viewFullMission" :disabled="!projectData.mission">
                      <v-list-item-title>View Full Mission</v-list-item-title>
                    </v-list-item>
                    <v-list-item @click="clearMission" :disabled="!projectData.mission">
                      <v-list-item-title>Clear Mission</v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-menu>
              </template>
            </v-textarea>

            <!-- Handover 0316: Soft deprecated (kept for backward compatibility) -->
            <v-text-field
              v-model.number="projectData.context_budget"
              label="Context Budget (Deprecated)"
              type="number"
              :rules="[(v) => v > 0 || 'Must be positive']"
              class="mb-3"
              aria-label="Context budget (deprecated)"
              hint="⚠️ Deprecated: This field will be removed in v4.0. Context is now managed via depth configuration in My Settings."
              persistent-hint
              disabled
              variant="outlined"
            ></v-text-field>

            <!-- Status removed - always defaults to inactive (Handover 0062) -->
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
            aria-label="Close dialog"
          />
        </v-card-title>

        <v-card-text>
          Are you sure you want to delete project <strong>"{{ projectToDelete?.name }}"</strong>?
          This will move the project to <strong>Deleted Projects</strong> for 10 days. It can be
          restored from there during that time. After 10 days it will be permanently purged.
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
          <v-alert
            v-if="deletedProjects.length > 0"
            type="warning"
            variant="tonal"
            density="compact"
            class="mb-3"
          >
            Permanently deleting items will remove all related data immediately. This action cannot
            be undone.
          </v-alert>

          <v-list v-if="deletedProjects.length > 0" class="border rounded">
            <v-list-item v-for="(project, index) in deletedProjects" :key="project.id">
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
                <div class="d-flex align-center ga-1">
                  <v-btn
                    icon="mdi-restore"
                    size="small"
                    variant="text"
                    @click="restoreFromDelete(project)"
                    :disabled="purgingProjectId === project.id || purgingAllDeleted"
                    title="Restore project"
                    aria-label="Restore deleted project"
                  ></v-btn>
                  <v-btn
                    icon="mdi-trash-can"
                    size="small"
                    variant="text"
                    color="error"
                    :loading="purgingProjectId === project.id"
                    :disabled="purgingAllDeleted"
                    @click="confirmPurgeDeleted(project)"
                    title="Permanently delete project"
                    aria-label="Permanently delete project"
                    data-testid="purge-project"
                  ></v-btn>
                </div>
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
          <v-btn
            color="error"
            variant="flat"
            prepend-icon="mdi-delete-forever"
            :disabled="deletedProjects.length === 0 || purgingAllDeleted"
            :loading="purgingAllDeleted"
            @click="confirmPurgeAllDeleted"
            data-testid="purge-projects-all"
          >
            Delete All
          </v-btn>
          <v-btn variant="text" @click="showDeletedDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Mission Viewer Dialog -->
    <v-dialog v-model="showMissionDialog" max-width="800" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <span>Full Mission Text</span>
          <v-spacer />
          <v-btn
            icon="mdi-close"
            variant="text"
            @click="showMissionDialog = false"
            aria-label="Close dialog"
          />
        </v-card-title>

        <v-card-text>
          <v-sheet
            class="pa-4 rounded border"
            color="grey-lighten-5"
            style="
              max-height: 500px;
              overflow-y: auto;
              white-space: pre-wrap;
              font-family: monospace;
              font-size: 0.875rem;
              line-height: 1.5;
            "
          >
            {{ projectData.mission || 'No mission text available' }}
          </v-sheet>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showMissionDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Closeout Modal -->
    <CloseoutModal
      :show="showCloseoutModal"
      :project-id="closeoutProjectId"
      :project-name="closeoutProjectName"
      @close="handleCloseoutClose"
      @complete="handleCloseoutComplete"
    />
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projects'
import { useProductStore } from '@/stores/products'
import { useAgentStore } from '@/stores/agents'
import { useProjectTabsStore } from '@/stores/projectTabs'
import StatusBadge from '@/components/StatusBadge.vue'
import CloseoutModal from '@/components/orchestration/CloseoutModal.vue'
import { formatStatus } from '@/utils/formatters'

// Router
const router = useRouter()

// Stores
const projectStore = useProjectStore()
const productStore = useProductStore()
const agentStore = useAgentStore()
const tabsStore = useProjectTabsStore()

// Reactive state
const searchQuery = ref('')
const filterStatus = ref('all')
const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const showDeletedDialog = ref(false)
const showMissionDialog = ref(false)
const showCloseoutModal = ref(false)
const closeoutProjectId = ref(null)
const closeoutProjectName = ref('')
const formValid = ref(false)
const editingProject = ref(null)
const projectToDelete = ref(null)
const createdProjectId = ref(null)
const currentPage = ref(1)
const itemsPerPage = ref(10)
const purgingProjectId = ref(null)
const purgingAllDeleted = ref(false)

// Sort configuration
const sortConfig = ref([{ key: 'created_at', order: 'desc' }])

// Date locale preference (US: MM-DD-YYYY, EU: DD-MM-YYYY)
const dateLocale = ref(localStorage.getItem('dateLocale') || 'US')

// Form data
const projectData = ref({
  name: '',
  description: '',
  mission: '',
  context_budget: 150000,
  status: 'inactive',
})

// Status options
const statusOptions = ['active', 'inactive', 'completed', 'cancelled']

// Filter options computed
const filterOptions = computed(() => {
  const counts = statusCounts.value
  return [
    { label: 'All', value: 'all', count: filteredBySearch.value.length },
    { label: 'Active', value: 'active', count: counts.active },
    { label: 'Inactive', value: 'inactive', count: counts.inactive },
    { label: 'Completed', value: 'completed', count: counts.completed },
    { label: 'Cancelled', value: 'cancelled', count: counts.cancelled },
  ]
})

// Table headers
const headers = [
  { title: 'Name', key: 'name', sortable: true, width: '25%' },
  { title: 'Status', key: 'status', sortable: true, width: '12%' },
  { title: 'Product', key: 'product', sortable: false, width: '15%' },
  { title: 'Staged', key: 'staged', sortable: false, width: '10%', align: 'center' },
  { title: 'Created', key: 'created_at', sortable: true, width: '15%' },
  { title: 'Completed', key: 'completed_at', sortable: true, width: '15%', align: 'center' },
  { title: 'Actions', key: 'actions', sortable: false, width: '120px', align: 'center' },
  { title: '', key: 'menu', sortable: false, width: '50px', align: 'center' },
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
      p.id.toLowerCase().includes(query),
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
    completed: activeProductProjects.value.filter((p) => p.status === 'completed').length,
    cancelled: activeProductProjects.value.filter((p) => p.status === 'cancelled').length,
  }
})

// Deleted projects
const deletedProjects = computed(() => projectStore.deletedProjects)

const deletedCount = computed(() => deletedProjects.value.length)

// Helper function to determine if project is staged
// A project is considered "staged" if:
// 1. Has agents assigned (agent_count > 0), OR
// 2. staging_status field is set to 'staged'
const isProjectStaged = (project) => {
  return project.agent_count > 0 || project.staging_status === 'staged'
}

// Launch button visibility - only show when exactly 1 active project exists
const hasActiveProject = computed(() => {
  return activeProductProjects.value.filter((p) => p.status === 'active').length === 1
})

// Get the single active project
const activeProject = computed(() => {
  return activeProductProjects.value.find((p) => p.status === 'active')
})

// Format date with locale support (US: MM-DD-YYYY HH:MM, EU: DD-MM-YYYY HH:MM)
function formatDateShort(dateStr) {
  if (!dateStr) return '—'
  const date = new Date(dateStr)

  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const year = date.getFullYear()
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')

  const time = `${hours}:${minutes}`

  if (dateLocale.value === 'EU') {
    return `${day}-${month}-${year} ${time}`
  } else {
    return `${month}-${day}-${year} ${time}`
  }
}

// Toggle date locale between US and EU
function toggleDateLocale() {
  dateLocale.value = dateLocale.value === 'US' ? 'EU' : 'US'
  localStorage.setItem('dateLocale', dateLocale.value)
}

// Normalize status values for UI (e.g., legacy 'paused' -> 'inactive')
function normalizeStatus(status) {
  if (status === 'paused') {
    return 'inactive'
  }
  return status || 'inactive'
}

// Get color for status chip
function getStatusColor(status) {
  const colors = {
    active: 'success',
    inactive: 'grey',
    completed: 'info',
    cancelled: 'warning',
  }
  return colors[status] || 'default'
}

// Methods
// Handover 0062: Activate project
async function activateProject(projectId) {
  try {
    // Call the new activate endpoint
    await projectStore.activateProject(projectId)
    await projectStore.fetchProjects()
  } catch (error) {
    console.error('[PROJECTS] Error activating project:', error)
  }
}

// Handover 0062: Launch project
function launchProject(projectId) {
  // Navigate to Project Launch Panel
  router.push({ name: 'ProjectLaunch', params: { projectId }, query: { via: 'jobs' } })
}

// Handle row click to navigate to project
function handleRowClick(event, item) {
  if (item && item.id) {
    launchProject(item.id)
  }
}

// Show "Working" label when the currently launched project is executing
function isWorking(project) {
  try {
    if (!tabsStore || !tabsStore.currentProject) return false
    const current = tabsStore.currentProject
    const launched = tabsStore.isLaunched === true
    const sameId = current?.id === project.id || current?.project_id === project.id
    return launched && sameId
  } catch (e) {
    return false
  }
}

// Mission helper methods
function viewFullMission() {
  showMissionDialog.value = true
}

function clearMission() {
  if (confirm('Clear the mission? It will be regenerated on next staging.')) {
    projectData.value.mission = ''
  }
}

function editProject(project) {
  editingProject.value = project
  createdProjectId.value = null
  projectData.value = {
    name: project.name,
    description: project.description || '',
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

function confirmPurgeDeleted(project) {
  if (!project) return
  const confirmed = window.confirm(
    `Permanently delete "${project.name}"? This will remove associated data and cannot be undone.`,
  )
  if (!confirmed) return
  purgeDeletedProject(project)
}

async function purgeDeletedProject(project) {
  if (!project || purgingProjectId.value || purgingAllDeleted.value) return

  purgingProjectId.value = project.id
  try {
    await projectStore.purgeDeletedProject(project.id)
    if (projectStore.deletedProjects.length === 0) {
      showDeletedDialog.value = false
    }
  } catch (error) {
    console.error('Failed to purge deleted project:', error)
    alert('Failed to permanently delete the project. Please try again.')
  } finally {
    purgingProjectId.value = null
  }
}

async function confirmPurgeAllDeleted() {
  if (deletedProjects.value.length === 0 || purgingAllDeleted.value) return

  const confirmed = window.confirm(
    'Permanently delete all projects in the Deleted Projects list? This cannot be undone.',
  )
  if (!confirmed) return

  purgingAllDeleted.value = true
  try {
    await projectStore.purgeAllDeletedProjects()
    showDeletedDialog.value = false
  } catch (error) {
    console.error('Failed to purge all deleted projects:', error)
    alert('Failed to permanently delete deleted projects. Please try again.')
  } finally {
    purgingAllDeleted.value = false
    purgingProjectId.value = null
  }
}

async function handleStatusAction({ action, projectId }) {
  try {
    switch (action) {
      case 'activate':
        await projectStore.activateProject(projectId)
        break
      case 'deactivate':
        await projectStore.deactivateProject(projectId)
        break
      case 'complete': {
        // Open CloseoutModal instead of direct API call
        const projectToClose = projectStore.projectById(projectId)
        if (projectToClose) {
          closeoutProjectId.value = projectId
          closeoutProjectName.value = projectToClose.name
          showCloseoutModal.value = true
        }
        break
      }
      case 'reopen':
        await projectStore.restoreCompletedProject(projectId)
        break
      case 'cancel':
        await projectStore.cancelProject(projectId)
        break
      case 'delete': {
        const projectToDelete = projectStore.projectById(projectId)
        if (projectToDelete) {
          confirmDelete(projectToDelete)
        }
        break
      }
    }

    // Refresh project list to show updated status
    await projectStore.fetchProjects()
  } catch (error) {
    console.error('Failed to perform action:', error)
    // Refresh even on error to show true server state
    await projectStore.fetchProjects()
  }
}

// Handle CloseoutModal events
async function handleCloseoutComplete() {
  showCloseoutModal.value = false
  closeoutProjectId.value = null
  closeoutProjectName.value = ''
  await projectStore.fetchProjects()
}

function handleCloseoutClose() {
  showCloseoutModal.value = false
  closeoutProjectId.value = null
  closeoutProjectName.value = ''
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
    console.warn('[PROJECTS][CreateProject] Form is not valid', {
      projectData: projectData.value,
    })
    return
  }

  try {
    console.log('[PROJECTS][CreateProject] saveProject clicked', {
      editing: !!editingProject.value,
      activeProduct: activeProduct.value,
      projectData: projectData.value,
    })

    if (editingProject.value) {
      // Update existing project
      const updateData = {
        name: projectData.value.name,
        mission: projectData.value.mission,
        status: projectData.value.status,
      }

      console.log('[PROJECTS][CreateProject] update payload', updateData)

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

      console.log('[PROJECTS][CreateProject] create payload', createData)

      const result = await projectStore.createProject(createData)
      console.log('[PROJECTS][CreateProject] createProject result', result)
      createdProjectId.value = result.id

      await projectStore.fetchProjects()

      // Keep dialog open briefly to show success, then close and reset form
      setTimeout(() => {
        showCreateDialog.value = false
        createdProjectId.value = null
        resetForm()
        formValid.value = false
      }, 2000)
    }
  } catch (error) {
    console.error('[PROJECTS][CreateProject] Failed to save project:', error)
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
      projectStore.fetchDeletedProjects(),
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

.border-b {
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
}

.rounded {
  border-radius: 4px;
}

/* Scrollable project list container */
.project-list-container {
  height: calc(100vh - 520px);
  overflow-y: auto;
  overflow-x: hidden;
}

/* Ensure table headers are sticky */
.project-list-container :deep(.v-data-table__thead) {
  position: sticky;
  top: 0;
  z-index: 2;
  background-color: white;
}

/* Remove default table wrapper overflow to allow container scroll */
.project-list-container :deep(.v-table__wrapper) {
  overflow: visible !important;
}
</style>
