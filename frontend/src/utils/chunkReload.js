// FE-6120: auto-recover from a stale lazy-chunk after a deploy.
// Edition Scope: Both.
//
// A browser tab still running a PRIOR build holds the old index.html in memory.
// When it lazy-loads a route chunk whose hashed filename no longer exists on the
// server, the SPA catch-all returns index.html (Content-Type: text/html), so the
// dynamic import throws ("Failed to fetch dynamically imported module" /
// "Refused to apply style ... MIME type ('text/html')") and the route never
// mounts. The fix: detect that specific failure and trigger ONE guarded full
// page reload so the browser pulls the fresh index.html + new chunk hashes and
// lands on the intended route. A sessionStorage sentinel (per-path, timestamped)
// prevents an infinite reload loop when an asset is genuinely missing/broken.
//
// This is a small pure helper wired into the EXISTING global error surfaces
// (main.js `vite:preloadError` listener + router.onError) — not a new
// layer/store/manager.

const SENTINEL_PREFIX = 'giljo:chunk-reload:'

// How long after a reload we still consider it "just tried". If a chunk import
// fails again for the same path inside this window, the asset is genuinely gone
// (not merely stale) and we surface a toast instead of reloading again. Long
// enough to cover a reload round-trip; short enough that a later genuine
// re-navigation to the same route after a NEW deploy reloads fresh.
const RELOAD_WINDOW_MS = 10000

const STALE_MESSAGE = 'A new version is available — please refresh the page.'

// Match the browser/Vite wording for a failed dynamic import or preload, plus
// the MIME-type refusal that happens when index.html (text/html) is served in
// place of a missing .js/.css asset.
const CHUNK_ERROR_PATTERNS = [
  /failed to fetch dynamically imported module/i,
  /error loading dynamically imported module/i,
  /importing a module script failed/i,
  /dynamically imported module/i,
  /unable to preload css/i,
  /failed to load module script/i,
  /expected a javascript[ -]?module/i,
  /mime type \(['"]text\/html['"]\)/i,
]

/**
 * Return true when `error` looks like a stale-chunk / failed-dynamic-import
 * failure (as opposed to an ordinary runtime error we must not swallow).
 * Accepts an Error, an event-like object, or a plain string.
 */
export function isChunkLoadError(error) {
  if (!error) return false
  const message =
    typeof error === 'string'
      ? error
      : error.message || (error.reason && error.reason.message) || String(error)
  if (!message) return false
  return CHUNK_ERROR_PATTERNS.some((re) => re.test(message))
}

function notifyStale(toast) {
  if (typeof toast === 'function') {
    toast(STALE_MESSAGE, { timeout: 0 })
    return
  }
  if (typeof window === 'undefined') return
  if (window.$toast && typeof window.$toast.warning === 'function') {
    window.$toast.warning(STALE_MESSAGE, { timeout: 0 })
    return
  }
  if (typeof window.dispatchEvent === 'function') {
    window.dispatchEvent(
      new CustomEvent('show-toast', {
        detail: { message: STALE_MESSAGE, type: 'warning', timeout: 0 },
      })
    )
  }
}

/**
 * Trigger a ONE-TIME guarded full reload to recover from a stale lazy-chunk.
 *
 * Guard: a per-path, timestamped sessionStorage sentinel. If we already reloaded
 * for this path within RELOAD_WINDOW_MS and the import STILL failed, we do NOT
 * reload again (the asset is genuinely broken) — we surface a warning toast.
 *
 * @param {string} key  Per-route key (defaults to the current pathname).
 * @param {object} deps Injectable seams for testing: { reload, storage, toast, now }.
 * @returns {boolean} true if a reload was triggered, false if suppressed.
 */
export function maybeReloadForChunkError(key, deps = {}) {
  const hasWindow = typeof window !== 'undefined'
  const pathKey = key || (hasWindow ? window.location.pathname : '/')
  const storage = deps.storage || (hasWindow ? window.sessionStorage : null)
  const reload = deps.reload || (() => window.location.reload())
  const nowFn = deps.now || (() => Date.now())
  const sentinelKey = SENTINEL_PREFIX + pathKey

  let last = 0
  try {
    last = storage ? Number(storage.getItem(sentinelKey)) || 0 : 0
  } catch {
    last = 0
  }

  const ts = nowFn()
  if (last && ts - last < RELOAD_WINDOW_MS) {
    // Already reloaded for this path very recently and it failed again ->
    // genuinely missing asset, not just stale. Do not loop; tell the user.
    notifyStale(deps.toast)
    return false
  }

  try {
    if (storage) storage.setItem(sentinelKey, String(ts))
  } catch {
    // sessionStorage unavailable (private mode / disabled): without persistence
    // we cannot loop-guard, but a single reload is still the right first move
    // and the browser will not tight-loop on one navigation.
  }

  reload()
  return true
}

export const __testing = { SENTINEL_PREFIX, RELOAD_WINDOW_MS, STALE_MESSAGE }
