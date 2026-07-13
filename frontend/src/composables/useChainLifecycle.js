/**
 * useChainLifecycle — FE-6165f / FE-6170 / FE-6171b
 *
 * Lifecycle control actions for a running sequential chain:
 *   - stageChain        lock the run (PATCH locked=true) + copy staging prompt
 *   - unstageChain      unlock the run (PATCH locked=false) — KEEP chain intact (FE-6171b redef)
 *   - terminateChain    graceful drain of the in-flight project
 *   - handoverConductor session-rotation for the conductor job
 *   - releaseChain      hard reset / "I killed my terminals" (dissolves run)
 *   - dissolveChain     internal dissolve primitive used by release/terminate
 *   - resumeChain       resume-from-failure via restage + sacred gate
 *
 * FE-6170 → FE-6171b REDEFINITION:
 *   unstageChain was "cancel+dissolve" in FE-6170. In FE-6171b it is UNLOCK ONLY —
 *   the chain stays intact. Full dissolve now lives ONLY in releaseChain (hard exit)
 *   and the terminate flow. This preserves the FE-6170 fix for release/terminate while
 *   giving the Stage⇄Unstage button the correct semantics.
 *
 * FE-6170: releaseChain accepts an optional `onDissolved` callback so MissionControlView
 * can clear the transient selection + re-hydrate the store after dissolving.
 *
 * All flows operate over existing API endpoints — NO new writers.
 * Edition scope: CE.
 */
import { api } from '@/services/api'
import { useToast } from '@/composables/useToast'
import { useClipboard } from '@/composables/useClipboard'
import { useSequenceRunStore } from '@/stores/sequenceRunStore'
import { useCommHubStore } from '@/stores/commHubStore'
import { useProjectBoundThread } from '@/composables/useProjectBoundThread'

