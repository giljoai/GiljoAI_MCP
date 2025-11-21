import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import MessageList from '@/components/messages/MessageList.vue'
import MessageItem from '@/components/messages/MessageItem.vue'

describe('MessageList Component (Handover 0231)', () => {
  let vuetify

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  it('renders message list container', () => {
    const messages = [
      { id: '1', content: 'Test message 1', status: 'pending', from: 'agent-1', to_agents: ['agent-2'], created_at: new Date().toISOString() },
      { id: '2', content: 'Test message 2', status: 'acknowledged', from: 'agent-2', to_agents: ['agent-1'], created_at: new Date().toISOString() }
    ]

    const wrapper = mount(MessageList, {
      props: { messages },
      global: {
        plugins: [vuetify],
        stubs: {
          'v-virtual-scroll': {
            template: '<div class="v-virtual-scroll-stub"><slot v-for="item in items" :item="item" /></div>',
            props: ['items', 'height', 'item-height']
          }
        }
      }
    })

    expect(wrapper.find('.message-list').exists()).toBe(true)
    // Virtual scroll stub should be present
    expect(wrapper.find('.v-virtual-scroll-stub').exists()).toBe(true)
  })

  it('emits message-click event when message clicked', async () => {
    const messages = [
      { id: '1', content: 'Test', status: 'pending', from: 'agent-1', to_agents: ['agent-2'], created_at: new Date().toISOString() }
    ]

    const wrapper = mount(MessageList, {
      props: { messages },
      global: {
        plugins: [vuetify],
        stubs: {
          'v-virtual-scroll': {
            template: '<div class="v-virtual-scroll-stub"><slot v-for="item in items" :item="item" /></div>',
            props: ['items', 'height', 'item-height']
          }
        }
      }
    })

    // Find the message item div and click it
    const messageDiv = wrapper.find('.px-4.pt-3')
    await messageDiv.trigger('click')

    expect(wrapper.emitted('message-click')).toBeTruthy()
    expect(wrapper.emitted('message-click')[0][0]).toEqual(messages[0])
  })

  it('shows empty state when no messages', () => {
    const wrapper = mount(MessageList, {
      props: { messages: [] },
      global: {
        plugins: [vuetify]
      }
    })

    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('No messages yet')
  })

  it('passes messages to MessageItem components', () => {
    const messages = [
      { id: '1', content: 'Message 1', status: 'pending', from: 'agent-1', to_agents: ['agent-2'], created_at: new Date().toISOString() },
      { id: '2', content: 'Message 2', status: 'acknowledged', from: 'agent-2', to_agents: ['agent-1'], created_at: new Date().toISOString() }
    ]

    const wrapper = mount(MessageList, {
      props: { messages },
      global: {
        plugins: [vuetify],
        stubs: {
          'v-virtual-scroll': {
            template: '<div class="v-virtual-scroll-stub"><slot v-for="item in items" :item="item" /></div>',
            props: ['items', 'height', 'item-height']
          }
        }
      }
    })

    const messageItems = wrapper.findAllComponents(MessageItem)

    expect(messageItems).toHaveLength(2)
    expect(messageItems[0].props('message')).toEqual(messages[0])
  })

  it('renders correctly with default empty messages prop', () => {
    const wrapper = mount(MessageList, {
      global: {
        plugins: [vuetify]
      }
    })

    // Should show empty state by default
    expect(wrapper.find('.empty-state').exists()).toBe(true)
  })
})
