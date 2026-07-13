/**
 * sequenceRunStore.chainReview.spec.js
 *
 * Tests for the client-side chain review tracking added in the chain closeout
 * review fix: reviewedProjects, isReviewed, markReviewed.
 *
 * Key invariant: markReviewed MUST use immutable Map replacement so Vue ref-
 * tracking re-evaluates any computed that reads isReviewed(). A plain Set.add()
 * inside an existing Map entry would be untracked and leave computeds stale.
 *
 * Edition scope: CE.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { computed } from 'vue'
import { useSequenceRunStore } from './sequenceRunStore'
import { resolveJobsNavPath } from '@/utils/jobsNavTarget'
import api from '@/services/api'

describe('sequenceRunStore — chain review (isReviewed / markReviewed)', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useSequenceRunStore()
  })

  it('isReviewed returns false when the project has not been reviewed', () => {
    expect(store.isReviewed('run-1', 'p1')).toBe(false)
  })

  it('isReviewed returns false for null/empty inputs (defensive guard)', () => {
    expect(store.isReviewed(null, 'p1')).toBe(false)
    expect(store.isReviewed('run-1', null)).toBe(false)
    expect(store.isReviewed('', 'p1')).toBe(false)
  })

  it('markReviewed marks a project as reviewed', () => {
    store.markReviewed('run-1', 'p1')
    expect(store.isReviewed('run-1', 'p1')).toBe(true)
  })

  it('markReviewed is idempotent — calling twice does not throw or corrupt state', () => {
    store.markReviewed('run-1', 'p1')
    store.markReviewed('run-1', 'p1') // no-op
    expect(store.isReviewed('run-1', 'p1')).toBe(true)
  })

  it('markReviewed tracks pids per run independently (cross-run isolation)', () => {
    store.markReviewed('run-1', 'p1')
    store.markReviewed('run-2', 'p2')
    expect(store.isReviewed('run-1', 'p1')).toBe(true)
    expect(store.isReviewed('run-2', 'p2')).toBe(true)
    // cross-run lookups return false
    expect(store.isReviewed('run-1', 'p2')).toBe(false)
    expect(store.isReviewed('run-2', 'p1')).toBe(false)
  })

  it('a Vue computed that reads isReviewed re-evaluates after markReviewed (immutable Map trigger)', () => {
    // The load-bearing reactivity test: immutable Map replacement (new Map(...))
    // changes the ref.value reference so Vue tracks the dependency and re-evaluates
    // the computed. A plain Set.add() inside an existing Map entry would not change
    // the ref reference — Vue would cache the old false and never re-evaluate.
    const result = computed(() => store.isReviewed('run-1', 'p1'))
    expect(result.value).toBe(false) // establish dependency

    store.markReviewed('run-1', 'p1')

    // Vue lazy-evaluates: .value triggers re-evaluation now that the dep changed.
    expect(result.value).toBe(true)
  })

  it('$reset clears the reviewedProjects map', () => {
    store.markReviewed('run-1', 'p1')
    expect(store.isReviewed('run-1', 'p1')).toBe(true)

    store.$reset()

    expect(store.isReviewed('run-1', 'p1')).toBe(false)
  })
})

// ── reviewPendingRun getter (FE-6199 nav fix) ────────────────────────────────

describe('sequenceRunStore — reviewPendingRun getter', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useSequenceRunStore()
  })

  it('returns the run when finished (not in activeRuns) but has unreviewed completed members (RED→GREEN)', () => {
    // runsById is empty → activeRuns[0] is undefined
    store._testSetActiveRun({
      id: 'run-1',
      resolved_order: ['p1', 'p2'],
      project_statuses: { p1: 'completed', p2: 'completed' },
    })
    expect(store.activeRuns).toHaveLength(0)
    expect(store.reviewPendingRun).not.toBeNull()
    expect(store.reviewPendingRun.id).toBe('run-1')
  })

  it('returns null after all completed members are reviewed — release-on-all-reviewed, no bounce', () => {
    store._testSetActiveRun({
      id: 'run-1',
      resolved_order: ['p1', 'p2'],
      project_statuses: { p1: 'completed', p2: 'completed' },
    })
    expect(store.reviewPendingRun).not.toBeNull()

    store.markReviewed('run-1', 'p1')
    store.markReviewed('run-1', 'p2')

    expect(store.reviewPendingRun).toBeNull()
  })

  it('resolver integration — finished+unreviewed run resolves to chain review path, not /launch dead end', () => {
    store._testSetActiveRun({
      id: 'run-1',
      resolved_order: ['p1', 'p2'],
      project_statuses: { p1: 'completed', p2: 'completed' },
    })

    // BEFORE fix equivalent: activeRuns[0] is undefined, reviewPendingRun supplies the run
    const target = resolveJobsNavPath({
      activeProject: null,
      activeRun: store.activeRuns[0] ?? store.reviewPendingRun ?? null,
    })
    expect(target).toBe('/projects/p1?run=run-1') // branch C — chain review view

    // After all reviewed: releases to branch B
    store.markReviewed('run-1', 'p1')
    store.markReviewed('run-1', 'p2')
    const released = resolveJobsNavPath({
      activeProject: null,
      activeRun: store.activeRuns[0] ?? store.reviewPendingRun ?? null,
    })
    expect(released).toBe('/launch?via=jobs')
  })

  it('ordering: in-flight run in activeRuns[0] takes precedence; reviewPendingRun is not consulted (?? short-circuits)', () => {
    // Seed an in-flight run into runsById so activeRuns[0] is non-null
    store._testSeedRuns([
      {
        id: 'run-active',
        resolved_order: ['pX'],
        project_ids: ['pX'],
        project_statuses: { pX: 'running' },
        status: 'running',
      },
    ])
    // Also set a finished+unreviewed run as activeRun (reviewPendingRun would return it)
    store._testSetActiveRun({
      id: 'run-finished',
      resolved_order: ['p1', 'p2'],
      project_statuses: { p1: 'completed', p2: 'completed' },
    })

    expect(store.activeRuns[0]).toBeDefined()
    expect(store.activeRuns[0].id).toBe('run-active')

    const target = resolveJobsNavPath({
      activeProject: null,
      activeRun: store.activeRuns[0] ?? store.reviewPendingRun ?? null,
    })
    // activeRuns[0] is non-null → ?? short-circuits → in-flight run wins
    expect(target).toBe('/projects/pX?run=run-active')
  })

  it('returns null when activeRun is null (no solo or chain run open)', () => {
    // Fresh store: activeRun is null
    expect(store.reviewPendingRun).toBeNull()
  })
})

// ── FE-9104: cold-refresh review reachability via reviewPendingById ───────────
//
// The gap FE-6199 left: reviewPendingRun read ONLY activeRun, which is null after
// a full page reload with no ?run= in the URL (nothing populates it). The chain
// review surface was then unreachable. FE-9104 seeds a SEPARATE reviewPendingById
// map from the server's include_review_pending listing on hydrate, and
// reviewPendingRun falls back to it — keeping the Jobs link alive across a cold
// refresh, releasing exactly as before once every completed member is reviewed.

describe('sequenceRunStore — FE-9104 cold-refresh review reachability', () => {
  let store

  const termRun = (extra = {}) => ({
    id: 'run-term',
    resolved_order: ['p1', 'p2'],
    project_ids: ['p1', 'p2'],
    project_statuses: { p1: 'completed', p2: 'completed' },
    status: 'completed',
    ...extra,
  })

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useSequenceRunStore()
  })

  it('cold refresh: terminal run in reviewPendingById (activeRun null) → reviewPendingRun resolves + nav → ?run (RED→GREEN)', () => {
    // Post-hydrate state after a reload with NO ?run: activeRun null, but the
    // server surfaced the finished-but-unreviewed run into reviewPendingById.
    store._testSeedReviewPending([termRun()])
    expect(store.activeRun).toBeNull()
    expect(store.activeRuns).toHaveLength(0)
    expect(store.reviewPendingRun).not.toBeNull()
    expect(store.reviewPendingRun.id).toBe('run-term')

    const target = resolveJobsNavPath({
      activeProject: null,
      activeRun: store.activeRuns[0] ?? store.reviewPendingRun ?? null,
    })
    expect(target).toBe('/projects/p1?run=run-term') // branch C — chain review view
  })

  it('release: after every completed member reviewed → reviewPendingRun releases + nav → /launch (no bounce)', () => {
    store._testSeedReviewPending([termRun()])
    expect(store.reviewPendingRun).not.toBeNull()

    store.markReviewed('run-term', 'p1')
    store.markReviewed('run-term', 'p2')

    expect(store.reviewPendingRun).toBeNull()
    const released = resolveJobsNavPath({
      activeProject: null,
      activeRun: store.activeRuns[0] ?? store.reviewPendingRun ?? null,
    })
    expect(released).toBe('/launch?via=jobs')
  })

  it('hydrate splits runs: active → runsById (locks checkbox), terminal review-pending → reviewPendingById (does NOT re-lock)', async () => {
    api.sequenceRuns.list.mockResolvedValueOnce({
      data: [
        {
          id: 'run-active',
          resolved_order: ['pA'],
          project_ids: ['pA'],
          project_statuses: { pA: 'running' },
          status: 'running',
        },
        termRun(),
      ],
    })
    await store.hydrate()

    // Active run drives the election set + the "In chain" checkbox lock.
    expect(store.activeRuns.map((r) => r.id)).toEqual(['run-active'])
    expect(store.isProjectInActiveChain('pA')).toBe(true)
    // The terminal review-pending run must NOT re-lock its members' checkboxes.
    expect(store.isProjectInActiveChain('p1')).toBe(false)
    expect(store.reviewPendingById.has('run-term')).toBe(true)
    // …but it IS reachable for review.
    expect(store.reviewPendingRun.id).toBe('run-term')
    expect(api.sequenceRuns.list).toHaveBeenCalledWith({
      status: 'pending,running,stalled',
      include_review_pending: true,
    })
  })

  it('solo deletion test: empty hydrate → reviewPendingRun null, nav byte-identical', async () => {
    api.sequenceRuns.list.mockResolvedValueOnce({ data: [] })
    await store.hydrate()

    expect(store.reviewPendingRun).toBeNull()
    // No project, no run → launch page (unchanged).
    expect(
      resolveJobsNavPath({
        activeProject: null,
        activeRun: store.activeRuns[0] ?? store.reviewPendingRun ?? null,
      }),
    ).toBe('/launch?via=jobs')
    // Solo project, no run → solo project page (unchanged).
    expect(
      resolveJobsNavPath({
        activeProject: { id: 'solo' },
        activeRun: store.activeRuns[0] ?? store.reviewPendingRun ?? null,
      }),
    ).toBe('/projects/solo?via=jobs')
  })

  it('$reset clears reviewPendingById', () => {
    store._testSeedReviewPending([termRun()])
    expect(store.reviewPendingRun).not.toBeNull()

    store.$reset()

    expect(store.reviewPendingRun).toBeNull()
    expect(store.reviewPendingById.size).toBe(0)
  })
})
