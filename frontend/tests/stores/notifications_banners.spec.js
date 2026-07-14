/**
 * Vitest spec for bannerNotifications getter (IMP-5037b Phase 2)
 *
 * TDD: written before implementation. These tests MUST FAIL until
 * bannerNotifications is added to notifications.js and normalizeServerNotif
 * is updated to preserve the Phase 1 fields.
 *
 * Covers:
 *  - bannerNotifications includes surface='banner' rows
 *  - bannerNotifications includes surface='both' rows
 *  - bannerNotifications excludes surface='bell' rows
 *  - bannerNotifications excludes dismissed (dismissed_at != null) rows
 *  - bannerNotifications excludes resolved (resolved_at != null) rows
 *  - normalizeServerNotif preserves surface, role_filter, cta_label, cta_route, dismissible
 *  - handleWsNewNotification merges banner-surface events into bannerNotifications
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useNotificationStore } from '@/stores/notifications'

// ---------------------------------------------------------------------------
// Fixtures — Phase 1 backend shape (includes new fields)
// ---------------------------------------------------------------------------
function makeBannerNotif(overrides = {}) {
  return {
    id: 'banner-1',
    type: 'system.update_available',
    severity: 'info',
    title: 'Update available',
    body: null,
    payload: null,
    surface: 'banner',
    role_filter: 'admin',
    cta_label: 'Go to settings',
    cta_route: 'SystemSettings',
    dismissible: true,
    read_at: null,
    dismissed_at: null,
    resolved_at: null,
    created_at: '2026-06-03T00:00:00Z',
    ...overrides,
  }
}

function makeBothSurfaceNotif(overrides = {}) {
  return makeBannerNotif({ id: 'both-1', surface: 'both', ...overrides })
}

function makeBellNotif(overrides = {}) {
  return makeBannerNotif({ id: 'bell-1', surface: 'bell', ...overrides })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('useNotificationStore — bannerNotifications getter', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useNotificationStore()
  })

  it('bannerNotifications is exported from the store', () => {
    // Getter must exist
    expect(store.bannerNotifications).toBeDefined()
  })

  it('returns empty array when no notifications', () => {
    expect(store.bannerNotifications).toEqual([])
  })

  it('includes notifications with surface="banner"', () => {
    store.handleWsNewNotification(makeBannerNotif())
    expect(store.bannerNotifications).toHaveLength(1)
    expect(store.bannerNotifications[0].id).toBe('banner-1')
  })

  it('includes notifications with surface="both"', () => {
    store.handleWsNewNotification(makeBothSurfaceNotif())
    expect(store.bannerNotifications).toHaveLength(1)
    expect(store.bannerNotifications[0].id).toBe('both-1')
  })

  it('excludes notifications with surface="bell"', () => {
    store.handleWsNewNotification(makeBellNotif())
    expect(store.bannerNotifications).toHaveLength(0)
  })

  it('excludes notifications with dismissed_at set', () => {
    store.handleWsNewNotification(
      makeBannerNotif({ dismissed_at: '2026-06-03T01:00:00Z' }),
    )
    expect(store.bannerNotifications).toHaveLength(0)
  })

  it('excludes notifications with resolved_at set', () => {
    store.handleWsNewNotification(
      makeBannerNotif({ id: 'resolved-1', resolved_at: '2026-06-03T02:00:00Z' }),
    )
    expect(store.bannerNotifications).toHaveLength(0)
  })

  it('returns multiple matching banner rows', () => {
    store.handleWsNewNotification(makeBannerNotif({ id: 'b1' }))
    store.handleWsNewNotification(makeBannerNotif({ id: 'b2', surface: 'both' }))
    store.handleWsNewNotification(makeBellNotif({ id: 'b3' }))
    expect(store.bannerNotifications).toHaveLength(2)
  })
})

describe('useNotificationStore — normalizeServerNotif preserves Phase 1 fields', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useNotificationStore()
  })

  it('preserves surface field', () => {
    store.handleWsNewNotification(makeBannerNotif())
    const n = store.notifications.find((x) => x.id === 'banner-1')
    expect(n.surface).toBe('banner')
  })

  it('preserves role_filter field', () => {
    store.handleWsNewNotification(makeBannerNotif({ role_filter: 'admin' }))
    const n = store.notifications.find((x) => x.id === 'banner-1')
    expect(n.role_filter).toBe('admin')
  })

  it('preserves cta_label field', () => {
    store.handleWsNewNotification(makeBannerNotif({ cta_label: 'Go to settings' }))
    const n = store.notifications.find((x) => x.id === 'banner-1')
    expect(n.cta_label).toBe('Go to settings')
  })

  it('preserves cta_route field (named route string)', () => {
    store.handleWsNewNotification(makeBannerNotif({ cta_route: 'SystemSettings' }))
    const n = store.notifications.find((x) => x.id === 'banner-1')
    expect(n.cta_route).toBe('SystemSettings')
  })

  it('preserves dismissible=true', () => {
    store.handleWsNewNotification(makeBannerNotif({ dismissible: true }))
    const n = store.notifications.find((x) => x.id === 'banner-1')
    expect(n.dismissible).toBe(true)
  })

  it('preserves dismissible=false', () => {
    store.handleWsNewNotification(
      makeBannerNotif({ id: 'lapsed', dismissible: false }),
    )
    const n = store.notifications.find((x) => x.id === 'lapsed')
    expect(n.dismissible).toBe(false)
  })

  it('preserves resolved_at field', () => {
    const ts = '2026-06-03T10:00:00Z'
    store.handleWsNewNotification(makeBannerNotif({ id: 'res', resolved_at: ts }))
    const n = store.notifications.find((x) => x.id === 'res')
    expect(n.resolved_at).toBe(ts)
  })

  it('defaults surface to null when absent (legacy bell notifications)', () => {
    store.addNotification({ id: 'legacy', type: 'info', title: 'T', message: 'M' })
    const n = store.notifications.find((x) => x.id === 'legacy')
    // legacy in-memory notifications have no surface field — should not appear in bannerNotifications
    expect(n.surface).toBeUndefined()
    expect(store.bannerNotifications.find((x) => x.id === 'legacy')).toBeUndefined()
  })
})
