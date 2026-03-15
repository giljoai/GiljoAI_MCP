/**
 * Unit tests for Handover 0287: Launch Button Staging Complete Signal
 *
 * Tests the staging-complete detection pattern:
 * - readyToLaunch computed checks projectStateStore.getProjectState(pid)?.stagingComplete
 * - hasActiveOrchestrator disables stage button after staging completes
 * - Launch button enables only when stagingComplete is true and execution mode is selected
 * - Execution mode must be selected before staging/launching
 *
 * Test Coverage:
 * 1. Launch button disabled when staging not complete
 * 2. Launch button enables after staging complete is set in projectStateStore
 * 3. Stage button disabled after staging complete (hasActiveOrchestrator)
 * 4. Both buttons disabled when no execution mode selected
 * 5. Launch button disabled during active staging (isStaging true)
 * 6. Staging complete resets when projectStateStore is reset
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import ProjectTabs from '@/components/projects/ProjectTabs.vue'
import { useProjectStateStore } from '@/stores/projectStateStore'

// -- Mocks --

const mockRouter = { push: vi.fn(), replace: vi.fn() }
const mockRoute = { query: {}, hash: '' }

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
  useRouter: () => mockRouter,
}))

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
      getMemoryEntries: vi.fn().mockResolvedValue({ data: { entries: [] } }),
    },
  },
}))

// -- Helpers --

const PROJECT_ID = 'project-123'

/**
 * Create wrapper with a SHARED pinia instance.
 *
 * Critical: The pinia must be passed as a mount plugin so the component
 * uses the same instance as the test's useProjectStateStore() calls.
 * Without this, the component gets the global setup pinia while the test
 * operates on a separate pinia from setActivePinia.
 */
function createWrapper(pinia, projectOverrides = {}) {
  const vuetify = createVuetify()
  const project = {
    id: PROJECT_ID,
    project_id: PROJECT_ID,
    name: 'Test Project',
    description: 'Test description',
    status: 'active',
    execution_mode: 'multi_terminal',
    ...projectOverrides,
  }

  return mount(ProjectTabs, {
    props: { project, orchestrator: null },
    global: {
      plugins: [vuetify, pinia],
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

/**
 * Activate execution mode selection by setting a mission in the project state store.
 *
 * The component watches missionText and syncs usingClaudeCodeSubagents from
 * project.execution_mode when a mission exists. This makes executionModeSelected
 * become true without needing to click Vuetify radio buttons (which are stubbed
 * and non-functional in the test environment).
 *
 * Must be called AFTER mount + flushPromises so loadProjectData runs first
 * (which would otherwise overwrite the mission with an empty string).
 */
async function activateExecutionMode(store) {
  store.setMission(PROJECT_ID, 'Test mission for execution mode sync')
  await flushPromises()
}

describe('Handover 0287: Launch Button Staging Complete Signal', () => {
  let pinia
  let projectStateStore

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    projectStateStore = useProjectStateStore()
    mockRouter.push.mockClear()
    mockRouter.replace.mockClear()
    mockShowToast.mockClear()
    mockSortedJobs.value = []
    mockRoute.query = {}
    mockRoute.hash = ''
  })

  /**
   * Test 1: Launch button is disabled when staging has not completed
   */
  it('launch button is disabled when staging is not complete', async () => {
    const wrapper = createWrapper(pinia)
    await flushPromises()

    const launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')
    expect(launchButton.exists()).toBe(true)
    expect(launchButton.attributes('disabled')).toBeDefined()
  })

  /**
   * Test 2: Launch button enables after stagingComplete is set in projectStateStore
   *
   * The component's readyToLaunch computed checks:
   *   projectStateStore.getProjectState(pid)?.stagingComplete && !isStaging
   *
   * The launch button disabled condition is:
   *   !executionModeSelected || !readyToLaunch
   */
  it('launch button enables after staging complete is set in projectStateStore', async () => {
    const wrapper = createWrapper(pinia)
    await flushPromises()

    // Activate execution mode (sets mission so watcher syncs radio)
    await activateExecutionMode(projectStateStore)

    // Set staging complete in the project state store
    projectStateStore.setStagingComplete(PROJECT_ID, true)
    await flushPromises()

    const launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')
    expect(launchButton.attributes('disabled')).toBeUndefined()
  })

  /**
   * Test 3: Stage button disabled after staging complete (hasActiveOrchestrator)
   *
   * hasActiveOrchestrator checks projectStateStore.getProjectState(pid)?.stagingComplete
   * Stage button disabled condition: !executionModeSelected || hasActiveOrchestrator
   */
  it('stage button is disabled after staging complete', async () => {
    const wrapper = createWrapper(pinia)
    await flushPromises()

    // Activate execution mode
    await activateExecutionMode(projectStateStore)

    // Before staging complete, stage button should be enabled
    let stageButton = wrapper.find('[data-testid="stage-project-btn"]')
    expect(stageButton.attributes('disabled')).toBeUndefined()

    // Set staging complete
    projectStateStore.setStagingComplete(PROJECT_ID, true)
    await flushPromises()

    // After staging complete, stage button should be disabled (hasActiveOrchestrator = true)
    stageButton = wrapper.find('[data-testid="stage-project-btn"]')
    expect(stageButton.attributes('disabled')).toBeDefined()
  })

  /**
   * Test 4: Both buttons require execution mode selection
   *
   * executionModeSelected computed checks usingClaudeCodeSubagents !== null
   * Both stage and launch buttons are disabled when no mode is selected.
   */
  it('stage and launch buttons are disabled when no execution mode selected', async () => {
    const wrapper = createWrapper(pinia)
    await flushPromises()

    const stageButton = wrapper.find('[data-testid="stage-project-btn"]')
    const launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')

    // No execution mode selected - both should be disabled
    expect(stageButton.attributes('disabled')).toBeDefined()
    expect(launchButton.attributes('disabled')).toBeDefined()
  })

  /**
   * Test 5: Launch button disabled during active staging (isStaging true)
   *
   * readyToLaunch requires stagingComplete AND !isStaging
   */
  it('launch button remains disabled when staging is in progress', async () => {
    const wrapper = createWrapper(pinia)
    await flushPromises()

    // Activate execution mode
    await activateExecutionMode(projectStateStore)

    // Set staging in progress AND staging complete simultaneously
    // readyToLaunch = stagingComplete && !isStaging => false
    projectStateStore.setStagingComplete(PROJECT_ID, true)
    projectStateStore.setIsStaging(PROJECT_ID, true)
    await flushPromises()

    const launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')
    expect(launchButton.attributes('disabled')).toBeDefined()
  })

  /**
   * Test 6: Staging complete flag properly resets via projectStateStore.$reset()
   */
  it('staging complete resets when projectStateStore is reset', async () => {
    const wrapper = createWrapper(pinia)
    await flushPromises()

    // Activate execution mode
    await activateExecutionMode(projectStateStore)

    // Set staging complete
    projectStateStore.setStagingComplete(PROJECT_ID, true)
    await flushPromises()

    let launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')
    expect(launchButton.attributes('disabled')).toBeUndefined()

    // Reset the project state store - clears all state including mission
    projectStateStore.$reset()
    await flushPromises()

    // After reset, readyToLaunch is false because stagingComplete state is gone.
    // The launch button should be disabled again.
    launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')
    expect(launchButton.attributes('disabled')).toBeDefined()
  })
})
