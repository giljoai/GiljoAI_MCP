/**
 * useProjectBoundThread.spec.js — BE-9012d Phase 5 / D1(a)
 *
 * The bound-thread resolution must be DETERMINISTIC (step (d) canonicalizes one
 * bound thread per project via the ce_0072 fold; the FE mirrors that precedence).
 * These tests pin the read-only, no-create resolver `resolveExistingProjectThread`:
 *   0 candidates -> null (and NEVER creates a thread as a side effect)
 *   1 candidate  -> that one
 *   several      -> the `(project comms)`-marker thread, else the OLDEST by created_at
 *
 * Edition scope: CE
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useProjectBoundThread } from '@/composables/useProjectBoundThread'
import { useCommHubStore } from '@/stores/commHubStore'

const P = 'proj-bound'

describe('useProjectBoundThread.resolveExistingProjectThread (deterministic, no-create)', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useCommHubStore()
    // loadThreads() is a network fetch; stub it to a no-op so the threads we seed
    // directly via _testSeedThread are what the resolver reads.
    vi.spyOn(store, 'loadThreads').mockResolvedValue(undefined)
    vi.spyOn(store, 'createThread').mockResolvedValue(undefined)
  })

  it('returns null and NEVER creates when the project has no bound thread', async () => {
    const { resolveExistingProjectThread } = useProjectBoundThread()
    const t = await resolveExistingProjectThread(P)
    expect(t).toBeNull()
    expect(store.createThread).not.toHaveBeenCalled()
  })

  it('returns the sole candidate', async () => {
    store._testSeedThread({ thread_id: 'only', project_id: P, subject: 'whatever', created_at: '2026-06-01T00:00:00Z' })
    const { resolveExistingProjectThread } = useProjectBoundThread()
    const t = await resolveExistingProjectThread(P)
    expect(t.thread_id).toBe('only')
    expect(store.createThread).not.toHaveBeenCalled()
  })

  it('prefers the (project comms)-marker thread when several exist', async () => {
    store._testSeedThread({ thread_id: 'plain', project_id: P, subject: 'chatter', created_at: '2026-06-01T00:00:00Z' })
    store._testSeedThread({ thread_id: 'marked', project_id: P, subject: '(project comms)', created_at: '2026-06-05T00:00:00Z' })
    const { resolveExistingProjectThread } = useProjectBoundThread()
    const t = await resolveExistingProjectThread(P)
    expect(t.thread_id).toBe('marked')
  })

  it('falls back to the OLDEST by created_at when several exist without the marker', async () => {
    store._testSeedThread({ thread_id: 'newer', project_id: P, subject: 'a', created_at: '2026-06-10T00:00:00Z' })
    store._testSeedThread({ thread_id: 'older', project_id: P, subject: 'b', created_at: '2026-06-01T00:00:00Z' })
    const { resolveExistingProjectThread } = useProjectBoundThread()
    const t = await resolveExistingProjectThread(P)
    expect(t.thread_id).toBe('older')
  })

  it('ignores threads belonging to other projects', async () => {
    store._testSeedThread({ thread_id: 'mine', project_id: P, subject: 'x', created_at: '2026-06-01T00:00:00Z' })
    store._testSeedThread({ thread_id: 'other', project_id: 'proj-other', subject: 'y', created_at: '2026-05-01T00:00:00Z' })
    const { resolveExistingProjectThread } = useProjectBoundThread()
    const t = await resolveExistingProjectThread(P)
    expect(t.thread_id).toBe('mine')
  })
})