export function useChainLifecycle() {
  const { showToast } = useToast()
  const { copy } = useClipboard()
  const sequenceRunStore = useSequenceRunStore()
  const commHub = useCommHubStore()
  const { resolveProjectThread } = useProjectBoundThread()

  /**
   * stageChain — FE-6171b Stage action (Editing → Staged tier).
   *
   * 1. PATCH run locked=true via the store (single write seam).
   * 2. Fetch the chain staging prompt and copy it to the clipboard.
   *
   * Replicates the solo Stage button in ProjectTabs.vue / useProjectStaging.
   * The dynamic Stage⇄Unstage button in ChainCockpitControls calls this.
   *
   * @param {Object} run - the sequence run object
   * @returns {Promise<Object|null>} updated run on success, null on error
   */
  async function stageChain(run) {
    try {
      const updated = await sequenceRunStore.lockRun(run.id)
      // Fetch and copy the chain staging prompt (mirrors useChainStaging.copyStagingPrompt).
      const { data } = await api.prompts.chainStaging(run.id)
      const prompt = data?.prompt
      if (prompt) {
        const copied = await copy(prompt)
        if (copied) {
          showToast({
            message: 'Chain staged. Staging prompt copied — paste it into your orchestrator terminal.',
            type: 'success',
            timeout: 6000,
          })
        } else {
          showToast({
            message: 'Chain staged. Browser blocked clipboard — copy the staging prompt manually.',
            type: 'warning',
            timeout: 6000,
          })
        }
      } else {
        showToast({
          message: 'Chain staged (no staging prompt available yet).',
          type: 'success',
          timeout: 4000,
        })
      }
      return updated
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Could not stage the chain.'
      showToast({ message: msg, type: 'error', timeout: 5000 })
      return null
    }
  }

  /**
   * unstageChain — FE-6171b Unstage action (Staged → Editing tier).
   *
   * UNLOCK ONLY — PATCHes locked=false. The chain stays intact.
   * This is a REDEFINITION from FE-6170 (where unstage dissolved the run).
   * Full dissolve now lives only in releaseChain and the terminate flow.
   *
   * The BE refuses with HTTP 422 at the ultralock tier (run is running/stalled,
   * or any member project has staging_status == 'staging_complete'). This function
   * surfaces that 422 gracefully — the caller (ChainCockpitControls) hides the
   * button at ultralock, so this is defense-in-depth.
   *
   * @param {Object} run - the sequence run object
   * @returns {Promise<Object|null>} updated run on success, null on error
   */
  async function unstageChain(run) {
    try {
      const updated = await sequenceRunStore.unlockRun(run.id)
      showToast({
        message: 'Chain unstaged — tickboxes unlocked. You can edit membership and re-stage.',
        type: 'success',
        timeout: 5000,
      })
      return updated
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Could not unstage the chain.'
      showToast({ message: msg, type: 'error', timeout: 5000 })
      return null
    }
  }

  /**
   * terminateChain — graceful drain of the in-flight project.
   *
   * 1. Fetch the solo termination prompt for activePid and copy it to the
   *    clipboard so the user can paste it into the conductor terminal.
   * 2. Post a TERMINATE_CHAIN notice to the project's bound Hub thread so
   *    every agent in the project sees the signal on its next poll (BE-9012d
   *    Part 2 rewire off the retired bus -- the old `/api/v1/messages/send`
   *    broadcast never auto-woke recipients either, so this is byte-equivalent
   *    poll-based delivery, not a regression).
   * 3. PATCH the run: mark the active project as terminated and close the run.
   *
   * Note: do NOT archive the project here — archiving is the conductor's drain
   * step after the user pastes the termination prompt and the conductor closes
   * out gracefully.
   *
   * @param {Object} run - the sequence run object
   * @param {string} activePid - project ID of the currently in-flight project
   * @returns {Promise<boolean>}
   */
  async function terminateChain(run, activePid) {
    try {
      const { data } = await api.prompts.termination(activePid)
      const prompt = data?.prompt
      if (!prompt) throw new Error('No termination prompt returned')

      await copy(prompt)
      showToast({
        message: 'Termination prompt copied — paste it to let the conductor drain + close out gracefully.',
        type: 'success',
        timeout: 6000,
      })

      const thread = await resolveProjectThread(activePid)
      await commHub.postMessage(thread.thread_id, { content: 'TERMINATE_CHAIN', requires_action: false })

      await api.sequenceRuns.update(run.id, {
        project_statuses: { ...run.project_statuses, [activePid]: 'terminated' },
        status: 'terminated',
      })

      return true
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Could not terminate the chain.'
      showToast({ message: msg, type: 'error', timeout: 5000 })
      return false
    }
  }

  /**
   * handoverConductor — reuse the solo session-rotation handover.
   *
   * The continuation prompt built by BE-6165e already embeds the chain brief,
   * so no extra work is needed here — just pass the data through to the
   * HandoverModal for display.
   *
   * @param {string} conductorJobId
   * @returns {Promise<Object|undefined>} the handover data (retirement_prompt + continuation_prompt)
   */
  async function handoverConductor(conductorJobId) {
    try {
      const res = await api.agentJobs.simpleHandover(conductorJobId)
      return res.data
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Could not initiate conductor handover.'
      showToast({ message: msg, type: 'error', timeout: 5000 })
      return undefined
    }
  }

  /**
   * releaseChain — hard reset / "I killed my terminals".
   *
   * Calls the release endpoint with mode='cancel', which sets run status to
   * cancelled and frees all elected projects. The endpoint itself mutates
   * status; no separate PATCH is required.
   *
   * FE-6170: accepts an optional `onDissolved` callback invoked on success so
   * the caller (MissionControlView) can clear the transient selection and
   * re-hydrate the store, unlocking all checkboxes on both surfaces.
   *
   * @param {Object} run
   * @param {Function} [onDissolved] — called with no args after a successful release.
   * @returns {Promise<boolean>}
   */
  async function releaseChain(run, onDissolved) {
    try {
      await api.sequenceRuns.release(run.id, 'cancel')
      showToast({
        message:
          'Chain released — all elected projects freed. ' +
          '(Any still-running agents keep running; use Terminate for a graceful exit.)',
        type: 'success',
        timeout: 6000,
      })
      if (typeof onDissolved === 'function') await onDissolved()
      return true
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Could not release the chain.'
      showToast({ message: msg, type: 'error', timeout: 5000 })
      return false
    }
  }

  // (FE-6170 unstageChain-as-dissolve removed by FE-6171b — that function now
  // lives as the new unstageChain above: UNLOCK, not dissolve. dissolveChain
  // is the internal helper for releaseChain / terminate flows.)

  /**
   * resumeChain — resume-from-failure at the failed project.
   *
   * Steps:
   * 1. PATCH the run: reset status to 'running' and mark the failed project
   *    back to 'pending'. Do NOT increment current_index — that would skip the
   *    failed project (off-by-one trap).
   * 2. Restage the failed project so it returns to a launchable state.
   * 3. launchImplementation — the sacred per-call gate.
   *    NOTE: do NOT use reactivate_job here — it refuses closed-out/failed
   *    projects. launchImplementation is the correct entry point for projects
   *    that need to be re-driven by the conductor.
   *
   * @param {Object} run
   * @param {string} failedPid - project ID of the project that failed
   * @returns {Promise<boolean>}
   */
  async function resumeChain(run, failedPid) {
    try {
      // Do NOT pass current_index — off-by-one trap would skip the failed project.
      await api.sequenceRuns.update(run.id, {
        status: 'running',
        project_statuses: { ...run.project_statuses, [failedPid]: 'pending' },
      })

      await api.projects.restage(failedPid)

      // Sacred per-call gate (never reactivate_job — it refuses failed/closed projects).
      await api.projects.launchImplementation(failedPid)

      showToast({
        message:
          'Resuming at the failed project — paste the continuation prompt and cross the implement gate.',
        type: 'success',
        timeout: 6000,
      })
      return true
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Could not resume the chain.'
      showToast({ message: msg, type: 'error', timeout: 5000 })
      return false
    }
  }

  return { stageChain, unstageChain, terminateChain, handoverConductor, releaseChain, resumeChain }
}
