/**
 * FE-6059 — request de-duplication + short-TTL (perf "API chattiness" pass).
 *
 * Edition Scope: CE (products = CE+SaaS core de-dupe primitive). The SaaS
 * account/status cases that exercise @/saas/services/account live in
 * frontend/src/saas/services/__tests__/accountDedupe.spec.js — importing the
 * saas/ service here would break the CE/SaaS import boundary (CE strips saas/
 * on export, so a static @/saas import breaks CE `npm test`). See INF-9049.
 *
 * DoD: N concurrent calls to a de-duped endpoint produce exactly ONE network
 * request. Also covers the short TTL window and the force-bypass path.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// tests/setup.js installs a global stub mock of '@/services/api'. This spec must
// exercise the REAL de-dupe implementation, so override that mock for this file
// only by re-exporting the actual module (a file-level vi.mock takes precedence
// over the setup-file mock).
vi.mock('@/services/api', async (importOriginal) => await importOriginal())

import { api, apiClient, __resetRequestDedupe } from '@/services/api'

describe('FE-6059 request de-duplication', () => {
  beforeEach(() => {
    __resetRequestDedupe()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
    __resetRequestDedupe()
  })

  it('collapses N concurrent api.products.list() calls into ONE network request', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: [{ id: 1 }] })

    const results = await Promise.all([
      api.products.list(),
      api.products.list(),
      api.products.list(),
      api.products.list(),
      api.products.list(),
    ])

    expect(get).toHaveBeenCalledTimes(1)
    // Every concurrent caller receives the same resolved payload.
    for (const r of results) expect(r.data).toEqual([{ id: 1 }])
  })

  it('serves products.list() from cache within the short TTL, then refetches after it expires', async () => {
    vi.useFakeTimers()
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: [] })

    await api.products.list()
    await api.products.list() // within the 1.5s TTL -> cached, no new request
    expect(get).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(1600) // past the TTL
    await api.products.list()
    expect(get).toHaveBeenCalledTimes(2)
  })

  it('keys de-dupe by params so a filtered list does not collide with the bare list', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: [] })

    await Promise.all([api.products.list(), api.products.list({ q: 'x' })])

    expect(get).toHaveBeenCalledTimes(2)
  })

  it('a rejected request is not cached — the next call retries', async () => {
    const get = vi
      .spyOn(apiClient, 'get')
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce({ data: [{ id: 2 }] })

    await expect(api.products.list()).rejects.toThrow('boom')
    const ok = await api.products.list()

    expect(get).toHaveBeenCalledTimes(2)
    expect(ok.data).toEqual([{ id: 2 }])
  })
})
