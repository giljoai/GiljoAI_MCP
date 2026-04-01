<template>
  <v-container>
    <!-- Header -->
    <v-row align="center" class="mb-4">
      <v-col>
        <div class="d-flex align-center">
          <h1 class="text-h4">Project Management</h1>
          <v-tooltip location="bottom start" max-width="600">
            <template #activator="{ props }">
              <v-icon v-bind="props" size="18" color="medium-emphasis" class="ml-2">mdi-information-outline</v-icon>
            </template>
            <div>
              <div class="font-weight-bold mb-1">Project Field Reference</div>
              <div class="text-caption text-medium-emphasis mb-2">Instructions for /gil_add</div>
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
        </div>
        <p class="text-body-2 text-medium-emphasis mt-1">Use MCP tool /gil_add to have the AI coding agent add new projects to the Project dashboard.</p>
      </v-col>
    </v-row>

    <!-- No Active Product Alert -->
    <v-alert v-if="!activeProduct" type="info" variant="tonal" class="ma-4" closable>
      No active product selected. Please activate a product to view and manage its projects.
    </v-alert>

    <!-- Filter Bar (0873: restyled to match TasksView pattern) -->
    <div v-if="activeProduct" class="filter-bar">
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
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        prepend-icon="mdi-plus"
        class="btn-pill"
        :disabled="!activeProduct"
        aria-label="Create new project"
        @click="showCreateDialog = true"
      >
        New Project
      </v-btn>
      <v-btn
        variant="outlined"
        prepend-icon="mdi-delete-restore"
        class="btn-pill"
        :disabled="deletedCount === 0"
        aria-label="View deleted projects"
        @click="showDeletedDialog = true"
      >
        Deleted ({{ deletedCount }})
      </v-btn>
    </div>

    <!-- Projects Table -->
    <v-card v-if="activeProduct" class="project-table-card smooth-border">
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
          <!-- Name Column with ID and Taxonomy Chip (Handover 0440c, 0870h) -->
          <template v-slot:item.name="{ item }">
            <div class="py-2">
              <div class="d-flex align-center">
                <v-tooltip v-if="item.project_type_id || item.series_number" :text="(item.project_type?.label || 'Untyped') + ' — ' + item.taxonomy_alias">
                  <template #activator="{ props: ttProps }">
                    <!-- Square tinted badge: desktop -->
                    <span
                      v-bind="ttProps"
                      class="project-id-badge mr-2 taxonomy-chip-full"
                      :style="projectIdBadgeStyle(item.project_type?.color || DEFAULT_PROJECT_TYPE_COLOR)"
                    >
                      {{ item.taxonomy_alias }}
                    </span>
                    <!-- Colored dot: compact viewports -->
                    <span
                      v-bind="ttProps"
                      class="taxonomy-dot mr-2"
                      :style="{ backgroundColor: item.project_type?.color || DEFAULT_PROJECT_TYPE_COLOR }"
                    ></span>
                  </template>
                </v-tooltip>
                <span class="project-name-text">
                  {{ item.name }}
                </span>
              </div>
              <div class="project-uuid-text project-id-text">
                Project ID: {{ item.id }}
              </div>
            </div>
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
            <!-- Tinted pill: desktop -->
            <span
              class="staged-full tinted-chip"
              :class="isProjectStaged(item) ? 'tinted-yes' : 'tinted-no'"
            >
              {{ isProjectStaged(item) ? 'Yes' : 'No' }}
            </span>
            <!-- Compact dot: small viewports -->
            <span
              class="staged-dot"
              :style="{ backgroundColor: isProjectStaged(item) ? 'var(--color-status-success)' : 'var(--color-text-muted)' }"
            >{{ isProjectStaged(item) ? 'Y' : 'N' }}</span>
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
                  <v-divider v-if="!['completed', 'cancelled', 'terminated'].includes(normalizeStatus(item.status))" class="my-1" />
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
      <v-card v-draggable class="smooth-border">
        <v-card-title class="d-flex align-center">
          <span>{{ editingProject ? 'Edit Project' : 'Create New Project' }}</span>
          <v-spacer />
          <AgentTipsDialog />
          <v-btn icon="mdi-close" variant="text" aria-label="Close dialog" @click="cancelEdit" />
        </v-card-title>

        <v-card-text>
          <!-- Save Error Alert (Handover 0440d) -->
          <v-alert
            v-if="saveError"
            type="error"
            variant="tonal"
            density="compact"
            class="mb-4"
            closable
            @click:close="saveError = ''"
          >
            {{ saveError }}
          </v-alert>

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
              <span class="ml-2 font-mono">{{ createdProjectId }}</span>
            </div>
          </v-alert>

          <!-- Project metadata (plain text, no alert box) -->
          <div v-if="editingProject" class="text-caption text-medium-emphasis mb-4">
            <div>Project ID: <span class="font-mono">{{ editingProject.id }}</span></div>
            <div>
              Created: {{ formatDateTime(editingProject.created_at) }}
              <span class="mx-2">|</span>
              Updated: {{ formatDateTime(editingProject.updated_at) }}
            </div>
          </div>

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
                  maxlength="4"
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

            <!-- Project Name -->
            <v-text-field
              v-model="projectData.name"
              label="Project Name"
              :rules="[(v) => !!v || 'Project name is required']"
              required
              density="compact"
              variant="outlined"
              hide-details="auto"
              class="mb-3"
              aria-label="Project name"
            />

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

    <!-- Clear Mission Confirmation Dialog -->
    <BaseDialog
      v-model="showClearMissionDialog"
      type="warning"
      title="Clear Mission?"
      confirm-label="Clear"
      size="sm"
      @confirm="projectData.mission = ''; showClearMissionDialog = false"
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

    <!-- Deleted Projects Modal -->
    <v-dialog v-model="showDeletedDialog" max-width="800" persistent retain-focus>
      <v-card v-draggable class="smooth-border">
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

          <v-list v-if="deletedProjects.length > 0" class="smooth-border rounded">
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
                    icon="mdi-delete-restore"
                    size="small"
                    variant="text"
                    :disabled="purgingProjectId === project.id || purgingAllDeleted"
                    title="Restore project"
                    aria-label="Restore deleted project"
                    @click="restoreFromDelete(project)"
                  ></v-btn>
                  <v-btn
                    icon="mdi-delete-forever"
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
      <v-card v-draggable class="smooth-border">
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
            class="pa-4 rounded smooth-border"
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

    <ProjectReviewModal
      :show="showReviewModal"
      :project-id="reviewProjectId"
      :product-id="reviewProductId"
      @close="showReviewModal = false; reviewProjectId = null; reviewProductId = null"
    />
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projects'
import { useProductStore } from '@/stores/products'
import { useNotificationStore } from '@/stores/notifications'
import StatusBadge from '@/components/StatusBadge.vue'
import ManualCloseoutModal from '@/components/orchestration/ManualCloseoutModal.vue'
import ProjectReviewModal from '@/components/projects/ProjectReviewModal.vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import AddTypeModal from '@/components/projects/AddTypeModal.vue'
import AgentTipsDialog from '@/components/common/AgentTipsDialog.vue'
import { DEFAULT_PROJECT_TYPE_COLOR } from '@/utils/constants'
import api from '@/services/api'
import { useFormatDate } from '@/composables/useFormatDate'
import { useToast } from '@/composables/useToast'

