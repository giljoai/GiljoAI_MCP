/**
 * Regression test — realtime/reconnect refresh must NOT clobber the active filter.
 *
 * Bug (live on prod): selecting "Completed" showed the completed rows briefly,
 * then the list reverted to the inactive/active default. Cause: a WS event
 * (`project:created`) — or the reconnect resync — called a BARE `fetchProjects()`,
 * which refetches the active-lifecycle default. Because it landed with a newer
 * `fetchSeq` than the user's filter fetch, it legitimately won and overwrote the
 * filtered view. The fetchSeq guard can't help — the bare call is genuinely later.
 *
 * Fix: those refreshers call `refreshList()`, which replays `_lastListOpts` (the
 * current filter/sort/page) instead of a bare default.
 *
 * Edition Scope: CE
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectStore } from '@/stores/projects'

const { mockList } = vi.hoisted(() => ({ mockList: vi.fn() }))

vi.mock('@/services/api', () => ({
  api: { projects: { list: mockList, get: vi.fn() } },
  default: { projects: { list: mockList, get: vi.fn() } },
}))

vi.mock('@/stores/products', () => ({
  useProductStore: () => ({ currentProductId: 'prod-1' }),
}))

const COMPLETED = { id: 'c1', name: 'Done', status: 'completed', product_id: 'prod-1' }

describe('projects store — refreshList preserves the active filter (flash-revert fix)', () => {
  let store

  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    store = useProjectStore()
  })

  it('refreshList replays the last server-mode query (statuses), not a bare default', async () => {
    mockList.mockResolvedValueOnce({ data: [COMPLETED], headers: { 'x-total-count': '1' } })
    await store.fetchProjects({ statuses: ['completed'], limit: 10, offset: 0, sort: 'created_at', sortDir: 'desc' })
    expect(store.projects).toEqual([COMPLETED])

    mockList.mockResolvedValueOnce({ data: [COMPLETED], headers: { 'x-total-count': '1' } })
    await store.refreshList()

    const lastParams = mockList.mock.calls.at(-1)[0]
    expect(lastParams.statuses).toEqual(['completed'])
    expect(lastParams).not.toHaveProperty('include_completed')
    expect(store.projects).toEqual([COMPLETED])
  })

  it('a BARE fetchProjects() while a filter is active replays it (products-store/post-create clobber)', async () => {
    // user filters to completed (server mode now active)
    mockList.mockResolvedValueOnce({ data: [COMPLETED], headers: { 'x-total-count': '29' } })
    await store.fetchProjects({ statuses: ['completed'], limit: 10, offset: 0 })
    expect(store.projects).toEqual([COMPLETED])

    // the products store (or a post-create reload) fires a BARE fetchProjects().
    // Without the guard this would request the active-lifecycle default and
    // clobber the filtered view. The guard replays statuses=completed instead, so
    // the server returns completed rows (not the inactive default).
    mockList.mockResolvedValueOnce({ data: [COMPLETED], headers: { 'x-total-count': '29' } })
    await store.fetchProjects()

    const lastParams = mockList.mock.calls.at(-1)[0]
    expect(lastParams.statuses).toEqual(['completed'])
    expect(lastParams).not.toHaveProperty('include_completed')
    expect(store.projects).toEqual([COMPLETED]) // not clobbered to inactive
  })

  it('clearListQuery() releases the guard so a later bare fetch returns the default', async () => {
    mockList.mockResolvedValueOnce({ data: [COMPLETED], headers: { 'x-total-count': '29' } })
    await store.fetchProjects({ statuses: ['completed'], limit: 10, offset: 0 })

    store.clearListQuery() // Projects page unmounted

    const INACTIVE = { id: 'i1', name: 'Idle', status: 'inactive', product_id: 'prod-1' }
    mockList.mockResolvedValueOnce({ data: [INACTIVE], headers: {} })
    await store.fetchProjects() // a different view wants the default list

    const lastParams = mockList.mock.calls.at(-1)[0]
    expect(lastParams).not.toHaveProperty('statuses')
    expect(store.projects).toEqual([INACTIVE])
  })

  it("a realtime 'created' event refreshes WITH the filter — no revert to inactive", async () => {
    mockList.mockResolvedValueOnce({ data: [COMPLETED], headers: { 'x-total-count': '1' } })
    await store.fetchProjects({ statuses: ['completed'], limit: 10, offset: 0 })
    expect(store.projects).toEqual([COMPLETED])

    // WS 'created' event arrives — must re-query the SAME filter, not bare.
    mockList.mockResolvedValueOnce({ data: [COMPLETED], headers: { 'x-total-count': '1' } })
    store.handleRealtimeUpdate({ project_id: 'x', update_type: 'created' })
    await vi.waitFor(() => expect(mockList).toHaveBeenCalledTimes(2))

    const lastParams = mockList.mock.calls.at(-1)[0]
    expect(lastParams.statuses).toEqual(['completed'])
    expect(store.projects).toEqual([COMPLETED])
  })
})
