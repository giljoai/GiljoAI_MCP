/**
 * useProjectFilters Composable
 *
 * Encapsulates search, type, and status filter state for the projects table.
 * Sorting is handled entirely by Vuetify's v-data-table — this composable
 * only filters.
 *
 * Extracted from ProjectsView.vue (Handover 0950k).
 */
import { ref, computed } from 'vue'

export function useProjectFilters({ projects, projectTypes, activeProduct }) {
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
    if (!filterStatus.value || filterStatus.value === 'all') return filteredBySearch.value
    return filteredBySearch.value.filter((p) => p.status === filterStatus.value)
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
    activeProductProjects,
    filteredBySearch,
    filteredProjects,
    clearFilters,
  }
}