// Router
const router = useRouter()

// Stores
const projectStore = useProjectStore()
const productStore = useProductStore()
const notificationStore = useNotificationStore()
const { showToast } = useToast()

// Reactive state
const searchQuery = ref('')
const filterType = ref(null)
const filterStatus = ref(null)
const projectTypes = ref([])
const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const showDeletedDialog = ref(false)
const showMissionDialog = ref(false)
const showCloseoutModal = ref(false)
const closeoutProjectId = ref(null)
const closeoutProjectName = ref('')
const showReviewModal = ref(false)
const reviewProjectId = ref(null)
const reviewProductId = ref(null)
const formValid = ref(false)
const editingProject = ref(null)
const projectToDelete = ref(null)
const createdProjectId = ref(null)
const saveError = ref('')
const currentPage = ref(1)
const itemsPerPage = ref(10)
const purgingProjectId = ref(null)
const purgingAllDeleted = ref(false)
const showClearMissionDialog = ref(false)
const showPurgeSingleDialog = ref(false)
const projectToPurge = ref(null)
const showPurgeAllDialog = ref(false)

// Sort configuration
const sortConfig = ref([{ key: 'created_at', order: 'desc' }])

const { formatDate, formatDateTime, formatDateCompact } = useFormatDate()

/* 0870h: tinted square badge style for project taxonomy IDs */
function projectIdBadgeStyle(color) {
  return {
    backgroundColor: `${color}26`, /* ~15% opacity */
    color: color,
  }
}

