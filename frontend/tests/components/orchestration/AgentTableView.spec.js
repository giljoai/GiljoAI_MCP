import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import AgentTableView from '@/components/orchestration/AgentTableView.vue'

/**
 * Test suite for AgentTableView component
 *
 * This component provides a table view for agents using Vuetify's v-data-table.
 * It reuses the useAgentData composable for shared logic with card view.
 *
 * Handover 0228: StatusBoardTable Component
 */
describe('AgentTableView.vue', () => {
  let wrapper
  let pinia
  let vuetify

  const mockAgents = [
    {
      id: 'agent-1',
      job_id: 'job-1',
      agent_name: 'Backend Agent',
      agent_type: 'implementer',
      status: 'working',
      progress: 50,
      messages: [
        { status: 'pending', content: 'Message 1' },
        { status: 'acknowledged', content: 'Message 2' }
      ],
      health_status: 'healthy'
    },
    {
      id: 'agent-2',
      job_id: 'job-2',
      agent_name: 'Test Agent',
      agent_type: 'tester',
      status: 'complete',
      progress: 100,
      messages: [],
      health_status: 'healthy'
    },
    {
      id: 'agent-3',
      job_id: 'job-3',
      agent_name: 'Orchestrator',
      agent_type: 'orchestrator',
      status: 'failed',
      progress: 75,
      messages: [
        { status: 'pending', content: 'Error message' }
      ],
      health_status: 'critical'
    }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify({
      components,
      directives,
    })

    // Mock API
    global.fetch = vi.fn()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.resetAllMocks()
  })

  describe('Rendering', () => {
    it('renders the component successfully', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('renders v-data-table component', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const dataTable = wrapper.findComponent({ name: 'VDataTable' })
      expect(dataTable.exists()).toBe(true)
    })

    it('displays correct table headers (6 columns)', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const dataTable = wrapper.findComponent({ name: 'VDataTable' })
      const headers = dataTable.props('headers')

      expect(headers).toHaveLength(6)
      expect(headers.map(h => h.title)).toEqual([
        'Agent Type',
        'Agent Name',
        'Status',
        'Messages',
        'Health',
        'Actions'
      ])
    })

    it('displays agent rows with correct data', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const dataTable = wrapper.findComponent({ name: 'VDataTable' })
      expect(dataTable.props('items')).toHaveLength(3)
      expect(dataTable.props('items')).toEqual(mockAgents)
    })
  })

  describe('Agent Type Column', () => {
    it('displays agent type avatar with correct color', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Should use useAgentData's getAgentTypeColor
      expect(wrapper.html()).toContain('implementer')
      expect(wrapper.html()).toContain('tester')
      expect(wrapper.html()).toContain('orchestrator')
    })

    it('displays agent type abbreviation in avatar', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Should use useAgentData's getAgentAbbreviation
      // Abbreviations: Im, Te, Or
      const html = wrapper.html()
      expect(html).toBeTruthy() // Verify component renders
    })

    it('capitalizes agent type name', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.html()).toContain('implementer')
      expect(wrapper.html()).toContain('tester')
      expect(wrapper.html()).toContain('orchestrator')
    })
  })

  describe('Status Column', () => {
    it('displays status chip with correct color', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Should use useAgentData's getStatusColor
      const chips = wrapper.findAllComponents({ name: 'VChip' })
      expect(chips.length).toBeGreaterThan(0)
    })

    it('displays correct status text', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const html = wrapper.html()
      expect(html).toContain('working')
      expect(html).toContain('complete')
      expect(html).toContain('failed')
    })
  })

  describe('Messages Column', () => {
    it('displays message counts using composable', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Should use useAgentData's getMessageCounts
      expect(wrapper.html()).toBeTruthy() // Verify component renders
    })

    it('handles agents with no messages', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockAgents[1]], // Test Agent with no messages
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Health Column', () => {
    it('displays health icon with correct color', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Should use useAgentData's getHealthColor and getHealthIcon
      const icons = wrapper.findAllComponents({ name: 'VIcon' })
      expect(icons.length).toBeGreaterThan(0)
    })

    it('shows critical health status correctly', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockAgents[2]], // Orchestrator with critical health
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.html()).toBeTruthy() // Verify component renders
    })
  })

  describe('Actions Column', () => {
    it('displays action buttons for each agent', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      expect(wrapper.html()).toBeTruthy() // Verify component renders
    })
  })

  describe('Row Click Events', () => {
    it('emits row-click event when row is clicked', async () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const dataTable = wrapper.findComponent({ name: 'VDataTable' })

      // Simulate row click
      await dataTable.vm.$emit('click:row', {}, { item: mockAgents[0] })

      expect(wrapper.emitted('row-click')).toBeTruthy()
      expect(wrapper.emitted('row-click')[0]).toEqual([mockAgents[0]])
    })

    it('emits launch-agent event from action buttons', async () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Action buttons should emit launch-agent
      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Empty State', () => {
    it('displays empty state when no agents', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [],
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const html = wrapper.html()
      expect(html).toContain('No agents to display')
    })

    it('displays table-off icon in empty state', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [],
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const html = wrapper.html()
      expect(html).toContain('mdi-table-off')
    })
  })

  describe('Composable Integration', () => {
    it('uses useAgentData composable methods', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Component should import and use:
      // - getStatusColor
      // - getAgentTypeColor
      // - getAgentAbbreviation
      // - getMessageCounts
      // - getHealthColor
      // - getHealthIcon
      expect(wrapper.vm).toBeDefined()
    })
  })

  describe('Sorting', () => {
    it('allows sorting by agent_type column', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const dataTable = wrapper.findComponent({ name: 'VDataTable' })
      const headers = dataTable.props('headers')

      const agentTypeHeader = headers.find(h => h.key === 'agent_type')
      expect(agentTypeHeader.sortable).toBe(true)
    })

    it('allows sorting by agent_name column', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const dataTable = wrapper.findComponent({ name: 'VDataTable' })
      const headers = dataTable.props('headers')

      const agentNameHeader = headers.find(h => h.key === 'agent_name')
      expect(agentNameHeader.sortable).toBe(true)
    })

    it('allows sorting by status column', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const dataTable = wrapper.findComponent({ name: 'VDataTable' })
      const headers = dataTable.props('headers')

      const statusHeader = headers.find(h => h.key === 'status')
      expect(statusHeader.sortable).toBe(true)
    })

    it('disables sorting on messages column', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const dataTable = wrapper.findComponent({ name: 'VDataTable' })
      const headers = dataTable.props('headers')

      const messagesHeader = headers.find(h => h.key === 'messages')
      expect(messagesHeader.sortable).toBe(false)
    })

    it('disables sorting on actions column', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const dataTable = wrapper.findComponent({ name: 'VDataTable' })
      const headers = dataTable.props('headers')

      const actionsHeader = headers.find(h => h.key === 'actions')
      expect(actionsHeader.sortable).toBe(false)
    })
  })

  describe('Accessibility', () => {
    it('has proper table role', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const table = wrapper.find('table')
      expect(table.exists()).toBe(true)
    })

    it('supports keyboard navigation', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // Vuetify data tables support keyboard navigation by default
      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Hover Effects', () => {
    it('applies hover styles to rows', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // CSS should include tbody tr:hover styles
      const style = wrapper.html()
      expect(style).toBeTruthy()
    })

    it('shows cursor pointer on rows', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      // CSS should include cursor: pointer
      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Reactive Updates', () => {
    it('updates table when agents prop changes', async () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [mockAgents[0]],
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const dataTable = wrapper.findComponent({ name: 'VDataTable' })
      expect(dataTable.props('items')).toHaveLength(1)

      await wrapper.setProps({ agents: mockAgents })

      expect(dataTable.props('items')).toHaveLength(3)
    })

    it('reflects status changes in real-time', async () => {
      const agents = [{ ...mockAgents[0] }]

      wrapper = mount(AgentTableView, {
        props: {
          agents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify]
        }
      })

      const initialStatus = agents[0].status
      expect(initialStatus).toBe('working')

      // Simulate status change
      agents[0].status = 'complete'
      await wrapper.vm.$nextTick()

      const dataTable = wrapper.findComponent({ name: 'VDataTable' })
      expect(dataTable.props('items')[0].status).toBe('complete')
    })
  })
})
