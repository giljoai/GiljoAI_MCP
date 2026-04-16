/**
 * ProjectTabs Re-Stage Button Lifecycle Tests
 *
 * Tests the Stage/Re-Stage/Staging... button lifecycle,
 * isStaging hydration from backend, and restage UX flow.
 *
 * Covers:
 * - Button shows "Stage Project" when no staging_status
 * - Button shows "Re-Stage" when staging + orchestrator waiting
 * - Button shows "Staging..." (disabled) when orchestrator active
 * - Re-Stage click calls restage endpoint and resets UI
 * - Navigate away and back: button state persists from store
 * - Execution mode locked when isStaging, unlocked after restage
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

function createWrapper(projectOverrides = {}, extraProps = {}) {
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
    props: { project, orchestrator: null, ...extraProps },
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

/**
 * Helper: set up orchestrator job in the mock jobs list
 */
function setOrchestratorJob(status) {
  mockJobsRef.value = [
    {
      job_id: 'orch-job-1',
      agent_id: 'orch-agent-1',
      unique_key: 'orch-agent-1',
      agent_display_name: 'orchestrator',
      agent_name: 'orchestrator',
      status,
    },
  ]
}

describe('ProjectTabs - Re-Stage Button Lifecycle', () => {
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

    it('shows "Re-Stage" when isStaging is true and orchestrator is waiting', async () => {
      const wrapper = createWrapper({ staging_status: 'staging' })
      await flushPromises()

      // Set isStaging in state store (hydrated from backend)
      const stateStore = useProjectStateStore()
      stateStore.setIsStaging('project-123', true)

      // Set orchestrator to waiting status
      setOrchestratorJob('waiting')
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      expect(stageButton.text()).toContain('Re-Stage')
    })

    it('shows "Staging..." when isStaging is true and orchestrator is active/working', async () => {
      const wrapper = createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      stateStore.setIsStaging('project-123', true)

      // Set orchestrator to working status
      setOrchestratorJob('working')
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      expect(stageButton.text()).toContain('Staging...')
    })

    it('"Staging..." button is disabled', async () => {
      const wrapper = createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      stateStore.setIsStaging('project-123', true)

      setOrchestratorJob('working')
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      expect(stageButton.attributes('disabled')).toBeDefined()
    })
  })

  // ==================== RE-STAGE CLICK TESTS ====================

  describe('Re-Stage Click Behavior', () => {
    it('calls restage API endpoint when Re-Stage is clicked', async () => {
      const wrapper = createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      stateStore.setIsStaging('project-123', true)
      setOrchestratorJob('waiting')
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      expect(api.projects.restage).toHaveBeenCalledWith('project-123')
    })

    it('resets isStaging to false after successful restage', async () => {
      const wrapper = createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      stateStore.setIsStaging('project-123', true)
      setOrchestratorJob('waiting')
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      const state = stateStore.getProjectState('project-123')
      expect(state.isStaging).toBe(false)
    })

    it('clears execution mode selection after successful restage', async () => {
      const wrapper = createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      stateStore.setIsStaging('project-123', true)
      setOrchestratorJob('waiting')

      // Select a mode before restage
      wrapper.vm.executionPlatform = 'claude_code_cli'
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      expect(wrapper.vm.executionPlatform).toBeNull()
    })

    it('button returns to "Stage Project" (disabled) after restage', async () => {
      const wrapper = createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      stateStore.setIsStaging('project-123', true)
      setOrchestratorJob('waiting')

      wrapper.vm.executionPlatform = 'multi_terminal'
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      // After restage: isStaging is false, executionPlatform is null
      // Button text should be "Stage Project" and disabled (no mode selected)
      expect(stageButton.text()).toContain('Stage Project')
      expect(stageButton.attributes('disabled')).toBeDefined()
    })

    it('shows success toast after restage', async () => {
      const wrapper = createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      stateStore.setIsStaging('project-123', true)
      setOrchestratorJob('waiting')
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      expect(mockShowToast).toHaveBeenCalledWith(expect.objectContaining({
        type: 'success',
      }))
    })

    it('shows error toast when restage fails', async () => {
      api.projects.restage.mockRejectedValueOnce(new Error('Restage failed'))

      const wrapper = createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      stateStore.setIsStaging('project-123', true)
      setOrchestratorJob('waiting')
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
    it('execution mode is locked when isStaging is true', async () => {
      const wrapper = createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      stateStore.setIsStaging('project-123', true)
      await flushPromises()

      const modeRow = wrapper.find('.execution-mode-pills')
      expect(modeRow.classes()).toContain('mode-locked')
    })

    it('execution mode is unlocked after restage completes', async () => {
      const wrapper = createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      stateStore.setIsStaging('project-123', true)
      setOrchestratorJob('waiting')
      await flushPromises()

      // Confirm locked
      let modeRow = wrapper.find('.execution-mode-pills')
      expect(modeRow.classes()).toContain('mode-locked')

      // Trigger restage
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
    it('isStaging hydrates from staging_status on project load', async () => {
      // Project has staging_status = 'staging' from backend
      createWrapper({ staging_status: 'staging' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      const state = stateStore.getProjectState('project-123')
      // isStaging should be hydrated from backend data
      expect(state.isStaging).toBe(true)
    })

    it('isStaging is false when staging_status is null', async () => {
      createWrapper({ staging_status: null })
      await flushPromises()

      const stateStore = useProjectStateStore()
      const state = stateStore.getProjectState('project-123')
      expect(state.isStaging).toBe(false)
    })

    it('isStaging is false when staging_status is staging_complete', async () => {
      createWrapper({ staging_status: 'staging_complete' })
      await flushPromises()

      const stateStore = useProjectStateStore()
      const state = stateStore.getProjectState('project-123')
      // staging_complete means staging is done, isStaging should be false
      expect(state.isStaging).toBe(false)
    })
  })

  // ==================== RESTAGE STORE ACTION TESTS ====================

  describe('projectStateStore.restageProject', () => {
    it('calls POST restage endpoint', async () => {
      createWrapper()
      await flushPromises()

      const stateStore = useProjectStateStore()
      await stateStore.restageProject('project-123')

      expect(api.projects.restage).toHaveBeenCalledWith('project-123')
    })

    it('sets isStaging to false on success', async () => {
      createWrapper()
      await flushPromises()

      const stateStore = useProjectStateStore()
      stateStore.setIsStaging('project-123', true)

      await stateStore.restageProject('project-123')

      const state = stateStore.getProjectState('project-123')
      expect(state.isStaging).toBe(false)
    })

    it('clears stagingComplete on success', async () => {
      createWrapper()
      await flushPromises()

      const stateStore = useProjectStateStore()
      stateStore.setStagingComplete('project-123', true)

      await stateStore.restageProject('project-123')

      const state = stateStore.getProjectState('project-123')
      expect(state.stagingComplete).toBe(false)
    })

    it('throws on API error', async () => {
      api.projects.restage.mockRejectedValueOnce(new Error('Network error'))

      createWrapper()
      await flushPromises()

      const stateStore = useProjectStateStore()
      await expect(stateStore.restageProject('project-123')).rejects.toThrow('Network error')
    })
  })
})