/* design-token-exempt: dynamic JS color lookup used in template :style bindings */
function statusDotColor(status) {
  const colors = {
    active: '#ffffff', /* design-token-exempt: $color-surface */
    inactive: '#9e9e9e', /* design-token-exempt: $color-text-muted */
    completed: '#4caf50', /* design-token-exempt: $color-status-success */
    cancelled: '#fb8c00', /* design-token-exempt: $color-status-warning */
    terminated: '#f44336', /* design-token-exempt: $color-status-error */
    deleted: '#f44336', /* design-token-exempt: $color-status-error */
  }
  return colors[status] || '#9e9e9e' /* design-token-exempt: $color-text-muted */
}

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

const statusFilterOptions = computed(() => [
  { label: 'All', value: 'all', count: activeProductProjects.value.length },
  { label: 'Active', value: 'active', count: statusCounts.value.active },
  { label: 'Inactive', value: 'inactive', count: statusCounts.value.inactive },
  { label: 'Completed', value: 'completed', count: statusCounts.value.completed },
  { label: 'Cancelled', value: 'cancelled', count: statusCounts.value.cancelled },
  { label: 'Terminated', value: 'terminated', count: statusCounts.value.terminated },
])

// 0873: v-select items for filter bar dropdowns
const statusSelectOptions = ['active', 'inactive', 'completed', 'cancelled', 'terminated']
const typeSelectOptions = computed(() => {
  const items = projectTypes.value.map((t) => ({
    title: t.abbreviation,
    value: t.id,
  }))
  items.push({ title: 'No Type', value: 'none' })
  return items
})

function clearFilters() {
  searchQuery.value = ''
  filterStatus.value = null
  filterType.value = null
}

// Table headers
const headers = [
  { title: 'Name', key: 'name', sortable: true, width: '33%' },
  { title: 'Status', key: 'status', sortable: true, width: '15%', align: 'center' },
  { title: 'Staged', key: 'staging_status', sortable: true, width: '9%' },
  { title: 'Created', key: 'created_at', sortable: true, width: '13%' },
  { title: 'Completed', key: 'completed_at', sortable: true, width: '13%', align: 'center' },
  { title: 'Actions', key: 'quick_action', sortable: false, width: '5%', align: 'center' },
  { title: '', key: 'menu', sortable: false, width: '3%', align: 'center' },
]

// --- Inline taxonomy state and logic (Handover 0440c) ---
const showAddTypeModal = ref(false)
const seriesNumberInput = ref('')
const seriesChecking = ref(false)
const seriesCheckResult = ref(null) // null = unchecked, true = available, false = taken
const seriesCheckMessage = ref('')
const usedSubseries = ref([]) // letters already taken for current type+serial
let seriesCheckTimer = null
let seriesAbortController = null // H-1: AbortController for in-flight series checks

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

