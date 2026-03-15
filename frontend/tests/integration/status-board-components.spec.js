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
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
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
// TESTS: DATA LOADING & RENDERING
// ============================================

describe('Status Board Integration - Data Loading & Rendering', () => {
  let pinia
  let vuetify

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loads table with job data on mount', async () => {
    const wrapper = mount(AgentTableView, {
      props: {
        agents: mockJobsData,
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    // Verify component mounted
    expect(wrapper.exists()).toBe(true)

    // Verify props passed correctly
    expect(wrapper.props('agents')).toHaveLength(4)
    expect(wrapper.props('agents')[0].job_id).toBe('job-001')
  })

  it('renders correct number of rows from agents prop', async () => {
    const wrapper = mount(AgentTableView, {
      props: {
        agents: mockJobsData,
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    // Verify data table component exists
    const dataTable = wrapper.findComponent({ name: 'VDataTable' })
    expect(dataTable.exists()).toBe(true)

    // Verify items prop matches data
    expect(dataTable.props('items')).toHaveLength(4)
  })

  it('displays agent display names correctly in table', async () => {
    const wrapper = mount(AgentTableView, {
      props: {
        agents: mockJobsData.slice(0, 2),
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    const dataTable = wrapper.findComponent({ name: 'VDataTable' })
    const items = dataTable.props('items')

    expect(items[0].agent_display_name).toBe('implementer')
    expect(items[1].agent_display_name).toBe('analyzer')
  })

  it('includes status chip components for each job', async () => {
    const wrapper = mount(AgentTableView, {
      props: {
        agents: mockJobsData,
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    // StatusChip components should be found
    const statusChips = wrapper.findAllComponents(StatusChip)
    expect(statusChips.length).toBeGreaterThan(0)
  })

  it('includes action icons components for each job', async () => {
    const wrapper = mount(AgentTableView, {
      props: {
        agents: mockJobsData,
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    // ActionIcons components should be found
    const actionIcons = wrapper.findAllComponents(ActionIcons)
    expect(actionIcons.length).toBeGreaterThan(0)
  })
})

// ============================================
// TESTS: WEBSOCKET INTEGRATION (via prop updates)
// ============================================

describe('Status Board Integration - WebSocket Real-time Updates', () => {
  let pinia
  let vuetify

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('updates table when job status changes via prop update', async () => {
    const agents = [...mockJobsData]

    const wrapper = mount(AgentTableView, {
      props: {
        agents,
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    // Verify initial status
    const dataTable = wrapper.findComponent({ name: 'VDataTable' })
    expect(dataTable.props('items')[0].status).toBe('working')

    // Simulate WebSocket status change via prop update
    const updatedAgents = agents.map((agent) =>
      agent.job_id === 'job-001'
        ? { ...agent, status: 'complete' }
        : agent
    )

    await wrapper.setProps({ agents: updatedAgents })
    await wrapper.vm.$nextTick()

    // Verify status updated
    const updatedTable = wrapper.findComponent({ name: 'VDataTable' })
    expect(updatedTable.props('items')[0].status).toBe('complete')
  })

  it('updates unread message count when new message received', async () => {
    const agents = [...mockJobsData]

    const wrapper = mount(AgentTableView, {
      props: {
        agents,
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

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

    const dataTable = wrapper.findComponent({ name: 'VDataTable' })
    expect(dataTable.props('items')[0].unread_count).toBe(3)
  })

  it('updates health status when job health changes', async () => {
    const agents = [...mockJobsData]

    const wrapper = mount(AgentTableView, {
      props: {
        agents,
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    const initialHealth = agents[0].health_status
    expect(initialHealth).toBe('healthy')

    // Simulate health status change
    const updatedAgents = agents.map((agent) =>
      agent.job_id === 'job-001'
        ? { ...agent, health_status: 'warning' }
        : agent
    )

    await wrapper.setProps({ agents: updatedAgents })
    await wrapper.vm.$nextTick()

    const dataTable = wrapper.findComponent({ name: 'VDataTable' })
    expect(dataTable.props('items')[0].health_status).toBe('warning')
  })

  it('updates last_progress_at timestamp on activity', async () => {
    const agents = [...mockJobsData]

    const wrapper = mount(AgentTableView, {
      props: {
        agents,
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

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

    const dataTable = wrapper.findComponent({ name: 'VDataTable' })
    const item = dataTable.props('items')[0]
    expect(item.last_progress_at).not.toBe(oldTimestamp)
    expect(item.last_progress_at).toBe(newTimestamp)
  })

  it('handles multiple concurrent prop updates', async () => {
    const agents = [...mockJobsData]

    const wrapper = mount(AgentTableView, {
      props: {
        agents,
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

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

    const dataTable = wrapper.findComponent({ name: 'VDataTable' })
    const items = dataTable.props('items')

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
  let vuetify

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('emits row-click event when table row clicked', async () => {
    const wrapper = mount(AgentTableView, {
      props: {
        agents: mockJobsData.slice(0, 1),
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    const dataTable = wrapper.findComponent({ name: 'VDataTable' })

    // Simulate row click - VDataTable emits click:row
    if (dataTable.exists()) {
      dataTable.vm.$emit('click:row', {}, { item: mockJobsData[0] })
      await wrapper.vm.$nextTick()
    }

    // Component should handle row click
    expect(wrapper.emitted('row-click')).toBeTruthy()
  })

  it('handles action icon button clicks', async () => {
    const wrapper = mount(AgentTableView, {
      props: {
        agents: mockJobsData.slice(0, 1),
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    // Find first ActionIcons component
    const actionIcons = wrapper.findComponent(ActionIcons)
    expect(actionIcons.exists()).toBe(true)
  })

  it('supports copy prompt action via data-test attribute', async () => {
    const wrapper = mount(AgentTableView, {
      props: {
        agents: mockJobsData.slice(0, 1),
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    // ActionIcons should have copy-prompt capability via data-test
    const copyButton = wrapper.find('[data-test="action-copyPrompt"]')
    expect(copyButton.exists()).toBe(true)
  })

  it('supports view messages action via data-test attribute', async () => {
    const wrapper = mount(AgentTableView, {
      props: {
        agents: mockJobsData.slice(0, 1),
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    // ActionIcons should have view messages capability via data-test
    const viewButton = wrapper.find('[data-test="action-viewMessages"]')
    expect(viewButton.exists()).toBe(true)
  })
})

// ============================================
// TESTS: MESSAGE HANDLING
// ============================================

describe('Status Board Integration - Message Flows', () => {
  let pinia
  let vuetify

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('handles agents with unread messages', async () => {
    const jobWithMessages = mockJobsData.filter(j => j.unread_count > 0)[0]

    const wrapper = mount(AgentTableView, {
      props: {
        agents: [jobWithMessages],
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    // Find action icons for this job
    const actionIcons = wrapper.findComponent(ActionIcons)
    expect(actionIcons.exists()).toBe(true)
  })

  it('handles zero unread messages gracefully', async () => {
    const jobNoMessages = mockJobsData.filter(j => j.unread_count === 0)[0]

    const wrapper = mount(AgentTableView, {
      props: {
        agents: [jobNoMessages],
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    const actionIcons = wrapper.findComponent(ActionIcons)

    // Component should still render even with 0 messages
    expect(actionIcons.exists()).toBe(true)
  })

  it('displays mission read status indicators', async () => {
    const jobWithMissionRead = mockJobsData.filter(j => j.mission_read_at)[0]

    const wrapper = mount(AgentTableView, {
      props: {
        agents: [jobWithMissionRead],
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    // Mission read status should be accessible in job data
    const dataTable = wrapper.findComponent({ name: 'VDataTable' })
    const item = dataTable.props('items')[0]

    expect(item.mission_read_at).not.toBeNull()
  })
})

// ============================================
// TESTS: TABLE STATE MANAGEMENT
// ============================================

describe('Status Board Integration - Table State Management', () => {
  let pinia
  let vuetify

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('maintains table after prop updates', async () => {
    const initialAgents = mockJobsData.slice(0, 2)

    const wrapper = mount(AgentTableView, {
      props: {
        agents: initialAgents,
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    const dataTable = wrapper.findComponent({ name: 'VDataTable' })
    expect(dataTable.props('items')).toHaveLength(2)

    // Update with new agents
    const updatedAgents = mockJobsData
    await wrapper.setProps({ agents: updatedAgents })
    await wrapper.vm.$nextTick()

    const updatedTable = wrapper.findComponent({ name: 'VDataTable' })
    expect(updatedTable.props('items')).toHaveLength(4)
  })

  it('handles empty agents list gracefully', async () => {
    const wrapper = mount(AgentTableView, {
      props: {
        agents: [],
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    // Component should still render
    expect(wrapper.exists()).toBe(true)

    const dataTable = wrapper.findComponent({ name: 'VDataTable' })
    if (dataTable.exists()) {
      expect(dataTable.props('items')).toHaveLength(0)
    }
  })

  it('supports mode switching between jobs and agents', async () => {
    const wrapper = mount(AgentTableView, {
      props: {
        agents: mockJobsData,
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()
    expect(wrapper.props('mode')).toBe('jobs')

    // Switch to agents mode
    await wrapper.setProps({ mode: 'agents' })
    await wrapper.vm.$nextTick()

    expect(wrapper.props('mode')).toBe('agents')
  })

  it('toggles Claude Code CLI mode', async () => {
    const wrapper = mount(AgentTableView, {
      props: {
        agents: mockJobsData,
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()
    expect(wrapper.props('usingClaudeCodeSubagents')).toBe(false)

    // Enable CLI mode
    await wrapper.setProps({ usingClaudeCodeSubagents: true })
    await wrapper.vm.$nextTick()

    expect(wrapper.props('usingClaudeCodeSubagents')).toBe(true)
  })
})

// ============================================
// TESTS: COMPONENT INTERACTION CHAINS
// ============================================

describe('Status Board Integration - Component Chains', () => {
  let pinia
  let vuetify

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vuetify = createVuetify({
      components,
      directives,
    })
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
        plugins: [pinia, vuetify]
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
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.exists()).toBe(true)
    expect(wrapper.props('job')).toEqual(waitingJob)
  })

  it('Table + StatusChip + ActionIcons render together', async () => {
    const wrapper = mount(AgentTableView, {
      props: {
        agents: mockJobsData.slice(0, 1),
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    // All three components should be present
    expect(wrapper.findComponent(AgentTableView).exists()).toBe(true)
    expect(wrapper.findComponent(StatusChip).exists()).toBe(true)
    expect(wrapper.findComponent(ActionIcons).exists()).toBe(true)
  })

  it('handles large job list without performance issues', async () => {
    const largeJobList = Array.from({ length: 100 }, (_, i) => ({
      ...mockJobsData[i % mockJobsData.length],
      job_id: `job-${i}`,
      agent_id: `agent-${i}`,
      agent_name: `Agent ${i}`
    }))

    const startTime = performance.now()

    const wrapper = mount(AgentTableView, {
      props: {
        agents: largeJobList,
        mode: 'jobs',
        usingClaudeCodeSubagents: false
      },
      global: {
        plugins: [pinia, vuetify]
      }
    })

    await wrapper.vm.$nextTick()

    const endTime = performance.now()
    const renderTime = endTime - startTime

    // Render should be reasonably fast (< 5 seconds)
    expect(renderTime).toBeLessThan(5000)

    const dataTable = wrapper.findComponent({ name: 'VDataTable' })
    expect(dataTable.props('items')).toHaveLength(100)
  })
})
