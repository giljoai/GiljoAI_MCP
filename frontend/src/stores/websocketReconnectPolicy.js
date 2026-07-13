/**
 * Reconnect policy for the WebSocket store (FE-9056).
 *
 * The store's exponential-backoff ladder gives up after maxReconnectAttempts
 * (~3 min total). Before this fix, any server restart or Railway deploy longer
 * than that left every open tab frozen — the red orb showed but data views
 * never received live updates again until a manual reload.
 *
 * This policy takes over AFTER the fast-retry cap is reached. It keeps a slow
 * heartbeat retry going (every slowRetryDelay ms) and re-arms an IMMEDIATE
 * reconnect whenever the browser signals the connection may be recoverable:
 *   - window 'online'                — the network came back
 *   - document visibilitychange->visible — the tab was refocused
 *
 * It owns no socket and no store state: the caller supplies onReconnectNeeded,
 * which performs the actual reconnect attempt (guarded so an already-open
 * connection is a no-op). arm()/disarm() are idempotent and disarm() removes
 * every listener + timer, so there is no leak across connect/disconnect cycles.
 */
export function createReconnectPolicy({ onReconnectNeeded, slowRetryDelay = 60000, log = () => {} }) {
  let slowRetryTimer = null
  let armed = false

  const hasWindow = typeof window !== 'undefined'
  const hasDocument = typeof document !== 'undefined'

  function handleOnline() {
    log('Network online — attempting immediate reconnect')
    onReconnectNeeded('online')
  }

  function handleVisibility() {
    if (hasDocument && document.visibilityState === 'visible') {
      log('Tab visible — attempting immediate reconnect')
      onReconnectNeeded('visibility')
    }
  }

  function arm() {
    if (armed) {
      return
    }
    armed = true
    slowRetryTimer = setInterval(() => onReconnectNeeded('slow-retry'), slowRetryDelay)
    if (hasWindow) {
      window.addEventListener('online', handleOnline)
    }
    if (hasDocument) {
      document.addEventListener('visibilitychange', handleVisibility)
    }
    log(`Reconnect policy armed (slow retry every ${slowRetryDelay}ms + online/visibility re-arm)`)
  }

  function disarm() {
    if (!armed) {
      return
    }
    armed = false
    if (slowRetryTimer) {
      clearInterval(slowRetryTimer)
      slowRetryTimer = null
    }
    if (hasWindow) {
      window.removeEventListener('online', handleOnline)
    }
    if (hasDocument) {
      document.removeEventListener('visibilitychange', handleVisibility)
    }
    log('Reconnect policy disarmed')
  }

  return {
    arm,
    disarm,
    isArmed: () => armed,
  }
}