// Handle type change: re-check availability with new type context
function handleTypeChange(typeId) {
  if (typeId === '__add_custom__') {
    showAddTypeModal.value = true
    projectData.value.project_type_id = null
    return
  }
  // Re-validate existing serial against new type context
  seriesCheckResult.value = null
  seriesCheckMessage.value = ''
  usedSubseries.value = []
  if (projectData.value.series_number) {
    seriesChecking.value = true
    if (seriesCheckTimer) clearTimeout(seriesCheckTimer)
    seriesCheckTimer = setTimeout(() => checkSeriesAvailability(projectData.value.series_number), 300)
  }
}

// Handle type created from AddTypeModal
function handleTypeCreated(newType) {
  projectTypes.value.push(newType)
  projectData.value.project_type_id = newType.id
  // Re-validate existing serial against new type context
  usedSubseries.value = []
  if (projectData.value.series_number) {
    seriesChecking.value = true
    if (seriesCheckTimer) clearTimeout(seriesCheckTimer)
    seriesCheckTimer = setTimeout(() => checkSeriesAvailability(projectData.value.series_number), 300)
  }
}

// Debounced series number input handler
function onSeriesInput(val) {
  if (seriesCheckTimer) clearTimeout(seriesCheckTimer)

  const trimmed = (val || '').trim()
  if (!trimmed) {
    projectData.value.series_number = null
    usedSubseries.value = []
    seriesCheckResult.value = null
    seriesCheckMessage.value = ''
    return
  }

  const num = parseInt(trimmed, 10)
  if (isNaN(num) || num < 1 || num > 9999) {
    projectData.value.series_number = null
    usedSubseries.value = []
    seriesCheckResult.value = false
    seriesCheckMessage.value = 'Enter 1-9999'
    return
  }

  projectData.value.series_number = num
  usedSubseries.value = []

  seriesChecking.value = true
  seriesCheckTimer = setTimeout(() => checkSeriesAvailability(num), 300)
}

// API call to check series availability + fetch used subseries
async function checkSeriesAvailability(num) {
  if (!num) {
    seriesChecking.value = false
    return
  }
  // H-1: Abort previous in-flight request
  if (seriesAbortController) seriesAbortController.abort()
  seriesAbortController = new AbortController()
  const { signal } = seriesAbortController

  const requestedTypeId = projectData.value.project_type_id
  const excludeId = editingProject.value?.id || null
  try {
    const [checkRes, usedRes] = await Promise.all([
      api.projects.checkSeries(
        requestedTypeId,
        num,
        projectData.value.subseries,
        excludeId,
        { signal },
      ),
      api.projects.usedSubseries(
        requestedTypeId,
        num,
        excludeId,
        { signal },
      ),
    ])
    // H-4: Guard against stale responses (type changed while request was in-flight)
    if (projectData.value.project_type_id !== requestedTypeId) return
    seriesCheckResult.value = checkRes.data.available
    seriesCheckMessage.value = checkRes.data.available
      ? `${String(num).padStart(4, '0')} available`
      : `${String(num).padStart(4, '0')} taken`
    usedSubseries.value = usedRes.data.used_subseries || []
  } catch (err) {
    if (err?.name === 'AbortError' || err?.name === 'CanceledError') return
    seriesCheckResult.value = null
    seriesCheckMessage.value = ''
    usedSubseries.value = []
  } finally {
    seriesChecking.value = false
  }
}

// Re-check when subseries changes
function onSubseriesChange() {
  if (projectData.value.series_number) {
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
  if (filterType.value && filterType.value !== 'all') {
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
  if (!filterStatus.value || filterStatus.value === 'all') return filteredBySearch.value
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
    terminated: activeProductProjects.value.filter((p) => p.status === 'terminated').length,
    staged: activeProductProjects.value.filter(
      (p) => p.staging_status === 'staged' || p.staging_status === 'staging_complete'
    ).length,
  }
})

// Deleted projects
const deletedProjects = computed(() => projectStore.deletedProjects)

const deletedCount = computed(() => deletedProjects.value.length)

// Helper function to determine if project is staged
// Uses staging_status from database for persistence across refresh/restart
const isProjectStaged = (project) => {
  return project.staging_status === 'staged' || project.staging_status === 'staging_complete'
}

