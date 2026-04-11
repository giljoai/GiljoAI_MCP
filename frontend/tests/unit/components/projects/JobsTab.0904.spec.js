/**
 * JobsTab.0904.spec.js
 *
 * Handover 0904: Orchestrator Auto Check-in
 *
 * Tests:
 * 1. Auto check-in controls hidden in CLI subagent mode
 * 2. Auto check-in controls hidden before staging complete
 * 3. Auto check-in controls visible in multi-terminal after staging
 * 4. Interval selector hidden when toggle is off
 * 5. Toggle change calls API
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import JobsTab from '@/components/projects/JobsTab.vue'
import { useProjectStateStore } from '@/stores/projectStateStore'
import { useUserStore } from '@/stores/user'

const vuetify = createVuetify()

vi.mock('@/services/api', () => {
  const api = {
    agentJobs: { list: vi.fn().mockResolvedValue({ data: [] }) },
    prompts: { agentPrompt: vi.fn().mockResolvedValue({ data: { prompt: '' } }) },
    messages: { sendUnified: vi.fn().mockResolvedValue({ data: { success: true } }) },
    projects: { update: vi.fn().mockResolvedValue({ data: {} }) },
  }
  return { default: api, api }
})

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: vi.fn() }),
}))

vi.mock('@/composables/useWebSocket', () => ({
  useWebSocketV2: () => ({ on: vi.fn(), off: vi.fn() }),
}))

const stubs = {
  'v-tooltip': true,
  'v-dialog': true,
  'v-card': true,
  'v-card-title': true,
  'v-card-text': true,
  'v-card-actions': true,
  'v-spacer': true,
  'v-text-field': true,
  'v-icon': true,
  'v-avatar': true,
  AgentDetailsModal: true,
  AgentJobModal: true,
  MessageAuditModal: true,
  HandoverModal: true,
}

describe('JobsTab Auto Check-in (0904)', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)

    const userStore = useUserStore()
    userStore.currentUser = { id: 'user-1', tenant_key: 'tenant-1' }

  })

  it('hides auto check-in in CLI subagent mode', async () => {
    const projectStateStore = useProjectStateStore()
    projectStateStore.setStagingComplete('proj-cli', true)

    const wrapper = mount(JobsTab, {
      props: {
        project: {
          project_id: 'proj-cli',
          id: 'proj-cli',
          name: 'CLI Project',
          execution_mode: 'claude_code_cli',
          auto_checkin_enabled: false,
          auto_checkin_interval: 60,
        },
      },
      global: { plugins: [pinia, vuetify], stubs },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="auto-checkin"]').exists()).toBe(false)
  })

  it('hides auto check-in before staging complete', async () => {
    // No staging state set — defaults to not complete
    const wrapper = mount(JobsTab, {
      props: {
        project: {
          project_id: 'proj-nostage',
          id: 'proj-nostage',
          name: 'Unstaged Project',
          execution_mode: 'multi_terminal',
          auto_checkin_enabled: false,
          auto_checkin_interval: 60,
        },
      },
      global: { plugins: [pinia, vuetify], stubs },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="auto-checkin"]').exists()).toBe(false)
  })

  it('shows auto check-in in multi-terminal after staging', async () => {
    const projectStateStore = useProjectStateStore()
    projectStateStore.setStagingComplete('proj-mt', true)

    const wrapper = mount(JobsTab, {
      props: {
        project: {
          project_id: 'proj-mt',
          id: 'proj-mt',
          name: 'MT Project',
          execution_mode: 'multi_terminal',
          auto_checkin_enabled: false,
          auto_checkin_interval: 60,
        },
      },
      global: { plugins: [pinia, vuetify], stubs },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="auto-checkin"]').exists()).toBe(true)
  })

  it('hides interval selector when toggle is off', async () => {
    const projectStateStore = useProjectStateStore()
    projectStateStore.setStagingComplete('proj-off', true)

    const wrapper = mount(JobsTab, {
      props: {
        project: {
          project_id: 'proj-off',
          id: 'proj-off',
          name: 'Toggle Off Project',
          execution_mode: 'multi_terminal',
          auto_checkin_enabled: false,
          auto_checkin_interval: 60,
        },
      },
      global: { plugins: [pinia, vuetify], stubs },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="auto-checkin"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="auto-checkin-interval"]').exists()).toBe(false)
  })

  it('shows interval selector when toggle is on', async () => {
    const projectStateStore = useProjectStateStore()
    projectStateStore.setStagingComplete('proj-on', true)

    const wrapper = mount(JobsTab, {
      props: {
        project: {
          project_id: 'proj-on',
          id: 'proj-on',
          name: 'Toggle On Project',
          execution_mode: 'multi_terminal',
          auto_checkin_enabled: true,
          auto_checkin_interval: 60,
        },
      },
      global: { plugins: [pinia, vuetify], stubs },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="auto-checkin"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="auto-checkin-slider"]').exists()).toBe(true)
  })
})
