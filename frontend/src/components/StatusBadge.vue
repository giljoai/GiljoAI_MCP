<template>
  <span
    class="status-badge"
    :style="badgeStyle"
    :aria-label="`Project status: ${statusLabel}`"
  >
    {{ statusLabel }}
  </span>
</template>

<script setup>
/**
 * StatusBadge — renders a project's lifecycle status as a tinted,
 * square-cornered (8px) pill.
 *
 * Single source of truth (BE-5039): label, color, and validity all
 * derive from `projectStatusesStore`, which mirrors the backend
 * `ProjectStatus` enum via `GET /api/v1/project-statuses/`. The store
 * is fetched once at app boot from `DefaultLayout.onMounted`; this
 * component never calls the API itself.
 *
 * Color/label resolution is shared with `TaskStatusBadge.vue` via
 * `useStatusBadgeMeta` (dup-7). No hex literals live in this file — the
 * Luminous Pastel palette in `design-tokens.scss` is the single source of
 * color truth.
 *
 * Design-system anatomy (`frontend/design-system-sample-v2.html`):
 * - `rgba(color, 0.15)` background with full-brightness color text
 * - `border-radius: 8px` (square-cornered pill)
 * - No CSS `border` — uses the global tinted-badge style
 */
import { computed, toRef } from 'vue'

import { hexToRgba } from '@/utils/colorUtils'
import { useProjectStatusesStore } from '@/stores/projectStatusesStore'
import { useStatusBadgeMeta } from '@/composables/useStatusBadgeMeta'

const props = defineProps({
  status: {
    type: String,
    required: true,
  },
})

const statusesStore = useProjectStatusesStore()

const { meta, statusLabel, colorHex } = useStatusBadgeMeta(
  toRef(props, 'status'),
  statusesStore,
)

const badgeStyle = computed(() => ({
  background: hexToRgba(colorHex.value, 0.15),
  color: colorHex.value,
  borderRadius: '8px',
}))

// Exposed for tests that need to assert internal computed state.
defineExpose({ statusLabel, meta, colorHex })
</script>

<style lang="scss" scoped>
@use '../styles/design-tokens' as *;
.status-badge {
  display: inline-flex;
  align-items: center;
  // Square-cornered pill per design-system-sample-v2.html (tinted badge).
  // No CSS `border` — tinted background carries the visual weight.
  border-radius: 8px;
  font-size: 0.68rem;
  font-weight: 600;
  padding: 3px 10px;
  white-space: nowrap;
  line-height: 1.4;
  user-select: none;
}
</style>
