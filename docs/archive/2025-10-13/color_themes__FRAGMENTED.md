# GiljoAI MCP Color Themes

## Official Color Palette

### Dark Theme (Primary)

#### Blue Gradient (Main UI)

- **Darkest Blue**: `#0e1c2d` - Primary background
- **Dark Blue**: `#182739` - Secondary background, panels
- **Medium Dark Blue**: `#1e3147` - Cards, elevated surfaces
- **Medium Blue**: `#315074` - Borders, dividers, inactive elements
- **Light Blue**: `#8f97b7` - Text on dark backgrounds, secondary text

#### Accent Colors

- **Primary Yellow**: `#ffc300` - Primary actions, highlights, warnings
- **Success Green**: `#67bd6d` - Success states, confirmations, healthy status
- **Alert Pink/Red**: `#c6298c` - Errors, critical alerts, destructive actions
- **Purple**: `#8b5cf6` - Special features, premium elements

#### Neutral

- **Light Gray**: `#e1e1e1` - Text on dark backgrounds, borders on dark
- **Icon Gray**: `#A5AAAF` - Navigation icons, secondary UI elements

### Light Theme (Secondary)

#### Base Colors

- **Background**: `#ffffff` - Main background
- **Surface**: `#f5f5f5` - Cards, panels
- **Text Primary**: `#363636` - Main text color
- **Text Secondary**: `#606060` - Secondary text

#### Accent Colors (Same as Dark Theme)

- **Primary Yellow**: `#ffc300`
- **Success Green**: `#67bd6d`
- **Alert Pink/Red**: `#c6298c`
- **Purple**: `#8b5cf6`

## Usage Guidelines

### Components

#### Buttons

- **Primary Action**: Yellow (`#ffc300`) with dark text
- **Secondary Action**: Medium Blue (`#315074`) with light text
- **Success Action**: Green (`#67bd6d`) with white text
- **Danger Action**: Pink/Red (`#c6298c`) with white text
- **Special/Premium**: Purple (`#8b5cf6`) with white text

#### Status Indicators

- **Healthy/Active**: Green (`#67bd6d`)
- **Warning/Pending**: Yellow (`#ffc300`)
- **Error/Critical**: Pink/Red (`#c6298c`)
- **Info/Special**: Purple (`#8b5cf6`)
- **Inactive/Disabled**: Light Blue (`#8f97b7`)

#### Context Usage Indicators

- 🟢 Green (`#67bd6d`): 0-50% usage
- 🟡 Yellow (`#ffc300`): 50-70% usage
- 🟠 Orange (blend yellow/red): 70-80% usage
- 🔴 Red (`#c6298c`): 80%+ usage

### Dashboard Sections

#### Navigation

- Background: Darkest Blue (`#0e1c2d`)
- Active Item: Medium Blue (`#315074`) background
- Hover: Dark Blue (`#182739`) background
- Text: Light Gray (`#e1e1e1`)

#### Main Content Area

- Background: Dark Blue (`#182739`)
- Cards: Medium Dark Blue (`#1e3147`)
- Borders: Medium Blue (`#315074`)
- Text: Light Gray (`#e1e1e1`)

#### Data Visualization

- Primary Series: Yellow (`#ffc300`)
- Secondary Series: Green (`#67bd6d`)
- Tertiary Series: Purple (`#8b5cf6`)
- Warning Series: Pink/Red (`#c6298c`)
- Grid Lines: Medium Blue (`#315074`)

### Implementation in Vue/Vuetify

```scss
// CSS Variables for theme switching
:root {
  // Dark theme (default)
  --color-bg-primary: #0e1c2d;
  --color-bg-secondary: #182739;
  --color-bg-elevated: #1e3147;
  --color-border: #315074;
  --color-text-primary: #e1e1e1;
  --color-text-secondary: #8f97b7;

  // Accent colors (same for both themes)
  --color-accent-primary: #ffc300;
  --color-accent-success: #67bd6d;
  --color-accent-danger: #c6298c;
  --color-accent-special: #8b5cf6;
}

// Light theme override
[data-theme="light"] {
  --color-bg-primary: #ffffff;
  --color-bg-secondary: #f5f5f5;
  --color-bg-elevated: #ffffff;
  --color-border: #e0e0e0;
  --color-text-primary: #363636;
  --color-text-secondary: #606060;
}
```

### Vuetify 3 Theme Configuration

```javascript
// vuetify.config.js
export default {
  theme: {
    defaultTheme: "dark",
    themes: {
      dark: {
        dark: true,
        colors: {
          background: "#0e1c2d",
          surface: "#182739",
          "surface-variant": "#1e3147",
          primary: "#ffc300",
          secondary: "#315074",
          success: "#67bd6d",
          error: "#c6298c",
          warning: "#ffc300",
          info: "#8b5cf6",
          "on-background": "#e1e1e1",
          "on-surface": "#e1e1e1",
          "on-primary": "#0e1c2d",
          "on-secondary": "#e1e1e1",
        },
      },
      light: {
        dark: false,
        colors: {
          background: "#ffffff",
          surface: "#f5f5f5",
          "surface-variant": "#f0f0f0",
          primary: "#ffc300",
          secondary: "#315074",
          success: "#67bd6d",
          error: "#c6298c",
          warning: "#ffc300",
          info: "#8b5cf6",
          "on-background": "#363636",
          "on-surface": "#363636",
          "on-primary": "#363636",
          "on-secondary": "#ffffff",
        },
      },
    },
  },
};
```

## Accessibility Requirements

### Contrast Ratios

- Normal text on backgrounds: Minimum 4.5:1
- Large text on backgrounds: Minimum 3:1
- Interactive elements: Minimum 3:1

### Tested Combinations

- Light Gray (`#e1e1e1`) on Darkest Blue (`#0e1c2d`): ✅ 9.8:1
- Yellow (`#ffc300`) on Darkest Blue (`#0e1c2d`): ✅ 10.4:1
- Green (`#67bd6d`) on Darkest Blue (`#0e1c2d`): ✅ 5.6:1
- Dark Gray (`#363636`) on White (`#ffffff`): ✅ 10.1:1

## Application Areas

### Agent Status Cards

- Background: Medium Dark Blue (`#1e3147`)
- Active border: Green (`#67bd6d`)
- Inactive border: Medium Blue (`#315074`)
- Context usage: Progressive color scale

### Message Queue

- Unread background: Dark Blue (`#182739`)
- Read background: Darkest Blue (`#0e1c2d`)
- Priority high: Yellow (`#ffc300`) indicator
- Acknowledged: Green (`#67bd6d`) checkmark

### Project Dashboard

- Active project: Yellow (`#ffc300`) highlight
- Completed: Green (`#67bd6d`) badge
- Planning: Purple (`#8b5cf6`) badge
- Failed: Pink/Red (`#c6298c`) badge

## DO NOT

- Don't use pure white (`#ffffff`) on dark backgrounds - use Light Gray (`#e1e1e1`)
- Don't use pure black (`#000000`) on light backgrounds - use Dark Gray (`#363636`)
- Don't create new accent colors - use the defined palette
- Don't modify the hex values - consistency is critical

## Notes for Developers

- All UI components MUST use these colors
- Theme switching must be smooth with CSS transitions
- Test all color combinations for accessibility
- Use CSS variables for easy theme switching
- Charts and graphs must follow the data visualization palette
