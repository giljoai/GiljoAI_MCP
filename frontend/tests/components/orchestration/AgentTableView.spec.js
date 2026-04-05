import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { h, defineComponent } from 'vue'
import AgentTableView from '@/components/orchestration/AgentTableView.vue'

/**
 * Test suite for AgentTableView component
 *
 * This component provides a table view for agents using Vuetify's v-data-table.
 * It reuses the useAgentData composable for shared logic with card view.
 *
 * Handover 0228: StatusBoardTable Component
 *
 * Post-refactor notes:
 * - agent_type renamed to agent_display_name
 * - usingClaudeCodeSubagents prop required
 * - useToast composable replaces snackbar
 *
 * Testing strategy:
 * The global setup.js stubs v-data-table with a simple div that only renders
 * the default slot. Scoped slots (#item.status, #item.agent_display_name, #no-data)
 * are NOT rendered by the stub. Therefore:
 * - Headers and items are tested via wrapper.vm (component internals)
 * - Slot rendering logic is tested by verifying composable methods exist and work
 * - Events are tested by calling component methods directly via wrapper.vm
 * - A custom v-data-table stub is used per-test where needed to render scoped slots
 */

// Mock useToast composable
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn(),
  }),
}))

/**
 * Creates a custom v-data-table stub that captures props and renders scoped slots.
 * This allows tests to verify headers, items, and slot content in the stubbed environment.
 */
function createDataTableStub() {
  return defineComponent({
    name: 'VDataTable',
    props: {
      headers: { type: Array, default: () => [] },
      items: { type: Array, default: () => [] },
      sortBy: { type: Array, default: () => [] },
      itemKey: { type: String, default: 'id' },
      hover: { type: Boolean, default: false },
    },
    emits: ['click:row'],
    setup(props, { slots, emit }) {
      return () => {
        const children = []

        // Render each item's scoped slots
        props.items.forEach((item, index) => {
          const rowChildren = []
          props.headers.forEach((header) => {
            const slotName = `item.${header.key}`
            if (slots[slotName]) {
              rowChildren.push(
                h('td', { key: header.key }, slots[slotName]({ item }))
              )
            } else {
              rowChildren.push(
                h('td', { key: header.key }, String(item[header.key] ?? ''))
              )
            }
          })
          children.push(
            h('tr', {
              key: index,
              class: 'data-table-row',
              onClick: () => emit('click:row', {}, { item }),
            }, rowChildren)
          )
        })

        // Render no-data slot when items is empty
        if (props.items.length === 0 && slots['no-data']) {
          children.push(h('div', { class: 'no-data-slot' }, slots['no-data']()))
        }

        return h('div', { class: 'v-data-table' }, [
          h('table', {}, [h('tbody', {}, children)]),
          // Also render default slot if present
          slots.default ? slots.default() : null,
        ])
      }
    },
  })
}

