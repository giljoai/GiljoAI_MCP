import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { aliases as mdiAliases, mdi } from 'vuetify/iconsets/mdi'
import CodexMarkIcon from '@/components/icons/CodexMarkIcon.vue'

const darkTheme = {
  dark: true,
  colors: {
    background: '#0e1c2d', // Darkest blue
    surface: '#182739', // Almost as dark blue
    'surface-variant': '#1e3147', // A hue lighter dark blue
    primary: '#ffc300', // Yellow
    secondary: '#315074', // Med blue
    accent: '#8f97b7', // Lightest blue
    error: '#c6298c', // Pink red
    info: '#8f97b7', // Lightest blue
    success: '#67bd6d', // Green
    warning: '#ffc300', // Yellow
    'on-background': '#e1e1e1', // White gray
    'on-surface': '#e1e1e1',
    'on-primary': '#000000', // Pure black for max contrast on yellow
    'on-secondary': '#e1e1e1',
    'on-accent': '#0e1c2d',
    'on-error': '#e1e1e1',
    'on-info': '#0e1c2d',
    'on-success': '#0e1c2d',
    'on-warning': '#0e1c2d',
  },
}

const lightTheme = {
  dark: false,
  colors: {
    background: '#ffffff',
    surface: '#f5f5f5',
    'surface-variant': '#e0e0e0',
    primary: '#ffc300', // Yellow
    secondary: '#8b5cf6', // Purple
    accent: '#315074', // Med blue
    error: '#c6298c', // Pink red
    info: '#315074',
    success: '#67bd6d', // Green
    warning: '#ffc300', // Yellow
    'on-background': '#363636', // Dark gray
    'on-surface': '#363636',
    'on-primary': '#363636',
    'on-secondary': '#ffffff',
    'on-accent': '#ffffff',
    'on-error': '#ffffff',
    'on-info': '#ffffff',
    'on-success': '#ffffff',
    'on-warning': '#363636',
  },
}

export default createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
    aliases: {
      ...mdiAliases,
      codexMark: { component: CodexMarkIcon },
    },
    sets: { mdi },
  },
  theme: {
    defaultTheme: 'dark',
    themes: {
      dark: darkTheme,
      light: lightTheme,
    },
  },
  defaults: {
    VBtn: {
      variant: 'flat',
      rounded: 'lg',
    },
    VCard: {
      elevation: 2,
      rounded: 'lg',
    },
    VTextField: {
      variant: 'outlined',
      density: 'comfortable',
    },
  },
})
