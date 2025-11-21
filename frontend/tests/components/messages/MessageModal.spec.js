import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import MessageModal from '@/components/messages/MessageModal.vue'
import MessageList from '@/components/messages/MessageList.vue'
import MessageInput from '@/components/projects/MessageInput.vue'

// Stub MessageList to avoid v-virtual-scroll rendering issues in tests
const MessageListStub = {
  name: 'MessageList',
  props: ['messages'],
  template: '<div class="message-list-stub"></div>'
}

describe('MessageModal (Handover 0231 Phase 3)', () => {
  const defaultProps = {
    isOpen: true,
    jobId: 'test-job-1',
    agentName: 'Test Agent',
    messages: []
  }

  it('renders when isOpen is true', () => {
    const wrapper = mount(MessageModal, { props: defaultProps })
    // Check for v-dialog by looking for the wrapper element
    expect(wrapper.find('.v-dialog').exists() || wrapper.find('[role="dialog"]').exists() || wrapper.findComponent(MessageList).exists()).toBe(true)
  })

  it('uses MessageList component', () => {
    const messages = [{ id: 1, content: 'Test', status: 'pending', timestamp: '2025-11-21T10:00:00Z' }]
    const wrapper = mount(MessageModal, {
      props: { ...defaultProps, messages },
      global: {
        stubs: {
          MessageList: MessageListStub
        }
      }
    })

    const messageList = wrapper.findComponent(MessageListStub)
    expect(messageList.exists()).toBe(true)
    // Verify messages prop is passed (structure is validated by MessageList's own tests)
    expect(messageList.props('messages').length).toBe(1)
  })

  it('uses MessageInput with modal position', () => {
    const wrapper = mount(MessageModal, { props: defaultProps })

    const messageInput = wrapper.findComponent(MessageInput)
    expect(messageInput.exists()).toBe(true)
    expect(messageInput.props('jobId')).toBe('test-job-1')
    expect(messageInput.props('position')).toBe('modal')
  })

  it('displays agent name in title', () => {
    const wrapper = mount(MessageModal, {
      props: { ...defaultProps, agentName: 'My Agent' }
    })
    expect(wrapper.text()).toContain('My Agent')
  })

  it('emits close event on X button', async () => {
    const wrapper = mount(MessageModal, { props: defaultProps })

    const closeBtn = wrapper.find('[data-testid="close-button"]')
    await closeBtn.trigger('click')

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits message-sent event from MessageInput', async () => {
    const wrapper = mount(MessageModal, { props: defaultProps })

    const messageInput = wrapper.findComponent(MessageInput)
    await messageInput.vm.$emit('message-sent', { content: 'Test message' })

    expect(wrapper.emitted('message-sent')).toBeTruthy()
  })
})
