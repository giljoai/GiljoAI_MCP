/**
 * HTML escape helper (SEC-0003).
 *
 * Escapes the five characters that DOMPurify treats as tokens when they appear
 * in what is supposed to be text. Used when we have untrusted strings that will
 * be concatenated INTO an HTML string before sanitization -- without escaping
 * here, attacker-supplied `<` would be parsed by DOMPurify as a real tag
 * (double-decode class vulnerability).
 *
 * If you already have a DOM node and can use `textContent`, prefer that. Only
 * reach for this helper when you must build HTML as a string.
 */
const HTML_ESCAPES = Object.freeze({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
})

const HTML_ESCAPE_RE = /[&<>"']/g

export function escapeHtml(value) {
  if (value === null || value === undefined) return ''
  return String(value).replace(HTML_ESCAPE_RE, (ch) => HTML_ESCAPES[ch])
}

/**
 * URL-slug generator: lowercases, strips everything outside [a-z0-9-],
 * collapses runs of `-`. Safe to interpolate into an HTML id attribute
 * because the output is restricted to that character class.
 */
export function slugify(text) {
  return String(text ?? '')
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}
