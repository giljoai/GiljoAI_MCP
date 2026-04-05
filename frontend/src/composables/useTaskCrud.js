/**
 * useTaskCrud Composable
 *
 * Encapsulates dialog state and CRUD operations for the task edit/create workflow.
 * Uses the task and product stores internally.
 *
 * Extracted from TasksView.vue (Handover 0950k).
 *
 * @returns {{ showTaskDialog, showCreateDialog, editingTask, saving, currentTask,
 *             editTask, cancelTask, saveTask, handleNewTask, completeTask,
 *             updateTaskField, updateTaskDueDate }}
 */
import { ref } from 'vue'
import { format } from 'date-fns'
import { useTaskStore } from '@/stores/tasks'
import { useProductStore } from '@/stores/products'
import { useToast } from '@/composables/useToast'

const DEFAULT_TASK = () => ({
  title: '',
  description: '',
  status: 'pending',
  priority: 'medium',
  category: 'general',
  due_date: null,
})

export function useTaskCrud() {
  const taskStore = useTaskStore()
  const productStore = useProductStore()
  const { showToast } = useToast()

  const showTaskDialog = ref(false)
  const showCreateDialog = ref(false)
  const editingTask = ref(null)
  const saving = ref(false)
  const currentTask = ref(DEFAULT_TASK())

  function editTask(task) {
    editingTask.value = task
    currentTask.value = { ...task }
    showTaskDialog.value = true
  }

  function cancelTask() {
    showTaskDialog.value = false
    showCreateDialog.value = false
    editingTask.value = null
    currentTask.value = DEFAULT_TASK()
  }

  function handleNewTask() {
    if (!productStore.effectiveProductId) {
      return { noProduct: true }
    }
    showTaskDialog.value = true
    return { noProduct: false }
  }

  async function completeTask(task) {
    try {
      await taskStore.updateTask(task.id, { status: 'completed' })
    } catch (error) {
      console.error('Failed to complete task:', error)
      showToast({ message: 'Failed to complete task. Please try again.', type: 'error' })
    }
  }

  async function updateTaskField(task, field, value) {
    try {
      await taskStore.updateTask(task.id, { [field]: value })
    } catch (error) {
      console.error(`Failed to update task ${field}:`, error)
      throw error
    }
  }

  async function updateTaskDueDate(task, newDate) {
    try {
      const formattedDate = newDate ? format(new Date(newDate), 'yyyy-MM-dd') : null
      await taskStore.updateTask(task.id, { due_date: formattedDate })
    } catch (error) {
      console.error('Failed to update due date:', error)
      throw error
    }
  }

  /**
   * Save the current task (create or update).
   * Requires a v-form ref for validation - pass the template ref from the parent component.
   *
   * @param {import('vue').Ref} taskForm - Template ref to the v-form element
   * @param {Function} afterSave - Optional callback run after successful save (e.g. fetchTasks)
   */
  async function saveTask(taskForm, afterSave) {
    const { valid } = await taskForm.value.validate()
    if (!valid) return

    saving.value = true
    try {
      if (editingTask.value) {
        const { parent_task_id: _parent, ...taskData } = currentTask.value
        await taskStore.updateTask(editingTask.value.id, taskData)
      } else {
        const productId = productStore.effectiveProductId
        if (productId) {
          currentTask.value.product_id = productId
        }
        const { parent_task_id: _parent, ...taskData } = currentTask.value
        await taskStore.createTask(taskData)
      }
      cancelTask()
      if (afterSave) {
        await afterSave()
      }
    } catch (error) {
      console.error('Failed to save task:', error)
      showToast({ message: 'Failed to save task. Please try again.', type: 'error' })
    } finally {
      saving.value = false
    }
  }

  return {
    showTaskDialog,
    showCreateDialog,
    editingTask,
    saving,
    currentTask,
    editTask,
    cancelTask,
    saveTask,
    handleNewTask,
    completeTask,
    updateTaskField,
    updateTaskDueDate,
  }
}
