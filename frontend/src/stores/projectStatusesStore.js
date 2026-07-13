/**
 * projectStatusesStore — single source of project-status metadata for the
 * frontend (BE-5039 Phase 4).
 *
 * The canonical six project statuses (inactive, active, completed,
 * cancelled, terminated, deleted) are declared once in the backend
 * `ProjectStatus` enum. The frontend mirrors them by fetching
 * `GET /api/v1/project-statuses/` exactly once per session and caching
 * the response in this Pinia store.
 *
 * Consumers (StatusBadge.vue, useProjectFilters.js, the contract test)
 * read `validValues`, `getMeta(value)`, or `isValid(value)` instead of
 * embedding their own list of statuses. This eliminates the drift
 * surface a frontend-side hardcoded validator used to introduce.
 *
 * Built on `createStatusesStore` (dup-8), shared with `taskStatusesStore.js`.
 *
 * Edition isolation: CE-foundational. SaaS reuses this store as-is.
 */
import api from '@/services/api'

import { createStatusesStore } from './createStatusesStore'

export const useProjectStatusesStore = createStatusesStore(
  'projectStatuses',
  () => api.projectStatuses.list(),
)
