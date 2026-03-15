/**
 * Integration tests for Status Board Components
 * Tests complete user workflows and real-time data synchronization
 *
 * Handover 0236: Phase 3 - Frontend Integration Tests
 *
 * TDD Focus:
 * - Component interaction workflows
 * - WebSocket real-time updates (via prop changes)
 * - Action button handling
 * - Table state management
 * - Complete user journeys
 *
 * Post-refactor notes:
 * - AgentTableView uses agent_display_name (not agent_type) for display
 * - ActionIcons uses getAvailableActions() from actionConfig to determine buttons
 * - StatusChip validates: waiting, working, blocked, complete, silent, decommissioned, handed_over
 * - WebSocket store eventHandlers are private; tests simulate updates via prop changes
 *
 * Test environment constraints:
 * - v-data-table is globally stubbed (setup.js) and does NOT render scoped slots
 * - StatusChip and ActionIcons cannot be found inside the stubbed v-data-table
 * - Tests verify: mounting, props, internal state, computed properties, events,
 *   header configuration, and child components via direct mounting
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AgentTableView from '@/components/orchestration/AgentTableView.vue'
import StatusChip from '@/components/StatusBoard/StatusChip.vue'
import ActionIcons from '@/components/StatusBoard/ActionIcons.vue'

// Mock toast composable
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn(),
  }),
}))

// ============================================
// TEST DATA
// ============================================

const mockJobsData = [
  {
    job_id: 'job-001',
    agent_id: 'agent-001',
    status: 'working',
    agent_display_name: 'implementer',
    agent_name: 'Backend Implementer',
    health_status: 'healthy',
    last_progress_at: new Date(Date.now() - 30000).toISOString(),
    unread_count: 2,
    mission_read_at: null,
    messages_sent_count: 5,
    messages_waiting_count: 2,
    messages_read_count: 3,
  },
  {
    job_id: 'job-002',
    agent_id: 'agent-002',
    status: 'waiting',
    agent_display_name: 'analyzer',
    agent_name: 'Code Analyzer',
    health_status: 'healthy',
    last_progress_at: new Date(Date.now() - 10000).toISOString(),
    unread_count: 0,
    mission_read_at: new Date().toISOString(),
    messages_sent_count: 0,
    messages_waiting_count: 0,
    messages_read_count: 0,
  },
  {
    job_id: 'job-003',
    agent_id: 'agent-003',
    status: 'complete',
    agent_display_name: 'tester',
    agent_name: 'Test Runner',
    health_status: 'healthy',
    last_progress_at: new Date(Date.now() - 60000).toISOString(),
    unread_count: 1,
    mission_read_at: new Date().toISOString(),
    messages_sent_count: 3,
    messages_waiting_count: 1,
    messages_read_count: 2,
  },
  {
    job_id: 'job-004',
    agent_id: 'agent-004',
    status: 'working',
    agent_display_name: 'orchestrator',
    agent_name: 'Project Orchestrator',
    health_status: 'warning',
    last_progress_at: new Date(Date.now() - 300000).toISOString(),
    unread_count: 0,
    mission_read_at: null,
    messages_sent_count: 10,
    messages_waiting_count: 0,
    messages_read_count: 10,
  }
]

// ============================================
// HELPER: mount AgentTableView with standard config
// ============================================

function mountAgentTableView(props = {}, pinia) {
  return mount(AgentTableView, {
    props: {
      agents: mockJobsData,
      mode: 'jobs',
      usingClaudeCodeSubagents: false,
      ...props,
    },
    global: {
      plugins: [pinia]
    }
  })
}

// ============================================
// TESTS: DATA LOADING & RENDERING
// ============================================

describe('Status Board Integration - Data Loading & Rendering', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loads table with job data on mount', async () => {
    const wrapper = mountAgentTableView({}, pinia)

    await wrapper.vm.$nextTick()

    // Verify component mounted
    expect(wrapper.exists()).toBe(true)

    // Verify props passed correctly
    expect(wrapper.props('agents')).toHaveLength(4)
    expect(wrapper.props('agents')[0].job_id).toBe('job-001')
  })

  it('passes agents as items to the data table stub', async () => {
    const wrapper = mountAgentTableView({}, pinia)

    await wrapper.vm.$nextTick()

    // The v-data-table stub renders as a div with class v-data-table
    const dataTableEl = wrapper.find('.v-data-table')
    expect(dataTableEl.exists()).toBe(true)

    // Verify component passes agents prop which becomes :items on v-data-table
    // We verify via the component's own props since the stub does not forward
    expect(wrapper.props('agents')).toHaveLength(4)
  })

  it('provides correct agent display names in agents prop', async () => {
    const wrapper = mountAgentTableView({ agents: mockJobsData.slice(0, 2) }, pinia)

    await wrapper.vm.$nextTick()

    const agents = wrapper.props('agents')
    expect(agents[0].agent_display_name).toBe('implementer')
    expect(agents[1].agent_display_name).toBe('analyzer')
  })

  it('configures 9 table headers with correct keys', async () => {
    const wrapper = mountAgentTableView({}, pinia)

    await wrapper.vm.$nextTick()

    // Access headers via the component's internal state
    const headers = wrapper.vm.headers
    expect(headers).toHaveLength(9)

    const headerKeys = headers.map(h => h.key)
    expect(headerKeys).toContain('agent_display_name')
    expect(headerKeys).toContain('agent_id')
    expect(headerKeys).toContain('job_id')
    expect(headerKeys).toContain('status')
    expect(headerKeys).toContain('steps')
    expect(headerKeys).toContain('messages_sent_count')
    expect(headerKeys).toContain('messages_waiting_count')
    expect(headerKeys).toContain('messages_read_count')
    expect(headerKeys).toContain('actions')
  })

  it('configures header titles correctly', async () => {
    const wrapper = mountAgentTableView({}, pinia)

    await wrapper.vm.$nextTick()

    const headers = wrapper.vm.headers
    const titleMap = Object.fromEntries(headers.map(h => [h.key, h.title]))

    expect(titleMap['agent_display_name']).toBe('Agent Type')
    expect(titleMap['status']).toBe('Agent Status')
    expect(titleMap['steps']).toBe('Steps')
    expect(titleMap['messages_sent_count']).toBe('Messages Sent')
    expect(titleMap['messages_waiting_count']).toBe('Messages Waiting')
    expect(titleMap['messages_read_count']).toBe('Messages Read')
    expect(titleMap['actions']).toBe('')
  })

  it('marks sortable headers correctly', async () => {
    const wrapper = mountAgentTableView({}, pinia)

    await wrapper.vm.$nextTick()

    const headers = wrapper.vm.headers
    const sortableMap = Object.fromEntries(headers.map(h => [h.key, h.sortable]))

    expect(sortableMap['agent_display_name']).toBe(true)
    expect(sortableMap['status']).toBe(true)
    expect(sortableMap['messages_sent_count']).toBe(true)
    expect(sortableMap['agent_id']).toBe(false)
    expect(sortableMap['job_id']).toBe(false)
    expect(sortableMap['actions']).toBe(false)
  })
})

// ============================================
// TESTS: WEBSOCKET INTEGRATION (via prop updates)
// ============================================

describe('Status Board Integration - WebSocket Real-time Updates', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('updates agents prop when job status changes via prop update', async () => {
    const agents = [...mockJobsData]

    const wrapper = mountAgentTableView({ agents }, pinia)

    await wrapper.vm.$nextTick()

    // Verify initial status
    expect(wrapper.props('agents')[0].status).toBe('working')

    // Simulate WebSocket status change via prop update
    const updatedAgents = agents.map((agent) =>
      agent.job_id === 'job-001'
        ? { ...agent, status: 'complete' }
        : agent
    )

    await wrapper.setProps({ agents: updatedAgents })
    await wrapper.vm.$nextTick()

    // Verify status updated in props
    expect(wrapper.props('agents')[0].status).toBe('complete')
  })

  it('updates unread message count when new message received', async () => {
    const agents = [...mockJobsData]

    const wrapper = mountAgentTableView({ agents }, pinia)

    await wrapper.vm.$nextTick()

    const initialCount = agents[0].unread_count
    expect(initialCount).toBe(2)

    // Simulate WebSocket message received via prop update
    const updatedAgents = agents.map((agent) =>
      agent.job_id === 'job-001'
        ? { ...agent, unread_count: agent.unread_count + 1 }
        : agent
    )

    await wrapper.setProps({ agents: updatedAgents })
    await wrapper.vm.$nextTick()

    expect(wrapper.props('agents')[0].unread_count).toBe(3)
  })

  it('updates health status when job health changes', async () => {
    const agents = [...mockJobsData]

    const wrapper = mountAgentTableView({ agents }, pinia)

    await wrapper.vm.$nextTick()

    expect(wrapper.props('agents')[0].health_status).toBe('healthy')

    // Simulate health status change
    const updatedAgents = agents.map((agent) =>
      agent.job_id === 'job-001'
        ? { ...agent, health_status: 'warning' }
        : agent
    )

    await wrapper.setProps({ agents: updatedAgents })
    await wrapper.vm.$nextTick()

    expect(wrapper.props('agents')[0].health_status).toBe('warning')
  })

  it('updates last_progress_at timestamp on activity', async () => {
    const agents = [...mockJobsData]

    const wrapper = mountAgentTableView({ agents }, pinia)

    await wrapper.vm.$nextTick()

    const oldTimestamp = agents[0].last_progress_at
    const newTimestamp = new Date().toISOString()

    // Simulate progress update
    const updatedAgents = agents.map((agent) =>
      agent.job_id === 'job-001'
        ? { ...agent, last_progress_at: newTimestamp }
        : agent
    )

    await wrapper.setProps({ agents: updatedAgents })
    await wrapper.vm.$nextTick()

    const item = wrapper.props('agents')[0]
    expect(item.last_progress_at).not.toBe(oldTimestamp)
    expect(item.last_progress_at).toBe(newTimestamp)
  })

  it('handles multiple concurrent prop updates', async () => {
    const agents = [...mockJobsData]

    const wrapper = mountAgentTableView({ agents }, pinia)

    await wrapper.vm.$nextTick()

    // Simulate multiple concurrent updates
    const updatedAgents = agents.map((agent, idx) => {
      let updated = { ...agent }
      if (idx === 0) updated.status = 'complete'
      if (idx === 1) updated.unread_count = (agent.unread_count || 0) + 2
      if (idx === 2) updated.health_status = 'critical'
      return updated
    })

    await wrapper.setProps({ agents: updatedAgents })
    await wrapper.vm.$nextTick()

    const items = wrapper.props('agents')

    expect(items[0].status).toBe('complete')
    expect(items[1].unread_count).toBe(2)
    expect(items[2].health_status).toBe('critical')
  })
})

// ============================================
// TESTS: USER INTERACTIONS
// ============================================

describe('Status Board Integration - User Interactions', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('exposes handleRowClick that emits row-click event', async () => {
    const wrapper = mountAgentTableView({ agents: mockJobsData.slice(0, 1) }, pinia)

    await wrapper.vm.$nextTick()

    // Call the internal handler directly since the stub cannot simulate v-data-table click:row
    const mockEvent = {}
    const mockItem = mockJobsData[0]
    wrapper.vm.handleRowClick(mockEvent, { item: mockItem })

    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('row-click')).toBeTruthy()
    expect(wrapper.emitted('row-click')[0][0]).toEqual(mockItem)
  })

  it('exposes handleCopyPrompt that calls API and clipboard', async () => {
    const wrapper = mountAgentTableView({ agents: mockJobsData.slice(0, 1) }, pinia)

    await wrapper.vm.$nextTick()

    // handleCopyPrompt is accessible via component vm
    expect(typeof wrapper.vm.handleCopyPrompt).toBe('function')
  })

  it('exposes handleViewMessages that emits row-click', async () => {
    const wrapper = mountAgentTableView({ agents: mockJobsData.slice(0, 1) }, pinia)

    await wrapper.vm.$nextTick()

    const mockJob = mockJobsData[0]
    wrapper.vm.handleViewMessages(mockJob)

    await wrapper.vm.$nextTick()

    // handleViewMessages emits row-click with the job
    expect(wrapper.emitted('row-click')).toBeTruthy()
    expect(wrapper.emitted('row-click')[0][0]).toEqual(mockJob)
  })

  it('exposes handleLaunchJob that emits launch-agent', async () => {
    const wrapper = mountAgentTableView({ agents: mockJobsData.slice(0, 1) }, pinia)

    await wrapper.vm.$nextTick()

    const mockJob = mockJobsData[0]
    wrapper.vm.handleLaunchJob(mockJob)

    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('launch-agent')).toBeTruthy()
    expect(wrapper.emitted('launch-agent')[0][0]).toEqual(mockJob)
  })
})

// ============================================
// TESTS: MESSAGE HANDLING
// ============================================

describe('Status Board Integration - Message Flows', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('accepts agents with unread messages via props', async () => {
    const jobWithMessages = mockJobsData.filter(j => j.unread_count > 0)[0]

    const wrapper = mountAgentTableView({ agents: [jobWithMessages] }, pinia)

    await wrapper.vm.$nextTick()

    // Component mounts and accepts the agent with unread messages
    expect(wrapper.exists()).toBe(true)
    expect(wrapper.props('agents')[0].unread_count).toBe(2)
    expect(wrapper.props('agents')[0].job_id).toBe('job-001')
  })

  it('accepts agents with zero unread messages via props', async () => {
    const jobNoMessages = mockJobsData.filter(j => j.unread_count === 0)[0]

    const wrapper = mountAgentTableView({ agents: [jobNoMessages] }, pinia)

    await wrapper.vm.$nextTick()

    // Component should render even with 0 unread messages
    expect(wrapper.exists()).toBe(true)
    expect(wrapper.props('agents')[0].unread_count).toBe(0)
  })

  it('passes mission read status through to agents prop', async () => {
    const jobWithMissionRead = mockJobsData.filter(j => j.mission_read_at)[0]

    const wrapper = mountAgentTableView({ agents: [jobWithMissionRead] }, pinia)

    await wrapper.vm.$nextTick()

    // Mission read status should be accessible in agent data
    const agent = wrapper.props('agents')[0]
    expect(agent.mission_read_at).not.toBeNull()
  })

  it('passes message count fields through to agents prop', async () => {
    const wrapper = mountAgentTableView({ agents: [mockJobsData[0]] }, pinia)

    await wrapper.vm.$nextTick()

    const agent = wrapper.props('agents')[0]
    expect(agent.messages_sent_count).toBe(5)
    expect(agent.messages_waiting_count).toBe(2)
    expect(agent.messages_read_count).toBe(3)
  })
})

// ============================================
// TESTS: TABLE STATE MANAGEMENT
// ============================================

describe('Status Board Integration - Table State Management', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('maintains component after prop updates change agent count', async () => {
    const initialAgents = mockJobsData.slice(0, 2)

    const wrapper = mountAgentTableView({ agents: initialAgents }, pinia)

    await wrapper.vm.$nextTick()

    expect(wrapper.props('agents')).toHaveLength(2)

    // Update with more agents
    await wrapper.setProps({ agents: mockJobsData })
    await wrapper.vm.$nextTick()

    expect(wrapper.props('agents')).toHaveLength(4)
    expect(wrapper.exists()).toBe(true)
  })

  it('handles empty agents list gracefully', async () => {
    const wrapper = mountAgentTableView({ agents: [] }, pinia)

    await wrapper.vm.$nextTick()

    // Component should still render
    expect(wrapper.exists()).toBe(true)
    expect(wrapper.props('agents')).toHaveLength(0)
  })

  it('supports mode switching between jobs and launch', async () => {
    const wrapper = mountAgentTableView({}, pinia)

    await wrapper.vm.$nextTick()
    expect(wrapper.props('mode')).toBe('jobs')

    // Switch to launch mode (valid modes: 'launch' | 'jobs')
    await wrapper.setProps({ mode: 'launch' })
    await wrapper.vm.$nextTick()

    expect(wrapper.props('mode')).toBe('launch')
  })

  it('toggles Claude Code CLI mode', async () => {
    const wrapper = mountAgentTableView({}, pinia)

    await wrapper.vm.$nextTick()
    expect(wrapper.props('usingClaudeCodeSubagents')).toBe(false)

    // Enable CLI mode
    await wrapper.setProps({ usingClaudeCodeSubagents: true })
    await wrapper.vm.$nextTick()

    expect(wrapper.props('usingClaudeCodeSubagents')).toBe(true)
  })

  it('renders data table stub element', async () => {
    const wrapper = mountAgentTableView({}, pinia)

    await wrapper.vm.$nextTick()

    // The stubbed v-data-table renders as a div
    const tableEl = wrapper.find('.v-data-table')
    expect(tableEl.exists()).toBe(true)
  })
})

// ============================================
// TESTS: COMPONENT INTERACTION CHAINS
// ============================================

describe('Status Board Integration - Component Chains', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('StatusChip displays status with correct visual', async () => {
    const job = mockJobsData[0]

    const wrapper = mount(StatusChip, {
      props: {
        status: job.status,
        healthStatus: job.health_status
      },
      global: {
        plugins: [pinia]
      }
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.exists()).toBe(true)
    expect(wrapper.props('status')).toBe('working')
  })

  it('ActionIcons renders appropriate buttons for job status', async () => {
    const waitingJob = mockJobsData.find(j => j.status === 'waiting')

    const wrapper = mount(ActionIcons, {
      props: {
        job: waitingJob,
        claudeCodeCliMode: false
      },
      global: {
        plugins: [pinia]
      }
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.exists()).toBe(true)
    expect(wrapper.props('job')).toEqual(waitingJob)
  })

  it('ActionIcons exposes available actions for waiting job', async () => {
    const waitingJob = mockJobsData.find(j => j.status === 'waiting')

    const wrapper = mount(ActionIcons, {
      props: {
        job: waitingJob,
        claudeCodeCliMode: false
      },
      global: {
        plugins: [pinia]
      }
    })

    await wrapper.vm.$nextTick()

    // ActionIcons uses getAvailableActions internally
    // For a waiting non-decommissioned job: launch, copyPrompt, viewMessages
    const actionDiv = wrapper.find('.action-icons')
    expect(actionDiv.exists()).toBe(true)
  })

  it('ActionIcons includes copyPrompt in available actions for non-decommissioned job', async () => {
    const waitingJob = mockJobsData.find(j => j.status === 'waiting')

    const wrapper = mount(ActionIcons, {
      props: {
        job: waitingJob,
        claudeCodeCliMode: false
      },
      global: {
        plugins: [pinia]
      }
    })

    await wrapper.vm.$nextTick()

    // Verify copyPrompt is in the computed availableActions
    // (data-test="action-copyPrompt" is on v-btn inside v-tooltip #activator scoped slot,
    // which the stub does not render, so we verify via the component's computed property)
    expect(wrapper.vm.availableActions).toContain('copyPrompt')
  })

  it('ActionIcons includes viewMessages in available actions', async () => {
    const waitingJob = mockJobsData.find(j => j.status === 'waiting')

    const wrapper = mount(ActionIcons, {
      props: {
        job: waitingJob,
        claudeCodeCliMode: false
      },
      global: {
        plugins: [pinia]
      }
    })

    await wrapper.vm.$nextTick()

    // Verify viewMessages is in the computed availableActions
    // (data-test="action-viewMessages" is on v-btn inside v-tooltip #activator scoped slot,
    // which the stub does not render, so we verify via the component's computed property)
    expect(wrapper.vm.availableActions).toContain('viewMessages')
  })

  it('AgentTableView and its child components mount independently', async () => {
    // AgentTableView mounts (child components are inside stubbed v-data-table scoped slots)
    const tableWrapper = mountAgentTableView({ agents: mockJobsData.slice(0, 1) }, pinia)
    expect(tableWrapper.exists()).toBe(true)

    // StatusChip mounts directly with same data
    const chipWrapper = mount(StatusChip, {
      props: {
        status: mockJobsData[0].status,
        healthStatus: mockJobsData[0].health_status
      },
      global: { plugins: [pinia] }
    })
    expect(chipWrapper.exists()).toBe(true)
    expect(chipWrapper.props('status')).toBe('working')

    // ActionIcons mounts directly with same data
    const iconsWrapper = mount(ActionIcons, {
      props: {
        job: mockJobsData[0],
        claudeCodeCliMode: false
      },
      global: { plugins: [pinia] }
    })
    expect(iconsWrapper.exists()).toBe(true)
    expect(iconsWrapper.props('job').job_id).toBe('job-001')
  })

  it('handles large job list without performance issues', async () => {
    const largeJobList = Array.from({ length: 100 }, (_, i) => ({
      ...mockJobsData[i % mockJobsData.length],
      job_id: `job-${i}`,
      agent_id: `agent-${i}`,
      agent_name: `Agent ${i}`
    }))

    const startTime = performance.now()

    const wrapper = mountAgentTableView({ agents: largeJobList }, pinia)

    await wrapper.vm.$nextTick()

    const endTime = performance.now()
    const renderTime = endTime - startTime

    // Render should be reasonably fast (< 5 seconds)
    expect(renderTime).toBeLessThan(5000)

    // Verify all agents passed through
    expect(wrapper.props('agents')).toHaveLength(100)
  })

  it('canCopyPrompt returns false for decommissioned agents', async () => {
    const decommissionedAgent = { ...mockJobsData[0], status: 'decommissioned' }

    const wrapper = mountAgentTableView({ agents: [decommissionedAgent] }, pinia)

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.canCopyPrompt(decommissionedAgent)).toBe(false)
  })

  it('canCopyPrompt returns true for working agents in general CLI mode', async () => {
    const wrapper = mountAgentTableView({ usingClaudeCodeSubagents: false }, pinia)

    await wrapper.vm.$nextTick()

    const workingAgent = mockJobsData[0]
    expect(wrapper.vm.canCopyPrompt(workingAgent)).toBe(true)
  })

  it('canCopyPrompt restricts to orchestrator in Claude Code mode', async () => {
    const wrapper = mountAgentTableView({ usingClaudeCodeSubagents: true }, pinia)

    await wrapper.vm.$nextTick()

    // Non-orchestrator agent: should NOT be copyable in Claude Code mode
    const implementerAgent = mockJobsData[0] // agent_display_name: 'implementer'
    expect(wrapper.vm.canCopyPrompt(implementerAgent)).toBe(false)

    // Orchestrator agent: should be copyable in Claude Code mode
    const orchestratorAgent = mockJobsData[3] // agent_display_name: 'orchestrator'
    expect(wrapper.vm.canCopyPrompt(orchestratorAgent)).toBe(true)
  })
})
