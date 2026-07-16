/**
 * api.js 401 refresh single-flight -- failure normalization (FE-9175).
 *
 * Regression for the refresh-hang defect: when a token refresh was in
 * flight, concurrent 401'd requests were parked in `refreshSubscribers`
 * with only their `resolve` wired. The sole flush (`onRefreshed()`) ran on
 * refresh SUCCESS; the failure path cleared the subscriber list without
 * settling the parked promises, so every awaiting caller other than the
 * one that triggered the refresh hung forever (stuck spinners, no error).
 * `silentRefresh()` shared `isRefreshing` but never flushed the queue,
 * opening a second hang window on an otherwise-healthy session.
 *
 * Also covers failure-shape normalization: a non-Axios rejected value
 * (null, a bare string) must leave the interceptor as a deliberate Error
 * the app can handle -- never a secondary TypeError from `error.config`
 * property access -- and must not disturb auth state. Cancellation must
 * pass through untouched so `axios.isCancel()` keeps working at call sites.
 *
 * Strategy (house pattern, see tests/saas/apiInterceptorPublicRoutes.spec.js):
 * import the real module fresh per test, replace the axios adapter so no
 * network is touched, and invoke the registered response-error handler
 * directly with fabricated 401 errors. The refresh POST itself goes through
 * the real apiClient and is settled manually via a deferred adapter entry,
 * which lets the test interleave "second 401 arrives while refresh is in
 * flight" deterministically.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import axios from 'axios'

// Global test setup replaces @/services/api with a shallow mock that lacks
// apiClient and the real interceptor. Unmock so the real module loads.
vi.unmock('@/services/api')

vi.mock('@/router', () => {
  const requiresAuthFalse = new Set(['/login', '/welcome', '/server-down'])
  const resolve = vi.fn((path) => {
    const normalized = String(path).split('?')[0]
    return {
      path: normalized,
      meta: { requiresAuth: requiresAuthFalse.has(normalized) ? false : true },
    }
  })
  return {
    default: {
      resolve,
      push: vi.fn(),
      currentRoute: { value: { meta: {} } },
    },
  }
})

vi.mock('@/services/setupService', () => ({
  default: {
    checkEnhancedStatus: vi.fn(() => Promise.resolve({ is_fresh_install: false })),
  },
}))

function mockLocation(path) {
  Object.defineProperty(window, 'location', {
    writable: true,
    configurable: true,
    value: { pathname: path, search: '' },
  })
}

function deferred() {
  let resolve, reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

/** Observe a promise without letting a hang block the test: resolves to
 *  { state: 'resolved' | 'rejected' | 'hung', value?, reason? }. */
function outcome(promise, ms = 400) {
  return Promise.race([
    promise.then(
      (value) => ({ state: 'resolved', value }),
      (reason) => ({ state: 'rejected', reason }),
    ),
    new Promise((res) => setTimeout(() => res({ state: 'hung' }), ms)),
  ])
}

function make401(url) {
  return Object.assign(new Error('Request failed with status code 401'), {
    isAxiosError: true,
    config: { url, method: 'get', headers: {} },
    response: { status: 401, data: {}, headers: {} },
  })
}

function networkError(url) {
  return Object.assign(new Error('Network Error'), {
    isAxiosError: true,
    config: { url, method: 'post', headers: {} },
    // no `response` -- adapter-level failure
  })
}

function okResponse(config) {
  return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
}

/** Fresh real module + interceptor handles + a manual-settle adapter. */
async function setup() {
  mockLocation('/home')
  vi.resetModules()
  const apiModule = await import('@/services/api.js')
  const { apiClient } = apiModule

  // Every POST /api/auth/refresh yields a deferred the test settles manually;
  // every other request resolves 200 immediately (a successful retry).
  const refreshCalls = []
  apiClient.defaults.adapter = vi.fn((config) => {
    if (String(config.url).includes('/api/auth/refresh')) {
      const d = deferred()
      refreshCalls.push(d)
      return d.promise
    }
    return Promise.resolve(okResponse(config))
  })

  const handlers = apiClient.interceptors.response.handlers.filter(Boolean)
  const { fulfilled, rejected } = handlers[handlers.length - 1]
  const router = (await import('@/router')).default
  return { apiClient, fulfilled, rejected, refreshCalls, router }
}

async function waitForRefreshCall(refreshCalls, count = 1) {
  await vi.waitFor(() => {
    if (refreshCalls.length < count) throw new Error('refresh POST not issued yet')
  })
}

