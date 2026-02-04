# Handover 0700a: Remove Light Mode Theme Support

**Date:** 2026-02-04
**From Agent:** documentation-manager
**To Agent:** frontend-tester / tdd-implementor
**Priority:** Medium
**Estimated Complexity:** 2-3 hours
**Status:** Not Started

---

## Task Summary

Simplify the GiljoAI MCP frontend by removing light mode theme support, maintaining only dark mode. This reduces codebase complexity and removes UI elements that have accessibility issues with the yellow brand color.

**Why it matters:** Developer tools typically use dark mode, the light mode has contrast issues with yellow branding, and removing it eliminates ~500+ lines of theme-switching code across 15+ files.

---

## Technical Details

### Files to Modify (by Phase)

#### Phase 1: Core Theme System (30 min)
| File | Changes | Lines Affected |
|------|---------|----------------|
| `frontend/src/config/theme.js` | DELETE `lightTheme` export | ~30 lines |
| `frontend/src/main.js` | Remove lightTheme import, simplify theme init | ~5 lines |
| `frontend/src/stores/settings.js` | DELETE toggleTheme method, simplify isDarkTheme | ~15 lines |

#### Phase 2: UI Component Cleanup (45 min)
| File | Changes | Lines Affected |
|------|---------|----------------|
| `frontend/src/components/navigation/NavigationDrawer.vue` | DELETE "Toggle Theme" button and `toggleTheme()` function | ~20 lines |
| `frontend/src/views/UserSettings.vue` | DELETE theme selector radio buttons from Appearance section | ~25 lines |

#### Phase 3: Icon Simplification (30 min)
Always use dark theme icon variants, remove conditional logic:

| File | Computed Property | Change |
|------|-------------------|--------|
| `frontend/src/components/navigation/NavigationDrawer.vue` | `jobsIcon` | Always return `'/icons/Giljo_Inactive.svg'` |
| `frontend/src/components/icons/GiljoFaceIcon.vue` | Icon path logic | Always use dark variant |
| `frontend/src/components/navigation/AppBar.vue` | Logo path | Always use dark variant |
| `frontend/src/views/Login.vue` | Logo path | Always use dark variant |
| `frontend/src/views/FirstLogin.vue` | Logo path | Always use dark variant |
| `frontend/src/views/UserSettings.vue` | Icon paths | Always use dark variant |
| `frontend/src/components/projects/AgentDetailsModal.vue` | Icon paths | Always use dark variant |
| `frontend/src/components/projects/JobsTab.vue` | Icon paths | Always use dark variant |
| `frontend/src/components/settings/integrations/McpIntegrationCard.vue` | Icon paths | Always use dark variant |
| `frontend/src/components/settings/tabs/AdminIntegrationsTab.vue` | Icon paths | Always use dark variant |
| `frontend/src/views/WelcomeView.vue` | Logo path | Always use dark variant |
| `frontend/src/components/GilMascot.vue` | Mascot images | Always use dark variant |

#### Phase 4: CSS Cleanup (30 min)
DELETE all `.v-theme--light` and `[data-theme="light"]` CSS blocks:

| File | Lines | Description |
|------|-------|-------------|
| `frontend/src/styles/main.scss` | 24-33 | Light theme CSS variables |
| `frontend/src/App.vue` | 47-49 | Light mode background |
| `frontend/src/views/Login.vue` | 348-351 | Light mode card styling |
| `frontend/src/views/FirstLogin.vue` | 382-385 | Light mode card styling |
| `frontend/src/components/TemplateManager.vue` | 1745-1752 | Light mode input styling |
| `frontend/src/components/projects/MessageInput.vue` | 388-399 | Light mode input border |

#### Phase 5: Test Updates (30 min)
| File | Changes |
|------|---------|
| `frontend/tests/unit/views/UserSettings.spec.js` | Remove theme toggle tests |
| `frontend/tests/unit/components/settings/integrations/McpIntegrationCard.spec.js` | Remove light mode icon tests |

#### Phase 6: Static Asset Deletion (15 min)
DELETE unused light mode assets (ONLY after code cleanup verified):

