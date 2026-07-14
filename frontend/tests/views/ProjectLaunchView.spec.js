/**
 * Regression: project EDIT (ProjectLaunchView) "Update" silently disabled /
 * silent no-op on an invalid form (perf-findings 2026-06-11, flagged from code
 * during the audit — same class as project-create: required Description next to
 * an optional-looking Mission, button was :disabled="!formValid" and
 * saveProject() bailed on formValid). Fix: button always clickable + validate
 * ON CLICK so "Description is required" surfaces instead of a dead Update button.
 *
 * saveProject() is called directly with projectForm overridden to a controllable
 * validate() — the edit form isn't rendered here, so the template ref stays as we
 * set it.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { projectId: 'p1' } }),
}))

const { mockUpdate } = vi.hoisted(() => ({ mockUpdate: vi.fn() }))

vi.mock('@/services/api', () => ({
  api: {
    projects: {
      get: vi.fn().mockResolvedValue({ data: { id: 'p1', name: 'P', description: 'D', mission: 'M' } }),
      getOrchestrator: vi.fn().mockResolvedValue({ data: {} }),
      update: mockUpdate,
    },
    agentJobs: { list: vi.fn().mockResolvedValue({ data: [] }) },
  },
}))

vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))

import ProjectLaunchView from '@/views/ProjectLaunchView.vue'

function mountView() {
  const vuetify = createVuetify()
  return mount(ProjectLaunchView, {
    global: {
      plugins: [vuetify],
      stubs: { ProjectTabs: true },
    },
  })
}

describe('ProjectLaunchView.vue — Update validate-on-click (silent-no-op regression)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockUpdate.mockResolvedValue({ data: {} })
  })

  it('saveProject() validates and does NOT PUT when the form is invalid', async () => {
    const wrapper = mountView()
    await flushPromises()

    const validate = vi.fn().mockResolvedValue({ valid: false })
    wrapper.vm.projectForm = { validate }

    await wrapper.vm.saveProject()
    await flushPromises()

    expect(validate).toHaveBeenCalledTimes(1) // validate-on-click (old code bailed on formValid, never validated)
    expect(mockUpdate).not.toHaveBeenCalled()
  })

  it('saveProject() PUTs when the form is valid', async () => {
    const wrapper = mountView()
    await flushPromises()

    wrapper.vm.projectData = { name: 'Edited', description: 'New desc', mission: 'M' }
    wrapper.vm.projectForm = { validate: vi.fn().mockResolvedValue({ valid: true }) }

    await wrapper.vm.saveProject()
    await flushPromises()

    expect(mockUpdate).toHaveBeenCalledTimes(1)
    expect(mockUpdate.mock.calls[0][1]).toMatchObject({ name: 'Edited', description: 'New desc' })
  })
})
