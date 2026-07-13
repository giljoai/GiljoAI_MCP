import { computed } from 'vue'

// Fallback hex used when the store hasn't loaded yet (first-paint window
// before DefaultLayout's onMounted resolves) or when an unknown status
// value slips through (orphan WebSocket payload during a deploy).
// intentional fallback — not a hardcoded-color violation: resolveColorToken()
// feeds hexToRgba() directly and requires a real hex string; var() would
// break the computation.
const FALLBACK_HEX = '#9e9e9e'

function formatFallbackLabel(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : 'Unknown'
}

/**
 * Resolve a SCSS color token name (e.g. `color-status-complete`) to its hex
 * value via the corresponding CSS custom property (e.g.
 * `--color-status-complete`) declared at `:root` in `main.scss`, which
 * mirrors the SCSS token in `design-tokens.scss`.
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

/**
 * Shared status-badge metadata resolution for StatusBadge.vue and
 * TaskStatusBadge.vue (dup-7). `statusRef` is a ref/computed wrapping the
 * `status` prop; `store` is the Pinia statuses store (project or task) —
 * both expose a `getMeta(status)` lookup mirroring the backend status enum.
 */
export function useStatusBadgeMeta(statusRef, store) {
  const meta = computed(() => store.getMeta(statusRef.value))

  const statusLabel = computed(() =>
    meta.value ? meta.value.label : formatFallbackLabel(statusRef.value),
  )

  const colorHex = computed(() =>
    meta.value ? resolveColorToken(meta.value.color_token) : FALLBACK_HEX,
  )

  return { meta, statusLabel, colorHex }
}
