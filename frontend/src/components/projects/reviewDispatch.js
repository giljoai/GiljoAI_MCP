/**
 * reviewDispatch.js — FE-6174c
 *
 * Pure helpers extracted from ProjectTabs.vue so both the host component and
 * specs import the SAME code (zero drift between component logic and test).
 *
 * Edition scope: CE.
 */

/**
 * Predicate: should the "Review project" button be visible?
 *
 * Chain context: show only when the VIEWED member needs review.
 * Solo context (chainCtx null): pass showCloseoutButton through unchanged.
 *
 * @param {Object|null} chainCtx
 * @param {Object|null} currentChainTab  the tab matching the currently viewed project
 * @param {boolean}     showCloseoutButton  the solo closeout eligibility flag
 */
export function buildChainAwareShowCloseout(chainCtx, currentChainTab, showCloseoutButton) {
  if (chainCtx) {
    return Boolean(currentChainTab?.needsReview)
  }
  return showCloseoutButton
}

/**
 * Dispatcher factory: returns a zero-arg function that routes the button click
 * correctly without capturing the closure early.
 *
 * Chain branch → calls handleTabReview(currentChainTab).
 *   The chain CloseoutModal is suppress-navigation + projectStatus='completed'.
 *   NEVER calls openCloseoutModal (that is the 28f25f9f7 eject vector).
 *
 * Solo branch → calls openCloseoutModal().
 *
 * @param {Object|null}   chainCtx
 * @param {Object|null}   currentChainTab
 * @param {Function}      handleTabReview   from useChainTabControls
 * @param {Function}      openCloseoutModal from useProjectCloseout
 */
export function buildReviewDispatcher(chainCtx, currentChainTab, handleTabReview, openCloseoutModal) {
  if (chainCtx && currentChainTab) {
    return () => handleTabReview(currentChainTab)
  }
  return () => openCloseoutModal()
}

/**
 * Computes the "done status" string to show the green State-A "Project Completed
 * and Closed" chip for a chain member after it has been reviewed and closed.
 *
 * Chain context:
 *   - member isCompleted AND already reviewed (!needsReview) → 'completed' (green chip)
 *   - member still needs review, or not yet completed → null (suppress)
 * Solo context (chainCtx null): pass projectDoneStatus through unchanged (byte-identical).
 *
 * Reactivity path: markReviewed → reviewedProjects Map → useChainContext tabs computed
 * → chainCtx prop → currentChainTab → this computed. One-tick prop lag is fine.
 *
 * @param {Object|null} chainCtx
 * @param {Object|null} currentChainTab  the tab matching the currently viewed project
 * @param {string|null} projectDoneStatus  the solo done-status value
 */
export function buildChainAwareProjectDoneStatus(chainCtx, currentChainTab, projectDoneStatus) {
  if (!chainCtx) return projectDoneStatus // SOLO byte-identical passthrough
  return (currentChainTab?.isCompleted && !currentChainTab.needsReview) ? 'completed' : null
}
