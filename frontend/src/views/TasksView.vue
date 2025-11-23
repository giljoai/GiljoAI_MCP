<template>
  <v-container>
    <!-- Header -->
    <v-row align="center" class="mb-4">
      <v-col>
        <h1 class="text-h4">Tasks</h1>
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

    <!-- Tasks Table -->
    <v-card class="task-table-card">
      <!-- Table Controls -->
      <v-card-title class="d-flex align-center py-3 bg-primary text-white">
        <span class="text-h6">Tasks</span>
        <v-spacer />
        <v-btn
          color="white"
          variant="outlined"
          prepend-icon="mdi-plus"
          @click="showTaskDialog = true"
        >
          New Task
        </v-btn>
      </v-card-title>

      <div class="table-wrapper">
        <v-data-table
          :headers="headers"
          :items="hierarchicalTasks"
          :search="search"
          :loading="loading"
          :items-per-page="25"
          class="elevation-0 scrollable-table"
          data-table
          item-value="id"
          height="600"
        >
          <!-- Loading State -->
          <template v-slot:loading>
            <div class="text-center pa-4">
              <v-progress-circular indeterminate color="primary" size="48" />
              <p class="text-body-2 text-medium-emphasis mt-2">Loading tasks...</p>
            </div>
          </template>

          <!-- Status Column - Inline Dropdown -->
          <template v-slot:item.status="{ item }">
            <div class="d-flex justify-center">
              <v-select
                :model-value="item.status"
                @update:model-value="(newStatus) => updateTaskField(item, 'status', newStatus)"
                :items="statusOptions"
                variant="plain"
                density="compact"
                hide-details
                class="inline-select inline-select-no-arrow"
              >
                <template v-slot:selection="{ item: statusItem }">
                  <v-chip
                    :color="getStatusColor(statusItem.value)"
                    size="small"
                    variant="flat"
                    class="status-chip"
                  >
                    <v-icon start size="x-small">{{ getStatusIcon(statusItem.value) }}</v-icon>
                    {{ statusItem.value }}
                  </v-chip>
                </template>
                <template v-slot:item="{ props, item: statusItem }">
                  <v-list-item v-bind="props">
                    <template v-slot:prepend>
                      <v-icon :color="getStatusColor(statusItem.value)" size="small">
                        {{ getStatusIcon(statusItem.value) }}
                      </v-icon>
                    </template>
                  </v-list-item>
                </template>
              </v-select>
            </div>
          </template>

          <!-- Priority Column - Inline Dropdown -->
          <template v-slot:item.priority="{ item }">
            <v-select
              :model-value="item.priority"
              @update:model-value="(newPriority) => updateTaskField(item, 'priority', newPriority)"
              :items="priorityOptions"
              variant="plain"
              density="compact"
              hide-details
              class="inline-select inline-select-no-arrow"
            >
              <template v-slot:selection="{ item: priorityItem }">
                <v-chip :color="getPriorityColor(priorityItem.value)" size="small" label>
                  {{ priorityItem.value }}
                </v-chip>
              </template>
              <template v-slot:item="{ props, item: priorityItem }">
                <v-list-item v-bind="props">
                  <template v-slot:prepend>
                    <v-chip :color="getPriorityColor(priorityItem.value)" size="x-small" label />
                  </template>
                </v-list-item>
              </template>
            </v-select>
          </template>

          <!-- Title Column with Hierarchy and Drag Support -->
          <template v-slot:item.title="{ item }">
            <div
              class="task-row-content"
              :data-test="`task-row-${item.id}`"
              @click="editTask(item)"
              style="cursor: pointer"
            >
              <!-- Task Content -->
              <div class="task-content flex-grow-1">
                <div class="d-flex align-center">
                  <span class="font-weight-medium">{{ item.title }}</span>
                </div>
                <div class="text-caption text-medium-emphasis description-truncate">
                  {{ item.description }}
                </div>
              </div>
            </div>
          </template>

          <!-- Category Column - Inline Dropdown -->
          <template v-slot:item.category="{ item }">
            <div class="d-flex justify-center">
              <v-select
                :model-value="item.category"
                @update:model-value="
                  (newCategory) => updateTaskField(item, 'category', newCategory)
                "
                :items="categoryOptions"
                variant="plain"
                density="compact"
                hide-details
                class="inline-select inline-select-no-arrow"
              >
                <template v-slot:selection="{ item: categoryItem }">
                  <span class="category-text">{{ categoryItem.value }}</span>
                </template>
              </v-select>
            </div>
          </template>

          <!-- Created By User Column (Phase 4) -->
          <template v-slot:item.created_by_user_id="{ item }">
            <v-chip size="small" variant="outlined">
              <v-icon start size="small">mdi-account-circle</v-icon>
              {{ getUserName(item.created_by_user_id) }}
            </v-chip>
          </template>

          <!-- Due Date Column - Inline Calendar Picker -->
          <template v-slot:item.due_date="{ item }">
            <v-menu
              :close-on-content-click="false"
              transition="scale-transition"
              :offset="[0, 50]"
              location="bottom"
            >
              <template v-slot:activator="{ props }">
                <div v-bind="props" class="date-text-clickable" style="cursor: pointer">
                  <v-icon
                    v-if="item.due_date && isOverdue(item.due_date)"
                    color="error"
                    size="x-small"
                    class="mr-1"
                  >
                    mdi-alert
                  </v-icon>
                  <span v-if="item.due_date">{{ formatDate(item.due_date) }}</span>
                  <span v-else class="text-medium-emphasis">Set date</span>
                </div>
              </template>
              <v-card class="compact-date-picker">
                <v-card-title class="py-2 px-3" style="background-color: #ffc300">
                  <span class="text-subtitle-2">Select Date</span>
                </v-card-title>
                <v-date-picker
                  :model-value="item.due_date ? new Date(item.due_date) : null"
                  @update:model-value="(newDate) => updateTaskDueDate(item, newDate)"
                  color="primary"
                  hide-header
                  width="280"
                />
              </v-card>
            </v-menu>
          </template>

          <!-- Convert Column -->
          <template v-slot:item.convert="{ item }">
            <div class="d-flex justify-center">
              <v-btn
                v-if="item.status !== 'completed' && !item.converted_project_id"
                icon
                size="small"
                variant="text"
                color="#ffc300"
                @click.stop="convertTaskToProject(item)"
              >
                <v-icon>mdi-folder-arrow-up</v-icon>
                <v-tooltip activator="parent" location="top"> Convert to Project </v-tooltip>
              </v-btn>
              <span v-else class="text-medium-emphasis">—</span>
            </div>
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

                <v-list-item v-if="item.status !== 'completed'" @click="convertTaskToProject(item)">
                  <template v-slot:prepend>
                    <v-icon>mdi-folder-arrow-up</v-icon>
                  </template>
                  <v-list-item-title>Convert to Project</v-list-item-title>
                </v-list-item>

                <v-list-item v-if="item.status !== 'completed'" @click="completeTask(item)">
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
      </div>
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

    <!-- No Active Product Warning Dialog -->
    <v-dialog v-model="showNoProductDialog" max-width="500" persistent>
      <v-card>
        <v-card-title class="d-flex align-center py-4" style="background-color: #ffc300">
          <v-icon class="mr-2" size="large">mdi-alert-circle</v-icon>
          <span class="text-h6">No Active Product</span>
        </v-card-title>
        <v-card-text class="pt-6 pb-4">
          <p class="text-body-1">
            No products are set to active state. Please activate a product before converting tasks
            to projects.
          </p>
        </v-card-text>
        <v-card-actions class="pb-4 px-4">
          <v-spacer />
          <v-btn color="primary" variant="flat" @click="showNoProductDialog = false"> OK </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Conversion Confirmation Dialog -->
    <v-dialog v-model="showConversionConfirmDialog" max-width="500" persistent>
      <v-card>
        <v-card-title class="d-flex align-center py-4" style="background-color: #ffc300">
          <v-icon class="mr-2" size="large">mdi-folder-arrow-up</v-icon>
          <span class="text-h6">Convert to Project</span>
        </v-card-title>
        <v-card-text class="pt-6 pb-4">
          <p class="text-body-1">
            Convert task <strong>"{{ conversionTaskName }}"</strong> to a project?
          </p>
          <p class="text-body-2 text-medium-emphasis mt-2">
            This will create a new project in the active product with the task's title and
            description.
          </p>
        </v-card-text>
        <v-card-actions class="pb-4 px-4">
          <v-spacer />
          <v-btn variant="text" @click="showConversionConfirmDialog = false"> Cancel </v-btn>
          <v-btn color="primary" variant="flat" @click="confirmConversion"> Convert </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="showDeleteConfirmDialog" max-width="500" persistent>
      <v-card>
        <v-card-title
          class="d-flex align-center py-4"
          style="background-color: #f44336; color: white"
        >
          <v-icon class="mr-2" size="large" color="white">mdi-delete-alert</v-icon>
          <span class="text-h6">Delete Task</span>
        </v-card-title>
        <v-card-text class="pt-6 pb-4">
          <p class="text-body-1">
            Are you sure you want to delete <strong>"{{ deleteTaskName }}"</strong>?
          </p>
          <p class="text-body-2 text-medium-emphasis mt-2">This action cannot be undone.</p>
        </v-card-text>
        <v-card-actions class="pb-4 px-4">
          <v-spacer />
          <v-btn variant="text" @click="showDeleteConfirmDialog = false"> Cancel </v-btn>
          <v-btn color="error" variant="flat" @click="confirmDelete"> Delete </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Success Dialog -->
    <v-dialog v-model="showSuccessDialog" max-width="500">
      <v-card>
        <v-card-title
          class="d-flex align-center py-4"
          style="background-color: #4caf50; color: white"
        >
          <v-icon class="mr-2" size="large" color="white">mdi-check-circle</v-icon>
          <span class="text-h6">Success</span>
        </v-card-title>
        <v-card-text class="pt-6 pb-4">
          <p class="text-body-1">{{ successMessage }}</p>
        </v-card-text>
        <v-card-actions class="pb-4 px-4">
          <v-spacer />
          <v-btn color="success" variant="flat" @click="showSuccessDialog = false"> OK </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Error Dialog -->
    <v-dialog v-model="showErrorDialog" max-width="500">
      <v-card>
        <v-card-title
          class="d-flex align-center py-4"
          style="background-color: #f44336; color: white"
        >
          <v-icon class="mr-2" size="large" color="white">mdi-alert-circle</v-icon>
          <span class="text-h6">Error</span>
        </v-card-title>
        <v-card-text class="pt-6 pb-4">
          <p class="text-body-1">{{ errorMessage }}</p>
        </v-card-text>
        <v-card-actions class="pb-4 px-4">
          <v-spacer />
          <v-btn color="error" variant="flat" @click="showErrorDialog = false"> OK </v-btn>
        </v-card-actions>
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

