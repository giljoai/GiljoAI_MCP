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
 * Color resolution: each status carries a `color_token` string (e.g.
 * `color-status-complete`). At render time we read the matching CSS
 * custom property (`--color-status-complete`) declared in `main.scss`,
 * which mirrors the SCSS token in `design-tokens.scss`. No hex literals
 * live in this file — the Luminous Pastel palette in `design-tokens.scss`
 * is the single source of color truth.
 *
 * Design-system anatomy (`frontend/design-system-sample-v2.html`):
 * - `rgba(color, 0.15)` background with full-brightness color text
 * - `border-radius: 8px` (square-cornered pill)
 * - No CSS `border` — uses the global tinted-badge style
 */
import { computed } from 'vue'

import { hexToRgba } from '@/utils/colorUtils'
import { useProjectStatusesStore } from '@/stores/projectStatusesStore'

const props = defineProps({
  status: {
    type: String,
    required: true,
  },
})

const statusesStore = useProjectStatusesStore()

// Fallback hex used when the store hasn't loaded yet (first-paint window
// before DefaultLayout's onMounted resolves) or when an unknown status
// value slips through (orphan WebSocket payload during a deploy). This
// matches `--color-text-muted` in `main.scss` so the visual fallback is
// the same as the canonical INACTIVE state.
const FALLBACK_HEX = '#9e9e9e'
const FALLBACK_LABEL_FORMATTER = (value) =>
  value ? value.charAt(0).toUpperCase() + value.slice(1) : 'Unknown'

const meta = computed(() => statusesStore.getMeta(props.status))

const statusLabel = computed(() =>
  meta.value ? meta.value.label : FALLBACK_LABEL_FORMATTER(props.status),
)

/**
 * Resolve a SCSS color token name (e.g. `color-status-complete`) to its
 * hex value via the corresponding CSS custom property `--color-status-complete`
 * declared at `:root` in `main.scss`.
 *
 * Falls back to the muted hex when the property is missing (jsdom test
 * environment, SSR, or before stylesheets have applied).
 */
function resolveColorToken(token) {
  if (!token) return FALLBACK_HEX
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return FALLBACK_HEX
  }
  try {
    const value = getComputedStyle(document.documentElement)
      .getPropertyValue(`--${token}`)
      .trim()
    if (!value) return FALLBACK_HEX
    return value
  } catch {
    return FALLBACK_HEX
  }
}

const colorHex = computed(() =>
  meta.value ? resolveColorToken(meta.value.color_token) : FALLBACK_HEX,
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
