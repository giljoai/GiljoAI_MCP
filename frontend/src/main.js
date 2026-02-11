import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { pinia } from './stores'
import { initializeApiConfig } from './config/api'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'

// Global Styles
import '@/styles/main.scss'
import '@/styles/global-tabs.scss'

// Theme configuration
import { darkTheme } from './config/theme'

// Create Vuetify instance with theme
const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'dark',
    themes: {
      dark: darkTheme,
    },
  },
  icons: {
    defaultSet: 'mdi',
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
  } catch (error) {
    console.warn('[MAIN] Failed to initialize API config, using fallback:', error)
    // App already mounted with fallback config, continue
  }
}

// Start background initialization (non-blocking)
initializeBackgroundConfig()
