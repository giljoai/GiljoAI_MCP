# Accessibility Action Plan - GiljoAI MCP
**Quick Reference Guide for Development Team**

**Current Compliance:** 85/100 WCAG 2.1 Level AA
**Target Compliance:** 95/100 WCAG 2.1 Level AA
**Timeline:** 2 weeks for critical fixes

---

## Critical Issues (Fix This Week)

### 1. Brand Color Correction
**File:** `frontend/src/plugins/vuetify.js`
**Lines:** 12, 18, 37, 43

**Change:**
```javascript
// BEFORE
primary: '#ffc300',
warning: '#ffc300',

// AFTER
primary: '#FFD93D',
warning: '#FFD93D',
```

**Impact:** 14% contrast improvement (11.2:1 → 12.8:1)
**Effort:** 5 minutes
**Priority:** HIGH

---

### 2. Touch Target Size - Icon Buttons
**Files:** `TemplateManager.vue` (lines 110-150), `App.vue` (lines 117-122)

**Change from:**
```vue
<v-btn icon="mdi-eye" size="small" variant="text" @click="preview" />
```

**Change to:**
```vue
<v-btn
  icon="mdi-eye"
  size="default"
  variant="text"
  :style="{ minWidth: '44px', minHeight: '44px' }"
  aria-label="Preview template"
  @click="preview"
/>
```

**Impact:** Critical mobile usability improvement
**Effort:** 30 minutes
**Priority:** CRITICAL

**Affected Components:**
- TemplateManager.vue action buttons (Preview, Edit, Copy, History, Delete)
- App.vue notification button
- App.vue user menu button

---

### 3. Missing Alt Text on Custom Navigation Icons
**File:** `App.vue`
**Line:** 54-60

**Change from:**
```vue
<v-img
  v-if="item.customIcon"
  :src="item.customIcon"
  width="28"
  height="28"
/>
```

**Change to:**
```vue
<v-img
  v-if="item.customIcon"
  :src="item.customIcon"
  :alt="`${item.title} icon`"
  width="28"
  height="28"
/>
```

**Impact:** Screen readers can identify navigation items
**Effort:** 10 minutes
**Priority:** HIGH

---

## Medium Priority (Next Sprint)

### 4. Data Table ARIA Labels
**File:** `TemplateManager.vue`
**Line:** 56

**Add:**
```vue
<v-data-table
  :headers="headers"
  :items="filteredTemplates"
  :search="search"
  aria-label="Agent Templates table"
  class="elevation-1 templates-table"
/>
```

**Impact:** Better screen reader table navigation
**Effort:** 30 minutes
**Priority:** MEDIUM

---

### 5. Router Focus Management
**File:** `frontend/src/router/index.js`

**Add after router creation:**
```javascript
import { nextTick } from 'vue'

router.afterEach((to, from) => {
  nextTick(() => {
    // Focus main content
    const mainContent = document.getElementById('main-content')
    if (mainContent) {
      mainContent.setAttribute('tabindex', '-1')
      mainContent.focus()
    }

    // Announce page change
    const announcement = document.createElement('div')
    announcement.setAttribute('role', 'status')
    announcement.setAttribute('aria-live', 'polite')
    announcement.setAttribute('aria-atomic', 'true')
    announcement.style.position = 'absolute'
    announcement.style.left = '-10000px'
    announcement.textContent = `Navigated to ${to.meta.title || to.name}`
    document.body.appendChild(announcement)
    setTimeout(() => document.body.removeChild(announcement), 1000)
  })
})
```

**Impact:** Proper page change announcements for screen readers
**Effort:** 1-2 hours
**Priority:** MEDIUM

---

### 6. Convert Font Sizes to REM
**Files:** All component style blocks

**Pattern:**
```css
/* BEFORE */
font-size: 14px;

/* AFTER */
font-size: 0.875rem; /* 14px at 16px base */
```

**Common conversions:**
- 12px = 0.75rem
- 14px = 0.875rem
- 16px = 1rem
- 18px = 1.125rem
- 20px = 1.25rem
- 24px = 1.5rem

**Impact:** Supports 200% text scaling
**Effort:** 2-3 hours
**Priority:** MEDIUM

---

## Low Priority (Future Sprints)

### 7. Loading State Announcements

**Add to components with async operations:**
```vue
<template>
  <!-- Existing UI -->

  <!-- Add this for screen readers -->
  <div v-if="loading" role="status" aria-live="polite" class="sr-only">
    {{ loadingMessage }}
  </div>
</template>

<style scoped>
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
</style>
```

**Impact:** Better async feedback for screen readers
**Effort:** 4-5 hours across all components
**Priority:** LOW

---

### 8. Mobile Touch Pattern for Dense UIs

**TemplateManager.vue - Add responsive action buttons:**

```vue
<template v-slot:item.actions="{ item }">
  <!-- Desktop: Icon buttons -->
  <template v-if="!$vuetify.display.mobile">
    <v-btn icon="mdi-eye" size="default" @click="preview(item)" />
    <v-btn icon="mdi-pencil" size="default" @click="edit(item)" />
    <v-btn icon="mdi-content-copy" size="default" @click="duplicate(item)" />
  </template>

  <!-- Mobile: Menu -->
  <v-menu v-else>
    <template v-slot:activator="{ props }">
      <v-btn
        icon="mdi-dots-vertical"
        v-bind="props"
        aria-label="Template actions"
      />
    </template>
    <v-list>
      <v-list-item @click="preview(item)">
        <template v-slot:prepend>
          <v-icon>mdi-eye</v-icon>
        </template>
        <v-list-item-title>Preview</v-list-item-title>
      </v-list-item>
      <v-list-item @click="edit(item)">
        <template v-slot:prepend>
          <v-icon>mdi-pencil</v-icon>
        </template>
        <v-list-item-title>Edit</v-list-item-title>
      </v-list-item>
      <!-- More items... -->
    </v-list>
  </v-menu>
</template>
```

