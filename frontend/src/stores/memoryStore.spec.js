/**
 * memoryStore.spec.js — FE-5042
 *
 * Proves the FE-3007 normalized contract + the client-side search/filter/sort
 * the 360 Memory browser relies on:
 *   - _upsertEntry is the single write path (immutable Map replacement).
 *   - fetchMemoryEntries reuses the EXISTING read endpoint and maps
 *     response.data.entries through that one path.
 *   - search (summary/outcomes/decisions/project/tags), tag filter, project
 *     filter, and the four sort modes are correct.
 *   - 1000-entry search is correct AND fast (client-side, trivially <200ms).
 *
 * Edition scope: Both.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const mockGetMemoryEntries = vi.fn()

vi.mock('@/services/api', () => {
  const apiMock = {
    products: {
      getMemoryEntries: (...a) => mockGetMemoryEntries(...a),
    },
  }
  return { api: apiMock, default: apiMock }
})

import { useMemoryStore } from './memoryStore'

function entry(over = {}) {
  return {
    id: over.id || `e-${Math.random().toString(36).slice(2)}`,
    sequence: 1,
    entry_type: 'project_completion',
    source: 'closeout_v1',
    timestamp: '2026-06-01T10:00:00Z',
    project_id: 'p1',
    project_name: 'Alpha',
    summary: 'Did a thing',
    key_outcomes: [],
    decisions_made: [],
    git_commits: [],
    tags: [],
    author_name: 'implementer',
    author_type: 'implementer',
    deleted_by_user: false,
    ...over,
  }
}

describe('memoryStore — FE-5042 normalized owner + client-side search', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('_upsertEntry is the single write path and replaces the Map immutably', () => {
    const store = useMemoryStore()
    const before = store.byId
    store._upsertEntry(entry({ id: 'a' }))
    // New Map reference each write (immutableMapSet — no in-place mutation).
    expect(store.byId).not.toBe(before)
    expect(store.byId.get('a')).toBeTruthy()
    expect(store.entries).toHaveLength(1)

    // Upsert same id overwrites, does not duplicate.
    store._upsertEntry(entry({ id: 'a', summary: 'updated' }))
    expect(store.entries).toHaveLength(1)
    expect(store.byId.get('a').summary).toBe('updated')
  })

  it('fetchMemoryEntries reuses the read endpoint and maps response.data.entries', async () => {
    const store = useMemoryStore()
    mockGetMemoryEntries.mockResolvedValue({
      data: { entries: [entry({ id: 'a' }), entry({ id: 'b' })], total_count: 2, filtered_count: 2 },
    })

    await store.fetchMemoryEntries('prod-1')

    expect(mockGetMemoryEntries).toHaveBeenCalledWith('prod-1', { limit: 100 })
    expect(store.entries).toHaveLength(2)
    expect(store.loadedProductId).toBe('prod-1')
    expect(store.loading).toBe(false)
  })

  it('fetchMemoryEntries records error and leaves store usable on failure', async () => {
    const store = useMemoryStore()
    mockGetMemoryEntries.mockRejectedValue(new Error('boom'))
    await store.fetchMemoryEntries('prod-1')
    expect(store.error).toBe('boom')
    expect(store.loading).toBe(false)
    expect(store.entries).toHaveLength(0)
  })

  it('availableTags and availableProjects are unique + sorted', () => {
    const store = useMemoryStore()
    store._upsertEntry(entry({ id: 'a', tags: ['security', 'bug-fix'], project_id: 'p1', project_name: 'Alpha' }))
    store._upsertEntry(entry({ id: 'b', tags: ['bug-fix', 'architecture'], project_id: 'p2', project_name: 'Beta' }))
    expect(store.availableTags).toEqual(['architecture', 'bug-fix', 'security'])
    expect(store.availableProjects.map((p) => p.name)).toEqual(['Alpha', 'Beta'])
  })

  it('search matches across summary, outcomes, decisions, project, and tags', () => {
    const store = useMemoryStore()
    store._upsertEntry(entry({ id: 'sum', summary: 'Refactored the tenant guard' }))
    store._upsertEntry(entry({ id: 'out', summary: 'x', key_outcomes: ['Closed the CSRF leak'] }))
    store._upsertEntry(entry({ id: 'dec', summary: 'x', decisions_made: ['Chose tsvector later'] }))
    store._upsertEntry(entry({ id: 'tag', summary: 'x', tags: ['security'] }))
    store._upsertEntry(entry({ id: 'proj', summary: 'x', project_name: 'Memory Browser' }))

    store.searchText = 'tenant'
    expect(store.filteredEntries.map((e) => e.id)).toEqual(['sum'])
    store.searchText = 'csrf'
    expect(store.filteredEntries.map((e) => e.id)).toEqual(['out'])
    store.searchText = 'tsvector'
    expect(store.filteredEntries.map((e) => e.id)).toEqual(['dec'])
    store.searchText = 'security'
    expect(store.filteredEntries.map((e) => e.id)).toEqual(['tag'])
    store.searchText = 'browser'
    expect(store.filteredEntries.map((e) => e.id)).toEqual(['proj'])
    // Case-insensitive
    store.searchText = 'TENANT'
    expect(store.filteredEntries.map((e) => e.id)).toEqual(['sum'])
  })

  it('tag filter (ANY-of) and project filter combine with search', () => {
    const store = useMemoryStore()
    store._upsertEntry(entry({ id: 'a', tags: ['security'], project_id: 'p1' }))
    store._upsertEntry(entry({ id: 'b', tags: ['perf'], project_id: 'p1' }))
    store._upsertEntry(entry({ id: 'c', tags: ['security'], project_id: 'p2' }))

    store.selectedTags = ['security']
    expect(store.filteredEntries.map((e) => e.id).sort()).toEqual(['a', 'c'])

    store.selectedProjectId = 'p1'
    expect(store.filteredEntries.map((e) => e.id)).toEqual(['a'])

    store.selectedTags = []
    store.selectedProjectId = 'p1'
    expect(store.filteredEntries.map((e) => e.id).sort()).toEqual(['a', 'b'])
  })

  it('sort modes order by date and sequence in both directions', () => {
    const store = useMemoryStore()
    store._upsertEntry(entry({ id: 'old', timestamp: '2026-01-01T00:00:00Z', sequence: 1 }))
    store._upsertEntry(entry({ id: 'new', timestamp: '2026-06-01T00:00:00Z', sequence: 3 }))
    store._upsertEntry(entry({ id: 'mid', timestamp: '2026-03-01T00:00:00Z', sequence: 2 }))

    store.sortMode = 'date_desc'
    expect(store.filteredEntries.map((e) => e.id)).toEqual(['new', 'mid', 'old'])
    store.sortMode = 'date_asc'
    expect(store.filteredEntries.map((e) => e.id)).toEqual(['old', 'mid', 'new'])
    store.sortMode = 'sequence_desc'
    expect(store.filteredEntries.map((e) => e.id)).toEqual(['new', 'mid', 'old'])
    store.sortMode = 'sequence_asc'
    expect(store.filteredEntries.map((e) => e.id)).toEqual(['old', 'mid', 'new'])
  })

  it('groupedByProjectEntries groups the filtered set by project', () => {
    const store = useMemoryStore()
    store._upsertEntry(entry({ id: 'a', project_id: 'p1', project_name: 'Alpha' }))
    store._upsertEntry(entry({ id: 'b', project_id: 'p1', project_name: 'Alpha' }))
    store._upsertEntry(entry({ id: 'c', project_id: 'p2', project_name: 'Beta' }))

    const groups = store.groupedByProjectEntries
    expect(groups).toHaveLength(2)
    const alpha = groups.find((g) => g.project_id === 'p1')
    expect(alpha.entries.map((e) => e.id).sort()).toEqual(['a', 'b'])
  })

  it('clearFilters resets search, tags, and project', () => {
    const store = useMemoryStore()
    store.searchText = 'x'
    store.selectedTags = ['security']
    store.selectedProjectId = 'p1'
    store.clearFilters()
    expect(store.searchText).toBe('')
    expect(store.selectedTags).toEqual([])
    expect(store.selectedProjectId).toBeNull()
  })

  it('searchMemoryEntries hits the server ?search= path when a term is present', async () => {
    const store = useMemoryStore()
    mockGetMemoryEntries.mockResolvedValue({
      data: { entries: [entry({ id: 's1' })], total_count: 1, filtered_count: 1 },
    })

    await store.searchMemoryEntries('prod-1', 'tenant guard')

    expect(mockGetMemoryEntries).toHaveBeenCalledWith('prod-1', { limit: 100, search: 'tenant guard' })
    expect(store.serverSearch).toBe(true)
    expect(store.entries.map((e) => e.id)).toEqual(['s1'])
    expect(store.loadedProductId).toBe('prod-1')
  })

  it('searchMemoryEntries falls back to the client-side full load when the term is blank', async () => {
    const store = useMemoryStore()
    mockGetMemoryEntries.mockResolvedValue({
      data: { entries: [entry({ id: 'a' }), entry({ id: 'b' })], total_count: 2, filtered_count: 2 },
    })

    await store.searchMemoryEntries('prod-1', '   ')

    // Blank term -> reuse the read endpoint with NO search param (client-side path).
    expect(mockGetMemoryEntries).toHaveBeenCalledWith('prod-1', { limit: 100 })
    expect(store.serverSearch).toBe(false)
    expect(store.entries).toHaveLength(2)
  })

  it('when serverSearch is active, filteredEntries trusts the server text match', async () => {
    const store = useMemoryStore()
    // Server returns a relevance/stemmed match whose summary does NOT contain the
    // raw search substring; the client must not re-filter it away.
    mockGetMemoryEntries.mockResolvedValue({
      data: { entries: [entry({ id: 'r1', summary: 'Stemmed running result' })], total_count: 1, filtered_count: 1 },
    })

    await store.searchMemoryEntries('prod-1', 'run')
    store.searchText = 'run' // raw substring not in the returned summary
    expect(store.filteredEntries.map((e) => e.id)).toEqual(['r1'])

    // After clearFilters, serverSearch resets and client-side filtering resumes.
    store.clearFilters()
    expect(store.serverSearch).toBe(false)
  })

  it('searches 1000 entries correctly and well under 200ms (client-side)', () => {
    const store = useMemoryStore()
    const seeded = new Map()
    for (let i = 0; i < 1000; i++) {
      const e = entry({
        id: `e-${i}`,
        summary: i === 742 ? 'unique-needle-xyz appears here' : `routine entry number ${i}`,
        sequence: i,
        timestamp: `2026-06-01T00:00:${String(i % 60).padStart(2, '0')}Z`,
      })
      seeded.set(e.id, e)
    }
    // Seed directly (single owner) to isolate the filter-latency measurement.
    store.byId = seeded
    expect(store.entries).toHaveLength(1000)

    const t0 = performance.now()
    store.searchText = 'unique-needle-xyz'
    const result = store.filteredEntries
    const elapsed = performance.now() - t0

    expect(result).toHaveLength(1)
    expect(result[0].id).toBe('e-742')
    expect(elapsed).toBeLessThan(200)
  })
})