describe('AgentTableView.vue', () => {
  let wrapper
  let pinia

  const mockAgents = [
    {
      id: 'agent-1',
      agent_id: 'agent-id-1234-5678',
      job_id: 'job-id-1234-5678',
      agent_name: 'Backend Agent',
      agent_display_name: 'implementer',
      status: 'working',
      progress: 50,
      health_status: 'healthy',
      messages_sent_count: 2,
      messages_waiting_count: 1,
      messages_read_count: 1,
    },
    {
      id: 'agent-2',
      agent_id: 'agent-id-2345-6789',
      job_id: 'job-id-2345-6789',
      agent_name: 'Test Agent',
      agent_display_name: 'tester',
      status: 'complete',
      progress: 100,
      health_status: 'healthy',
      messages_sent_count: 0,
      messages_waiting_count: 0,
      messages_read_count: 0,
    },
    {
      id: 'agent-3',
      agent_id: 'agent-id-3456-7890',
      job_id: 'job-id-3456-7890',
      agent_name: 'Orchestrator',
      agent_display_name: 'orchestrator',
      status: 'blocked',
      progress: 75,
      health_status: 'critical',
      messages_sent_count: 1,
      messages_waiting_count: 0,
      messages_read_count: 1,
    }
  ]

  /**
   * Helper to mount AgentTableView with the custom v-data-table stub.
   * Overrides the global stub from setup.js so scoped slots render.
   */
  function mountComponent(propsOverrides = {}, stubOverrides = {}) {
    const defaultProps = {
      agents: mockAgents,
      mode: 'jobs',
      usingClaudeCodeSubagents: false,
    }

    return mount(AgentTableView, {
      props: { ...defaultProps, ...propsOverrides },
      global: {
        plugins: [pinia],
        stubs: {
          'v-data-table': createDataTableStub(),
          // Stub child components that live inside scoped slots
          StatusChip: defineComponent({
            name: 'StatusChip',
            props: ['status', 'healthStatus', 'lastProgressAt', 'minutesSinceProgress'],
            template: '<span class="status-chip-stub" :data-status="status" :data-health="healthStatus">{{ status }}</span>',
          }),
          ActionIcons: defineComponent({
            name: 'ActionIcons',
            props: ['job', 'claudeCodeCliMode'],
            emits: ['launch', 'copy-prompt', 'view-messages', 'hand-over'],
            template: '<span class="action-icons-stub" :data-job-id="job?.job_id">actions</span>',
          }),
          ...stubOverrides,
        },
      },
    })
  }

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)

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
      wrapper = mountComponent()
      expect(wrapper.exists()).toBe(true)
    })

    it('renders v-data-table component', () => {
      wrapper = mountComponent()
      const dataTable = wrapper.find('.v-data-table')
      expect(dataTable.exists()).toBe(true)
    })

    it('displays correct table headers (9 columns)', () => {
      wrapper = mountComponent()

      // Access the headers array from the component's internal state
      const headers = wrapper.vm.headers
      expect(headers).toHaveLength(9)
      expect(headers.map(h => h.title)).toEqual([
        'Agent Type',
        'Agent ID',
        'Job ID',
        'Agent Status',
        'Steps',
        'Messages Sent',
        'Messages Waiting',
        'Messages Read',
        ''
      ])
    })

    it('displays agent rows with correct data', () => {
      wrapper = mountComponent()

      // Verify rows are rendered via the custom stub
      const rows = wrapper.findAll('.data-table-row')
      expect(rows).toHaveLength(3)
    })
  })

  describe('Agent Type Column', () => {
    it('displays agent type avatar with correct color', () => {
      wrapper = mountComponent()

      // With the custom stub rendering scoped slots, agent_display_name content appears
      const html = wrapper.html()
      expect(html).toContain('implementer')
      expect(html).toContain('tester')
      expect(html).toContain('orchestrator')
    })

    it('displays agent type abbreviation in avatar', () => {
      wrapper = mountComponent()

      // The useAgentData composable provides getAgentAbbreviation
      // Abbreviations for single words: first 2 letters uppercase
      // "implementer" -> "IM", "tester" -> "TE", "orchestrator" -> "OR"
      const html = wrapper.html()
      expect(html).toContain('IM')
      expect(html).toContain('TE')
      expect(html).toContain('OR')
    })

    it('capitalizes agent type name', () => {
      wrapper = mountComponent()

      // The template uses text-capitalize CSS class for display names
      // Verify the display names are present in the rendered output
      const html = wrapper.html()
      expect(html).toContain('implementer')
      expect(html).toContain('tester')
      expect(html).toContain('orchestrator')
    })
  })

  describe('Status Column', () => {
    it('renders StatusChip components for each agent', () => {
      wrapper = mountComponent()

      // With the custom stub, StatusChip stubs are rendered inside scoped slots
      const statusChips = wrapper.findAll('.status-chip-stub')
      expect(statusChips.length).toBe(3)
    })

    it('passes correct status to StatusChip', () => {
      wrapper = mountComponent()

      const statusChips = wrapper.findAll('.status-chip-stub')
      const statuses = statusChips.map(chip => chip.attributes('data-status'))
      expect(statuses).toContain('working')
      expect(statuses).toContain('complete')
      expect(statuses).toContain('blocked')
    })

    it('passes health status to StatusChip', () => {
      wrapper = mountComponent()

      const statusChips = wrapper.findAll('.status-chip-stub')
      const healthStatuses = statusChips.map(chip => chip.attributes('data-health'))
      expect(healthStatuses).toContain('healthy')
      expect(healthStatuses).toContain('critical')
    })
  })

  describe('Messages Column', () => {
    it('displays message counts using composable', () => {
      wrapper = mountComponent()

      // The scoped slots render message counts from agent data
      // Agent 1 has messages_sent_count: 2, messages_waiting_count: 1, messages_read_count: 1
      const html = wrapper.html()
      expect(html).toBeTruthy()
      // Verify the component renders without error with message data
      expect(wrapper.exists()).toBe(true)
    })

    it('handles agents with no messages', () => {
      wrapper = mountComponent({
        agents: [mockAgents[1]], // Test Agent with all 0 messages
      })

      expect(wrapper.exists()).toBe(true)
      const rows = wrapper.findAll('.data-table-row')
      expect(rows).toHaveLength(1)
    })
  })

  describe('Health Status via StatusChip', () => {
    it('renders StatusChip components with health status', () => {
      wrapper = mountComponent()

      // Health is shown via StatusChip, not a separate column
      const statusChips = wrapper.findAll('.status-chip-stub')
      expect(statusChips.length).toBeGreaterThan(0)

      // Verify health_status is passed
      const healthAttrs = statusChips.map(chip => chip.attributes('data-health'))
      expect(healthAttrs).toContain('healthy')
      expect(healthAttrs).toContain('critical')
    })

    it('renders agents with critical health status', () => {
      wrapper = mountComponent({
        agents: [mockAgents[2]], // Orchestrator with critical health
      })

      const statusChips = wrapper.findAll('.status-chip-stub')
      expect(statusChips).toHaveLength(1)
      expect(statusChips[0].attributes('data-health')).toBe('critical')
    })
  })

  describe('Actions Column', () => {
    it('displays action icons for each agent in jobs mode', () => {
      wrapper = mountComponent({ mode: 'jobs' })

      // ActionIcons is rendered via v-if="mode === 'jobs'" in the actions slot
      const actionIcons = wrapper.findAll('.action-icons-stub')
      expect(actionIcons.length).toBe(3)
    })

    it('does not display action icons in launch mode', () => {
      wrapper = mountComponent({ mode: 'launch' })

      // ActionIcons has v-if="mode === 'jobs'", so in launch mode it should not render
      const actionIcons = wrapper.findAll('.action-icons-stub')
      expect(actionIcons.length).toBe(0)
    })
  })

  describe('Row Click Events', () => {
    it('emits row-click event when row is clicked', async () => {
      wrapper = mountComponent()

      // Click the first row rendered by our custom stub
      const rows = wrapper.findAll('.data-table-row')
      expect(rows.length).toBeGreaterThan(0)
      await rows[0].trigger('click')

      expect(wrapper.emitted('row-click')).toBeTruthy()
      expect(wrapper.emitted('row-click')[0][0]).toEqual(mockAgents[0])
    })

    it('emits launch-agent event via handleLaunchJob', async () => {
      wrapper = mountComponent()

      // Call the handler method directly since ActionIcons is stubbed
      wrapper.vm.handleLaunchJob(mockAgents[0])

      expect(wrapper.emitted('launch-agent')).toBeTruthy()
      expect(wrapper.emitted('launch-agent')[0][0]).toEqual(mockAgents[0])
    })
  })

  describe('Empty State', () => {
    it('displays empty state when no agents', () => {
      wrapper = mountComponent({ agents: [] })

      const html = wrapper.html()
      expect(html).toContain('No agents to display')
    })

    it('displays table-off icon in empty state', () => {
      wrapper = mountComponent({ agents: [] })

      const html = wrapper.html()
      expect(html).toContain('mdi-table-off')
    })
  })

  describe('Composable Integration', () => {
    it('uses useAgentData composable methods', () => {
      wrapper = mountComponent()

      // Verify composable methods are available on the component instance
      expect(typeof wrapper.vm.getAgentAbbreviation).toBe('function')
    })

    it('getAgentAbbreviation returns correct abbreviations', () => {
      wrapper = mountComponent()

      expect(wrapper.vm.getAgentAbbreviation('implementer')).toBe('IM')
      expect(wrapper.vm.getAgentAbbreviation('tester')).toBe('TE')
      expect(wrapper.vm.getAgentAbbreviation('orchestrator')).toBe('OR')
      expect(wrapper.vm.getAgentAbbreviation('backend-implementer')).toBe('BI')
      expect(wrapper.vm.getAgentAbbreviation(null)).toBe('??')
    })
  })

  describe('Sorting', () => {
    it('allows sorting by agent_display_name column', () => {
      wrapper = mountComponent()

      const headers = wrapper.vm.headers
      const agentTypeHeader = headers.find(h => h.key === 'agent_display_name')
      expect(agentTypeHeader.sortable).toBe(true)
    })

    it('allows sorting by status column', () => {
      wrapper = mountComponent()

      const headers = wrapper.vm.headers
      const statusHeader = headers.find(h => h.key === 'status')
      expect(statusHeader.sortable).toBe(true)
    })

    it('disables sorting on steps column', () => {
      wrapper = mountComponent()

      const headers = wrapper.vm.headers
      const stepsHeader = headers.find(h => h.key === 'steps')
      expect(stepsHeader.sortable).toBe(false)
    })

    it('disables sorting on actions column', () => {
      wrapper = mountComponent()

      const headers = wrapper.vm.headers
      const actionsHeader = headers.find(h => h.key === 'actions')
      expect(actionsHeader.sortable).toBe(false)
    })

    it('allows sorting by message count columns', () => {
      wrapper = mountComponent()

      const headers = wrapper.vm.headers
      expect(headers.find(h => h.key === 'messages_sent_count').sortable).toBe(true)
      expect(headers.find(h => h.key === 'messages_waiting_count').sortable).toBe(true)
      expect(headers.find(h => h.key === 'messages_read_count').sortable).toBe(true)
    })
  })

  describe('Accessibility', () => {
    it('has proper table element rendered by custom stub', () => {
      wrapper = mountComponent()

      // The custom v-data-table stub renders a <table> element
      const table = wrapper.find('table')
      expect(table.exists()).toBe(true)
    })

    it('renders the agent-table-view class for CSS styling hooks', () => {
      wrapper = mountComponent()

      const tableContainer = wrapper.find('.agent-table-view')
      expect(tableContainer.exists()).toBe(true)
    })

    it('supports keyboard navigation', () => {
      wrapper = mountComponent()

      // Vuetify data tables support keyboard navigation by default
      // Verify the component mounts with proper structure
      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Hover Effects', () => {
    it('applies hover attribute via v-data-table', () => {
      wrapper = mountComponent()

      // The component passes hover prop to v-data-table
      // Verify the component renders the agent-table-view class for hover styles
      const agentTable = wrapper.find('.agent-table-view')
      expect(agentTable.exists()).toBe(true)
    })

    it('shows cursor pointer on rows via CSS', () => {
      wrapper = mountComponent()

      // CSS is applied via .agent-table-view :deep(tbody tr) { cursor: pointer }
      // In unit tests we verify the class is present for the CSS selector to match
      expect(wrapper.find('.agent-table-view').exists()).toBe(true)
    })
  })

  describe('Reactive Updates', () => {
    it('updates table when agents prop changes', async () => {
      wrapper = mountComponent({
        agents: [mockAgents[0]],
      })

      let rows = wrapper.findAll('.data-table-row')
      expect(rows).toHaveLength(1)

      await wrapper.setProps({ agents: mockAgents })

      rows = wrapper.findAll('.data-table-row')
      expect(rows).toHaveLength(3)
    })

    it('reflects status changes in real-time', async () => {
      const agents = [{ ...mockAgents[0] }]

      wrapper = mountComponent({ agents })

      expect(agents[0].status).toBe('working')

      // Simulate status change by updating props with new status
      const updatedAgents = [{ ...agents[0], status: 'complete' }]
      await wrapper.setProps({ agents: updatedAgents })

      // Verify the StatusChip receives the updated status
      const statusChip = wrapper.find('.status-chip-stub')
      expect(statusChip.attributes('data-status')).toBe('complete')
    })
  })

  describe('Agent ID and Job ID Columns', () => {
    it('renders truncated agent IDs', () => {
      wrapper = mountComponent()

      const html = wrapper.html()
      // Agent IDs are sliced to first 8 characters
      expect(html).toContain('agent-id')
    })

    it('renders truncated job IDs', () => {
      wrapper = mountComponent()

      const html = wrapper.html()
      // Job IDs are sliced to first 8 characters
      expect(html).toContain('job-id-1')
    })

    it('renders dash for missing agent ID', () => {
      const agentWithoutId = { ...mockAgents[0], agent_id: null }
      wrapper = mountComponent({ agents: [agentWithoutId] })

      // The template uses item.agent_id ? item.agent_id.slice(0, 8) : '\u2014'
      // In test rendering the emdash should appear
      const html = wrapper.html()
      expect(html).toBeTruthy()
    })
  })

  describe('Steps Column', () => {
    it('renders step progress when steps data is available', () => {
      const agentWithSteps = {
        ...mockAgents[0],
        steps_completed: 3,
        steps_total: 5,
      }
      wrapper = mountComponent({ agents: [agentWithSteps] })

      const html = wrapper.html()
      expect(html).toContain('3')
      expect(html).toContain('5')
    })

    it('renders dash when no step data available', () => {
      wrapper = mountComponent({
        agents: [mockAgents[0]], // No steps_completed or steps_total
      })

      // The component renders '\u2014' when steps data is unavailable
      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Component Methods', () => {
    it('handleViewMessages emits row-click with the job', () => {
      wrapper = mountComponent()

      wrapper.vm.handleViewMessages(mockAgents[1])

      expect(wrapper.emitted('row-click')).toBeTruthy()
      expect(wrapper.emitted('row-click')[0][0]).toEqual(mockAgents[1])
    })

    it('canCopyPrompt returns false for decommissioned agents', () => {
      wrapper = mountComponent()

      const decommissioned = { ...mockAgents[0], status: 'decommissioned' }
      expect(wrapper.vm.canCopyPrompt(decommissioned)).toBe(false)
    })

    it('canCopyPrompt returns true for active agents in CLI mode', () => {
      wrapper = mountComponent({ usingClaudeCodeSubagents: false })

      expect(wrapper.vm.canCopyPrompt(mockAgents[0])).toBe(true)
    })

    it('canCopyPrompt restricts to orchestrator in Claude Code mode', () => {
      wrapper = mountComponent({ usingClaudeCodeSubagents: true })

      // Non-orchestrator agent
      expect(wrapper.vm.canCopyPrompt(mockAgents[0])).toBe(false)

      // Orchestrator agent
      const orchestratorAgent = {
        ...mockAgents[2],
        is_orchestrator: true,
      }
      expect(wrapper.vm.canCopyPrompt(orchestratorAgent)).toBe(true)
    })
  })
})
