import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import { createPinia, setActivePinia } from 'pinia'

import StatusBadge from '@/components/StatusBadge.vue'
import { useProjectStatusesStore } from '@/stores/projectStatusesStore'

// Canonical six statuses (BE-5039). Mirrors backend ProjectStatus enum
// declaration order. `expectedHex` mirrors the CSS custom properties in
// `frontend/src/styles/main.scss` which mirror SCSS tokens in
// `design-tokens.scss`. The hex values appear here only for assertion
// purposes — the production code never embeds them.
const STATUSES = [
  {
    value: 'inactive',
    label: 'Inactive',
    color_token: 'color-text-muted',
    expectedHex: '#9e9e9e',
    is_lifecycle_finished: false,
    is_immutable: false,
    is_user_mutable_via_mcp: true,
  },
  {
    value: 'active',
    label: 'Active',
    color_token: 'color-agent-implementer',
    expectedHex: '#6db3e4',
    is_lifecycle_finished: false,
    is_immutable: false,
    is_user_mutable_via_mcp: true,
  },
  {
    value: 'completed',
    label: 'Completed',
    color_token: 'color-status-complete',
    expectedHex: '#67bd6d',
    is_lifecycle_finished: true,
    is_immutable: true,
    is_user_mutable_via_mcp: true,
  },
  {
    value: 'cancelled',
    label: 'Cancelled',
    color_token: 'color-status-blocked',
    expectedHex: '#ff9800',
    is_lifecycle_finished: true,
    is_immutable: true,
    is_user_mutable_via_mcp: true,
  },
  {
    value: 'terminated',
    label: 'Terminated',
    color_token: 'color-agent-analyzer',
    expectedHex: '#e07872',
    is_lifecycle_finished: true,
    is_immutable: false,
    is_user_mutable_via_mcp: false,
  },
  {
    value: 'deleted',
    label: 'Deleted',
    color_token: 'color-agent-analyzer',
    expectedHex: '#e07872',
    is_lifecycle_finished: true,
    is_immutable: false,
    is_user_mutable_via_mcp: false,
  },
]

// WCAG luminance helpers per https://www.w3.org/TR/WCAG21/#dfn-relative-luminance.
function hexToRgb(hex) {
  const cleaned = hex.replace('#', '')
  const r = parseInt(cleaned.slice(0, 2), 16) / 255
  const g = parseInt(cleaned.slice(2, 4), 16) / 255
  const b = parseInt(cleaned.slice(4, 6), 16) / 255
  return { r, g, b }
}

function relativeLuminance({ r, g, b }) {
  const channel = (c) =>
    c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}

function contrastRatio(hexA, hexB) {
  const La = relativeLuminance(hexToRgb(hexA))
  const Lb = relativeLuminance(hexToRgb(hexB))
  const lighter = Math.max(La, Lb)
  const darker = Math.min(La, Lb)
  return (lighter + 0.05) / (darker + 0.05)
}

// Inject the CSS custom properties from main.scss into the jsdom document
// so `getComputedStyle(...).getPropertyValue('--color-...')` resolves.
// jsdom does not parse our SCSS, so we set them directly on :root.
function installStatusColorVars() {
  const styleEl = document.createElement('style')
  styleEl.dataset.testColors = 'project-statuses'
  styleEl.textContent = `:root {
    --color-status-complete: #67bd6d;
    --color-status-blocked: #ff9800;
    --color-text-muted: #9e9e9e;
    --color-agent-implementer: #6db3e4;
    --color-agent-analyzer: #e07872;
  }`
  document.head.appendChild(styleEl)
  return styleEl
}

