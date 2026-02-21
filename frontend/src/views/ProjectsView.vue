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
              <v-icon size="32" color="info" class="mr-3">mdi-clipboard-check</v-icon>
              <div>
                <div class="text-caption">Completed</div>
                <div class="text-h5">{{ statusCounts.completed }}</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon size="32" color="warning" class="mr-3">mdi-progress-clock</v-icon>
              <div>
                <div class="text-caption">Staged</div>
                <div class="text-h5">{{ statusCounts.staged }}</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon size="32" color="error" class="mr-3">mdi-cancel</v-icon>
              <div>
                <div class="text-caption">Cancelled</div>
                <div class="text-h5">{{ statusCounts.cancelled }}</div>
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
            :aria-label="`Filter by ${status.label}`"
            class="cursor-pointer"
            @click="filterStatus = status.value"
          >
            {{ status.label }} ({{ status.count }})
          </v-chip>
        </div>

        <!-- Type Filter Chips (Handover 0440c) -->
        <div v-if="projectTypes.length > 0" class="d-flex gap-2 flex-wrap align-center mt-3">
          <span class="text-caption text-medium-emphasis mr-2">Type:</span>
          <v-chip
            :color="filterType === 'all' ? 'primary' : 'default'"
            :variant="filterType === 'all' ? 'tonal' : 'outlined'"
            size="small"
            class="cursor-pointer"
            @click="filterType = 'all'"
          >
            All
          </v-chip>
          <v-chip
            v-for="ptype in projectTypes"
            :key="ptype.id"
            :color="filterType === ptype.id ? ptype.color : 'default'"
            :variant="filterType === ptype.id ? 'flat' : 'outlined'"
            size="small"
            class="cursor-pointer"
            @click="filterType = ptype.id"
          >
            {{ ptype.abbreviation }}
          </v-chip>
          <v-chip
            :color="filterType === 'none' ? 'grey' : 'default'"
            :variant="filterType === 'none' ? 'tonal' : 'outlined'"
            size="small"
            class="cursor-pointer"
            @click="filterType = 'none'"
          >
            No Type
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
            :title="isWorking(activeProject) ? 'View running jobs' : 'Launch active project'"
            @click="launchProject(activeProject.id)"
          >
            {{ isWorking(activeProject) ? 'Working' : 'Launch Project' }}
          </v-btn>

          <v-divider v-if="hasActiveProject" vertical class="mx-1" style="height: 24px" />

          <!-- New Project Button -->
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

          <!-- Deleted Projects Button -->
          <v-btn
            variant="outlined"
            prepend-icon="mdi-delete-restore"
            :disabled="deletedCount === 0"
            aria-label="View deleted projects"
            @click="showDeletedDialog = true"
          >
            Deleted ({{ deletedCount }})
          </v-btn>

          <v-divider vertical class="mx-1" style="height: 24px" />

          <!-- Date Format Toggle -->
          <v-btn
            variant="outlined"
            :title="`Switch to ${dateLocale === 'US' ? 'EU' : 'US'} date format`"
            prepend-icon="mdi-calendar"
            @click="toggleDateLocale"
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
          :sort-by="sortConfig"
          class="elevation-0"
          item-key="id"
          fixed-header
          :item-props="() => ({ 'data-testid': 'project-card' })"
          @update:page="currentPage = $event"
          @update:sort-by="sortConfig = $event"
          @click:row="handleRowClick"
        >
          <!-- Name Column with ID and Taxonomy Chip (Handover 0440c) -->
          <template v-slot:item.name="{ item }">
            <div class="py-2">
              <div class="d-flex align-center">
                <v-chip
                  v-if="item.taxonomy_alias && item.series_number"
                  :color="item.project_type?.color || '#607D8B'"
                  size="x-small"
                  variant="flat"
                  class="mr-2"
                  :title="item.project_type?.label || 'Untyped'"
                >
                  {{ item.taxonomy_alias }}
                </v-chip>
                <span
                  class="font-weight-bold text-body-2 project-name-link"
                  @click.stop="editProject(item)"
                >
                  {{ item.name }}
                </span>
              </div>
              <div class="text-caption text-medium-emphasis" style="font-family: monospace">
                Project ID: {{ item.id }}
              </div>
            </div>
          </template>

          <!-- Product Column -->
          <template v-slot:item.product="{ item }">
            <span class="text-caption project-name-link" @click.stop="router.push('/products')">
              {{ activeProduct?.name || '—' }}
            </span>
          </template>

          <!-- Staged Column -->
          <template v-slot:item.staging_status="{ item }">
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

          <!-- Status Column (StatusBadge with actions dropdown) -->
          <template v-slot:item.status="{ item }">
            <div class="d-flex align-center justify-center">
              <StatusBadge
                :status="normalizeStatus(item.status)"
                :project-id="item.id"
                @action="handleStatusAction"
              />
            </div>
          </template>

          <!-- Actions Column (edit/delete menu) -->
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
                    prepend-icon="mdi-pencil"
                    title="Edit Project"
                    @click="editProject(item)"
                  ></v-list-item>
                  <v-divider class="my-1" />
                  <v-list-item
                    prepend-icon="mdi-delete"
                    title="Delete Project"
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
              <p class="text-body-2 text-medium-emphasis">No projects found</p>
              <v-btn size="small" color="primary" class="mt-4" @click="showCreateDialog = true">
                Create First Project
              </v-btn>
            </div>
          </template>
        </v-data-table>
      </div>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="showCreateDialog" max-width="800" persistent retain-focus>
      <v-card v-draggable>
        <v-card-title class="d-flex align-center">
          <span>{{ editingProject ? 'Edit Project' : 'Create New Project' }}</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" aria-label="Close dialog" @click="cancelEdit" />
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
            <!-- Taxonomy Row: Type | Serial # | Suffix (Handover 0440c) -->
            <v-row dense class="mb-1" align="start">
              <!-- Type Dropdown -->
              <v-col cols="5">
                <v-select
                  v-model="projectData.project_type_id"
                  :items="typeDropdownItems"
                  label="Type"
                  item-title="display"
                  item-value="id"
                  density="compact"
                  variant="outlined"
                  clearable
                  hide-details
                  aria-label="Project type"
                  @update:model-value="handleTypeChange"
                >
                  <template #item="{ props: itemProps, item }">
                    <v-list-item v-if="item.raw.id === '__add_custom__'" v-bind="itemProps" @click.stop="showAddTypeModal = true">
                      <template #prepend>
                        <v-icon size="small">mdi-plus-circle</v-icon>
                      </template>
                    </v-list-item>
                    <v-list-item v-else v-bind="itemProps">
                      <template #prepend>
                        <div :style="{ backgroundColor: item.raw.color, width: '12px', height: '12px', borderRadius: '50%' }" />
                      </template>
                    </v-list-item>
                  </template>
                  <template #selection="{ item }">
                    <div class="d-flex align-center">
                      <div :style="{ backgroundColor: item.raw.color, width: '10px', height: '10px', borderRadius: '50%', marginRight: '6px' }" />
                      {{ item.raw.abbreviation }}
                    </div>
                  </template>
                </v-select>
              </v-col>

              <!-- Serial Number Text Input -->
              <v-col cols="4">
                <v-text-field
                  v-model="seriesNumberInput"
                  label="Serial #"
                  density="compact"
                  variant="outlined"
                  :disabled="!projectData.project_type_id"
                  :error="seriesCheckResult === false"
                  :color="seriesCheckResult === true ? 'success' : undefined"
                  :messages="seriesCheckMessage"
                  :loading="seriesChecking"
                  placeholder="0001"
                  aria-label="Series number"
                  @update:model-value="onSeriesInput"
                >
                  <template #append-inner>
                    <v-icon v-if="seriesCheckResult === true" color="success" size="small">mdi-check-circle</v-icon>
                    <v-icon v-else-if="seriesCheckResult === false" color="error" size="small">mdi-close-circle</v-icon>
                  </template>
                </v-text-field>
              </v-col>

              <!-- Suffix Dropdown (only shows available letters) -->
              <v-col cols="3">
                <v-select
                  v-model="projectData.subseries"
                  :items="subseriesItems"
                  label="Suffix"
                  item-title="title"
                  item-value="value"
                  density="compact"
                  variant="outlined"
                  clearable
                  hide-details
                  :disabled="!projectData.series_number"
                  aria-label="Subseries suffix"
                  @update:model-value="onSubseriesChange"
                />
              </v-col>
            </v-row>

            <!-- Project Name with taxonomy prefix -->
            <v-text-field
              v-model="projectData.name"
              label="Project Name"
              :rules="[(v) => !!v || 'Name is required']"
              required
              density="compact"
              variant="outlined"
              hide-details="auto"
              class="mb-3"
              aria-label="Project name"
            >
              <template v-if="taxonomyPrefix" #prepend-inner>
                <span class="text-caption font-weight-bold text-medium-emphasis mr-1" style="white-space: nowrap;">{{ taxonomyPrefix }}</span>
              </template>
            </v-text-field>

            <v-textarea
              v-model="projectData.description"
              label="Project Description"
              :rules="[(v) => !!v || 'Description is required']"
              hint="User-written description of what you want to accomplish. This will be shown to the orchestrator."
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
                    <v-list-item :disabled="!projectData.mission" @click="viewFullMission">
                      <v-list-item-title>View Full Mission</v-list-item-title>
                    </v-list-item>
                    <v-list-item :disabled="!projectData.mission" @click="clearMission">
                      <v-list-item-title>Clear Mission</v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-menu>
              </template>
            </v-textarea>

            <!-- Status removed - always defaults to inactive (Handover 0062) -->
          </v-form>

          <!-- Add Type Modal (Handover 0440c) -->
          <AddTypeModal v-model="showAddTypeModal" @type-created="handleTypeCreated" />
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

    <!-- Deleted Projects Modal -->
    <v-dialog v-model="showDeletedDialog" max-width="800" persistent retain-focus>
      <v-card v-draggable>
        <v-card-title class="d-flex align-center">
          <span>Deleted Projects ({{ deletedProjects.length }})</span>
          <v-spacer />
          <v-btn
            icon="mdi-close"
            variant="text"
            aria-label="Close dialog"
            @click="showDeletedDialog = false"
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
                    :disabled="purgingProjectId === project.id || purgingAllDeleted"
                    title="Restore project"
                    aria-label="Restore deleted project"
                    @click="restoreFromDelete(project)"
                  ></v-btn>
                  <v-btn
                    icon="mdi-trash-can"
                    size="small"
                    variant="text"
                    color="error"
                    :loading="purgingProjectId === project.id"
                    :disabled="purgingAllDeleted"
                    title="Permanently delete project"
                    aria-label="Permanently delete project"
                    data-testid="purge-project"
                    @click="confirmPurgeDeleted(project)"
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
            data-testid="purge-projects-all"
            @click="confirmPurgeAllDeleted"
          >
            Delete All
          </v-btn>
          <v-btn variant="text" @click="showDeletedDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Mission Viewer Dialog -->
    <v-dialog v-model="showMissionDialog" max-width="800" persistent retain-focus>
      <v-card v-draggable>
        <v-card-title class="d-flex align-center">
          <span>Full Mission Text</span>
          <v-spacer />
          <v-btn
            icon="mdi-close"
            variant="text"
            aria-label="Close dialog"
            @click="showMissionDialog = false"
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

    <!-- Manual Closeout Modal (for user-initiated project completion) -->
    <ManualCloseoutModal
      :show="showCloseoutModal"
      :project-id="closeoutProjectId"
      :project-name="closeoutProjectName"
      @close="handleCloseoutClose"
      @completed="handleCloseoutComplete"
    />
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projects'
import { useProductStore } from '@/stores/products'
import { useAgentStore } from '@/stores/agents'
import { useProjectTabsStore } from '@/stores/projectTabs'
import StatusBadge from '@/components/StatusBadge.vue'
import ManualCloseoutModal from '@/components/orchestration/ManualCloseoutModal.vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import AddTypeModal from '@/components/projects/AddTypeModal.vue'
import api from '@/services/api'

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
const filterType = ref('all')  // Handover 0440c: Type filter
const projectTypes = ref([])  // Handover 0440c: Available project types
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
  status: 'inactive',
  project_type_id: null,
  series_number: null,
  subseries: null,
})

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
  { title: 'Name', key: 'name', sortable: true, width: '24%' },
  { title: 'Product', key: 'product', sortable: false, width: '12%' },
  { title: 'Staged', key: 'staging_status', sortable: true, width: '12%' },
  { title: 'Created', key: 'created_at', sortable: true, width: '14%' },
  { title: 'Completed', key: 'completed_at', sortable: true, width: '14%', align: 'center' },
  { title: 'Status', key: 'status', sortable: true, width: '13%', align: 'center' },
  { title: 'Actions', key: 'menu', sortable: false, width: '11%', align: 'center' },
]

