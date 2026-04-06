import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useTaskCrud } from './useTaskCrud'

const mockUpdateTask = vi.fn(() => Promise.resolve())
const mockCreateTask = vi.fn(() => Promise.resolve())
const mockFetchTasks = vi.fn(() => Promise.resolve())

vi.mock('@/stores/tasks', () => ({
  useTaskStore: () => ({
    updateTask: mockUpdateTask,
    createTask: mockCreateTask,
    fetchTasks: mockFetchTasks,
    tasks: [],
    loading: false,
  }),
}))

vi.mock('@/stores/products', () => ({
  useProductStore: () => ({
    effectiveProductId: 'product-1',
    currentProductId: 'product-1',
  }),
}))

describe('useTaskCrud', () => {
  let crud

  beforeEach(() => {
    vi.clearAllMocks()
    crud = useTaskCrud()
  })

  it('initializes with dialog closed and no editing task', () => {
    expect(crud.showTaskDialog.value).toBe(false)
    expect(crud.editingTask.value).toBeNull()
    expect(crud.saving.value).toBe(false)
  })

  it('initializes currentTask with default values', () => {
    expect(crud.currentTask.value.title).toBe('')
    expect(crud.currentTask.value.status).toBe('pending')
    expect(crud.currentTask.value.priority).toBe('medium')
    expect(crud.currentTask.value.category).toBe('general')
    expect(crud.currentTask.value.due_date).toBeNull()
  })

  it('editTask sets editingTask and opens dialog', () => {
    const task = { id: 1, title: 'Test', status: 'pending', priority: 'high', category: 'bug', due_date: null }
    crud.editTask(task)
    expect(crud.editingTask.value).toEqual(task)
    expect(crud.currentTask.value.title).toBe('Test')
    expect(crud.showTaskDialog.value).toBe(true)
  })

  it('cancelTask resets state and closes dialog', () => {
    crud.editTask({ id: 1, title: 'Test', status: 'pending', priority: 'high', category: 'bug' })
    crud.cancelTask()

    expect(crud.showTaskDialog.value).toBe(false)
    expect(crud.showCreateDialog.value).toBe(false)
    expect(crud.editingTask.value).toBeNull()
    expect(crud.currentTask.value.title).toBe('')
    expect(crud.currentTask.value.status).toBe('pending')
  })

  it('handleNewTask opens dialog when product is active', () => {
    crud.handleNewTask()
    expect(crud.showTaskDialog.value).toBe(true)
  })

  it('completeTask calls store updateTask with completed status', async () => {
    const task = { id: 42, title: 'Do something', status: 'pending' }
    await crud.completeTask(task)
    expect(mockUpdateTask).toHaveBeenCalledWith(42, { status: 'completed' })
  })

  it('updateTaskField calls store updateTask with the given field', async () => {
    const task = { id: 5, title: 'task', status: 'pending' }
    await crud.updateTaskField(task, 'status', 'in_progress')
    expect(mockUpdateTask).toHaveBeenCalledWith(5, { status: 'in_progress' })
  })

  it('updateTaskDueDate formats and calls store updateTask', async () => {
    const task = { id: 7, title: 'task' }
    // Use a local-time date to avoid UTC-midnight timezone shift
    const localDate = new Date(2025, 5, 15) // month is 0-indexed: June = 5
    await crud.updateTaskDueDate(task, localDate)
    expect(mockUpdateTask).toHaveBeenCalledWith(7, { due_date: '2025-06-15' })
  })

  it('updateTaskDueDate passes null when no date provided', async () => {
    const task = { id: 8, title: 'task' }
    await crud.updateTaskDueDate(task, null)
    expect(mockUpdateTask).toHaveBeenCalledWith(8, { due_date: null })
  })
})
