import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'
import { TASK_STATUS } from '@/utils/constants'

export const useTaskStore = defineStore('tasks', () => {
  // State
  const tasks = ref([])
  const currentTask = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const tasksByStatus = computed(() => {
    const grouped = {}
    Object.values(TASK_STATUS).forEach(status => {
      grouped[status] = tasks.value.filter(t => t.status === status)
    })
    return grouped
  })
  
  const tasksByProject = computed(() => (projectId) =>
    tasks.value.filter(t => t.project_id === projectId)
  )
  
  const tasksByAgent = computed(() => (agentName) =>
    tasks.value.filter(t => t.assigned_to === agentName)
  )
  
  const pendingTasks = computed(() =>
    tasks.value.filter(t => t.status === TASK_STATUS.PENDING)
  )
  
  const inProgressTasks = computed(() =>
    tasks.value.filter(t => t.status === TASK_STATUS.IN_PROGRESS)
  )
  
  const completedTasks = computed(() =>
    tasks.value.filter(t => t.status === TASK_STATUS.COMPLETED)
  )

  const taskStats = computed(() => ({
    total: tasks.value.length,
    pending: pendingTasks.value.length,
    inProgress: inProgressTasks.value.length,
    completed: completedTasks.value.length,
    failed: tasks.value.filter(t => t.status === TASK_STATUS.FAILED).length
  }))

  // Actions
  async function fetchTasks(params = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await api.tasks.list(params)
      tasks.value = response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch tasks:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.tasks.get(id)
      currentTask.value = response.data
      
      // Update in list if exists
      const index = tasks.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tasks.value[index] = response.data
      }
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch task:', err)
    } finally {
      loading.value = false
    }
  }

  async function createTask(taskData) {
    loading.value = true
    error.value = null
    try {
      const response = await api.tasks.create(taskData)
      tasks.value.push(response.data)
      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to create task:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateTask(id, updates) {
    loading.value = true
    error.value = null
    try {
      const response = await api.tasks.update(id, updates)
      
      const index = tasks.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tasks.value[index] = response.data
      }
      
      if (currentTask.value?.id === id) {
        currentTask.value = response.data
      }
      
      return response.data
    } catch (err) {
      error.value = err.message
      console.error('Failed to update task:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteTask(id) {
    loading.value = true
    error.value = null
    try {
      await api.tasks.delete(id)
      
      tasks.value = tasks.value.filter(t => t.id !== id)
      
      if (currentTask.value?.id === id) {
        currentTask.value = null
      }
    } catch (err) {
      error.value = err.message
      console.error('Failed to delete task:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function changeTaskStatus(id, status) {
    try {
      const response = await api.tasks.changeStatus(id, status)
      
      const task = tasks.value.find(t => t.id === id)
      if (task) {
        task.status = status
        task.updated_at = new Date().toISOString()
        
        // Update progress based on status
        if (status === TASK_STATUS.COMPLETED) {
          task.progress = 100
        } else if (status === TASK_STATUS.IN_PROGRESS && task.progress === 0) {
          task.progress = 50
        }
      }
      
      return response.data
    } catch (err) {
      console.error('Failed to change task status:', err)
      throw err
    }
  }

  function moveTask(taskId, newStatus) {
    // Local update for drag-and-drop (optimistic update)
    const task = tasks.value.find(t => t.id === taskId)
    if (task) {
      const oldStatus = task.status
      task.status = newStatus
      
      // Sync with backend
      changeTaskStatus(taskId, newStatus).catch(() => {
        // Revert on error
        task.status = oldStatus
      })
    }
  }

  function updateTaskFromWebSocket(updatedTask) {
    const index = tasks.value.findIndex(t => t.id === updatedTask.id)
    if (index !== -1) {
      tasks.value[index] = { ...tasks.value[index], ...updatedTask }
    } else {
      // New task from WebSocket
      tasks.value.push(updatedTask)
    }
  }

  function clearError() {
    error.value = null
  }

  // Handle real-time updates from WebSocket
  function handleRealtimeUpdate(data) {
    const { 
      task_id, 
      project_id, 
      update_type, 
      title, 
      description, 
      status, 
      assigned_to, 
      priority,
      progress,
      completed_at 
    } = data
    
    // Find task by ID
    const taskIndex = tasks.value.findIndex(t => t.id === task_id)
    
    if (update_type === 'created' && taskIndex === -1) {
      // New task - add to list
      const newTask = {
        id: task_id,
        project_id,
        title,
        description,
        status: status || TASK_STATUS.PENDING,
        assigned_to,
        priority: priority || 'medium',
        progress: progress || 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
      
      tasks.value.push(newTask)
      
    } else if (taskIndex !== -1) {
      // Update existing task
      const task = tasks.value[taskIndex]
      
      if (update_type === 'status_changed' && status) {
        task.status = status
        if (status === TASK_STATUS.COMPLETED) {
          task.completed_at = completed_at || new Date().toISOString()
          task.progress = 100
        }
      }
      
      // Update other fields if provided
      if (title) task.title = title
      if (description) task.description = description
      if (assigned_to !== undefined) task.assigned_to = assigned_to
      if (priority) task.priority = priority
      if (progress !== undefined) task.progress = progress
      
      task.updated_at = new Date().toISOString()
      
      // Update current task if it's the same
      if (currentTask.value?.id === task_id) {
        currentTask.value = { ...task }
      }
    } else if (task_id && update_type === 'created') {
      // Unknown task - fetch updated list
      fetchTasks({ project_id })
    }
  }

  return {
    // State
    tasks,
    currentTask,
    loading,
    error,
    
    // Getters
    tasksByStatus,
    tasksByProject,
    tasksByAgent,
    pendingTasks,
    inProgressTasks,
    completedTasks,
    taskStats,
    
    // Actions
    fetchTasks,
    fetchTask,
    createTask,
    updateTask,
    deleteTask,
    changeTaskStatus,
    moveTask,
    updateTaskFromWebSocket,
    clearError,
    handleRealtimeUpdate
  }
})