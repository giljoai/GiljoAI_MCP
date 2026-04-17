/**
 * ProjectTabs Stage/Unstage Button Lifecycle Tests
 *
 * Tests the Stage/Unstage/Staging... button lifecycle,
 * isStaged hydration from backend, and unstage UX flow.
 *
 * Covers:
 * - Button shows "Stage Project" when no staging_status
 * - Button shows "Unstage" when staging_status = 'staged' (reversible)
 * - Button shows "Staging..." (disabled) when staging_status = 'staging' (irreversible)
 * - Unstage click calls unstage endpoint and resets UI
 * - Navigate away and back: button state persists from store
 * - Execution mode locked when staged/staging, unlocked after unstage
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import { ref, computed } from 'vue'
import ProjectTabs from '@/components/projects/ProjectTabs.vue'
import { useProjectStateStore } from '@/stores/projectStateStore'

// -- Router mock --

const mockRoute = { query: {}, hash: '' }
const mockRouter = { push: vi.fn(), replace: vi.fn() }

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
  useRouter: () => mockRouter,
}))

// -- Composable mocks --

const mockJobsRef = ref([])
const mockSortedJobs = computed(() => mockJobsRef.value)
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

const mockCopy = vi.fn().mockResolvedValue(true)
vi.mock('@/composables/useClipboard', () => ({
  useClipboard: () => ({
    copy: mockCopy,
  }),
}))

// -- Store mocks --

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

// -- API mock --

vi.mock('@/services/api', () => ({
  default: {
    projects: {
      get: vi.fn().mockResolvedValue({ data: {} }),
      update: vi.fn().mockResolvedValue({}),
      restage: vi.fn().mockResolvedValue({ data: { message: 'Restage successful' } }),
      unstage: vi.fn().mockResolvedValue({ data: { message: 'Unstage successful' } }),
    },
    prompts: {
      staging: vi.fn().mockResolvedValue({
        data: {
          prompt: 'Test staging prompt',
          estimated_prompt_tokens: 100,
        },
      }),
    },
    orchestrator: {
      launchProject: vi.fn().mockResolvedValue({}),
    },
    products: {
      getMemoryEntries: vi.fn().mockResolvedValue({ data: { entries: [] } }),
    },
  },
}))

import api from '@/services/api'

// -- Helper --

function createWrapper(projectOverrides = {}) {
  const vuetify = createVuetify()
  const project = {
    id: 'project-123',
    project_id: 'project-123',
    name: 'Test Project',
    description: 'Test description',
    status: 'active',
    execution_mode: 'multi_terminal',
    ...projectOverrides,
  }

  return mount(ProjectTabs, {
    props: { project, orchestrator: null },
    global: {
      plugins: [vuetify],
      stubs: {
        LaunchTab: {
          name: 'LaunchTab',
          template: '<div class="launch-tab-stub" />',
          props: ['project', 'orchestrator', 'isStaging', 'gitEnabled', 'serenaEnabled'],
          emits: ['edit-description'],
        },
        JobsTab: {
          name: 'JobsTab',
          template: '<div class="jobs-tab-stub" />',
          props: ['project'],
        },
        CloseoutModal: {
          name: 'CloseoutModal',
          template: '<div class="closeout-modal-stub" />',
          props: ['show', 'projectId', 'projectName', 'productId'],
          emits: ['close', 'closeout', 'continue'],
        },
        'v-tooltip': {
          template: '<div class="v-tooltip-stub"><slot /><slot name="activator" /></div>',
        },
        'v-progress-circular': {
          template: '<div class="v-progress-circular-stub" />',
        },
      },
    },
  })
}

describe('ProjectTabs - Stage/Unstage Button Lifecycle', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockRoute.query = {}
    mockRoute.hash = ''
    mockRouter.replace.mockClear()
    mockRouter.push.mockClear()
    mockShowToast.mockClear()
    mockCopy.mockClear()
    mockJobsRef.value = []
    api.prompts.staging.mockClear()
    api.prompts.staging.mockResolvedValue({
      data: { prompt: 'Test staging prompt', estimated_prompt_tokens: 100 },
    })
    api.orchestrator.launchProject.mockClear()
    api.projects.update.mockClear()
    api.projects.restage.mockClear()
    api.projects.restage.mockResolvedValue({ data: { message: 'Restage successful' } })
    api.projects.unstage.mockClear()
    api.projects.unstage.mockResolvedValue({ data: { message: 'Unstage successful' } })
    api.products.getMemoryEntries.mockClear()
    api.products.getMemoryEntries.mockResolvedValue({ data: { entries: [] } })
  })

  // ==================== BUTTON TEXT TESTS ====================

  describe('Button Text Lifecycle', () => {
    it('shows "Stage Project" when no staging_status (fresh project)', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      expect(stageButton.text()).toContain('Stage Project')
    })

    it('shows "Unstage" when staging_status is staged', async () => {
      const wrapper = createWrapper({ staging_status: 'staged' })
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      expect(stageButton.text()).toContain('Unstage')
    })

    it('shows "Staging..." when staging_status is staging (agent contacted)', async () => {
      const wrapper = createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      expect(stageButton.text()).toContain('Staging...')
    })

    it('"Staging..." button is disabled (irreversible)', async () => {
      const wrapper = createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      expect(stageButton.attributes('disabled')).toBeDefined()
    })

    it('"Unstage" button is NOT disabled (reversible)', async () => {
      const wrapper = createWrapper({ staging_status: 'staged' })
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      expect(stageButton.attributes('disabled')).toBeUndefined()
    })
  })

  // ==================== UNSTAGE CLICK TESTS ====================

  describe('Unstage Click Behavior', () => {
    it('calls unstage API endpoint when Unstage is clicked', async () => {
      const wrapper = createWrapper({ staging_status: 'staged' })
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      expect(api.projects.unstage).toHaveBeenCalledWith('project-123')
    })

    it('resets isStaged to false after successful unstage', async () => {
      const wrapper = createWrapper({ staging_status: 'staged' })
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      const stateStore = useProjectStateStore()
      const state = stateStore.getProjectState('project-123')
      expect(state.isStaged).toBe(false)
    })

    it('button returns to "Stage Project" after unstage', async () => {
      const wrapper = createWrapper({ staging_status: 'staged' })
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      expect(stageButton.text()).toContain('Stage Project')
    })

    it('shows success toast after unstage', async () => {
      const wrapper = createWrapper({ staging_status: 'staged' })
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      expect(mockShowToast).toHaveBeenCalledWith(expect.objectContaining({
        type: 'success',
      }))
    })

    it('shows error toast when unstage fails', async () => {
      api.projects.unstage.mockRejectedValueOnce(new Error('Unstage failed'))

      const wrapper = createWrapper({ staging_status: 'staged' })
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      expect(mockShowToast).toHaveBeenCalledWith(expect.objectContaining({
        type: 'error',
      }))
    })
  })

  // ==================== EXECUTION MODE LOCK TESTS ====================

  describe('Execution Mode Lock', () => {
    it('execution mode is locked when staged', async () => {
      const wrapper = createWrapper({ staging_status: 'staged' })
      await flushPromises()

      const modeRow = wrapper.find('.execution-mode-pills')
      expect(modeRow.classes()).toContain('mode-locked')
    })

    it('execution mode is locked when staging', async () => {
      const wrapper = createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const modeRow = wrapper.find('.execution-mode-pills')
      expect(modeRow.classes()).toContain('mode-locked')
    })

    it('execution mode is unlocked after unstage completes', async () => {
      const wrapper = createWrapper({ staging_status: 'staged' })
      await flushPromises()

      // Confirm locked
      let modeRow = wrapper.find('.execution-mode-pills')
      expect(modeRow.classes()).toContain('mode-locked')

      // Trigger unstage
      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      // Should be unlocked now
      modeRow = wrapper.find('.execution-mode-pills')
      expect(modeRow.classes()).not.toContain('mode-locked')
    })
  })

  // ==================== STATE PERSISTENCE TESTS ====================

  describe('State Persistence', () => {
    it('isStaged hydrates from staging_status=staged on project load', async () => {
      createWrapper({ staging_status: 'staged' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      const state = stateStore.getProjectState('project-123')
      expect(state.isStaged).toBe(true)
      expect(state.isStaging).toBe(false)
    })

    it('isStaging hydrates from staging_status=staging on project load', async () => {
      createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      const state = stateStore.getProjectState('project-123')
      expect(state.isStaged).toBe(false)
      expect(state.isStaging).toBe(true)
    })

    it('both false when staging_status is null', async () => {
      createWrapper({ staging_status: null })
      await flushPromises()

      const stateStore = useProjectStateStore()
      const state = stateStore.getProjectState('project-123')
      expect(state.isStaged).toBe(false)
      expect(state.isStaging).toBe(false)
    })

    it('both false when staging_status is staging_complete', async () => {
      createWrapper({ staging_status: 'staging_complete' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      const state = stateStore.getProjectState('project-123')
      expect(state.isStaged).toBe(false)
      expect(state.isStaging).toBe(false)
    })
  })

  // ==================== UNSTAGE STORE ACTION TESTS ====================

  describe('projectStateStore.unstageProject', () => {
    it('calls POST unstage endpoint', async () => {
      createWrapper()
      await flushPromises()

      const stateStore = useProjectStateStore()
      stateStore.setIsStaged('project-123', true)
      await stateStore.unstageProject('project-123')

      expect(api.projects.unstage).toHaveBeenCalledWith('project-123')
    })

    it('sets isStaged to false on success', async () => {
      createWrapper()
      await flushPromises()

      const stateStore = useProjectStateStore()
      stateStore.setIsStaged('project-123', true)

      await stateStore.unstageProject('project-123')

      const state = stateStore.getProjectState('project-123')
      expect(state.isStaged).toBe(false)
    })

    it('throws on API error', async () => {
      api.projects.unstage.mockRejectedValueOnce(new Error('Network error'))

      createWrapper()
      await flushPromises()

      const stateStore = useProjectStateStore()
      await expect(stateStore.unstageProject('project-123')).rejects.toThrow('Network error')
    })
  })
})