// --- Inline taxonomy state and logic (Handover 0440c) ---
const showAddTypeModal = ref(false)
const seriesNumberInput = ref('')
const seriesChecking = ref(false)
const seriesCheckResult = ref(null) // null = unchecked, true = available, false = taken
const seriesCheckMessage = ref('')
const usedSubseries = ref([]) // letters already taken for current type+serial
let seriesCheckTimer = null

// Type dropdown items (with "Add custom type..." appended)
const typeDropdownItems = computed(() => {
  const items = projectTypes.value.map((t) => ({
    id: t.id,
    display: `${t.abbreviation} - ${t.label}`,
    abbreviation: t.abbreviation,
    color: t.color,
  }))
  items.push({ id: '__add_custom__', display: 'Add custom type...', color: 'transparent', abbreviation: '' })
  return items
})

// Subseries items (a-z, excluding already-used letters)
const subseriesItems = computed(() => {
  const items = []
  for (let i = 0; i < 26; i++) {
    const letter = String.fromCharCode(97 + i)
    if (!usedSubseries.value.includes(letter)) {
      items.push({ title: letter, value: letter })
    }
  }
  return items
})

// Taxonomy prefix shown in project name field (e.g. "FEAT-0440c")
const taxonomyPrefix = computed(() => {
  const typeId = projectData.value.project_type_id
  const serial = projectData.value.series_number
  if (!typeId || !serial) return ''
  const type = projectTypes.value.find((t) => t.id === typeId)
  if (!type) return ''
  const padded = String(serial).padStart(4, '0')
  const suffix = projectData.value.subseries || ''
  return `${type.abbreviation}-${padded}${suffix}`
})

