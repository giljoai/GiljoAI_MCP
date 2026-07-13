/**
 * useSequenceRunner — FE-6131e / FE-6165f
 *
 * Owns the "select projects → create a sequence run → navigate to the
 * sequence-scoped cockpit (staging phase)" flow shared by /projects and
 * /roadmap. Keeping the selection state and the run-creation call here
 * (rather than in each view) keeps the views thin (both are near the 800-line
 * guardrail) and gives the flow one tested home.
 *
 * Reuse-first: consumes the existing BE-6131a sequence-runs REST
 * (api.sequenceRuns) and the existing roadmap REST (api.roadmap.get) for the
 * default run order. NO new backend, NO new MCP tool. The dashboard CREATES the
 * run record + navigates to OBSERVE it; execution is CLI-driven (spec §11).
 *
 * Edition scope: CE.
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'
import { useToast } from '@/composables/useToast'
import {
  MAX_SEQUENCE_PROJECTS,
  DEFAULT_EXECUTION_MODE,
  computeChains,
  isChainLocked,
  orderByRoadmap,
  normalizeChainOrder,
} from '@/utils/sequenceOrder'

export function useSequenceRunner() {
  const router = useRouter()
  const { showToast } = useToast()

  const creating = ref(false)

  // --- Selection (keyed by PROJECT id; retains display metadata across pagination) ---
  const selection = ref(new Map()) // project_id → { id, name, taxonomy_alias }
  const selectedIds = computed(() => Array.from(selection.value.keys()))
  const selectedCount = computed(() => selection.value.size)
  // True while 2+ projects are elected — drives the per-card Activate / per-row
  // play fade (FE-6170) so the per-row/card single-project affordance stays
  // usable when exactly 1 project is elected (chain requires >=2).
  // Threshold raised from >0 to >=2 per FE-6170 sub-decision: do not dead-end
  // the user when they have elected exactly one project.
  const electionActive = computed(() => selection.value.size >= 2)

  function toggle(item) {
    // Key by project_id FIRST: roadmap rows carry BOTH a roadmap_item PK (`id`)
    // and a `project_id`; the checkbox membership test reads `project_id`, so the
    // selection Map MUST hold project_ids or the box never renders ticked
    // (FE-6165a). Project-list rows have no `project_id` field → `id` IS the
    // project_id, so the fallback keeps them correct.
    const id = item?.project_id || item?.id
    if (!id) return
    const next = new Map(selection.value)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.set(id, {
        id,
        name: item.name || item.title || '(untitled)',
        taxonomy_alias: item.taxonomy_alias || '',
      })
    }
    selection.value = next
  }

  function clear() {
    selection.value = new Map()
  }

  /**
   * Resolve a selected set into the run order: default = roadmap order, chain
   * members flagged `locked`. Reads LIVE get_roadmap at call time (spec §3 —
   * membership/order is read fresh, never regenerated). Roadmap-absent projects
   * sort to the end in their selection order.
   */
  async function resolveRunOrder(selected) {
    const rows = (selected || []).map((p) => ({
      project_id: p.id || p.project_id,
      name: p.name || p.title || '(untitled)',
      taxonomy_alias: p.taxonomy_alias || '',
    }))
    const orderMap = new Map()
    try {
      const { data } = await api.roadmap.get()
      const items = Array.isArray(data?.items) ? data.items : []
      for (const it of items) {
        // The roadmap list mixes project AND task rows — filter to projects.
        if (it.item_type === 'project' && it.project_id != null) {
          orderMap.set(it.project_id, it.sort_order ?? 0)
        }
      }
    } catch (err) {
      // No active product / no roadmap yet (404) — fall back to selection order.
      console.warn('[useSequenceRunner] roadmap unavailable; using selection order', err)
    }
    const chains = computeChains(rows)
    const ordered = normalizeChainOrder(orderByRoadmap(rows, orderMap), chains)
    return ordered.map((r) => ({ ...r, locked: isChainLocked(r, chains) }))
  }

  /**
   * Create the durable run record then navigate to the sequence-scoped cockpit.
   * review_policy is fixed to 'per_card' (spec decision #1 — a sequence run is
   * ALWAYS per-card review; never auto-close).
   */
  async function startSequence({ projectIds, resolvedOrder, executionMode }) {
    if (creating.value) return null
    if (!resolvedOrder?.length || resolvedOrder.length > MAX_SEQUENCE_PROJECTS) {
      showToast({
        message: `Select 1–${MAX_SEQUENCE_PROJECTS} projects to run sequentially.`,
        type: 'warning',
      })
      return null
    }
    creating.value = true
    try {
      const project_statuses = {}
      for (const pid of resolvedOrder) project_statuses[pid] = 'pending'
      const { data } = await api.sequenceRuns.create({
        project_ids: projectIds || resolvedOrder,
        resolved_order: resolvedOrder,
        execution_mode: executionMode || DEFAULT_EXECUTION_MODE,
        review_policy: 'per_card',
        status: 'pending',
        current_index: 0,
        project_statuses,
      })
      // FE-6174c: Mission Control is retired. Navigate to the /jobs multi variant
      // for the chain's HEAD project — same convention the FE-6174b ProjectTabStrip
      // tab-click uses (/projects/<pid>?run=<id>; useChainContext reads ?run= to
      // light up the conditional chain layer). The head is resolved_order[0]; fall
      // back to the locally-resolved order if the create response omits it.
      const headPid = data.resolved_order?.[0] || resolvedOrder?.[0]
      router.push({ name: 'ProjectLaunch', params: { projectId: headPid }, query: { run: data.id } })
      return data
    } catch (err) {
      const detail = err?.response?.data?.detail
      const message =
        typeof detail === 'string'
          ? detail
          : 'Could not start the sequence. Check your selection and try again.'
      showToast({ message, type: 'error' })
      return null
    } finally {
      creating.value = false
    }
  }

  return {
    creating,
    // selection
    selection,
    selectedIds,
    selectedCount,
    electionActive,
    toggle,
    clear,
    // primitives (exposed for direct use / tests)
    resolveRunOrder,
    startSequence,
  }
}
