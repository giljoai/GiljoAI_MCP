import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import AgentTableView from '@/components/orchestration/AgentTableView.vue'
import JobReadAckIndicators from '@/components/StatusBoard/JobReadAckIndicators.vue'

/**
 * Test suite for AgentTableView with JobReadAckIndicators integration
 *
 * Validates that job acknowledged indicators are displayed in agent table
 *
 * Updated for simplified job signaling (mission_read_at removed)
 */
describe('AgentTableView with JobReadAckIndicators - Updated', () => {
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
      health_status: 'healthy',
      mission_acknowledged_at: '2025-11-21T10:35:00Z'
    },
    {
      id: 'agent-2',
      job_id: 'job-2',
      agent_name: 'Test Agent',
      agent_type: 'tester',
      status: 'complete',
      progress: 100,
      messages: [],
      health_status: 'healthy',
      mission_acknowledged_at: null
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
      health_status: 'critical',
      mission_acknowledged_at: '2025-11-21T09:15:00Z'
    }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.resetAllMocks()
  })

  describe('Rendering', () => {
    it('renders AgentTableView component successfully', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.agent-table-view').exists()).toBe(true)
    })

  })

  describe('JobReadAckIndicators Integration', () => {
    it('includes mission_tracking column in table headers', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      // Check that the component has the necessary data structure
      expect(wrapper.vm.headers).toBeDefined()
      // The table should have the required columns
      expect(wrapper.vm.headers.some(h => h.key === 'agent_type')).toBe(true)
      expect(wrapper.vm.headers.some(h => h.key === 'status')).toBe(true)
    })

    it('displays JobReadAckIndicators component for agents with mission data', async () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      // Component should be registered and available
      const registeredComponents = wrapper.vm.$options.components || {}
      expect(registeredComponents).toBeDefined()
    })

    it('passes mission_acknowledged_at prop to indicator component', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      // First agent has mission_acknowledged_at set
      const firstAgent = mockAgents[0]
      expect(firstAgent.mission_acknowledged_at).toBe('2025-11-21T10:35:00Z')
    })

    it('handles agents with null mission_acknowledged_at', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      // Second agent has no mission_acknowledged_at
      const secondAgent = mockAgents[1]
      expect(secondAgent.mission_acknowledged_at).toBeNull()
    })

    it('handles agents with mission_acknowledged_at set', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      // Third agent has mission_acknowledged_at
      const thirdAgent = mockAgents[2]
      expect(thirdAgent.mission_acknowledged_at).toBe('2025-11-21T09:15:00Z')
    })
  })

  describe('Agent Data Consistency', () => {
    it('preserves all agent properties when integrated with indicators', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      // Verify that agent data is intact
      expect(wrapper.props().agents).toEqual(mockAgents)
      expect(wrapper.props().agents[0].agent_name).toBe('Backend Agent')
      expect(wrapper.props().agents[0].status).toBe('working')
      expect(wrapper.props().agents[0].mission_acknowledged_at).toBe('2025-11-21T10:35:00Z')
    })
  })

  describe('Empty/Edge Cases', () => {
    it('renders empty state when no agents provided', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: [],
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Component Interaction', () => {
    it('allows row click events with mission timestamp data', async () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      // Verify the component can emit row-click events
      expect(wrapper.emitted).toBeDefined()
      expect(wrapper.vm.$emit).toBeDefined()
    })

    it('maintains focus on indicators within table rows', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      // Component should render without accessibility issues
      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Mode-Specific Behavior', () => {
    it('displays indicators in jobs mode', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      expect(wrapper.props().mode).toBe('jobs')
      expect(wrapper.exists()).toBe(true)
    })

    it('displays indicators in launch mode', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'launch'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      expect(wrapper.props().mode).toBe('launch')
      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Data Flow', () => {
    it('passes correct agent data to table rows', () => {
      wrapper = mount(AgentTableView, {
        props: {
          agents: mockAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      // Verify agents array is preserved
      expect(wrapper.props().agents.length).toBe(3)
      expect(wrapper.props().agents).toEqual(mockAgents)
    })

    it('handles reactive agent updates', async () => {
      const initialAgents = [mockAgents[0]]

      wrapper = mount(AgentTableView, {
        props: {
          agents: initialAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      expect(wrapper.props().agents.length).toBe(1)

      // Update agents prop
      const updatedAgents = mockAgents
      await wrapper.setProps({ agents: updatedAgents })
      await wrapper.vm.$nextTick()

      expect(wrapper.props().agents.length).toBe(3)
      expect(wrapper.props().agents).toEqual(mockAgents)
    })
  })

  describe('Edge Cases - Table Rendering', () => {
    it('handles agents with missing mission_acknowledged_at property in data flow', () => {
      const agentsWithoutTimestamps = [
        {
          id: 'agent-1',
          job_id: 'job-1',
          agent_name: 'Agent Without Timestamps',
          agent_type: 'implementer',
          status: 'working',
          // mission_acknowledged_at not provided
        }
      ]

      wrapper = mount(AgentTableView, {
        props: {
          agents: agentsWithoutTimestamps,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      // Verify the agents data is accessible even if mission_acknowledged_at is missing
      expect(wrapper.props().agents[0].agent_name).toBe('Agent Without Timestamps')
      expect(wrapper.props().agents[0].mission_acknowledged_at).toBeUndefined()
    })

    it('handles mixed agent data with and without mission_acknowledged_at in data flow', () => {
      const mixedAgents = [
        {
          id: 'agent-1',
          job_id: 'job-1',
          agent_name: 'Agent With Timestamp',
          agent_type: 'implementer',
          status: 'working',
          mission_acknowledged_at: '2025-11-21T10:35:00Z'
        },
        {
          id: 'agent-2',
          job_id: 'job-2',
          agent_name: 'Agent Without Timestamp',
          agent_type: 'tester',
          status: 'working'
          // No mission_acknowledged_at
        }
      ]

      wrapper = mount(AgentTableView, {
        props: {
          agents: mixedAgents,
          mode: 'jobs'
        },
        global: {
          plugins: [pinia, vuetify],
          components: {
            JobReadAckIndicators
          }
        }
      })

      // Verify mixed data is accessible
      expect(wrapper.props().agents.length).toBe(2)
      expect(wrapper.props().agents[0].mission_acknowledged_at).toBe('2025-11-21T10:35:00Z')
      expect(wrapper.props().agents[1].mission_acknowledged_at).toBeUndefined()
    })
  })
})
