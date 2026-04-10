<template>
  <v-container>
    <!-- Header -->
    <v-row align="center" class="mb-4 main-window-reveal main-window-reveal--hero main-window-delay-1">
      <v-col>
        <h1 class="text-h4">Project Management</h1>
        <p class="text-body-2 text-muted-a11y mt-1">
          Use MCP tool /gil_add to have the AI coding agent add new projects to the Project dashboard.
          <v-tooltip location="bottom start" max-width="600">
            <template #activator="{ props }">
              <v-icon v-bind="props" size="16" class="help-icon">mdi-help-circle-outline</v-icon>
            </template>
            <div>
              <div class="font-weight-bold mb-1">Project Field Reference</div>
              <div class="text-caption mb-2 text-muted-a11y">Instructions for /gil_add</div>
              <div><span class="font-weight-medium">name (required):</span> Free text</div>
              <div class="mt-1"><span class="font-weight-medium">description (recommended):</span> Free text</div>
              <div class="mt-1"><span class="font-weight-medium">status (optional):</span></div>
              <div class="ml-2 text-caption">inactive · active · completed · cancelled · deleted</div>
              <div class="mt-2"><span class="font-weight-medium">project_type (optional):</span></div>
              <div class="text-caption text-center">Taxonomy category abbreviation (e.g. BE, FE, API)</div>
              <div class="mt-1"><span class="font-weight-medium">series_number (optional):</span></div>
              <div class="text-caption text-center">Sequential number within a type (e.g. 1 → BE-0001)</div>
              <div class="mt-1"><span class="font-weight-medium">subseries (optional):</span></div>
              <div class="text-caption text-center">Single-letter suffix (e.g. a → BE-0001a)</div>
              <div class="mt-2"><span class="font-weight-medium">Example:</span></div>
              <div class="ml-2 text-caption">/gil_add add project ... description ...</div>
            </div>
          </v-tooltip>
        </p>
      </v-col>
    </v-row>

    <!-- No Active Product Alert -->
    <v-alert v-if="!activeProduct" type="info" variant="tonal" class="ma-4 main-window-reveal main-window-delay-2" closable>
      No active product selected. Please activate a product to view and manage its projects.
    </v-alert>

    <!-- Filter Bar (0873: restyled to match TasksView pattern) -->
    <div v-if="activeProduct" class="filter-bar main-window-reveal main-window-delay-2">
      <v-text-field
        v-model="searchQuery"
        prepend-inner-icon="mdi-magnify"
        placeholder="Search projects..."
        variant="solo"
        density="compact"
        clearable
        hide-details
        flat
        aria-label="Search projects by name"
        class="filter-search"
      />
      <v-select
        v-model="filterStatus"
        :items="statusSelectOptions"
        placeholder="Status"
        variant="solo"
        density="compact"
        clearable
        hide-details
        flat
        class="filter-select"
      />
      <v-select
        v-if="projectTypes.length > 0"
        v-model="filterType"
        :items="typeSelectOptions"
        placeholder="Type"
        variant="solo"
        density="compact"
        clearable
        hide-details
        flat
        class="filter-select"
      />
      <v-btn variant="text" class="filter-clear-btn" @click="clearFilters">Clear Filters</v-btn>
      <v-btn
        color="primary"
        variant="flat"
        prepend-icon="mdi-plus"
        :disabled="!activeProduct"
        aria-label="Create new project"
        @click="showCreateDialog = true"
      >
        New Project
      </v-btn>
      <v-btn
        variant="outlined"
        prepend-icon="mdi-delete-restore"
        :disabled="deletedCount === 0"
        aria-label="View deleted projects"
        @click="showDeletedDialog = true"
      >
        Deleted ({{ deletedCount }})
      </v-btn>
    </div>

    <!-- Projects Table -->
    <v-card v-if="activeProduct" class="project-table-card smooth-border main-window-reveal main-window-delay-3">
      <!-- Scrollable Table Container -->
      <div class="project-list-container">
        <v-data-table
          :headers="headers"
          :items="sortedProjects"
          :loading="loading"
          :items-per-page="itemsPerPage"
          :page="currentPage"
          :sort-by="sortConfig"
          class="elevation-0"
          item-key="id"
          fixed-header
          :item-props="() => ({ 'data-testid': 'project-card' })"
          @update:page="currentPage = $event"
          @update:sort-by="sortConfig = $event"
          @click:row="handleRowClick"
        >
          <!-- Name Column -->
          <template v-slot:item.name="{ item }">
            <div class="py-2">
              <span class="project-name-text">{{ item.name }}</span>
              <div class="project-uuid-text project-id-text">
                Project ID: {{ item.id }}
              </div>
            </div>
          </template>

          <!-- Serial Column (colorized tinted badge) -->
          <template v-slot:item.serial="{ item }">
            <span
              v-if="item.taxonomy_alias"
              class="project-id-badge"
              :style="projectIdBadgeStyle(item.project_type?.color || DEFAULT_PROJECT_TYPE_COLOR)"
            >
              {{ item.taxonomy_alias }}
            </span>
            <span v-else class="staged-dash">—</span>
          </template>

          <!-- Quick Action Column — play button to activate + launch -->
          <template v-slot:item.quick_action="{ item }">
            <v-tooltip v-if="normalizeStatus(item.status) === 'inactive'" :text="isProjectStaged(item) ? 'Activate & resume' : 'Activate & launch'">
              <template #activator="{ props: ttProps }">
                <button
                  v-bind="ttProps"
                  type="button"
                  class="play-circle-btn icon-interactive-play"
                  aria-label="Activate project"
                  @click.stop="activateAndLaunch(item.id)"
                >
                  <v-icon size="18">mdi-play</v-icon>
                </button>
              </template>
            </v-tooltip>
          </template>

          <!-- Staged Column (0870h: tinted style) -->
          <template v-slot:item.staging_status="{ item }">
            <v-icon
              v-if="isProjectStaged(item)"
              size="18"
              style="color: var(--color-accent-success)"
              aria-label="Staged"
            >mdi-check</v-icon>
            <span v-else class="staged-dash">—</span>
          </template>

          <!-- Created Date Column (0870h: accessible muted text) -->
          <template v-slot:item.created_at="{ item }">
            <span class="date-full date-cell">{{ formatDate(item.created_at) }}</span>
            <span class="date-compact date-cell">{{ formatDateCompact(item.created_at) }}</span>
          </template>

          <!-- Completed Date Column (0870h: accessible muted text) -->
          <template v-slot:item.completed_at="{ item }">
            <div class="text-center">
              <template v-if="item.status === 'completed' || item.status === 'cancelled' || item.status === 'terminated'">
                <span class="date-full date-cell">{{ formatDate(item.completed_at || item.updated_at) }}</span>
                <span class="date-compact date-cell">{{ formatDateCompact(item.completed_at || item.updated_at) }}</span>
              </template>
              <template v-else><span class="date-cell date-cell--empty">—</span></template>
            </div>
          </template>

          <!-- Status Column (display-only badge; actions moved to ... menu) -->
          <template v-slot:item.status="{ item }">
            <div class="d-flex align-center justify-center">
              <!-- Full pill: desktop -->
              <span class="status-full">
                <StatusBadge :status="normalizeStatus(item.status)" />
              </span>
              <!-- Compact dot with initial: small viewports -->
              <v-tooltip :text="normalizeStatus(item.status)">
                <template #activator="{ props: ttProps }">
                  <span
                    v-bind="ttProps"
                    class="status-dot"
                    :style="{ backgroundColor: statusDotColor(normalizeStatus(item.status)) }"
                  >{{ normalizeStatus(item.status).charAt(0).toUpperCase() }}</span>
                </template>
              </v-tooltip>
            </div>
          </template>

          <!-- Actions Column (status actions + edit/delete menu) -->
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

                <v-list density="compact" min-width="180">
                  <!-- Status-aware actions -->
                  <v-list-item
                    v-for="sa in getStatusActions(item)"
                    :key="sa.key"
                    :prepend-icon="sa.icon"
                    :title="sa.label"
                    :class="sa.color ? `text-${sa.color}` : undefined"
                    @click="handleStatusAction({ action: sa.key, projectId: item.id })"
                  ></v-list-item>

                  <v-divider class="my-1" />

                  <!-- Edit (not available for completed/cancelled/terminated) -->
                  <v-list-item
                    v-if="!['completed', 'cancelled', 'terminated'].includes(normalizeStatus(item.status))"
                    prepend-icon="mdi-pencil"
                    title="Edit Project"
                    @click="editProject(item)"
                  ></v-list-item>
                  <!-- Duplicate -->
                  <v-list-item
                    prepend-icon="mdi-content-copy"
                    title="Duplicate"
                    @click="duplicateProject(item)"
                  ></v-list-item>
                  <v-divider class="my-1" />
                  <v-list-item
                    prepend-icon="mdi-delete"
                    title="Delete Project"
                    class="text-error"
                    @click="confirmDelete(item)"
                  ></v-list-item>
                </v-list>
              </v-menu>
            </div>
          </template>

          <!-- No data state -->
          <template v-slot:no-data>
            <div class="text-center py-8">
              <v-icon size="48" color="medium-emphasis" class="mb-4">mdi-folder-open</v-icon>
              <p class="text-body-2 text-muted-a11y">No projects found</p>
              <v-btn size="small" color="primary" class="mt-4" @click="showCreateDialog = true">
                Create First Project
              </v-btn>
            </div>
          </template>
        </v-data-table>
      </div>
    </v-card>

    <!-- Create/Edit Dialog -->
    <ProjectCreateEditDialog
      ref="createEditDialogRef"
      v-model="showCreateDialog"
      :editing-project="editingProject"
      :active-product="activeProduct"
      :project-types="projectTypes"
      @saved="onDialogSaved"
      @clear-mission="showClearMissionDialog = true"
      @type-created="onTypeCreated"
    />

    <!-- Delete Confirmation Dialog -->
    <BaseDialog
      v-model="showDeleteDialog"
      type="danger"
      title="Delete Project?"
      confirm-label="Delete"
      size="sm"
      @confirm="deleteProject"
      @cancel="showDeleteDialog = false"
    >
      <p class="mb-3">
        Are you sure you want to delete project <strong>"{{ projectToDelete?.name }}"</strong>?
      </p>
      <v-alert type="info" variant="tonal" density="compact">
        This will move the project to <strong>Deleted Projects</strong> for 10 days.
        It can be restored during that time. After 10 days it will be permanently purged.
      </v-alert>
    </BaseDialog>

    <!-- Clear Mission Confirmation Dialog -->
    <BaseDialog
      v-model="showClearMissionDialog"
      type="warning"
      title="Clear Mission?"
      confirm-label="Clear"
      size="sm"
      @confirm="onClearMissionConfirmed"
      @cancel="showClearMissionDialog = false"
    >
      <p>Clear the mission? It will be regenerated on next staging.</p>
    </BaseDialog>

    <!-- Purge Single Project Confirmation Dialog -->
    <BaseDialog
      v-model="showPurgeSingleDialog"
      type="danger"
      title="Permanently Delete Project?"
      confirm-label="Delete Forever"
      size="sm"
      @confirm="purgeDeletedProject(projectToPurge); showPurgeSingleDialog = false"
      @cancel="showPurgeSingleDialog = false"
    >
      <p class="mb-3">
        Permanently delete <strong>"{{ projectToPurge?.name }}"</strong>?
      </p>
      <v-alert type="error" variant="tonal" density="compact">
        This will remove all associated data and <strong>cannot be undone</strong>.
      </v-alert>
    </BaseDialog>

    <!-- Purge All Deleted Projects Confirmation Dialog -->
    <BaseDialog
      v-model="showPurgeAllDialog"
      type="danger"
      title="Permanently Delete All?"
      confirm-label="Delete All Forever"
      size="sm"
      @confirm="executePurgeAll"
      @cancel="showPurgeAllDialog = false"
    >
      <p class="mb-3">
        Permanently delete <strong>all {{ deletedProjects.length }}</strong> projects in the Deleted Projects list?
      </p>
      <v-alert type="error" variant="tonal" density="compact">
        This will remove all associated data and <strong>cannot be undone</strong>.
      </v-alert>
    </BaseDialog>

    <!-- Deleted Projects Dialog -->
    <ProjectDeletedDialog
      v-model="showDeletedDialog"
      :deleted-projects="deletedProjects"
      :purging-project-id="purgingProjectId"
      :purging-all-deleted="purgingAllDeleted"
      @restore="restoreFromDelete"
      @purge="confirmPurgeDeleted"
      @purge-all="confirmPurgeAllDeleted"
    />

    <!-- Manual Closeout Modal (for user-initiated project completion) -->
    <ManualCloseoutModal
      :show="showCloseoutModal"
      :project-id="closeoutProjectId"
      :project-name="closeoutProjectName"
      @close="handleCloseoutClose"
      @completed="handleCloseoutComplete"
    />

    <ProjectReviewModal
      :show="showReviewModal"
      :project-id="reviewProjectId"
      :product-id="reviewProductId"
      @close="showReviewModal = false; reviewProjectId = null; reviewProductId = null"
    />
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projects'
import { useProductStore } from '@/stores/products'
import { useNotificationStore } from '@/stores/notifications'
import StatusBadge from '@/components/StatusBadge.vue'
import ManualCloseoutModal from '@/components/orchestration/ManualCloseoutModal.vue'
import ProjectReviewModal from '@/components/projects/ProjectReviewModal.vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import ProjectCreateEditDialog from '@/components/projects/ProjectCreateEditDialog.vue'
import ProjectDeletedDialog from '@/components/projects/ProjectDeletedDialog.vue'
import { DEFAULT_PROJECT_TYPE_COLOR } from '@/utils/constants'
import api from '@/services/api'
import { useFormatDate } from '@/composables/useFormatDate'
import { useToast } from '@/composables/useToast'
import { useProjectFilters } from '@/composables/useProjectFilters'