**Impact:** Significantly improved mobile usability
**Effort:** 8-10 hours for all dense UIs
**Priority:** LOW

---

## Testing Checklist

### Before Every PR
```
[ ] All interactive elements reachable via keyboard
[ ] Focus indicators visible (2px outline)
[ ] All images have appropriate alt text
[ ] Forms have associated labels
[ ] Color contrast verified (4.5:1 minimum)
[ ] Touch targets minimum 44x44px
[ ] ARIA labels on icon-only buttons
[ ] No horizontal scrolling at 200% zoom
```

### Manual Testing Process

1. **Keyboard Navigation**
   ```
   - Tab through entire page
   - Verify logical order
   - Check focus indicators
   - Test Enter/Space activation
   - Verify Escape closes dialogs
   ```

2. **Screen Reader Simulation**
   ```
   - Use browser DevTools accessibility inspector
   - Verify ARIA labels read correctly
   - Check form field associations
   - Test error message announcements
   ```

3. **Touch Target Measurement**
   ```
   - Open DevTools
   - Inspect button elements
   - Verify computed size ≥ 44x44px
   - Check spacing between targets ≥ 8px
   ```

4. **Color Contrast**
   ```
   - Use WebAIM Contrast Checker
   - Test all text on backgrounds
   - Verify icon contrast (3:1 minimum)
   - Check hover/focus states
   ```

---

## Quick Wins (30 Minutes Total)

Run these commands to make immediate improvements:

### 1. Update Brand Color (5 min)
```bash
# Edit frontend/src/plugins/vuetify.js
# Find and replace: #ffc300 → #FFD93D
```

### 2. Fix Navigation Icon Alt Text (5 min)
```bash
# Edit frontend/src/App.vue line 54-60
# Add :alt binding to v-img
```

### 3. Increase Icon Button Sizes (20 min)
```bash
# Edit frontend/src/components/TemplateManager.vue
# Change size="small" to size="default"
# Add minWidth/minHeight inline styles
```

---

## Automated Testing Integration

### Install axe-core for Vue
```bash
npm install --save-dev @axe-core/vue
```

### Add to main.js (development only)
```javascript
if (process.env.NODE_ENV !== 'production') {
  import('@axe-core/vue').then(axe => {
    axe.default(app, {
      clearConsoleOnUpdate: false,
      config: {
        rules: [
          { id: 'color-contrast', enabled: true },
          { id: 'button-name', enabled: true },
          { id: 'image-alt', enabled: true },
          { id: 'label', enabled: true },
        ]
      }
    })
  })
}
```

### Run Lighthouse Accessibility Audit
```bash
# Install Lighthouse
npm install -g lighthouse

# Run audit
lighthouse http://localhost:7274 --only-categories=accessibility --output=html --output-path=./accessibility-report.html
```

---

## Progress Tracking

### Week 1 Goals
- [x] Complete accessibility audit
- [ ] Fix brand color (#FFC300 → #FFD93D)
- [ ] Increase all icon button touch targets to 44x44px
- [ ] Add missing alt text to navigation icons
- [ ] Test keyboard navigation on all pages

### Week 2 Goals
- [ ] Add ARIA labels to data tables
- [ ] Implement router focus management
- [ ] Convert font sizes to rem units
- [ ] Test at 200% text scaling
- [ ] Run automated accessibility tests

### Success Metrics
- **Current:** 85/100 WCAG 2.1 AA
- **After Week 1:** 92/100 (target)
- **After Week 2:** 95/100 (target)

---

## Resources

### Testing Tools
- **WebAIM Contrast Checker:** https://webaim.org/resources/contrastchecker/
- **axe DevTools Browser Extension:** Free browser extension
- **Lighthouse:** Built into Chrome DevTools
- **NVDA Screen Reader:** Free Windows screen reader

### Documentation
- **WCAG 2.1 Guidelines:** https://www.w3.org/WAI/WCAG21/quickref/
- **Vuetify Accessibility:** https://vuetifyjs.com/en/features/accessibility/
- **Vue Accessibility:** https://vue-a11y.com/

### Quick Reference
- **Minimum contrast:** 4.5:1 (normal text), 3:1 (large text)
- **Touch targets:** 44x44 CSS pixels minimum
- **Focus indicators:** 2px visible outline
- **ARIA required:** Icon-only buttons, decorative images, complex widgets

---

## Contact

For accessibility questions or concerns:
- Review full audit: `docs/WCAG_2_1_AA_ACCESSIBILITY_AUDIT.md`
- Check handover: `handovers/0009_HANDOVER_UI_UX_ACCESSIBILITY_VERIFICATION.md`
- Design system: `docs/UI_UX_DESIGN_SYSTEM.md`

**Remember:** Accessibility is not optional. It's a legal requirement and makes our application better for everyone.
