/**
 * ProjectTabs 360 Memory Gate Tests (Handover 0822)
 *
 * Tests the memory gate feature that delays the closeout button
 * until 360 memory has been written (or fail-open on error).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import ProjectTabs from '@/components/projects/ProjectTabs.vue'

// -- Hoisted mocks (vi.mock is hoisted, so referenced variables must be too) --

const {
  mockRouter,
  mockRoute,
  mockSortedJobs,
  mockLoadJobs,
  mockShowToast,
  mockWsOn,
  mockGetMemoryEntries,
} = vi.hoisted(() => {
  const mockGetMemoryEntries = vi.fn().mockResolvedValue({ data: { entries: [] } })
  const mockWsOn = vi.fn().mockImplementation(() => vi.fn())
  return {
    mockRouter: { push: vi.fn(), replace: vi.fn() },
    mockRoute: { query: {}, hash: '' },
    mockSortedJobs: { value: [] },
    mockLoadJobs: vi.fn().mockResolvedValue([]),
    mockShowToast: vi.fn(),
    mockWsOn,
    mockGetMemoryEntries,
  }
})

// Variable to capture the WS handler - set at runtime, not hoisted
let capturedMemoryHandler = null

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
  useRouter: () => mockRouter,
}))

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
    on: mockWsOn,
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
    products: {
      getMemoryEntries: mockGetMemoryEntries,
    },
  },
}))

// -- Test data --

const terminalJobs = [
  { id: '1', agent_display_name: 'orchestrator', status: 'complete' },
  { id: '2', agent_display_name: 'specialist-a', status: 'completed' },
]

const projectWithProduct = {
  id: 'proj-1',
  project_id: 'proj-1',
  name: 'Test Project',
  description: 'Test',
  product_id: 'prod-1',
  status: 'active',
  execution_mode: 'multi_terminal',
}

const projectWithoutProduct = {
  ...projectWithProduct,
  product_id: null,
}

// -- Helpers --

function createWrapper(projectOverrides = {}) {
  const vuetify = createVuetify()
  const project = { ...projectWithProduct, ...projectOverrides }

  return mount(ProjectTabs, {
    props: { project, orchestrator: null },
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

// -- Tests --

describe('ProjectTabs - 360 Memory Gate (Handover 0822)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockRouter.push.mockClear()
    mockRouter.replace.mockClear()
    mockShowToast.mockClear()
    mockGetMemoryEntries.mockClear()
    capturedMemoryHandler = null
    mockSortedJobs.value = []
    mockRoute.query = { tab: 'jobs' }
    mockRoute.hash = ''
    // Reset getMemoryEntries to default (empty entries)
    mockGetMemoryEntries.mockResolvedValue({ data: { entries: [] } })
    // Reset wsStore.on to capture handler
    mockWsOn.mockClear()
    mockWsOn.mockImplementation((event, handler) => {
      if (event === 'product:memory:updated') {
        capturedMemoryHandler = handler
      }
      return vi.fn() // unsubscribe function
    })
  })

  // ==================== GROUP 1: showCloseoutButton computed ====================

  describe('showCloseoutButton computed', () => {
    it('does NOT show closeout button when all jobs terminal but memory not written (with product_id)', async () => {
      mockSortedJobs.value = terminalJobs

      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.find('[data-testid="close-project-btn"]').exists()).toBe(false)
      expect(wrapper.find('[data-testid="memory-pending-chip"]').exists()).toBe(true)
    })

    it('shows closeout button when all jobs terminal AND memory written', async () => {
      mockSortedJobs.value = terminalJobs
      mockGetMemoryEntries.mockResolvedValue({ data: { entries: [{ id: '1' }] } })

      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.find('[data-testid="close-project-btn"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="memory-pending-chip"]').exists()).toBe(false)
    })

    it('shows closeout button immediately when no product_id (skip gate)', async () => {
      mockSortedJobs.value = terminalJobs

      const wrapper = createWrapper({ product_id: null })
      await flushPromises()

      expect(wrapper.find('[data-testid="close-project-btn"]').exists()).toBe(true)
    })
  })

  // ==================== GROUP 2: API watcher behavior ====================

  describe('API watcher behavior', () => {
    it('calls getMemoryEntries when all jobs become terminal', async () => {
      mockSortedJobs.value = terminalJobs

      createWrapper()
      await flushPromises()

      expect(mockGetMemoryEntries).toHaveBeenCalledWith('prod-1', {
        project_id: 'proj-1',
        limit: 1,
      })
    })

    it('fails open on API error', async () => {
      mockSortedJobs.value = terminalJobs
      mockGetMemoryEntries.mockRejectedValue(new Error('Network error'))

      const wrapper = createWrapper()
      await flushPromises()

      // Fail open: closeout button should appear despite API error
      expect(wrapper.find('[data-testid="close-project-btn"]').exists()).toBe(true)
    })

    it('does not call API when no product_id', async () => {
      mockSortedJobs.value = terminalJobs

      createWrapper({ product_id: null })
      await flushPromises()

      expect(mockGetMemoryEntries).not.toHaveBeenCalled()
    })
  })

  // ==================== GROUP 3: WebSocket handler ====================

  describe('WebSocket handler', () => {
    it('sets memoryWritten when matching project_id event received', async () => {
      mockSortedJobs.value = terminalJobs

      const wrapper = createWrapper()
      await flushPromises()

      // The handler should have been captured during mount
      expect(capturedMemoryHandler).not.toBeNull()

      // Simulate WS event with matching project_id
      capturedMemoryHandler({ entry: { project_id: 'proj-1' } })
      await flushPromises()

      expect(wrapper.find('[data-testid="close-project-btn"]').exists()).toBe(true)
    })

    it('ignores events for other projects', async () => {
      mockSortedJobs.value = terminalJobs

      const wrapper = createWrapper()
      await flushPromises()

      expect(capturedMemoryHandler).not.toBeNull()

      // Simulate WS event with different project_id
      capturedMemoryHandler({ entry: { project_id: 'other-proj' } })
      await flushPromises()

      expect(wrapper.find('[data-testid="close-project-btn"]').exists()).toBe(false)
      expect(wrapper.find('[data-testid="memory-pending-chip"]').exists()).toBe(true)
    })
  })

  // ==================== GROUP 4: Template rendering ====================

  describe('Template rendering', () => {
    it('shows "Saving project memory..." chip with spinner', async () => {
      mockSortedJobs.value = terminalJobs

      const wrapper = createWrapper()
      await flushPromises()

      const chip = wrapper.find('[data-testid="memory-pending-chip"]')
      expect(chip.exists()).toBe(true)
      expect(chip.text()).toContain('Saving project memory')
      // Vuetify v-chip renders with color and variant attributes
      expect(chip.attributes('color')).toBe('info')
      expect(chip.attributes('variant')).toBe('tonal')
    })

    it('does not show memory pending chip when project has terminal status', async () => {
      mockSortedJobs.value = terminalJobs

      const wrapper = createWrapper({ status: 'completed' })
      await flushPromises()

      expect(wrapper.find('[data-testid="memory-pending-chip"]').exists()).toBe(false)
      // The done banner shows for terminal project statuses
      const banner = wrapper.find('[data-testid="project-done-banner"]')
      expect(banner.exists()).toBe(true)
      expect(banner.text()).toContain('Project Completed and Closed')
    })
  })
})
