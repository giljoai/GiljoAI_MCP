/**
 * useProjectFilters Composable
 *
 * Owns the projects-table FILTER + SORT + PAGINATION state and builds the
 * server query from it. BE-6076 moved search + multi-status + hidden filtering
 * AND sort + pagination into SQL, so this composable no longer slices the list
 * client-side — it is the source of truth for the controls and translates them
 * into the params `projectStore.fetchProjects` sends.
 *
 * Composes with BE-6078 (UX preserved, now server-driven):
 *  - Status is a MULTI-SELECT (checkboxes), persisted per-browser in
 *    localStorage. The selection drives the server `statuses` param. An empty
 *    selection means "show nothing" (the store short-circuits to an empty page),
 *    matching the prior client behavior — NOT a silent default-to-all.
 *  - Search is "nuclear": a non-empty query matches across ALL lifecycle
 *    statuses (the status multi-select is ignored while searching), handled
 *    server-side.
 *  - Hidden is a SEPARATE per-row axis. "Show hidden" sets the server
 *    `include_hidden` param so hidden rows join the page; `hiddenProjects`
 *    (fetched separately) only powers the "Show hidden (N)" count badge.
 *
 * `projectStatuses` is the canonical status metadata (from
 * `projectStatusesStore`); callers may pass it as a Vue ref so the composable
 * stays Pinia-free at unit-test time.
 */
import { ref, computed, watch } from 'vue'

// Per-browser persistence of the status multi-select (migration-free; promote
// to a user-settings DB field only if cross-device persistence is later wanted).
const STATUS_STORAGE_KEY = 'giljo.projects.selectedStatuses'

function loadPersistedStatuses() {
  try {
    const raw = localStorage.getItem(STATUS_STORAGE_KEY)
    if (raw === null) return null
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((v) => typeof v === 'string') : null
  } catch {
    return null
  }
}

export function useProjectFilters({
  activeProduct,
  projectStatuses = ref([]),
  hiddenProjects = ref([]),
  showHidden = ref(false),
}) {
  const searchQuery = ref('')
  const currentPage = ref(1)
  const itemsPerPage = ref(10)
  // Single-column server sort (v-data-table-server `must-sort`). Default matches
  // the prior client default (newest first).
  const sortBy = ref([{ key: 'created_at', order: 'desc' }])

  /**
   * Status multi-select dropdown items, derived from the canonical
   * `projectStatusesStore` payload (BE-5039). No 'hidden' pseudo-option — hidden
   * is an orthogonal server-side axis now, surfaced as "Show hidden (N)".
   */
  // 'deleted' is NOT a selectable filter here — soft-deleted projects are reached
  // via the separate "Deleted (N)" dialog, not the status multi-select. Exclude it
  // from both the dropdown options and the default "all" selection.
  const _selectableStatuses = computed(() =>
    (projectStatuses.value || []).filter((s) => s.value !== 'deleted'),
  )

  const statusSelectOptions = computed(() =>
    _selectableStatuses.value.map((s) => ({ title: s.label, value: s.value })),
  )

  const allStatusValues = computed(() => _selectableStatuses.value.map((s) => s.value))

  // Selected statuses: load any persisted selection; otherwise default to
  // all-checked once the canonical status list is known (full listing).
  const persisted = loadPersistedStatuses()
  const selectedStatuses = ref(persisted ?? [])
  let defaulted = persisted !== null

  watch(
    allStatusValues,
    (vals) => {
      if (!defaulted && vals.length) {
        selectedStatuses.value = [...vals]
        defaulted = true
      }
    },
    { immediate: true },
  )

  // Persist every change (default-all included — that IS the default rule).
  watch(
    selectedStatuses,
    (vals) => {
      try {
        localStorage.setItem(STATUS_STORAGE_KEY, JSON.stringify(vals))
      } catch {
        /* localStorage unavailable (private mode / quota) — non-fatal */
      }
    },
    { deep: true },
  )

  // Count of hidden projects for the active product — drives the conditional
  // "Show hidden (N)" affordance (rendered only when > 0).
  const hiddenCount = computed(() => {
    if (!activeProduct.value) return 0
    return (hiddenProjects.value || []).filter(
      (p) => p.product_id === activeProduct.value.id && !p.deleted_at,
    ).length
  })

  /**
   * Build the server query for `projectStore.fetchProjects`. Pure function of
   * the current control state — call it on every control change to re-fetch the
   * page. Nuclear search wins over the status multi-select; an empty selection
   * (while not searching) yields an empty `statuses` array (empty page).
   */
  function buildServerParams() {
    const params = {
      limit: itemsPerPage.value,
      offset: (currentPage.value - 1) * itemsPerPage.value,
    }
    const sb = sortBy.value && sortBy.value[0]
    if (sb && sb.key) {
      params.sort = sb.key
      params.sortDir = sb.order || 'asc'
    }
    const q = (searchQuery.value || '').trim()
    if (q) {
      params.search = q
      // BE-2002: search is "nuclear" over the hidden axis too. Archived (hidden)
      // rows are excluded from default views, but a user searching must be able to
      // find something they archived — so a query always reveals hidden rows
      // (the frontend badges them "Archived"). Mirrors the store's search ->
      // include_completed widening. Default (non-search) views stay unchanged.
      params.includeHidden = true
    } else {
      params.statuses = [...selectedStatuses.value]
    }
    if (showHidden.value) {
      params.includeHidden = true
    }
    return params
  }

  return {
    searchQuery,
    selectedStatuses,
    showHidden,
    currentPage,
    itemsPerPage,
    sortBy,
    statusSelectOptions,
    hiddenCount,
    buildServerParams,
  }
}