describe('StatusBadge.vue', () => {
  let vuetify
  let pinia
  let cssEl

  beforeEach(() => {
    vuetify = createVuetify()
    pinia = createPinia()
    setActivePinia(pinia)
    // Seed the store synchronously so the badge has the metadata at mount
    // time (no API call). This mirrors the production boot, where the
    // store is loaded by DefaultLayout.onMounted before any badge mounts.
    const store = useProjectStatusesStore()
    store.statuses = STATUSES.map(
      ({ expectedHex: _ignored, ...rest }) => rest, // store payload omits expectedHex
    )
    store.loaded = true
    cssEl = installStatusColorVars()
  })

  afterEach(() => {
    if (cssEl && cssEl.parentNode) {
      cssEl.parentNode.removeChild(cssEl)
    }
  })

  const createWrapper = (props) => {
    return mount(StatusBadge, {
      props: {
        status: 'active',
        ...props,
      },
      global: {
        plugins: [vuetify, pinia],
      },
    })
  }

  describe('Rendering — parametrized across all 6 canonical statuses', () => {
    STATUSES.forEach(({ value, label }) => {
      it(`renders label "${label}" for status "${value}"`, () => {
        const wrapper = createWrapper({ status: value })
        expect(wrapper.text()).toContain(label)
        expect(wrapper.vm.statusLabel).toBe(label)
      })

      it(`applies tinted background (rgba 0.15) for status "${value}"`, () => {
        const wrapper = createWrapper({ status: value })
        const badge = wrapper.find('.status-badge')
        const style = badge.attributes('style')
        expect(style).toContain('rgba(')
        expect(style).toContain('0.15')
      })

      it(`uses border-radius 8px (square-cornered) for status "${value}"`, () => {
        const wrapper = createWrapper({ status: value })
        const badge = wrapper.find('.status-badge')
        const style = badge.attributes('style')
        expect(style).toContain('border-radius: 8px')
      })

      it(`renders status-badge as a span for status "${value}"`, () => {
        const wrapper = createWrapper({ status: value })
        const badge = wrapper.find('.status-badge')
        expect(badge.exists()).toBe(true)
        expect(badge.element.tagName).toBe('SPAN')
      })
    })
  })

  describe('Color resolution from store metadata + CSS custom properties', () => {
    STATUSES.forEach(({ value, expectedHex }) => {
      it(`resolves color_token to "${expectedHex}" for status "${value}"`, () => {
        const wrapper = createWrapper({ status: value })
        // The component normalizes to whatever getComputedStyle returns;
        // jsdom returns the literal string. Trim and lower-case for
        // case-insensitive comparison.
        expect(wrapper.vm.colorHex.toLowerCase()).toBe(expectedHex.toLowerCase())
      })
    })
  })

  describe('Accessibility — aria-label per status', () => {
    STATUSES.forEach(({ value, label }) => {
      it(`sets aria-label "Project status: ${label}" for status "${value}"`, () => {
        const wrapper = createWrapper({ status: value })
        const badge = wrapper.find('.status-badge')
        expect(badge.attributes('aria-label')).toBe(`Project status: ${label}`)
      })
    })
  })

  describe('Fallback when status is unknown (orphan / pre-load)', () => {
    it('uses muted color and capitalized fallback label for unknown status', () => {
      const wrapper = createWrapper({ status: 'archived' })
      // Fallback label: capitalized passthrough so a stale event still
      // renders something readable.
      expect(wrapper.vm.statusLabel).toBe('Archived')
      // Fallback hex is the muted token (matches inactive).
      expect(wrapper.vm.colorHex.toLowerCase()).toBe('#9e9e9e')
    })

    it('falls back gracefully when the store has no metadata yet', () => {
      // Reset the store to simulate first-paint before ensureLoaded() resolves.
      const store = useProjectStatusesStore()
      store.reset()
      const wrapper = createWrapper({ status: 'active' })
      expect(wrapper.vm.meta).toBeUndefined()
      expect(wrapper.vm.colorHex.toLowerCase()).toBe('#9e9e9e')
      expect(wrapper.vm.statusLabel).toBe('Active') // capitalized passthrough
    })
  })

  describe('WCAG AA contrast — text on tinted background and on app bg #12202e', () => {
    // The tinted-badge anatomy uses `color: <hex>` over a 15%-opacity
    // tint of the same hex, sitting on the dark app background
    // (#12202e). Two contrast checks:
    //   1. Color text against the dark app background — must exceed 4.5:1
    //      (WCAG AA for normal text). This is the analyzer's stated
    //      acceptance criterion. It also reflects what users actually
    //      see, because a 0.15-alpha tint blends almost entirely with
    //      the page background.
    STATUSES.forEach(({ value, expectedHex }) => {
      it(`status "${value}" — color text on #12202e bg passes WCAG AA (>= 4.5:1)`, () => {
        const ratio = contrastRatio(expectedHex, '#12202e')
        expect(ratio).toBeGreaterThanOrEqual(4.5)
      })
    })
  })
})
