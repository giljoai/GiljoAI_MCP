import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { pinia } from './stores'
import { initializeApiConfig } from './config/api'
import configService from './services/configService'
import setupService from './services/setupService'
import { initSentry } from './sentry'
import { applyNonceToApp, readCspNonce } from '@/composables/useCspNonce'
import { maybeReloadForChunkError } from '@/utils/chunkReload'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import '@mdi/font/css/materialdesignicons.css'

// Custom Directives
import { draggable } from './directives/draggable'

// Global Styles
import '@/styles/main.scss'
import '@/styles/global-tabs.scss'

// Theme configuration
import { darkTheme } from './config/theme'

// SEC-0021: Read the per-request CSP nonce from <meta name="csp-nonce"> BEFORE
// createVuetify(). Vuetify 3 only stamps its runtime-injected <style> tags with
// the nonce when it's passed as `theme.cspNonce` in the create options — it does
// NOT read `app.config.globalProperties.$nonce`. Under nonce-only style-src in
// SaaS/demo, missing this wiring blocks every Vuetify theme stylesheet and the
// SPA renders unstyled (brand yellow, theme vars all gone). CE has no meta tag,
// readCspNonce() returns '', cspNonce becomes undefined, behavior unchanged.
const cspNonce = readCspNonce() || undefined

// Create Vuetify instance with theme
const vuetify = createVuetify({
  theme: {
    defaultTheme: 'dark',
    cspNonce,
    themes: {
      dark: darkTheme,
    },
  },
  icons: {
    defaultSet: 'mdi',
  },
  display: {
    mobileBreakpoint: 'md', // Vuetify 4: md = 840px (was 960px in v3). Sidebar SIDEBAR_BREAKPOINT stays 1024px (DefaultLayout.vue). Accepting v4's default thresholds; revisit here if a numeric mobileBreakpoint is wanted.
  },
  // Native browser spellcheck on prose inputs. Without explicit autocorrect/
  // autocapitalize, Safari sometimes drops the right-click suggestion menu.
  // Code/prompt editors that need to opt out set spellcheck="false" locally
  // (e.g. SystemPromptTab.vue).
  defaults: {
    VTextField: {
      spellcheck: 'true',
      autocorrect: 'on',
      autocapitalize: 'sentences',
    },
    VTextarea: {
      spellcheck: 'true',
      autocorrect: 'on',
      autocapitalize: 'sentences',
    },
  },
})

// FE-6120: recover from a stale lazy-chunk after a deploy. Vite fires
// `vite:preloadError` on the window when a dynamically-imported chunk (or its
// preloaded CSS) fails to load — typically because this tab is running an older
// build and the hashed chunk filename no longer exists on the server. We cancel
// Vite's default rethrow and trigger a one-time guarded reload (sentinel-guarded
// in chunkReload.js) so the browser pulls the fresh index.html + new chunk
// hashes. Registered before mount so an early lazy import is covered.
window.addEventListener('vite:preloadError', (event) => {
  event.preventDefault()
  maybeReloadForChunkError()
})

// Create Vue app SYNCHRONOUSLY (before async operations)
const app = createApp(App)

// pinia + vuetify can install before bootstrap (no navigation side-effects).
// Router install is DEFERRED into bootstrap() so SaaS routes can be added
// BEFORE Vue Router resolves the initial location. Vue Router 4's docs:
// "Adding a new route to a router that is already navigating will have no
// effect on the current navigation." If we app.use(router) here, the initial
// navigation to e.g. /welcome begins resolving immediately and any addRoute
// in bootstrap fires too late — the new SaaS routes aren't in the matcher
// when the beforeEach guard redirects to /landing, so the redirect
// falls into the NotFound catch-all and bounces to /login. Discovered
// 2026-04-21 demo go-live.
// SEC-0021: Pick up the per-request CSP nonce injected by the SaaS backend
// into <meta name="csp-nonce"> and assign it to app.config.globalProperties.$nonce
// BEFORE app.use(vuetify), so Vuetify's first runtime-injected <style> tag
// carries the nonce attribute and is not blocked under nonce-only style-src.
// CE mode (no meta tag) is a silent no-op; CE keeps 'unsafe-inline'.
applyNonceToApp(app)

app.use(pinia)
app.use(vuetify)

// Register custom directives
app.directive('draggable', draggable)

// Always use dark theme
localStorage.setItem('theme-preference', 'dark')
vuetify.theme.change('dark')
document.documentElement.setAttribute('data-theme', 'dark')

// Initialize API config BEFORE mounting to ensure correct baseURL for auth check.
// The router guard fires on mount and calls /api/auth/me -- baseURL must be resolved first.
async function bootstrap() {
  try {
    await initializeApiConfig()
  } catch (error) {
    console.warn('[MAIN] Failed to initialize API config, using fallback:', error)
  }

  // INF-5063: initialize Sentry BEFORE app.mount() so it can attach the Vue
  // error handler before any component renders. Gated on a non-null DSN from
  // the backend setup-status response — CE returns null and skips entirely
  // (no @sentry/vue load, no network calls). Errors here must never block
  // bootstrap.
  try {
    const status = await setupService.checkEnhancedStatus()
    if (status?.sentryDsn) {
      await initSentry(app, {
        dsn: status.sentryDsn,
        environment: status.environment || status.mode || 'unknown',
        tenantKey: null, // tag refreshed post-login from user store
      })
    }
  } catch (error) {
    console.warn('[MAIN] Sentry init skipped:', error)
  }

  // Register edition-specific routes BEFORE mount.
  //
  // The router.beforeEach guard fires synchronously on the initial navigation
  // triggered by app.mount(). For saas mode that guard may redirect to
  // SaaS-only routes like /landing. The routes must already exist when
  // the guard fires, so registration happens here, not after mount.
  //
  // CE-export safety via import.meta.glob:
  //   - In private/SaaS builds, Vite finds @/saas/routes/index.js and bundles
  //     it (plus its transitive Vue component imports) into a lazy chunk.
  //   - In CE builds, the export pipeline removes the saas/ directory before
  //     `npm run build` runs. Vite's static glob scan finds zero matches and
  //     the loader map is empty — registration silently no-ops, no errors.
  //
  // This replaces an earlier @vite-ignore + runtime-URL-fetch pattern that
  // looked safe in dev (Vite dev server serves source files) but broke in
  // production builds, where the SPA fallback returned index.html for the
  // missing path with Content-Type: text/html, which the browser refuses to
  // execute as a JS module. The result was that SaaS routes never registered
  // and /landing fell through to /login. Discovered live 2026-04-21.
  // Pick the loader by value, not by key — Vite's glob result key format
  // varies by config (could be '/src/saas/...' or '@/saas/...'). Iterating
  // values is robust. Pattern matches at most one file (a literal path).
  const saasRouteLoaders = import.meta.glob('@/saas/routes/index.js')
  const [saasRoutesLoader] = Object.values(saasRouteLoaders)
  if (saasRoutesLoader && configService.getGiljoMode() !== 'ce') {
    try {
      const saasRoutes = await saasRoutesLoader()
      saasRoutes.registerSaasRoutes()
    } catch (error) {
      console.warn('[MAIN] SaaS routes failed to register:', error)
    }
  }

  // Install the router AFTER all routes (CE static + SaaS dynamic) are
  // registered. This is what makes the initial navigation resolve against
  // the complete route table — including /landing — instead of
  // triggering navigation against a partial table and then having addRoute
  // be a no-op for the in-flight nav.
  app.use(router)

  app.mount('#app')
}

bootstrap()
