import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { pinia } from './stores'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'

// Theme configuration
import { darkTheme, lightTheme } from './config/theme'

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

// Create Vue app
const app = createApp(App)

// Use plugins
app.use(router)
app.use(pinia)
app.use(vuetify)

// Mount app
app.mount('#app')
