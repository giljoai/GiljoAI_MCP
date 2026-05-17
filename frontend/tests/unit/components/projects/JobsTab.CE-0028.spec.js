/**
 * CE-0028 — staging→implementation handoff status display.
 *
 * At the handoff window (after the staging orchestrator calls complete_job
 * but before the user clicks Implement), the orchestrator's staging execution
 * is `status='complete'` in the DB but the project is NOT done. The UI must
 * display the orchestrator as "Waiting" during this window so users don't
 * mistake session-complete for project-complete.
 *
 * The override is bounded by project.staging_status === 'staging_complete'
 * AND project.implementation_launched_at is null. Outside that window, the
 * raw status flows through unchanged.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import JobsTab from '@/components/projects/JobsTab.vue'
import { useAgentJobsStore } from '@/stores/agentJobsStore'
import { useUserStore } from '@/stores/user'

const vuetify = createVuetify()

vi.mock('@/services/api', () => {
  const api = {
    agentJobs: { list: vi.fn().mockResolvedValue({ data: [] }) },
    prompts: { agentPrompt: vi.fn().mockResolvedValue({ data: { prompt: '' } }) },
    messages: { sendUnified: vi.fn().mockResolvedValue({ data: { success: true } }) },
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
  'v-btn': true,
  AgentDetailsModal: true,
  AgentJobModal: true,
  MessageAuditModal: true,
  HandoverModal: true,
}

function makeProject(overrides = {}) {
  return {
    project_id: 'proj-1',
    id: 'proj-1',
    name: 'CE-0028 Test Project',
    execution_mode: 'multi_terminal',
    staging_status: 'staging_complete',
    implementation_launched_at: null,
    ...overrides,
  }
}

async function mountWithJobs(project, jobs) {
  const wrapper = mount(JobsTab, {
    props: { project },
    global: { plugins: [createPinia(), vuetify], stubs },
  })
  await wrapper.vm.$nextTick()
  const store = useAgentJobsStore()
  store.setJobs(jobs)
  await wrapper.vm.$nextTick()
  return wrapper
}

describe('JobsTab CE-0028 staging→implementation handoff status', () => {
  beforeEach(() => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const userStore = useUserStore()
    userStore.currentUser = { id: 'user-1', tenant_key: 'tenant-1' }
  })

  it('displays a complete orchestrator as "Waiting." at the staging handoff', async () => {
    const project = makeProject({
      staging_status: 'staging_complete',
      implementation_launched_at: null,
    })
    const wrapper = await mountWithJobs(project, [
      {
        job_id: 'j-orch',
        agent_id: 'a-orch',
        agent_name: 'orchestrator',
        agent_display_name: 'orchestrator',
        status: 'complete',
        phase: null,
      },
    ])

    const row = wrapper.find('[data-testid="agent-row"]')
    expect(row.exists()).toBe(true)
    // data-agent-status reflects the displayed override (consistent with the chip).
    expect(row.attributes('data-agent-status')).toBe('waiting')
    const chip = row.find('[data-testid="status-chip"]')
    expect(chip.text()).toContain('Waiting')
    expect(chip.text()).not.toContain('Complete')
  })

  it('shows real "Complete" once implementation_launched_at is set', async () => {
    const project = makeProject({
      staging_status: 'staging_complete',
      implementation_launched_at: '2026-05-17T12:00:00Z',
    })
    const wrapper = await mountWithJobs(project, [
      {
        job_id: 'j-orch',
        agent_id: 'a-orch',
        agent_name: 'orchestrator',
        agent_display_name: 'orchestrator',
        status: 'complete',
        phase: null,
      },
    ])

    const row = wrapper.find('[data-testid="agent-row"]')
    expect(row.attributes('data-agent-status')).toBe('complete')
    expect(row.find('[data-testid="status-chip"]').text()).toContain('Complete')
  })

  it('does not override a working orchestrator', async () => {
    const project = makeProject({
      staging_status: 'staging',
      implementation_launched_at: null,
    })
    const wrapper = await mountWithJobs(project, [
      {
        job_id: 'j-orch',
        agent_id: 'a-orch',
        agent_name: 'orchestrator',
        agent_display_name: 'orchestrator',
        status: 'working',
        phase: null,
      },
    ])

    const row = wrapper.find('[data-testid="agent-row"]')
    expect(row.attributes('data-agent-status')).toBe('working')
    expect(row.find('[data-testid="status-chip"]').text()).toContain('Working')
  })

  it('does not override non-orchestrator complete agents', async () => {
    const project = makeProject({
      staging_status: 'staging_complete',
      implementation_launched_at: null,
    })
    const wrapper = await mountWithJobs(project, [
      {
        job_id: 'j-impl',
        agent_id: 'a-impl',
        agent_name: 'backend-implementer',
        agent_display_name: 'backend-implementer',
        status: 'complete',
        phase: 1,
      },
    ])

    const row = wrapper.find('[data-testid="agent-row"]')
    expect(row.attributes('data-agent-status')).toBe('complete')
    expect(row.find('[data-testid="status-chip"]').text()).toContain('Complete')
  })

  it('does not override when project staging_status is not staging_complete', async () => {
    // E.g., closed-out project whose orchestrator is complete — that IS the real
    // project-complete state. Override must not fire.
    const project = makeProject({
      staging_status: 'staging',
      implementation_launched_at: null,
    })
    const wrapper = await mountWithJobs(project, [
      {
        job_id: 'j-orch',
        agent_id: 'a-orch',
        agent_name: 'orchestrator',
        agent_display_name: 'orchestrator',
        status: 'complete',
        phase: null,
      },
    ])

    const row = wrapper.find('[data-testid="agent-row"]')
    expect(row.attributes('data-agent-status')).toBe('complete')
    expect(row.find('[data-testid="status-chip"]').text()).toContain('Complete')
  })
})
