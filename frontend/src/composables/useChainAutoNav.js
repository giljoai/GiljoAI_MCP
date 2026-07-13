/**
 * useChainAutoNav — FE-6218 (solo extension: FE-6228)
 *
 * Live-follow for a HEADLESS drive (chain sequence-run OR a single solo project).
 * When a conductor/agent drives over MCP tools — no dashboard clicks — the backend
 * already broadcasts state live and the stores already re-hydrate reactively:
 *   - `sequence:updated`              -> sequenceRunStore.handleSequenceUpdated (current_index)
 *   - `project:staging_complete`      -> projectStateStore.handleStagingComplete
 *   - `project:implementation_launched` -> projectStateStore.handleImplementationLaunched
 * The GAP this closes: the active pane never AUTO-NAVIGATES to track the drive.
 * Tab/pane flips fire ONLY on user clicks today (useChainTabControls
 * handleChainImplement; ProjectTabs onLaunchSuccess). So a user watching the
 * dashboard while a headless drive runs sees badges update but is NOT carried
 * staging -> implement/jobs.
 *
 * This composable ADDS an event-driven flip OVER the existing reactive plumbing —
 * it introduces NO new store, broker, or navigation system, and runs ALONGSIDE
 * the existing user-click flips; it never replaces them.
 *
 * What it does — split by scope (FE-6228):
 *   SAME-PROJECT flips (fire in BOTH solo and chain — gated ONLY on the
 *   anti-hijack window, not on chain membership):
 *     - viewed project reaches staging_complete    -> flip to the implement/launch surface
 *     - viewed project's implementation launches    -> flip to the jobs pane
 *   CROSS-PROJECT advance (chain ONLY — a solo run has a single project and must
 *   NEVER navigate to a different project route):
 *     - chain advances to a new member (currentPid moves) -> navigate to that member,
 *       preserving ?run, landing on the jobs pane (reuses the ProjectLaunch route seam)
 *
 * ANTI-HIJACK (load-bearing UX): a user actively driving via their OWN clicks must
 * not be yanked. Every existing user-action seam calls markUserAction(), opening a
 * short suppression window; the WS echo of the user's own action lands inside that
 * window and is ignored. Only a headless/external drive (no recent local action)
 * carries the user along — this holds identically for solo and chain.
 *
 * Solo behavior (FE-6228): the two same-project flips now carry a SOLO headless run
 * (chainCtx null) too; the cross-project advance watcher stays fully inert in solo
 * (chainBlocked() short-circuits on !chainCtx), so solo can never cross-navigate.
 *
 * Reuse map (build NO new store/broker/nav system): sequenceRunStore.activeRun
 * (read via chainCtx.currentPid) + projectStateStore flags (state — exist); the
 * ProjectLaunch route + the activeTab/router.replace seam (the flip — exists).
 *
 * Edition scope: CE.
 */
import { watch } from 'vue'
import { useProjectStateStore } from '@/stores/projectStateStore'

// Anti-hijack: ignore auto-nav for this many ms after a local user action, so a
// user's own click (and its WS echo) never yanks their pane. Short by design —
// once the window lapses, a still-running headless drive resumes carrying the
// user along. The window only needs to outlast the click -> REST -> broadcast ->
// WS echo round-trip.
export const USER_ACTION_GUARD_MS = 4000

/**
 * @param {Object} opts
 * @param {import('vue').Ref<Object|null>} opts.chainCtx   chain bundle (or null in solo)
 * @param {import('vue').Ref<string|null>} opts.projectId  the currently viewed project
 * @param {import('vue').Ref<string>}      opts.activeTab   host launch/jobs tab ref (the flip seam)
 * @param {Object} opts.router  vue-router instance
 * @param {Object} opts.route   vue-router route
 * @param {() => number} [opts.now]  injectable clock (defaults to Date.now) — for deterministic tests
 * @returns {{ markUserAction: () => void }}
 */
