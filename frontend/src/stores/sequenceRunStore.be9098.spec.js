/**
 * sequenceRunStore.be9098.spec.js
 *
 * BE-9098: chain review-badge persistence. Before the fix, per-member review
 * acknowledgment lived ONLY in the ephemeral `reviewedProjects` Map, so it reset
 * on every page refresh and the Review badge returned. The fix persists it to
 * `sequence_runs.reviewed_project_ids` and hydrates the Map from the server on
 * fetch/hydrate.
 *
 * The load-bearing test here is the "refresh simulation": a FRESH store, given a
 * run whose server payload carries reviewed_project_ids, reports isReviewed=true
 * WITHOUT any prior local markReviewed() — the exact user-visible regression.
 *
 * `@/services/api` is globally mocked in tests/setup.js.
 *
 * Edition scope: CE.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSequenceRunStore } from './sequenceRunStore'
import api from '@/services/api'

describe('sequenceRunStore — BE-9098 durable review persistence', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useSequenceRunStore()
  })

  it('REFRESH SIMULATION: a fresh store hydrates isReviewed from reviewed_project_ids with NO local mark', () => {
    // Fresh store: the ephemeral Map is empty (as after a page refresh).
    expect(store.isReviewed('run-1', 'p1')).toBe(false)

    // The cockpit fetches the run; the server payload carries the durable ack.
    store.setActiveRun({
      id: 'run-1',
      project_ids: ['p1', 'p2'],
      resolved_order: ['p1', 'p2'],
      project_statuses: { p1: 'completed', p2: 'completed' },
      reviewed_project_ids: ['p1'],
    })

    // The badge is correct immediately — WITHOUT anyone calling markReviewed().
    expect(store.isReviewed('run-1', 'p1')).toBe(true)
    expect(store.isReviewed('run-1', 'p2')).toBe(false)
  })

  it('fetchRun hydrates the review Map from the server payload (end-to-end path)', async () => {
    api.sequenceRuns.get.mockResolvedValueOnce({
      data: {
        id: 'run-9',
        project_ids: ['pA', 'pB'],
        resolved_order: ['pA', 'pB'],
        project_statuses: { pA: 'completed', pB: 'completed' },
        reviewed_project_ids: ['pB'],
      },
    })

    await store.fetchRun('run-9')

    expect(store.isReviewed('run-9', 'pB')).toBe(true)
    expect(store.isReviewed('run-9', 'pA')).toBe(false)
  })

  it('hydrate() seeds review acks for every run in the active list', async () => {
    api.sequenceRuns.list.mockResolvedValueOnce({
      data: [
        {
          id: 'run-1',
          project_ids: ['p1'],
          resolved_order: ['p1'],
          status: 'running',
          project_statuses: { p1: 'completed' },
          reviewed_project_ids: ['p1'],
        },
      ],
    })

    await store.hydrate()

    expect(store.isReviewed('run-1', 'p1')).toBe(true)
  })

  it('server hydrate UNIONS with an optimistic local mark (never clobbers in-flight state)', () => {
    // User just reviewed p2 optimistically (local mark, POST not yet echoed).
    store.markReviewed('run-1', 'p2')
    expect(store.isReviewed('run-1', 'p2')).toBe(true)

    // A hydrate arrives carrying only the already-persisted p1.
    store.setActiveRun({
      id: 'run-1',
      project_ids: ['p1', 'p2'],
      resolved_order: ['p1', 'p2'],
      reviewed_project_ids: ['p1'],
    })

    // Both survive — the union keeps the optimistic p2 AND adds the server p1.
    expect(store.isReviewed('run-1', 'p1')).toBe(true)
    expect(store.isReviewed('run-1', 'p2')).toBe(true)
  })

  it('markReviewedRemote POSTs and merges the authoritative server array', async () => {
    api.sequenceRuns.markReviewed.mockResolvedValueOnce({
      data: { id: 'run-1', project_ids: ['p1'], resolved_order: ['p1'], reviewed_project_ids: ['p1'] },
    })

    await store.markReviewedRemote('run-1', 'p1')

    expect(api.sequenceRuns.markReviewed).toHaveBeenCalledWith('run-1', 'p1')
    expect(store.isReviewed('run-1', 'p1')).toBe(true)
  })

  it('markReviewedRemote rejects on API failure so the caller can toast', async () => {
    api.sequenceRuns.markReviewed.mockRejectedValueOnce(new Error('network down'))

    await expect(store.markReviewedRemote('run-1', 'p1')).rejects.toThrow('network down')
  })

  it('$reset clears server-hydrated acks too', () => {
    store.setActiveRun({ id: 'run-1', project_ids: ['p1'], reviewed_project_ids: ['p1'] })
    expect(store.isReviewed('run-1', 'p1')).toBe(true)

    store.$reset()

    expect(store.isReviewed('run-1', 'p1')).toBe(false)
  })
})
