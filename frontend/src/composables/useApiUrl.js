/**
 * API URL resolver
 *
 * Single source of truth for building REST and WebSocket base URLs in the
 * frontend. Replaces scattered `${hostname}:${port}` composition that broke
 * deployments behind Cloudflare Tunnel (demo.giljo.ai).
 *
 * Resolution order (API base):
 *   1. VITE_API_URL (absolute http(s) URL) — used verbatim, no port appended.
 *      Used by the demo (VITE_API_URL=https://demo.giljo.ai).
 *   2. window.API_BASE_URL — server-injected runtime override.
 *   3. import.meta.env.DEV — empty string so Vite proxy handles /api and /ws.
 *   4. window.location.origin — same-origin fallback (CE prod, SaaS subdomain
 *      tenants). FastAPI serves dist/ and the API from the same origin.
 *
 * VITE_API_PORT is intentionally NOT considered here. It must never be
 * concatenated with an absolute URL (that was the demo bug). If a deployment
 * needs a non-standard port, set VITE_API_URL=http://host:port explicitly.
 *
 * WebSocket base is always derived from the API base: http->ws, https->wss.
 */

/**
 * Get the REST API base URL for the current deployment.
 * Returns empty string in dev so callers use Vite's proxy via relative URLs.
 * @returns {string}
 */
export function getApiBaseUrl() {
  const envUrl = import.meta.env.VITE_API_URL
  if (envUrl && (envUrl.startsWith('http://') || envUrl.startsWith('https://'))) {
    return envUrl.replace(/\/$/, '')
  }
  if (typeof window !== 'undefined' && window.API_BASE_URL) {
    return window.API_BASE_URL.replace(/\/$/, '')
  }
  if (import.meta.env.DEV) {
    return ''
  }
  if (typeof window !== 'undefined' && window.location) {
    return window.location.origin
  }
  return ''
}

/**
 * Get the WebSocket base URL for the current deployment.
 * Derived from the API base so scheme and host always agree.
 * Returns empty string in dev so callers build relative `/ws/...` URLs.
 * @returns {string}
 */
export function getWsBaseUrl() {
  const base = getApiBaseUrl()
  if (!base) return ''
  return base.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:')
}
