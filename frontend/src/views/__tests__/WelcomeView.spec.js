import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { PROJECT_TEMPLATES } from '@/composables/projectTemplates'

// ---------- Module mocks ----------

const pushMock = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
}))

const showToastMock = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

vi.mock('@/services/configService', () => ({
  default: {
    fetchConfig: vi.fn().mockResolvedValue({}),
    getRawConfig: vi.fn().mockReturnValue(null),
  },
}))

vi.mock('@/services/api', () => ({
  default: {
    templates: {
      list: vi.fn().mockResolvedValue({ data: [] }),
      activeCount: vi.fn().mockResolvedValue({ data: { max_slots: 8 } }),
    },
    stats: {
      getDashboard: vi.fn().mockResolvedValue({ data: { recent_projects: [] } }),
      getSystem: vi.fn().mockResolvedValue({ data: { version: 'test' } }),
    },
  },
}))

// Stub heavy child components so we don't need their full graphs.
vi.mock('@/components/GilMascot.vue', () => ({
  default: { name: 'GilMascot', template: '<div />' },
}))
vi.mock('@/components/setup/SetupWizardOverlay.vue', () => ({
  default: { name: 'SetupWizardOverlay', template: '<div />' },
}))
vi.mock('@/components/setup/CertTrustModal.vue', () => ({
  default: { name: 'CertTrustModal', template: '<div />' },
}))
vi.mock('@/components/dashboard/RecentProjectsList.vue', () => ({
  default: { name: 'RecentProjectsList', template: '<div />' },
}))
vi.mock('@/components/projects/ProjectReviewModal.vue', () => ({
  default: { name: 'ProjectReviewModal', template: '<div />' },
}))

// Pinia stores -----------------------------------------------------------

const createProjectMock = vi.fn().mockResolvedValue({ id: 'proj-new' })

vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: {
      full_name: 'Test User',
      setup_complete: true,
      learning_complete: true,
      setup_step_completed: 4,
      setup_selected_tools: [],
    },
    updateSetupState: vi.fn().mockResolvedValue(),
  }),
}))

vi.mock('@/stores/products', () => ({
  useProductStore: () => ({
    activeProduct: { id: 'prod-1', name: 'Test Product' },
    hasProducts: true,
    effectiveProductId: 'prod-1',
    fetchProducts: vi.fn().mockResolvedValue(),
  }),
}))

vi.mock('@/stores/projects', () => ({
  useProjectStore: () => ({
    projects: [],
    activeProjects: [],
    fetchProjects: vi.fn().mockResolvedValue(),
    createProject: createProjectMock,
  }),
}))

// Vuetify icons rendered as v-icon — stub globally to avoid plugin setup
const globalStubs = {
  'v-icon': { template: '<i><slot /></i>' },
  'v-tooltip': { template: '<div><slot name="activator" :props="{}" /><slot /></div>' },
  'router-link': { template: '<a><slot /></a>' },
}

async function mountWelcome() {
  const WelcomeView = (await import('@/views/WelcomeView.vue')).default
  return mount(WelcomeView, {
    global: { stubs: globalStubs },
  })
}

// -----------------------------------------------------------------------

describe('WelcomeView — step-4 template-card bootstrap', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    pushMock.mockClear()
    createProjectMock.mockClear()
    createProjectMock.mockResolvedValue({ id: 'proj-new' })
    showToastMock.mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders three quick-launch cards in order: [newProjectCard, template[0], template[1]]', async () => {
    const wrapper = await mountWelcome()
    await flushPromises()

    const cards = wrapper.findAll('.quick-card')
    expect(cards).toHaveLength(3)

    // First card: blank-slate "New Project" — no data-template-id attr
    expect(cards[0].attributes('data-template-id')).toBeFalsy()
    expect(cards[0].text()).toContain('New Project')

    // Second + third: template cards in PROJECT_TEMPLATES order
    expect(cards[1].attributes('data-template-id')).toBe(PROJECT_TEMPLATES[0].id)
    expect(cards[1].text()).toContain(PROJECT_TEMPLATES[0].cardTitle)

    expect(cards[2].attributes('data-template-id')).toBe(PROJECT_TEMPLATES[1].id)
    expect(cards[2].text()).toContain(PROJECT_TEMPLATES[1].cardTitle)
  })

  it('clicking each template card calls projectStore.createProject with the verbatim template payload', async () => {
    const wrapper = await mountWelcome()
    await flushPromises()

    for (let i = 0; i < PROJECT_TEMPLATES.length; i += 1) {
      const tmpl = PROJECT_TEMPLATES[i]
      const card = wrapper.find(`[data-template-id="${tmpl.id}"]`)
      expect(card.exists()).toBe(true)

      await card.trigger('click')
      await flushPromises()

      expect(createProjectMock).toHaveBeenCalledWith({
        name: tmpl.projectName,
        description: tmpl.projectDescription,
        product_id: 'prod-1',
      })
    }
    expect(createProjectMock).toHaveBeenCalledTimes(PROJECT_TEMPLATES.length)
    // Each successful template create routes to /Projects (matching newProjectCard).
    expect(pushMock).toHaveBeenCalledWith('/Projects')
  })

  it('clicking "New Project" card still triggers the existing manual flow (router push to /Projects)', async () => {
    const wrapper = await mountWelcome()
    await flushPromises()

    const newProjectCard = wrapper.findAll('.quick-card')[0]
    await newProjectCard.trigger('click')
    await flushPromises()

    expect(createProjectMock).not.toHaveBeenCalled()
    expect(pushMock).toHaveBeenCalledWith('/Projects')
  })

  it('surfaces a toast when createProject fails and clears the busy state', async () => {
    createProjectMock.mockRejectedValueOnce(new Error('boom'))
    const wrapper = await mountWelcome()
    await flushPromises()

    const card = wrapper.find(`[data-template-id="${PROJECT_TEMPLATES[0].id}"]`)
    await card.trigger('click')
    await flushPromises()

    expect(showToastMock).toHaveBeenCalledTimes(1)
    expect(showToastMock.mock.calls[0][0].color).toBe('error')

    // Busy class should be cleared after the rejection resolves.
    expect(card.classes()).not.toContain('quick-card--busy')
  })
})