// Dialog state
const showNoProductDialog = ref(false)
const showConversionConfirmDialog = ref(false)
const showDeleteConfirmDialog = ref(false)
const showSuccessDialog = ref(false)
const showErrorDialog = ref(false)
const conversionTaskName = ref('')
const deleteTaskName = ref('')
const currentConvertingTask = ref(null)
const currentDeletingTask = ref(null)
const successMessage = ref('')
const errorMessage = ref('')

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
  { title: 'Status', key: 'status', width: '140', align: 'center' },
  { title: 'Priority', key: 'priority', width: '110' },
  { title: 'Task', key: 'title' },
  { title: 'Category', key: 'category', width: '120', align: 'center' },
  // Hidden for now - may be relevant in future
  // { title: 'Created By', key: 'created_by_user_id', width: '150' },
  { title: 'Due Date', key: 'due_date', width: '120' },
  { title: 'Convert', key: 'convert', width: '80', align: 'center', sortable: false },
  { title: 'Actions', key: 'actions', sortable: false, width: '120' },
]

// Filter options
const statusOptions = ['pending', 'in_progress', 'completed', 'cancelled']
const priorityOptions = ['low', 'medium', 'high', 'critical']
const categoryOptions = ['general', 'feature', 'bug', 'improvement', 'docs', 'testing']

