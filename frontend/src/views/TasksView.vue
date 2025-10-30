<template>
  <v-container>
    <!-- Header with Actions -->
    <v-row align="center" class="mb-4">
      <v-col>
        <h1 class="text-h4">Tasks</h1>
      </v-col>
      <v-col cols="auto">
        <v-btn
          variant="outlined"
          prepend-icon="mdi-history"
          @click="showConversionHistory = true"
          class="mr-2"
        >
          History
        </v-btn>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="showTaskDialog = true">
          New Task
        </v-btn>
      </v-col>
    </v-row>

    <!-- Task Statistics -->
    <v-row class="mb-4">
      <v-col cols="12" sm="6" md="3">
        <v-card class="stats-card">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon color="info" size="large">mdi-clipboard-list</v-icon>
              <div class="ml-4">
                <div class="text-h5">{{ totalTasks }}</div>
                <div class="text-caption">Total Tasks</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card class="stats-card">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon color="warning" size="large">mdi-clock-outline</v-icon>
              <div class="ml-4">
                <div class="text-h5">{{ pendingTasks }}</div>
                <div class="text-caption">Pending</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card class="stats-card">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon color="info" size="large">mdi-progress-clock</v-icon>
              <div class="ml-4">
                <div class="text-h5">{{ inProgressTasks }}</div>
                <div class="text-caption">In Progress</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card class="stats-card">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon color="success" size="large">mdi-check-circle</v-icon>
              <div class="ml-4">
                <div class="text-h5">{{ completedTasks }}</div>
                <div class="text-caption">Completed</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filters Row -->
    <v-row class="mb-4" align="center">
      <!-- Product Task Filter -->
      <v-col cols="12" md="3">
        <v-chip-group v-model="taskFilter" mandatory active-class="primary" density="comfortable">
          <v-chip value="product_tasks" data-test="product-tasks-chip">
            <v-icon start>mdi-package-variant</v-icon>
            Product Tasks
          </v-chip>
          <v-chip value="all_tasks" data-test="all-tasks-chip">
            <v-icon start>mdi-format-list-bulleted</v-icon>
            All Tasks
          </v-chip>
        </v-chip-group>
      </v-col>

      <v-col cols="12" md="3">
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="Search tasks"
          variant="outlined"
          density="compact"
          clearable
          hide-details
          data-search-input
        />
      </v-col>
      <v-col cols="12" md="2">
        <v-select
          v-model="statusFilter"
          :items="statusOptions"
          label="Status"
          variant="outlined"
          density="compact"
          clearable
          hide-details
        />
      </v-col>
      <v-col cols="12" md="2">
        <v-select
          v-model="priorityFilter"
          :items="priorityOptions"
          label="Priority"
          variant="outlined"
          density="compact"
          clearable
          hide-details
        />
      </v-col>
      <v-col cols="12" md="2">
        <v-btn variant="outlined" @click="clearFilters" block> Clear Filters </v-btn>
      </v-col>
    </v-row>

    <!-- Conversion Action Bar -->
    <v-row v-if="selectedTasks.length > 0" class="mb-4">
      <v-col>
        <v-card color="primary" variant="outlined">
          <v-card-text class="d-flex align-center">
            <v-icon>mdi-checkbox-marked-multiple</v-icon>
            <span class="ml-2"
              >{{ selectedTasks.length }} task{{
                selectedTasks.length > 1 ? 's' : ''
              }}
              selected</span
            >
            <v-spacer />
            <v-btn
              color="primary"
              variant="flat"
              prepend-icon="mdi-arrow-right-bold-circle"
              @click="openConversionDialog"
            >
              Convert to Project{{ selectedTasks.length > 1 ? 's' : '' }}
            </v-btn>
            <v-btn
              variant="text"
              icon="mdi-close"
              size="small"
              class="ml-2"
              @click="clearSelection"
              aria-label="Clear selection"
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Tasks Table -->
    <v-card>
      <!-- Table Controls -->
      <v-card-title class="d-flex align-center py-3">
        <span class="text-h6">Tasks</span>
        <v-spacer />
        <v-btn-toggle v-model="showHierarchy" size="small" density="compact">
          <v-btn :value="false" icon="mdi-format-list-bulleted" aria-label="List view" />
          <v-btn :value="true" icon="mdi-file-tree" aria-label="Hierarchy view" />
        </v-btn-toggle>
      </v-card-title>

      <v-data-table
        :headers="headers"
        :items="hierarchicalTasks"
        :search="search"
        :loading="loading"
        :items-per-page="10"
        class="elevation-0 draggable-table"
        data-table
        item-value="id"
      >
        <!-- Loading State -->
        <template v-slot:loading>
          <div class="text-center pa-4">
            <v-progress-circular indeterminate color="primary" size="48" />
            <p class="text-body-2 text-medium-emphasis mt-2">Loading tasks...</p>
          </div>
        </template>

        <!-- Selection Column -->
        <template v-slot:item.select="{ item }">
          <v-checkbox-btn
            :model-value="selectedTasks.includes(item.id)"
            @update:model-value="toggleTaskSelection(item.id)"
            density="compact"
            hide-details
          />
        </template>

        <!-- Status Column -->
        <template v-slot:item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" size="small" variant="flat">
            <v-icon start size="x-small">{{ getStatusIcon(item.status) }}</v-icon>
            {{ item.status }}
          </v-chip>
        </template>

        <!-- Priority Column -->
        <template v-slot:item.priority="{ item }">
          <v-chip :color="getPriorityColor(item.priority)" size="small" label>
            {{ item.priority }}
          </v-chip>
        </template>

        <!-- Title Column with Hierarchy and Drag Support -->
        <template v-slot:item.title="{ item }">
          <div
            class="task-row-content"
            :class="{
              'drag-over': dropTarget === item.id,
              dragging: draggedTask?.id === item.id,
              'hierarchy-item': showHierarchy && item.parent_task_id,
              'parent-item': showHierarchy && hasChildren(item.id),
            }"
            :data-test="`task-row-${item.id}`"
            draggable="true"
            @dragstart="handleDragStart(item, $event)"
            @dragend="handleDragEnd"
            @dragover="handleDragOver($event)"
            @dragenter="handleDragEnter(item)"
            @dragleave="handleDragLeave"
            @drop="handleDrop(item, $event)"
          >
            <!-- Hierarchy Indicators -->
            <div v-if="showHierarchy" class="hierarchy-indicators">
              <div
                v-if="item.parent_task_id"
                class="hierarchy-line"
                :style="{ marginLeft: getTaskDepth(item.id) * 20 + 'px' }"
              >
                <v-icon size="small" color="grey">mdi-subdirectory-arrow-right</v-icon>
              </div>
              <v-icon
                v-if="hasChildren(item.id)"
                size="small"
                color="primary"
                class="parent-indicator"
              >
                mdi-folder
              </v-icon>
            </div>

            <!-- Drag Handle -->
            <v-icon class="drag-handle mr-2" size="small" color="grey">
              mdi-drag-horizontal
            </v-icon>

            <!-- Task Content -->
            <div class="task-content flex-grow-1">
              <div class="d-flex align-center">
                <!-- Owner indicator (Phase 4) -->
                <v-icon
                  v-if="item.created_by_user_id === user?.id"
                  color="primary"
                  size="small"
                  class="mr-2"
                  data-test="owner-icon"
                >
                  mdi-account-circle
                </v-icon>

                <span class="font-weight-medium">{{ item.title }}</span>
              </div>
              <div class="text-caption text-medium-emphasis">{{ item.description }}</div>

              <!-- Parent/Child Indicators -->
              <div v-if="showHierarchy" class="hierarchy-info mt-1">
                <v-chip
                  v-if="item.parent_task_id"
                  size="x-small"
                  color="info"
                  variant="outlined"
                  class="mr-1"
                >
                  <v-icon start size="x-small">mdi-arrow-up</v-icon>
                  Child of {{ getTaskTitle(item.parent_task_id) }}
                </v-chip>
                <v-chip
                  v-if="hasChildren(item.id)"
                  size="x-small"
                  color="primary"
                  variant="outlined"
                >
                  <v-icon start size="x-small">mdi-arrow-down</v-icon>
                  {{ getChildCount(item.id) }} child{{ getChildCount(item.id) > 1 ? 'ren' : '' }}
                </v-chip>
              </div>
            </div>

            <!-- Drop Zone Indicator -->
            <div v-if="isDragging && dropTarget === item.id" class="drop-indicator">
              <v-icon color="primary">mdi-arrow-down-drop-circle</v-icon>
              <span class="text-caption">Drop here to make child task</span>
            </div>
          </div>
        </template>


        <!-- Created By User Column (Phase 4) -->
        <template v-slot:item.created_by_user_id="{ item }">
          <v-chip size="small" variant="outlined">
            <v-icon start size="small">mdi-account-circle</v-icon>
            {{ getUserName(item.created_by_user_id) }}
          </v-chip>
        </template>

        <!-- Due Date Column -->
        <template v-slot:item.due_date="{ item }">
          <div v-if="item.due_date">
            <v-icon v-if="isOverdue(item.due_date)" color="error" size="x-small" class="mr-1">
              mdi-alert
            </v-icon>
            {{ formatDate(item.due_date) }}
          </div>
          <span v-else class="text-medium-emphasis">No due date</span>
        </template>

        <!-- Convert Status Column -->
        <template v-slot:item.convert_status="{ item }">
          <div v-if="item.converted_project_id">
            <v-tooltip text="Task converted to project">
              <template v-slot:activator="{ props }">
                <v-chip
                  v-bind="props"
                  color="success"
                  size="small"
                  prepend-icon="mdi-arrow-right-bold-circle"
                  variant="flat"
                >
                  Converted
                </v-chip>
              </template>
            </v-tooltip>
          </div>
          <div v-else-if="item.conversion_pending">
            <v-chip color="warning" size="small" prepend-icon="mdi-clock-outline" variant="flat">
              Pending
            </v-chip>
          </div>
          <span v-else class="text-medium-emphasis">—</span>
        </template>

        <!-- Actions Column -->
        <template v-slot:item.actions="{ item }">
          <v-menu>
            <template v-slot:activator="{ props }">
              <v-btn icon="mdi-dots-vertical" size="small" variant="text" v-bind="props" />
            </template>
            <v-list>
              <v-list-item @click="editTask(item)">
                <template v-slot:prepend>
                  <v-icon>mdi-pencil</v-icon>
                </template>
                <v-list-item-title>Edit</v-list-item-title>
              </v-list-item>

              <v-list-item
                v-if="item.status !== 'completed'"
                @click="convertTaskToProject(item)"
              >
                <template v-slot:prepend>
                  <v-icon>mdi-folder-arrow-up</v-icon>
                </template>
                <v-list-item-title>Convert to Project</v-list-item-title>
              </v-list-item>

              <v-list-item
                v-if="item.status !== 'completed'"
                @click="completeTask(item)"
              >
                <template v-slot:prepend>
                  <v-icon color="success">mdi-check</v-icon>
                </template>
                <v-list-item-title>Mark Complete</v-list-item-title>
              </v-list-item>

              <v-divider />

              <v-list-item @click="deleteTask(item)">
                <template v-slot:prepend>
                  <v-icon color="error">mdi-delete</v-icon>
                </template>
                <v-list-item-title>Delete</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </template>

        <!-- No Data -->
        <template v-slot:no-data>
          <div class="text-center py-8">
            <v-icon size="64" color="grey-lighten-2">mdi-clipboard-text-outline</v-icon>
            <p class="text-h6 mt-4">No tasks found</p>
            <p class="text-body-2 text-medium-emphasis">
              {{
                search || statusFilter || priorityFilter || categoryFilter
                  ? 'Try adjusting your filters'
                  : 'Create your first task to get started'
              }}
            </p>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create/Edit Task Dialog -->
    <v-dialog v-model="showTaskDialog" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">{{ editingTask ? 'mdi-pencil' : 'mdi-plus' }}</v-icon>
          <span>{{ editingTask ? 'Edit Task' : 'Create Task' }}</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" @click="cancelTask" aria-label="Close" />
        </v-card-title>

        <v-card-text>
          <v-form ref="taskForm">
            <v-text-field
              v-model="currentTask.title"
              label="Task Title"
              variant="outlined"
              :rules="[(v) => !!v || 'Title is required']"
            />

            <v-textarea
              v-model="currentTask.description"
              label="Description"
              variant="outlined"
              rows="3"
            />

            <v-row>
              <v-col cols="6">
                <v-select
                  v-model="currentTask.status"
                  :items="statusOptions"
                  label="Status"
                  variant="outlined"
                />
              </v-col>
              <v-col cols="6">
                <v-select
                  v-model="currentTask.priority"
                  :items="priorityOptions"
                  label="Priority"
                  variant="outlined"
                />
              </v-col>
            </v-row>

            <v-row>
              <v-col cols="6">
                <v-select
                  v-model="currentTask.category"
                  :items="categoryOptions"
                  label="Category"
                  variant="outlined"
                />
              </v-col>
            </v-row>

            <v-text-field
              v-model="currentTask.due_date"
              label="Due Date"
              type="date"
              variant="outlined"
            />
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="cancelTask"> Cancel </v-btn>
          <v-btn color="primary" variant="flat" @click="saveTask" :loading="saving">
            {{ editingTask ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Task Converter Dialog -->
    <TaskConverter
      :show="showConversionDialog"
      :selected-task-ids="selectedTasks"
      @close="closeConversionDialog"
      @converted="onTasksConverted"
    />

    <!-- Conversion History Dialog -->
    <v-dialog v-model="showConversionHistory" max-width="900">
      <v-card>
        <v-card-title class="d-flex align-center">
          <span>Conversion History</span>
          <v-spacer />
          <v-btn
            icon="mdi-close"
            variant="text"
            @click="showConversionHistory = false"
            aria-label="Close"
          />
        </v-card-title>
        <ConversionHistory
          :product-id="productStore.currentProductId"
          @project-selected="handleProjectSelected"
          @conversion-rolled-back="handleConversionRollback"
        />
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useTaskStore } from '@/stores/tasks'
import { useProductStore } from '@/stores/products'
import { useAgentStore } from '@/stores/agents'
import { useUserStore } from '@/stores/user'
import { format, isAfter } from 'date-fns'
import api from '@/services/api'
import TaskConverter from '@/components/TaskConverter.vue'
import ConversionHistory from '@/components/ConversionHistory.vue'

// Stores
const taskStore = useTaskStore()
const productStore = useProductStore()
const agentStore = useAgentStore()
const userStore = useUserStore()

// State
const search = ref('')
const statusFilter = ref(null)
const priorityFilter = ref(null)
const categoryFilter = ref(null)
const showTaskDialog = ref(false)
const showCreateDialog = ref(false)
const editingTask = ref(null)
const taskForm = ref(null)
const saving = ref(false)

// Product task filter
const taskFilter = ref('product_tasks')
const user = computed(() => userStore.currentUser)

// Bulk selection state
const selectedTasks = ref([])
const selectAll = ref(false)
const showConversionDialog = ref(false)

// Drag and drop state
const draggedTask = ref(null)
const dropTarget = ref(null)
const isDragging = ref(false)
const showHierarchy = ref(false)
const showConversionHistory = ref(false)

// Current task form
const currentTask = ref({
  title: '',
  description: '',
  status: 'pending',
  priority: 'medium',
  category: 'general',
  due_date: null,
})

// Table headers
const headers = [
  { title: 'Select', key: 'select', sortable: false, width: '60' },
  { title: 'Status', key: 'status', width: '120' },
  { title: 'Priority', key: 'priority', width: '100' },
  { title: 'Task', key: 'title' },
  { title: 'Category', key: 'category', width: '120' },
  { title: 'Created By', key: 'created_by_user_id', width: '150' },
  { title: 'Due Date', key: 'due_date', width: '120' },
  { title: 'Convert Status', key: 'convert_status', width: '130' },
  { title: 'Actions', key: 'actions', sortable: false, width: '120' },
]

// Filter options
const statusOptions = ['pending', 'in_progress', 'completed', 'cancelled']
const priorityOptions = ['low', 'medium', 'high', 'critical']
const categoryOptions = ['general', 'feature', 'bug', 'improvement', 'documentation', 'testing']


// Computed
const loading = computed(() => taskStore.loading)
const tasks = computed(() => taskStore.tasks)

// Product-filtered tasks
const userFilteredTasks = computed(() => {
  if (taskFilter.value === 'product_tasks') {
    // Show tasks for active product only
    if (!productStore.currentProductId) {
      return [] // No active product, return empty list
    }
    return tasks.value.filter((task) => task.product_id === productStore.currentProductId)
  } else if (taskFilter.value === 'all_tasks') {
    // Show tasks with NULL product_id
    return tasks.value.filter((task) => task.product_id === null || task.product_id === undefined)
  }
  return tasks.value
})

const agentOptions = computed(() => {
  return agentStore.agents.map((agent) => agent.name)
})

const filteredTasks = computed(() => {
  // Start with user-filtered tasks (Phase 4)
  let filteredList = userFilteredTasks.value

  // Then filter by product if one is selected
  if (productStore.currentProductId) {
    filteredList = filteredList.filter((t) => t.product_id === productStore.currentProductId)
  }

  if (statusFilter.value) {
    filteredList = filteredList.filter((t) => t.status === statusFilter.value)
  }

  if (priorityFilter.value) {
    filteredList = filteredList.filter((t) => t.priority === priorityFilter.value)
  }

  if (categoryFilter.value) {
    filteredList = filteredList.filter((t) => t.category === categoryFilter.value)
  }

  return filteredList
})

const hierarchicalTasks = computed(() => {
  if (!showHierarchy.value) {
    return filteredTasks.value
  }

  // Sort tasks to show parents before children
  const sorted = [...filteredTasks.value].sort((a, b) => {
    // Root tasks (no parent) come first
    if (!a.parent_task_id && b.parent_task_id) return -1
    if (a.parent_task_id && !b.parent_task_id) return 1

    // If both have parents, sort by parent first, then by creation date
    if (a.parent_task_id && b.parent_task_id) {
      if (a.parent_task_id !== b.parent_task_id) {
        return a.parent_task_id.localeCompare(b.parent_task_id)
      }
    }

    // Sort by creation date as fallback
    return new Date(a.created_at || 0) - new Date(b.created_at || 0)
  })

  return sorted
})

const totalTasks = computed(() => tasks.value.length)
const pendingTasks = computed(() => tasks.value.filter((t) => t.status === 'pending').length)
const inProgressTasks = computed(() => tasks.value.filter((t) => t.status === 'in_progress').length)
const completedTasks = computed(() => tasks.value.filter((t) => t.status === 'completed').length)

// Methods
function getStatusColor(status) {
  const colors = {
    pending: 'warning',
    in_progress: 'info',
    completed: 'success',
    cancelled: 'grey',
  }
  return colors[status] || 'grey'
}

function getStatusIcon(status) {
  const icons = {
    pending: 'mdi-clock-outline',
    in_progress: 'mdi-progress-clock',
    completed: 'mdi-check-circle',
    cancelled: 'mdi-cancel',
  }
  return icons[status] || 'mdi-help'
}

function getPriorityColor(priority) {
  const colors = {
    low: 'grey',
    medium: 'info',
    high: 'warning',
    critical: 'error',
  }
  return colors[priority] || 'grey'
}

function formatDate(date) {
  if (!date) return ''
  return format(new Date(date), 'MMM dd, yyyy')
}

function isOverdue(date) {
  if (!date) return false
  return isAfter(new Date(), new Date(date))
}

function clearFilters() {
  search.value = ''
  statusFilter.value = null
  priorityFilter.value = null
  categoryFilter.value = null
}

function editTask(task) {
  editingTask.value = task
  currentTask.value = { ...task }
  showTaskDialog.value = true
}

async function completeTask(task) {
  try {
    await taskStore.updateTask(task.id, { status: 'completed' })
  } catch (error) {
    console.error('Failed to complete task:', error)
  }
}

async function convertTaskToProject(task) {
  if (!productStore.currentProductId) {
    alert('Please activate a product before converting tasks to projects.')
    return
  }

  if (confirm(`Convert task "${task.title}" to a project?\n\nThis will create a new project with the task's title and description.`)) {
    try {
      const response = await api.tasks.convertToProject(task.id)
      await taskStore.fetchTasks()
      alert(`Task successfully converted to project: ${response.data.name}`)
    } catch (error) {
      console.error('Error converting task to project:', error)
      const errorMsg = error.response?.data?.detail || 'Failed to convert task to project'
      alert(errorMsg)
    }
  }
}

async function deleteTask(task) {
  if (confirm(`Are you sure you want to delete "${task.title}"?`)) {
    try {
      await taskStore.deleteTask(task.id)
    } catch (error) {
      console.error('Failed to delete task:', error)
    }
  }
}

function cancelTask() {
  showTaskDialog.value = false
  showCreateDialog.value = false
  editingTask.value = null
  currentTask.value = {
    title: '',
    description: '',
    status: 'pending',
    priority: 'medium',
    category: 'general',
    due_date: null,
  }
}

// Bulk selection methods
function toggleTaskSelection(taskId) {
  const index = selectedTasks.value.indexOf(taskId)
  if (index > -1) {
    selectedTasks.value.splice(index, 1)
  } else {
    selectedTasks.value.push(taskId)
  }
}

function clearSelection() {
  selectedTasks.value = []
  selectAll.value = false
}

function openConversionDialog() {
  if (selectedTasks.value.length === 0) return
  showConversionDialog.value = true
}

function closeConversionDialog() {
  showConversionDialog.value = false
}

function onTasksConverted(convertedProjects) {
  // Clear selection after successful conversion
  clearSelection()

  // Refresh tasks to show updated conversion status
  taskStore.fetchTasks()

  // Optional: Show success message
  console.log(
    `Successfully converted ${selectedTasks.value.length} tasks to ${convertedProjects.length} project(s)`,
  )
}

// Hierarchy management methods
function hasChildren(taskId) {
  return filteredTasks.value.some((task) => task.parent_task_id === taskId)
}

function getChildCount(taskId) {
  return filteredTasks.value.filter((task) => task.parent_task_id === taskId).length
}

function getTaskDepth(taskId, depth = 0) {
  const task = filteredTasks.value.find((t) => t.id === taskId)
  if (!task || !task.parent_task_id || depth > 10) return depth
  return getTaskDepth(task.parent_task_id, depth + 1)
}

function getTaskTitle(taskId) {
  const task = filteredTasks.value.find((t) => t.id === taskId)
  return task ? task.title : 'Unknown Task'
}

// Drag and drop methods
function handleDragStart(task, event) {
  draggedTask.value = task
  isDragging.value = true
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', task.id)

  // Add visual feedback
  event.target.style.opacity = '0.5'
}

function handleDragEnd(event) {
  draggedTask.value = null
  isDragging.value = false
  dropTarget.value = null

  // Reset visual feedback
  event.target.style.opacity = '1'
}

function handleDragOver(event) {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
}

function handleDragEnter(item) {
  if (draggedTask.value && draggedTask.value.id !== item.id) {
    // Prevent dropping on descendants
    if (!isDescendant(draggedTask.value.id, item.id)) {
      dropTarget.value = item.id
    }
  }
}

function handleDragLeave() {
  // Add small delay to prevent flickering
  setTimeout(() => {
    if (!document.querySelector(':hover')?.closest('.task-row-content')) {
      dropTarget.value = null
    }
  }, 50)
}

async function handleDrop(targetTask, event) {
  event.preventDefault()

  if (!draggedTask.value || draggedTask.value.id === targetTask.id) {
    return
  }

  // Prevent creating circular dependencies
  if (isDescendant(draggedTask.value.id, targetTask.id)) {
    console.warn('Cannot create circular dependency')
    return
  }

  try {
    // Update the dragged task to have the target as parent
    await taskStore.updateTask(draggedTask.value.id, {
      parent_task_id: targetTask.id,
    })

    // Refresh tasks to show updated hierarchy
    await taskStore.fetchTasks()
  } catch (error) {
    console.error('Failed to update task hierarchy:', error)
  } finally {
    draggedTask.value = null
    isDragging.value = false
    dropTarget.value = null
  }
}

function isDescendant(ancestorId, descendantId) {
  const descendant = filteredTasks.value.find((t) => t.id === descendantId)
  if (!descendant || !descendant.parent_task_id) return false

  if (descendant.parent_task_id === ancestorId) return true
  return isDescendant(ancestorId, descendant.parent_task_id)
}

// Conversion history handlers
function handleProjectSelected(projectId) {
  // Navigate to project or emit event to parent
  console.log('Navigate to project:', projectId)
  // Could integrate with router: router.push(`/projects/${projectId}`)
}

function handleConversionRollback(conversion) {
  // Refresh tasks after rollback
  taskStore.fetchTasks()
  console.log('Conversion rolled back:', conversion.id)
}

async function saveTask() {
  const { valid } = await taskForm.value.validate()
  if (!valid) return

  saving.value = true
  try {
    if (editingTask.value) {
      await taskStore.updateTask(editingTask.value.id, currentTask.value)
    } else {
      // Add current product_id to new task
      if (productStore.currentProductId) {
        currentTask.value.product_id = productStore.currentProductId
      }
      await taskStore.createTask(currentTask.value)
    }
    cancelTask()
    // Phase 4: Refresh tasks to show updates
    await fetchTasks()
  } catch (error) {
    console.error('Failed to save task:', error)
  } finally {
    saving.value = false
  }
}

// Phase 4: Fetch tasks with user filter
async function fetchTasks() {
  const params = {
    filter_type: taskFilter.value,
  }

  if (productStore.currentProductId) {
    params.product_id = productStore.currentProductId
  }

  await taskStore.fetchTasks(params)
}

// Phase 4: Watch filter changes
watch(taskFilter, () => {
  fetchTasks()
})

// Watch for dialog trigger
onMounted(() => {
  if (showCreateDialog.value) {
    showTaskDialog.value = true
  }
})

// Lifecycle
onMounted(async () => {
  await Promise.all([fetchTasks(), agentStore.fetchAgents()])
})
</script>

<style scoped>
.task-row-content {
  display: flex;
  align-items: center;
  padding: 8px 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
  min-height: 48px;
  cursor: grab;
}

.task-row-content:hover {
  background-color: rgba(0, 0, 0, 0.04);
}

.task-row-content.dragging {
  opacity: 0.5;
  transform: rotate(5deg);
  cursor: grabbing;
}

.task-row-content.drag-over {
  background-color: rgba(25, 118, 210, 0.1);
  border: 2px dashed #1976d2;
  transform: scale(1.02);
}

.drag-handle {
  cursor: grab;
  opacity: 0.6;
  transition: opacity 0.2s ease;
}

.drag-handle:hover {
  opacity: 1;
}

.task-row-content.dragging .drag-handle {
  cursor: grabbing;
}

.hierarchy-indicators {
  display: flex;
  align-items: center;
  margin-right: 8px;
}

.hierarchy-line {
  display: flex;
  align-items: center;
  height: 20px;
}

.parent-indicator {
  margin-left: 4px;
}

.hierarchy-item {
  border-left: 2px solid #e0e0e0;
  margin-left: 8px;
}

.parent-item {
  font-weight: 500;
  background-color: rgba(25, 118, 210, 0.05);
}

.hierarchy-info {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.drop-indicator {
  position: absolute;
  top: 50%;
  right: 16px;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(25, 118, 210, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #1976d2;
}

.draggable-table {
  user-select: none;
}

.stats-card {
  transition: transform 0.2s ease;
}

.stats-card:hover {
  transform: translateY(-2px);
}

</style>