// Handle type change: reset series + subseries
function handleTypeChange(typeId) {
  if (typeId === '__add_custom__') {
    showAddTypeModal.value = true
    projectData.value.project_type_id = null
    return
  }
  projectData.value.series_number = null
  projectData.value.subseries = null
  seriesNumberInput.value = ''
  seriesCheckResult.value = null
  seriesCheckMessage.value = ''
  usedSubseries.value = []
}

// Handle type created from AddTypeModal
function handleTypeCreated(newType) {
  projectTypes.value.push(newType)
  projectData.value.project_type_id = newType.id
  projectData.value.series_number = null
  projectData.value.subseries = null
  seriesNumberInput.value = ''
  usedSubseries.value = []
}

// Debounced series number input handler
function onSeriesInput(val) {
  if (seriesCheckTimer) clearTimeout(seriesCheckTimer)

  const trimmed = (val || '').trim()
  if (!trimmed) {
    projectData.value.series_number = null
    projectData.value.subseries = null
    usedSubseries.value = []
    seriesCheckResult.value = null
    seriesCheckMessage.value = ''
    return
  }

  const num = parseInt(trimmed, 10)
  if (isNaN(num) || num < 1 || num > 9999) {
    projectData.value.series_number = null
    projectData.value.subseries = null
    usedSubseries.value = []
    seriesCheckResult.value = false
    seriesCheckMessage.value = 'Enter 1-9999'
    return
  }

  projectData.value.series_number = num
  projectData.value.subseries = null

  seriesChecking.value = true
  seriesCheckTimer = setTimeout(() => checkSeriesAvailability(num), 300)
}

