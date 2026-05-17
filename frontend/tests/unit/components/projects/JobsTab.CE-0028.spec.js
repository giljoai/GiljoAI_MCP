/**
 * CE-0029 Item 2 — staging→implementation handoff status display.
 *
 * Pre-CE-0029, the orchestrator's staging execution was the only orch row
 * (status='complete') and `applyStagingHandoffStatusOverride` rewrote it to
 * 'waiting' in the displayed table. CE-0029 Item 2 makes the backend
 * pre-spawn an actual impl-phase orchestrator execution at staging-end with
 * status='waiting'. The UI now naturally displays "Waiting" because there
 * IS a waiting orch exec — no override function needed, no UI relabel.
 *
 * These tests verify the post-CE-0029 reality:
 *   - With both execs present (complete staging + waiting impl), the table
 *     renders both rows; the impl row's status is genuinely 'waiting' WITHOUT
 *     any override.
 *   - The CE-0028b override function is gone (assertion checks the rendered
 *     status equals the raw store-fed status with no rewrite).
 *
 * Per feedback_frontend_prop_vs_store_source_of_truth, store state changes
 * are fed through the agent store mutation path, not by injecting fields
 * onto the prop. The prop carries only stable identifying fields.
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
    name: 'CE-0029 Test Project',
    execution_mode: 'multi_terminal',
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

describe('JobsTab CE-0029 staging→implementation handoff (no-override)', () => {
  beforeEach(() => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const userStore = useUserStore()
    userStore.currentUser = { id: 'user-1', tenant_key: 'tenant-1' }
  })

  it('renders a real waiting impl exec WITHOUT any status override', async () => {
    // Post-CE-0029 reality: staging exec is complete (historical), impl exec
    // is waiting (pre-spawned by _handle_staging_end). Both rows render with
    // their actual statuses; the UI does not rewrite 'complete' to 'waiting'.
    const project = makeProject()
    const wrapper = await mountWithJobs(project, [
      {
        job_id: 'j-orch',
        agent_id: 'a-orch-staging',
        agent_name: 'orchestrator',
        agent_display_name: 'orchestrator',
        status: 'complete',
        phase: null,
      },
      {
        job_id: 'j-orch',
        agent_id: 'a-orch-impl',
        agent_name: 'orchestrator',
        agent_display_name: 'orchestrator',
        status: 'waiting',
        phase: null,
      },
    ])

    const rows = wrapper.findAll('[data-testid="agent-row"]')
    expect(rows.length).toBe(2)

    const orchStatuses = rows.map((r) => r.attributes('data-agent-status'))
    expect(orchStatuses).toContain('complete')
    expect(orchStatuses).toContain('waiting')

    // No row has rewritten its status — the chip text matches the raw
    // store-fed status for both rows.
    const chips = rows.map((r) => r.find('[data-testid="status-chip"]').text())
    expect(chips.some((t) => t.includes('Complete'))).toBe(true)
    expect(chips.some((t) => t.includes('Waiting'))).toBe(true)
  })

  it('does not rewrite a working orchestrator', async () => {
    const project = makeProject()
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

  it('does not rewrite a complete orchestrator post-implementation', async () => {
    // After implementation finishes there is no pre-spawn — the impl orch
    // exec is genuinely complete. The table must render that as-is, no
    // relabel to 'waiting'.
    const project = makeProject()
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

  it('does not rewrite non-orchestrator complete agents', async () => {
    const project = makeProject()
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
})
