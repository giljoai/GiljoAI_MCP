/**
 * JobsTab Component - Handover 0249c
 *
 * Verifies closeout UI wiring:
 * - Button visibility when orchestrator completes
 * - Button hidden while orchestrator still working
 * - Re-emits closeout-project from CloseoutModal
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import JobsTab from '@/components/projects/JobsTab.vue'

// Mocks
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn(),
  }),
}))

vi.mock('@/composables/useWebSocket', () => ({
  useWebSocketV2: () => ({
    on: vi.fn(),
    off: vi.fn(),
  }),
}))

vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: { tenant_key: 'tk_test' },
  }),
}))

vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const CloseoutStub = {
  name: 'CloseoutModal',
  props: ['show', 'projectId', 'projectName'],
  emits: ['close', 'complete'],
  template: `<div
    class="closeout-modal-stub"
    @click="$emit('complete', { project_id: projectId || 'project-123', sequence_number: 1 })"
  ></div>`,
}

const LaunchSuccessorStub = {
  name: 'LaunchSuccessorDialog',
  template: '<div class=\"launch-successor-stub\"></div>',
  props: ['jobId', 'currentJob'],
}

const AgentDetailsStub = {
  name: 'AgentDetailsModal',
  template: '<div class=\"agent-details-stub\"></div>',
  props: ['modelValue', 'agent'],
}

describe('JobsTab.vue - Handover 0249c (Closeout UI)', () => {
  let vuetify

  const baseProject = {
    project_id: 'project-123',
    id: 'project-123',
    name: 'Test Project',
    description: 'Test project description',
  }

  const orchestratorComplete = {
    job_id: 'orchestrator-1',
    agent_id: 'orchestrator-1',
    agent_type: 'orchestrator',
    status: 'complete',
    mission: 'Run everything',
  }

  const orchestratorWorking = {
    ...orchestratorComplete,
    status: 'working',
  }

  function mountComponent(overrides = {}) {
    const props = {
      project: baseProject,
      agents: [orchestratorComplete],
      messages: [],
      allAgentsComplete: true,
      ...overrides,
    }

    return mount(JobsTab, {
      props,
      global: {
        plugins: [vuetify],
        stubs: {
          CloseoutModal: CloseoutStub,
          LaunchSuccessorDialog: LaunchSuccessorStub,
          AgentDetailsModal: AgentDetailsStub,
        },
      },
    })
  }

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  it('shows Close Out Project button when orchestrator is complete and all agents complete', () => {
    const wrapper = mountComponent()

    const button = wrapper.find('.closeout-btn')
    expect(button.exists()).toBe(true)
    expect(button.text()).toContain('Close Out Project')
  })

  it('hides Close Out Project button when orchestrator is still working', () => {
    const wrapper = mountComponent({
      agents: [orchestratorWorking],
      allAgentsComplete: false,
    })

    const button = wrapper.find('.closeout-btn')
    expect(button.exists()).toBe(false)
  })

  it('re-emits closeout-project when modal emits event', async () => {
    const wrapper = mountComponent()

    const modal = wrapper.find('.closeout-modal-stub')
    expect(modal.exists()).toBe(true)

    await modal.trigger('click')

    const emitted = wrapper.emitted('closeout-project')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0]).toMatchObject({
      project_id: 'project-123',
      sequence_number: 1,
    })
  })
})
