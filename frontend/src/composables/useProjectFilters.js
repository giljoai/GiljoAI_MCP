/**
 * useProjectFilters Composable
 *
 * Encapsulates search, type, and status filter state for the projects table.
 * Accepts reactive refs for projects, projectTypes, and activeProduct, and
 * returns filter refs, a sortedProjects computed, and a clearFilters helper.
 *
 * Extracted from ProjectsView.vue (Handover 0950k).
 *
 * @param {object} params
 * @param {import('vue').Ref<Array>} params.projects - Raw project array
 * @param {import('vue').Ref<Array>} params.projectTypes - Available project type objects
 * @param {import('vue').Ref<object|null>} params.activeProduct - Currently active product
 */
import { ref, computed } from 'vue'

export function useProjectFilters({ projects, projectTypes, activeProduct }) {
  const searchQuery = ref('')
  const filterType = ref(null)
  const filterStatus = ref(null)
  const currentPage = ref(1)
  const itemsPerPage = ref(10)
  const sortConfig = ref([{ key: 'created_at', order: 'desc' }])

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

  const sortedProjects = computed(() => {
    const sorted = [...filteredProjects.value]

    sorted.sort((a, b) => {
      const aActive = a.status === 'active' ? 0 : 1
      const bActive = b.status === 'active' ? 0 : 1
      if (aActive !== bActive) return aActive - bActive

      if (sortConfig.value && sortConfig.value.length > 0) {
        const { key, order } = sortConfig.value[0]
        const isAsc = order === 'asc'

        if (key === 'name') {
          const aType = a.project_type?.abbreviation || 'ZZZ'
          const bType = b.project_type?.abbreviation || 'ZZZ'
          if (aType !== bType) {
            return isAsc ? aType.localeCompare(bType) : bType.localeCompare(aType)
          }

          const aSeries = a.series_number || 99999
          const bSeries = b.series_number || 99999
          if (aSeries !== bSeries) {
            return isAsc ? aSeries - bSeries : bSeries - aSeries
          }

          const aSub = a.subseries || ''
          const bSub = b.subseries || ''
          if (aSub !== bSub) {
            return isAsc ? aSub.localeCompare(bSub) : bSub.localeCompare(aSub)
          }

          const aName = a.name.toLowerCase()
          const bName = b.name.toLowerCase()
          return isAsc ? aName.localeCompare(bName) : bName.localeCompare(aName)
        }

        let aVal = a[key]
        let bVal = b[key]

        if (!aVal) aVal = ''
        if (!bVal) bVal = ''

        if (typeof aVal === 'string') {
          aVal = aVal.toLowerCase()
          bVal = bVal.toLowerCase()
        }

        if (aVal < bVal) return isAsc ? -1 : 1
        if (aVal > bVal) return isAsc ? 1 : -1
      }

      return 0
    })

    return sorted
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
    sortConfig,
    typeSelectOptions,
    activeProductProjects,
    filteredBySearch,
    filteredProjects,
    sortedProjects,
    clearFilters,
  }
}
