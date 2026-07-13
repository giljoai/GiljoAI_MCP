/**
 * ProjectStatusBanner.spec.js — FE-6006 unit 3a
 *
 * Tests banner state visibility: one state shown at a time.
 * Edition scope: CE
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ProjectStatusBanner from './ProjectStatusBanner.vue'

const globalStubs = {
  'v-icon': { template: '<i class="v-icon"><slot /></i>' },
  'v-chip': { template: '<div class="v-chip"><slot /></div>' },
  'v-btn': { template: '<button class="v-btn" v-bind="$attrs"><slot /></button>' },
  'v-progress-circular': { template: '<div class="v-progress-circular" />' },
}

function mountBanner(props = {}) {
  return mount(ProjectStatusBanner, {
    props: {
      projectDoneStatus: null,
      orchestratorCloseoutBlocked: false,
      showOrchUnlockedBanner: false,
      showCloseoutButton: false,
      showMemoryPending: false,
      allJobsTerminal: false,
      memoryPollTimedOut: false,
      memoryPollError: false,
      ...props,
    },
    global: { stubs: globalStubs },
  })
}

describe('ProjectStatusBanner', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders nothing when all props are false/null', () => {
    const wrapper = mountBanner()
    expect(wrapper.find('[data-testid="project-done-banner"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="closeout-decision-banner"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="close-project-btn"]').exists()).toBe(false)
  })

  it('shows done banner when projectDoneStatus is "completed"', () => {
    const wrapper = mountBanner({ projectDoneStatus: 'completed' })
    expect(wrapper.find('[data-testid="project-done-banner"]').exists()).toBe(true)
  })

  it('shows done banner when projectDoneStatus is "terminated"', () => {
    const wrapper = mountBanner({ projectDoneStatus: 'terminated' })
    expect(wrapper.find('[data-testid="project-done-banner"]').exists()).toBe(true)
  })

  it('shows decision banner when orchestratorCloseoutBlocked is true', () => {
    const wrapper = mountBanner({ orchestratorCloseoutBlocked: true })
    expect(wrapper.find('[data-testid="closeout-decision-banner"]').exists()).toBe(true)
  })

  it('clicking decision banner emits open-decision-modal', async () => {
    const wrapper = mountBanner({ orchestratorCloseoutBlocked: true })
    await wrapper.find('[data-testid="closeout-decision-banner"]').trigger('click')
    expect(wrapper.emitted('open-decision-modal')).toBeTruthy()
  })

  it('shows unlocked banner when showOrchUnlockedBanner is true', () => {
    const wrapper = mountBanner({ showOrchUnlockedBanner: true })
    expect(wrapper.find('[data-testid="orchestrator-unlocked-banner"]').exists()).toBe(true)
  })

  it('clicking dismiss on unlocked banner emits dismiss-orch-unlocked', async () => {
    const wrapper = mountBanner({ showOrchUnlockedBanner: true })
    await wrapper.find('[data-testid="orchestrator-unlocked-dismiss"]').trigger('click')
    expect(wrapper.emitted('dismiss-orch-unlocked')).toBeTruthy()
  })

  it('shows closeout button when showCloseoutButton is true', () => {
    const wrapper = mountBanner({ showCloseoutButton: true })
    expect(wrapper.find('[data-testid="close-project-btn"]').exists()).toBe(true)
  })

  it('clicking closeout button emits open-closeout-modal', async () => {
    const wrapper = mountBanner({ showCloseoutButton: true })
    await wrapper.find('[data-testid="close-project-btn"]').trigger('click')
    expect(wrapper.emitted('open-closeout-modal')).toBeTruthy()
  })

  it('shows memory-pending chip when showMemoryPending is true', () => {
    const wrapper = mountBanner({ showMemoryPending: true })
    expect(wrapper.find('[data-testid="memory-pending-chip"]').exists()).toBe(true)
  })
})
