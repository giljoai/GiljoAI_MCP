/**
 * API failure handling (FE-9175 — axios refresh single-flight failure
 * normalization).
 *
 * Client-independent failure helpers for the api.js interceptors:
 *
 * - handleAuthFailure: the shared "session is dead" exit path — route-meta
 *   aware (public routes never bounce), fresh-install aware (/welcome), and
 *   otherwise redirects to /login with a redirect query.
 * - normalizeRejection: guarantees every rejection leaving the response
 *   interceptor is an Error (or an axios-shaped object) the app can handle
 *   deliberately, never a value whose property access throws a secondary
 *   TypeError that masks the real failure.
 *
 * Extracted from api.js (FE-9175) to keep api.js under the 800-line CI
 * guardrail — same precedent as sequenceRunsApi.js. Neither function touches
 * apiClient, so there is no circular import.
 */

export async function handleAuthFailure(error) {
  const { default: router } = await import('@/router')

  // Route-meta-aware: honor the target route's `meta.requiresAuth`. Public
  // routes (SaaS /landing, /register, /reset-password; CE /welcome,
  // /login, /server-down) all declare `requiresAuth: false` and must never
  // be redirected to /login on a background 401 (e.g. a pre-auth GET
  // /api/auth/me fired by DefaultLayout during initial bootstrap before
  // the router has settled on the real route).
  //
  // We resolve against window.location.pathname because router.currentRoute
  // still points at START_LOCATION during the very first navigation, when
  // this race fires. The URL bar is the authoritative signal at that point.
  try {
    const resolved = router.resolve(window.location.pathname + window.location.search)
    if (resolved?.meta?.requiresAuth === false) {
      return Promise.reject(error)
    }
  } catch {
    // Resolution failed -- fall through to legacy path-based handling.
  }

  try {
    const { default: setupService } = await import('@/services/setupService')
    const setupData = await setupService.checkEnhancedStatus()
    if (setupData.is_fresh_install) {
      router.push('/welcome')
      return Promise.reject(error)
    }
  } catch {
    // Secure fallback to login
  }

  const currentPath = window.location.pathname + window.location.search
  if (!currentPath.includes('/login') && !currentPath.includes('/welcome')) {
    router.push({ path: '/login', query: { redirect: currentPath } })
  }
  return Promise.reject(error)
}

// FE-9175: every rejection leaving the response interceptor must be an Error
// the app can handle deliberately. Interceptors and adapters can reject with
// non-Axios shapes (null, bare strings, plain objects); property access like
// `error.config` on those raised a secondary TypeError that masked the real
// failure. Error instances (all Axios errors incl. CanceledError) pass as-is.
export function normalizeRejection(value) {
  if (value instanceof Error) return value
  // Axios-shaped plain objects (a response or config present) keep their
  // shape: the 401/403 branches and downstream interceptors read those
  // properties, and property access on an object is already safe.
  if (value && typeof value === 'object' && (value.response || value.config)) {
    return value
  }
  const normalized = new Error(
    typeof value === 'string' && value ? value : 'An unexpected error occurred',
  )
  normalized.errorCode = 'UNKNOWN_ERROR'
  normalized.cause = value
  normalized.isNormalizedRejection = true
  return normalized
}
