import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { pinia } from './stores'
import { initializeApiConfig } from './config/api'
import configService from './services/configService'

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

// Create Vuetify instance with theme
const vuetify = createVuetify({
  theme: {
    defaultTheme: 'dark',
    themes: {
      dark: darkTheme,
    },
  },
  icons: {
    defaultSet: 'mdi',
  },
  display: {
    mobileBreakpoint: 'md', // 960px — aligns with sidebar SIDEBAR_BREAKPOINT (1024px)
  },
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
// when the beforeEach guard redirects to /demo-landing, so the redirect
// falls into the NotFound catch-all and bounces to /login. Discovered
// 2026-04-21 demo go-live.
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

  // Register edition-specific routes BEFORE mount.
  //
  // The router.beforeEach guard fires synchronously on the initial navigation
  // triggered by app.mount(). For demo/saas mode that guard may redirect to
  // SaaS-only routes like /demo-landing. The routes must already exist when
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
  // and /demo-landing fell through to /login. Discovered live 2026-04-21.
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
  // the complete route table — including /demo-landing — instead of
  // triggering navigation against a partial table and then having addRoute
  // be a no-op for the in-flight nav.
  app.use(router)

  app.mount('#app')
}

bootstrap()
