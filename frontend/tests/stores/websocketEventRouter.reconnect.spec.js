/**
 * FE-3007b — generalized reconnect-resync registry.
 *
 * The router owns ONE connection listener; any store/view registers a resync
 * callback and every registration refetches on a WS reconnect (automatic OR
 * manual). Tests drive the fan-out through that single connection listener (the
 * real production path). vi.resetModules per test gives a fresh module-level
 * registry + init-once guard.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('websocketEventRouter — reconnect-resync registry (FE-3007b)', () => {
  let router

  // Init the router against a fake ws store and capture its connection handler,
  // so a test can simulate reconnect events the way the live ws store would.
  function initWithFakeWs() {
    let connectionHandler = null
    const fakeWs = {
      on: vi.fn(),
      onConnectionChange: vi.fn((cb) => {
        connectionHandler = cb
        return vi.fn()
      }),
    }
    router.initWebsocketEventRouter({ wsStore: fakeWs })
    return { fakeWs, reconnect: () => connectionHandler({ state: 'connected', isReconnect: true }) }
  }

  beforeEach(async () => {
    vi.resetModules()
    router = await import('@/stores/websocketEventRouter')
  })

  it('a registered callback fires on reconnect', async () => {
    const cb = vi.fn()
    router.registerReconnectResync(cb)
    const { reconnect } = initWithFakeWs()

    await reconnect()

    expect(cb).toHaveBeenCalledTimes(1)
  })

  it('the unregister fn removes the callback', async () => {
    const cb = vi.fn()
    const unregister = router.registerReconnectResync(cb)
    const { reconnect } = initWithFakeWs()

    unregister()
    await reconnect()

    expect(cb).not.toHaveBeenCalled()
  })

  it('fans out to ALL registered callbacks (projects, messages, agent-jobs)', async () => {
    const projects = vi.fn()
    const messages = vi.fn()
    const jobs = vi.fn()
    router.registerReconnectResync(projects)
    router.registerReconnectResync(messages)
    router.registerReconnectResync(jobs)
    const { reconnect } = initWithFakeWs()

    await reconnect()

    expect(projects).toHaveBeenCalledTimes(1)
    expect(messages).toHaveBeenCalledTimes(1)
    expect(jobs).toHaveBeenCalledTimes(1)
  })

  it('one failing callback does not block the others (allSettled)', async () => {
    const ok1 = vi.fn()
    const boom = vi.fn(() => {
      throw new Error('refetch failed')
    })
    const ok2 = vi.fn().mockResolvedValue(undefined)
    router.registerReconnectResync(ok1)
    router.registerReconnectResync(boom)
    router.registerReconnectResync(ok2)
    const { reconnect } = initWithFakeWs()

    await expect(reconnect()).resolves.toBeUndefined()

    expect(ok1).toHaveBeenCalledTimes(1)
    expect(ok2).toHaveBeenCalledTimes(1)
  })

  it('init wires exactly ONE connection listener that fires only on reconnect', async () => {
    let connectionHandler = null
    const fakeWs = {
      on: vi.fn(),
      onConnectionChange: vi.fn((cb) => {
        connectionHandler = cb
        return vi.fn()
      }),
    }
    const resync = vi.fn()
    router.registerReconnectResync(resync)

    router.initWebsocketEventRouter({ wsStore: fakeWs })

    expect(fakeWs.onConnectionChange).toHaveBeenCalledTimes(1)

    // First connect (not a reconnect) → no resync.
    await connectionHandler({ state: 'connected', isReconnect: false })
    expect(resync).not.toHaveBeenCalled()

    // Reconnect (automatic backoff OR manual reconnect()) → resync.
    await connectionHandler({ state: 'connected', isReconnect: true })
    expect(resync).toHaveBeenCalledTimes(1)

    // A plain disconnect event → no resync.
    await connectionHandler({ state: 'disconnected' })
    expect(resync).toHaveBeenCalledTimes(1)
  })
})
