/**
 * MessageInput E2E Test - Agent ID Selection
 *
 * Tests that MessageInput component can:
 * 1. Display agents by UUID in dropdown
 * 2. Send message to specific agent by UUID
 * 3. Emit payload with to_agent_id field
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import MessageInput from '@/components/projects/MessageInput.vue'

const vuetify = createVuetify({
  components,
  directives,
})

// Mock ResizeObserver for Vuetify components
global.ResizeObserver = class ResizeObserver {
  constructor(callback) {}
  observe() {}
  unobserve() {}
  disconnect() {}
}

describe('MessageInput - Agent ID Selection', () => {
  it('should display agents by UUID in dropdown and emit to_agent_id when message sent', async () => {
    const mockAgents = [
      {
        agent_id: 'abc12345-6789-0123-4567-890abcdef123',
        agent_display_name: 'orchestrator',
        instance_number: 1,
      },
      {
        agent_id: 'def67890-1234-5678-9012-345678901234',
        agent_display_name: 'implementor',
        instance_number: 2,
      },
    ]

    const wrapper = mount(MessageInput, {
      props: {
        jobId: 'test-job-123',
        agents: mockAgents,
      },
      global: {
        plugins: [vuetify],
      },
    })

    // Verify dropdown has correct number of options (broadcast + 2 agents)
    const recipientSelect = wrapper.find('[data-testid="recipient-select"]')
    expect(recipientSelect.exists()).toBe(true)

    // Verify dropdown options include truncated UUIDs
    const dropdown = wrapper.vm.recipientOptions
    expect(dropdown).toHaveLength(3) // Broadcast + 2 agents
    expect(dropdown[0].label).toBe('Broadcast')
    expect(dropdown[0].value).toBe('broadcast')
    expect(dropdown[1].label).toBe('orchestrator (Instance 1) - abc12345...')
    expect(dropdown[1].value).toBe('abc12345-6789-0123-4567-890abcdef123')
    expect(dropdown[2].label).toBe('implementor (Instance 2) - def67890...')
    expect(dropdown[2].value).toBe('def67890-1234-5678-9012-345678901234')

    // Select agent by UUID
    wrapper.vm.recipient = 'abc12345-6789-0123-4567-890abcdef123'
    await wrapper.vm.$nextTick()

    // Type message
    wrapper.vm.messageText = 'Test message to orchestrator'
    await wrapper.vm.$nextTick()

    // Verify canSend is true before submitting
    expect(wrapper.vm.canSend).toBe(true)

    // Submit message
    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()

    // Verify message-sent event emitted with to_agent_id
    const emittedEvents = wrapper.emitted('message-sent')
    expect(emittedEvents).toBeTruthy()
    expect(emittedEvents).toHaveLength(1)

    const payload = emittedEvents[0][0]
    expect(payload.content).toBe('Test message to orchestrator')
    expect(payload.to_agent_id).toBe('abc12345-6789-0123-4567-890abcdef123')
    expect(payload.recipient).toBe('abc12345-6789-0123-4567-890abcdef123')
    expect(payload.jobId).toBe('test-job-123')
  })

  it('should emit to_agent_id as null when broadcast selected', async () => {
    const mockAgents = [
      {
        agent_id: 'abc12345-6789-0123-4567-890abcdef123',
        agent_display_name: 'orchestrator',
        instance_number: 1,
      },
    ]

    const wrapper = mount(MessageInput, {
      props: {
        jobId: 'test-job-123',
        agents: mockAgents,
      },
      global: {
        plugins: [vuetify],
      },
    })

    // Select broadcast (default)
    wrapper.vm.recipient = 'broadcast'
    await wrapper.vm.$nextTick()

    // Type message
    wrapper.vm.messageText = 'Test broadcast message'
    await wrapper.vm.$nextTick()

    // Submit message
    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()

    // Verify message-sent event emitted with to_agent_id = null
    const emittedEvents = wrapper.emitted('message-sent')
    expect(emittedEvents).toBeTruthy()
    expect(emittedEvents).toHaveLength(1)

    const payload = emittedEvents[0][0]
    expect(payload.content).toBe('Test broadcast message')
    expect(payload.to_agent_id).toBeNull()
    expect(payload.recipient).toBe('broadcast')
  })

  it('should handle empty agents array gracefully', async () => {
    const wrapper = mount(MessageInput, {
      props: {
        jobId: 'test-job-123',
        agents: [],
      },
      global: {
        plugins: [vuetify],
      },
    })

    // Verify dropdown only has broadcast option
    const dropdown = wrapper.vm.recipientOptions
    expect(dropdown).toHaveLength(1)
    expect(dropdown[0].label).toBe('Broadcast')
    expect(dropdown[0].value).toBe('broadcast')
  })
})
