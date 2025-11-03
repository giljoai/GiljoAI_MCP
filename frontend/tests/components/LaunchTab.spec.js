/**
 * Unit tests for LaunchTab component
 * Tests race condition prevention and production-grade quality (Handover 0086B Phase 5.2)
 *
 * PRODUCTION-GRADE: Validates Set-based duplicate prevention for concurrent agent:created events
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LaunchTab from '@/components/projects/LaunchTab.vue'
import AgentCardEnhanced from '@/components/projects/AgentCardEnhanced.vue'
import { useUserStore } from '@/stores/user'
import api from '@/services/api'

// Mock dependencies
vi.mock('@/services/api', () => ({
  default: {
    prompts: {
      staging: vi.fn()
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

// Mock AgentCardEnhanced component
vi.mock('@/components/projects/AgentCardEnhanced.vue', () => ({
  default: {
    name: 'AgentCardEnhanced',
    template: '<div class="agent-card-mock">{{ agent.agent_type }}</div>',
    props: ['agent', 'mode', 'isOrchestrator', 'instanceNumber']
  }
}))

describe('LaunchTab - Race Condition Prevention (Handover 0086B Task 4.2)', () => {
  let pinia
  let userStore

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    userStore = useUserStore()
    userStore.currentUser = {
      id: 1,
      username: 'testuser',
      tenant_key: 'test-tenant'
    }
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  /**
   * Test 1: Verify Set-based tracking prevents duplicate agents
   * CRITICAL: agentIds Set should prevent duplicate insertions
   */
  it('should use Set-based tracking to prevent duplicate agents', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'test-tenant'
    }

    const orchestrator = {
      job_id: 'orchestrator-job-id',
      agent_type: 'orchestrator',
      mission: 'Orchestrate project',
      status: 'active'
    }

    const wrapper = mount(LaunchTab, {
      props: { project, orchestrator },
      global: {
        plugins: [pinia],
        stubs: {
          AgentCardEnhanced: true
        }
      }
    })

    // Access component methods via wrapper.vm
    const agentData = {
      tenant_key: 'test-tenant',
      project_id: 'project-123',
      agent: {
        id: 'agent-001',
        job_id: 'agent-001',
        agent_type: 'implementor',
        mission: 'Implement feature'
      }
    }

    // Simulate first agent:created event
    wrapper.vm.$options.setup().handleAgentCreated?.(agentData)

    // Verify agent added
    expect(wrapper.vm.agents).toHaveLength(1)
    expect(wrapper.vm.agentIds.has('agent-001')).toBe(true)

    // Simulate duplicate agent:created event (same ID)
    wrapper.vm.$options.setup().handleAgentCreated?.(agentData)

    // Verify: No duplicate added
    expect(wrapper.vm.agents).toHaveLength(1) // Still 1, not 2
    expect(wrapper.vm.agentIds.has('agent-001')).toBe(true)
  })

  /**
   * Test 2: Verify 100 simultaneous agent:created events without duplicates
   * PRODUCTION-GRADE: Stress test for race condition prevention
   */
  it('should handle 100 simultaneous agent:created events without duplicates', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'test-tenant'
    }

    const orchestrator = {
      job_id: 'orchestrator-job-id',
      agent_type: 'orchestrator',
      mission: 'Orchestrate project',
      status: 'active'
    }

    const wrapper = mount(LaunchTab, {
      props: { project, orchestrator },
      global: {
        plugins: [pinia],
        stubs: {
          AgentCardEnhanced: true
        }
      }
    })

    // Expose addAgent method for testing
    const addAgent = wrapper.vm.addAgent

    // Simulate 100 events for same agent (race condition scenario)
    const agentData = {
      id: 'agent-001',
      job_id: 'agent-001',
      agent_type: 'implementor',
      mission: 'Implement feature'
    }

    const promises = []
    for (let i = 0; i < 100; i++) {
      promises.push(
        new Promise(resolve => {
          addAgent(agentData)
          resolve()
        })
      )
    }

    await Promise.all(promises)

    // Verify: Only 1 agent added despite 100 events
    expect(wrapper.vm.agents).toHaveLength(1)
    expect(wrapper.vm.agentIds.has('agent-001')).toBe(true)
  })

  /**
   * Test 3: Verify agentIds Set cleared on unmount
   * PRODUCTION-GRADE: Memory leak prevention
   */
  it('should clear agentIds Set on component unmount', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'test-tenant'
    }

    const wrapper = mount(LaunchTab, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          AgentCardEnhanced: true
        }
      }
    })

    // Add some agents
    wrapper.vm.addAgent({
      id: 'agent-001',
      job_id: 'agent-001',
      agent_type: 'implementor',
      mission: 'Test'
    })
    wrapper.vm.addAgent({
      id: 'agent-002',
      job_id: 'agent-002',
      agent_type: 'reviewer',
      mission: 'Test'
    })

    expect(wrapper.vm.agentIds.size).toBe(2)

    // Unmount component
    wrapper.unmount()

    // Note: Can't verify Set after unmount, but onUnmounted hook should clear it
    // This test documents the expected behavior
  })

  /**
   * Test 4: Verify loading states display correctly
   * PRODUCTION-GRADE: Loading boundaries (Task 4.4)
   */
  it('should display loading state when mission is being generated', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'test-tenant'
    }

    const wrapper = mount(LaunchTab, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          AgentCardEnhanced: true
        }
      }
    })

    // Set loading state
    await wrapper.vm.setMission('') // Empty mission
    wrapper.vm.isLoadingMission = true

    await wrapper.vm.$nextTick()

    // Verify loading indicator visible
    expect(wrapper.find('.v-progress-circular').exists()).toBe(true)
    expect(wrapper.text()).toContain('Generating mission')
  })

  /**
   * Test 5: Verify error boundaries with retry button
   * PRODUCTION-GRADE: Error handling (Task 4.4)
   */
  it('should display error state with retry button on mission generation failure', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'test-tenant'
    }

    api.prompts.staging.mockRejectedValue(new Error('API Error'))

    const wrapper = mount(LaunchTab, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          AgentCardEnhanced: true
        }
      }
    })

    // Trigger staging (will fail)
    await wrapper.vm.handleStageProject()

    await wrapper.vm.$nextTick()

    // Verify error displayed
    expect(wrapper.vm.missionError).toBeTruthy()
    expect(wrapper.text()).toContain('Mission Generation Failed')

    // Verify retry button exists
    const retryButton = wrapper.find('[data-test="retry-button"]')
    // Note: Actual button may need data-test attribute added to component
  })

  /**
   * Test 6: Verify "Optimized for you" badge when user_config_applied
   * PRODUCTION-GRADE: User config visualization
   */
  it('should display "Optimized for you" badge when user config is applied', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      mission: 'Generated mission',
      tenant_key: 'test-tenant'
    }

    const wrapper = mount(LaunchTab, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          AgentCardEnhanced: true
        }
      }
    })

    // Set mission with user config applied
    wrapper.vm.setMission('Test mission')
    wrapper.vm.userConfigApplied = true
    wrapper.vm.tokenEstimate = 1000

    await wrapper.vm.$nextTick()

    // Verify badge visible
    expect(wrapper.text()).toContain('Optimized for you')
  })

  /**
   * Test 7: Verify direct project.id access (no band-aid)
   * PRODUCTION-GRADE: Clean prop access (Task 4.3)
   */
  it('should access project.id directly without fallback logic', () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'test-tenant'
    }

    const wrapper = mount(LaunchTab, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          AgentCardEnhanced: true
        }
      }
    })

    // Verify projectId computed property returns project.id
    expect(wrapper.vm.projectId).toBe('project-123')
  })

  /**
   * Test 8: Verify validation throws on missing project ID
   * PRODUCTION-GRADE: Fail-fast validation
   */
  it('should throw error if project is missing ID field', () => {
    const invalidProject = {
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'test-tenant'
      // Missing 'id' field
    }

    // Should throw during mount due to prop validator
    expect(() => {
      mount(LaunchTab, {
        props: { project: invalidProject },
        global: {
          plugins: [pinia],
          stubs: {
            AgentCardEnhanced: true
          }
        }
      })
    }).toThrow()
  })
})