// API call to check series availability + fetch used subseries
async function checkSeriesAvailability(num) {
  if (!projectData.value.project_type_id || !num) {
    seriesChecking.value = false
    return
  }
  const excludeId = editingProject.value?.id || null
  try {
    const [checkRes, usedRes] = await Promise.all([
      api.projects.checkSeries(
        projectData.value.project_type_id,
        num,
        projectData.value.subseries,
        excludeId,
      ),
      api.projects.usedSubseries(
        projectData.value.project_type_id,
        num,
        excludeId,
      ),
    ])
    seriesCheckResult.value = checkRes.data.available
    seriesCheckMessage.value = checkRes.data.available
      ? `${String(num).padStart(4, '0')} available`
      : `${String(num).padStart(4, '0')} taken`
    usedSubseries.value = usedRes.data.used_subseries || []
  } catch {
    seriesCheckResult.value = null
    seriesCheckMessage.value = ''
    usedSubseries.value = []
  } finally {
    seriesChecking.value = false
  }
}

// Re-check when subseries changes
function onSubseriesChange() {
  if (projectData.value.series_number && projectData.value.project_type_id) {
    if (seriesCheckTimer) clearTimeout(seriesCheckTimer)
    seriesChecking.value = true
    seriesCheckTimer = setTimeout(
      () => checkSeriesAvailability(projectData.value.series_number),
      300,
    )
  }
}

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
  let results = activeProductProjects.value

  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    results = results.filter(
      (p) =>
        p.name.toLowerCase().includes(query) ||
        p.mission?.toLowerCase().includes(query) ||
        p.id.toLowerCase().includes(query) ||
        p.taxonomy_alias?.toLowerCase().includes(query),
    )
  }

  // Type filter (Handover 0440c)
  if (filterType.value !== 'all') {
    if (filterType.value === 'none') {
      results = results.filter((p) => !p.project_type_id)
    } else {
      results = results.filter((p) => p.project_type_id === filterType.value)
    }
  }

  return results
})

// Filter by status
const filteredProjects = computed(() => {
  if (filterStatus.value === 'all') return filteredBySearch.value
  return filteredBySearch.value.filter((p) => p.status === filterStatus.value)
})

