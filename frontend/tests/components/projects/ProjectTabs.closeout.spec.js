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
    on: vi.fn().mockReturnValue(vi.fn()),
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
      // Mount-time hydration now fetches from API; return a complete object
      // so localProject and projectStateStore are populated correctly.
      // Tests that need custom status pass it via createWrapper projectOverrides
      // AND override this mock with mockResolvedValueOnce when needed.
      get: vi.fn().mockResolvedValue({
        data: {
          id: 'proj-1',
          project_id: 'proj-1',
          name: 'Test Project',
          description: 'Test',
          status: 'active',
          product_id: 'prod-1',
          staging_status: null,
          implementation_launched_at: null,
          execution_mode: 'multi_terminal',
          mission: '',
          alias: 'BE-0001',
          agent_count: 0,
          message_count: 0,
          agents: [],
        },
      }),
      update: vi.fn().mockResolvedValue({}),
    },
    prompts: {
      staging: vi.fn().mockResolvedValue({ data: { prompt: 'test' } }),
    },
    orchestrator: {
      launchProject: vi.fn().mockResolvedValue({}),
    },
    products: {
      getMemoryEntries: vi.fn().mockResolvedValue({ data: { entries: [] } }),
    },
  },
}))

// Import the mocked module so we can reference it in helpers
import api from '@/services/api'

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

  // Mount-time hydration now calls api.projects.get; pre-configure the mock
  // to return matching data so status, staging_status, etc. are not overwritten.
  api.projects.get.mockResolvedValueOnce({
    data: {
      id: project.id,
      project_id: project.project_id,
      name: project.name,
      description: project.description || 'Test',
      status: project.status || 'active',
      product_id: project.product_id || null,
      staging_status: project.staging_status ?? null,
      implementation_launched_at: project.implementation_launched_at ?? null,
      execution_mode: project.execution_mode || 'multi_terminal',
      mission: project.mission || '',
      alias: 'BE-0001',
      agent_count: 0,
      message_count: 0,
      agents: [],
    },
  })

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
    api.projects.get.mockClear()
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

  // The "Continue working guidance" affordance was REMOVED with the chain rework
  // (CHAIN_ARCHITECTURE.md §11: closing a project is now a Review, not a
  // Continue-Working gate). ProjectTabs no longer renders [data-testid=
  // "continue-guidance"] nor wires CloseoutModal's @continue to it, so the former
  // "shows guidance after continue event" test asserted removed behavior and was
  // deleted. The Review-badge flow is covered by the chain pill/review specs.

  // ==================== STAY ON PAGE + EMIT TEST ====================

  describe('Closeout stays on page and emits project-updated', () => {
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

    it('emits project-updated so parent can refetch', async () => {
      mockSortedJobs.value = []

      const wrapper = createWrapper({ status: 'active' })
      await flushPromises()

      const modal = wrapper.findComponent({ name: 'CloseoutModal' })
      modal.vm.$emit('closeout')
      await flushPromises()

      expect(wrapper.emitted('project-updated')).toBeTruthy()
    })
  })
})
