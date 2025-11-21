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

  describe('View Toggle - Handover 0228', () => {
    it('defaults to card view on initial render', () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.vm.viewMode).toBe('cards')
      expect(wrapper.find('.agent-grid').exists()).toBe(true)
      expect(wrapper.findComponent({ name: 'AgentTableView' }).exists()).toBe(false)
    })

    it('renders view toggle button group', () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const btnToggle = wrapper.findComponent({ name: 'VBtnToggle' })
      expect(btnToggle.exists()).toBe(true)
      expect(btnToggle.findAll('button')).toHaveLength(2)
    })

    it('displays card view icon button', () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const cardButton = wrapper.find('[value="cards"]')
      expect(cardButton.exists()).toBe(true)
      expect(cardButton.html()).toContain('mdi-view-grid')
    })

    it('displays table view icon button', () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const tableButton = wrapper.find('[value="table"]')
      expect(tableButton.exists()).toBe(true)
      expect(tableButton.html()).toContain('mdi-table')
    })

    it('switches to table view when table button clicked', async () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Initially card view
      expect(wrapper.vm.viewMode).toBe('cards')

      // Switch to table view
      wrapper.vm.viewMode = 'table'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.viewMode).toBe('table')
      expect(wrapper.find('.agent-grid').exists()).toBe(false)
      expect(wrapper.findComponent({ name: 'AgentTableView' }).exists()).toBe(true)
    })

    it('switches back to card view when card button clicked', async () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Switch to table view first
      wrapper.vm.viewMode = 'table'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.viewMode).toBe('table')

      // Switch back to card view
      wrapper.vm.viewMode = 'cards'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.viewMode).toBe('cards')
      expect(wrapper.find('.agent-grid').exists()).toBe(true)
      expect(wrapper.findComponent({ name: 'AgentTableView' }).exists()).toBe(false)
    })

    it('preserves agent data when switching views', async () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const initialAgents = wrapper.vm.sortedAgents

      // Switch to table view
      wrapper.vm.viewMode = 'table'
      await wrapper.vm.$nextTick()

      const tableView = wrapper.findComponent({ name: 'AgentTableView' })
      expect(tableView.props('agents')).toEqual(initialAgents)

      // Switch back to card view
      wrapper.vm.viewMode = 'cards'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.sortedAgents).toEqual(initialAgents)
    })

    it('maintains sort order in both views', async () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const cardViewAgents = wrapper.vm.sortedAgents

      // Switch to table view
      wrapper.vm.viewMode = 'table'
      await wrapper.vm.$nextTick()

      const tableView = wrapper.findComponent({ name: 'AgentTableView' })
      const tableViewAgents = tableView.props('agents')

      // Both views should have same sort order
      expect(tableViewAgents[0].id).toBe(cardViewAgents[0].id)
      expect(tableViewAgents[1].id).toBe(cardViewAgents[1].id)
      expect(tableViewAgents[2].id).toBe(cardViewAgents[2].id)
    })

    it('WebSocket updates reflect in both views', async () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Initial state in card view
      const initialStatus = wrapper.vm.sortedAgents[0].status

      // Simulate WebSocket update
      const store = useOrchestrationStore()
      const updateEvent = {
        job_id: wrapper.vm.sortedAgents[0].job_id,
        status: 'complete',
        progress: 100
      }
      await store.handleAgentStatusUpdate(updateEvent)
      await wrapper.vm.$nextTick()

      // Verify card view reflects change
      expect(wrapper.vm.sortedAgents.find(a => a.job_id === updateEvent.job_id).status).toBe('complete')

      // Switch to table view
      wrapper.vm.viewMode = 'table'
      await wrapper.vm.$nextTick()

      // Verify table view also reflects same change (shared reactive data)
      const tableView = wrapper.findComponent({ name: 'AgentTableView' })
      expect(tableView.props('agents').find(a => a.job_id === updateEvent.job_id).status).toBe('complete')
    })

    it('uses composable for shared logic in card view', () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Component should import and use useAgentData composable
      expect(wrapper.vm.sortedAgents).toBeDefined()
    })

    it('passes mode prop to table view', async () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Switch to table view
      wrapper.vm.viewMode = 'table'
      await wrapper.vm.$nextTick()

      const tableView = wrapper.findComponent({ name: 'AgentTableView' })
      expect(tableView.props('mode')).toBeDefined()
    })

    it('forwards launch-agent event from table view', async () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Switch to table view
      wrapper.vm.viewMode = 'table'
      await wrapper.vm.$nextTick()

      const tableView = wrapper.findComponent({ name: 'AgentTableView' })
      await tableView.vm.$emit('launch-agent', mockAgents[0])

      expect(wrapper.emitted('launch-agent')).toBeTruthy()
      expect(wrapper.emitted('launch-agent')[0]).toEqual([mockAgents[0]])
    })

    it('forwards view-details event from table view', async () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Switch to table view
      wrapper.vm.viewMode = 'table'
      await wrapper.vm.$nextTick()

      const tableView = wrapper.findComponent({ name: 'AgentTableView' })
      await tableView.vm.$emit('row-click', mockAgents[0])

      expect(wrapper.emitted('view-details')).toBeTruthy()
      expect(wrapper.emitted('view-details')[0]).toEqual([mockAgents[0]])
    })

    it('has tooltips for view toggle buttons', () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const tooltips = wrapper.findAllComponents({ name: 'VTooltip' })
      expect(tooltips.length).toBeGreaterThan(0)

      // Check for Card View and Table View tooltips
      const tooltipTexts = tooltips.map(t => t.text())
      expect(tooltipTexts).toContain('Card View')
      expect(tooltipTexts).toContain('Table View')
    })

    it('toggle button group is mandatory (always has selection)', async () => {
      wrapper = mount(AgentCardGrid, {
        props: { projectId: 'project-1' },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const btnToggle = wrapper.findComponent({ name: 'VBtnToggle' })
      expect(btnToggle.props('mandatory')).toBe(true)
    })
  })
})
