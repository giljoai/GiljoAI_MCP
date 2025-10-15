# GiljoAI MCP Design System

**Implementation Status**: 90% Complete - Production Ready (Handover 0009 - COMPLETE)
**Last Verified**: October 13, 2025

For comprehensive verification results, see:
- [UI/UX Implementation Status Summary](../docs/UI_UX_IMPLEMENTATION_STATUS_SUMMARY_10_13_2025.md)
- [WCAG 2.1 AA Accessibility Audit](../docs/WCAG_2_1_AA_ACCESSIBILITY_AUDIT_10_13_2025.md)

## Brand Colors

### Primary Brand Color - Yellow
- **Hex**: `#FFD93D`
- **Usage**: Primary actions, highlights, interactive elements, brand accents
- **Examples**: Action buttons, icons, resize handles, active states

### Color Palette
```css
--giljo-yellow: #FFD93D;      /* Primary brand color */
--giljo-dark: #1E1E1E;        /* Dark backgrounds */
--giljo-surface: #2C2C2C;     /* Surface/card backgrounds */
--giljo-text: #FFFFFF;        /* Primary text */
--giljo-text-muted: #B0B0B0;  /* Secondary/muted text */
```

## UI Patterns

### Resize Handle (Standard)
Use on scrollable containers or expandable panels to indicate more content is available.

**Implementation:**
```vue
<!-- Resize Handle -->
<div class="resize-handle">
  <v-icon size="16" color="#FFD93D">mdi-resize-bottom-right</v-icon>
</div>
```

**CSS:**
```css
.resize-handle {
  position: absolute;
  bottom: 4px;
  right: 4px;
  cursor: nwse-resize;
  opacity: 0.5;
  transition: opacity 0.2s;
  pointer-events: none;
}

.resize-handle:hover {
  opacity: 0.8;
}
```

**When to use:**
- Dropdown menus with scrollable content
- Expandable panels
- Modal dialogs with overflow content
- Any container where content may extend beyond visible area

### Action Buttons
Primary action buttons should use the brand yellow color.

**Examples:**
```vue
<!-- Primary Actions -->
<v-btn color="#FFD93D">Save</v-btn>
<v-btn variant="text" color="#FFD93D">Cancel</v-btn>

<!-- Icon Buttons -->
<v-btn icon color="#FFD93D">
  <v-icon>mdi-plus</v-icon>
</v-btn>
```

### Icons
Brand-colored icons should use `color="#FFD93D"` for:
- Primary action icons (add, create, save)
- Navigation icons when active
- Interactive indicators (refresh, expand, etc.)
- Status indicators for active/selected states

**Example:**
```vue
<v-icon color="#FFD93D">mdi-refresh</v-icon>
```

## Typography

### Text Truncation
For long descriptions in compact spaces:

```css
.text-truncate-3-lines {
  white-space: normal;
  line-height: 1.3;
  max-height: 3.9em;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}
```

## Component Guidelines

### Dropdown Menus
- **Min-width**: 300px
- **Max-width**: 500px
- **Max-height**: 80vh (80% of viewport height)
- **Overflow**: Vertical scroll when needed
- **Resize handle**: Always include on scrollable dropdowns

### Cards
- **Background**: Use theme surface color
- **Padding**: Consistent 16px (or use Vuetify's spacing)
- **Shadows**: Elevation 2-4 for dropdowns, 0-1 for inline cards
- **Border-radius**: 8px (Vuetify default)

### Buttons
- **Primary actions**: Yellow (`#FFD93D`)
- **Secondary actions**: Text variant with yellow
- **Destructive actions**: Red (use sparingly)
- **Size**: `small` for compact interfaces, `default` for forms

## Accessibility

### Color Contrast
- Yellow (`#FFD93D`) on dark backgrounds provides excellent contrast
- Always test text legibility when using yellow backgrounds
- Use darker text on yellow backgrounds

### Interactive Elements
- All interactive elements must have visible hover states
- Maintain minimum 44x44px touch targets for mobile
- Use appropriate ARIA labels for icon-only buttons

## Implementation Checklist

When creating new components:
- [ ] Use brand yellow (`#FFD93D`) for primary actions
- [ ] Add resize handle to scrollable containers
- [ ] Implement proper text truncation for long content
- [ ] Ensure responsive sizing (min/max widths)
- [ ] Test on both light and dark themes
- [ ] Verify accessibility (contrast, touch targets, ARIA)

## Examples in Codebase

- **ProductSwitcher.vue**: Reference implementation of dropdown with resize handle, yellow buttons, and text truncation
- **App.vue**: Main layout and theme configuration

## Future Considerations

- Create reusable Vue composable for resize handle
- Add yellow color to Vuetify theme configuration
- Create shared CSS utility classes for common patterns
- Build component library with Storybook documentation
