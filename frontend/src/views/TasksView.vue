<template>
  <v-container>
    <!-- Header with Actions -->
    <v-row align="center" class="mb-4">
      <v-col>
        <h1 class="text-h4">Tasks</h1>
      </v-col>
      <v-col cols="auto">
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="showCreateDialog = true"
        >
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
    <v-row class="mb-4">
      <v-col cols="12" md="4">
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
        <v-select
          v-model="categoryFilter"
          :items="categoryOptions"
          label="Category"
          variant="outlined"
          density="compact"
          clearable
          hide-details
        />
      </v-col>
      <v-col cols="12" md="2">
        <v-btn
          variant="outlined"
          @click="clearFilters"
          block
        >
          Clear Filters
        </v-btn>
      </v-col>
    </v-row>

    <!-- Tasks Table -->
    <v-card>
      <v-data-table
        :headers="headers"
        :items="filteredTasks"
        :search="search"
        :loading="loading"
        :items-per-page="10"
        class="elevation-0"
        data-table
      >
        <!-- Loading State -->
        <template v-slot:loading>
          <MascotLoader 
            variant="working"
            :size="60"
            text="Loading tasks..."
          />
        </template>

        <!-- Status Column -->
        <template v-slot:item.status="{ item }">
          <v-chip
            :color="getStatusColor(item.status)"
            size="small"
            variant="flat"
          >
            <v-icon start size="x-small">{{ getStatusIcon(item.status) }}</v-icon>
            {{ item.status }}
          </v-chip>
        </template>

        <!-- Priority Column -->
        <template v-slot:item.priority="{ item }">
          <v-chip
            :color="getPriorityColor(item.priority)"
            size="small"
            label
          >
            {{ item.priority }}
          </v-chip>
        </template>

        <!-- Title Column -->
        <template v-slot:item.title="{ item }">
          <div>
            <div class="font-weight-medium">{{ item.title }}</div>
            <div class="text-caption text-medium-emphasis">{{ item.description }}</div>
          </div>
        </template>

        <!-- Assigned To Column -->
        <template v-slot:item.assigned_to="{ item }">
          <v-chip
            v-if="item.assigned_to"
            size="small"
            prepend-icon="mdi-robot"
          >
            {{ item.assigned_to }}
          </v-chip>
          <span v-else class="text-medium-emphasis">Unassigned</span>
        </template>

        <!-- Due Date Column -->
        <template v-slot:item.due_date="{ item }">
          <div v-if="item.due_date">
            <v-icon
              v-if="isOverdue(item.due_date)"
              color="error"
              size="x-small"
              class="mr-1"
            >
              mdi-alert
            </v-icon>
            {{ formatDate(item.due_date) }}
          </div>
          <span v-else class="text-medium-emphasis">No due date</span>
        </template>

        <!-- Actions Column -->
        <template v-slot:item.actions="{ item }">
          <v-btn
            icon="mdi-pencil"
            size="small"
            variant="text"
            @click="editTask(item)"
            aria-label="Edit task"
          />
          <v-btn
            v-if="item.status !== 'completed'"
            icon="mdi-check"
            size="small"
            variant="text"
            color="success"
            @click="completeTask(item)"
            aria-label="Mark as complete"
          />
          <v-btn
            icon="mdi-delete"
            size="small"
            variant="text"
            color="error"
            @click="deleteTask(item)"
            aria-label="Delete task"
          />
        </template>

        <!-- No Data -->
        <template v-slot:no-data>
          <div class="text-center py-8">
            <MascotLoader
              type="image"
              variant="thinker"
              :size="80"
              :show-text="false"
            />
            <p class="text-h6 mt-4">No tasks found</p>
            <p class="text-body-2 text-medium-emphasis">
              {{ search || statusFilter || priorityFilter || categoryFilter ? 'Try adjusting your filters' : 'Create your first task to get started' }}
            </p>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create/Edit Task Dialog -->
    <v-dialog v-model="showTaskDialog" max-width="600">
      <v-card>
        <v-card-title>
          <v-icon class="mr-2">{{ editingTask ? 'mdi-pencil' : 'mdi-plus' }}</v-icon>
          {{ editingTask ? 'Edit Task' : 'Create Task' }}
        </v-card-title>
        
        <v-card-text>
          <v-form ref="taskForm">
            <v-text-field
              v-model="currentTask.title"
              label="Task Title"
              variant="outlined"
              :rules="[v => !!v || 'Title is required']"
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
              <v-col cols="6">
                <v-select
                  v-model="currentTask.assigned_to"
                  :items="agentOptions"
                  label="Assign To"
                  variant="outlined"
                  clearable
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
          <v-btn
            variant="text"
            @click="cancelTask"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            variant="flat"
            @click="saveTask"
            :loading="saving"
          >
            {{ editingTask ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTaskStore } from '@/stores/tasks'
import { useAgentStore } from '@/stores/agents'
import { format, isAfter } from 'date-fns'
import MascotLoader from '@/components/MascotLoader.vue'

// Stores
const taskStore = useTaskStore()
const agentStore = useAgentStore()

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

// Current task form
const currentTask = ref({
  title: '',
  description: '',
  status: 'pending',
  priority: 'medium',
  category: 'general',
  assigned_to: null,
  due_date: null
})

// Table headers
const headers = [
  { title: 'Status', key: 'status', width: '120' },
  { title: 'Priority', key: 'priority', width: '100' },
  { title: 'Task', key: 'title' },
  { title: 'Category', key: 'category', width: '120' },
  { title: 'Assigned To', key: 'assigned_to', width: '150' },
  { title: 'Due Date', key: 'due_date', width: '120' },
  { title: 'Actions', key: 'actions', sortable: false, width: '120' }
]

// Filter options
const statusOptions = ['pending', 'in_progress', 'completed', 'cancelled']
const priorityOptions = ['low', 'medium', 'high', 'critical']
const categoryOptions = ['general', 'feature', 'bug', 'improvement', 'documentation', 'testing']

// Computed
const loading = computed(() => taskStore.loading)
const tasks = computed(() => taskStore.tasks)

const agentOptions = computed(() => {
  return agentStore.agents.map(agent => agent.name)
})

const filteredTasks = computed(() => {
  let filtered = [...tasks.value]
  
  if (statusFilter.value) {
    filtered = filtered.filter(t => t.status === statusFilter.value)
  }
  
  if (priorityFilter.value) {
    filtered = filtered.filter(t => t.priority === priorityFilter.value)
  }
  
  if (categoryFilter.value) {
    filtered = filtered.filter(t => t.category === categoryFilter.value)
  }
  
  return filtered
})

const totalTasks = computed(() => tasks.value.length)
const pendingTasks = computed(() => tasks.value.filter(t => t.status === 'pending').length)
const inProgressTasks = computed(() => tasks.value.filter(t => t.status === 'in_progress').length)
const completedTasks = computed(() => tasks.value.filter(t => t.status === 'completed').length)

// Methods
function getStatusColor(status) {
  const colors = {
    pending: 'warning',
    in_progress: 'info',
    completed: 'success',
    cancelled: 'grey'
  }
  return colors[status] || 'grey'
}

function getStatusIcon(status) {
  const icons = {
    pending: 'mdi-clock-outline',
    in_progress: 'mdi-progress-clock',
    completed: 'mdi-check-circle',
    cancelled: 'mdi-cancel'
  }
  return icons[status] || 'mdi-help'
}

function getPriorityColor(priority) {
  const colors = {
    low: 'grey',
    medium: 'info',
    high: 'warning',
    critical: 'error'
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
    assigned_to: null,
    due_date: null
  }
}

async function saveTask() {
  const { valid } = await taskForm.value.validate()
  if (!valid) return
  
  saving.value = true
  try {
    if (editingTask.value) {
      await taskStore.updateTask(editingTask.value.id, currentTask.value)
    } else {
      await taskStore.createTask(currentTask.value)
    }
    cancelTask()
  } catch (error) {
    console.error('Failed to save task:', error)
  } finally {
    saving.value = false
  }
}

// Watch for dialog trigger
onMounted(() => {
  if (showCreateDialog.value) {
    showTaskDialog.value = true
  }
})

// Lifecycle
onMounted(async () => {
  await Promise.all([
    taskStore.fetchTasks(),
    agentStore.fetchAgents()
  ])
})
</script>
