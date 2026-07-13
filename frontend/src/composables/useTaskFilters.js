/**
 * useTaskFilters Composable
 *
 * Encapsulates search and dropdown filter state for the task list.
 * Accepts a reactive tasks array and returns filter refs, a filteredTasks
 * computed, and a clearFilters helper.
 *
 * Mirrors `useProjectFilters.js` (the project-side spec) — same search +
 * status pattern, adapted for task fields.
 *
 * FE-6049e: tasks are auto-TSK (BE-6049c), so there is no task-type filter —
 * every task carries the one reserved tag and filtering by it is meaningless.
 *
 * @param {import('vue').Ref<Array>} tasks - Raw task array (ref or computed)
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

export function useTaskFilters(tasks) {
  const search = ref('')
  const statusFilter = ref(null)
  const priorityFilter = ref(null)
  // BE-2002: "Show archived" view toggle (mirrors the projects action-bar badge).
  // Off by default so the default list excludes archived (hidden) tasks; flipping
  // it reveals them without needing a search term. NOTE: "archived" is the
  // user-facing name; the backing field on the task is `hidden` (backend name
  // unchanged — see useTaskFilters / TasksView).
  const showHidden = ref(false)

  // Count of archived (hidden) tasks in the current product-scoped list — drives
  // the "Show archived (N)" badge count.
  const hiddenCount = computed(() => (tasks.value || []).filter((t) => t.hidden).length)

  /**
   * Status filter dropdown items. Constant for now — see TASK_STATUS_OPTIONS
   * comment above for the future SSOT migration path.
   */
  const statusSelectOptions = computed(() => TASK_STATUS_OPTIONS.slice())

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

    // IMP-5038 / BE-2002: Archived (hidden) exclusion is independent of other
    // filters. An active search is "nuclear" and reveals archived rows so users
    // can find what they archived; the "Show archived" toggle (showHidden) also
    // reveals them in the default view. TasksView has no 'Hidden' pseudo-status,
    // so there is no status-filter override here (unlike the projects side).
    if (!search.value && !showHidden.value) {
      list = list.filter((t) => !t.hidden)
    }

    return list
  })

  function clearFilters() {
    search.value = ''
    statusFilter.value = null
    priorityFilter.value = null
  }

  return {
    search,
    statusFilter,
    priorityFilter,
    showHidden,
    hiddenCount,
    statusSelectOptions,
    filteredTasks,
    clearFilters,
  }
}
