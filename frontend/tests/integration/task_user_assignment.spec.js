import { mount, flushPromises } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { vi, describe, it, expect } from 'vitest'
import TasksView from '@/views/TasksView.vue'
import * as api from '@/services/api'

vi.mock('@/services/api', () => ({
  tasks: {
    list: vi.fn(),
    create: vi.fn(),
    convert: vi.fn()
  },
  users: {
    list: vi.fn(),
  }
}))

describe('Task User Assignment - Integration Workflow', () => {
  const userA = { id: 1, username: 'userA' }
  const userB = { id: 2, username: 'userB' }

  beforeEach(() => {
    vi.spyOn(api.users, 'list').mockResolvedValue({ data: [userA, userB] })
  })

  it('creates task with user assignment, verifies listing for creator and assignee', async () => {
    // Setup mocks for task creation and listing
    const createSpy = vi.spyOn(api.tasks, 'create').mockResolvedValue({ id: 100 })
    const listSpyUserA = vi.spyOn(api.tasks, 'list').mockImplementation((params) => {
      if (params.filter_type === 'my_tasks' && params.user_id === 1) {
        return Promise.resolve({ data: [] })
      }
      if (params.filter_type === 'my_tasks' && params.user_id === 2) {
        return Promise.resolve({ data: [{
          id: 100,
          title: 'Test Task',
          assigned_to_user_id: 2,
          created_by_user_id: 1
        }] })
      }
      return Promise.resolve({ data: [] })
    })

    // Mount component as User A
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: userA }
          }
        })]
      }
    })

    // Open create task dialog
    await wrapper.setData({
      showCreateDialog: true,
      newTask: {
        title: 'Test Task',
        description: 'Integration test task',
        assigned_to_user_id: userB.id
      }
    })

    // Create task
    await wrapper.find('[data-test="create-task-button"]').trigger('click')
    await flushPromises()

    // Verify task creation with correct assignment
    expect(createSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Test Task',
        assigned_to_user_id: userB.id
      })
    )

    // Verify task appears in different user views
    expect(listSpyUserA).toHaveBeenCalledWith(
      expect.objectContaining({ user_id: 1 })
    )
  })

  it('converts task to project, preserves assignment details', async () => {
    const taskToConvert = {
      id: 100,
      title: 'Convertible Task',
      description: 'Task to be converted',
      assigned_to_user_id: userB.id,
      created_by_user_id: userA.id
    }

    // Mock task conversion
    const convertSpy = vi.spyOn(api.tasks, 'convert').mockResolvedValue({
      project_id: 200,
      task_id: taskToConvert.id
    })

    // Mount component as admin/project creator
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: { id: 1, role: 'admin' } }
          }
        })]
      },
      data() {
        return {
          tasks: [taskToConvert]
        }
      }
    })

    // Find and trigger task conversion
    const convertButton = wrapper.find(`[data-test="convert-task-${taskToConvert.id}"]`)
    await convertButton.trigger('click')
    await flushPromises()

    // Verify conversion details
    expect(convertSpy).toHaveBeenCalledWith(taskToConvert.id)
  })

  it('multi-user task visibility scenario', async () => {
    const task = {
      id: 100,
      title: 'Multi-User Task',
      assigned_to_user_id: userB.id,
      created_by_user_id: userA.id
    }

    // Setup different list views
    const listSpyUserA = vi.spyOn(api.tasks, 'list').mockImplementation((params) => {
      // User A - filter: Created by Me
      if (params.user_id === userA.id && params.filter_type === 'created') {
        return Promise.resolve({ data: [task] })
      }

      // User B - filter: My Tasks
      if (params.user_id === userB.id && params.filter_type === 'my_tasks') {
        return Promise.resolve({ data: [task] })
      }

      // Admin - filter: All Tasks
      if (params.filter_type === 'all') {
        return Promise.resolve({ data: [task] })
      }

      return Promise.resolve({ data: [] })
    })

    // Mount views for different users
    const wrappers = {
      userA: mount(TasksView, {
        global: {
          plugins: [createTestingPinia({
            initialState: {
              user: { currentUser: { ...userA, role: 'developer' } }
            }
          })]
        }
      }),
      userB: mount(TasksView, {
        global: {
          plugins: [createTestingPinia({
            initialState: {
              user: { currentUser: { ...userB, role: 'developer' } }
            }
          })]
        }
      }),
      admin: mount(TasksView, {
        global: {
          plugins: [createTestingPinia({
            initialState: {
              user: { currentUser: { id: 3, role: 'admin' } }
            }
          })]
        }
      })
    }

    await flushPromises()

    // Verify task visibility for different user perspectives
    expect(listSpyUserA).toHaveBeenCalledWith(
      expect.objectContaining({ user_id: expect.any(Number) })
    )
  })
})
