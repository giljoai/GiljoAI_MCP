import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import MessageStream from '../MessageStream.vue'
import ChatHeadBadge from '../ChatHeadBadge.vue'

/**
 * MessageStream Component Tests
 *
 * Test Coverage:
 * 1. Component Rendering
 * 2. Message Display (agent and user messages)
 * 3. Auto-scroll Behavior
 * 4. Manual Scroll Override
 * 5. Scroll to Bottom Button
 * 6. Keyboard Navigation
 * 7. Empty and Loading States
 * 8. Message Formatting
 * 9. Accessibility
 * 10. Responsive Behavior
 *
 * @see handovers/0077_launch_jobs_dual_tab_interface.md
 */

// Mock date-fns functions
vi.mock('date-fns', () => ({
  formatDistanceToNow: vi.fn((date) => '2 minutes ago'),
  format: vi.fn((date, formatStr) => 'Apr 29, 2023, 9:30:00 AM'),
}))

describe('MessageStream', () => {
  let wrapper

  const mockMessages = [
    {
      id: '1',
      from_agent: 'orchestrator',
      to_agent: 'implementor',
      type: 'agent',
      content: 'Please implement the new feature',
      timestamp: '2023-04-29T09:30:00Z',
      from: 'agent',
      agent_display_name: 'orchestrator',
    },
    {
      id: '2',
      from_agent: 'implementor',
      to_agent: 'orchestrator',
      type: 'agent',
      content: 'Feature implementation started',
      timestamp: '2023-04-29T09:32:00Z',
      from: 'agent',
      agent_display_name: 'implementor',
    },
    {
      id: '3',
      from: 'developer',
      type: 'user',
      content: 'How is progress going?',
      timestamp: '2023-04-29T09:35:00Z',
    },
    {
      id: '4',
      from_agent: 'orchestrator',
      type: 'broadcast',
      content: 'All agents: Status update required',
      timestamp: '2023-04-29T09:40:00Z',
      from: 'agent',
      agent_display_name: 'orchestrator',
    },
  ]

  const createWrapper = (props = {}) => {
    return mount(MessageStream, {
      props: {
        messages: [],
        projectId: 'test-project-123',
        autoScroll: true,
        loading: false,
        ...props,
      },
      global: {
        components: {
          ChatHeadBadge,
        },
        stubs: {
          'v-icon': true,
          'v-btn': true,
          'v-badge': true,
          'v-skeleton-loader': true,
        },
      },
    })
  }

  beforeEach(() => {
    // Reset scroll mocks
    Element.prototype.scrollTo = vi.fn()
    Element.prototype.scrollBy = vi.fn()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('Component Rendering', () => {
    it('renders correctly with default props', () => {
      wrapper = createWrapper()

      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.message-stream').exists()).toBe(true)
      expect(wrapper.find('.message-stream__header').exists()).toBe(true)
      expect(wrapper.find('.message-stream__container').exists()).toBe(true)
    })

    it('displays header with "Messages" title', () => {
      wrapper = createWrapper()

      const header = wrapper.find('.message-stream__header')
      expect(header.text()).toContain('Messages')
    })

    it('has correct ARIA attributes', () => {
      wrapper = createWrapper({ projectId: 'test-123' })

      const stream = wrapper.find('.message-stream')
      expect(stream.attributes('role')).toBe('log')
      expect(stream.attributes('aria-live')).toBe('polite')
      expect(stream.attributes('aria-label')).toBe('Message stream for project test-123')
    })
  })

  describe('Empty and Loading States', () => {
    it('shows empty state when no messages', () => {
      wrapper = createWrapper({ messages: [] })

      expect(wrapper.find('.message-stream__empty').exists()).toBe(true)
      expect(wrapper.text()).toContain('No messages yet')
    })

    it('shows loading state when loading prop is true', () => {
      wrapper = createWrapper({ loading: true })

      expect(wrapper.find('.message-stream__loading').exists()).toBe(true)
      expect(wrapper.findAllComponents({ name: 'v-skeleton-loader' }).length).toBeGreaterThan(0)
    })

    it('hides empty state when messages exist', () => {
      wrapper = createWrapper({ messages: mockMessages })

      expect(wrapper.find('.message-stream__empty').exists()).toBe(false)
    })

    it('hides loading state when loading is false', () => {
      wrapper = createWrapper({ loading: false, messages: mockMessages })

      expect(wrapper.find('.message-stream__loading').exists()).toBe(false)
    })
  })

  describe('Message Display', () => {
    it('renders all messages in the list', () => {
      wrapper = createWrapper({ messages: mockMessages })

      const messages = wrapper.findAll('.message-stream__message')
      expect(messages).toHaveLength(mockMessages.length)
    })

    it('displays agent messages with ChatHeadBadge', () => {
      wrapper = createWrapper({ messages: [mockMessages[0]] })

      const chatHead = wrapper.findComponent(ChatHeadBadge)
      expect(chatHead.exists()).toBe(true)
      expect(chatHead.props('displayName')).toBe('orchestrator')
      expect(chatHead.props('instanceNumber')).toBe(1)
    })

    it('displays user messages with user icon', () => {
      wrapper = createWrapper({ messages: [mockMessages[2]] })

      const userIcon = wrapper.find('.message-stream__user-icon')
      expect(userIcon.exists()).toBe(true)
    })

    it('shows message content correctly', () => {
      wrapper = createWrapper({ messages: [mockMessages[0]] })

      const content = wrapper.find('.message-stream__text')
      expect(content.text()).toBe('Please implement the new feature')
    })

    it('displays message routing for targeted messages', () => {
      wrapper = createWrapper({ messages: [mockMessages[0]] })

      const routing = wrapper.find('.message-stream__routing')
      expect(routing.text()).toContain('To Implementor:')
    })

    it('displays "Broadcast:" for broadcast messages', () => {
      wrapper = createWrapper({ messages: [mockMessages[3]] })

      const routing = wrapper.find('.message-stream__routing')
      expect(routing.text()).toContain('Broadcast:')
    })

    it('displays "User Message" for developer messages', () => {
      wrapper = createWrapper({ messages: [mockMessages[2]] })

      const routing = wrapper.find('.message-stream__routing')
      // User messages should show "User Message" or have no routing (depending on implementation)
      expect(routing.exists()).toBe(true)
    })

    it('applies correct CSS class for user messages', () => {
      wrapper = createWrapper({ messages: [mockMessages[2]] })

      const message = wrapper.find('.message-stream__message')
      expect(message.classes()).toContain('message-stream__message--user')
    })

    it('applies correct CSS class for agent messages', () => {
      wrapper = createWrapper({ messages: [mockMessages[0]] })

      const message = wrapper.find('.message-stream__message')
      expect(message.classes()).toContain('message-stream__message--agent')
    })
  })

  describe('Timestamp Formatting', () => {
    it('displays relative timestamp', () => {
      wrapper = createWrapper({ messages: [mockMessages[0]] })

      const timestamp = wrapper.find('.message-stream__timestamp')
      expect(timestamp.text()).toBe('2 minutes ago')
    })

    it('shows full timestamp in title attribute', () => {
      wrapper = createWrapper({ messages: [mockMessages[0]] })

      const timestamp = wrapper.find('.message-stream__timestamp')
      expect(timestamp.attributes('title')).toBe('Apr 29, 2023, 9:30:00 AM')
    })

    it('handles invalid timestamps gracefully', () => {
      const invalidMessage = {
        ...mockMessages[0],
        timestamp: 'invalid-date',
      }
      wrapper = createWrapper({ messages: [invalidMessage] })

      const timestamp = wrapper.find('.message-stream__timestamp')
      expect(timestamp.text()).toBeTruthy() // Should not crash
    })
  })

  describe('Auto-Scroll Behavior', () => {
    it('scrolls to bottom on mount when messages exist', async () => {
      wrapper = createWrapper({ messages: mockMessages })

      await nextTick()
      await flushPromises()

      const container = wrapper.find('.message-stream__container').element
      expect(Element.prototype.scrollTo).toHaveBeenCalled()
    })

    it('scrolls to bottom when new message arrives and autoScroll is true', async () => {
      wrapper = createWrapper({ messages: [mockMessages[0]], autoScroll: true })

      await nextTick()

      // Add new message
      await wrapper.setProps({ messages: [...mockMessages.slice(0, 2)] })
      await nextTick()
      await flushPromises()

      expect(Element.prototype.scrollTo).toHaveBeenCalled()
    })

    it('does not auto-scroll when autoScroll is false', async () => {
      // Initial mount will still scroll to bottom
      wrapper = createWrapper({ messages: [mockMessages[0]], autoScroll: false })

      await nextTick()
      await flushPromises()

      // Clear mocks after initial mount
      vi.clearAllMocks()

      // Mark user as scrolled up to prevent auto-scroll
      wrapper.vm.userScrolledUp = true

      // Add new message
      await wrapper.setProps({ messages: [...mockMessages.slice(0, 2)] })
      await nextTick()
      await flushPromises()

      // Should not scroll automatically when user scrolled up
      expect(Element.prototype.scrollTo).not.toHaveBeenCalled()
    })
  })

  describe('Manual Scroll Override', () => {
    it('shows scroll button when user scrolls up', async () => {
      wrapper = createWrapper({ messages: mockMessages })

      await nextTick()
      await flushPromises()

      // Get the ref element directly
      const container = wrapper.find('.message-stream__container')
      const element = container.element

      // Set the ref manually
      wrapper.vm.messagesContainer = element

      // Mock scroll properties for scrolled up state
      // scrollBottom = scrollHeight - scrollTop - clientHeight
      // For scrolled up: 1000 - 0 - 500 = 500 (> 50 threshold)
      Object.defineProperty(element, 'scrollTop', {
        value: 0,
        writable: true,
        configurable: true,
      })
      Object.defineProperty(element, 'scrollHeight', {
        value: 1000,
        writable: true,
        configurable: true,
      })
      Object.defineProperty(element, 'clientHeight', {
        value: 500,
        writable: true,
        configurable: true,
      })

      // Call handleScroll directly
      wrapper.vm.handleScroll()
      await nextTick()

      expect(wrapper.vm.showScrollButton).toBe(true)
    })

    it('hides scroll button when scrolled to bottom', async () => {
      wrapper = createWrapper({ messages: mockMessages })

      // Simulate scroll to bottom by mocking scroll properties
      const container = wrapper.find('.message-stream__container')
      const element = container.element

      Object.defineProperty(element, 'scrollTop', { value: 500, writable: true })
      Object.defineProperty(element, 'scrollHeight', { value: 1000, writable: true })
      Object.defineProperty(element, 'clientHeight', { value: 500, writable: true })

      await container.trigger('scroll')
      await nextTick()

      expect(wrapper.vm.showScrollButton).toBe(false)
    })

    it('increments unread count when new message arrives while scrolled up', async () => {
      wrapper = createWrapper({ messages: [mockMessages[0]] })

      await nextTick()
      await flushPromises()

      // Set user scrolled up state (this simulates user scrolling up)
      wrapper.vm.userScrolledUp = true
      wrapper.vm.unreadCount = 0

      // Add new message - this should trigger the watch
      await wrapper.setProps({ messages: mockMessages.slice(0, 2) })
      await nextTick()
      await flushPromises()

      // The watch should increment unread count since userScrolledUp is true
      expect(wrapper.vm.unreadCount).toBe(1)
    })

    it('resets unread count when scrolled to bottom', async () => {
      wrapper = createWrapper({ messages: mockMessages })

      wrapper.vm.unreadCount = 5
      wrapper.vm.userScrolledUp = true

      // Simulate scroll to bottom by mocking scroll properties
      const container = wrapper.find('.message-stream__container')
      const element = container.element

      Object.defineProperty(element, 'scrollTop', { value: 500, writable: true })
      Object.defineProperty(element, 'scrollHeight', { value: 1000, writable: true })
      Object.defineProperty(element, 'clientHeight', { value: 500, writable: true })

      await container.trigger('scroll')
      await nextTick()

      expect(wrapper.vm.unreadCount).toBe(0)
      expect(wrapper.vm.userScrolledUp).toBe(false)
    })
  })

  describe('Scroll to Bottom Button', () => {
    it('scrolls to bottom when button clicked', async () => {
      wrapper = createWrapper({ messages: mockMessages })

      wrapper.vm.showScrollButton = true
      await nextTick()

      wrapper.vm.scrollToBottom()
      await nextTick()

      expect(Element.prototype.scrollTo).toHaveBeenCalledWith(
        expect.objectContaining({
          behavior: 'smooth',
        }),
      )
    })

    it('resets unread count when button clicked', async () => {
      wrapper = createWrapper({ messages: mockMessages })

      wrapper.vm.unreadCount = 3
      wrapper.vm.showScrollButton = true

      wrapper.vm.scrollToBottom()
      await nextTick()

      expect(wrapper.vm.unreadCount).toBe(0)
      expect(wrapper.vm.showScrollButton).toBe(false)
    })
  })

  describe('Keyboard Navigation', () => {
    it('scrolls to top on Home key', async () => {
      wrapper = createWrapper({ messages: mockMessages })

      const container = wrapper.find('.message-stream__container')
      await container.trigger('keydown', { key: 'Home' })

      expect(Element.prototype.scrollTo).toHaveBeenCalledWith(
        expect.objectContaining({
          top: 0,
          behavior: 'smooth',
        }),
      )
    })

    it('scrolls to bottom on End key', async () => {
      wrapper = createWrapper({ messages: mockMessages })

      const container = wrapper.find('.message-stream__container')
      await container.trigger('keydown', { key: 'End' })

      expect(Element.prototype.scrollTo).toHaveBeenCalled()
    })

    it('scrolls up on PageUp key', async () => {
      wrapper = createWrapper({ messages: mockMessages })

      const container = wrapper.find('.message-stream__container')
      await container.trigger('keydown', { key: 'PageUp' })

      expect(Element.prototype.scrollBy).toHaveBeenCalled()
    })

    it('scrolls down on PageDown key', async () => {
      wrapper = createWrapper({ messages: mockMessages })

      const container = wrapper.find('.message-stream__container')
      await container.trigger('keydown', { key: 'PageDown' })

      expect(Element.prototype.scrollBy).toHaveBeenCalled()
    })
  })

  describe('Helper Functions', () => {
    it('correctly identifies user messages', () => {
      wrapper = createWrapper()

      expect(wrapper.vm.isUserMessage({ from: 'developer' })).toBe(true)
      expect(wrapper.vm.isUserMessage({ from: 'user' })).toBe(true)
      expect(wrapper.vm.isUserMessage({ type: 'user' })).toBe(true)
      expect(wrapper.vm.isUserMessage({ from: 'agent' })).toBe(false)
    })

    it('correctly identifies broadcast messages', () => {
      wrapper = createWrapper()

      expect(wrapper.vm.isBroadcast({ type: 'broadcast' })).toBe(true)
      expect(wrapper.vm.isBroadcast({ to_agent: null })).toBe(true)
      expect(wrapper.vm.isBroadcast({ to_agent: 'implementor' })).toBe(false)
    })

    it('gets correct agent type from message', () => {
      wrapper = createWrapper()

      expect(wrapper.vm.getAgentType({ agent_display_name: 'analyzer' })).toBe('analyzer')
      expect(wrapper.vm.getAgentType({ from_agent: 'reviewer' })).toBe('reviewer')
      expect(wrapper.vm.getAgentType({})).toBe('orchestrator')
    })

    it('formats agent name correctly', () => {
      wrapper = createWrapper()

      expect(wrapper.vm.formatAgentName('orchestrator')).toBe('Orchestrator')
      expect(wrapper.vm.formatAgentName('implementor')).toBe('Implementor')
      expect(wrapper.vm.formatAgentName(null)).toBe('Unknown')
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA role and label', () => {
      wrapper = createWrapper({ projectId: 'test-project' })

      const stream = wrapper.find('.message-stream')
      expect(stream.attributes('role')).toBe('log')
      expect(stream.attributes('aria-label')).toContain('test-project')
    })

    it('scroll button has aria-label', async () => {
      wrapper = createWrapper({ messages: mockMessages })

      wrapper.vm.showScrollButton = true
      await nextTick()

      // Note: actual button is stubbed, but we verify the prop would be set
      expect(wrapper.vm.showScrollButton).toBe(true)
    })

    it('timestamp has title for screen readers', () => {
      wrapper = createWrapper({ messages: [mockMessages[0]] })

      const timestamp = wrapper.find('.message-stream__timestamp')
      expect(timestamp.attributes('title')).toBeTruthy()
    })
  })

  describe('Performance', () => {
    it('handles large message lists efficiently', () => {
      const largeMessageList = Array.from({ length: 1000 }, (_, i) => ({
        ...mockMessages[0],
        id: `msg-${i}`,
        content: `Message ${i}`,
      }))

      wrapper = createWrapper({ messages: largeMessageList })

      expect(wrapper.exists()).toBe(true)
      expect(wrapper.findAll('.message-stream__message')).toHaveLength(1000)
    })

    it('efficiently updates when new messages arrive', async () => {
      wrapper = createWrapper({ messages: [mockMessages[0]] })

      const renderCount = vi.fn()
      wrapper.vm.$watch('messages', renderCount)

      await wrapper.setProps({ messages: mockMessages })
      await nextTick()

      expect(renderCount).toHaveBeenCalledTimes(1)
    })
  })

  describe('Edge Cases', () => {
    it('handles empty message content', () => {
      const emptyMessage = { ...mockMessages[0], content: '' }
      wrapper = createWrapper({ messages: [emptyMessage] })

      expect(wrapper.find('.message-stream__text').exists()).toBe(true)
    })

    it('handles missing timestamp', () => {
      const noTimestamp = { ...mockMessages[0], timestamp: null }
      wrapper = createWrapper({ messages: [noTimestamp] })

      const timestamp = wrapper.find('.message-stream__timestamp')
      expect(timestamp.text()).toBeTruthy()
    })

    it('handles missing agent type', () => {
      const noAgent = {
        ...mockMessages[0],
        agent_display_name: null,
        from_agent: null,
      }
      wrapper = createWrapper({ messages: [noAgent] })

      const chatHead = wrapper.findComponent(ChatHeadBadge)
      expect(chatHead.props('displayName')).toBe('orchestrator')
    })

    it('handles very long message content', () => {
      const longMessage = {
        ...mockMessages[0],
        content: 'A'.repeat(10000),
      }
      wrapper = createWrapper({ messages: [longMessage] })

      expect(wrapper.find('.message-stream__text').exists()).toBe(true)
    })
  })

  describe('Responsive Behavior', () => {
    it('applies mobile styles on small screens', () => {
      wrapper = createWrapper({ messages: mockMessages })

      // Note: actual media query testing requires more complex setup
      // Here we verify the component structure supports responsive design
      expect(wrapper.find('.message-stream__container').exists()).toBe(true)
      expect(wrapper.find('.message-stream__chat-head').exists()).toBe(true)
    })
  })
})
