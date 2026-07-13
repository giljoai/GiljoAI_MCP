/**
 * useChainLifecycle.spec.js — FE-6165f
 * Lifecycle actions for a running chain:
 *   terminateChain, handoverConductor, releaseChain, resumeChain.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import api from '@/services/api'

const { mockShowToast, mockCopy } = vi.hoisted(() => ({
  mockShowToast: vi.fn(),
  mockCopy: vi.fn(() => Promise.resolve(true)),
}))

vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: mockShowToast }) }))
vi.mock('@/composables/useClipboard', () => ({ useClipboard: () => ({ copy: mockCopy }) }))

import { useChainLifecycle } from './useChainLifecycle'

const makeRun = (overrides = {}) => ({
  id: 'run-1',
  status: 'running',
  current_index: 2,
  project_statuses: { 'pid-a': 'completed', 'pid-b': 'running' },
  ...overrides,
})

describe('useChainLifecycle (FE-6165f)', () => {
  beforeEach(() => {
    // FE-6171b: useChainLifecycle now uses useSequenceRunStore; Pinia must be active.
    setActivePinia(createPinia())
    mockShowToast.mockClear()
    mockCopy.mockClear()
    mockCopy.mockResolvedValue(true)
  })

  // ---------------------------------------------------------------------------
  // terminateChain
  // ---------------------------------------------------------------------------
  describe('terminateChain', () => {
    it('fetches termination prompt, copies it, posts TERMINATE_CHAIN to the project bound thread, and PATCHes run', async () => {
      api.prompts.termination.mockResolvedValueOnce({ data: { prompt: 'TERMINATE NOW' } })
      api.threads.list.mockResolvedValueOnce({
        data: { threads: [{ thread_id: 'thread-pid-b', project_id: 'pid-b', subject: '(project comms)' }] },
      })
      api.threads.post.mockResolvedValueOnce({ data: { message_id: 'msg-terminate' } })
      api.sequenceRuns.update.mockResolvedValueOnce({ data: { id: 'run-1' } })

      const { terminateChain } = useChainLifecycle()
      const ok = await terminateChain(makeRun(), 'pid-b')

      expect(ok).toBe(true)
      expect(api.prompts.termination).toHaveBeenCalledWith('pid-b')
      expect(mockCopy).toHaveBeenCalledWith('TERMINATE NOW')
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'success' }),
      )
      // BE-9012d: TERMINATE_CHAIN now posts (broadcast, no to_participant) to the
      // project's bound Hub thread instead of the retired bus's sendUnified.
      expect(api.threads.post).toHaveBeenCalledWith(
        'thread-pid-b',
        expect.objectContaining({ content: 'TERMINATE_CHAIN', requires_action: false }),
      )
      // update: mark project + run as terminated; current_index must NOT change
      expect(api.sequenceRuns.update).toHaveBeenCalledWith(
        'run-1',
        expect.objectContaining({
          project_statuses: expect.objectContaining({ 'pid-b': 'terminated' }),
          status: 'terminated',
        }),
      )
    })

    it('returns false and toasts on error', async () => {
      api.prompts.termination.mockRejectedValueOnce({ response: { data: { detail: 'bad pid' } } })

      const { terminateChain } = useChainLifecycle()
      const ok = await terminateChain(makeRun(), 'pid-b')

      expect(ok).toBe(false)
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'error', message: 'bad pid' }),
      )
    })
  })

  // ---------------------------------------------------------------------------
  // handoverConductor
  // ---------------------------------------------------------------------------
  describe('handoverConductor', () => {
    it('calls simpleHandover and returns its data', async () => {
      const handoverData = {
        retirement_prompt: 'You are retiring…',
        continuation_prompt: 'You are continuing…',
      }
      api.agentJobs.simpleHandover.mockResolvedValueOnce({ data: handoverData })

      const { handoverConductor } = useChainLifecycle()
      const result = await handoverConductor('job-42')

      expect(api.agentJobs.simpleHandover).toHaveBeenCalledWith('job-42')
      expect(result).toEqual(handoverData)
    })

    it('toasts on error and returns undefined', async () => {
      api.agentJobs.simpleHandover.mockRejectedValueOnce(new Error('network fail'))

      const { handoverConductor } = useChainLifecycle()
      const result = await handoverConductor('job-42')

      expect(result).toBeUndefined()
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'error' }),
      )
    })
  })

  // ---------------------------------------------------------------------------
  // releaseChain
  // ---------------------------------------------------------------------------
  describe('releaseChain', () => {
    it('calls sequenceRuns.release with mode=cancel and toasts success', async () => {
      api.sequenceRuns.release.mockResolvedValueOnce({ data: { id: 'run-1', status: 'cancelled' } })

      const { releaseChain } = useChainLifecycle()
      const ok = await releaseChain(makeRun())

      expect(ok).toBe(true)
      expect(api.sequenceRuns.release).toHaveBeenCalledWith('run-1', 'cancel')
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'success' }),
      )
    })

    it('returns false and toasts on error', async () => {
      api.sequenceRuns.release.mockRejectedValueOnce(new Error('server down'))

      const { releaseChain } = useChainLifecycle()
      const ok = await releaseChain(makeRun())

      expect(ok).toBe(false)
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'error' }),
      )
    })
  })

  // ---------------------------------------------------------------------------
  // resumeChain
  // ---------------------------------------------------------------------------
  describe('resumeChain', () => {
    it('PATCHes run status + project_statuses, then restages and launches the failed project', async () => {
      const run = makeRun({ current_index: 1 })
      api.sequenceRuns.update.mockResolvedValueOnce({ data: { id: 'run-1' } })
      api.projects.restage.mockResolvedValueOnce({ data: { success: true } })
      api.projects.launchImplementation.mockResolvedValueOnce({ data: { success: true } })

      const { resumeChain } = useChainLifecycle()
      const ok = await resumeChain(run, 'pid-b')

      expect(ok).toBe(true)

      // PATCH must set status + reset failed project status — must NOT change current_index
      expect(api.sequenceRuns.update).toHaveBeenCalledWith(
        'run-1',
        expect.objectContaining({
          status: 'running',
          project_statuses: expect.objectContaining({ 'pid-b': 'pending' }),
        }),
      )
      // Verify current_index is absent from the patch (off-by-one guard)
      const patchArg = api.sequenceRuns.update.mock.calls[0][1]
      expect(patchArg).not.toHaveProperty('current_index')

      // Sacred per-call gate: restage then launchImplementation (NOT reactivate_job)
      expect(api.projects.restage).toHaveBeenCalledWith('pid-b')
      expect(api.projects.launchImplementation).toHaveBeenCalledWith('pid-b')

      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'success' }),
      )
    })

    it('does NOT call reactivate_job-style API (api.agentJobs.* reactivation) on resume', async () => {
      api.sequenceRuns.update.mockResolvedValueOnce({ data: { id: 'run-1' } })
      api.projects.restage.mockResolvedValueOnce({ data: { success: true } })
      api.projects.launchImplementation.mockResolvedValueOnce({ data: { success: true } })

      const { resumeChain } = useChainLifecycle()
      await resumeChain(makeRun(), 'pid-b')

      // agentJobs.spawn / status / updateMission must NOT be called — those are
      // the reactivate_job patterns that refuse closed-out or failed projects.
      expect(api.agentJobs.spawn).not.toHaveBeenCalled()
      expect(api.agentJobs.status).not.toHaveBeenCalled()
    })

    it('returns false and toasts on update error', async () => {
      api.sequenceRuns.update.mockRejectedValueOnce({ response: { data: { detail: 'update failed' } } })

      const { resumeChain } = useChainLifecycle()
      const ok = await resumeChain(makeRun(), 'pid-b')

      expect(ok).toBe(false)
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'error', message: 'update failed' }),
      )
    })
  })
})
