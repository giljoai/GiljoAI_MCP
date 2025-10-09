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

// Initialize API configuration from backend before mounting app
async function initializeApp() {
  console.log('[MAIN] Initializing API configuration from backend...')

  // Fetch API configuration from backend
  // This ensures WebSocket uses correct host in LAN mode
  await initializeApiConfig()

  console.log('[MAIN] API configuration initialized')

  // Create Vue app
  const app = createApp(App)

  console.log('[MAIN] Vue app created')

  // Use plugins
  app.use(router)
  console.log('[MAIN] Router registered')

  app.use(pinia)
  console.log('[MAIN] Pinia registered')

  app.use(vuetify)
  console.log('[MAIN] Vuetify registered')

  // Mount app
  app.mount('#app')
  console.log('[MAIN] App mounted to #app')
}

// Start app initialization
initializeApp().catch((error) => {
  console.error('[MAIN] Failed to initialize app:', error)
  // Even if API config fails, still mount the app with fallback config
  const app = createApp(App)
  app.use(router)
  app.use(pinia)
  app.use(vuetify)
  app.mount('#app')
  console.log('[MAIN] App mounted with fallback configuration')
})
