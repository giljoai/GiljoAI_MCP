/**
 * useChainTabControls — FE-6174b
 *
 * Extracted from ProjectTabs.vue (keeps it under the 800-line guardrail, mirroring
 * the earlier useProjectStaging / useExecutionMode extractions). Owns the chain
 * (multi-project) control wiring for the conditional /jobs variant: Stage Chain /
 * Implement button state, the per-tab Review flow, tab navigation, and the
 * execution-mode-on-the-run write.
 *
 * Reuse-only: drives the existing chain verbs (useChainLifecycle.stageChain /
 * unstageChain, useChainImplementation.copyImplPrompt) and sequenceRunStore.patchRun.
 * NO new endpoint / writer / store. All inert in solo — the host only calls these
 * when chainCtx is present.
 *
 * Edition scope: CE.
 */
import { ref, computed } from 'vue'
import { useSequenceRunStore } from '@/stores/sequenceRunStore'
import { useChainLifecycle } from '@/composables/useChainLifecycle'
import { useChainImplementation } from '@/composables/useChainImplementation'
import { useToast } from '@/composables/useToast'

/**
 * @param {Object}   opts
 * @param {import('vue').Ref<Object|null>} opts.chainCtx  the chain bundle (or null)
 * @param {import('vue').Ref<string|null>} opts.projectId the currently viewed project
 * @param {Object}   opts.router  vue-router instance
 * @param {Object}   opts.route   vue-router route
 * @param {import('vue').Ref<string>} [opts.activeTab] the host's launch/jobs tab
 *                   ref. After a successful chain Implement this composable flips it
 *                   to 'jobs' (solo parity with onLaunchSuccess). Optional/inert if
 *                   omitted.
 * @param {() => void} [opts.onUserNav] FE-6218 anti-hijack hook. Called when the
 *                   user drives navigation themselves (tab-strip select / Implement)
 *                   so useChainAutoNav opens its suppression window and the WS echo
 *                   of the user's own action never auto-yanks the pane. Defaults to a
 *                   no-op, so existing callers/tests are unaffected.
 */
