/**
 * useTaskFilters Composable
 *
 * Encapsulates search and dropdown filter state for the task list.
 * Accepts a reactive tasks array and returns filter refs, a filteredTasks
 * computed, and a clearFilters helper.
 *
 * Extracted from TasksView.vue (Handover 0950k).
 *
 * @param {import('vue').Ref<Array>} tasks - Raw task array (ref or computed)
 * @returns {{ search, statusFilter, priorityFilter, categoryFilter, filteredTasks, clearFilters }}
 */
import { ref, computed } from 'vue'

export function useTaskFilters(tasks) {
  const search = ref('')
  const statusFilter = ref(null)
  const priorityFilter = ref(null)
  const categoryFilter = ref(null)

  const filteredTasks = computed(() => {
    let list = tasks.value

    if (search.value) {
      const term = search.value.toLowerCase()
      list = list.filter((t) => t.title?.toLowerCase().includes(term))
    }

    if (statusFilter.value) {
      list = list.filter((t) => t.status === statusFilter.value)
    }

    if (priorityFilter.value) {
      list = list.filter((t) => t.priority === priorityFilter.value)
    }

    if (categoryFilter.value) {
      list = list.filter((t) => t.category === categoryFilter.value)
    }

    return list
  })

  function clearFilters() {
    search.value = ''
    statusFilter.value = null
    priorityFilter.value = null
    categoryFilter.value = null
  }

  return {
    search,
    statusFilter,
    priorityFilter,
    categoryFilter,
    filteredTasks,
    clearFilters,
  }
}
