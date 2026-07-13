/**
 * useProjectFilters.spec.js — BE-6076 (server-driven; supersedes the BE-6078
 * client-side filtering spec).
 *
 * Edition Scope: CE.
 *
 * BE-6076 moved search + multi-status + hidden filtering AND sort + pagination
 * into SQL, so the composable no longer slices the list client-side — it owns
 * the control state and builds the SERVER query. These tests preserve the
 * BE-6078 UX intent, now asserted on `buildServerParams`:
 *  - Status MULTI-SELECT defaults to all-checked, persisted in localStorage; the
 *    selection becomes the server `statuses` param. Unchecking removes a status
 *    from the emitted set; an empty selection emits `[]` (empty page).
 *  - Search is "nuclear": a query drops the status multi-select server-side.
 *  - Hidden is a separate axis: "Show hidden" sets `includeHidden`; `hiddenCount`
 *    still drives the "Show hidden (N)" badge.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { ref, nextTick } from 'vue'
import { useProjectFilters } from './useProjectFilters'

describe('useProjectFilters (BE-6076 server-driven params)', () => {
  const makeProjectStatuses = () => [
    { value: 'inactive', label: 'Inactive' },
    { value: 'active', label: 'Active' },
    { value: 'completed', label: 'Completed' },
    { value: 'cancelled', label: 'Cancelled' },
    { value: 'terminated', label: 'Terminated' },
    { value: 'deleted', label: 'Deleted' },
  ]

  let hiddenProjects
  let activeProduct
  let projectStatuses
  let showHidden

  beforeEach(() => {
    // The global test setup stubs localStorage with no-op vi.fn()s; back it with
    // a real in-memory store so the persistence path is exercised end-to-end.
    const store = new Map()
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: (k) => (store.has(k) ? store.get(k) : null),
        setItem: (k, v) => store.set(k, String(v)),
        removeItem: (k) => store.delete(k),
        clear: () => store.clear(),
      },
      writable: true,
      configurable: true,
    })
    hiddenProjects = ref([
      { id: 'p6', name: 'Hidden Backend', product_id: 'prod-1', deleted_at: null },
      { id: 'p7', name: 'Hidden No Type', product_id: 'prod-1', deleted_at: null },
    ])
    activeProduct = ref({ id: 'prod-1', name: 'Test Product' })
    projectStatuses = ref(makeProjectStatuses())
    showHidden = ref(false)
  })

  const make = () => useProjectFilters({ activeProduct, projectStatuses, hiddenProjects, showHidden })

  it('defaults the status multi-select to all SELECTABLE statuses (excludes deleted)', () => {
    const { selectedStatuses } = make()
    expect(selectedStatuses.value).toEqual([
      'inactive',
      'active',
      'completed',
      'cancelled',
      'terminated',
    ])
  })

  it('emits the default selectable status set as the server `statuses` param', async () => {
    const { buildServerParams } = make()
    await nextTick()
    const params = buildServerParams()
    expect(params.statuses).toEqual([
      'inactive',
      'active',
      'completed',
      'cancelled',
      'terminated',
    ])
    // pagination + default sort travel with the query
    expect(params.limit).toBe(10)
    expect(params.offset).toBe(0)
    expect(params.sort).toBe('created_at')
    expect(params.sortDir).toBe('desc')
  })

  it('unchecking a status removes it from the emitted server filter', async () => {
    const { buildServerParams, selectedStatuses } = make()
    await nextTick()
    selectedStatuses.value = ['active', 'inactive']
    expect(buildServerParams().statuses).toEqual(['active', 'inactive'])
  })

  it('an empty selection emits an empty statuses array (store renders an empty page)', async () => {
    const { buildServerParams, selectedStatuses } = make()
    await nextTick()
    selectedStatuses.value = []
    expect(buildServerParams().statuses).toEqual([])
  })

  it('persists the status selection across reload (localStorage)', async () => {
    const first = make()
    await nextTick()
    first.selectedStatuses.value = ['active']
    await nextTick()
    expect(JSON.parse(localStorage.getItem('giljo.projects.selectedStatuses'))).toEqual(['active'])

    // A fresh instance (simulating reload) loads the persisted selection and
    // emits it as the server filter.
    const second = make()
    expect(second.selectedStatuses.value).toEqual(['active'])
    expect(second.buildServerParams().statuses).toEqual(['active'])
  })

  it('search is "nuclear" — emits search and DROPS the status multi-select', async () => {
    const { buildServerParams, searchQuery, selectedStatuses } = make()
    await nextTick()
    selectedStatuses.value = [] // even with nothing checked...
    searchQuery.value = 'cancelled'
    const params = buildServerParams()
    expect(params.search).toBe('cancelled') // ...search still matches across statuses
    expect(params.statuses).toBeUndefined()
  })

  it('search is "nuclear" over the hidden axis too — emits includeHidden so archived rows are findable (BE-2002)', async () => {
    const { buildServerParams, searchQuery } = make()
    await nextTick()
    // Default (no search, no toggle) leaves archived excluded — default view unchanged.
    expect(buildServerParams().includeHidden).toBeUndefined()
    // A non-empty search must reveal archived (hidden) rows so a user can find
    // something they archived (the SEC-0013 miss this project fixes).
    searchQuery.value = 'sec-0013'
    expect(buildServerParams().includeHidden).toBe(true)
  })

  it('"Show hidden" adds include_hidden to the server query', async () => {
    const { buildServerParams } = make()
    await nextTick()
    expect(buildServerParams().includeHidden).toBeUndefined()
    showHidden.value = true
    expect(buildServerParams().includeHidden).toBe(true)
  })

  it('hiddenCount reflects active-product, non-deleted hidden rows', () => {
    const { hiddenCount } = make()
    expect(hiddenCount.value).toBe(2)
  })

  it('pagination offset tracks the current page + page size', async () => {
    const f = make()
    await nextTick()
    f.currentPage.value = 3
    f.itemsPerPage.value = 25
    const params = f.buildServerParams()
    expect(params.limit).toBe(25)
    expect(params.offset).toBe(50)
  })

  it('sortBy drives the server sort key + direction', async () => {
    const f = make()
    await nextTick()
    f.sortBy.value = [{ key: 'name', order: 'asc' }]
    const params = f.buildServerParams()
    expect(params.sort).toBe('name')
    expect(params.sortDir).toBe('asc')
  })

  it('statusSelectOptions excludes "deleted" (Deleted dialog) and the "hidden" pseudo-option', () => {
    const { statusSelectOptions } = make()
    const values = statusSelectOptions.value.map((o) => o.value)
    expect(values).toEqual(['inactive', 'active', 'completed', 'cancelled', 'terminated'])
    expect(values).not.toContain('deleted')
    expect(values).not.toContain('hidden')
  })

  it('no longer exposes the removed client-side filtering surface', () => {
    const api = make()
    expect(api.filteredProjects).toBeUndefined()
    expect(api.filteredBySearch).toBeUndefined()
    expect(api.typeSelectOptions).toBeUndefined()
    expect(api.clearFilters).toBeUndefined()
  })
})
