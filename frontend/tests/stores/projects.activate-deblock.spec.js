/**
 * Regression tests for IMP-1002 frontend fixes:
 *
 * 1. activateProject / deactivateProject: Launch navigation must NOT be gated
 *    on fetchProjects completing. The store action must resolve immediately after
 *    the activate/deactivate API call, letting router.push fire while the list
 *    reconcile runs detached.
 *
 * 2. fetchProject: must return the fetched data so callers can guard against a
 *    failed GET before opening the edit dialog (prevents mission data-loss when
 *    the list row carries trimmed ProjectListResponse without mission/description).
 *
 * Edition Scope: CE
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectStore } from '@/stores/projects'

// ── helpers ────────────────────────────────────────────────────────────────────

/** Create a deferred promise — lets tests control when a mock resolves. */
function deferred() {
  let resolve, reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

// ── mocks ──────────────────────────────────────────────────────────────────────
// vi.mock is hoisted — factory MUST NOT reference variables defined below it.
// Use vi.hoisted() for shared mock refs across the factory boundary.

const { mockActivate, mockDeactivate, mockList, mockGet } = vi.hoisted(() => ({
  mockActivate: vi.fn(),
  mockDeactivate: vi.fn(),
  mockList: vi.fn(),
  mockGet: vi.fn(),
}))

vi.mock('@/services/api', () => ({
  api: {
    projects: {
      activate: mockActivate,
      deactivate: mockDeactivate,
      list: mockList,
      get: mockGet,
      // BE-6076: activate/deactivate now refresh the off-page active flag.
      getActive: vi.fn().mockResolvedValue({ data: null }),
    },
  },
  // ProjectsView imports via `import api from '@/services/api'` (default export);
  // store imports via `import { api }` (named export). Provide both.
  default: {
    projects: {
      activate: mockActivate,
      deactivate: mockDeactivate,
      list: mockList,
      get: mockGet,
      getActive: vi.fn().mockResolvedValue({ data: null }),
    },
  },
}))

// products store used by fetchProjects
vi.mock('@/stores/products', () => ({
  useProductStore: () => ({ currentProductId: 'prod-1' }),
}))

// ── fixtures ───────────────────────────────────────────────────────────────────

const PROJ = {
  id: 'proj-1',
  name: 'Alpha',
  status: 'inactive',
  staging_status: null,
  mission: 'Do great things',
  description: 'Full description text',
  updated_at: '2026-01-01T00:00:00Z',
}

// ── suite ──────────────────────────────────────────────────────────────────────

describe('projects store — IMP-1002 activate deblock + fetchProject return', () => {
  let store

  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    store = useProjectStore()
    store.projects = [{ ...PROJ }]
  })

  // ────────────────────────────────────────────────────────────────────────────
  // 1a. activateProject resolves BEFORE fetchProjects completes
  // ────────────────────────────────────────────────────────────────────────────
  it('activateProject resolves without waiting for fetchProjects to complete', async () => {
    // Arrange: activate resolves immediately; list is deliberately deferred
    mockActivate.mockResolvedValueOnce({ data: { ...PROJ, status: 'active' } })
    const listDefer = deferred()
    mockList.mockReturnValueOnce(listDefer.promise)

    // Act: activateProject must settle while list is still pending
    const activatePromise = store.activateProject('proj-1')

    // Assert: activateProject has already resolved (would hang here if it still
    // awaited the list reload)
    await expect(activatePromise).resolves.toBeDefined()

    // list is still in-flight — confirm it was called (reconcile preserved)
    expect(mockList).toHaveBeenCalledTimes(1)

    // Clean up: resolve the deferred so no leaked promise
    listDefer.resolve({ data: [{ ...PROJ, status: 'active' }] })
  })

  // ────────────────────────────────────────────────────────────────────────────
  // 1b. fetchProjects fires even though we don't await it (sibling reconcile)
  // ────────────────────────────────────────────────────────────────────────────
  it('activateProject fires fetchProjects for sibling-deactivation reconcile', async () => {
    mockActivate.mockResolvedValueOnce({ data: { ...PROJ, status: 'active' } })
    const listDefer = deferred()
    mockList.mockReturnValueOnce(listDefer.promise)

    await store.activateProject('proj-1')

    // fetchProjects (list) must have been called even though we didn't await it
    expect(mockList).toHaveBeenCalledTimes(1)

    listDefer.resolve({ data: [] })
  })

  // ────────────────────────────────────────────────────────────────────────────
  // 1c. deactivateProject resolves BEFORE fetchProjects completes
  // ────────────────────────────────────────────────────────────────────────────
  it('deactivateProject resolves without waiting for fetchProjects to complete', async () => {
    store.projects[0].status = 'active'
    mockDeactivate.mockResolvedValueOnce(undefined)
    const listDefer = deferred()
    mockList.mockReturnValueOnce(listDefer.promise)

    const deactivatePromise = store.deactivateProject('proj-1')

    await expect(deactivatePromise).resolves.toBeUndefined()
    expect(mockList).toHaveBeenCalledTimes(1)

    listDefer.resolve({ data: [] })
  })

  // ────────────────────────────────────────────────────────────────────────────
  // 1d. detached fetchProjects failure does NOT throw (unhandled rejection guard)
  // ────────────────────────────────────────────────────────────────────────────
  it('activateProject does not surface an unhandled rejection when fetchProjects fails', async () => {
    mockActivate.mockResolvedValueOnce({ data: { ...PROJ, status: 'active' } })
    // list rejects — must be caught internally by the detached .catch()
    mockList.mockRejectedValueOnce(new Error('network timeout'))

    // Should not throw
    await expect(store.activateProject('proj-1')).resolves.toBeDefined()

    // Give the detached fetch a tick to run its .catch
    await new Promise((r) => setTimeout(r, 0))
    // No unhandled rejection here → test passes cleanly
  })

  // ────────────────────────────────────────────────────────────────────────────
  // 2. fetchProject returns the fetched data (guards the edit-dialog data-loss fix)
  // ────────────────────────────────────────────────────────────────────────────
  it('fetchProject returns the fetched project data', async () => {
    const fullProject = { ...PROJ, mission: 'Do great things', description: 'Full description text' }
    mockGet.mockResolvedValueOnce({ data: fullProject })

    const result = await store.fetchProject('proj-1')

    expect(result).toEqual(fullProject)
    expect(mockGet).toHaveBeenCalledWith('proj-1')
  })

  it('fetchProject returns undefined when the API call fails', async () => {
    mockGet.mockRejectedValueOnce(new Error('404 not found'))

    const result = await store.fetchProject('proj-1')

    // Should return undefined (not throw), so callers can guard
    expect(result).toBeUndefined()
  })
})
