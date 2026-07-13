<template>
  <span
    class="task-status-badge smooth-border"
    :style="badgeStyle"
    :aria-label="`Task status: ${statusLabel}`"
  >
    {{ statusLabel }}
  </span>
</template>

<script setup>
/**
 * TaskStatusBadge — renders a task's lifecycle status as a tinted,
 * square-cornered (8px) pill.
 *
 * Single source of truth (FE-5041 Phase 2): label, color, and validity
 * all derive from `taskStatusesStore`, which mirrors the backend
 * `TaskStatus` enum via `GET /api/v1/task-statuses/`. The store is
 * fetched once at app boot from `DefaultLayout.onMounted`; this
 * component never calls the API itself.
 *
 * Color/label resolution is shared with `StatusBadge.vue` (the
 * project-side equivalent) via `useStatusBadgeMeta` (dup-7); the
 * remaining differences are (a) the store dependency, (b) the
 * `aria-label` prefix ("Task status:" vs "Project status:"), and
 * (c) the `smooth-border` class with a tinted `--smooth-border-color`
 * for inset border styling on the rounded element.
 *
 * Design-system anatomy (`frontend/design-system-sample-v2.html`):
 * - `rgba(color, 0.15)` background with full-brightness color text
 * - `border-radius: 8px` (square-cornered pill)
 * - `smooth-border` (inset box-shadow) — never CSS `border` on rounded
 */
import { computed, toRef } from 'vue'

import { hexToRgba } from '@/utils/colorUtils'
import { useTaskStatusesStore } from '@/stores/taskStatusesStore'
import { useStatusBadgeMeta } from '@/composables/useStatusBadgeMeta'

const props = defineProps({
  status: {
    type: String,
    required: true,
  },
})

const statusesStore = useTaskStatusesStore()

const { meta, statusLabel, colorHex } = useStatusBadgeMeta(
  toRef(props, 'status'),
  statusesStore,
)

const badgeStyle = computed(() => ({
  background: hexToRgba(colorHex.value, 0.15),
  color: colorHex.value,
  borderRadius: '8px',
  '--smooth-border-color': hexToRgba(colorHex.value, 0.35),
}))

// Exposed for tests that need to assert internal computed state.
defineExpose({ statusLabel, meta, colorHex })
</script>

<style lang="scss" scoped>
.task-status-badge {
  display: inline-flex;
  align-items: center;
  // Square-cornered pill per design-system-sample-v2.html (tinted badge).
  // `smooth-border` from main.scss carries the inset border (no CSS `border`
  // on a rounded element).
  border-radius: 8px;
  font-size: 0.68rem;
  font-weight: 600;
  padding: 3px 10px;
  white-space: nowrap;
  line-height: 1.4;
  user-select: none;
}
</style>