// Router
const router = useRouter()

// Stores
const projectStore = useProjectStore()
const productStore = useProductStore()
const notificationStore = useNotificationStore()
const { showToast } = useToast()
const { formatDate, formatDateCompact } = useFormatDate()

// Dialog ref for imperative calls (e.g., clearMissionData)
const createEditDialogRef = ref(null)

// Dialog visibility
const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const showDeletedDialog = ref(false)
const showCloseoutModal = ref(false)
const showClearMissionDialog = ref(false)
const showPurgeSingleDialog = ref(false)
const showPurgeAllDialog = ref(false)
const showReviewModal = ref(false)

// Editing state
const editingProject = ref(null)
const projectToDelete = ref(null)
const projectToPurge = ref(null)

// Closeout / review state
const closeoutProjectId = ref(null)
const closeoutProjectName = ref('')
const reviewProjectId = ref(null)
const reviewProductId = ref(null)

// Purge state
const purgingProjectId = ref(null)
const purgingAllDeleted = ref(false)

// Project types (fetched on mount, shared with create/edit dialog)
const projectTypes = ref([])

// Store computeds
const activeProduct = computed(() => productStore.activeProduct)
const projects = computed(() => projectStore.projects)
const loading = computed(() => projectStore.loading)
const deletedProjects = computed(() => projectStore.deletedProjects)
const deletedCount = computed(() => deletedProjects.value.length)

