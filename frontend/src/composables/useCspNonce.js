/**
 * SEC-0021: CSP nonce pickup for Vuetify runtime style injection.
 *
 * The SaaS backend's CspNonceMiddleware (api/saas_middleware/csp_nonce.py)
 * generates a per-request base64 nonce, sets the response CSP header
 * `style-src 'self' 'nonce-<X>'` (no `'unsafe-inline'`), and injects
 * `<meta name="csp-nonce" content="<X>">` into index.html before
 * `<div id="app">`.
 *
 * Vuetify 3 honors `app.config.globalProperties.$nonce` and stamps every
 * dynamically-injected `<style>` tag with `nonce="<value>"`. Without this
 * wiring, Vuetify-injected styles are blocked under nonce-only CSP and the
 * SPA renders unstyled.
 *
 * In CE mode the backend never injects the meta tag, so `readCspNonce()`
 * returns '' and `applyNonceToApp()` is a silent no-op (CE keeps
 * `'unsafe-inline'` per analyzer §1.4).
 *
 * Edition Scope: Both. The wiring lives in shared frontend code and is a
 * no-op when the backend doesn't emit a nonce.
 */

const META_NAME = 'csp-nonce'

/**
 * Read the CSP nonce from `<meta name="csp-nonce">`. Returns '' when the
 * meta tag is absent (CE mode) or empty.
 */
export function readCspNonce() {
  try {
    const meta = document.querySelector(`meta[name="${META_NAME}"]`)
    if (!meta) return ''
    return meta.getAttribute('content') || ''
  } catch {
    return ''
  }
}

/**
 * Assign the nonce to `app.config.globalProperties.$nonce` so Vuetify's
 * style injector picks it up. Also mirrors onto `window.__CSP_NONCE__` for
 * any future ad-hoc style injectors that need to inherit it.
 *
 * Defensive: never throws — a missing meta tag, a bare `app` shape, or a
 * null app argument all result in a no-op. This keeps the boot path safe
 * for CE and for unit tests that pass partial app fakes.
 */
export function applyNonceToApp(app) {
  const nonce = readCspNonce()

  try {
    if (typeof window !== 'undefined') {
      window.__CSP_NONCE__ = nonce
    }
  } catch {
    /* ignore — non-browser env */
  }

  if (!app || !app.config) return
  if (!app.config.globalProperties) return
  app.config.globalProperties.$nonce = nonce
}