```
frontend/public/Giljo_BY.svg
frontend/public/icons/Giljo_BY_Face.svg
frontend/public/icons/Giljo_Inactive_Light.svg
frontend/public/icons/Giljo_Dark_Face.svg
frontend/public/mascot/Giljo_*_Blue_*.svg  (various blue mascot variants)
```

---

## Implementation Plan

### Phase 1: Core Theme System (30 min)

**1.1 Simplify theme.js**
```javascript
// DELETE lightTheme export entirely
// KEEP only darkTheme export

// Before:
export const lightTheme = { ... }
export const darkTheme = { ... }

// After:
export const darkTheme = { ... }
// Remove lightTheme completely
```

**1.2 Update main.js**
```javascript
// Before:
import { darkTheme, lightTheme } from './config/theme'
const vuetify = createVuetify({
  theme: {
    defaultTheme: 'darkTheme',
    themes: { darkTheme, lightTheme }
  }
})

// After:
import { darkTheme } from './config/theme'
const vuetify = createVuetify({
  theme: {
    defaultTheme: 'darkTheme',
    themes: { darkTheme }
  }
})
```

**1.3 Simplify settings.js store**
```javascript
// DELETE toggleTheme() method entirely
// KEEP isDarkTheme as constant true

// Before:
const isDarkTheme = computed(() =>
  localStorage.getItem('theme') !== 'light'
)

function toggleTheme() {
  const newTheme = isDarkTheme.value ? 'light' : 'dark'
  localStorage.setItem('theme', newTheme)
  // ...
}

// After:
const isDarkTheme = computed(() => true)
// Remove toggleTheme completely
```

### Phase 2: UI Component Cleanup (45 min)

**2.1 NavigationDrawer.vue - Remove Toggle Button**
```vue
<!-- DELETE this entire section (around line 80-100): -->
<v-list-item @click="toggleTheme">
  <v-list-item-title>Toggle Theme</v-list-item-title>
  <template v-slot:prepend>
    <v-icon :icon="isDarkTheme ? 'mdi-weather-night' : 'mdi-weather-sunny'" />
  </template>
</v-list-item>

<!-- DELETE toggleTheme method from script section -->
```

**2.2 UserSettings.vue - Remove Theme Selector**
```vue
<!-- DELETE from Appearance section (around line 200-225): -->
<v-card-text>
  <v-radio-group v-model="selectedTheme" @change="updateTheme">
    <v-radio label="Dark Mode" value="dark" />
    <v-radio label="Light Mode" value="light" />
  </v-radio-group>
</v-card-text>

<!-- DELETE related methods: updateTheme(), selectedTheme computed -->
```

### Phase 3: Icon Simplification (30 min)

**Pattern to apply across all files:**
```javascript
// Before (conditional):
computed: {
  logoPath() {
    return this.isDarkTheme
      ? '/icons/Giljo_Logo.svg'
      : '/icons/Giljo_BY.svg'
  }
}

// After (always dark):
computed: {
  logoPath() {
    return '/icons/Giljo_Logo.svg'
  }
}

// OR simplify to direct template usage:
<img src="/icons/Giljo_Logo.svg" alt="Giljo Logo" />
```

**Files requiring this pattern:**
1. NavigationDrawer.vue - `jobsIcon` computed
2. GiljoFaceIcon.vue - icon path logic
3. AppBar.vue - logo path
4. Login.vue - logo path
5. FirstLogin.vue - logo path
6. UserSettings.vue - icon paths
7. AgentDetailsModal.vue - icon paths
8. JobsTab.vue - icon paths
9. McpIntegrationCard.vue - icon paths
10. AdminIntegrationsTab.vue - icon paths
11. WelcomeView.vue - logo path
12. GilMascot.vue - mascot image paths

### Phase 4: CSS Cleanup (30 min)

**DELETE all light theme CSS blocks:**

```scss
// DELETE from main.scss (lines 24-33):
.v-theme--light {
  --v-bg-color: #f5f5f5;
  --v-surface-color: #ffffff;
  // ... entire block
}

// DELETE from App.vue (lines 47-49):
[data-theme="light"] {
  background-color: #f5f5f5;
}

// DELETE from Login.vue, FirstLogin.vue, TemplateManager.vue, MessageInput.vue
// (search for ".v-theme--light" and "[data-theme='light']")
```

