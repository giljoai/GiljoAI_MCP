/**
 * ProjectTabs.reviewDispatch.spec.js — FE-6174c
 *
 * Tests the extracted pure helpers. Imports the SAME code the component uses
 * (zero drift). Covers the eject guard: chain branch NEVER calls openCloseoutModal.
 *
 * Edition scope: CE.
 */
import { describe, it, expect, vi } from 'vitest'
import { buildChainAwareShowCloseout, buildReviewDispatcher } from '@/components/projects/reviewDispatch.js'

const makeChainCtx = () => ({
  run: { id: 'run-1' },
  runId: 'run-1',
  tabs: [],
})

describe('buildChainAwareShowCloseout', () => {
  it('chain + needsReview=true → true', () => {
    expect(buildChainAwareShowCloseout(makeChainCtx(), { needsReview: true }, false)).toBe(true)
  })

  it('chain + needsReview=false → false', () => {
    expect(buildChainAwareShowCloseout(makeChainCtx(), { needsReview: false }, true)).toBe(false)
  })

  it('chain + null currentChainTab → false', () => {
    expect(buildChainAwareShowCloseout(makeChainCtx(), null, true)).toBe(false)
  })

  it('solo (chainCtx=null) → passes showCloseoutButton through', () => {
    expect(buildChainAwareShowCloseout(null, null, true)).toBe(true)
    expect(buildChainAwareShowCloseout(null, null, false)).toBe(false)
  })
})

describe('buildReviewDispatcher', () => {
  it('chain branch → calls handleTabReview with currentChainTab, NOT openCloseoutModal', () => {
    const handleTabReview = vi.fn()
    const openCloseoutModal = vi.fn()
    const tab = { projectId: 'p1', needsReview: true }

    const dispatch = buildReviewDispatcher(makeChainCtx(), tab, handleTabReview, openCloseoutModal)
    dispatch()

    expect(handleTabReview).toHaveBeenCalledOnce()
    expect(handleTabReview).toHaveBeenCalledWith(tab)
    expect(openCloseoutModal).not.toHaveBeenCalled()
  })

  it('solo branch → calls openCloseoutModal, NOT handleTabReview', () => {
    const handleTabReview = vi.fn()
    const openCloseoutModal = vi.fn()

    const dispatch = buildReviewDispatcher(null, null, handleTabReview, openCloseoutModal)
    dispatch()

    expect(openCloseoutModal).toHaveBeenCalledOnce()
    expect(handleTabReview).not.toHaveBeenCalled()
  })
})
