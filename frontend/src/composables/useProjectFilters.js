/**
 * useProjectFilters Composable
 *
 * Encapsulates search, type, and status filter state for the projects table.
 * Sorting is handled entirely by Vuetify's v-data-table — this composable
 * only filters.
 *
 * Extracted from ProjectsView.vue (Handover 0950k).
 *
 * BE-5039: `statusSelectOptions` derives the filter dropdown items from
 * the canonical project-status enum exposed by `projectStatusesStore`.
 * The 'hidden' pseudo-option is appended client-side because hidden is
 * a UI-state (the `hidden` flag on the project), not a status enum
 * member. Callers may pass `projectStatuses` as a Vue ref of the
 * canonical metadata array so the composable stays test-friendly
 * without depending on Pinia at unit-test time.
 */
import { ref, computed } from 'vue'

export function useProjectFilters({
  projects,
  projectTypes,
  activeProduct,
  projectStatuses = ref([]),
}) {
  const searchQuery = ref('')
  const filterType = ref(null)
  const filterStatus = ref(null)
  const currentPage = ref(1)
  const itemsPerPage = ref(10)

  const typeSelectOptions = computed(() => {
    const items = projectTypes.value.map((t) => ({
      title: t.abbreviation,
      value: t.id,
    }))
    items.push({ title: 'No Type', value: 'none' })
    return items
  })

  /**
   * Status filter dropdown items, derived from the canonical
   * `projectStatusesStore` payload (BE-5039). When the store hasn't
   * loaded yet the array is empty — callers should treat this as
   * "filter unavailable" rather than rendering a stale list. The
   * `hidden` option is appended last; it filters by the per-project
   * `hidden` UI flag, not by an enum member.
   */
  const statusSelectOptions = computed(() => {
    const items = (projectStatuses.value || []).map((s) => ({
      title: s.label,
      value: s.value,
    }))
    items.push({ title: 'Hidden', value: 'hidden' })
    return items
  })

  /**
   * Set of canonical status values (string), used to defensively drop
   * orphan values that may surface from stale WebSocket payloads during
   * a deploy window. Empty until the store loads.
   */
  const validStatusValues = computed(
    () => new Set((projectStatuses.value || []).map((s) => s.value)),
  )

  const activeProductProjects = computed(() => {
    if (!activeProduct.value) return []
    return projects.value.filter(
      (p) => p.product_id === activeProduct.value.id && !p.deleted_at,
    )
  })

  const filteredBySearch = computed(() => {
    let results = activeProductProjects.value

    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      results = results.filter(
        (p) =>
          p.name.toLowerCase().includes(query) ||
          p.mission?.toLowerCase().includes(query) ||
          p.id.toLowerCase().includes(query) ||
          p.taxonomy_alias?.toLowerCase().includes(query),
      )
    }

    if (filterType.value && filterType.value !== 'all') {
      if (filterType.value === 'none') {
        results = results.filter((p) => !p.project_type_id)
      } else {
        results = results.filter((p) => p.project_type_id === filterType.value)
      }
    }

    return results
  })

  const filteredProjects = computed(() => {
    let results = filteredBySearch.value

    // CE-OPT-4: Hidden exclusion is independent of other filters.
    // Only show hidden projects when filterStatus is explicitly 'hidden'.
    // Exception: active search query is "nuclear" — searches ALL projects including hidden.
    if (filterStatus.value === 'hidden') {
      return results.filter((p) => p.hidden)
    }
    if (!searchQuery.value) {
      results = results.filter((p) => !p.hidden)
    }

    if (filterStatus.value && filterStatus.value !== 'all') {
      return results.filter((p) => p.status === filterStatus.value)
    }
    return results
  })

  function clearFilters() {
    searchQuery.value = ''
    filterStatus.value = null
    filterType.value = null
  }

  return {
    searchQuery,
    filterType,
    filterStatus,
    currentPage,
    itemsPerPage,
    typeSelectOptions,
    statusSelectOptions,
    validStatusValues,
    activeProductProjects,
    filteredBySearch,
    filteredProjects,
    clearFilters,
  }
}
