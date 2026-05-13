/**
 * useTaskCrud Composable
 *
 * Encapsulates dialog state and CRUD operations for the task edit/create
 * workflow. Uses the task and product stores internally.
 *
 * Mirrors the project-side update/complete pattern (`useProjectCrud` /
 * `update_project` MCP tool) — `updateTask(id, fields)` is the single
 * write path; status changes flow through the same call (no
 * `updateTaskStatus`, on parity with how projects do it).
 *
 * @returns {{
 *   showTaskDialog, showCreateDialog, editingTask, saving, currentTask,
 *   editTask, cancelTask, saveTask, handleNewTask, completeTask,
 *   updateTask, updateTaskField, updateTaskDueDate
 * }}
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
  task_type: null,
  series_number: null,
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
    editingTask.value = null
    currentTask.value = DEFAULT_TASK()
    showTaskDialog.value = true
    return { noProduct: false }
  }

  /**
   * Update an arbitrary set of fields on a task. Mirrors the MCP
   * `update_task` tool surface — status flows through this call, there
   * is no separate `updateTaskStatus` (parity with how
   * `update_project` handles project status).
   *
   * @param {string} taskId
   * @param {object} fields - e.g. `{ status: 'in_progress' }` or
   *        `{ task_type: 'BE' }`. The store dispatches a PUT to
   *        `/api/v1/tasks/{id}/`.
   * @returns {Promise<object>} the updated task
   */
  async function updateTask(taskId, fields) {
    return await taskStore.updateTask(taskId, fields)
  }

  /**
   * Mark a task complete. Optional `notes` are accepted for parity
   * with the MCP `complete_task` tool, but the REST `TaskUpdate` schema
   * does not (yet) carry a completion-notes field — the param is
   * forwarded so that when the schema gains the field, no caller signature
   * needs to change. Until then it is a no-op on the wire.
   *
   * @param {string} taskId
   * @param {string} [notes]
   */
  async function completeTask(taskId, notes) {
    try {
      const fields = { status: 'completed' }
      if (notes != null && notes !== '') {
        fields.completion_notes = notes
      }
      return await taskStore.updateTask(taskId, fields)
    } catch (error) {
      console.error('Failed to complete task:', error)
      showToast({ message: 'Failed to complete task. Please try again.', type: 'error' })
      throw error
    }
  }

  /**
   * Convenience helper used by inline-edit dropdowns (status / priority /
   * task_type cells). Routes through `updateTask` so there's a single
   * write path.
   */
  async function updateTaskField(task, field, value) {
    try {
      await updateTask(task.id, { [field]: value })
    } catch (error) {
      console.error(`Failed to update task ${field}:`, error)
      throw error
    }
  }

  async function updateTaskDueDate(task, newDate) {
    try {
      const formattedDate = newDate ? format(new Date(newDate), 'yyyy-MM-dd') : null
      await updateTask(task.id, { due_date: formattedDate })
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
    updateTask,
    updateTaskField,
    updateTaskDueDate,
  }
}