export function useChainTabControls({ chainCtx, projectId, router, route, activeTab, onUserNav = () => {} }) {
  const sequenceRunStore = useSequenceRunStore()
  const { stageChain, unstageChain } = useChainLifecycle()
  const { copyImplPrompt } = useChainImplementation()
  const { showToast } = useToast()

  const chainStaging = ref(false)
  const showChainReview = ref(false)
  const chainReviewTab = ref(null)

  const chainStageText = computed(() => (chainCtx.value?.locked ? 'Unstage Chain' : 'Stage Chain'))
  const chainStageDisabled = computed(
    () => chainStaging.value || !chainCtx.value?.run?.execution_mode,
  )
  const chainStageColor = computed(() => {
    if (!chainCtx.value) return undefined
    return chainCtx.value.locked ? undefined : 'yellow-darken-2'
  })
  const chainStageTitle = computed(() => {
    if (!chainCtx.value) return ''
    if (chainCtx.value.locked) return 'Unlock the chain to edit descriptions, order, and mode'
    if (!chainCtx.value.run?.execution_mode) return 'Select an execution mode first'
    return 'Lock the chain and copy the staging prompt'
  })
  // Implement arms once the chain is STAGED and the conductor has written the chain
  // mission, and the run has not started implementing or finished.
  //
  // FE-6199 fix: do NOT gate on per-member 'staging_complete'. Projects only reach
  // staging_complete DURING drive (after Implement, when each sub-orch self-stages),
  // so gating Implement on it was a chicken-and-egg deadlock (the button could never
  // light). And run.project_statuses never holds 'staging_complete' anyway — it holds
  // pending/staged/implementing/... (project-level staging_status is a separate field).
  // The authoritative, live-refreshed (sequence:updated) run-record signal for "the
  // conductor finished staging" is: locked (Stage Chain pressed) + chain_mission
  // written + the run still in a pre-implementation status (pending/staged). Once the
  // run starts (running/implementing) or ends (completed/failed/stalled/terminated) the
  // button hides — that was FE-6173 C1's real complaint (it wrongly showed on finished
  // runs and hid during staging).
  const chainImplementReady = computed(() => {
    const ctx = chainCtx.value
    if (!ctx) return false
    const run = ctx.run
    if (ctx.locked !== true) return false
    if (!(run?.chain_mission ?? '').trim()) return false
    return run?.status === 'pending' || run?.status === 'staged'
  })

  // Execution mode is stored on the RUN (one mode for the whole chain). Await +
  // catch so a failed write surfaces a toast (matching the solo convention) and
  // never leaves an unhandled rejection. patchRun is non-optimistic (it mutates
  // store state only from the server response), so on failure the selector simply
  // stays on the previous mode.
  async function patchRunMode(mode) {
    if (!chainCtx.value || chainCtx.value.locked) return
    try {
      await sequenceRunStore.patchRun(chainCtx.value.runId, { execution_mode: mode })
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Could not change the chain execution mode.'
      showToast({ message: msg, type: 'error', timeout: 5000 })
    }
  }

  async function handleChainStage() {
    if (!chainCtx.value) return
    chainStaging.value = true
    try {
      if (chainCtx.value.locked) {
        await unstageChain(chainCtx.value.run)
      } else {
        await stageChain(chainCtx.value.run)
      }
    } finally {
      chainStaging.value = false
    }
  }

  async function handleChainImplement() {
    if (!chainCtx.value) return
    // FE-6218: a user-driven Implement — open the anti-hijack window so the
    // resulting implementation_launched WS echo does not double-flip the pane.
    onUserNav()
    // Head pid = resolved_order[0] (fall back to project_ids / the first tab).
    // The head's launch gate is crossed inside copyImplPrompt before the
    // chain-implementation prompt is fetched (mirrors the solo play button).
    const run = chainCtx.value.run
    const headPid =
      run?.resolved_order?.[0] || run?.project_ids?.[0] || chainCtx.value.tabs?.[0]?.projectId || null
    const ok = await copyImplPrompt(chainCtx.value.runId, headPid)
    // Solo parity (Bug 2): after a successful Implement, auto-switch the /jobs view
    // to the Implementation variant (solo does this via onLaunchSuccess). Only on
    // success — a failed copy/launch leaves the user on the Staging tab to retry.
    if (ok && activeTab) {
      activeTab.value = 'jobs'
      if (route.query.via !== 'jobs') {
        router.replace({ query: { ...route.query, via: 'jobs' } })
      }
    }
  }

  // Tab strip: switch the viewed project (carry ?run so the chain layer persists).
  function handleTabSelect(pid) {
    if (!pid || pid === projectId.value) return
    // FE-6218: a user-driven tab-strip switch — open the anti-hijack window so a
    // concurrent headless drive does not immediately yank the pane off the member
    // the user just chose.
    onUserNav()
    router.push({ name: 'ProjectLaunch', params: { projectId: pid }, query: { ...route.query } })
  }

  function handleTabReview(tab) {
    chainReviewTab.value = tab
    showChainReview.value = true
  }

  function handleChainReviewComplete() {
    // UI-2 / BE-6177: do NOT patch project_statuses (stale-spread eject risk).
    showChainReview.value = false
    const runId = chainCtx.value?.runId
    const reviewedPid = chainReviewTab.value?.projectId
    chainReviewTab.value = null

    // Mark this member reviewed in the client-side set BEFORE finding next
    // (optimistic — the synchronous allDone/nextUnreviewed reads below depend on it).
    if (runId && reviewedPid) {
      sequenceRunStore.markReviewed(runId, reviewedPid)
      // BE-9098: persist the review so the badge survives refresh/navigation. Fire-
      // and-forget (non-gating); a failure surfaces a toast (patchRunMode convention)
      // and leaves the optimistic mark in place (it self-corrects on next hydrate).
      sequenceRunStore.markReviewedRemote(runId, reviewedPid).catch((err) => {
        const msg =
          err?.response?.data?.detail || err?.message || 'Could not save the review; it may reappear after refresh.'
        showToast({ message: msg, type: 'error', timeout: 5000 })
      })
    }

    // Read from store synchronously (just updated above) — not tab.needsReview (lags prop cycle).
    const tabs = chainCtx.value?.tabs || []
    // Terminal gate: leave /jobs ONLY when EVERY chain member is completed AND reviewed.
    const allDone = tabs.length > 0 && tabs.every(
      (t) => t.isCompleted && sequenceRunStore.isReviewed(runId, t.projectId),
    )
    if (allDone) {
      router.push('/projects') // the ONLY path that may leave /jobs
      return
    }
    // Not finished: stay in /jobs. If another member is ALREADY completed-and-unreviewed,
    // advance to it (preserves the review-walk); else do NOTHING — remain on the just-reviewed
    // member so its banner flips green (C2). NEVER /projects here.
    const nextUnreviewed = tabs.find(
      (t) => t.isCompleted && !sequenceRunStore.isReviewed(runId, t.projectId),
    )
    if (nextUnreviewed && nextUnreviewed.projectId !== reviewedPid) {
      router.push({ name: 'ProjectLaunch', params: { projectId: nextUnreviewed.projectId }, query: { ...route.query } })
    }
  }

  return {
    chainStaging,
    showChainReview,
    chainReviewTab,
    chainStageText,
    chainStageDisabled,
    chainStageColor,
    chainStageTitle,
    chainImplementReady,
    patchRunMode,
    handleChainStage,
    handleChainImplement,
    handleTabSelect,
    handleTabReview,
    handleChainReviewComplete,
  }
}