// Sort projects - active projects always on top (Handover 0440c: series-aware sorting)
const sortedProjects = computed(() => {
  const sorted = [...filteredProjects.value]

  sorted.sort((a, b) => {
    // Active projects always come first
    const aActive = a.status === 'active' ? 0 : 1
    const bActive = b.status === 'active' ? 0 : 1
    if (aActive !== bActive) return aActive - bActive

    // Then apply user-selected sort
    if (sortConfig.value && sortConfig.value.length > 0) {
      const { key, order } = sortConfig.value[0]
      const isAsc = order === 'asc'

      // Series-aware sorting (Handover 0440c)
      if (key === 'name') {
        // Sort by: type abbreviation -> series number -> subseries -> name
        const aType = a.project_type?.abbreviation || 'ZZZ'
        const bType = b.project_type?.abbreviation || 'ZZZ'
        if (aType !== bType) {
          return isAsc ? aType.localeCompare(bType) : bType.localeCompare(aType)
        }

        const aSeries = a.series_number || 99999
        const bSeries = b.series_number || 99999
        if (aSeries !== bSeries) {
          return isAsc ? aSeries - bSeries : bSeries - aSeries
        }

        const aSub = a.subseries || ''
        const bSub = b.subseries || ''
        if (aSub !== bSub) {
          return isAsc ? aSub.localeCompare(bSub) : bSub.localeCompare(aSub)
        }

        // Fall through to name comparison
        const aName = a.name.toLowerCase()
        const bName = b.name.toLowerCase()
        return isAsc ? aName.localeCompare(bName) : bName.localeCompare(aName)
      }

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
    }

    return 0
  })

  return sorted
})

// Count projects by status
const statusCounts = computed(() => {
  return {
    active: activeProductProjects.value.filter((p) => p.status === 'active').length,
    inactive: activeProductProjects.value.filter((p) => p.status === 'inactive').length,
    completed: activeProductProjects.value.filter((p) => p.status === 'completed').length,
    cancelled: activeProductProjects.value.filter((p) => p.status === 'cancelled').length,
    staged: activeProductProjects.value.filter((p) => p.staging_status === 'staged').length,
  }
})

// Deleted projects
const deletedProjects = computed(() => projectStore.deletedProjects)

const deletedCount = computed(() => deletedProjects.value.length)

// Helper function to determine if project is staged
// Uses staging_status from database for persistence across refresh/restart
const isProjectStaged = (project) => {
  return project.staging_status === 'staged'
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
    status: project.status,
    project_type_id: project.project_type_id || null,
    series_number: project.series_number || null,
    subseries: project.subseries || null,
  }
  // Populate inline taxonomy state (Handover 0440c)
  seriesNumberInput.value = project.series_number
    ? String(project.series_number).padStart(4, '0')
    : ''
  if (project.series_number && project.project_type_id) {
    seriesCheckResult.value = true
    seriesCheckMessage.value = 'Current value'
    // Fetch used subseries so suffix dropdown is filtered
    api.projects
      .usedSubseries(project.project_type_id, project.series_number, project.id)
      .then(({ data }) => {
        usedSubseries.value = data.used_subseries || []
      })
      .catch(() => {
        usedSubseries.value = []
      })
  } else {
    seriesCheckResult.value = null
    seriesCheckMessage.value = ''
    usedSubseries.value = []
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
    description: '',
    mission: '',
    status: 'inactive',
    project_type_id: null,
    series_number: null,
    subseries: null,
  }
  // Reset inline taxonomy state (Handover 0440c)
  seriesNumberInput.value = ''
  seriesCheckResult.value = null
  seriesCheckMessage.value = ''
  seriesChecking.value = false
  usedSubseries.value = []
  if (seriesCheckTimer) clearTimeout(seriesCheckTimer)
}

async function saveProject() {
  if (!formValid.value) {
    console.warn('[PROJECTS][CreateProject] Form is not valid', {
      projectData: projectData.value,
    })
    return
  }

  try {
    if (editingProject.value) {
      // Update existing project
      const updateData = {
        name: projectData.value.name,
        description: projectData.value.description,
        mission: projectData.value.mission,
        status: projectData.value.status,
        project_type_id: projectData.value.project_type_id,
        series_number: projectData.value.series_number,
        subseries: projectData.value.subseries,
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
    // Handover 0440c: Fetch project types for filter chips
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

/* Clickable project name */
.project-name-link {
  cursor: pointer;
  color: #ffc300;
}

.project-name-link:hover {
  text-decoration: underline;
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
