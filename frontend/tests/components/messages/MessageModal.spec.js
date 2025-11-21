import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import MessageModal from '@/components/messages/MessageModal.vue'
import MessageList from '@/components/messages/MessageList.vue'
import MessageInput from '@/components/projects/MessageInput.vue'

describe('MessageModal (Handover 0231 Phase 3)', () => {
  const defaultProps = {
    isOpen: true,
    jobId: 'test-job-1',
    agentName: 'Test Agent',
    messages: []
  }

  it('renders when isOpen is true', () => {
    const wrapper = mount(MessageModal, { props: defaultProps })
    expect(wrapper.findComponent({ name: 'VDialog' }).exists()).toBe(true)
  })

  it('uses MessageList component', () => {
    const messages = [{ id: 1, content: 'Test', status: 'pending' }]
    const wrapper = mount(MessageModal, {
      props: { ...defaultProps, messages }
    })

    const messageList = wrapper.findComponent(MessageList)
    expect(messageList.exists()).toBe(true)
    expect(messageList.props('messages')).toEqual(messages)
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
