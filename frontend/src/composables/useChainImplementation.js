/**
 * useChainImplementation — FE-6165f
 *
 * The Implement Chain button's copy action. Fetches the chain IMPLEMENTATION
 * kickoff prompt (BE-6165d: GET /api/v1/prompts/chain-implementation/{run_id}) —
 * the ONE master prompt that, pasted into the head project's orchestrator
 * session, makes that session the conductor and drives the whole chain.
 *
 * Like useChainStaging, this is a thin fetch + clipboard: the CH_CONDUCTOR /
 * CH_CHAIN_DRIVE chapters arrive at RUNTIME via the conductor's get_job_mission
 * call (BE-6165c/d), not embedded in this response.
 *
 * Edition scope: CE.
 */
import { api } from '@/services/api'
import { useToast } from '@/composables/useToast'
import { useClipboard } from '@/composables/useClipboard'

export function useChainImplementation() {
  const { showToast } = useToast()
  const { copy } = useClipboard()

  async function copyImplPrompt(runId, headProjectId) {
    if (!runId) return false
    // Mirror the solo play button (usePlayButton.handlePlay): the human pressing
    // Implement Chain authorizes project 1 by crossing its launch gate, exactly as
    // solo authorizes its one project. Without this the chain-implementation
    // endpoint raises ImplementationNotReadyError (404) because the head's
    // implementation_launched_at is still null. Non-blocking + caught (solo
    // convention): the conductor auto-launches projects 2..N itself via
    // CH_CHAIN_DRIVE, so only the head needs the dashboard-driven launch.
    if (headProjectId) {
      try {
        await api.projects.launchImplementation(headProjectId)
      } catch (gateError) {
        console.warn('[useChainImplementation] head launch-implementation failed (non-blocking):', gateError)
      }
    }
    try {
      const { data } = await api.prompts.chainImplementation(runId)
      const prompt = data?.prompt
      if (!prompt) throw new Error('No implementation prompt returned')
      const ok = await copy(prompt)
      if (!ok) {
        showToast({
          message: 'Browser blocked clipboard access. Copy the implementation prompt manually.',
          type: 'error',
          timeout: 6000,
        })
        return false
      }
      showToast({
        message: 'Chain implementation prompt copied. Paste it into the head project orchestrator terminal to drive the whole chain.',
        type: 'success',
        timeout: 5000,
      })
      return true
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Could not copy the chain implementation prompt.'
      showToast({ message: msg, type: 'error', timeout: 5000 })
      return false
    }
  }

  return { copyImplPrompt }
}
