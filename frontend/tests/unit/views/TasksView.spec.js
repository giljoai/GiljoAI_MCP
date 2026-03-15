/**
 * TasksView.spec.js
 *
 * Tests for TasksView component - task management interface.
 *
 * Post-refactor notes:
 * - TasksView uses search, statusFilter, priorityFilter, categoryFilter for filtering
 * - No taskFilter ref or data-test chip selectors (my-tasks-chip, all-tasks-chip)
 * - Uses taskStore, productStore, userStore
 * - Task creation via showTaskDialog ref
 * - Inline v-select dropdowns for status/priority editing
 * - Tasks filtered by productStore.effectiveProductId
 * - Component uses <script setup> - no setData(), access refs via wrapper.vm
 */

import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import TasksView from '@/views/TasksView.vue'

// Mock API
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

import api from '@/services/api'

describe('TasksView - Component Rendering', () => {
  let vuetify

  beforeEach(() => {
    setActivePinia(createPinia())
    vuetify = createVuetify({ components, directives })
    vi.clearAllMocks()
  })

  it('renders the component without errors', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [vuetify],
      },
    })

    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('displays page title "Tasks"', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [vuetify],
      },
    })

    await flushPromises()
    expect(wrapper.text()).toContain('Tasks')
  })

  it('renders a v-data-table for tasks', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [vuetify],
      },
    })

    await flushPromises()
    // Global test setup stubs v-data-table as <div class="v-data-table">
    const dataTable = wrapper.find('.v-data-table')
    expect(dataTable.exists()).toBe(true)
  })

  it('has search field for tasks', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [vuetify],
      },
    })

    await flushPromises()
    expect(wrapper.vm.search).toBe('')
  })

  it('has status and priority filter refs', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [vuetify],
      },
    })

    await flushPromises()
    expect(wrapper.vm.statusFilter).toBeNull()
    expect(wrapper.vm.priorityFilter).toBeNull()
  })
})

describe('TasksView - Task Statistics', () => {
  let vuetify

  beforeEach(() => {
    setActivePinia(createPinia())
    vuetify = createVuetify({ components, directives })
    vi.clearAllMocks()
  })

  it('displays statistics cards', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [vuetify],
      },
    })

    await flushPromises()
    expect(wrapper.text()).toContain('Total Tasks')
    expect(wrapper.text()).toContain('Pending')
    expect(wrapper.text()).toContain('In Progress')
    expect(wrapper.text()).toContain('Completed')
  })
})

describe('TasksView - Task Dialog', () => {
  let vuetify

  beforeEach(() => {
    setActivePinia(createPinia())
    vuetify = createVuetify({ components, directives })
    vi.clearAllMocks()
  })

  it('has showTaskDialog ref initialized to false', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [vuetify],
      },
    })

    await flushPromises()
    expect(wrapper.vm.showTaskDialog).toBe(false)
  })

  it('has saveTask method', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [vuetify],
      },
    })

    await flushPromises()
    expect(typeof wrapper.vm.saveTask).toBe('function')
  })

  it('has currentTask ref with default values', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [vuetify],
      },
    })

    await flushPromises()
    expect(wrapper.vm.currentTask).toBeDefined()
    expect(wrapper.vm.currentTask.status).toBe('pending')
    expect(wrapper.vm.currentTask.priority).toBe('medium')
  })
})

describe('TasksView - Table Headers', () => {
  let vuetify

  beforeEach(() => {
    setActivePinia(createPinia())
    vuetify = createVuetify({ components, directives })
    vi.clearAllMocks()
  })

  it('has correct table headers', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [vuetify],
      },
    })

    await flushPromises()
    // Access headers directly from the component instance since
    // the global test setup stubs VDataTable as a simple div
    const headers = wrapper.vm.headers

    const headerKeys = headers.map((h) => h.key)
    expect(headerKeys).toContain('status')
    expect(headerKeys).toContain('priority')
    expect(headerKeys).toContain('title')
    expect(headerKeys).toContain('actions')
  })
})

describe('TasksView - Filter Controls', () => {
  let vuetify

  beforeEach(() => {
    setActivePinia(createPinia())
    vuetify = createVuetify({ components, directives })
    vi.clearAllMocks()
  })

  it('has clearFilters method', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [vuetify],
      },
    })

    await flushPromises()
    expect(typeof wrapper.vm.clearFilters).toBe('function')
  })

  it('has New Task button', async () => {
    const wrapper = mount(TasksView, {
      global: {
        plugins: [vuetify],
      },
    })

    await flushPromises()
    expect(wrapper.text()).toContain('New Task')
  })
})
