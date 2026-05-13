import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ApprovalBanner from '@/components/orchestration/ApprovalBanner.vue'
import { useApprovalsStore } from '@/stores/useApprovalsStore'

let pinia

const baseApproval = {
  id: 'appr-banner-1',
  agent_display_name: 'orchestrator',
  job_id: 'job-1',
  reason: 'Protected Zone edit needs approval',
  context: { file: 'pyproject.toml' },
  options: [
    { id: 'approve', label: 'Approve once' },
    { id: 'deny', label: 'Deny' },
  ],
}

const secondApproval = {
  id: 'appr-banner-2',
  agent_display_name: 'implementer',
  job_id: 'job-2',
  reason: 'Scope change: include extra file',
  context: null,
  options: [{ id: 'ok', label: 'OK' }],
}

function mountBanner() {
  return mount(ApprovalBanner, {
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

describe('ApprovalBanner.vue', () => {
  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()
  })

  it('renders nothing when there are no pending approvals', () => {
    const wrapper = mountBanner()
    expect(wrapper.find('[data-testid="approval-banner-stack"]').exists()).toBe(false)
  })

  it('renders one banner per pending approval with reason preview', () => {
    const store = useApprovalsStore()
    store.upsertApproval(baseApproval)
    store.upsertApproval(secondApproval)

    const wrapper = mountBanner()
    expect(wrapper.find('[data-testid="approval-banner-stack"]').exists()).toBe(true)
    expect(wrapper.find(`[data-testid="approval-banner-${baseApproval.id}"]`).exists()).toBe(true)
    expect(wrapper.find(`[data-testid="approval-banner-${secondApproval.id}"]`).exists()).toBe(true)
    expect(wrapper.text()).toContain('Protected Zone edit needs approval')
    expect(wrapper.text()).toContain('Scope change: include extra file')
  })

  it('exposes the agent name + decision call-to-action in the banner', () => {
    const store = useApprovalsStore()
    store.upsertApproval(baseApproval)

    const wrapper = mountBanner()
    const banner = wrapper.find(`[data-testid="approval-banner-${baseApproval.id}"]`)
    expect(banner.text()).toContain('orchestrator needs your decision')
    expect(banner.text()).toContain('Review')
  })

  it('opens a dialog with the selected approval when the banner is clicked', async () => {
    const store = useApprovalsStore()
    store.upsertApproval(baseApproval)
    store.upsertApproval(secondApproval)

    const wrapper = mountBanner()
    expect(wrapper.vm.dialogApproval).toBeNull()

    await wrapper.find(`[data-testid="approval-banner-${secondApproval.id}"]`).trigger('click')
    await flushPromises()

    expect(wrapper.vm.dialogApproval).not.toBeNull()
    expect(wrapper.vm.dialogApproval.id).toBe(secondApproval.id)
    expect(wrapper.find('[data-testid="approval-banner-dialog-card"]').exists()).toBe(true)
  })

  it('closes the dialog without deciding via the close button', async () => {
    const store = useApprovalsStore()
    store.upsertApproval(baseApproval)

    const wrapper = mountBanner()
    await wrapper.find(`[data-testid="approval-banner-${baseApproval.id}"]`).trigger('click')
    expect(wrapper.vm.dialogApproval).not.toBeNull()

    await wrapper.find('[data-testid="approval-banner-dialog-close"]').trigger('click')
    expect(wrapper.vm.dialogApproval).toBeNull()
  })

  it('renders the deliberate-decision hint inside the dialog', async () => {
    const store = useApprovalsStore()
    store.upsertApproval(baseApproval)

    const wrapper = mountBanner()
    await wrapper.find(`[data-testid="approval-banner-${baseApproval.id}"]`).trigger('click')
    expect(wrapper.text()).toContain("Read the agent's reasoning in chat before choosing")
  })

  it('exposes an aria-label that includes the reason for screen readers', () => {
    const store = useApprovalsStore()
    store.upsertApproval(baseApproval)

    const wrapper = mountBanner()
    const banner = wrapper.find(`[data-testid="approval-banner-${baseApproval.id}"]`)
    expect(banner.attributes('aria-label')).toContain('Protected Zone edit needs approval')
  })
})
