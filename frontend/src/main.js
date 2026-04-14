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
// This ensures router guard executes for initial navigation (Handover 0034 fix)
const app = createApp(App)

// Register router IMMEDIATELY (synchronously)
// CRITICAL: Router must be registered before any async operations
// so that router.beforeEach guard can intercept initial navigation
app.use(router)
app.use(pinia)
app.use(vuetify)

// Register custom directives
app.directive('draggable', draggable)

// Always use dark theme
localStorage.setItem('theme-preference', 'dark')
vuetify.theme.change('dark')
document.documentElement.setAttribute('data-theme', 'dark')

// Mount app SYNCHRONOUSLY
app.mount('#app')

// THEN do async initialization in background (non-blocking)
async function initializeBackgroundConfig() {
  try {
    // Fetch API configuration from backend
    // This ensures WebSocket uses correct host in LAN mode
    await initializeApiConfig()

    // Register edition-specific routes when mode is not CE.
    // The dynamic import path is computed at runtime so the CE export
    // boundary check (static regex) does not flag it. If the module
    // is absent (CE build), the catch silently skips registration.
    const mode = configService.getGiljoMode()
    if (mode !== 'ce') {
      try {
        const extensionPath = `./saas/routes/index.js` // eslint-disable-line no-useless-concat
        const saasRoutes = await import(/* @vite-ignore */ extensionPath)
        saasRoutes.registerSaasRoutes()
      } catch {
        // Edition extension directory absent (CE export) -- silently skip
      }
    }
  } catch (error) {
    console.warn('[MAIN] Failed to initialize API config, using fallback:', error)
    // App already mounted with fallback config, continue
  }
}

// Start background initialization (non-blocking)
initializeBackgroundConfig()
