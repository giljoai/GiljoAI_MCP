/**
 * Regression test — repeatable query-param serialization (Projects status filter).
 *
 * Bug: the Projects-page Status multi-select sends `params.statuses = [...]`.
 * Axios 1.x's DEFAULT serializer emits bracketed `statuses[]=completed`, which
 * FastAPI's `statuses: list[str]` param does NOT bind — it stays None and the
 * endpoint falls back to its active-lifecycle default, so selecting "completed"
 * returned inactive rows. The pre-existing store test mocked `api.projects.list`
 * and only asserted the params OBJECT, so it never exercised serialization and
 * could not catch this.
 *
 * This test exercises the REAL configured axios instance (`apiClient`) at the
 * serialization boundary — the layer the bug lived in — via `getUri`, which
 * applies the instance `paramsSerializer`.
 *
 * Edition Scope: CE
 */
import { beforeAll, describe, expect, it, vi } from 'vitest'

// tests/setup.js globally mocks '@/services/api'; load the REAL module so we
// exercise the actual configured axios instance (the serialization boundary).
let apiClient
beforeAll(async () => {
  ;({ apiClient } = await vi.importActual('@/services/api'))
})

describe('apiClient paramsSerializer — FastAPI-compatible repeated array params', () => {
  it('serializes array params as repeated bare keys, NOT bracketed', () => {
    const uri = decodeURIComponent(
      apiClient.getUri({ url: '/api/v1/projects/', params: { statuses: ['completed', 'active'] } }),
    )
    // FastAPI binds `?statuses=completed&statuses=active`
    expect(uri).toContain('statuses=completed')
    expect(uri).toContain('statuses=active')
    // The default (broken) form must never reappear.
    expect(uri).not.toContain('statuses[]')
  })

  it('single-element array still serializes to a bare key', () => {
    const uri = decodeURIComponent(
      apiClient.getUri({ url: '/api/v1/projects/', params: { statuses: ['completed'] } }),
    )
    expect(uri).toContain('statuses=completed')
    expect(uri).not.toContain('statuses[]')
  })

  it('scalar params are unaffected', () => {
    const uri = decodeURIComponent(
      apiClient.getUri({ url: '/api/v1/projects/', params: { product_id: 'p1', limit: 10, search: 'BE-50' } }),
    )
    expect(uri).toContain('product_id=p1')
    expect(uri).toContain('limit=10')
    expect(uri).toContain('search=BE-50')
  })
})
