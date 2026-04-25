import DOMPurify from 'dompurify'
import { marked } from 'marked'

/**
 * SEC-0003 -- single sanctioned entry point for v-html content.
 *
 * HARDENED_CONFIG is stricter than DOMPurify's default `USE_PROFILES.html`:
 *  - ALLOWED_TAGS is an explicit allow-list (no SVG, no math, no form controls).
 *  - ALLOWED_ATTR is narrow (href/src/alt/target/rel/id/class only).
 *  - ALLOW_DATA_ATTR: false -- blocks `data-*` exfiltration sinks.
 *  - ALLOWED_URI_REGEXP restricts schemes to http(s), mailto, and relative.
 *    Explicitly blocks `javascript:` and `data:` schemes on any attribute.
 *  - FORBID_ATTR adds belt-and-suspenders for common inline event handlers
 *    (DOMPurify already strips on* by default, but being explicit protects
 *    future-config-change from silently reintroducing them).
 *
 * Tag list was derived from the 3 markdown call sites (MessageItem,
 * BroadcastPanel, UserGuideView) -- basic text formatting, lists, headings,
 * code blocks, blockquotes, tables, images, and links. Extend deliberately
 * if a new call site needs more.
 */
const HARDENED_CONFIG = Object.freeze({
  ALLOWED_TAGS: [
    'a', 'b', 'i', 'em', 'strong', 'mark',
    'p', 'br', 'hr', 'div', 'span',
    'code', 'pre', 'blockquote',
    'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'img',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
  ],
  ALLOWED_ATTR: ['href', 'target', 'rel', 'src', 'alt', 'id', 'class'],
  ALLOW_DATA_ATTR: false,
  ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|[^a-z]|[a-z+.-]+(?:[^a-z+.:-]|$))/i,
  FORBID_ATTR: ['onerror', 'onclick', 'onload', 'onmouseover', 'onfocus', 'onblur'],
})

function buildConfig(overrides) {
  if (!overrides) return HARDENED_CONFIG
  // Shallow-merge: overrides replace top-level keys (e.g. extend ALLOWED_TAGS).
  return { ...HARDENED_CONFIG, ...overrides }
}

/**
 * Sanitize raw HTML (no markdown parsing). Use at call sites that already
 * hold HTML (e.g. DatabaseConnection.formatTestResultMessage).
 */
export function sanitizeHtml(html, overrides) {
  if (!html) return ''
  return DOMPurify.sanitize(html, buildConfig(overrides))
}

/**
 * Composable: parses markdown through `marked` then sanitizes with the
 * hardened DOMPurify config. Returns `{ sanitizeMarkdown }` so call sites
 * can destructure it the same way they do other composables.
 */
export function useSanitizeMarkdown() {
  function sanitizeMarkdown(content, overrides) {
    if (!content) return ''
    const html = marked(content)
    return DOMPurify.sanitize(html, buildConfig(overrides))
  }

  return { sanitizeMarkdown }
}
