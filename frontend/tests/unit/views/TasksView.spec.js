import { mount, flushPromises } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import TasksView from '@/views/TasksView.vue'

// Mock API inline (must be declared inline for vi.mock hoisting)
vi.mock('@/services/api', () => ({
  default: {
    tasks: {
      list: vi.fn().mockResolvedValue({ data: [] }),
      create: vi.fn().mockResolvedValue({ data: {} }),
      update: vi.fn().mockResolvedValue({ data: {} }),
      delete: vi.fn().mockResolvedValue({}),
    },
    users: {
      list: vi.fn().mockResolvedValue({ data: [] }),
    },
    agents: {
      list: vi.fn().mockResolvedValue({ data: [] }),
    },
  },
}))

// Import the mocked API
import api from '@/services/api'

describe('TasksView - Task Filtering', () => {
  it('defaults to "My Tasks" filter on mount', () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia()]
      }
    })

    expect(wrapper.vm.taskFilter).toBe('my_tasks')
    expect(wrapper.find('[data-test="my-tasks-chip"]').classes()).toContain('v-chip--active')
  })

  it('fetches tasks with my_tasks filter on mount', async () => {
    api.tasks.list.mockResolvedValue({ data: [] })

    mount(TasksView, {
      global: {
        plugins: [createTestingPinia()]
      }
    })

    await flushPromises()

    expect(api.tasks.list).toHaveBeenCalledWith({ filter_type: 'my_tasks' })
  })

  it('shows "All Tasks" chip only for admin', () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: { role: 'admin' } }
          }
        })]
      }
    })

    expect(wrapper.find('[data-test="all-tasks-chip"]').exists()).toBe(true)
  })

  it('hides "All Tasks" chip for non-admin', () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: { role: 'developer' } }
          }
        })]
      }
    })

    expect(wrapper.find('[data-test="all-tasks-chip"]').exists()).toBe(false)
  })
})

describe('TasksView - User Assignment Display', () => {
  const mockTasks = [
    { id: 1, title: 'Task 1', assigned_to_user_id: 10, created_by_user_id: 5 },
    { id: 2, title: 'Task 2', assigned_to_user_id: null, created_by_user_id: 10 }
  ]

  const mockUsers = [
    { id: 10, username: 'currentUser' },
    { id: 5, username: 'creatorUser' }
  ]

  beforeEach(() => {
    api.tasks.list.mockResolvedValue({ data: mockTasks })
    api.users.list.mockResolvedValue({ data: mockUsers })
  })

  it('displays assigned user correctly', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: { id: 10 } }
          }
        })]
      }
    })

    await flushPromises()

    const assignedUserCell = wrapper.find('[data-test="task-assignee-10"]')
    expect(assignedUserCell.text()).toBe('currentUser')
  })

  it('shows "Unassigned" for tasks without assigned user', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia()]
      }
    })

    await flushPromises()

    const unassignedCell = wrapper.find('[data-test="task-assignee-null"]')
    expect(unassignedCell.text()).toBe('Unassigned')
  })

  it('highlights tasks assigned to current user', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: { id: 10 } }
          }
        })]
      }
    })

    await flushPromises()

    const assignedTaskRow = wrapper.find('[data-test="task-row-1"]')
    expect(assignedTaskRow.classes()).toContain('assigned-to-me')
  })
})

describe('TasksView - Task Creation with Assignment', () => {
  beforeEach(() => {
    api.users.list.mockResolvedValue({
      data: [
        { id: 1, username: 'user1' },
        { id: 2, username: 'user2' }
      ]
    })
  })

  it('populates assignment dropdown with tenant users', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia()]
      }
    })

    await wrapper.setData({ showCreateDialog: true })
    await flushPromises()

    const assignSelect = wrapper.find('[data-test="assign-to-user-select"]')
    expect(assignSelect.props('items')).toHaveLength(2)
    expect(assignSelect.props('items')[0].username).toBe('user1')
  })

  it('can create task without assignment', async () => {
    api.tasks.create.mockResolvedValue({ data: { id: 100 } })
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia()]
      }
    })

    await wrapper.setData({
      showCreateDialog: true,
      currentTask: {
        title: 'Unassigned Task',
        description: 'Test task',
        assigned_to_user_id: null
      }
    })

    await wrapper.vm.saveTask()
    await flushPromises()

    expect(api.tasks.create).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Unassigned Task',
        assigned_to_user_id: null
      })
    )
  })

  it('can create task with user assignment', async () => {
    api.tasks.create.mockResolvedValue({ data: { id: 100 } })
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia()]
      }
    })

    await wrapper.setData({
      showCreateDialog: true,
      currentTask: {
        title: 'Assigned Task',
        description: 'Test task',
        assigned_to_user_id: 1
      }
    })

    await wrapper.vm.saveTask()
    await flushPromises()

    expect(api.tasks.create).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Assigned Task',
        assigned_to_user_id: 1
      })
    )
  })
})

describe('TasksView - Visual Indicators', () => {
  const mockTasks = [
    { id: 1, title: 'Task 1', assigned_to_user_id: 10, created_by_user_id: 5 },
    { id: 2, title: 'Task 2', assigned_to_user_id: 10, created_by_user_id: 10 },
    { id: 3, title: 'Task 3', assigned_to_user_id: 5, created_by_user_id: 10 }
  ]

  beforeEach(() => {
    api.tasks.list.mockResolvedValue({ data: mockTasks })
  })

  it('shows owner icon for tasks created by user', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: { id: 10 } },
            tasks: { tasks: mockTasks }
          }
        })]
      }
    })

    await flushPromises()

    const ownerIcons = wrapper.findAll('[data-test="owner-icon"]')
    expect(ownerIcons.length).toBeGreaterThanOrEqual(1)  // Task 2 and 3 created by current user
  })

  it('shows assignment icon for tasks assigned to user', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: { id: 10 } },
            tasks: { tasks: mockTasks }
          }
        })]
      }
    })

    await flushPromises()

    const assignmentIcons = wrapper.findAll('[data-test="assigned-icon"]')
    expect(assignmentIcons.length).toBeGreaterThanOrEqual(1)  // Task 1 and 2 assigned to current user
  })
})

describe('TasksView - Permission Checks', () => {
  it('admin can see "All Tasks" filter', () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: { role: 'admin' } }
          }
        })]
      }
    })

    expect(wrapper.find('[data-test="all-tasks-chip"]').exists()).toBe(true)
  })

  it('developer sees only "My Tasks" filter', () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: { role: 'developer' } }
          }
        })]
      }
    })

    expect(wrapper.find('[data-test="all-tasks-chip"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="my-tasks-chip"]').exists()).toBe(true)
  })

  it('viewer sees only "My Tasks" filter', () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: { role: 'viewer' } }
          }
        })]
      }
    })

    expect(wrapper.find('[data-test="all-tasks-chip"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="my-tasks-chip"]').exists()).toBe(true)
  })
})
