/**
 * Test Suite: JobsTab Message Counters
 *
 * Handover 0387g: Tests for per-agent message counter display
 *
 * Post-refactor: Message counters are now server-provided fields on agent objects
 * (messages_sent_count, messages_waiting_count, messages_read_count) rather than
 * client-side computation from messages arrays.
 *
 * The JobsTab component only exposes getMessagesWaiting(agent) and displays
 * messages_waiting_count in the table. The getMessagesSent and getMessagesRead
 * methods no longer exist on JobsTab. The table header shows "Messages Waiting"
 * (not "Messages Sent" or "Messages Read").
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import JobsTab from '@/components/projects/JobsTab.vue'

const vuetify = createVuetify()

// Mock API service
vi.mock('@/services/api', () => ({
  default: {
    prompts: {
      agentPrompt: vi.fn().mockResolvedValue({
        data: { prompt: 'Mock prompt text' }
      }),
      implementation: vi.fn(),
    },
    projects: {
      launchImplementation: vi.fn(),
    },
  },
}))

// Mock toast composable
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn(),
  }),
}))

// Mock useAgentJobs composable
vi.mock('@/composables/useAgentJobs', () => ({
  useAgentJobs: () => ({
    sortedJobs: { value: [] },
    loadJobs: vi.fn(),
    store: {
      getJob: vi.fn(),
    },
  })
}))

// Mock WebSocket store
vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: () => ({
    on: vi.fn(() => vi.fn()),
    off: vi.fn(),
    isConnected: { value: false },
  }),
}))

describe('JobsTab Message Counters', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  const mountJobsTab = () => {
    return mount(JobsTab, {
      props: {
        project: {
          project_id: 'proj-123',
          name: 'Test Project',
          description: 'Test',
        },
      },
      global: {
        plugins: [pinia, vuetify],
        stubs: {
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
          'v-snackbar': true,
          'AgentDetailsModal': true,
          'AgentJobModal': true,
          'MessageAuditModal': true,
          'CloseoutModal': true,
          'HandoverModal': true,
        },
      },
    })
  }

  describe('Message Counter Display', () => {
    it('renders Messages Waiting table header', () => {
      const wrapper = mountJobsTab()
      const headers = wrapper.findAll('th')
      const headerTexts = headers.map(h => h.text())

      expect(headerTexts).toContain('Messages Waiting')
    })

    it('does NOT render Messages Sent or Messages Read headers (server-side counters only)', () => {
      const wrapper = mountJobsTab()
      const headers = wrapper.findAll('th')
      const headerTexts = headers.map(h => h.text())

      // These headers are on AgentTableView, not JobsTab
      // JobsTab only shows "Messages Waiting" in its own table
      expect(headerTexts).not.toContain('Messages Sent')
      expect(headerTexts).not.toContain('Messages Read')
    })
  })

  describe('getMessagesWaiting Method', () => {
    it('returns messages_waiting_count from agent object', () => {
      const wrapper = mountJobsTab()
      const vm = wrapper.vm

      expect(vm.getMessagesWaiting({ messages_waiting_count: 5 })).toBe(5)
    })

    it('returns 0 when messages_waiting_count is undefined', () => {
      const wrapper = mountJobsTab()
      const vm = wrapper.vm

      expect(vm.getMessagesWaiting({})).toBe(0)
    })

    it('returns 0 when agent is null', () => {
      const wrapper = mountJobsTab()
      const vm = wrapper.vm

      expect(vm.getMessagesWaiting(null)).toBe(0)
    })

    it('returns 0 when messages_waiting_count is null', () => {
      const wrapper = mountJobsTab()
      const vm = wrapper.vm

      expect(vm.getMessagesWaiting({ messages_waiting_count: null })).toBe(0)
    })

    it('returns correct count for various values', () => {
      const wrapper = mountJobsTab()
      const vm = wrapper.vm

      expect(vm.getMessagesWaiting({ messages_waiting_count: 0 })).toBe(0)
      expect(vm.getMessagesWaiting({ messages_waiting_count: 1 })).toBe(1)
      expect(vm.getMessagesWaiting({ messages_waiting_count: 10 })).toBe(10)
    })
  })

  describe('Counter Reactivity', () => {
    it('component mounts without error', () => {
      const wrapper = mountJobsTab()
      expect(wrapper.exists()).toBe(true)
    })

    it('getMessagesWaiting is a function on the vm', () => {
      const wrapper = mountJobsTab()
      expect(typeof wrapper.vm.getMessagesWaiting).toBe('function')
    })
  })

  describe('Integration with Server-Provided Counters', () => {
    it('counter values come from agent object fields, not client-side computation', () => {
      const wrapper = mountJobsTab()
      const vm = wrapper.vm

      // Server provides these fields directly
      const agent = {
        messages_sent_count: 10,
        messages_waiting_count: 3,
        messages_read_count: 7,
      }

      // Only getMessagesWaiting is exposed on JobsTab
      expect(vm.getMessagesWaiting(agent)).toBe(3)
    })

    it('handles agent with all zero counters', () => {
      const wrapper = mountJobsTab()
      const vm = wrapper.vm

      const agent = {
        messages_sent_count: 0,
        messages_waiting_count: 0,
        messages_read_count: 0,
      }

      expect(vm.getMessagesWaiting(agent)).toBe(0)
    })
  })
})
