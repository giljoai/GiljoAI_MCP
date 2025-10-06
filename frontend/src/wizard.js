/**
 * GiljoAI MCP Setup Wizard Entry Point
 *
 * Minimal Vue 3 app for the standalone setup wizard.
 * This runs independently from the main dashboard application.
 */

console.log('[WIZARD] Starting wizard initialization')

import { createApp } from 'vue'
import SetupWizard from './views/SetupWizard.vue'

console.log('[WIZARD] Imports loaded')

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'

console.log('[WIZARD] Vuetify imports loaded')

// Theme configuration
import { darkTheme, lightTheme } from './config/theme'

console.log('[WIZARD] Theme configuration loaded')

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

console.log('[WIZARD] Vuetify instance created')

// Create Vue app
const app = createApp(SetupWizard)

console.log('[WIZARD] Vue app created')

// Use Vuetify
app.use(vuetify)
console.log('[WIZARD] Vuetify registered')

// Mount app
app.mount('#app')
console.log('[WIZARD] App mounted to #app')