describe('api.js 401 refresh single-flight -- failure normalization (FE-9175)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // The interceptor logs every error path; keep test output readable.
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  it('refresh FAILURE settles ALL parked concurrent 401 requests (none hang) and bounces to /login', async () => {
    const { rejected, refreshCalls, router } = await setup()

    // Request A triggers the refresh.
    const errA = make401('/api/v1/projects/')
    const pA = outcome(rejected(errA))
    await waitForRefreshCall(refreshCalls)

    // Requests B and C 401 while the refresh is in flight -> parked.
    const errB = make401('/api/v1/tasks/')
    const errC = make401('/api/v1/templates/')
    const pB = outcome(rejected(errB))
    const pC = outcome(rejected(errC))

    // The refresh fails.
    refreshCalls[0].reject(networkError('/api/auth/refresh'))

    const [a, b, c] = await Promise.all([pA, pB, pC])
    expect(a.state).toBe('rejected')
    // THE BUG: b and c hung forever (state 'hung') -- their reject was never wired.
    expect(b.state).toBe('rejected')
    expect(c.state).toBe('rejected')
    // Each parked caller gets its own original 401 back, not a swallowed void.
    expect(b.reason).toBe(errB)
    expect(c.reason).toBe(errC)
    // The auth failure still routes to /login exactly like before.
    expect(router.push).toHaveBeenCalledWith(expect.objectContaining({ path: '/login' }))
  })

  it('a 401 parked during silentRefresh is flushed when the silent refresh settles (second hang window)', async () => {
    const { fulfilled, rejected, refreshCalls } = await setup()

    // Proactive path: a response with a low x-token-expires-in fires silentRefresh().
    fulfilled({ ...okResponse({ url: '/api/v1/products/' }), headers: { 'x-token-expires-in': '100' } })
    await waitForRefreshCall(refreshCalls)

    // A request 401s while the silent refresh is in flight -> parked.
    const errB = make401('/api/v1/tasks/')
    const pB = outcome(rejected(errB))

    // The silent refresh succeeds -- the parked request must be retried, not hang.
    refreshCalls[0].resolve(okResponse({ url: '/api/auth/refresh', method: 'post', headers: {} }))

    const b = await pB
    // THE BUG: silentRefresh never flushed the queue -> state 'hung'.
    expect(b.state).toBe('resolved')
    expect(b.value.config.url).toBe('/api/v1/tasks/')
  })

  it('a null rejection leaves the interceptor as a deliberate normalized Error, not a secondary TypeError', async () => {
    const { rejected, refreshCalls, router } = await setup()

    const o = await outcome(rejected(null))
    expect(o.state).toBe('rejected')
    // THE BUG: `error.config` on null threw TypeError, masking the original failure.
    expect(o.reason).toBeInstanceOf(Error)
    expect(o.reason.isNormalizedRejection).toBe(true)
    expect(o.reason.cause).toBe(null)
    // No auth side effects from garbage shapes: no redirect, single-flight not wedged.
    expect(router.push).not.toHaveBeenCalled()
    const pNext = outcome(rejected(make401('/api/v1/projects/')))
    await waitForRefreshCall(refreshCalls) // a fresh refresh attempt still starts
    refreshCalls[0].resolve(okResponse({ url: '/api/auth/refresh', method: 'post', headers: {} }))
    expect((await pNext).state).toBe('resolved')
  })

  it('a bare-string rejection is wrapped into an Error carrying the original value as cause', async () => {
    const { rejected, router } = await setup()

    const o = await outcome(rejected('boom'))
    expect(o.state).toBe('rejected')
    expect(o.reason).toBeInstanceOf(Error)
    expect(o.reason.isNormalizedRejection).toBe(true)
    expect(o.reason.message).toBe('boom')
    expect(o.reason.cause).toBe('boom')
    expect(router.push).not.toHaveBeenCalled()
  })

  it('cancellation passes through untouched so axios.isCancel() keeps working at call sites', async () => {
    const { rejected, router } = await setup()

    const canceled = new axios.CanceledError('operation canceled')
    const o = await outcome(rejected(canceled))
    expect(o.state).toBe('rejected')
    expect(o.reason).toBe(canceled)
    expect(axios.isCancel(o.reason)).toBe(true)
    expect(router.push).not.toHaveBeenCalled()
  })
})
