// Tests for the system:update_available WS handler wiring (Skills version drift).
// Per project mission: when the WS event fires, the existing window event MUST
// continue to dispatch (SystemStatusBanner depends on it) AND a notification
// MUST be added to the notification store so the bell-icon badge surfaces it.

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { SYSTEM_EVENT_ROUTES } from '@/stores/eventRoutes/systemEventRoutes'
import { useNotificationStore } from '@/stores/notifications'

describe('systemEventRoutes - system:update_available', () => {
  let dispatchSpy

  beforeEach(() => {
    setActivePinia(createPinia())
    dispatchSpy = vi.spyOn(window, 'dispatchEvent')
  })

  it('still dispatches the ws-system-update-available window event (banner contract)', async () => {
    const route = SYSTEM_EVENT_ROUTES['system:update_available']
    expect(route).toBeTruthy()
    expect(typeof route.handler).toBe('function')

    await route.handler({ commits_behind: 3, current: '1.1.11' })

    const calls = dispatchSpy.mock.calls.filter(
      ([evt]) => evt instanceof CustomEvent && evt.type === 'ws-system-update-available',
    )
    expect(calls).toHaveLength(1)
  })

  it('adds a system_alert notification to the notification store', async () => {
    const store = useNotificationStore()
    const route = SYSTEM_EVENT_ROUTES['system:update_available']

    await route.handler({ commits_behind: 2, current: '1.1.11' })

    expect(store.notifications).toHaveLength(1)
    const note = store.notifications[0]
    expect(note.type).toBe('system_alert')
    expect(note.message).toMatch(/git pull|restart your server/i)
  })

  it('passes through gracefully when payload is missing', async () => {
    const store = useNotificationStore()
    const route = SYSTEM_EVENT_ROUTES['system:update_available']

    await expect(route.handler(undefined)).resolves.not.toThrow()
    // Still adds a notification (best-effort) and still dispatches the window event
    expect(store.notifications).toHaveLength(1)
  })
})