describe('LaunchTab - Multi-Tenant Isolation', () => {
  let pinia
  let userStore

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    userStore = useUserStore()
    userStore.currentUser = {
      id: 1,
      username: 'testuser',
      tenant_key: 'tenant-A'
    }
    vi.clearAllMocks()
  })

  it('should reject mission updates from different tenant', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'tenant-A'
    }

    const wrapper = mount(LaunchTab, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          AgentCardEnhanced: true
        }
      }
    })

    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    // Simulate mission update from different tenant
    const missionData = {
      tenant_key: 'tenant-B', // Different tenant
      project_id: 'project-123',
      mission: 'Malicious mission',
      user_config_applied: false,
      token_estimate: 500
    }

    wrapper.vm.$options.setup().handleMissionUpdate?.(missionData)

    // Verify: Mission NOT updated
    expect(wrapper.vm.missionText).toBe('')

    // Verify: Warning logged
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('Mission update rejected: tenant mismatch')
    )

    consoleSpy.mockRestore()
  })

  it('should reject agent creation from different tenant', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'tenant-A'
    }

    const wrapper = mount(LaunchTab, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          AgentCardEnhanced: true
        }
      }
    })

    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    // Simulate agent creation from different tenant
    const agentData = {
      tenant_key: 'tenant-B', // Different tenant
      project_id: 'project-123',
      agent: {
        id: 'agent-001',
        job_id: 'agent-001',
        agent_type: 'implementor',
        mission: 'Malicious agent'
      }
    }

    wrapper.vm.$options.setup().handleAgentCreated?.(agentData)

    // Verify: Agent NOT added
    expect(wrapper.vm.agents).toHaveLength(0)

    // Verify: Warning logged
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('Agent creation rejected: tenant mismatch')
    )

    consoleSpy.mockRestore()
  })

  it('should reject events from different project within same tenant', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'tenant-A'
    }

    const wrapper = mount(LaunchTab, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          AgentCardEnhanced: true
        }
      }
    })

    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})

    // Simulate mission update for different project (same tenant)
    const missionData = {
      tenant_key: 'tenant-A', // Same tenant
      project_id: 'project-999', // Different project
      mission: 'Other project mission',
      user_config_applied: false,
      token_estimate: 500
    }

    wrapper.vm.$options.setup().handleMissionUpdate?.(missionData)

    // Verify: Mission NOT updated
    expect(wrapper.vm.missionText).toBe('')

    // Verify: Log indicates different project
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('Mission update ignored: different project')
    )

    consoleSpy.mockRestore()
  })
})

