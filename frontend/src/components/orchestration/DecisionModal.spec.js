import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DecisionModal from '@/components/orchestration/DecisionModal.vue'
import { useApprovalsStore } from '@/stores/useApprovalsStore'
import api from '@/services/api'

let pinia

const approval = {
  id: 'appr-1',
  job_id: 'job-1',
  agent_display_name: 'orchestrator',
  reason: 'Approve the Protected Zone edit?',
  context: { task_id: 'e8e118a5' },
  options: [
    { id: 'approve', label: 'Approve' },
    { id: 'deny', label: 'Deny' },
  ],
  status: 'pending',
}

vi.mock('@/services/api', () => ({
  default: {
    approvals: {
      listPending: vi.fn().mockResolvedValue({ data: { items: [] } }),
      decide: vi.fn(),
    },
  },
}))

vi.mock('vuetify', async () => {
  const actual = await vi.importActual('vuetify')
  return {
    ...actual,
    useDisplay: () => ({ mobile: { value: false } }),
  }
})

function mountModal(props = {}) {
  return mount(DecisionModal, {
    props: {
      show: true,
      orchestratorJobId: 'job-1',
      ...props,
    },
    global: {
      plugins: [pinia],
      stubs: {
        'v-dialog': { template: '<div><slot /></div>' },
        'v-card': { template: '<div><slot /></div>' },
        'v-divider': true,
        'v-icon': true,
        'v-btn': {
          props: ['disabled', 'loading'],
          emits: ['click'],
          template: '<button :data-testid="$attrs[\'data-testid\']" @click="$emit(\'click\')"><slot /></button>',
        },
        'v-spacer': true,
      },
      directives: { draggable: {} },
    },
  })
}

describe('DecisionModal — single-dialog two-state', () => {
  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()
  })

  it('renders ApprovalCard while approval is pending', () => {
    const store = useApprovalsStore()
    store.upsertApproval(approval)

    const wrapper = mountModal()
    expect(wrapper.find('[data-testid="decision-modal-card"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Approve the Protected Zone edit?')
    expect(wrapper.find('[data-testid="decision-modal-confirmation"]').exists()).toBe(false)
  })

  it('swaps to static confirmation after ApprovalCard emits "decided"', async () => {
    const store = useApprovalsStore()
    store.upsertApproval(approval)

    const wrapper = mountModal()
    const card = wrapper.findComponent({ name: 'ApprovalCard' })
    expect(card.exists()).toBe(true)

    card.vm.$emit('decided', { approvalId: approval.id, optionId: 'approve' })
    await flushPromises()

    expect(wrapper.findComponent({ name: 'ApprovalCard' }).exists()).toBe(false)
    const confirmation = wrapper.find('[data-testid="decision-modal-confirmation"]')
    expect(confirmation.exists()).toBe(true)
    expect(confirmation.text()).toContain('Your choice has been sent to the orchestrator')
    expect(confirmation.text()).toContain('tell it to read its message and proceed')
  })

  it('header title swaps from "Decision Required" to "Orchestrator unlocked" after decide', async () => {
    const store = useApprovalsStore()
    store.upsertApproval(approval)

    const wrapper = mountModal()
    expect(wrapper.text()).toContain('Decision Required')
    expect(wrapper.text()).not.toContain('Orchestrator unlocked')

    wrapper.findComponent({ name: 'ApprovalCard' }).vm.$emit('decided', {})
    await flushPromises()

    expect(wrapper.text()).toContain('Orchestrator unlocked')
  })

  it('renders nothing in the body before approval loads (no spinner, no loading text)', () => {
    const wrapper = mountModal()
    expect(wrapper.findComponent({ name: 'ApprovalCard' }).exists()).toBe(false)
    expect(wrapper.find('[data-testid="decision-modal-confirmation"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Loading')
  })

  it('emits "close" on Cancel click', async () => {
    const store = useApprovalsStore()
    store.upsertApproval(approval)
    const wrapper = mountModal()

    await wrapper.findAll('button').find((b) => b.text() === 'Cancel').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits "close" on post-decision Close click', async () => {
    const store = useApprovalsStore()
    store.upsertApproval(approval)
    const wrapper = mountModal()

    wrapper.findComponent({ name: 'ApprovalCard' }).vm.$emit('decided', {})
    await flushPromises()

    await wrapper.find('[data-testid="decision-modal-close"]').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('resets to pre-decision state when re-opened (decided flag clears on show=true)', async () => {
    const store = useApprovalsStore()
    store.upsertApproval(approval)

    const wrapper = mountModal({ show: true })
    wrapper.findComponent({ name: 'ApprovalCard' }).vm.$emit('decided', {})
    await flushPromises()
    expect(wrapper.find('[data-testid="decision-modal-confirmation"]').exists()).toBe(true)

    await wrapper.setProps({ show: false })
    // The watcher on `show` calls fetchPending() which replaces the store map.
    // Mock the server response so the fresh approval row lands in the store.
    const freshApproval = { ...approval, id: 'appr-2' }
    api.approvals.listPending.mockResolvedValueOnce({ data: { items: [freshApproval] } })
    await wrapper.setProps({ show: true })
    await flushPromises()

    expect(wrapper.find('[data-testid="decision-modal-confirmation"]').exists()).toBe(false)
    expect(wrapper.findComponent({ name: 'ApprovalCard' }).exists()).toBe(true)
  })

  it('hydrates pending approvals when opened (watch on `show`)', async () => {
    api.approvals.listPending.mockClear()
    const wrapper = mountModal({ show: false })
    expect(api.approvals.listPending).not.toHaveBeenCalled()

    await wrapper.setProps({ show: true })
    await flushPromises()
    expect(api.approvals.listPending).toHaveBeenCalledTimes(1)
  })
})
