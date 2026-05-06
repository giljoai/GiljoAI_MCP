<template>
  <span
    class="task-status-badge smooth-border"
    :style="badgeStyle"
    :aria-label="`Task status: ${label}`"
  >
    {{ label }}
  </span>
</template>

<script setup>
/**
 * TaskStatusBadge — renders a task's lifecycle status as a tinted,
 * square-cornered (8px) pill.
 *
 * Mirrors the project-side StatusBadge.vue pattern verbatim
 * (`smooth-border` + `rgba(color, 0.15)` background + full-brightness
 * color text + `border-radius: 8px`), but uses a local mapping for the
 * six canonical task statuses defined in the backend `TaskUpdate` schema:
 *   pending, in_progress, completed, blocked, cancelled, converted.
 *
 * Tasks do not (yet) expose a /api/v1/task-statuses/ SSOT endpoint the
 * way projects do (BE-5039). Once that lands, this component should be
 * collapsed onto a shared store-driven implementation.
 *
 * Color choices (Luminous Pastels palette, all WCAG AA on `#12202e`):
 *   - pending     -> --color-text-muted (neutral, 4.98:1)
 *   - in_progress -> --color-agent-implementer (#6DB3E4, 6.64:1)
 *   - completed   -> #5EC48E (mint, 7.03:1)
 *   - blocked     -> #E07872 (coral, 5.11:1)
 *   - cancelled   -> --color-text-muted (intentional same as pending —
 *                     terminal/inert state)
 *   - converted   -> #AC80CC (lavender, 4.84:1)
 */
import { computed } from 'vue'

import { hexToRgba } from '@/utils/colorUtils'

const props = defineProps({
  status: {
    type: String,
    required: true,
  },
})

// Hex literals are intentional here: tasks don't yet have a backend SSOT
// for status metadata, and these match the Luminous Pastel tokens in
// `design-tokens.scss` (kept in lockstep with `--color-agent-*` /
// `--color-status-*` custom properties).
const STATUS_META = {
  pending: { label: 'Pending', hex: '#9e9e9e' },
  in_progress: { label: 'In Progress', hex: '#6db3e4' },
  completed: { label: 'Completed', hex: '#5ec48e' },
  blocked: { label: 'Blocked', hex: '#e07872' },
  cancelled: { label: 'Cancelled', hex: '#8895a8' },
  converted: { label: 'Converted', hex: '#ac80cc' },
}

const FALLBACK = { label: 'Unknown', hex: '#9e9e9e' }

const meta = computed(() => STATUS_META[props.status] || FALLBACK)

const label = computed(() => meta.value.label)

const badgeStyle = computed(() => ({
  background: hexToRgba(meta.value.hex, 0.15),
  color: meta.value.hex,
  borderRadius: '8px',
  '--smooth-border-color': hexToRgba(meta.value.hex, 0.35),
}))

defineExpose({ label, meta })
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
