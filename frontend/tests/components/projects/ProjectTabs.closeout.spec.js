/**
 * ProjectTabs Closeout UI State Tests (Handover 0819a)
 *
 * Tests the tri-state area: done banner, closeout button, continue guidance
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import ProjectTabs from '@/components/projects/ProjectTabs.vue'

// -- Mocks --

const mockRouter = { push: vi.fn(), replace: vi.fn() }
const mockRoute = { query: {}, hash: '' }

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
  useRouter: () => mockRouter,
}))

// Mock agentJobs composable - expose sortedJobs for per-test control
const mockSortedJobs = { value: [] }
const mockLoadJobs = vi.fn().mockResolvedValue([])

vi.mock('@/composables/useAgentJobs', () => ({
  useAgentJobs: () => ({
    store: {},
    sortedJobs: mockSortedJobs,
    loadJobs: mockLoadJobs,
  }),
}))

vi.mock('@/composables/useProjectMessages', () => ({
  useProjectMessages: () => ({
    store: {},
    loadMessages: vi.fn().mockResolvedValue([]),
  }),
}))

vi.mock('@/composables/useIntegrationStatus', () => ({
  useIntegrationStatus: () => ({
    gitEnabled: { value: false },
    serenaEnabled: { value: false },
  }),
}))

const mockShowToast = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: mockShowToast,
  }),
}))

vi.mock('@/composables/useClipboard', () => ({
  useClipboard: () => ({
    copy: vi.fn().mockResolvedValue(true),
  }),
}))

vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: () => ({
    subscribeToProject: vi.fn(),
    unsubscribe: vi.fn(),
    onConnectionChange: vi.fn().mockReturnValue(vi.fn()),
  }),
}))

vi.mock('@/stores/notifications', () => ({
  useNotificationStore: () => ({
    clearForProject: vi.fn(),
  }),
}))

vi.mock('@/services/api', () => ({
  default: {
    projects: {
      get: vi.fn().mockResolvedValue({ data: {} }),
      update: vi.fn().mockResolvedValue({}),
    },
    prompts: {
      staging: vi.fn().mockResolvedValue({ data: { prompt: 'test' } }),
    },
    orchestrator: {
      launchProject: vi.fn().mockResolvedValue({}),
    },
  },
}))

// -- Helpers --

function createWrapper(projectOverrides = {}, extraOptions = {}) {
  const vuetify = createVuetify()
  const project = {
    id: 'proj-1',
    project_id: 'proj-1',
    name: 'Test Project',
    description: 'Test',
    status: 'active',
    product_id: 'prod-1',
    execution_mode: 'multi_terminal',
    ...projectOverrides,
  }

  return mount(ProjectTabs, {
    props: { project, orchestrator: null, ...extraOptions.props },
    global: {
      plugins: [vuetify],
      stubs: {
        LaunchTab: { template: '<div class="launch-tab-stub" />' },
        JobsTab: { template: '<div class="jobs-tab-stub" />' },
        CloseoutModal: {
          name: 'CloseoutModal',
          template: '<div class="closeout-modal-stub" />',
          props: ['show', 'projectId', 'projectName', 'productId'],
          emits: ['close', 'closeout', 'continue'],
        },
      },
    },
  })
}

describe('ProjectTabs - Closeout UI State (Handover 0819a)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockRouter.push.mockClear()
    mockRouter.replace.mockClear()
    mockShowToast.mockClear()
    mockSortedJobs.value = []
    mockRoute.query = { tab: 'jobs' }
    mockRoute.hash = ''
  })

  // ==================== CLOSEOUT BUTTON HIDDEN TESTS ====================

  describe('Closeout button hidden for terminal project statuses', () => {
    it('hides closeout button when project.status is completed', async () => {
      // All agents terminal so closeout WOULD show without the status guard
      mockSortedJobs.value = [
        { agent_display_name: 'orchestrator', status: 'complete' },
        { agent_display_name: 'implementor', status: 'complete' },
      ]

      const wrapper = createWrapper({ status: 'completed' })
      await flushPromises()

      expect(wrapper.find('[data-testid="close-project-btn"]').exists()).toBe(false)
    })

    it('hides closeout button when project.status is terminated', async () => {
      mockSortedJobs.value = [
        { agent_display_name: 'orchestrator', status: 'complete' },
      ]

      const wrapper = createWrapper({ status: 'terminated' })
      await flushPromises()

      expect(wrapper.find('[data-testid="close-project-btn"]').exists()).toBe(false)
    })

    it('hides closeout button when project.status is cancelled', async () => {
      mockSortedJobs.value = [
        { agent_display_name: 'orchestrator', status: 'complete' },
      ]

      const wrapper = createWrapper({ status: 'cancelled' })
      await flushPromises()

      expect(wrapper.find('[data-testid="close-project-btn"]').exists()).toBe(false)
    })
  })

  // ==================== DONE BANNER TESTS ====================

  describe('Done banner shows for terminal project statuses', () => {
    it('shows completed banner with correct text', async () => {
      const wrapper = createWrapper({ status: 'completed' })
      await flushPromises()

      const banner = wrapper.find('[data-testid="project-done-banner"]')
      expect(banner.exists()).toBe(true)
      expect(banner.text()).toContain('Project Completed and Closed')
    })

    it('shows terminated banner with correct text', async () => {
      const wrapper = createWrapper({ status: 'terminated' })
      await flushPromises()

      const banner = wrapper.find('[data-testid="project-done-banner"]')
      expect(banner.exists()).toBe(true)
      expect(banner.text()).toContain('Project Terminated')
    })

    it('shows cancelled banner with correct text', async () => {
      const wrapper = createWrapper({ status: 'cancelled' })
      await flushPromises()

      const banner = wrapper.find('[data-testid="project-done-banner"]')
      expect(banner.exists()).toBe(true)
      expect(banner.text()).toContain('Project Cancelled')
    })
  })

  // ==================== CONTINUE GUIDANCE TEST ====================

  describe('Continue working guidance', () => {
    it('shows guidance after continue event from CloseoutModal', async () => {
      mockSortedJobs.value = [
        { agent_display_name: 'orchestrator', status: 'complete' },
        { agent_display_name: 'implementor', status: 'complete' },
      ]

      // After continue-working, loadProjectData refreshes agents to 'waiting'
      mockLoadJobs.mockImplementationOnce(() => {
        mockSortedJobs.value = [
          { agent_display_name: 'orchestrator', status: 'waiting' },
          { agent_display_name: 'implementor', status: 'waiting' },
        ]
        return Promise.resolve([])
      })

      const wrapper = createWrapper({ status: 'active' })
      await flushPromises()

      // Emit @continue from CloseoutModal
      const modal = wrapper.findComponent({ name: 'CloseoutModal' })
      modal.vm.$emit('continue')
      await flushPromises()

      const guidance = wrapper.find('[data-testid="continue-guidance"]')
      expect(guidance.exists()).toBe(true)
    })
  })

  // ==================== STAY ON PAGE TEST ====================

  describe('Closeout stays on page', () => {
    it('does not navigate away after closeout event', async () => {
      mockSortedJobs.value = [
        { agent_display_name: 'orchestrator', status: 'complete' },
        { agent_display_name: 'implementor', status: 'complete' },
      ]

      const wrapper = createWrapper({ status: 'active' })
      await flushPromises()

      // Emit @closeout from CloseoutModal
      const modal = wrapper.findComponent({ name: 'CloseoutModal' })
      modal.vm.$emit('closeout', { project_id: 'proj-1', sequence_number: 1 })
      await flushPromises()

      expect(mockRouter.push).not.toHaveBeenCalled()
    })
  })
})
