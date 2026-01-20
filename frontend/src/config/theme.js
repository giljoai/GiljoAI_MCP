// Vuetify Theme Configuration for GiljoAI MCP Dashboard
export const darkTheme = {
  dark: true,
  colors: {
    // Primary colors from docs/Website colors.txt
    background: '#0e1c2d', // Darkest blue
    surface: '#182739', // Almost as dark blue
    'surface-variant': '#1e3147', // A hue lighter dark blue
    primary: '#315074', // Med blue
    'primary-darken-1': '#1e3147',
    'primary-lighten-1': '#8f97b7', // Lightest blue

    // Accent colors
    secondary: '#ffc300', // Yellow
    success: '#67bd6d', // Green
    accent: '#c6298c', // Pink red
    info: '#8f97b7', // Lightest blue
    warning: '#ffc300', // Yellow (brand color)
    error: '#c6298c', // Pink red

    // Text colors
    'on-background': '#e1e1e1', // White gray
    'on-surface': '#e1e1e1',
    'on-surface-variant': '#c0c0c0', // Caption text
    'on-primary': '#e1e1e1',
    'on-secondary': '#0e1c2d',
    'on-success': '#0e1c2d',
    'on-accent': '#e1e1e1',
    'on-info': '#0e1c2d',
    'on-warning': '#0e1c2d',
    'on-error': '#e1e1e1',
  },
}

export const lightTheme = {
  dark: false,
  colors: {
    background: '#ffffff',
    surface: '#f5f5f5',
    'surface-variant': '#e0e0e0',
    primary: '#315074',
    'primary-darken-1': '#1e3147',
    'primary-lighten-1': '#8f97b7',

    secondary: '#ffc300',
    success: '#67bd6d',
    accent: '#8b5cf6', // Purple for light theme
    info: '#315074',
    warning: '#ffc300',
    error: '#c6298c',

    'on-background': '#363636', // Dark gray for light theme
    'on-surface': '#363636',
    'on-surface-variant': '#666666', // Caption text
    'on-primary': '#ffffff',
    'on-secondary': '#363636',
    'on-success': '#ffffff',
    'on-accent': '#ffffff',
    'on-info': '#ffffff',
    'on-warning': '#363636',
    'on-error': '#ffffff',
  },
}

export default { darkTheme, lightTheme }
