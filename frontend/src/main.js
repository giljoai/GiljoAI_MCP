console.log('[MAIN] Starting application initialization')

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { pinia } from './stores'
import { initializeApiConfig } from './config/api'

console.log('[MAIN] Imports loaded')

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'

// Global Styles
import '@/styles/global-tabs.scss'

console.log('[MAIN] Vuetify imports loaded')

// Theme configuration
import { darkTheme, lightTheme } from './config/theme'

console.log('[MAIN] Theme configuration loaded')

// Create Vuetify instance with theme
const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'dark',
    themes: {
      dark: darkTheme,
      light: lightTheme,
    },
  },
  icons: {
    defaultSet: 'mdi',
  },
})

console.log('[MAIN] Vuetify instance created')

// Create Vue app SYNCHRONOUSLY (before async operations)
// This ensures router guard executes for initial navigation (Handover 0034 fix)
const app = createApp(App)
console.log('[MAIN] Vue app created')

// Register router IMMEDIATELY (synchronously)
// CRITICAL: Router must be registered before any async operations
// so that router.beforeEach guard can intercept initial navigation
app.use(router)
console.log('[MAIN] Router registered')

app.use(pinia)
console.log('[MAIN] Pinia registered')

app.use(vuetify)
console.log('[MAIN] Vuetify registered')

// Restore theme preference from localStorage BEFORE mounting
// This prevents theme flashing and ensures Settings page reads correct theme
const savedTheme = localStorage.getItem('theme-preference')
if (savedTheme && (savedTheme === 'dark' || savedTheme === 'light')) {
  vuetify.theme.global.name.value = savedTheme // TODO: Upgrade to theme.change() after Vuetify 3.7+
  document.documentElement.setAttribute('data-theme', savedTheme)
  console.log(`[MAIN] Theme restored from localStorage: ${savedTheme}`)
} else {
  // Set default theme in localStorage if not present
  localStorage.setItem('theme-preference', 'dark')
  document.documentElement.setAttribute('data-theme', 'dark')
  console.log('[MAIN] Theme initialized to default: dark')
}

// Mount app SYNCHRONOUSLY
app.mount('#app')
console.log('[MAIN] App mounted to #app')

// THEN do async initialization in background (non-blocking)
async function initializeBackgroundConfig() {
  try {
    console.log('[MAIN] Initializing API configuration from backend...')

    // Fetch API configuration from backend
    // This ensures WebSocket uses correct host in LAN mode
    await initializeApiConfig()

    console.log('[MAIN] API configuration initialized')
  } catch (error) {
    console.warn('[MAIN] Failed to initialize API config, using fallback:', error)
    // App already mounted with fallback config, continue
  }
}

// Start background initialization (non-blocking)
initializeBackgroundConfig()
