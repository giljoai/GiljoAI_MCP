import { describe, it, expect, beforeEach, vi } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import MessagePanel from '@/components/messages/MessagePanel.vue'
import MessageList from '@/components/messages/MessageList.vue'

// Mock the API module
vi.mock('@/services/api', () => ({
  default: {
    messages: {
      list: vi.fn(() => Promise.resolve({ data: [] }))
    }
  }
}))

// Mock WebSocket composable
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    isConnected: { value: false },
    on: vi.fn(),
    connect: vi.fn()
  })
}))

describe('MessagePanel - Refactored (Handover 0231)', () => {
  let vuetify

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  it('imports and uses MessageList component when messages exist', () => {
    const wrapper = shallowMount(MessagePanel, {
      global: {
        plugins: [vuetify]
      }
    })

    // Set messages so MessageList renders (instead of empty state)
    wrapper.vm.messages = [
      { id: '1', content: 'Test', status: 'pending', from: 'agent-1', to_agents: [], created_at: new Date().toISOString() }
    ]
    wrapper.vm.loading = false
    wrapper.vm.error = null

    // Force re-render
    return wrapper.vm.$nextTick().then(() => {
      // Check that MessageList stub is present in shallow render
      const html = wrapper.html()
      expect(html).toContain('message-list-stub')
    })
  })

  it('behavioral equivalence - filteredMessages computed property still works', () => {
    const wrapper = shallowMount(MessagePanel, {
      global: {
        plugins: [vuetify]
      }
    })

    // Set test messages
    wrapper.vm.messages = [
      { id: '1', content: 'Test 1', status: 'pending', type: 'direct', from: 'agent-1', to_agents: [], created_at: new Date().toISOString() },
      { id: '2', content: 'Test 2', status: 'acknowledged', type: 'broadcast', from: 'agent-2', to_agents: [], created_at: new Date().toISOString() }
    ]

    // Filter logic should still work
    expect(wrapper.vm.filteredMessages).toBeDefined()
    expect(wrapper.vm.filteredMessages).toHaveLength(2)

    // Apply filter
    wrapper.vm.selectedType = 'direct'
    expect(wrapper.vm.filteredMessages).toHaveLength(1)
    expect(wrapper.vm.filteredMessages[0].type).toBe('direct')
  })

  it('preserves search functionality', () => {
    const wrapper = shallowMount(MessagePanel, {
      global: {
        plugins: [vuetify]
      }
    })

    wrapper.vm.messages = [
      { id: '1', content: 'Important message', status: 'pending', from: 'agent-1', to_agents: [], created_at: new Date().toISOString() },
      { id: '2', content: 'Regular message', status: 'pending', from: 'agent-2', to_agents: [], created_at: new Date().toISOString() }
    ]

    wrapper.vm.searchQuery = 'Important'

    expect(wrapper.vm.filteredMessages).toHaveLength(1)
    expect(wrapper.vm.filteredMessages[0].content).toContain('Important')
  })

  it('preserves agent filter functionality', () => {
    const wrapper = shallowMount(MessagePanel, {
      global: {
        plugins: [vuetify]
      }
    })

    wrapper.vm.messages = [
      { id: '1', content: 'Test 1', status: 'pending', from: 'agent-1', to_agents: ['agent-2'], created_at: new Date().toISOString() },
      { id: '2', content: 'Test 2', status: 'pending', from: 'agent-2', to_agents: ['agent-3'], created_at: new Date().toISOString() }
    ]

    wrapper.vm.selectedAgent = 'agent-1'

    // Filter includes messages FROM agent-1 OR TO agent-1
    // In this case, only message 1 matches (from agent-1)
    expect(wrapper.vm.filteredMessages).toHaveLength(1)
    expect(wrapper.vm.filteredMessages[0].from).toBe('agent-1')
  })

  it('preserves status filter functionality', () => {
    const wrapper = shallowMount(MessagePanel, {
      global: {
        plugins: [vuetify]
      }
    })

    wrapper.vm.messages = [
      { id: '1', content: 'Test 1', status: 'pending', from: 'agent-1', to_agents: [], created_at: new Date().toISOString() },
      { id: '2', content: 'Test 2', status: 'acknowledged', from: 'agent-2', to_agents: [], created_at: new Date().toISOString() }
    ]

    wrapper.vm.selectedStatus = 'pending'

    expect(wrapper.vm.filteredMessages).toHaveLength(1)
    expect(wrapper.vm.filteredMessages[0].status).toBe('pending')
  })
})