// Filters composable
const {
  searchQuery,
  filterType,
  filterStatus,
  currentPage,
  itemsPerPage,
  sortConfig,
  typeSelectOptions,
  // eslint-disable-next-line no-unused-vars -- exposed on vm for test assertions
  activeProductProjects,
  // eslint-disable-next-line no-unused-vars -- exposed on vm for test assertions
  filteredBySearch,
  // eslint-disable-next-line no-unused-vars -- exposed on vm for test assertions
  filteredProjects,
  sortedProjects,
  clearFilters,
} = useProjectFilters({ projects, projectTypes, activeProduct })

// 0873: v-select items for filter bar dropdowns
const statusSelectOptions = ['active', 'inactive', 'completed', 'cancelled', 'terminated']

// Table headers
const headers = [
  { title: 'Serial', key: 'serial', sortable: true, width: '10%' },
  { title: 'Name', key: 'name', sortable: true, width: '28%' },
  { title: 'Status', key: 'status', sortable: true, width: '13%', align: 'center' },
  { title: 'Staged', key: 'staging_status', sortable: true, width: '9%', align: 'center' },
  { title: 'Created', key: 'created_at', sortable: true, width: '13%' },
  { title: 'Completed', key: 'completed_at', sortable: true, width: '13%', align: 'center' },
  { title: 'Actions', key: 'quick_action', sortable: false, width: '5%', align: 'center' },
  { title: '', key: 'menu', sortable: false, width: '3%', align: 'center' },
]

