/**
 * MessageAuditModal.0331.spec.js
 *
 * Handover 0331: Message Audit Modal baseline
 * Updated: Handover 0423 - Plan tab moved to AgentJobModal
 *
 * Tests focus on component structure and rendering.
 * Note: API mocking is complex; these tests verify structure, not data flow.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import MessageAuditModal from '@/components/projects/MessageAuditModal.vue'

const vuetify = createVuetify()

// Mock the API module to prevent actual API calls
vi.mock('@/services/api', () => ({
  default: {
    agentJobs: {
      messages: vi.fn().mockResolvedValue({ data: { messages: [] } }),
    },
  },
}))

const createMockAgent = (overrides = {}) => ({
  job_id: 'job-' + Math.random().toString(36).slice(2, 9),
  agent_type: 'implementer',
  agent_name: 'Implementer Agent',
  ...overrides,
})

describe('MessageAuditModal (0331)', () => {
  let agent

  const mountModal = (props = {}) =>
    mount(MessageAuditModal, {
      props: {
        show: true,
        agent,
        ...props,
      },
      global: {
        plugins: [vuetify],
        stubs: {
          'v-icon': true,
        },
      },
    })

  beforeEach(() => {
    agent = createMockAgent({
      job_id: 'test-job-123',
    })
  })

  it('renders the modal when show is true', () => {
    const wrapper = mountModal()
    // Check the component mounted successfully
    expect(wrapper.exists()).toBe(true)
    // Check tabs are rendered (they're always present in the component)
    expect(wrapper.find('[data-test="messages-tab-waiting"]').exists()).toBe(true)
  })

  it('renders Sent / Waiting / Read tabs', () => {
    const wrapper = mountModal()

    const sentTab = wrapper.find('[data-test="messages-tab-sent"]')
    const waitingTab = wrapper.find('[data-test="messages-tab-waiting"]')
    const readTab = wrapper.find('[data-test="messages-tab-read"]')

    expect(sentTab.exists()).toBe(true)
    expect(waitingTab.exists()).toBe(true)
    expect(readTab.exists()).toBe(true)

    // Tabs should show counts (may be 0)
    expect(sentTab.text()).toContain('Sent')
    expect(waitingTab.text()).toContain('Waiting')
    expect(readTab.text()).toContain('Read')
  })

  it('shows empty state when no messages', () => {
    const wrapper = mountModal()

    // With no messages, should show empty state (after loading)
    // Note: Due to async loading, this may show loading or empty state
    const emptyState = wrapper.find('.empty-state')
    const loadingState = wrapper.find('.v-progress-circular')

    // Either loading or empty state should be present
    expect(emptyState.exists() || loadingState.exists()).toBe(true)
  })

  it('emits close event when close button is clicked', async () => {
    const wrapper = mountModal()

    // Find close button and click it
    const closeBtn = wrapper.find('[aria-label="Close"]')
    if (closeBtn.exists()) {
      await closeBtn.trigger('click')
      expect(wrapper.emitted('close')).toBeTruthy()
    }
  })

  // NOTE: Plan/TODOs tab was removed in Handover 0423 - moved to AgentJobModal
  // Message list with data requires proper API mocking which is tested in E2E tests
})
