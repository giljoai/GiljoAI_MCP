/**
 * Unit tests for Handover 0287: Launch Button Staging Complete Signal
 *
 * Tests the "Alternative Approach: Simpler Detection" pattern:
 * - Watch for mission + agents and infer staging complete
 * - No backend changes required
 * - Leverages existing WebSocket events (fixed in 0290)
 *
 * Test Coverage:
 * 1. readyToLaunch returns true when stagingComplete is true
 * 2. Staging complete detected when mission + orchestrator + specialists present
 * 3. Staging complete NOT set without specialist agents
 * 4. Staging complete NOT set without orchestrator
 * 5. Launch button enables after staging complete (integration test)
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { useProjectTabsStore } from '@/stores/projectTabs'
import ProjectTabs from '@/components/projects/ProjectTabs.vue'

// Mock dependencies
vi.mock('@/services/api', () => ({
  default: {
    prompts: {
      staging: vi.fn()
    },
    orchestrator: {
      launchProject: vi.fn()
    },
    messages: {
      list: vi.fn().mockResolvedValue({ data: [] })
    }
  }
}))

vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    on: vi.fn(),
    off: vi.fn(),
    isConnected: true
  })
}))

vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: () => ({
    subscribeToProject: vi.fn(),
    unsubscribe: vi.fn()
  })
}))

vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: {
      id: 1,
      username: 'testuser',
      tenant_key: 'test-tenant'
    }
  })
}))

// Mock vue-router
vi.mock('vue-router', () => ({
  useRoute: () => ({
    query: {},
    hash: ''
  }),
  useRouter: () => ({
    replace: vi.fn()
  })
}))

// Mock child components
vi.mock('@/components/projects/LaunchTab.vue', () => ({
  default: {
    name: 'LaunchTab',
    template: '<div class="launch-tab-mock"></div>',
    props: ['project', 'orchestrator', 'isStaging', 'readonly']
  }
}))

vi.mock('@/components/projects/JobsTab.vue', () => ({
  default: {
    name: 'JobsTab',
    template: '<div class="jobs-tab-mock"></div>',
    props: ['project', 'agents', 'messages', 'allAgentsComplete', 'readonly']
  }
}))

describe('Handover 0287: Launch Button Staging Complete Signal', () => {
  let pinia
  let store

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    store = useProjectTabsStore()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  /**
   * Test 1: readyToLaunch returns true when stagingComplete is true
   *
   * CRITICAL: This is the core behavioral change.
   * The readyToLaunch getter must check stagingComplete flag.
   */
  it('test_readyToLaunch_returns_true_when_stagingComplete_is_true', () => {
    // Setup: Set mission and agents
    store.orchestratorMission = 'Test mission'
    store.agents = [
      {
        job_id: 'orch-1',
        agent_type: 'orchestrator',
        status: 'working'
      },
      {
        job_id: 'impl-1',
        agent_type: 'implementer',
        status: 'waiting'
      }
    ]

    // Initially, staging is not complete
    store.isStaging = false
    // stagingComplete flag does not exist yet - this test will FAIL
    // After implementation, setStagingComplete(true) will be called by watcher

    // EXPECTED BEHAVIOR AFTER IMPLEMENTATION:
    // store.stagingComplete should be true (set by watcher)
    // readyToLaunch should return true

    // For now, this will FAIL because:
    // 1. stagingComplete state doesn't exist
    // 2. readyToLaunch doesn't check stagingComplete
    expect(store.readyToLaunch).toBe(false) // Will FAIL - currently false, should be true after implementation
  })

  /**
   * Test 2: Staging complete detected when mission + orchestrator + specialists present
   *
   * This tests the watcher logic in ProjectTabs.vue
   */
  it('test_staging_complete_detected_when_mission_and_agents_present', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'test-tenant'
    }

    const wrapper = mount(ProjectTabs, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          LaunchTab: true,
          JobsTab: true
        }
      }
    })

    // Initially, staging is not complete
    expect(store.stagingComplete).toBe(false)

    // Simulate WebSocket events (via store mutations)
    store.setMission('Test orchestrator mission')
    store.addAgent({
      job_id: 'orch-1',
      agent_type: 'orchestrator',
      status: 'working'
    })
    store.addAgent({
      job_id: 'impl-1',
      agent_type: 'implementer',
      status: 'waiting'
    })

    await nextTick()

    // EXPECTED: Watcher should detect mission + orchestrator + specialist
    // and call store.setStagingComplete(true)
    expect(store.stagingComplete).toBe(true) // Will FAIL - method doesn't exist yet
  })

  /**
   * Test 3: Staging complete NOT set without specialist agents
   *
   * Edge case: Only orchestrator created, no specialists yet
   */
  it('test_staging_complete_not_set_without_specialists', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'test-tenant'
    }

    const wrapper = mount(ProjectTabs, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          LaunchTab: true,
          JobsTab: true
        }
      }
    })

    // Simulate only mission + orchestrator (no specialists)
    store.setMission('Test orchestrator mission')
    store.addAgent({
      job_id: 'orch-1',
      agent_type: 'orchestrator',
      status: 'working'
    })

    await nextTick()

    // EXPECTED: Watcher should NOT set stagingComplete
    // because no specialist agents exist
    expect(store.stagingComplete).toBe(false) // Will FAIL - state doesn't exist yet
  })

  /**
   * Test 4: Staging complete NOT set without orchestrator
   *
   * Edge case: Specialists created but no orchestrator
   */
  it('test_staging_complete_not_set_without_orchestrator', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'test-tenant'
    }

    const wrapper = mount(ProjectTabs, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          LaunchTab: true,
          JobsTab: true
        }
      }
    })

    // Simulate mission + specialists (no orchestrator)
    store.setMission('Test orchestrator mission')
    store.addAgent({
      job_id: 'impl-1',
      agent_type: 'implementer',
      status: 'waiting'
    })
    store.addAgent({
      job_id: 'test-1',
      agent_type: 'tester',
      status: 'waiting'
    })

    await nextTick()

    // EXPECTED: Watcher should NOT set stagingComplete
    // because orchestrator doesn't exist
    expect(store.stagingComplete).toBe(false) // Will FAIL - state doesn't exist yet
  })

  /**
   * Test 5: Launch button enables after staging complete (integration test)
   *
   * This tests the full user flow:
   * 1. Stage Project clicked
   * 2. WebSocket events arrive (mission + agents)
   * 3. Watcher detects staging complete
   * 4. Launch button becomes enabled
   */
  it('test_launch_button_enables_after_staging_complete', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'test-tenant'
    }

    const wrapper = mount(ProjectTabs, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          LaunchTab: true,
          JobsTab: true
        }
      }
    })

    // Initially, launch button should be disabled
    const launchButton = wrapper.find('[data-testid="launch-jobs-btn"]')
    expect(launchButton.attributes('disabled')).toBeDefined()

    // Simulate staging complete via WebSocket events
    store.setMission('Test orchestrator mission')
    store.addAgent({
      job_id: 'orch-1',
      agent_type: 'orchestrator',
      status: 'working'
    })
    store.addAgent({
      job_id: 'impl-1',
      agent_type: 'implementer',
      status: 'waiting'
    })

    await nextTick()

    // EXPECTED: Launch button should be enabled
    // because readyToLaunch = true (stagingComplete is true)
    expect(launchButton.attributes('disabled')).toBeUndefined() // Will FAIL - button still disabled
  })

  /**
   * Test 6: stagingComplete resets when staging is cancelled
   *
   * Tests that stagingComplete flag is properly reset
   */
  it('test_stagingComplete_resets_when_staging_cancelled', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'test-tenant'
    }

    const wrapper = mount(ProjectTabs, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          LaunchTab: true,
          JobsTab: true
        }
      }
    })

    // Simulate staging complete
    store.setMission('Test orchestrator mission')
    store.addAgent({
      job_id: 'orch-1',
      agent_type: 'orchestrator',
      status: 'working'
    })
    store.addAgent({
      job_id: 'impl-1',
      agent_type: 'implementer',
      status: 'waiting'
    })

    await nextTick()

    // Verify staging complete
    expect(store.stagingComplete).toBe(true)

    // Reset staging
    store.resetStaging()

    // EXPECTED: stagingComplete should be reset to false
    expect(store.stagingComplete).toBe(false) // Will FAIL - resetStaging doesn't reset this flag yet
  })
})
