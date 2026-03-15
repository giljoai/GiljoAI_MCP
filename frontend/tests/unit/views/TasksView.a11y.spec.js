import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { vi, describe, it, expect } from 'vitest'
import TasksView from '@/views/TasksView.vue'
import axe from 'axe-core'

describe.skip('TasksView - Accessibility - axe-core not installed', () => {
  it('passes accessibility checks', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia()]
      }
    })

    // Convert mounted wrapper to DOM element
    const results = await axe.run(wrapper.element)

    expect(results.violations).toHaveLength(0)
  })

  it('keyboard navigation for filter chips works', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia()]
      }
    })

    const myTasksChip = wrapper.find('[data-test="my-tasks-chip"]')

    // Simulate focus and keyboard activation
    myTasksChip.element.focus()
    expect(document.activeElement).toBe(myTasksChip.element)

    await myTasksChip.trigger('keydown.enter')
    expect(wrapper.vm.taskFilter).toBe('my_tasks')
  })

  it('assignment dropdown has proper ARIA attributes', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia()]
      }
    })

    await wrapper.setData({ showCreateDialog: true })

    const assignSelect = wrapper.find('[data-test="assign-to-select"]')
    expect(assignSelect.attributes('aria-label')).toBe('Assign task to team member')
    expect(assignSelect.attributes('role')).toBe('combobox')
  })

  it('task table has semantic HTML and ARIA roles', () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia()]
      }
    })

    const table = wrapper.find('[role="table"]')
    expect(table.exists()).toBe(true)

    const headers = wrapper.findAll('[role="columnheader"]')
    expect(headers.length).toBeGreaterThan(0)

    const rows = wrapper.findAll('[role="row"]')
    rows.forEach(row => {
      expect(row.attributes('role')).toBe('row')
    })
  })

  it('error messages have aria-live for screen readers', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [createTestingPinia()]
      }
    })

    // Simulate an error state
    await wrapper.setData({
      error: 'Failed to load tasks',
      errorDetails: 'Network connection issue'
    })

    const errorAlert = wrapper.find('[data-test="error-alert"]')
    expect(errorAlert.attributes('aria-live')).toBe('assertive')
  })
})
