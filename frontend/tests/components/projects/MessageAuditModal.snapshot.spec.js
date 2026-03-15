/**
 * MessageAuditModal.snapshot.spec.js - Handover 0818 Phase 3
 *
 * Tests for the snapshot pattern that decouples the MessageAuditModal
 * from live WebSocket reactivity. When the modal opens, it takes a
 * shallow clone of the agent prop. While open, it uses the snapshot
 * instead of the live prop, preventing WebSocket-driven reference
 * changes from resetting expanded state or re-fetching messages.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import MessageAuditModal from '@/components/projects/MessageAuditModal.vue'

// Mock the API module -- override the global setup mock with agentJobs.messages
const mockMessages = vi.fn().mockResolvedValue({ data: { messages: [] } })
vi.mock('@/services/api', () => ({
  default: {
    agentJobs: {
      messages: (...args) => mockMessages(...args),
    },
  },
}))

// Mock the child component to keep tests focused
vi.mock('@/components/projects/MessageDetailView.vue', () => ({
  default: { name: 'MessageDetailView', template: '<div class="mock-detail" />' },
}))

const createMockAgent = (overrides = {}) => ({
  job_id: 'job-100',
  agent_id: 'agent-200',
  agent_name: 'implementer',
  agent_display_name: 'Code Implementer',
  mission: 'Build feature Y',
  ...overrides,
})

function mountModal(propsData = {}) {
  return mount(MessageAuditModal, {
    props: {
      show: false,
      agent: createMockAgent(),
      ...propsData,
    },
    global: {
      directives: { draggable: () => {} },
      stubs: {
        'v-dialog': { template: '<div><slot /></div>' },
        'v-card': { template: '<div><slot /></div>' },
        'v-card-title': { template: '<div><slot /></div>' },
        'v-card-text': { template: '<div><slot /></div>' },
        'v-divider': { template: '<hr />' },
        'v-icon': { template: '<span class="v-icon"><slot /></span>' },
        'v-btn': { template: '<button class="v-btn"><slot /></button>' },
        'v-progress-circular': { template: '<div>Loading</div>' },
        'v-alert': { template: '<div class="v-alert"><slot /></div>' },
      },
    },
  })
}

describe('MessageAuditModal snapshot pattern (Handover 0818 Phase 3)', () => {
  let wrapper

  beforeEach(() => {
    vi.clearAllMocks()
    mockMessages.mockResolvedValue({
      data: {
        messages: [
          { id: 'msg-1', direction: 'outbound', status: 'sent', text: 'Hello', to: 'orchestrator', timestamp: '2026-03-14T10:00:00Z' },
          { id: 'msg-2', direction: 'outbound', status: 'sent', text: 'World', to: 'orchestrator', timestamp: '2026-03-14T10:01:00Z' },
        ],
      },
    })
    if (wrapper) wrapper.unmount()
  })

  it('snapshot captures agent data on open', async () => {
    const agent = createMockAgent({ job_id: 'job-snap-1' })
    wrapper = mountModal({ show: false, agent })

    // Before opening, snapshot should be null
    expect(wrapper.vm.agentSnapshot).toBeNull()

    // Open the modal
    await wrapper.setProps({ show: true })
    await flushPromises()

    // Snapshot should now hold a copy of the agent data
    expect(wrapper.vm.agentSnapshot).not.toBeNull()
    expect(wrapper.vm.agentSnapshot.job_id).toBe('job-snap-1')
    expect(wrapper.vm.agentSnapshot.agent_name).toBe('implementer')

    // Snapshot should be a separate object, not the same reference
    expect(wrapper.vm.agentSnapshot).not.toBe(agent)
  })

  it('expanded messages persist when props.agent reference changes while modal is open', async () => {
    const agent = createMockAgent({ job_id: 'job-persist' })
    wrapper = mountModal({ show: true, agent })
    await flushPromises()

    // Expand a message
    wrapper.vm.toggleMessageExpansion('msg-1')
    expect(wrapper.vm.isMessageExpanded('msg-1')).toBe(true)

    // Simulate WebSocket creating a new agent reference (same data, new object)
    const newAgentRef = { ...agent, _wsUpdate: true }
    await wrapper.setProps({ agent: newAgentRef })
    await flushPromises()

    // Expanded state should be preserved -- the snapshot shields the modal
    expect(wrapper.vm.isMessageExpanded('msg-1')).toBe(true)
  })

  it('closing modal resets expanded state', async () => {
    wrapper = mountModal({ show: true, agent: createMockAgent() })
    await flushPromises()

    // Expand a message
    wrapper.vm.toggleMessageExpansion('msg-1')
    expect(wrapper.vm.isMessageExpanded('msg-1')).toBe(true)

    // Close the modal
    await wrapper.setProps({ show: false })
    await flushPromises()

    // State should be cleared
    expect(wrapper.vm.isMessageExpanded('msg-1')).toBe(false)
    expect(wrapper.vm.agentSnapshot).toBeNull()
  })

  it('reopening modal fetches fresh data', async () => {
    wrapper = mountModal({ show: true, agent: createMockAgent({ job_id: 'job-fresh' }) })
    await flushPromises()

    // First open should have fetched
    expect(mockMessages).toHaveBeenCalledTimes(1)
    expect(mockMessages).toHaveBeenCalledWith('job-fresh')

    // Close the modal
    await wrapper.setProps({ show: false })
    await flushPromises()
    mockMessages.mockClear()

    // Reopen with updated agent data
    const updatedAgent = createMockAgent({ job_id: 'job-fresh-v2' })
    await wrapper.setProps({ agent: updatedAgent, show: true })
    await flushPromises()

    // Should have fetched again with the new snapshot's job_id
    expect(mockMessages).toHaveBeenCalledTimes(1)
    expect(mockMessages).toHaveBeenCalledWith('job-fresh-v2')
  })

  it('agent watcher does not re-fetch when agent prop changes while open', async () => {
    wrapper = mountModal({ show: true, agent: createMockAgent({ job_id: 'job-no-refetch' }) })
    await flushPromises()

    // Initial fetch on open
    expect(mockMessages).toHaveBeenCalledTimes(1)
    mockMessages.mockClear()

    // Simulate multiple WebSocket updates creating new agent references
    for (let i = 0; i < 5; i++) {
      const newRef = createMockAgent({ job_id: 'job-no-refetch', _tick: i })
      await wrapper.setProps({ agent: newRef })
      await flushPromises()
    }

    // No additional fetches should have occurred
    expect(mockMessages).not.toHaveBeenCalled()
  })
})
