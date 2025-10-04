console.log('[MAIN] Starting application initialization')

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { pinia } from './stores'

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