export function useChainAutoNav({ chainCtx, projectId, activeTab, router, route, now = () => Date.now() }) {
  const projectStateStore = useProjectStateStore()

  let suppressUntil = 0

  /** Existing user-action seams call this to open the anti-hijack suppression window. */
  function markUserAction() {
    suppressUntil = now() + USER_ACTION_GUARD_MS
  }

  // Anti-hijack window only. The SAME-PROJECT pane flips gate on THIS alone — they
  // are valid in BOTH solo and chain, because a headless drive of the VIEWED project
  // should carry the user's pane regardless of chain membership (FE-6228). While a
  // user's own action is still echoing over WS, this is true and the flip is skipped.
  function suppressed() {
    return now() < suppressUntil
  }

  // Cross-project advance gate: chain-only. In solo chainCtx is null, so this is
  // always true and the advance watcher stays fully inert — a solo run can never
  // cross-navigate to a different project route. Also honors the anti-hijack window.
  function chainBlocked() {
    return !chainCtx?.value || suppressed()
  }

  // Viewed member reaches staging_complete -> implement/launch surface. Reading
  // the VIEWED project's flag scopes this to the pane the user is on: a sibling
  // member being driven changes its OWN state, not this getter, so no spurious flip.
  watch(
    () => projectStateStore.getProjectState(projectId.value)?.stagingComplete === true,
    (isComplete, was) => {
      if (!isComplete || was) return // rising edge only (the flag is monotonic)
      if (suppressed()) return // anti-hijack only — fires in solo AND chain
      activeTab.value = 'launch'
    },
  )

  // Viewed member's implementation launches -> jobs pane.
  //
  // TSK-6254 / BE-9111: the backend tags the project:implementation_launched
  // broadcast with an authoritative source (surfaced by the store as lastLaunchSource):
  //   - "mcp" -> a headless MCP/conductor drive: always FOLLOW it (flip to jobs).
  //   - "ui"  -> a dashboard Implement click: fall through to the per-window
  //             anti-hijack window. The CLICKING window opened its own suppression
  //             window via markUserAction(), so its WS echo is ignored and it stays
  //             put; every OTHER window/surface (projects-table play button, a second
  //             window, or a view switch — none of which called markUserAction here)
  //             has no window open and follows the drive. TSK-6254 wrongly made "ui"
  //             mean "never flip on any surface", stranding those cases (BE-9111).
  //   - absent (older backend / untagged) -> same per-window anti-hijack fallback.
  watch(
    () => projectStateStore.getProjectState(projectId.value)?.implementationLaunched === true,
    (launched, was) => {
      if (!launched || was) return // rising edge only (the flag is monotonic)
      const source = projectStateStore.getProjectState(projectId.value)?.lastLaunchSource || null
      // Authoritative headless drive: always follow.
      if (source === 'mcp') {
        activeTab.value = 'jobs'
        return
      }
      // "ui" or absent: the clicking window is protected by its own suppression
      // window; every other window/surface follows once the window lapses.
      if (suppressed()) return // anti-hijack fallback — fires in solo AND chain
      activeTab.value = 'jobs'
    },
  )

  // Chain advances to a new member (current_index moved -> currentPid changes) ->
  // follow it to the jobs pane. Navigate via the EXISTING ProjectLaunch route seam
  // (the chain tab-select shape), preserving ?run; tab=jobs lands the new mount on
  // the Implementation pane.
  //
  // Rule-3 guard (FE-6221b): the cross-project router.replace is ONLY allowed when
  // the user is inside the ?run= cockpit. Without ?run, useChainContext returns null,
  // so chainCtx should also be null — but this guard makes the invariant explicit and
  // refactor-proof: even if chainCtx somehow becomes non-null outside the cockpit,
  // the advance watcher cannot yank the user to a different project route.
  watch(
    () => chainCtx?.value?.currentPid || null,
    (pid, prev) => {
      if (!pid || !prev || pid === prev) return // genuine advance only (not initial / unchanged)
      if (chainBlocked()) return // chain-only (inert in solo) + anti-hijack
      if (pid === projectId.value) {
        activeTab.value = 'jobs'
        return
      }
      // Rule-3 gate: only follow to a different project when inside the ?run= cockpit.
      if (!route.query?.run) return
      router.replace({
        name: 'ProjectLaunch',
        params: { projectId: pid },
        query: { ...route.query, tab: 'jobs' },
      })
    },
  )

  return { markUserAction }
}
