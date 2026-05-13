import { describe, it, expect, beforeEach } from 'vitest'
import { ref } from 'vue'
import { useTaskFilters } from './useTaskFilters'

describe('useTaskFilters', () => {
  const makeTasks = () => [
    {
      id: 1,
      title: 'Fix login bug',
      status: 'pending',
      priority: 'high',
      task_type: 'BE',
      task_type_id: 'type-be',
    },
    {
      id: 2,
      title: 'Add dashboard feature',
      status: 'in_progress',
      priority: 'medium',
      task_type: 'FE',
      task_type_id: 'type-fe',
    },
    {
      id: 3,
      title: 'Write docs',
      status: 'completed',
      priority: 'low',
      task_type: null,
      task_type_id: null,
    },
    {
      id: 4,
      title: 'Critical security patch',
      status: 'pending',
      priority: 'critical',
      task_type: 'BE',
      task_type_id: 'type-be',
    },
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

  it('filters by task_type_id', () => {
    const { filteredTasks, taskTypeFilter } = useTaskFilters(tasks)
    taskTypeFilter.value = 'type-be'
    expect(filteredTasks.value).toHaveLength(2)
    expect(filteredTasks.value.every((t) => t.task_type_id === 'type-be')).toBe(true)
  })

  it('filters by "none" task_type to surface untagged tasks', () => {
    const { filteredTasks, taskTypeFilter } = useTaskFilters(tasks)
    taskTypeFilter.value = 'none'
    expect(filteredTasks.value).toHaveLength(1)
    expect(filteredTasks.value[0].id).toBe(3)
  })

  it('filters by search term (case-insensitive)', () => {
    const { filteredTasks, search } = useTaskFilters(tasks)
    search.value = 'login'
    expect(filteredTasks.value).toHaveLength(1)
    expect(filteredTasks.value[0].id).toBe(1)
  })

  it('combines multiple filters', () => {
    const { filteredTasks, statusFilter, taskTypeFilter } = useTaskFilters(tasks)
    statusFilter.value = 'pending'
    taskTypeFilter.value = 'type-be'
    expect(filteredTasks.value).toHaveLength(2)
  })

  it('returns empty array when no tasks match', () => {
    const { filteredTasks, search } = useTaskFilters(tasks)
    search.value = 'nonexistent task xyz'
    expect(filteredTasks.value).toHaveLength(0)
  })

  it('clearFilters resets all filter state', () => {
    const { search, statusFilter, priorityFilter, taskTypeFilter, clearFilters } =
      useTaskFilters(tasks)
    search.value = 'something'
    statusFilter.value = 'pending'
    priorityFilter.value = 'high'
    taskTypeFilter.value = 'type-be'

    clearFilters()

    expect(search.value).toBe('')
    expect(statusFilter.value).toBeNull()
    expect(priorityFilter.value).toBeNull()
    expect(taskTypeFilter.value).toBeNull()
  })

  it('search filters by title', () => {
    const { filteredTasks, search } = useTaskFilters(tasks)
    search.value = 'DOCS'
    expect(filteredTasks.value).toHaveLength(1)
    expect(filteredTasks.value[0].id).toBe(3)
  })

  it('search matches by description (case-insensitive)', () => {
    const taggedTasks = ref([
      {
        id: 10,
        title: 'Reseed agents on activation',
        description: 'Activating a product should not re-run the agent seed.',
        status: 'pending',
        priority: 'medium',
        task_type_id: 'type-be',
        taxonomy_alias: 'BE5042',
        series_number: 5042,
      },
      {
        id: 11,
        title: 'Unrelated work',
        description: 'Nothing here.',
        status: 'pending',
        priority: 'low',
        task_type_id: null,
        taxonomy_alias: '',
        series_number: null,
      },
    ])
    const { filteredTasks, search } = useTaskFilters(taggedTasks)
    search.value = 'agent seed'
    expect(filteredTasks.value.map((t) => t.id)).toEqual([10])
  })

  it('search matches by taxonomy_alias (full serial badge)', () => {
    const taggedTasks = ref([
      {
        id: 20,
        title: 'A task',
        description: null,
        status: 'pending',
        priority: 'medium',
        task_type_id: 'type-fe',
        taxonomy_alias: 'FE5047',
        series_number: 5047,
      },
      {
        id: 21,
        title: 'Another task',
        description: null,
        status: 'pending',
        priority: 'medium',
        task_type_id: 'type-be',
        taxonomy_alias: 'BE5042',
        series_number: 5042,
      },
    ])
    const { filteredTasks, search } = useTaskFilters(taggedTasks)
    search.value = 'FE5047'
    expect(filteredTasks.value.map((t) => t.id)).toEqual([20])
  })

  it('search matches by partial serial number digits', () => {
    const taggedTasks = ref([
      {
        id: 30,
        title: 'A task',
        description: null,
        status: 'pending',
        priority: 'medium',
        task_type_id: 'type-be',
        taxonomy_alias: 'BE5042',
        series_number: 5042,
      },
      {
        id: 31,
        title: 'Another task',
        description: null,
        status: 'pending',
        priority: 'medium',
        task_type_id: 'type-fe',
        taxonomy_alias: 'FE5047',
        series_number: 5047,
      },
    ])
    const { filteredTasks, search } = useTaskFilters(taggedTasks)
    search.value = '5042'
    expect(filteredTasks.value.map((t) => t.id)).toEqual([30])
  })

  it('search does not throw on tasks with null description / empty alias', () => {
    const taggedTasks = ref([
      {
        id: 40,
        title: 'Untyped scratch note',
        description: null,
        status: 'pending',
        priority: 'low',
        task_type_id: null,
        taxonomy_alias: '',
        series_number: null,
      },
    ])
    const { filteredTasks, search } = useTaskFilters(taggedTasks)
    search.value = 'scratch'
    expect(filteredTasks.value.map((t) => t.id)).toEqual([40])
  })

  it('reacts to task list changes', () => {
    const { filteredTasks, statusFilter } = useTaskFilters(tasks)
    statusFilter.value = 'pending'
    expect(filteredTasks.value).toHaveLength(2)

    tasks.value = [
      { id: 5, title: 'New task', status: 'pending', priority: 'low', task_type_id: null },
    ]
    expect(filteredTasks.value).toHaveLength(1)
  })

  describe('statusSelectOptions', () => {
    it('exposes the six canonical task statuses (mirrors BE TaskUpdate enum)', () => {
      const { statusSelectOptions } = useTaskFilters(tasks)
      const values = statusSelectOptions.value.map((o) => o.value)
      expect(values).toEqual([
        'pending',
        'in_progress',
        'completed',
        'blocked',
        'cancelled',
        'converted',
      ])
    })
  })

  describe('typeSelectOptions', () => {
    it('builds dropdown items from injected taxonomyTypes plus the "No Type" pseudo-option', () => {
      const taxonomyTypes = ref([
        { id: 'type-be', abbreviation: 'BE', label: 'Backend' },
        { id: 'type-fe', abbreviation: 'FE', label: 'Frontend' },
      ])
      const { typeSelectOptions } = useTaskFilters(tasks, { taxonomyTypes })
      expect(typeSelectOptions.value).toHaveLength(3)
      expect(typeSelectOptions.value.some((o) => o.title === 'BE')).toBe(true)
      expect(typeSelectOptions.value.some((o) => o.value === 'none')).toBe(true)
    })

    it('returns only the "No Type" pseudo-option when no taxonomyTypes are provided', () => {
      const { typeSelectOptions } = useTaskFilters(tasks)
      expect(typeSelectOptions.value).toEqual([{ title: 'No Type', value: 'none' }])
    })
  })
})
