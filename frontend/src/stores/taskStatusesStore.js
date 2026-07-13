/**
 * taskStatusesStore — single source of task-status metadata for the
 * frontend (FE-5041 Phase 2).
 *
 * The canonical five task statuses (pending, in_progress, completed,
 * blocked, cancelled) are declared once in the backend
 * `TaskStatus` enum. The frontend mirrors them by fetching
 * `GET /api/v1/task-statuses/` exactly once per session and caching
 * the response in this Pinia store.
 *
 * Consumers (TaskStatusBadge.vue) read `validValues`, `getMeta(value)`,
 * or `isValid(value)` instead of embedding their own status list. This
 * eliminates the drift surface a frontend-side hardcoded validator used
 * to introduce.
 *
 * Built on `createStatusesStore` (dup-8), shared with `projectStatusesStore.js`.
 *
 * Edition isolation: CE-foundational. SaaS reuses this store as-is.
 */
import api from '@/services/api'

import { createStatusesStore } from './createStatusesStore'

export const useTaskStatusesStore = createStatusesStore(
  'taskStatuses',
  () => api.taskStatuses.list(),
)