/* 0870h: tinted square badge style for project taxonomy IDs */
function projectIdBadgeStyle(color) {
  return {
    backgroundColor: `${color}26`,
    color: color,
  }
}

// Status dot colors — traced to design-tokens.scss
const DOT_SURFACE = '#ffffff'
const DOT_MUTED = '#9e9e9e'
const DOT_SUCCESS = '#4caf50'
const DOT_WARNING = '#fb8c00'
const DOT_ERROR = '#f44336'

function statusDotColor(status) {
  const colors = {
    active: DOT_SURFACE,
    inactive: DOT_MUTED,
    completed: DOT_SUCCESS,
    cancelled: DOT_WARNING,
    terminated: DOT_ERROR,
    deleted: DOT_ERROR,
  }
  return colors[status] || DOT_MUTED
}

// Helper: is project staged?
const isProjectStaged = (project) =>
  project.staging_status === 'staged' || project.staging_status === 'staging_complete'

// Normalize legacy status values
function normalizeStatus(status) {
  if (status === 'paused') return 'inactive'
  return status || 'inactive'
}

// Status action definitions for the "..." menu
const statusActionDefs = {
  activate: { label: 'Activate', icon: 'mdi-play-circle', color: 'success', confirm: false },
  deactivate: { label: 'Deactivate', icon: 'mdi-pause-circle', color: null, confirm: true },
  complete: { label: 'Complete', icon: 'mdi-check-circle', color: null, confirm: true },
  cancel: { label: 'Cancel Project', icon: 'mdi-cancel', color: 'warning', confirm: true },
  reopen: { label: 'Reopen', icon: 'mdi-refresh', color: 'success', confirm: false },
  review: { label: 'Review', icon: 'mdi-eye', color: null, confirm: false },
}