// Computed
const loading = computed(() => taskStore.loading)
const tasks = computed(() => taskStore.tasks)

// Product-filtered tasks
const userFilteredTasks = computed(() => {
  if (taskFilter.value === 'product_tasks') {
    // Show tasks for active product only
    const productId = productStore.effectiveProductId
    if (!productId) {
      return [] // No active product, return empty list
    }
    return tasks.value.filter((task) => task.product_id === productId)
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
  const productId = productStore.effectiveProductId
  if (productId) {
    filteredList = filteredList.filter((t) => t.product_id === productId)
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

// Hierarchy feature disabled - return filtered tasks directly
const hierarchicalTasks = computed(() => {
  return filteredTasks.value
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

// Inline editing helper functions
async function updateTaskField(task, field, value) {
  try {
    await taskStore.updateTask(task.id, { [field]: value })
  } catch (error) {
    console.error(`Failed to update task ${field}:`, error)
    errorMessage.value = `Failed to update ${field}`
    showErrorDialog.value = true
  }
}

async function updateTaskDueDate(task, newDate) {
  try {
    // Format date as YYYY-MM-DD
    const formattedDate = newDate ? format(new Date(newDate), 'yyyy-MM-dd') : null
    await taskStore.updateTask(task.id, { due_date: formattedDate })
  } catch (error) {
    console.error('Failed to update due date:', error)
    errorMessage.value = 'Failed to update due date'
    showErrorDialog.value = true
  }
}

async function convertTaskToProject(task) {
  // Check if there's an active product using effectiveProductId
  if (!productStore.effectiveProductId) {
    showNoProductDialog.value = true
    return
  }

  // Show conversion confirmation dialog
  conversionTaskName.value = task.title
  currentConvertingTask.value = task
  showConversionConfirmDialog.value = true
}

async function confirmConversion() {
  showConversionConfirmDialog.value = false
  const task = currentConvertingTask.value

  if (!task) return

  try {
    const response = await api.tasks.convertToProject(task.id)
    await taskStore.fetchTasks()

    // Show success dialog
    successMessage.value = `Task successfully converted to project: ${response.data.name}`
    showSuccessDialog.value = true
  } catch (error) {
    console.error('Error converting task to project:', error)
    const errorMsg = error.response?.data?.detail || 'Failed to convert task to project'

    // Show error dialog
    errorMessage.value = errorMsg
    showErrorDialog.value = true
  }

  currentConvertingTask.value = null
}

async function deleteTask(task) {
  // Show branded delete confirmation dialog
  deleteTaskName.value = task.title
  currentDeletingTask.value = task
  showDeleteConfirmDialog.value = true
}

async function confirmDelete() {
  showDeleteConfirmDialog.value = false
  const task = currentDeletingTask.value

  if (!task) return

  try {
    await taskStore.deleteTask(task.id)
    successMessage.value = `Task "${task.title}" deleted successfully`
    showSuccessDialog.value = true
  } catch (error) {
    console.error('Failed to delete task:', error)
    errorMessage.value = 'Failed to delete task'
    showErrorDialog.value = true
  }

  currentDeletingTask.value = null
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

async function saveTask() {
  const { valid } = await taskForm.value.validate()
  if (!valid) return

  saving.value = true
  try {
    if (editingTask.value) {
      // Exclude parent_task_id from updates (feature not used)
      const { parent_task_id, ...taskData } = currentTask.value
      await taskStore.updateTask(editingTask.value.id, taskData)
    } else {
      // Add current product_id to new task
      const productId = productStore.effectiveProductId
      if (productId) {
        currentTask.value.product_id = productId
      }
      // Exclude parent_task_id from creation (feature not used)
      const { parent_task_id, ...taskData } = currentTask.value
      await taskStore.createTask(taskData)
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

// Helper function to get user name
function getUserName(userId) {
  if (!userId) return 'Unknown'
  // If it's the current user, return their username
  if (userStore.currentUser?.id === userId) {
    return userStore.currentUser.username
  }
  // Otherwise return a placeholder (could be enhanced with user lookup API later)
  return 'User'
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
  try {
    await Promise.all([fetchTasks(), agentStore.fetchAgents()])
  } catch (error) {
    console.error('Failed to initialize TasksView:', error)
  }
})
</script>

<style scoped>
/* Scrollable Table Styles */
.task-table-card {
  max-height: calc(100vh - 450px);
  min-height: 600px;
  display: flex;
  flex-direction: column;
}

.table-wrapper {
  flex: 1;
  overflow: auto;
  max-height: 600px;
}

.scrollable-table {
  height: 100%;
}

.scrollable-table :deep(.v-table__wrapper) {
  overflow-y: auto;
  max-height: 600px;
}

/* Inline editing styles */
.inline-select :deep(.v-field) {
  border: none;
  box-shadow: none;
}

.inline-select :deep(.v-field__input) {
  padding: 0;
  min-height: auto;
}

.inline-select:hover :deep(.v-field) {
  background-color: rgba(0, 0, 0, 0.04);
  border-radius: 4px;
}

/* Compact date picker styling */
.compact-date-picker {
  max-width: 280px;
}

.compact-date-picker :deep(.v-date-picker-month) {
  padding: 8px;
}

.compact-date-picker :deep(.v-date-picker-header) {
  padding: 4px 8px;
}

/* Hide arrow indicator for category column */
.inline-select-no-arrow :deep(.v-field__append-inner) {
  display: none;
}

.category-text {
  cursor: pointer;
  padding: 4px 8px;
  display: inline-block;
}

.category-text:hover {
  background-color: rgba(0, 0, 0, 0.04);
  border-radius: 4px;
}

/* Date text clickable styling */
.date-text-clickable {
  padding: 4px 8px;
  border-radius: 4px;
  display: inline-block;
  transition: background-color 0.2s ease;
}

.date-text-clickable:hover {
  background-color: rgba(0, 0, 0, 0.04);
}

.task-row-content {
  display: flex;
  align-items: center;
  padding: 8px 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
  min-height: 48px;
}

.task-row-content:hover {
  background-color: rgba(0, 0, 0, 0.04);
}

/* Hierarchy CSS removed - feature not used */

.stats-card {
  transition: transform 0.2s ease;
}

.stats-card:hover {
  transform: translateY(-2px);
}

/* Truncate description to 2 lines */
.description-truncate {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
  max-height: 2.8em; /* 2 lines × 1.4 line-height */
}

/* Status chip centered text with compact sizing */
.status-chip {
  justify-content: center;
  padding: 4px 10px !important;
  min-width: 100px !important;
  max-width: 100px !important;
}

.status-chip :deep(.v-chip__content) {
  display: flex !important;
  align-items: center !important;
  gap: 4px !important;
  padding: 0 !important;
}

.status-chip :deep(.v-icon) {
  margin: 0 !important;
  flex-shrink: 0 !important;
}

/* Status column - allow badge overflow and remove constraints */
.inline-select :deep(.v-field__input) {
  overflow: visible !important;
}

.inline-select :deep(.v-input__control) {
  overflow: visible !important;
}

.inline-select :deep(.v-field__field) {
  overflow: visible !important;
}

/* Fix dropdown menu icons being cut off */
.inline-select :deep(.v-list-item) {
  padding-left: 16px !important;
  padding-right: 16px !important;
}

.inline-select :deep(.v-list-item__prepend) {
  margin-right: 12px !important;
}

.inline-select :deep(.v-list-item__prepend .v-icon) {
  margin: 0 !important;
}
</style>
