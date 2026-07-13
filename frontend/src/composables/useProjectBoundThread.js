/**
 * useProjectBoundThread — BE-9012d Part 1/2
 *
 * Resolve (or create) THE project's canonical bound Hub thread, replicating
 * CommThreadService.resolve_or_create_bound_thread's precedence (ce_0072 D8
 * migration + D9 shims) client-side: exactly one live project-bound thread ->
 * use it; none -> create one with the reserved marker subject; several -> the
 * marker-subject one if present, else the oldest. Composed from the existing
 * threads.list/threads.create calls (via commHubStore) -- no new endpoint.
 *
 * Shared by any UI that needs to post to "the" project's Hub thread rather
 * than a user-selected one: MessageComposer.vue's Orchestrator/Broadcast
 * buttons, and useChainLifecycle's terminateChain() TERMINATE_CHAIN notice
 * (both formerly posted via the now-retired agent bus, `/api/v1/messages/*`).
 *
 * Also shared by read-only surfaces that must resolve the SAME thread without
 * ever creating one: the Project Review pane's read-only "Project Comms"
 * timeline (Phase 5 / D1(a)) and the /jobs message icon deep-link
 * (useJobActions.handleMessages), via resolveExistingProjectThread below.
 *
 * Edition scope: CE.
 */
import { useCommHubStore } from '@/stores/commHubStore'

// Reserved subject stamped on a bound thread this resolver creates when a
// project has none yet. MUST mirror
// giljo_mcp.models.comm.BOUND_THREAD_MARKER_SUBJECT / ce_0072's
// _BOUND_THREAD_MARKER -- kept as a literal here (like the migration) since
// this is a cross-layer protocol constant, not app state.
const BOUND_THREAD_MARKER_SUBJECT = '(project comms)'

// Internal — the deterministic pick (no side effects). Shared by both the
// create-if-missing and read-only resolvers so their precedence can never
// drift apart: exactly-one candidate -> it; none -> null (caller decides
// whether to create); several -> the marker-subject one, else the OLDEST by
// created_at.
function _pickBoundThread(candidates) {
  if (candidates.length === 0) return null
  if (candidates.length === 1) return candidates[0]
  const marked = candidates.find((t) => t.subject === BOUND_THREAD_MARKER_SUBJECT)
  if (marked) return marked
  return candidates.reduce((oldest, t) =>
    new Date(t.created_at) < new Date(oldest.created_at) ? t : oldest,
  )
}

export function useProjectBoundThread() {
  const commHub = useCommHubStore()

  /**
   * Resolve THE project's bound Hub thread, creating one if none exists yet.
   */
  async function resolveProjectThread(projectId) {
    await commHub.loadThreads({ project_id: projectId })
    const candidates = commHub.projectThreadList.filter((t) => t.project_id === projectId)
    const existing = _pickBoundThread(candidates)
    if (existing) return existing
    return commHub.createThread({ project_id: projectId, subject: BOUND_THREAD_MARKER_SUBJECT })
  }

  /**
   * Resolve THE project's bound Hub thread WITHOUT creating one. Returns null
   * when the project has no bound thread yet -- read-only surfaces must not
   * mutate state as a side effect of being viewed.
   */
  async function resolveExistingProjectThread(projectId) {
    await commHub.loadThreads({ project_id: projectId })
    return _pickBoundThread(commHub.projectThreadList.filter((t) => t.project_id === projectId))
  }

  return { resolveProjectThread, resolveExistingProjectThread }
}
