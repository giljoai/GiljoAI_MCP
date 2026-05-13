/**
 * useTaskFilters Composable
 *
 * Encapsulates search and dropdown filter state for the task list.
 * Accepts a reactive tasks array and returns filter refs, a filteredTasks
 * computed, and a clearFilters helper.
 *
 * Mirrors `useProjectFilters.js` (the project-side spec) — same search +
 * status + type pattern, adapted for task fields.
 *
 * @param {import('vue').Ref<Array>} tasks - Raw task array (ref or computed)
 * @param {object} [opts]
 * @param {import('vue').Ref<Array>} [opts.taxonomyTypes] - Available taxonomy
 *        types (ref of `[{id, abbreviation, label}]`) used to populate the
 *        type filter dropdown. Optional — when not provided, `typeSelectOptions`
 *        contains only the "No Type" pseudo-option.
 *
 * Note: tasks expose taxonomy via the `task_type` abbreviation (e.g. "BE")
 *   and `task_type_id` FK side-by-side. The filter compares `task_type_id`
 *   so it stays correct even if a type is renamed mid-session.
 */
import { ref, computed } from 'vue'

// Canonical five task statuses (backend `TaskUpdate` schema). Order matches
// declaration order in `api/schemas/task.py`. Once tasks gain a /
// `/api/v1/task-statuses/` SSOT (parity with BE-5039 for projects), this
// list should be replaced by a store-driven one and this hardcoded copy
// removed.
const TASK_STATUS_OPTIONS = [
  { title: 'Pending', value: 'pending' },
  { title: 'In Progress', value: 'in_progress' },
  { title: 'Completed', value: 'completed' },
  { title: 'Blocked', value: 'blocked' },
  { title: 'Cancelled', value: 'cancelled' },
]

export function useTaskFilters(tasks, { taxonomyTypes = ref([]) } = {}) {
  const search = ref('')
  const statusFilter = ref(null)
  const priorityFilter = ref(null)
  const taskTypeFilter = ref(null)
  // Legacy alias retained while the rest of TasksView migrates from
  // `categoryFilter`. Kept null and never read internally — included only
  // so existing callers that destructure `categoryFilter` don't break.
  const categoryFilter = ref(null)

  /**
   * Status filter dropdown items. Constant for now — see TASK_STATUS_OPTIONS
   * comment above for the future SSOT migration path.
   */
  const statusSelectOptions = computed(() => TASK_STATUS_OPTIONS.slice())

  /**
   * Type filter dropdown items derived from the injected taxonomy_types ref.
   * Mirrors `useProjectFilters.typeSelectOptions` — adds a 'No Type' option
   * for tasks whose `task_type_id` is NULL (post-migration backfill leaves
   * some tasks untagged).
   */
  const typeSelectOptions = computed(() => {
    const items = (taxonomyTypes.value || []).map((t) => ({
      title: t.abbreviation,
      value: t.id,
    }))
    items.push({ title: 'No Type', value: 'none' })
    return items
  })

  const filteredTasks = computed(() => {
    let list = tasks.value

    if (search.value) {
      const term = search.value.toLowerCase()
      list = list.filter(
        (t) =>
          t.title?.toLowerCase().includes(term) ||
          t.description?.toLowerCase().includes(term) ||
          t.taxonomy_alias?.toLowerCase().includes(term),
      )
    }

    if (statusFilter.value) {
      list = list.filter((t) => t.status === statusFilter.value)
    }

    if (priorityFilter.value) {
      list = list.filter((t) => t.priority === priorityFilter.value)
    }

    if (taskTypeFilter.value) {
      if (taskTypeFilter.value === 'none') {
        list = list.filter((t) => !t.task_type_id)
      } else {
        list = list.filter((t) => t.task_type_id === taskTypeFilter.value)
      }
    }

    return list
  })

  function clearFilters() {
    search.value = ''
    statusFilter.value = null
    priorityFilter.value = null
    taskTypeFilter.value = null
    categoryFilter.value = null
  }

  return {
    search,
    statusFilter,
    priorityFilter,
    taskTypeFilter,
    categoryFilter,
    statusSelectOptions,
    typeSelectOptions,
    filteredTasks,
    clearFilters,
  }
}
