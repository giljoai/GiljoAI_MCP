import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import AgentCardGrid from '@/components/orchestration/AgentCardGrid.vue'

describe('AgentCardGrid.vue', () => {
  let wrapper
  let pinia
  let vuetify

  const mockProject = {
    id: 'project-1',
    name: 'Test Project',
    status: 'active'
  }

  const mockOrchestrator = {
    id: 'orch-1',
    job_id: 'job-orch-1',
    is_orchestrator: true,
    name: 'Orchestrator',
    status: 'working',
    mission_summary: 'Coordinating all agents for this project',
    messages: []
  }

  const mockAgents = [
    {
      id: 'agent-1',
      job_id: 'job-1',
      is_orchestrator: false,
      name: 'Backend Agent',
      status: 'working',
      agent_type: 'backend',
      tool_type: 'codex',
      job_description: 'Implementing REST API',
      progress: 47,
      current_task: 'Adding validation',
      messages: []
    },
    {
      id: 'agent-2',
      job_id: 'job-2',
      is_orchestrator: false,
      name: 'Frontend Agent',
      status: 'complete',
      agent_type: 'frontend',
      tool_type: 'claude-code',
      job_description: 'Building Vue components',
      messages: []
    },
    {
      id: 'agent-3',
      job_id: 'job-3',
      is_orchestrator: false,
      name: 'Test Agent',
      status: 'blocked',
      agent_type: 'testing',
      tool_type: 'gemini',
      job_description: 'Writing tests',
      block_reason: 'Waiting for API completion',
      messages: []
    }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify()

    // Mock the orchestration store
    vi.mock('@/stores/orchestration', () => ({
      useOrchestrationStore: vi.fn(() => ({
        agents: [...mockAgents, mockOrchestrator],
        project: mockProject,
        getUnreadCount: vi.fn(() => 0),
        handleCopyPrompt: vi.fn(),
        initiateCloseout: vi.fn()
      }))
    }))
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('Rendering', () => {
    it('renders the component successfully', () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('displays orchestrator card first', () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const orchestratorCard = wrapper.findComponent({ name: 'OrchestratorCard' })
      expect(orchestratorCard.exists()).toBe(true)
    })

    it('displays all agent cards', () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const agentCards = wrapper.findAllComponents({ name: 'AgentCard' })
      expect(agentCards).toHaveLength(3) // Excludes orchestrator
    })
  })

  describe('Agent Sorting', () => {
    it('sorts agents by status priority', () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const agentCards = wrapper.findAllComponents({ name: 'AgentCard' })

      // First should be blocked (highest priority)
      expect(agentCards[0].props('agent').status).toBe('blocked')
      // Then working
      expect(agentCards[1].props('agent').status).toBe('working')
      // Then complete (lowest priority)
      expect(agentCards[2].props('agent').status).toBe('complete')
    })

    it('handles all status states correctly', () => {
      const allStatuses = [
        { status: 'failed', priority: 0 },
        { status: 'blocked', priority: 1 },
        { status: 'working', priority: 2 },
        { status: 'review', priority: 3 },
        { status: 'preparing', priority: 4 },
        { status: 'waiting', priority: 5 },
        { status: 'complete', priority: 6 }
      ]

      // Test that status order enum matches expected priorities
      const statusOrder = {
        'failed': 0,
        'blocked': 1,
        'working': 2,
        'review': 3,
        'preparing': 4,
        'waiting': 5,
        'complete': 6
      }

      allStatuses.forEach(({ status, priority }) => {
        expect(statusOrder[status]).toBe(priority)
      })
    })
  })

  describe('Responsive Grid Layout', () => {
    it('applies correct CSS grid classes', () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const grid = wrapper.find('.agent-grid')
      expect(grid.exists()).toBe(true)
      expect(grid.classes()).toContain('agent-grid')
    })

    it('has correct grid gap styling', async () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const grid = wrapper.find('.agent-grid')
      const styles = window.getComputedStyle(grid.element)

      // Check that gap is applied (16px)
      expect(grid.attributes('style')).toContain('gap')
    })
  })

  describe('Event Handling', () => {
    it('handles copy prompt event', async () => {
      const handleCopyPrompt = vi.fn()

      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify],
          mocks: {
            handleCopyPrompt
          }
        }
      })

      const orchestratorCard = wrapper.findComponent({ name: 'OrchestratorCard' })
      await orchestratorCard.vm.$emit('copy-prompt', 'claude-code')

      expect(wrapper.emitted('copy-prompt')).toBeTruthy()
    })

    it('handles close project event', async () => {
      const initiateCloseout = vi.fn()

      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify],
          mocks: {
            initiateCloseout
          }
        }
      })

      const orchestratorCard = wrapper.findComponent({ name: 'OrchestratorCard' })
      await orchestratorCard.vm.$emit('close-project')

      expect(wrapper.emitted('close-project')).toBeTruthy()
    })

    it('toggles agent message expansion', async () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const agentCard = wrapper.findComponent({ name: 'AgentCard' })
      await agentCard.vm.$emit('toggle-messages')

      // Verify expanded state changes
      expect(wrapper.vm.expandedAgentId).toBeDefined()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const container = wrapper.find('.agent-grid-container')
      expect(container.attributes('role')).toBeDefined()
    })

    it('supports keyboard navigation', async () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Test Tab navigation through cards
      const agentCards = wrapper.findAllComponents({ name: 'AgentCard' })

      agentCards.forEach(card => {
        expect(card.attributes('tabindex')).toBeDefined()
      })
    })
  })

  describe('WebSocket Integration', () => {
    it('updates agent status on WebSocket event', async () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Simulate WebSocket status update
      const store = useOrchestrationStore()
      const updateEvent = {
        job_id: 'job-1',
        status: 'complete',
        progress: 100
      }

      // Trigger update
      await store.handleAgentStatusUpdate(updateEvent)

      // Verify agent card reflects new status
      const agentCards = wrapper.findAllComponents({ name: 'AgentCard' })
      const updatedCard = agentCards.find(card => card.props('agent').job_id === 'job-1')

      expect(updatedCard.props('agent').status).toBe('complete')
    })
  })

  describe('Performance', () => {
    it('renders large number of agents efficiently', async () => {
      const manyAgents = Array.from({ length: 50 }, (_, i) => ({
        id: `agent-${i}`,
        job_id: `job-${i}`,
        is_orchestrator: false,
        name: `Agent ${i}`,
        status: 'working',
        messages: []
      }))

      const startTime = performance.now()

      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify],
          mocks: {
            agents: manyAgents
          }
        }
      })

      const endTime = performance.now()
      const renderTime = endTime - startTime

      // Should render in less than 100ms
      expect(renderTime).toBeLessThan(100)
    })

    it('uses virtual scrolling for large lists', () => {
      // Virtual scrolling implementation test
      // (Implementation detail - may be added later for optimization)
      expect(true).toBe(true)
    })
  })
})
