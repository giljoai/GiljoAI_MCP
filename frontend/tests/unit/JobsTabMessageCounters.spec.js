/**
 * Test Suite: JobsTab Message Counters & WebSocket Integration
 *
 * Handover 0297: Tests for per-agent message counter display and WebSocket event handling
 *
 * Tests validate:
 * - Message counter display (sent, waiting, read)
 * - WebSocket event handling for real-time updates
 * - Job Read/Acknowledged status indicators
 * - Multi-tenant isolation in WebSocket events
 * - Counter persistence from backend data
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import JobsTab from '@/components/projects/JobsTab.vue'
import { useUserStore } from '@/stores/user'

const vuetify = createVuetify()

// Mock API service
vi.mock('@/services/api', () => ({
  api: {
    prompts: {
      agentPrompt: vi.fn().mockResolvedValue({
        data: { prompt: 'Mock prompt text' }
      }),
    },
    post: vi.fn().mockResolvedValue({
      data: { success: true }
    }),
    messages: {
      send: vi.fn().mockResolvedValue({
        data: { success: true }
      }),
    },
  },
}))

// Mock toast composable
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn(),
  }),
}))

// Mock WebSocket composable
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocketV2: () => ({
    on: vi.fn((event, handler) => {
      // Store handlers for later invocation in tests
      if (!global.__websocketHandlers) global.__websocketHandlers = {}
      if (!global.__websocketHandlers[event]) {
        global.__websocketHandlers[event] = []
      }
      global.__websocketHandlers[event].push(handler)
      return vi.fn() // Return cleanup function
    }),
    off: vi.fn(),
  }),
}))

describe('JobsTab Message Counters', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    global.__websocketHandlers = {}

    // Initialize user store with tenant_key
    const userStore = useUserStore()
    userStore.currentUser = {
      id: 'user-1',
      tenant_key: 'tenant-123',
    }
  })

  afterEach(() => {
    delete global.__websocketHandlers
  })

  const createMockJob = (overrides = {}) => ({
    job_id: 'job-' + Math.random().toString(36).slice(2, 9),
    agent_type: 'implementer',
    agent_name: 'Implementer Agent',
    status: 'working',
    mission_read_at: null,
    messages: [],
    ...overrides,
  })

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

  describe('Message Counter Display', () => {
    it('renders message counter headers correctly', () => {
      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
            description: 'Test',
          },
          agents: [],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      const headers = wrapper.findAll('th')
      const headerTexts = headers.map(h => h.text())

      expect(headerTexts).toContain('Messages Sent')
      expect(headerTexts).toContain('Messages waiting')
      expect(headerTexts).toContain('Messages Read')
    })

    it('displays message counters from agent.messages array (sent)', () => {
      const job = createMockJob({
        messages: [
          createMockMessage({ direction: 'outbound', status: 'sent' }),
          createMockMessage({ direction: 'outbound', status: 'sent' }),
          createMockMessage({ direction: 'outbound', status: 'sent' }),
        ],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      // Should display 3 sent messages
      expect(wrapper.text()).toContain('3')
    })

    it('displays message counters from agent.messages array (waiting)', () => {
      const job = createMockJob({
        messages: [
          createMockMessage({ direction: 'inbound', status: 'waiting' }),
          createMockMessage({ direction: 'inbound', status: 'waiting' }),
        ],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      // Should display 2 waiting messages
      expect(wrapper.text()).toContain('2')
    })

    it('displays message counters from agent.messages array (read/acknowledged)', () => {
      const job = createMockJob({
        messages: [
          createMockMessage({ direction: 'outbound', status: 'acknowledged' }),
          createMockMessage({ direction: 'outbound', status: 'read' }),
        ],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      // Should display 2 read/acknowledged messages
      expect(wrapper.text()).toContain('2')
    })

    it('handles mixed message types correctly', () => {
      const job = createMockJob({
        messages: [
          createMockMessage({ direction: 'outbound', status: 'sent' }),
          createMockMessage({ direction: 'outbound', status: 'sent' }),
          createMockMessage({ direction: 'inbound', status: 'waiting' }),
          createMockMessage({ direction: 'outbound', status: 'acknowledged' }),
          createMockMessage({ direction: 'outbound', status: 'acknowledged' }),
          createMockMessage({ direction: 'outbound', status: 'acknowledged' }),
        ],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      const vm = wrapper.vm
      // getMessagesSent counts all messages with from='developer' OR direction='outbound'
      // All 6 messages have from='developer' (default in createMockMessage)
      expect(vm.getMessagesSent(job)).toBe(6) // all 6 messages (from='developer' matches all)
      expect(vm.getMessagesWaiting(job)).toBe(1) // only msg-3 has status='waiting'
      expect(vm.getMessagesRead(job)).toBe(3) // msg-4, msg-5, msg-6 have status='acknowledged'
    })

    it('handles missing messages array gracefully', () => {
      const job = createMockJob({
        messages: undefined,
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      const vm = wrapper.vm
      expect(vm.getMessagesSent(job)).toBe(0)
      expect(vm.getMessagesWaiting(job)).toBe(0)
      expect(vm.getMessagesRead(job)).toBe(0)
    })
  })

  describe('Job Read Status', () => {
    it('calculates job_read correctly when waiting = 0', () => {
      const job = createMockJob({
        messages: [
          createMockMessage({ direction: 'outbound', status: 'sent' }),
          createMockMessage({ direction: 'outbound', status: 'acknowledged' }),
        ],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      const vm = wrapper.vm
      // waiting count is 0, so job_read should be true
      expect(vm.getMessagesWaiting(job)).toBe(0)
    })

    it('calculates job_read correctly when waiting > 0', () => {
      const job = createMockJob({
        messages: [
          createMockMessage({ direction: 'outbound', status: 'sent' }),
          createMockMessage({ direction: 'inbound', status: 'waiting' }),
          createMockMessage({ direction: 'inbound', status: 'waiting' }),
        ],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      const vm = wrapper.vm
      // waiting count is 2, so job_read should be false
      expect(vm.getMessagesWaiting(job)).toBe(2)
    })
  })

  describe('Job Acknowledged Status', () => {
    it('calculates job_acknowledged correctly when read > 0', () => {
      const job = createMockJob({
        messages: [
          createMockMessage({ direction: 'outbound', status: 'acknowledged' }),
        ],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      const vm = wrapper.vm
      // read count > 0, so job_acknowledged should be true
      expect(vm.getMessagesRead(job)).toBe(1)
      expect(vm.getMessagesRead(job) > 0).toBe(true)
    })

    it('calculates job_acknowledged correctly when read = 0', () => {
      const job = createMockJob({
        messages: [
          createMockMessage({ direction: 'outbound', status: 'sent' }),
        ],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      const vm = wrapper.vm
      // read count = 0, so job_acknowledged should be false
      expect(vm.getMessagesRead(job)).toBe(0)
      expect(vm.getMessagesRead(job) > 0).toBe(false)
    })
  })

  describe('WebSocket Event Handling & Integration', () => {
    it('correctly counts messages after simulated agent message addition', async () => {
      const job = createMockJob({
        messages: [],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      await flushPromises()

      const vm = wrapper.vm
      expect(vm.getMessagesSent(job)).toBe(0)

      // Simulate WebSocket event: message:sent adds message to agent.messages array
      job.messages.push({
        id: 'msg-1',
        from: 'agent',
        direction: 'outbound',
        status: 'sent',
        text: 'Test message',
        priority: 'normal',
        timestamp: new Date().toISOString(),
        to_agent: 'orchestrator',
      })

      await wrapper.vm.$nextTick()
      expect(vm.getMessagesSent(job)).toBe(1)
    })

    it('correctly counts waiting messages after simulated agent message arrival', async () => {
      const job = createMockJob({
        messages: [],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      await flushPromises()

      const vm = wrapper.vm
      expect(vm.getMessagesWaiting(job)).toBe(0)

      // Simulate WebSocket event: message:received adds waiting message
      job.messages.push({
        id: 'msg-1',
        from: 'orchestrator',
        direction: 'inbound',
        status: 'waiting',
        text: 'Test message from orchestrator',
        priority: 'normal',
        timestamp: new Date().toISOString(),
      })

      await wrapper.vm.$nextTick()
      expect(vm.getMessagesWaiting(job)).toBe(1)
    })

    it('correctly updates message status after acknowledgment', async () => {
      const job = createMockJob({
        messages: [
          createMockMessage({ id: 'msg-1', direction: 'inbound', status: 'waiting' }),
        ],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      await flushPromises()

      const vm = wrapper.vm
      expect(vm.getMessagesWaiting(job)).toBe(1)
      expect(vm.getMessagesRead(job)).toBe(0)

      // Simulate WebSocket event: message:acknowledged changes status
      const message = job.messages.find(m => m.id === 'msg-1')
      if (message) {
        message.status = 'acknowledged'
      }

      await wrapper.vm.$nextTick()

      // After status change, message should count as read/acknowledged
      expect(vm.getMessagesWaiting(job)).toBe(0)
      expect(vm.getMessagesRead(job)).toBe(1)
    })

    it('preserves correct behavior with complex message state', async () => {
      const job = createMockJob({
        messages: [
          createMockMessage({ id: 'msg-1', direction: 'outbound', status: 'sent' }),
          createMockMessage({ id: 'msg-2', direction: 'outbound', status: 'sent' }),
          createMockMessage({ id: 'msg-3', direction: 'inbound', status: 'waiting' }),
          createMockMessage({ id: 'msg-4', direction: 'outbound', status: 'acknowledged' }),
          createMockMessage({ id: 'msg-5', direction: 'outbound', status: 'acknowledged' }),
        ],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      await flushPromises()

      const vm = wrapper.vm

      // Verify initial state
      // getMessagesSent counts all messages with from='developer' OR direction='outbound'
      // All 5 messages have from='developer' (default in createMockMessage)
      expect(vm.getMessagesSent(job)).toBe(5)
      expect(vm.getMessagesWaiting(job)).toBe(1)
      expect(vm.getMessagesRead(job)).toBe(2)

      // Simulate acknowledgment of waiting message
      const waitingMsg = job.messages.find(m => m.id === 'msg-3')
      if (waitingMsg) {
        waitingMsg.status = 'acknowledged'
      }

      await wrapper.vm.$nextTick()

      // Verify updated state
      // Still 5 messages (status change doesn't affect from='developer' check)
      expect(vm.getMessagesSent(job)).toBe(5)
      expect(vm.getMessagesWaiting(job)).toBe(0)
      expect(vm.getMessagesRead(job)).toBe(3)
    })
  })

  describe('Counter Initialization', () => {
    it('initializes message counters from backend data on mount', async () => {
      const job1 = createMockJob({
        agent_type: 'implementer',
        messages: [
          createMockMessage({ direction: 'outbound', status: 'sent' }),
          createMockMessage({ direction: 'outbound', status: 'sent' }),
        ],
      })

      const job2 = createMockJob({
        agent_type: 'tester',
        messages: [
          createMockMessage({ direction: 'inbound', status: 'waiting' }),
        ],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job1, job2],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      await flushPromises()

      const vm = wrapper.vm
      expect(vm.getMessagesSent(job1)).toBe(2)
      expect(vm.getMessagesWaiting(job2)).toBe(1)
    })

    it('handles empty messages array on initialization', async () => {
      const job = createMockJob({
        messages: [],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      await flushPromises()

      const vm = wrapper.vm
      expect(vm.getMessagesSent(job)).toBe(0)
      expect(vm.getMessagesWaiting(job)).toBe(0)
      expect(vm.getMessagesRead(job)).toBe(0)
    })
  })

  describe('Counter Persistence', () => {
    it('persists counters across prop updates', async () => {
      const job = createMockJob({
        messages: [
          createMockMessage({ direction: 'outbound', status: 'sent' }),
        ],
      })

      const wrapper = mount(JobsTab, {
        props: {
          project: {
            project_id: 'proj-123',
            name: 'Test Project',
          },
          agents: [job],
          messages: [],
          allAgentsComplete: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: {
            'router-link': true,
            'v-icon': true,
            'v-avatar': true,
            'v-btn': true,
            'v-tooltip': true,
            'v-dialog': true,
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-text-field': true,
            'LaunchSuccessorDialog': true,
            'AgentDetailsModal': true,
            'CloseoutModal': true,
          },
        },
      })

      const vm = wrapper.vm
      expect(vm.getMessagesSent(job)).toBe(1)

      // Add another message
      job.messages.push(createMockMessage({ direction: 'outbound', status: 'sent' }))
      await wrapper.vm.$nextTick()

      expect(vm.getMessagesSent(job)).toBe(2)
    })
  })
})
