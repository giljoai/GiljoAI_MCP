/**
 * JobsTab.0331.spec.js
 *
 * Handover 0331: Message Audit Modal baseline
 *
 * Tests focus on JobsTab behavior:
 * - Clicking the folder icon opens MessageAuditModal.
 * - The modal receives the correct agent and messages.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import JobsTab from '@/components/projects/JobsTab.vue'
import { useUserStore } from '@/stores/user'

const vuetify = createVuetify()

// Mock API service (only methods used by JobsTab in this test)
vi.mock('@/services/api', () => ({
  api: {
    prompts: {
      agentPrompt: vi.fn().mockResolvedValue({
        data: { prompt: 'Mock prompt text' },
      }),
    },
    post: vi.fn().mockResolvedValue({
      data: { success: true },
    }),
    messages: {
      sendUnified: vi.fn().mockResolvedValue({
        data: { success: true },
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

// Mock WebSocket composable (no-op handlers for this test)
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocketV2: () => ({
    on: vi.fn(),
    off: vi.fn(),
  }),
}))

const createMockJob = (overrides = {}) => ({
  job_id: 'job-' + Math.random().toString(36).slice(2, 9),
  agent_type: 'implementer',
  agent_name: 'Implementer Agent',
  status: 'working',
  mission_read_at: null,
  mission_acknowledged_at: null,
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

describe('JobsTab MessageAuditModal integration (0331)', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)

    // Initialize user store with tenant_key
    const userStore = useUserStore()
    userStore.currentUser = {
      id: 'user-1',
      tenant_key: 'tenant-123',
    }
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('opens MessageAuditModal with selected agent when folder button is clicked', async () => {
    const job = createMockJob({
      messages: [
        createMockMessage({ text: 'message-1' }),
        createMockMessage({ text: 'message-2' }),
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
          // Forward activator slot so buttons are rendered inside tooltips
          'v-tooltip': {
            template: '<div><slot name="activator" :props="{}" /><slot /></div>',
          },
          'v-dialog': true,
          'v-card': true,
          'v-card-title': true,
          'v-card-text': true,
          'v-card-actions': true,
          'v-spacer': true,
          'v-text-field': true,
          LaunchSuccessorDialog: true,
          AgentDetailsModal: true,
          CloseoutModal: true,
          // Stub the audit modal so we can assert props/visibility
          MessageAuditModal: {
            props: ['show', 'agent', 'initialTab', 'steps'],
            template: `
              <div v-if="show" data-test="message-audit-modal">
                <span data-test="modal-agent-id">{{ agent.job_id }}</span>
                <span data-test="modal-message-count">{{ agent.messages.length }}</span>
                <span data-test="modal-initial-tab">{{ initialTab }}</span>
                <span data-test="modal-steps">
                  {{ steps && steps.completed }} / {{ steps && steps.total }}
                </span>
              </div>
            `,
          },
        },
      },
    })

    // Click the folder button for the first agent
    const folderButton = wrapper.get('[data-testid="jobs-folder-btn"]')
    await folderButton.trigger('click')
    await flushPromises()

    const modal = wrapper.get('[data-test="message-audit-modal"]')
    expect(modal.exists()).toBe(true)

    expect(modal.get('[data-test="modal-agent-id"]').text()).toBe(job.job_id)
    expect(modal.get('[data-test="modal-message-count"]').text()).toBe(
      String(job.messages.length),
    )
    expect(modal.get('[data-test="modal-initial-tab"]').text()).toBe('waiting')
  })

  it('opens MessageAuditModal with Plan tab and steps summary when Steps cell is clicked', async () => {
    const job = createMockJob({
      steps: { total: 4, completed: 2 },
      messages: [
        createMockMessage({ text: 'plan-1', message_type: 'plan' }),
        createMockMessage({ text: 'regular-1' }),
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
          'v-tooltip': {
            template: '<div><slot name="activator" :props="{}" /><slot /></div>',
          },
          'v-dialog': true,
          'v-card': true,
          'v-card-title': true,
          'v-card-text': true,
          'v-card-actions': true,
          'v-spacer': true,
          'v-text-field': true,
          LaunchSuccessorDialog: true,
          AgentDetailsModal: true,
          CloseoutModal: true,
          MessageAuditModal: {
            props: ['show', 'agent', 'initialTab', 'steps'],
            template: `
              <div v-if="show" data-test="message-audit-modal">
                <span data-test="modal-agent-id">{{ agent.job_id }}</span>
                <span data-test="modal-message-count">{{ agent.messages.length }}</span>
                <span data-test="modal-initial-tab">{{ initialTab }}</span>
                <span data-test="modal-steps">
                  {{ steps && steps.completed }} / {{ steps && steps.total }}
                </span>
              </div>
            `,
          },
        },
      },
    })

    // Click the Steps cell trigger
    const stepsTrigger = wrapper.get('[data-testid="steps-trigger"]')
    await stepsTrigger.trigger('click')
    await flushPromises()

    const modal = wrapper.get('[data-test="message-audit-modal"]')
    expect(modal.exists()).toBe(true)

    expect(modal.get('[data-test="modal-agent-id"]').text()).toBe(job.job_id)
    expect(modal.get('[data-test="modal-message-count"]').text()).toBe(
      String(job.messages.length),
    )
    expect(modal.get('[data-test="modal-initial-tab"]').text()).toBe('plan')
    expect(modal.get('[data-test="modal-steps"]').text().trim()).toBe('2 / 4')
  })
})
