/**
 * CloseoutModal.firstOpen.spec.js
 *
 * Regression guard for the chain-first-open empty-pane bug (be-chain-cold-start-hardening).
 *
 * ROOT CAUSE: the watch on props.show was placed ABOVE the const arrow-functions
 * loadMemoryEntries/resetState (TDZ). Adding { immediate: true } to that watch
 * without relocating it caused a ReferenceError on every mount. The fix:
 * (1) move the watch to below resetState, (2) add { immediate: true }.
 *
 * Three tests:
 *  1. FIRST-OPEN — mount with show=true (chain v-if pattern) → getMemoryEntries called.
 *  2. SOLO-UNAFFECTED — mount with show=false → getMemoryEntries NOT called (no spurious fetch).
 *  3. TRANSITION-PRESERVED — edge load + resetState-on-close still work after adding immediate.
 *
 * Edition scope: CE.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const { mockArchive, mockGetMemoryEntries, mockRouterPush, mockShowToast } = vi.hoisted(() => ({
  mockArchive: vi.fn(),
  mockGetMemoryEntries: vi.fn(),
  mockRouterPush: vi.fn(),
  mockShowToast: vi.fn(),
}))

vi.mock('@/services/api', () => ({
  default: {
    projects: { archive: mockArchive },
    products: { getMemoryEntries: mockGetMemoryEntries },
  },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: mockShowToast }),
}))

vi.mock('vuetify', () => ({
  useDisplay: () => ({ mobile: { value: false } }),
}))

vi.mock('@/composables/useFormatDate', () => ({
  useFormatDate: () => ({ formatDateTime: (v) => String(v) }),
}))

// Import AFTER mocks
import CloseoutModal from './CloseoutModal.vue'

const globalConfig = {
  stubs: {
    'v-dialog': { template: '<div v-if="modelValue"><slot /></div>', props: ['modelValue'] },
    'v-card': { template: '<div><slot /></div>' },
    'v-card-text': { template: '<div><slot /></div>' },
    'v-btn': {
      template:
        '<button v-bind="$attrs" :data-testid="$attrs[\'data-testid\']" @click="$emit(\'click\')"><slot /></button>',
    },
    'v-icon': { template: '<i />' },
    'v-spacer': { template: '<div />' },
    'v-divider': { template: '<hr />' },
    'v-progress-circular': { template: '<div />' },
    'v-alert': { template: '<div><slot /></div>' },
    'v-expansion-panels': { template: '<div><slot /></div>' },
    'v-expansion-panel': { template: '<div><slot /></div>' },
    'v-expansion-panel-title': { template: '<div><slot /></div>' },
    'v-expansion-panel-text': { template: '<div><slot /></div>' },
    'v-list': { template: '<ul><slot /></ul>' },
    'v-list-item': { template: '<li><slot /></li>' },
    'v-list-item-title': { template: '<span><slot /></span>' },
  },
  directives: { draggable: {} },
}

const BASE_PROPS = {
  projectId: 'proj-1',
  projectName: 'Test Project',
  productId: 'prod-1',
  projectStatus: 'completed',
  suppressNavigation: true,
}

describe('CloseoutModal — first-open fix (immediate watch)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockArchive.mockResolvedValue({ data: { id: 'proj-1', status: 'completed' } })
    mockGetMemoryEntries.mockResolvedValue({
      data: { entries: [{ id: 'm1', summary: 'x', entry_type: 'lesson' }] },
    })
  })

  it('FIRST-OPEN: mounts with show=true (chain v-if pattern) and loads entries immediately', async () => {
    // Reproduces the chain modal: v-if unmounts+remounts with show already true.
    // Before fix: immediate watcher not present → getMemoryEntries never called → empty pane.
    // After fix: { immediate: true } watch fires on mount → entries loaded.
    const wrapper = mount(CloseoutModal, {
      props: { ...BASE_PROPS, show: true },
      global: { ...globalConfig, plugins: [createPinia()] },
    })

    await flushPromises()

    expect(mockGetMemoryEntries).toHaveBeenCalledWith('prod-1', {
      project_id: 'proj-1',
      limit: 10,
    })
    // Rendered pane shows the entry count, not the empty-state alert
    expect(wrapper.text()).toContain('1 Memory')
    expect(wrapper.text()).not.toContain('No 360 memory entries found')
  })

  it('SOLO-UNAFFECTED: mounts with show=false → getMemoryEntries NOT called (no spurious fetch)', async () => {
    // The always-mounted solo modal starts with show=false.
    // A projectId-keyed immediate watch would spuriously fetch on page load — this
    // test guards that the show-keyed immediate watch does NOT fetch when show=false.
    const wrapper = mount(CloseoutModal, {
      props: { ...BASE_PROPS, show: false },
      global: { ...globalConfig, plugins: [createPinia()] },
    })

    await flushPromises()

    expect(mockGetMemoryEntries).not.toHaveBeenCalled()
    // Solo modal is hidden (v-dialog stub hides slot when modelValue=false)
    expect(wrapper.text()).toBe('')
  })

  it('TRANSITION-PRESERVED: false→true fetches; false→true again re-fetches; false resets', async () => {
    // Proves the edge-transition path (reopen) still works after adding immediate.
    const wrapper = mount(CloseoutModal, {
      props: { ...BASE_PROPS, show: false },
      global: { ...globalConfig, plugins: [createPinia()] },
    })

    await flushPromises()
    expect(mockGetMemoryEntries).not.toHaveBeenCalled()

    // First open (false→true edge)
    await wrapper.setProps({ show: true })
    await flushPromises()
    expect(mockGetMemoryEntries).toHaveBeenCalledTimes(1)

    // Close (true→false → resetState)
    await wrapper.setProps({ show: false })
    await flushPromises()

    // Reopen (false→true again → re-fetch)
    await wrapper.setProps({ show: true })
    await flushPromises()
    expect(mockGetMemoryEntries).toHaveBeenCalledTimes(2)
  })
})