const actionsByStatus = {
  inactive: ['activate', 'complete', 'cancel'],
  active: ['deactivate', 'complete', 'cancel'],
  completed: ['review'],
  cancelled: ['review'],
  terminated: ['review'],
}

function getStatusActions(item) {
  const normalized = normalizeStatus(item.status)
  const keys = [...(actionsByStatus[normalized] || [])]
  if (normalized === 'cancelled' && !isProjectStaged(item)) {
    keys.unshift('reopen')
  }
  return keys.map((key) => ({ key, ...statusActionDefs[key] }))
}

// Activate project and navigate to its jobs page
async function activateAndLaunch(projectId) {
  await projectStore.activateProject(projectId)
  const project = projectStore.projects.find((p) => p.id === projectId)
  const staged = project && isProjectStaged(project)
  router.push({ name: 'ProjectLaunch', params: { projectId }, query: { via: 'jobs', ...(staged ? { tab: 'jobs' } : {}) } })
}

// Handle row click — completed projects open review summary, others open edit modal
function handleRowClick(event, row) {
  const item = row?.item
  if (!item?.id) return
  const status = normalizeStatus(item.status)
  if (status === 'completed') {
    reviewProjectId.value = item.id
    reviewProductId.value = item.product_id
    showReviewModal.value = true
  } else {
    editProject(item)
  }
}

async function editProject(project) {
  editingProject.value = project
  showCreateDialog.value = true
}

async function duplicateProject(project) {
  try {
    const createData = {
      name: project.name,
      description: `${project.description || ''} #2`.trim(),
      mission: '',
      status: 'inactive',
      project_type_id: null,
      series_number: null,
      subseries: null,
      product_id: activeProduct.value?.id,
    }
    await projectStore.createProject(createData)
    await projectStore.fetchProjects()
    showToast({ message: `Duplicated project "${project.name}"`, type: 'success' })
  } catch (error) {
    console.error('[PROJECTS] Failed to duplicate project:', error)
    showToast({ message: error.response?.data?.detail || 'Failed to duplicate project', type: 'error' })
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
      showToast({ message: 'Failed to delete project. Please try again.', type: 'error' })
    }
  }
}

