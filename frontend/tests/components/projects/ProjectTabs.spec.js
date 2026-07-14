/**
 * ProjectTabs Component Tests
 *
 * Tests action buttons (Stage Project, Implement), tab navigation,
 * button state management, and LaunchTab integration.
 *
 * Follows the same mock/mount pattern as ProjectTabs.closeout.spec.js.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
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

vi.mock('@/services/api', () => {
  const apiMock = {
    projects: {
      // FE-3007a: ProjectTabs no longer self-fetches on initial mount (the
      // page-open double-fetch is gone — the view fetches the canonical row
      // into the store and passes it down). This get() is only hit on a real
      // project switch / WS reconnect, routed through the project store (which
      // imports the NAMED `api` export — hence the dual export below).
      get: vi.fn().mockResolvedValue({
        data: {
          id: 'project-123',
          project_id: 'project-123',
          name: 'Test Project',
          description: 'Test description',
          status: 'active',
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
  }
  return { api: apiMock, default: apiMock }
})

// Import the mocked module so we can reference it in tests
import api from '@/services/api'

// -- Helper --

// FE-6061: tests/setup.js adds a global pinia to config.global.plugins.
// When mount() is called, Vue Test Utils installs the global pinia FIRST
// (via app.provide(piniaSymbol, global_pinia)), then installs the per-test
// pinia SECOND. Because app.provide overwrites, the component ends up using
// the per-test pinia — giving each test a fresh, isolated store.
// The per-test pinia must be created in beforeEach and passed here so that
// direct useProjectStateStore() calls in the test body and the mounted
// component's internal calls all use the SAME pinia instance.
let currentTestPinia = null

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
      plugins: [vuetify, currentTestPinia],
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
        // Stubs for Vuetify components not in global setup
        'v-btn-toggle': {
          template: '<div class="v-btn-toggle-stub"><slot /></div>',
          props: ['modelValue'],
        },
        'v-radio-group': {
          template: '<div class="v-radio-group-stub"><slot /></div>',
          props: ['modelValue', 'inline', 'hideDetails', 'density', 'disabled'],
          emits: ['update:model-value'],
        },
        'v-radio': {
          template: '<div class="v-radio-stub" v-bind="$attrs"><slot /></div>',
          props: ['value', 'label'],
        },
        'v-tooltip': {
          template: '<div class="v-tooltip-stub"><slot /><slot name="activator" /></div>',
        },
        'v-window': {
          template: '<div class="v-window-stub"><slot /></div>',
          props: ['modelValue'],
        },
        'v-window-item': {
          template: '<div class="v-window-item-stub"><slot /></div>',
          props: ['value'],
        },
        'v-progress-circular': {
          template: '<div class="v-progress-circular-stub" />',
        },
      },
    },
  })
}

describe('ProjectTabs - Action Buttons', () => {
  beforeEach(() => {
    // FE-6061: Create a fresh pinia per test and set it as both the active
    // pinia (for direct useProjectStateStore() calls) and as a per-test
    // plugin passed to createWrapper (so mounted components use it too via
    // app.use(pinia) → app.provide(piniaSymbol) which overrides the global
    // pinia from tests/setup.js). This ensures tests that directly call store
    // methods AND the mounted component always read/write the same fresh store.
    currentTestPinia = createPinia()
    setActivePinia(currentTestPinia)
    mockRoute.query = {}
    mockRoute.hash = ''
    mockRouter.replace.mockClear()
    mockRouter.push.mockClear()
    mockShowToast.mockClear()
    mockCopy.mockClear()
    mockSortedJobs.value = []
    // Reset API mocks
    api.projects.get.mockClear()
    api.projects.get.mockResolvedValue({
      data: {
        id: 'project-123',
        project_id: 'project-123',
        name: 'Test Project',
        description: 'Test description',
        status: 'active',
        staging_status: null,
        implementation_launched_at: null,
        execution_mode: 'multi_terminal',
        mission: '',
        alias: 'BE-0001',
        agent_count: 0,
        message_count: 0,
        agents: [],
      },
    })
    api.prompts.staging.mockClear()
    api.prompts.staging.mockResolvedValue({
      data: { prompt: 'Test staging prompt', estimated_prompt_tokens: 100 },
    })
    api.orchestrator.launchProject.mockClear()
    api.orchestrator.launchProject.mockResolvedValue({})
    api.projects.update.mockClear()
    api.products.getMemoryEntries.mockClear()
    api.products.getMemoryEntries.mockResolvedValue({ data: { entries: [] } })
  })

  // ==================== LAYOUT TESTS ====================

  describe('Button Layout', () => {
    it('renders action buttons row on the launch tab', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const actionRow = wrapper.find('.action-buttons-row')
      expect(actionRow.exists()).toBe(true)
    })

    it('displays Stage Project button', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      expect(stageButton.exists()).toBe(true)
      expect(stageButton.text()).toContain('Stage Project')
    })

    it('displays Implement button (launch jobs)', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')
      expect(launchButton.exists()).toBe(true)
      expect(launchButton.text()).toContain('Implement')
    })

    it('renders both buttons in the same action-buttons-row', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const actionRow = wrapper.find('.action-buttons-row')
      const stageBtn = actionRow.find('[data-testid="stage-project-btn"]')
      const launchBtn = actionRow.find('[data-testid="launch-jobs-btn"]')
      expect(stageBtn.exists()).toBe(true)
      expect(launchBtn.exists()).toBe(true)
    })
  })

  // ==================== STAGE BUTTON STATE TESTS ====================

  describe('Stage Project Button', () => {
    it('is disabled when no execution mode is selected (default state)', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      // Default: executionPlatform is null, executionModeSelected is false
      expect(stageButton.attributes('disabled')).toBeDefined()
    })

    it('is enabled once an execution mode is selected and no active orchestrator', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Directly set the execution mode on the component instance
      // (radio stubs don't support v-model binding, so we set it programmatically)
      wrapper.vm.executionPlatform = 'multi_terminal'
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      expect(stageButton.attributes('disabled')).toBeUndefined()
    })

    // BE-6047: staging_complete WITHOUT implementation launched → button is ENABLED as "Re-Stage" (recovery affordance)
    // staging_complete WITH implementation launched → button is DISABLED (no recovery possible)
    it('shows Re-Stage (enabled) when staging complete but implementation not yet launched', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Mark staging as complete in the project state store (no implementation launched)
      const stateStore = useProjectStateStore()
      stateStore.setStagingComplete('project-123', true)

      // Select execution mode
      wrapper.vm.executionPlatform = 'multi_terminal'
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      // BE-6047: button should be ENABLED as recovery affordance
      expect(stageButton.attributes('disabled')).toBeUndefined()
      expect(stageButton.text()).toBe('Re-Stage')
    })

    it('is disabled when staging complete AND implementation already launched', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Set staging complete + implementation launched (Implement button was clicked)
      const stateStore = useProjectStateStore()
      stateStore.setStagingComplete('project-123', true)
      stateStore.setImplementationLaunched('project-123', '2026-06-07T00:00:00Z')

      wrapper.vm.executionPlatform = 'multi_terminal'
      await flushPromises()

      // FE-6228: implementation_launched now trips the same-project auto-flip to
      // the jobs pane (the solo auto-follow contract — consistent with chain).
      // That is intended; this test asserts the orthogonal concern of the stage
      // button's disabled STATE, which lives on the launch pane, so return to it
      // explicitly before asserting.
      wrapper.vm.activeTab = 'launch'
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      expect(stageButton.attributes('disabled')).toBeDefined()
    })

    it('calls API staging endpoint when clicked', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Select execution mode
      wrapper.vm.executionPlatform = 'multi_terminal'
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      expect(api.prompts.staging).toHaveBeenCalledWith('project-123', expect.objectContaining({
        tool: 'claude-code',
        execution_mode: 'multi_terminal',
      }))
    })

    it('copies prompt to clipboard after successful staging', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Select execution mode
      wrapper.vm.executionPlatform = 'multi_terminal'
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      expect(mockCopy).toHaveBeenCalledWith('Test staging prompt')
    })

    it('shows success toast after prompt is copied', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Select execution mode
      wrapper.vm.executionPlatform = 'multi_terminal'
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      expect(mockShowToast).toHaveBeenCalledWith(expect.objectContaining({
        message: expect.stringContaining('Orchestrator brief copied'),
        type: 'success',
      }))
    })
  })

  // ==================== LAUNCH BUTTON STATE TESTS ====================

  describe('Implement (Launch Jobs) Button', () => {
    it('is disabled when project is not ready to launch', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')
      expect(launchButton.attributes('disabled')).toBeDefined()
    })

    it('is enabled when execution mode selected and staging is complete', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Mark staging as complete in state store
      const stateStore = useProjectStateStore()
      stateStore.setStagingComplete('project-123', true)

      // Select execution mode
      wrapper.vm.executionPlatform = 'multi_terminal'
      await flushPromises()

      const launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')
      expect(launchButton.attributes('disabled')).toBeUndefined()
    })

    it('calls orchestrator.launchProject API when clicked', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Set up ready-to-launch state
      const stateStore = useProjectStateStore()
      stateStore.setStagingComplete('project-123', true)

      wrapper.vm.executionPlatform = 'multi_terminal'
      await flushPromises()

      const launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')
      await launchButton.trigger('click')
      await flushPromises()

      expect(api.orchestrator.launchProject).toHaveBeenCalledWith({
        project_id: 'project-123',
      })
    })

    it('switches to jobs tab after successful launch', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Set up ready-to-launch state
      const stateStore = useProjectStateStore()
      stateStore.setStagingComplete('project-123', true)

      wrapper.vm.executionPlatform = 'multi_terminal'
      await flushPromises()

      const launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')
      await launchButton.trigger('click')
      await flushPromises()

      // Check the internal activeTab ref changed to 'jobs'
      expect(wrapper.vm.activeTab).toBe('jobs')
    })
  })

  // ==================== BUTTON STYLING TESTS ====================

  describe('Button Styling', () => {
    it('Stage button uses stage-button CSS class', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      expect(stageButton.classes()).toContain('stage-button')
    })

    it('Launch button uses launch-button CSS class', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')
      expect(launchButton.classes()).toContain('launch-button')
    })

    it('Stage button has outlined variant attribute', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      expect(stageButton.attributes('variant')).toBe('outlined')
    })
  })

  // ==================== TAB NAVIGATION TESTS ====================

  describe('Tab Navigation', () => {
    it('defaults activeTab to launch', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.activeTab).toBe('launch')
    })

    it('renders launch tab and jobs tab buttons', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.find('[data-testid="launch-tab"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="jobs-tab"]').exists()).toBe(true)
    })

    it('initializes tab from URL query param', async () => {
      mockRoute.query = { tab: 'jobs' }

      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.activeTab).toBe('jobs')
    })

    it('hides stage/launch buttons when on jobs tab', async () => {
      mockRoute.query = { tab: 'jobs' }

      const wrapper = createWrapper()
      await flushPromises()

      // The stage/launch buttons are v-if="activeTab === 'launch'", so hidden on jobs tab
      const stageBtn = wrapper.find('[data-testid="stage-project-btn"]')
      expect(stageBtn.exists()).toBe(false)
    })
  })

  // ==================== LAUNCHTAB INTEGRATION TESTS ====================

  describe('LaunchTab Integration', () => {
    it('passes project prop to LaunchTab', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const launchTab = wrapper.findComponent({ name: 'LaunchTab' })
      expect(launchTab.exists()).toBe(true)
      expect(launchTab.props('project')).toMatchObject({ project_id: 'project-123' })
    })

    it('passes orchestrator prop to LaunchTab', async () => {
      const wrapper = createWrapper({}, { orchestrator: { id: 'orch-1' } })
      await flushPromises()

      const launchTab = wrapper.findComponent({ name: 'LaunchTab' })
      expect(launchTab.props('orchestrator')).toEqual({ id: 'orch-1' })
    })

    it('relays edit-description event from LaunchTab', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const launchTab = wrapper.findComponent({ name: 'LaunchTab' })
      launchTab.vm.$emit('edit-description')
      await flushPromises()

      expect(wrapper.emitted('edit-description')).toBeTruthy()
    })
  })

  // ==================== EXECUTION MODE TESTS ====================

  describe('Execution Mode', () => {
    it('renders execution mode radio area on launch tab', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.find('.execution-mode-row').exists()).toBe(true)
    })

    it('persists execution mode change to backend via API', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Call the handler directly with a valid execution mode value
      // BE-9035c: the UI only ever writes 'multi_terminal' or 'subagent' now.
      await wrapper.vm.handleExecutionModeChange('subagent')
      await flushPromises()

      expect(api.projects.update).toHaveBeenCalledWith(
        'project-123',
        { execution_mode: 'subagent' },
      )
    })

    it('shows info toast after execution mode change', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      await wrapper.vm.handleExecutionModeChange('subagent')
      await flushPromises()

      expect(mockShowToast).toHaveBeenCalledWith(expect.objectContaining({
        type: 'info',
        message: expect.stringContaining('Subagent'),
      }))
    })
  })

  // ==================== ERROR HANDLING TESTS ====================

  describe('Error Handling', () => {
    it('shows error toast when staging fails', async () => {
      api.prompts.staging.mockRejectedValueOnce(new Error('Staging failed'))

      const wrapper = createWrapper()
      await flushPromises()

      // Select execution mode
      wrapper.vm.executionPlatform = 'multi_terminal'
      await flushPromises()

      const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
      await stageButton.trigger('click')
      await flushPromises()

      expect(mockShowToast).toHaveBeenCalledWith(expect.objectContaining({
        type: 'error',
      }))
    })

    it('shows error toast when launch fails', async () => {
      api.orchestrator.launchProject.mockRejectedValueOnce(new Error('Launch failed'))

      const wrapper = createWrapper()
      await flushPromises()

      // Set up ready-to-launch state
      const stateStore = useProjectStateStore()
      stateStore.setStagingComplete('project-123', true)

      wrapper.vm.executionPlatform = 'multi_terminal'
      await flushPromises()

      const launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')
      await launchButton.trigger('click')
      await flushPromises()

      expect(mockShowToast).toHaveBeenCalledWith(expect.objectContaining({
        type: 'error',
      }))
    })
  })

  // ==================== PROJECT HEADER TESTS ====================

  describe('Project Header', () => {
    it('displays project name', async () => {
      // With mount-time API hydration, localProject is set from the API
      // response, not just the parent prop.  Override the fetch to return
      // the custom name so the display reflects the canonical server value.
      api.projects.get.mockResolvedValueOnce({
        data: {
          id: 'project-123',
          project_id: 'project-123',
          name: 'My Test Project',
          description: 'Test description',
          status: 'active',
          staging_status: null,
          implementation_launched_at: null,
          execution_mode: 'multi_terminal',
          mission: '',
          alias: 'BE-0001',
          agent_count: 0,
          message_count: 0,
          agents: [],
        },
      })
      const wrapper = createWrapper({ name: 'My Test Project' })
      await flushPromises()

      expect(wrapper.text()).toContain('My Test Project')
    })

    it('displays project ID', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.text()).toContain('project-123')
    })
  })

  // ==================== MOUNT-TIME HYDRATION TESTS ====================

  describe('Store-first staging state, no mount double-fetch (FE-5070 Part 2 / FE-3007a)', () => {
    it('derives readyToLaunch from the canonical project prop and does NOT self-fetch on mount', async () => {
      // FE-3007a relocated the FE-5070 guarantee: ProjectTabs no longer fetches
      // the canonical row itself on mount (that was the page-open double-fetch).
      // The VIEW fetches the canonical project into the store and passes it down,
      // so the prop ProjectTabs receives is already canonical — there is no
      // stale-prop window to "correct" and no second GET. Here the canonical
      // prop carries staging_complete; readyToLaunch must follow it.
      api.projects.get.mockClear()

      const wrapper = createWrapper({ staging_status: 'staging_complete' })
      await flushPromises()

      // executionModeSelected requires executionPlatform !== null.
      wrapper.vm.executionPlatform = 'multi_terminal'
      await flushPromises()

      const launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')
      expect(launchButton.exists()).toBe(true)
      // readyToLaunch true (stagingComplete derived from the canonical prop),
      // executionModeSelected true → button enabled.
      expect(launchButton.attributes('disabled')).toBeUndefined()

      // The double-fetch is gone: ProjectTabs issued no project GET on mount.
      expect(api.projects.get).not.toHaveBeenCalled()
    })
  })
})