// Launch button visibility - only show when exactly 1 active project exists and it is not staged
// Normalize status values for UI (e.g., legacy 'paused' -> 'inactive')
function normalizeStatus(status) {
  if (status === 'paused') {
    return 'inactive'
  }
  return status || 'inactive'
}

// Status action definitions for the "..." menu (moved from StatusBadge)
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

// Get available status actions for a project based on its current status
function getStatusActions(item) {
  const normalized = normalizeStatus(item.status)
  const keys = [...(actionsByStatus[normalized] || [])]
  if (normalized === 'cancelled' && !isProjectStaged(item)) {
    keys.unshift('reopen')
  }
  return keys.map((key) => ({ key, ...statusActionDefs[key] }))
}

// Methods

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

// Mission helper methods
function viewFullMission() {
  showMissionDialog.value = true
}

function clearMission() {
  showClearMissionDialog.value = true
}

async function editProject(project) {
  editingProject.value = project
  createdProjectId.value = null
  saveError.value = ''
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
    // H-3: Await usedSubseries fetch before opening dialog to prevent flash
    try {
      const { data } = await api.projects.usedSubseries(
        project.project_type_id,
        project.series_number,
        project.id,
      )
      usedSubseries.value = data.used_subseries || []
    } catch {
      usedSubseries.value = []
    }
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
        // Open CloseoutModal instead of direct API call
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
    showToast({ message: 'Failed to update project status. Try refreshing the page to get the latest state.', type: 'error' })
    // Refresh even on error to show true server state
    await projectStore.fetchProjects()
  }
}

// Handle CloseoutModal events
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
  saveError.value = ''
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
    saveError.value = error.response?.data?.error || error.message || 'Failed to save project'
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

// H-2: Clean up timer and abort controller on unmount
onBeforeUnmount(() => {
  if (seriesCheckTimer) clearTimeout(seriesCheckTimer)
  if (seriesAbortController) seriesAbortController.abort()
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
  max-width: 600px;
}

.filter-search :deep(.v-field) {
  box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255, 255, 255, 0.10));
  border-radius: $border-radius-default;
}

.filter-search :deep(.v-field:focus-within) {
  box-shadow: inset 0 0 0 1px rgba($color-brand-yellow, 0.3);
}

.filter-select {
  max-width: 160px;
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

.cursor-pointer {
  cursor: pointer;
}

.gap-2 {
  gap: 0.5rem;
}

.border-b {
  border-bottom: 1px solid $color-border-subtle;
}

.rounded {
  border-radius: $border-radius-sharp;
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

/* Scrollable project list container */
.project-list-container {
  height: calc(100vh - 260px);
  overflow-y: auto;
  overflow-x: hidden;
}

/* Ensure table headers are sticky */
.project-list-container :deep(.v-data-table__thead) {
  position: sticky;
  top: 0;
  z-index: 2;
  background-color: $color-surface;
}

/* Remove default table wrapper overflow to allow container scroll */
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

/* 0870h: Tinted chip base */
.tinted-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: $border-radius-pill;
  font-size: 0.65rem;
  font-weight: 600;
}

/* 0870h: Tinted Yes/No staged chips */
.tinted-yes {
  background: rgba($color-status-success, 0.12);
  color: $color-status-success;
}

.tinted-no {
  background: rgba($color-agent-analyzer, 0.12);
  color: $color-agent-analyzer;
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
.taxonomy-dot,
.status-dot,
.staged-dot,
.date-compact {
  display: none;
}

/* Taxonomy colored dot */
.taxonomy-dot {
  width: 10px;
  height: 10px;
  min-width: 10px;
  border-radius: 50%;
  flex-shrink: 0;
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

/* Staged compact dot with Y/N */
.staged-dot {
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
  .taxonomy-chip-full,
  .status-full,
  .staged-full,
  .date-full {
    display: none !important;
  }
  .taxonomy-dot,
  .status-dot,
  .staged-dot,
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
