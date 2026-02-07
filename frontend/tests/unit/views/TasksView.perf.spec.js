import { mount, flushPromises } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { vi, describe, it, expect } from 'vitest'
import TasksView from '@/views/TasksView.vue'
import * as api from '@/services/api'

vi.mock('@/services/api', () => ({
  tasks: {
    list: vi.fn(),
  }
}))

describe('TasksView - Performance Tests', () => {
  // Generate a large number of mock tasks
  const generateMockTasks = (count) => {
    return Array.from({ length: count }, (_, i) => ({
      id: i + 1,
      title: `Performance Task ${i + 1}`,
      description: `Description for task ${i + 1}`,
      assigned_to_user_id: i % 10 + 1,
      created_by_user_id: i % 5 + 1,
      status: ['todo', 'in_progress', 'done'][i % 3],
      priority: ['low', 'medium', 'high'][i % 3]
    }))
  }

  it('renders 1000 tasks without significant performance degradation', async () => {
    // Generate large dataset
    const largeTasks = generateMockTasks(1000)

    // Mock tasks list API
    vi.spyOn(api.tasks, 'list').mockResolvedValue({ data: largeTasks })

    // Measure render time
    const start = performance.now()

    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: { id: 1, role: 'admin' } }
          }
        })]
      }
    })

    // Wait for async operations
    await flushPromises()

    const end = performance.now()
    const renderTime = end - start

    // Check render time (should be under 500ms)
    expect(renderTime).toBeLessThan(500)

    // Verify task count
    expect(wrapper.findAll('[data-test="task-row"]').length).toBe(1000)
  })

  it('filters large task list efficiently', async () => {
    const largeTasks = generateMockTasks(1000)

    // Mock tasks list API
    vi.spyOn(api.tasks, 'list').mockResolvedValue({ data: largeTasks })

    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: { id: 1, role: 'admin' } }
          }
        })]
      }
    })

    // Wait for initial render
    await flushPromises()

    // Measure filter time
    const start = performance.now()

    // Change filter
    await wrapper.setData({ taskFilter: 'all' })
    await flushPromises()

    const end = performance.now()
    const filterTime = end - start

    // Check filter time (should be under 100ms)
    expect(filterTime).toBeLessThan(100)

    // Verify filtered task list
    const filteredTasks = wrapper.findAll('[data-test="task-row"]')
    expect(filteredTasks.length).toBe(1000)
  })

  it('handles rapid filter changes', async () => {
    const largeTasks = generateMockTasks(1000)

    // Mock tasks list API
    vi.spyOn(api.tasks, 'list').mockResolvedValue({ data: largeTasks })

    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: { id: 1, role: 'admin' } }
          }
        })]
      }
    })

    // Wait for initial render
    await flushPromises()

    // Rapid filter changes
    const filterSequence = ['my_tasks', 'all', 'created', 'my_tasks']
    const filterPromises = filterSequence.map(async (filter) => {
      const start = performance.now()
      await wrapper.setData({ taskFilter: filter })
      await flushPromises()
      const end = performance.now()
      return end - start
    })

    const filterTimes = await Promise.all(filterPromises)

    // Each filter change should be quick
    filterTimes.forEach(time => {
      expect(time).toBeLessThan(150)
    })
  })

  it('memory usage remains stable with large task list', async () => {
    const largeTasks = generateMockTasks(1000)

    // Check initial memory usage
    const initialMemory = process.memoryUsage().heapUsed

    // Create component
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            user: { currentUser: { id: 1, role: 'admin' } }
          }
        })]
      }
    })

    // Wait for render
    await flushPromises()

    // Perform multiple filter operations
    for (let i = 0; i < 10; i++) {
      await wrapper.setData({ taskFilter: i % 2 === 0 ? 'my_tasks' : 'all' })
      await flushPromises()
    }

    // Check memory after operations
    const finalMemory = process.memoryUsage().heapUsed

    // Memory increase should be reasonable (under 50MB)
    const memoryIncrease = finalMemory - initialMemory
    expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024)
  })
})
