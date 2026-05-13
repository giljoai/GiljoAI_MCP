import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DecisionModal from '@/components/orchestration/DecisionModal.vue'
import { useApprovalsStore } from '@/stores/useApprovalsStore'
import api from '@/services/api'

let pinia

const approval = {
  id: 'appr-decision-1',
  agent_display_name: 'orchestrator',
  job_id: 'job-orch-1',
  reason: 'Approve the Protected Zone edit?',
  context: { file: 'pyproject.toml' },
  options: [
    { id: 'approve', label: 'Approve once' },
    { id: 'deny', label: 'Deny' },
  ],
}

function mountModal(props = {}) {
  return mount(DecisionModal, {
    props: { show: true, orchestratorJobId: approval.job_id, ...props },
    global: {
      plugins: [pinia],
      stubs: {
        'v-dialog': {
          props: ['modelValue'],
          template: '<div v-if="modelValue" data-testid="v-dialog-stub"><slot /></div>',
        },
      },
    },
  })
}

describe('DecisionModal.vue', () => {
  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()
  })

  it('renders nothing when show=false', () => {
    const wrapper = mountModal({ show: false })
    expect(wrapper.find('[data-testid="v-dialog-stub"]').exists()).toBe(false)
  })

  it('renders the ApprovalCard when the approval is in the store', () => {
    const store = useApprovalsStore()
    store.upsertApproval(approval)
    const wrapper = mountModal()
    expect(wrapper.find('[data-testid="decision-modal-card"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Approve the Protected Zone edit?')
  })

  it('renders a quiet loading state (spinner only) when no approval is in the store yet', () => {
    const wrapper = mountModal()
    expect(wrapper.find('[data-testid="decision-modal-card"]').exists()).toBe(false)
    // No verbose copy that invites the user to wait around -- just a spinner.
    expect(wrapper.find('.decision-modal-loading').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Loading')
  })

  it('emits "close" when the Cancel button is clicked', async () => {
    const wrapper = mountModal()
    await wrapper.find('button[aria-label="Cancel"]').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('re-emits "approval-decided" when the inner ApprovalCard signals "decided"', async () => {
    const store = useApprovalsStore()
    store.upsertApproval(approval)

    const wrapper = mountModal()
    const card = wrapper.findComponent({ name: 'ApprovalCard' })
    expect(card.exists()).toBe(true)

    card.vm.$emit('decided', { approvalId: approval.id, optionId: 'approve' })
    await flushPromises()

    expect(wrapper.emitted('approval-decided')).toBeTruthy()
    expect(wrapper.emitted('approval-decided')[0][0]).toMatchObject({
      approvalId: approval.id,
      optionId: 'approve',
    })
  })

  it('hydrates pending approvals when opened (watch on `show`)', async () => {
    api.approvals.listPending.mockResolvedValueOnce({ data: { items: [approval] } })
    const wrapper = mount(DecisionModal, {
      props: { show: false, orchestratorJobId: approval.job_id },
      global: {
        plugins: [pinia],
        stubs: {
          'v-dialog': {
            props: ['modelValue'],
            template: '<div v-if="modelValue"><slot /></div>',
          },
        },
      },
    })
    await wrapper.setProps({ show: true })
    await flushPromises()
    expect(api.approvals.listPending).toHaveBeenCalled()
  })
})
