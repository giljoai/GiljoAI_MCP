/**
 * MessageAuditModal.0331.spec.js
 *
 * Handover 0331: Message Audit Modal baseline
 *
 * Tests focus on behavior:
 * - Grouping messages into Sent / Waiting / Read buckets using the same
 *   semantics as JobsTab message counters.
 * - Filtering the visible list when switching tabs.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import { nextTick } from 'vue'
import MessageAuditModal from '@/components/projects/MessageAuditModal.vue'

const vuetify = createVuetify()

const createMockMessage = (overrides = {}) => ({
  id: 'msg-' + Math.random().toString(36).slice(2, 9),
  from: 'developer',
  direction: 'outbound',
  status: 'sent',
  text: 'Test message',
  priority: 'normal',
  timestamp: new Date().toISOString(),
  ...overrides,
})

const createMockAgent = (overrides = {}) => ({
  job_id: 'job-' + Math.random().toString(36).slice(2, 9),
  agent_type: 'implementer',
  agent_name: 'Implementer Agent',
  messages: [],
  ...overrides,
})

// Mirror JobsTab helper semantics so we assert behavior, not implementation details
const getMessagesSent = (agent) =>
  (agent.messages || []).filter(
    (m) => m.from === 'developer' || m.direction === 'outbound',
  ).length

const getMessagesWaiting = (agent) =>
  (agent.messages || []).filter(
    (m) => m.status === 'pending' || m.status === 'waiting',
  ).length

const getMessagesRead = (agent) =>
  (agent.messages || []).filter(
    (m) =>
      m.direction === 'inbound' &&
      (m.status === 'acknowledged' || m.status === 'read'),
  ).length

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
      messages: [
        // Sent
        createMockMessage({
          from: 'developer',
          direction: 'outbound',
          status: 'sent',
          text: 'sent-1',
        }),
        createMockMessage({
          direction: 'outbound',
          status: 'sent',
          text: 'sent-2',
        }),
        // Waiting
        createMockMessage({
          direction: 'inbound',
          status: 'waiting',
          text: 'waiting-1',
        }),
        createMockMessage({
          direction: 'inbound',
          status: 'pending',
          text: 'waiting-2',
        }),
        // Read
        createMockMessage({
          direction: 'inbound',
          status: 'acknowledged',
          text: 'read-1',
        }),
        createMockMessage({
          direction: 'inbound',
          status: 'read',
          text: 'read-2',
        }),
      ],
    })
  })

  it('renders Sent / Waiting / Read tabs with counts matching JobsTab counters', () => {
    const wrapper = mountModal()

    const sentCount = getMessagesSent(agent)
    const waitingCount = getMessagesWaiting(agent)
    const readCount = getMessagesRead(agent)

    const sentTab = wrapper.get('[data-test="messages-tab-sent"]')
    const waitingTab = wrapper.get('[data-test="messages-tab-waiting"]')
    const readTab = wrapper.get('[data-test="messages-tab-read"]')

    expect(sentTab.text()).toContain(`Sent (${sentCount})`)
    expect(waitingTab.text()).toContain(`Waiting (${waitingCount})`)
    expect(readTab.text()).toContain(`Read (${readCount})`)
  })

  it('filters message list when switching between Sent / Waiting / Read tabs', async () => {
    const wrapper = mountModal()

    // Default tab is Waiting
    let rows = wrapper.findAll('[data-test="audit-message-row"]')
    expect(rows.length).toBe(getMessagesWaiting(agent))
    rows.forEach((row) => {
      expect(row.text()).toMatch(/waiting-1|waiting-2/)
    })

    // Switch to Sent
    await wrapper.get('[data-test="messages-tab-sent"]').trigger('click')
    await nextTick()

    rows = wrapper.findAll('[data-test="audit-message-row"]')
    expect(rows.length).toBe(getMessagesSent(agent))
    // Sent tab should include our sent messages (it may also include others)
    const sentText = rows.map((row) => row.text()).join(' ')
    expect(sentText).toContain('sent-1')
    expect(sentText).toContain('sent-2')

    // Switch to Read
    await wrapper.get('[data-test="messages-tab-read"]').trigger('click')
    await nextTick()

    rows = wrapper.findAll('[data-test="audit-message-row"]')
    expect(rows.length).toBe(getMessagesRead(agent))
    const readText = rows.map((row) => row.text()).join(' ')
    expect(readText).toContain('read-1')
    expect(readText).toContain('read-2')
  })
})