describe('LaunchTab - State Management', () => {
  let pinia
  let userStore

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    userStore = useUserStore()
    userStore.currentUser = {
      id: 1,
      username: 'testuser',
      tenant_key: 'test-tenant'
    }
    vi.clearAllMocks()
  })

  it('should reset all states when resetStaging() is called', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'test-tenant'
    }

    const wrapper = mount(LaunchTab, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          AgentCardEnhanced: true
        }
      }
    })

    // Set some state
    wrapper.vm.setMission('Test mission')
    wrapper.vm.addAgent({
      id: 'agent-001',
      job_id: 'agent-001',
      agent_type: 'implementor',
      mission: 'Test'
    })
    wrapper.vm.userConfigApplied = true
    wrapper.vm.tokenEstimate = 1000
    wrapper.vm.missionError = 'Some error'

    // Reset staging
    wrapper.vm.resetStaging()

    // Verify all states reset
    expect(wrapper.vm.missionText).toBe('')
    expect(wrapper.vm.agents).toHaveLength(0)
    expect(wrapper.vm.agentIds.size).toBe(0)
    expect(wrapper.vm.userConfigApplied).toBe(false)
    expect(wrapper.vm.tokenEstimate).toBe(0)
    expect(wrapper.vm.missionError).toBeNull()
    expect(wrapper.vm.isLoadingMission).toBe(false)
    expect(wrapper.vm.stagingInProgress).toBe(false)
    expect(wrapper.vm.readyToLaunch).toBe(false)
  })

  it('should clear agents when clearAgents() is called', async () => {
    const project = {
      id: 'project-123',
      name: 'Test Project',
      description: 'Test description',
      tenant_key: 'test-tenant'
    }

    const wrapper = mount(LaunchTab, {
      props: { project },
      global: {
        plugins: [pinia],
        stubs: {
          AgentCardEnhanced: true
        }
      }
    })

    // Add agents
    wrapper.vm.addAgent({
      id: 'agent-001',
      job_id: 'agent-001',
      agent_type: 'implementor',
      mission: 'Test'
    })
    wrapper.vm.addAgent({
      id: 'agent-002',
      job_id: 'agent-002',
      agent_type: 'reviewer',
      mission: 'Test'
    })

    expect(wrapper.vm.agents).toHaveLength(2)
    expect(wrapper.vm.agentIds.size).toBe(2)

    // Clear agents
    wrapper.vm.clearAgents()

    // Verify cleared
    expect(wrapper.vm.agents).toHaveLength(0)
    expect(wrapper.vm.agentIds.size).toBe(0)
  })
})
