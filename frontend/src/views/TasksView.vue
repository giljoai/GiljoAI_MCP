<template>
  <v-container>
    <!-- Header -->
    <v-row align="center" class="mb-4">
      <v-col>
        <div class="d-flex align-center">
          <h1 class="text-h4">Tasks</h1>
          <v-tooltip location="bottom start" max-width="600">
            <template #activator="{ props }">
              <v-icon v-bind="props" size="18" color="medium-emphasis" class="ml-2">mdi-information-outline</v-icon>
            </template>
            <div>
              <div class="font-weight-bold mb-1">Task Field Reference</div>
              <div class="text-caption text-medium-emphasis mb-2">Instructions for /gil_add</div>
              <div><span class="font-weight-medium">title (required):</span> Free text</div>
              <div class="mt-1"><span class="font-weight-medium">description (recommended):</span> Free text</div>
              <div class="mt-1"><span class="font-weight-medium">status (optional):</span></div>
              <div class="ml-2 text-caption">pending · in_progress · completed · blocked · cancelled · converted</div>
              <div class="mt-1"><span class="font-weight-medium">priority (optional):</span></div>
              <div class="ml-2 text-caption">low · medium · high · critical</div>
              <div class="mt-1"><span class="font-weight-medium">category (optional):</span></div>
              <div class="ml-2 text-caption">general · feature · bug · improvement · docs · testing</div>
              <div class="mt-2"><span class="font-weight-medium">Example:</span></div>
              <div class="ml-2 text-caption">/gil_add add task ... description ...</div>
            </div>
          </v-tooltip>
        </div>
        <p class="text-body-2 text-medium-emphasis mt-1">Use MCP tool /gil_add to have the AI coding agent add ideas and thoughts to Task dashboard.</p>
      </v-col>
    </v-row>

    <!-- Filters Row -->
    <v-row class="mb-4" align="center">
      <v-col cols="12" md="4">
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="Search tasks"
          variant="outlined"
          density="compact"
          clearable
          hide-details
          aria-label="Search tasks by title"
          data-search-input
        />
      </v-col>
      <v-col cols="12" md="3">
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
      <v-col cols="12" md="3">
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
        <v-btn variant="outlined" block @click="clearFilters"> Clear Filters </v-btn>
      </v-col>
    </v-row>

    <!-- Tasks Table -->
    <v-card class="task-table-card">
      <!-- Table Controls -->
      <v-card-title class="d-flex align-center justify-space-between px-4 py-3 border-b">
        <span class="text-h6">Task List</span>
        <v-btn
          color="primary"
          variant="flat"
          prepend-icon="mdi-plus"
          @click="handleNewTask"
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
                :items="statusOptions"
                variant="plain"
                density="compact"
                hide-details
                class="inline-select inline-select-no-arrow"
                @update:model-value="(newStatus) => updateTaskField(item, 'status', newStatus)"
              >
                <template v-slot:selection="{ item: statusItem }">
                  <v-chip
                    :color="getStatusColor(statusItem.value)"
                    :style="getStatusTextStyle(statusItem.value)"
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
              :items="priorityOptions"
              variant="plain"
              density="compact"
              hide-details
              class="inline-select inline-select-no-arrow"
              @update:model-value="(newPriority) => updateTaskField(item, 'priority', newPriority)"
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
              style="cursor: pointer"
              @click="editTask(item)"
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
                :items="categoryOptions"
                variant="plain"
                density="compact"
                hide-details
                class="inline-select inline-select-no-arrow"
                @update:model-value="
                  (newCategory) => updateTaskField(item, 'category', newCategory)
                "
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
                <v-card-title class="py-2 px-3 bg-primary">
                  <span class="text-subtitle-2">Select Date</span>
                </v-card-title>
                <v-date-picker
                  :model-value="item.due_date ? new Date(item.due_date) : null"
                  color="primary"
                  hide-header
                  width="280"
                  @update:model-value="(newDate) => updateTaskDueDate(item, newDate)"
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
                color="primary"
                aria-label="Convert to project"
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
                <v-btn icon="mdi-dots-vertical" size="small" variant="text" v-bind="props" aria-label="Task actions" />
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
    <v-dialog v-model="showTaskDialog" max-width="600" persistent>
      <v-card v-draggable>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">{{ editingTask ? 'mdi-pencil' : 'mdi-plus' }}</v-icon>
          <span>{{ editingTask ? 'Edit Task' : 'Create Task' }}</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" aria-label="Close" @click="cancelTask" />
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
          <v-btn color="primary" variant="flat" :loading="saving" @click="saveTask">
            {{ editingTask ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- No Active Product Warning Dialog -->
    <BaseDialog
      v-model="showNoProductDialog"
      type="warning"
      title="No Active Product"
      confirm-label="OK"
      cancel-text=""
      @confirm="showNoProductDialog = false"
    >
      <p class="text-body-1">
        No products are set to active state. Please activate a product before creating or converting tasks.
      </p>
    </BaseDialog>

    <!-- Conversion Confirmation Dialog -->
    <BaseDialog
      v-model="showConversionConfirmDialog"
      type="info"
      title="Convert to Project"
      icon="mdi-folder-arrow-up"
      confirm-label="Convert"
      @confirm="confirmConversion"
      @cancel="showConversionConfirmDialog = false"
    >
      <p class="text-body-1 mb-2">
        Convert task <strong>"{{ conversionTaskName }}"</strong> to a project?
      </p>
      <p class="text-body-2 text-medium-emphasis">
        This will create a new project in the active product with the task's title and
        description.
      </p>
    </BaseDialog>

    <!-- Delete Confirmation Dialog -->
    <BaseDialog
      v-model="showDeleteConfirmDialog"
      type="danger"
      title="Delete Task"
      icon="mdi-delete-alert"
      confirm-label="Delete"
      @confirm="confirmDelete"
      @cancel="showDeleteConfirmDialog = false"
    >
      <p class="text-body-1 mb-2">
        Are you sure you want to delete <strong>"{{ deleteTaskName }}"</strong>?
      </p>
      <v-alert type="info" variant="tonal" density="compact">
        This action cannot be undone.
      </v-alert>
    </BaseDialog>

    <!-- Success Dialog -->
    <BaseDialog
      v-model="showSuccessDialog"
      type="success"
      title="Success"
      confirm-label="OK"
      :persistent="false"
      @confirm="showSuccessDialog = false"
    >
      <p class="text-body-1">{{ successMessage }}</p>
    </BaseDialog>

    <!-- Error Dialog -->
    <BaseDialog
      v-model="showErrorDialog"
      type="danger"
      title="Error"
      confirm-label="OK"
      :persistent="false"
      @confirm="showErrorDialog = false"
    >
      <p class="text-body-1">{{ errorMessage }}</p>
    </BaseDialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTaskStore } from '@/stores/tasks'
import { useProductStore } from '@/stores/products'
import { useUserStore } from '@/stores/user'
import { format, isAfter } from 'date-fns'
import api from '@/services/api'
import BaseDialog from '@/components/common/BaseDialog.vue'

// Stores
const taskStore = useTaskStore()
const productStore = useProductStore()
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

// Product-filtered tasks (all tasks are bound to a product - Handover 0433)
const userFilteredTasks = computed(() => {
  const productId = productStore.effectiveProductId
  if (!productId) {
    return []
  }
  return tasks.value.filter((task) => task.product_id === productId)
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

// Methods
function getStatusColor(status) {
  const colors = {
    pending: 'warning',
    in_progress: '#fff',
    completed: 'success',
    cancelled: '#c6298c',
  }
  return colors[status] || 'grey'
}

function getStatusTextStyle(status) {
  if (status === 'in_progress') return { color: '#333' }
  return {}
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

function handleNewTask() {
  if (!productStore.effectiveProductId) {
    showNoProductDialog.value = true
    return
  }
  showTaskDialog.value = true
}

async function saveTask() {
  const { valid } = await taskForm.value.validate()
  if (!valid) return

  saving.value = true
  try {
    if (editingTask.value) {
      // Exclude parent_task_id from updates (feature not used)
      const { parent_task_id: _parent_task_id, ...taskData } = currentTask.value
      await taskStore.updateTask(editingTask.value.id, taskData)
    } else {
      // Add current product_id to new task
      const productId = productStore.effectiveProductId
      if (productId) {
        currentTask.value.product_id = productId
      }
      // Exclude parent_task_id from creation (feature not used)
      const { parent_task_id: _parent_task_id, ...taskData } = currentTask.value
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

async function fetchTasks() {
  const params = {}

  if (productStore.currentProductId) {
    params.product_id = productStore.currentProductId
  }

  await taskStore.fetchTasks(params)
}

// Watch for dialog trigger
onMounted(() => {
  if (showCreateDialog.value) {
    showTaskDialog.value = true
  }
})

// Lifecycle
onMounted(async () => {
  try {
    await fetchTasks()
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
  padding: 4px 10px;
  min-width: 100px;
  max-width: 100px;
}

.status-chip :deep(.v-chip__content) {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0;
}

.status-chip :deep(.v-icon) {
  margin: 0;
  flex-shrink: 0;
}

/* Status column - allow badge overflow and remove constraints */
.inline-select :deep(.v-field__input) {
  overflow: visible;
}

.inline-select :deep(.v-input__control) {
  overflow: visible;
}

.inline-select :deep(.v-field__field) {
  overflow: visible;
}

/* Fix dropdown menu icons being cut off */
.inline-select :deep(.v-list-item) {
  padding-left: 16px;
  padding-right: 16px;
}

.inline-select :deep(.v-list-item__prepend) {
  margin-right: 12px;
}

.inline-select :deep(.v-list-item__prepend .v-icon) {
  margin: 0;
}
</style>
