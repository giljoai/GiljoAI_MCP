/**
 * Regression test — BE-9141: api.tasks.list passes a bounded default limit.
 *
 * The tasks list read was unbounded. api.tasks.list now injects a sane safety
 * ceiling (limit=500, the endpoint's cap) so the default dashboard read is
 * bounded, while any explicit limit a caller passes still wins.
 *
 * tests/setup.js globally mocks '@/services/api'; load the REAL module so we
 * exercise the actual list wrapper (the layer the default lives in) and spy on
 * the configured axios instance.
 *
 * Edition Scope: CE
 */
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

let api
let apiClient
beforeAll(async () => {
  ;({ default: api, apiClient } = await vi.importActual('@/services/api'))
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('api.tasks.list — BE-9141 default safety ceiling', () => {
  it('injects limit=500 when the caller passes no params', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: [] })
    await api.tasks.list()
    expect(get).toHaveBeenCalledWith('/api/v1/tasks/', { params: { limit: 500 } })
  })

  it('keeps caller filters and still applies the default limit', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: [] })
    await api.tasks.list({ product_id: 'p1', status: 'pending' })
    const { params } = get.mock.calls[0][1]
    expect(params.product_id).toBe('p1')
    expect(params.status).toBe('pending')
    expect(params.limit).toBe(500)
  })

  it('an explicit limit from the caller wins over the default', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: [] })
    await api.tasks.list({ limit: 25, offset: 50 })
    const { params } = get.mock.calls[0][1]
    expect(params.limit).toBe(25)
    expect(params.offset).toBe(50)
  })
})
