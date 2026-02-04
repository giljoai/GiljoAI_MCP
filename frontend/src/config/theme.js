// Vuetify Theme Configuration for GiljoAI MCP Dashboard
export const darkTheme = {
  dark: true,
  colors: {
    // Primary colors from docs/Website colors.txt
    background: '#0e1c2d', // Darkest blue
    surface: '#182739', // Almost as dark blue
    'surface-variant': '#1e3147', // A hue lighter dark blue
    primary: '#ffc300', // Yellow (brand color) - high contrast buttons
    'primary-darken-1': '#1e3147',
    'primary-lighten-1': '#8f97b7', // Lightest blue

    // Accent colors
    // NOTE: secondary is yellow for now for consistency. Future consideration:
    // use lightest blue (#8f97b7) for secondary in dark mode for visual variety
    secondary: '#ffc300', // Yellow (brand color) - same as primary for consistency
    success: '#67bd6d', // Green
    accent: '#8f97b7', // Lightest blue
    info: '#8f97b7', // Lightest blue
    warning: '#ffc300', // Yellow (brand color)
    error: '#c6298c', // Pink red

    // Text colors
    'on-background': '#e1e1e1', // White gray
    'on-surface': '#e1e1e1',
    'on-surface-variant': '#c0c0c0', // Caption text
    'on-primary': '#0e1c2d', // Dark text on yellow buttons
    'on-secondary': '#0e1c2d', // Dark text on yellow (matches primary)
    'on-success': '#0e1c2d',
    'on-accent': '#0e1c2d',
    'on-info': '#0e1c2d',
    'on-warning': '#0e1c2d',
    'on-error': '#e1e1e1',
  },
}

export const lightTheme = {
  dark: false,
  colors: {
    // Darkened light mode for better yellow contrast
    background: '#e8e8e8', // Light gray (was #ffffff)
    surface: '#dedede', // Medium-light gray (was #f5f5f5)
    'surface-variant': '#d0d0d0', // Darker gray (was #e0e0e0)
    primary: '#ffc300', // Yellow (brand color) - consistent with dark theme
    'primary-darken-1': '#1e3147',
    'primary-lighten-1': '#8f97b7',

    // NOTE: secondary is yellow for now for consistency. Future consideration:
    // use med blue (#315074) for secondary in light mode for visual variety
    secondary: '#ffc300', // Yellow (brand color) - same as primary for consistency
    success: '#67bd6d',
    accent: '#8b5cf6', // Purple for light theme
    info: '#315074',
    warning: '#ffc300',
    error: '#c6298c',

    'on-background': '#1a1a1a', // Darker text for better contrast
    'on-surface': '#1a1a1a',
    'on-surface-variant': '#444444', // Caption text (darker)
    'on-primary': '#1a1a1a', // Dark text on yellow buttons
    'on-secondary': '#1a1a1a', // Dark text on yellow (matches primary)
    'on-success': '#ffffff',
    'on-accent': '#ffffff',
    'on-info': '#ffffff',
    'on-warning': '#1a1a1a',
    'on-error': '#ffffff',
  },
}

export default { darkTheme, lightTheme }