### Phase 5: Test Updates (30 min)

**UserSettings.spec.js - Remove theme tests:**
```javascript
// DELETE tests like:
it('toggles theme when theme selector changes', async () => { ... })
it('shows current theme in radio group', () => { ... })
```

**McpIntegrationCard.spec.js - Remove light mode icon tests:**
```javascript
// DELETE tests checking for light mode icon variants
```

### Phase 6: Asset Deletion (15 min)

**ONLY after all code changes verified:**
```bash
# Navigate to frontend directory
cd frontend/public

# Delete light mode assets
rm Giljo_BY.svg
rm icons/Giljo_BY_Face.svg
rm icons/Giljo_Inactive_Light.svg
rm icons/Giljo_Dark_Face.svg

# Delete blue mascot variants (if any exist)
rm -f mascot/Giljo_*_Blue_*.svg
```

---

## Testing Requirements

### Unit Tests
- [ ] `theme.js` - verify only darkTheme export exists
- [ ] `settings.js` - verify isDarkTheme always returns true
- [ ] `NavigationDrawer.vue` - verify no "Toggle Theme" button renders
- [ ] `UserSettings.vue` - verify no theme selector renders
- [ ] All icon components - verify correct dark theme icon paths

### Integration Tests
- [ ] Full app loads in dark mode
- [ ] No console errors about missing light theme
- [ ] No broken image paths (404s for light mode assets)
- [ ] Settings panel renders without theme options
- [ ] Navigation drawer renders without theme toggle

### Manual Verification
- [ ] Open app in browser - should be dark mode
- [ ] Check localStorage - no theme key should affect rendering
- [ ] Navigate through all views - verify consistent dark theme
- [ ] Check browser console - no CSS warnings about light theme
- [ ] Verify all icons/logos display correctly

---

## Dependencies and Blockers

**Dependencies:**
- Node.js and npm installed
- Frontend dev server running (`npm run dev`)
- Access to browser dev tools for verification

**No blockers identified.**

---

## Success Criteria

- [ ] `lightTheme` removed from `theme.js`
- [ ] No theme toggle button in NavigationDrawer
- [ ] No theme selector in UserSettings
- [ ] All icon paths use dark variants only (no conditionals)
- [ ] No `.v-theme--light` or `[data-theme="light"]` CSS exists
- [ ] All tests pass (`npm run test:unit`)
- [ ] No console errors when loading app
- [ ] App loads in dark mode by default
- [ ] Light mode assets deleted (after verification)
- [ ] Documentation updated if User Settings screenshots exist

---

## Rollback Plan

If dark-mode-only causes issues:

1. Restore files from git:
```bash
git checkout frontend/src/config/theme.js
git checkout frontend/src/main.js
git checkout frontend/src/stores/settings.js
# ... (restore other modified files)
```

2. Restore deleted assets:
```bash
git checkout frontend/public/Giljo_BY.svg
git checkout frontend/public/icons/
```

3. Run tests to verify rollback:
```bash
npm run test:unit
npm run dev  # Verify app loads
```

---

## Output Artifacts

After completion:
1. Simplified theme system (~50 lines of code removed from theme files)
2. Cleaner UI components (~45 lines removed from Vue components)
3. Simplified icon logic (~120 lines removed from conditional icon paths)
4. Cleaner CSS (~60 lines of light mode CSS removed)
5. Updated tests (theme toggle tests removed)
6. Smaller bundle size (unused assets deleted)

**Estimated total cleanup:** ~500+ lines of code removed

---

## Context for Future Work

**Why dark mode only?**
- Developer tools convention (VS Code, Chrome DevTools, etc.)
- Yellow brand color has better contrast on dark backgrounds
- Simpler codebase with fewer conditional branches
- Removes maintenance burden of two parallel theme systems

**Related work:**
- This handover is part of the 0700 series code cleanup
- Follows patterns from 0700 (cleanup index creation)
- Prepares codebase for future simplification efforts

---

## Next Handover

**0700b_cleanup_deprecated_markers.md** - Systematically remove or update files marked with DEPRECATED comments using the cleanup index from 0700.
