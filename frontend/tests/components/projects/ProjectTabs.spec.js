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

// Import the mocked module so we can reference it in tests
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
    setActivePinia(createPinia())
    mockRoute.query = {}
    mockRoute.hash = ''
    mockRouter.replace.mockClear()
    mockRouter.push.mockClear()
    mockShowToast.mockClear()
    mockCopy.mockClear()
    mockSortedJobs.value = []
    // Reset API mocks
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

    it('is disabled when staging is already complete (hasActiveOrchestrator)', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Mark staging as complete in the project state store
      const stateStore = useProjectStateStore()
      stateStore.setStagingComplete('project-123', true)

      // Select execution mode
      wrapper.vm.executionPlatform = 'multi_terminal'
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
        message: expect.stringContaining('Orchestrator prompt copied'),
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
      await wrapper.vm.handleExecutionModeChange('claude_code_cli')
      await flushPromises()

      expect(api.projects.update).toHaveBeenCalledWith(
        'project-123',
        { execution_mode: 'claude_code_cli' },
      )
    })

    it('shows info toast after execution mode change', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      await wrapper.vm.handleExecutionModeChange('claude_code_cli')
      await flushPromises()

      expect(mockShowToast).toHaveBeenCalledWith(expect.objectContaining({
        type: 'info',
        message: expect.stringContaining('Claude Code CLI'),
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
})
