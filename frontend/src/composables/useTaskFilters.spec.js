import { describe, it, expect, beforeEach } from 'vitest'
import { ref } from 'vue'
import { useTaskFilters } from './useTaskFilters'

describe('useTaskFilters', () => {
  const makeTasks = () => [
    { id: 1, title: 'Fix login bug', status: 'pending', priority: 'high', category: 'bug' },
    { id: 2, title: 'Add dashboard feature', status: 'in_progress', priority: 'medium', category: 'feature' },
    { id: 3, title: 'Write docs', status: 'completed', priority: 'low', category: 'docs' },
    { id: 4, title: 'Critical security patch', status: 'pending', priority: 'critical', category: 'bug' },
  ]

  let tasks

  beforeEach(() => {
    tasks = ref(makeTasks())
  })

  it('returns all tasks when no filters are applied', () => {
    const { filteredTasks } = useTaskFilters(tasks)
    expect(filteredTasks.value).toHaveLength(4)
  })

  it('filters by status', () => {
    const { filteredTasks, statusFilter } = useTaskFilters(tasks)
    statusFilter.value = 'pending'
    expect(filteredTasks.value).toHaveLength(2)
    expect(filteredTasks.value.every((t) => t.status === 'pending')).toBe(true)
  })

  it('filters by priority', () => {
    const { filteredTasks, priorityFilter } = useTaskFilters(tasks)
    priorityFilter.value = 'high'
    expect(filteredTasks.value).toHaveLength(1)
    expect(filteredTasks.value[0].id).toBe(1)
  })

  it('filters by category', () => {
    const { filteredTasks, categoryFilter } = useTaskFilters(tasks)
    categoryFilter.value = 'bug'
    expect(filteredTasks.value).toHaveLength(2)
    expect(filteredTasks.value.every((t) => t.category === 'bug')).toBe(true)
  })

  it('filters by search term (case-insensitive)', () => {
    const { filteredTasks, search } = useTaskFilters(tasks)
    search.value = 'login'
    expect(filteredTasks.value).toHaveLength(1)
    expect(filteredTasks.value[0].id).toBe(1)
  })

  it('combines multiple filters', () => {
    const { filteredTasks, statusFilter, categoryFilter } = useTaskFilters(tasks)
    statusFilter.value = 'pending'
    categoryFilter.value = 'bug'
    expect(filteredTasks.value).toHaveLength(2)
  })

  it('returns empty array when no tasks match', () => {
    const { filteredTasks, search } = useTaskFilters(tasks)
    search.value = 'nonexistent task xyz'
    expect(filteredTasks.value).toHaveLength(0)
  })

  it('clearFilters resets all filter state', () => {
    const { search, statusFilter, priorityFilter, categoryFilter, clearFilters } = useTaskFilters(tasks)
    search.value = 'something'
    statusFilter.value = 'pending'
    priorityFilter.value = 'high'
    categoryFilter.value = 'bug'

    clearFilters()

    expect(search.value).toBe('')
    expect(statusFilter.value).toBeNull()
    expect(priorityFilter.value).toBeNull()
    expect(categoryFilter.value).toBeNull()
  })

  it('search filters by title', () => {
    const { filteredTasks, search } = useTaskFilters(tasks)
    search.value = 'DOCS'
    expect(filteredTasks.value).toHaveLength(1)
    expect(filteredTasks.value[0].id).toBe(3)
  })

  it('reacts to task list changes', () => {
    const { filteredTasks, statusFilter } = useTaskFilters(tasks)
    statusFilter.value = 'pending'
    expect(filteredTasks.value).toHaveLength(2)

    tasks.value = [
      { id: 5, title: 'New task', status: 'pending', priority: 'low', category: 'general' },
    ]
    expect(filteredTasks.value).toHaveLength(1)
  })
})
