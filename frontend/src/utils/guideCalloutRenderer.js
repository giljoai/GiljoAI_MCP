/**
 * Guide callout renderer for marked.
 *
 * Implements GitHub-style alert blockquotes:
 *   > [!CE]
 *   > Self-hosted only.
 *
 *   > [!SAAS]
 *   > Hosted-only feature.
 *
 * A blockquote whose first child paragraph is exactly `[!CE]` or `[!SAAS]`
 * is transformed into a typed callout element:
 *   <blockquote class="guide-callout guide-callout--ce">
 *     <span class="guide-callout__label">Community Edition only</span>
 *     ...body...
 *   </blockquote>
 *
 * SEC-0003 posture:
 *  - `body` is the already-rendered HTML output from marked for the
 *    blockquote's inner tokens — all text nodes have been HTML-escaped by
 *    marked's own paragraph/text renderers.
 *  - Label text is a compile-time constant (not user data).
 *  - DOMPurify sanitizeHtml is applied downstream by all call sites.
 *  - The DOMPurify hook in useSanitizeMarkdown restricts class on blockquote
 *    to the known callout values only (GUIDE_CALLOUT_CLASSES).
 *
 * Usage: call installGuideCalloutRenderer(marked) once per marked instance.
 */

/**
 * Compile-time label map — not user data.
 * Exported for test assertions (tests/unit/views/UserGuideView.edition.spec.js).
 */
// eslint-disable-next-line giljo-internal/no-orphaned-exports -- consumed by tests/
export const CALLOUT_LABELS = Object.freeze({
  CE: 'Community Edition only',
  SAAS: 'Hosted (SaaS) only',
})

/**
 * Install the callout blockquote renderer on the given `marked` instance via
 * `marked.use()`. Idempotent: subsequent calls for the same instance add an
 * additional renderer layer but the callout detection regex is deterministic
 * so the output is the same.
 *
 * Detection strategy: inspect the first paragraph TOKEN's text before rendering.
 * Marked merges `> [!CE]\n> content` into a single paragraph token (text starts
 * with `[!CE]\n`). We detect the marker in the token text, then strip it before
 * rendering the body so the output contains only the callout body — not the tag.
 *
 * Two formats are handled:
 *   Format A (single paragraph, no blank line):
 *     > [!CE]
 *     > Body text.
 *     → single paragraph token with text "[!CE]\nBody text."
 *
 *   Format B (separate paragraphs, blank line between):
 *     > [!CE]
 *     >
 *     > Body text.
 *     → first paragraph token text is exactly "[!CE]"; body is a separate token.
 *
 * @param {import('marked').Marked} markedInstance
 */
export function installGuideCalloutRenderer(markedInstance) {
  markedInstance.use({
    renderer: {
      heading({ text, depth }) {
        const safeText = _escapeHtml(text)
        if (depth === 2) {
          const anchor = _slugify(text)
          return `<h2 id="${anchor}">${safeText}</h2>\n`
        }
        return `<h${depth}>${safeText}</h${depth}>\n`
      },

      // Detect `[!CE]` / `[!SAAS]` alert markers in blockquotes.
      // We inspect the token tree before rendering to handle both markdown formats.
      blockquote({ tokens }) {
        // Find the first non-space token — it should be a paragraph.
        const firstToken = tokens.find((t) => t.type !== 'space')

        if (!firstToken || firstToken.type !== 'paragraph') {
          // No paragraph at start — not a callout. Render normally.
          const body = markedInstance.parser(tokens, { renderer: this })
          return `<blockquote>${body}</blockquote>\n`
        }

        // Check if the paragraph text starts with `[!CE]` or `[!SAAS]`.
        // The text may be exactly "[!CE]" (Format B) or "[!CE]\nContent" (Format A).
        const markerMatch = firstToken.text.match(/^\[!(CE|SAAS)\](\n|$)/i)
        if (!markerMatch) {
          const body = markedInstance.parser(tokens, { renderer: this })
          return `<blockquote>${body}</blockquote>\n`
        }

        const kind = markerMatch[1].toUpperCase()
        const label = CALLOUT_LABELS[kind]

        // Build the body token list: strip the marker line from the first paragraph.
        const restText = firstToken.text.slice(markerMatch[0].length).trimStart()
        let bodyTokens

        if (restText) {
          // Format A: remaining text after the marker in the same paragraph.
          // Replace the first token with a stripped version preserving the rest.
          const stripped = {
            ...firstToken,
            text: restText,
            raw: restText,
            tokens: [{ type: 'text', raw: restText, text: restText }],
          }
          bodyTokens = [stripped, ...tokens.slice(tokens.indexOf(firstToken) + 1)]
        } else {
          // Format B: marker was the entire first paragraph; remaining tokens are body.
          const firstIdx = tokens.indexOf(firstToken)
          bodyTokens = tokens.slice(firstIdx + 1).filter((t) => t.type !== 'space' || tokens.indexOf(t) > firstIdx + 1)
        }

        const innerBody = markedInstance.parser(bodyTokens, { renderer: this })
        // label is a compile-time constant — safe to interpolate directly.
        const cls = kind.toLowerCase()
        return `<blockquote class="guide-callout guide-callout--${cls}"><span class="guide-callout__label">${label}</span>${innerBody}</blockquote>\n`
      },
    },
  })
}

// ─── Local copies of escapeHtml / slugify ────────────────────────────────────
// Duplicated here to avoid a circular dependency (escapeHtml.js → (no deps)
// but this module is loaded before @/utils/escapeHtml in some test contexts).
// If escapeHtml.js changes, update these too.

const _HTML_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }
const _HTML_ESCAPE_RE = /[&<>"']/g

function _escapeHtml(value) {
  if (value === null || value === undefined) return ''
  return String(value).replace(_HTML_ESCAPE_RE, (ch) => _HTML_ESCAPES[ch])
}

function _slugify(text) {
  return String(text ?? '')
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}
