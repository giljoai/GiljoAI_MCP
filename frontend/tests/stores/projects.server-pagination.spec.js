/**
 * projects store — BE-6076 server-side pagination/search/sort param mapping.
 *
 * fetchProjects gained opt-in server-mode params (statuses/search/sort/limit/
 * offset/includeHidden) and reads the filtered total from the X-Total-Count
 * header into `projectsTotal`. The legacy bare/includeCompleted/statusFilter
 * paths are unchanged (covered by projects.status-filter.spec.js).
 *
 * Edition Scope: CE
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectStore } from '@/stores/projects'

const { mockList } = vi.hoisted(() => ({ mockList: vi.fn() }))

vi.mock('@/services/api', () => ({
  api: { projects: { list: mockList, getActive: vi.fn() } },
  default: { projects: { list: mockList, getActive: vi.fn() } },
}))

vi.mock('@/stores/products', () => ({
  useProductStore: () => ({ currentProductId: 'prod-1' }),
}))

const ROW = { id: 'p1', name: 'Alpha', status: 'inactive', product_id: 'prod-1' }

describe('projects store — BE-6076 server-mode fetchProjects', () => {
  let store

  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    store = useProjectStore()
  })

  it('maps multi-status/search/sort/pagination to the right query params', async () => {
    mockList.mockResolvedValueOnce({ data: [ROW], headers: { 'x-total-count': '42' } })

    await store.fetchProjects({
      statuses: ['active', 'inactive'],
      sort: 'series_number',
      sortDir: 'desc',
      limit: 10,
      offset: 20,
    })

    const params = mockList.mock.calls[0][0]
    expect(params.statuses).toEqual(['active', 'inactive'])
    expect(params.sort).toBe('series_number')
    expect(params.sort_dir).toBe('desc')
    expect(params.limit).toBe(10)
    expect(params.offset).toBe(20)
    expect(params.product_id).toBe('prod-1')
  })

  it('reads X-Total-Count into projectsTotal (the :items-length total)', async () => {
    mockList.mockResolvedValueOnce({ data: [ROW], headers: { 'x-total-count': '137' } })
    await store.fetchProjects({ statuses: ['active'], limit: 10, offset: 0 })
    expect(store.projectsTotal).toBe(137)
    expect(store.projects).toHaveLength(1)
  })

  it('nuclear search adds include_completed and omits statuses', async () => {
    mockList.mockResolvedValueOnce({ data: [], headers: {} })
    await store.fetchProjects({ search: 'login', limit: 10, offset: 0 })
    const params = mockList.mock.calls[0][0]
    expect(params.search).toBe('login')
    expect(params.include_completed).toBe(true)
    expect(params).not.toHaveProperty('statuses')
  })

  it('Show hidden sets include_hidden=true', async () => {
    mockList.mockResolvedValueOnce({ data: [], headers: {} })
    await store.fetchProjects({ statuses: ['active'], includeHidden: true, limit: 10, offset: 0 })
    expect(mockList.mock.calls[0][0].include_hidden).toBe(true)
  })

  it('empty statuses selection short-circuits to an empty page (no request)', async () => {
    await store.fetchProjects({ statuses: [], limit: 10, offset: 0 })
    expect(mockList).not.toHaveBeenCalled()
    expect(store.projects).toEqual([])
    expect(store.projectsTotal).toBe(0)
  })

  it('falls back to row count for projectsTotal when no header is present', async () => {
    mockList.mockResolvedValueOnce({ data: [ROW, { ...ROW, id: 'p2' }] })
    await store.fetchProjects()
    expect(store.projectsTotal).toBe(2)
  })
})