async function restoreFromDelete(project) {
  try {
    await projectStore.restoreProject(project.id)
    showDeletedDialog.value = false
  } catch (error) {
    console.error('Failed to restore project:', error)
    showToast({ message: 'Failed to restore project. Please try again.', type: 'error' })
  }
}

function confirmPurgeDeleted(project) {
  if (!project) return
  projectToPurge.value = project
  showPurgeSingleDialog.value = true
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
    showToast({ message: 'Failed to permanently delete the project. Please try again.', type: 'error' })
  } finally {
    purgingProjectId.value = null
  }
}

function confirmPurgeAllDeleted() {
  if (deletedProjects.value.length === 0 || purgingAllDeleted.value) return
  showPurgeAllDialog.value = true
}

async function executePurgeAll() {
  showPurgeAllDialog.value = false
  purgingAllDeleted.value = true
  try {
    await projectStore.purgeAllDeletedProjects()
    showDeletedDialog.value = false
  } catch (error) {
    console.error('Failed to purge all deleted projects:', error)
    showToast({ message: 'Failed to purge deleted projects. Please try again.', type: 'error' })
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
        const projectToClose = projectStore.projectById(projectId)
        if (projectToClose) {
          closeoutProjectId.value = projectId
          closeoutProjectName.value = projectToClose.name
          showCloseoutModal.value = true
        }
        break
      }
      case 'review': {
        const projectToReview = projectStore.projectById(projectId)
        reviewProjectId.value = projectId
        reviewProductId.value = projectToReview?.product_id
        showReviewModal.value = true
        break
      }
      case 'reopen':
        await api.projects.restore(projectId)
        break
      case 'cancel':
        await projectStore.cancelProject(projectId)
        notificationStore.clearForProject(projectId)
        break
      case 'delete': {
        const projectToDeleteById = projectStore.projectById(projectId)
        if (projectToDeleteById) {
          confirmDelete(projectToDeleteById)
        }
        break
      }
    }
    await projectStore.fetchProjects()
  } catch (error) {
    console.error('Failed to perform action:', error)
    showToast({ message: 'Failed to update project status. Try refreshing the page to get the latest state.', type: 'error' })
    await projectStore.fetchProjects()
  }
}

async function handleCloseoutComplete() {
  const projectIdToClear = closeoutProjectId.value
  showCloseoutModal.value = false
  closeoutProjectId.value = null
  closeoutProjectName.value = ''
  notificationStore.clearForProject(projectIdToClear)
  await projectStore.fetchProjects()
}

function handleCloseoutClose() {
  showCloseoutModal.value = false
  closeoutProjectId.value = null
  closeoutProjectName.value = ''
}

function onDialogSaved() {
  editingProject.value = null
}

function onClearMissionConfirmed() {
  createEditDialogRef.value?.clearMissionData()
  showClearMissionDialog.value = false
}

function onTypeCreated() {
  // No-op: useProjectTaxonomy.handleTypeCreated already pushes to projectTypes
}

// Lifecycle
onMounted(async () => {
  try {
    await Promise.all([
      productStore.fetchProducts(),
      productStore.fetchActiveProduct(),
      projectStore.fetchProjects(),
      projectStore.fetchDeletedProjects(),
    ])
    try {
      const typesResponse = await api.projectTypes.list()
      projectTypes.value = typesResponse.data || []
    } catch {
      console.error('Failed to load project types')
    }
  } catch (error) {
    console.error('Failed to load data:', error)
  }
})
</script>

<style lang="scss" scoped>
@use '../styles/variables' as *;
@use '../styles/design-tokens' as *;

/* CSS custom properties for template-level token references */
:deep(.v-container) {
  --color-status-success: #{$color-status-success};
  --color-text-muted: #{$color-text-muted};
}

/* 0873: smooth-border table panel */
.project-table-card {
  border: none !important;
  border-radius: $border-radius-rounded !important;
  overflow: hidden;

  :deep(.v-table) {
    background: transparent;
  }

  :deep(.v-data-table__th) {
    background: transparent !important;
  }
}

