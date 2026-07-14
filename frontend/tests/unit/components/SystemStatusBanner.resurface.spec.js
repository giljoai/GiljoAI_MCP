// Tests for the skills-drift 24-hour daily-resurface behavior.
//
// IMP-6038 Phase 2: backend now clears dismissed_at on a re-emit when the
// banner was dismissed >24h ago and drift still exists. Frontend contract:
//
//   dismiss → banner hidden → 24h passes → backend clears dismissed_at
//     → either a fresh fetch() OR a WS notification:new event arrives
//     → banner re-renders even though local state had it filtered out.
//
// Behavior under test:
//   1. A re-fetched un-dismissed skills_drift row re-renders after a prior dismiss
//      (fetch path — bannerNotifications re-evaluates from the new full list).
//   2. A WS-re-emitted un-dismissed skills_drift row re-renders after a prior dismiss
//      (WS path — handleWsNewNotification inserts the fresh row since it was
//      removed from local state on dismiss).
//   3. The dismiss + re-surface cycle is idempotent: a second dismiss hides the
//      banner again and a second fetch resurfaces it again.
//   4. FE-6011 regression guard: CTA route on re-surfaced banner is still 'Tools'.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { useUserStore } from '@/stores/user'
import { useNotificationStore } from '@/stores/notifications'

const mockRouterPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush }),
  useRoute: () => ({ name: 'Dashboard', meta: {} }),
}))

vi.mock('@/services/configService', () => ({
  default: {
    fetchConfig: vi.fn().mockResolvedValue(undefined),
    getGiljoMode: vi.fn(() => 'ce'),
  },
}))

async function importBanner() {
  const mod = await import('@/components/system/SystemStatusBanner.vue')
  return mod.default
}

/** Canonical skills_drift fixture matching the stable dedupe key from IMP-6038 Phase 1. */
function makeSkillsDrift(overrides = {}) {
  return {
    id: 'skills-resurface-1',
    type: 'system.skills_drift',
    severity: 'warning',
    title: 'Skills updated to v1.1.20.',
    body: 'Skills updated to v1.1.20. Update with git pull, restart server and run giljo_setup MCP command.',
    surface: 'banner',
    role_filter: 'admin',
    cta_label: 'Go to tools',
    cta_route: 'Tools',
    dismissible: true,
    dismissed_at: null,
    resolved_at: null,
    created_at: '2026-06-04T00:00:00Z',
    ...overrides,
  }
}

/** Simulate the local-state effect of a successful markDismissed() call. */
function simulateDismissed(notifStore, id) {
  notifStore.notifications = notifStore.notifications.filter((n) => n.id !== id)
}

/** Simulate fetch() replacing the full notification list with server response. */
function simulateFetch(notifStore, serverRows) {
  // fetch() does: notifications.value = (response.data ?? []).map(normalizeServerNotif)
  // Assigning through the Pinia proxy is equivalent (triggers reactivity).
  notifStore.notifications = serverRows
}

describe('SystemStatusBanner — 24h resurface (IMP-6038)', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    mockRouterPush.mockReset()

    // All tests run as admin so the role guard passes.
    const userStore = useUserStore()
    userStore.currentUser = { id: 1, username: 'admin', role: 'admin' }
  })

  // ---------------------------------------------------------------------------
  // Path 1: fetch() re-surface
  // The store starts empty (notification was dismissed and removed). A fresh
  // fetch() returns the row with dismissed_at cleared — banner re-renders.
  // ---------------------------------------------------------------------------

  it('re-renders after dismiss when fetch returns an un-dismissed row (fetch path)', async () => {
    const notifStore = useNotificationStore()

    // State after dismiss: store is empty (markDismissed filtered out the row).
    expect(notifStore.bannerNotifications).toHaveLength(0)

    // Mount with empty store — banner is hidden.
    const SystemStatusBanner = await importBanner()
    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="system-banner"]').exists()).toBe(false)

    // 24h later: backend re-surfaces. fetch() replaces the full list with the
    // un-dismissed row. bannerNotifications recomputes and banner appears.
    simulateFetch(notifStore, [makeSkillsDrift()])
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="system-banner"]').exists()).toBe(true)
    expect(wrapper.text()).toMatch(/Skills updated/i)
  })

  // ---------------------------------------------------------------------------
  // Path 2: WS re-surface
  // The banner was showing, user dismisses (row removed), then WS fires the
  // re-surfaced notification. handleWsNewNotification re-inserts the fresh row.
  // ---------------------------------------------------------------------------

  it('re-renders after dismiss when WS notification:new fires with un-dismissed row (WS path)', async () => {
    const notifStore = useNotificationStore()

    // Step 1: notification in store — banner is showing.
    notifStore.handleWsNewNotification(makeSkillsDrift())
    expect(notifStore.bannerNotifications).toHaveLength(1)

    const SystemStatusBanner = await importBanner()
    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="system-banner"]').exists()).toBe(true)

    // Step 2: user dismisses — row removed from local state.
    simulateDismissed(notifStore, 'skills-resurface-1')
    await wrapper.vm.$nextTick()
    expect(notifStore.bannerNotifications).toHaveLength(0)
    expect(wrapper.find('[data-testid="system-banner"]').exists()).toBe(false)

    // Step 3: 24h later — backend clears dismissed_at and fires notification:new.
    // Row is absent from local state (removed at dismiss) → WS inserts it fresh.
    notifStore.handleWsNewNotification(makeSkillsDrift({ dismissed_at: null }))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="system-banner"]').exists()).toBe(true)
    expect(wrapper.text()).toMatch(/Skills updated/i)
  })

  // ---------------------------------------------------------------------------
  // Idempotency: dismiss → resurface → dismiss → resurface
  // ---------------------------------------------------------------------------

  it('second dismiss+resurface cycle works correctly', async () => {
    const notifStore = useNotificationStore()

    const SystemStatusBanner = await importBanner()
    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    // First cycle: add → dismiss → resurface.
    notifStore.handleWsNewNotification(makeSkillsDrift())
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="system-banner"]').exists()).toBe(true)

    simulateDismissed(notifStore, 'skills-resurface-1')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="system-banner"]').exists()).toBe(false)

    notifStore.handleWsNewNotification(makeSkillsDrift())
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="system-banner"]').exists()).toBe(true)

    // Second dismiss cycle.
    simulateDismissed(notifStore, 'skills-resurface-1')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="system-banner"]').exists()).toBe(false)

    // Second resurface via fetch.
    simulateFetch(notifStore, [makeSkillsDrift()])
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="system-banner"]').exists()).toBe(true)
    expect(wrapper.text()).toMatch(/Skills updated/i)
  })

  // ---------------------------------------------------------------------------
  // FE-6011 regression guard: CTA route must remain 'Tools' after re-surface
  // ---------------------------------------------------------------------------

  it('FE-6011: re-surfaced banner CTA still routes to "Tools"', async () => {
    const notifStore = useNotificationStore()

    // Simulate dismiss then resurface.
    simulateDismissed(notifStore, 'skills-resurface-1')
    simulateFetch(notifStore, [makeSkillsDrift({ dismissed_at: null, cta_route: 'Tools' })])

    const SystemStatusBanner = await importBanner()
    const wrapper = mount(SystemStatusBanner, { global: { plugins: [pinia] } })
    await flushPromises()
    await wrapper.vm.$nextTick()

    const ctaBtn = wrapper.find('[data-testid="banner-cta-btn"]')
    expect(ctaBtn.exists()).toBe(true)
    await ctaBtn.trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith({ name: 'Tools' })
  })
})