/* 0873: filter bar layout (matches TasksView pattern) */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.filter-search {
  flex: 1;
}

/* Help icon on subtitle (Handover 0875) */
.help-icon {
  color: rgba(255, 255, 255, 0.5);
  cursor: help;
  vertical-align: middle;
  margin-left: 4px;
}

.filter-search :deep(.v-field) {
  box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255, 255, 255, 0.10));
  border-radius: $border-radius-default;
}

.filter-search :deep(.v-field:focus-within) {
  box-shadow: inset 0 0 0 1px rgba($color-brand-yellow, 0.3);
}

.filter-select {
  flex: 0 0 160px;
}

.filter-select :deep(.v-field) {
  box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255, 255, 255, 0.10));
  border-radius: $border-radius-default;
}

.filter-clear-btn {
  color: $color-text-muted !important;
  font-size: 0.72rem;
  text-transform: none;
  letter-spacing: 0;
}

/* Clickable rows — entire row opens edit/review */
:deep(.v-data-table__tr) {
  cursor: pointer;
  transition: background $transition-fast;
}

:deep(.v-data-table__tr:hover) {
  background: rgba(255, 255, 255, 0.02) !important;
}

/* 0870h: table header styling */
:deep(.v-data-table__thead th) {
  @include table-header-label;
  border-bottom: 1px solid $color-border-subtle !important;
}

/* 0870h: table cell row separators */
:deep(.v-data-table__td) {
  @include table-row-separator;
}

:deep(.v-data-table__tr:last-child .v-data-table__td) {
  border-bottom: none !important;
}

/* Project list container — no height constraint, browser scrollbar handles overflow */
.project-list-container {
  overflow: visible;
}

/* Remove default table wrapper overflow so table expands fully */
.project-list-container :deep(.v-table__wrapper) {
  overflow: visible;
}

/* 0870h: Square tinted project ID badge */
.project-id-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: $border-radius-sharp;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.62rem;
  font-weight: 600;
}

/* 0870h: Project name text */
.project-name-text {
  font-size: 0.82rem;
  font-weight: 500;
}

/* 0870h: Project UUID text — accessible muted color */
.project-uuid-text {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.58rem;
  color: var(--text-muted, #{$color-text-muted});
  margin-top: 2px;
}

/* 0870h: Date cell styling */
.date-cell {
  font-size: 0.72rem;
  color: var(--text-secondary, #{$color-text-secondary});
  white-space: nowrap;
}

.date-cell--empty {
  color: var(--text-muted, #{$color-text-muted});
}

/* Staged column: check or dash (Handover 0875) */
.staged-dash {
  color: var(--text-muted);
  font-size: 0.85rem;
}

/* Force center alignment on Staged column cells (3rd column) */
.project-table-card :deep(td:nth-child(3)) {
  text-align: center;
}

/* Play-circle activate button — uses global .icon-interactive-play */
.play-circle-btn {
  width: 32px;
  height: 32px;
  border: none !important;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.play-circle-btn :deep(.v-icon) {
  color: $color-brand-yellow;
}

/* ── Responsive compact elements (hidden by default, shown via media queries) ── */
.status-dot,
.date-compact {
  display: none;
}

/* Status compact dot with initial letter */
.status-dot {
  width: 22px;
  height: 22px;
  min-width: 22px;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 700;
  color: $darkest-blue;
  line-height: 22px;
  text-align: center;
}

/* ── Compact breakpoint (≤1280px): collapse badges to dots, dates to DD/MM/YY ── */
/* At 1200px with sidebar open (~160px), content area is ~1040px and badges overflow */
@media (max-width: 1280px) {
  .status-full,
  .date-full {
    display: none !important;
  }
  .status-dot,
  .date-compact {
    display: inline-block;
  }
  .project-id-text {
    display: none;
  }
}

/* ── Mobile breakpoint (≤600px): further tighten ── */
@media (max-width: 600px) {
  .project-id-text {
    display: none;
  }
}

/* 0873: responsive filter bar */
@media (max-width: 960px) {
  .filter-bar {
    flex-wrap: wrap;
  }
  .filter-search {
    max-width: 100%;
  }
}
</style>
