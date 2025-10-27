# Handover 0052: Field Priority Unassigned Category - Implementation Guide

**Document Version**: 1.0
**Date**: 2025-10-27
**For**: Development Team

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Implementation Checklist](#implementation-checklist)
3. [Step-by-Step Instructions](#step-by-step-instructions)
4. [Code Snippets](#code-snippets)
5. [Testing Guide](#testing-guide)
6. [Deployment Steps](#deployment-steps)
7. [Rollback Procedure](#rollback-procedure)

---

## Prerequisites

### Required Knowledge

- Vue 3 Composition API
- Vuetify 3 component library
- vuedraggable library (drag-and-drop)
- JavaScript ES6+ (computed properties, refs, watchers)

### Required Tools

- Node.js 18+
- npm or yarn
- Git
- Text editor (VS Code recommended)

### Environment Setup

```bash
# Navigate to project root
cd F:/GiljoAI_MCP

# Ensure dependencies installed
cd frontend
npm install

# Verify vuedraggable is available
npm list vuedraggable
# Should show: vuedraggable@4.x.x
```

---

## Implementation Checklist

### Phase 1: Create Composable (1.5 hours)

- [ ] Create `frontend/src/composables/useFieldPriority.js`
- [ ] Define `ALL_FIELDS` constant (13 fields)
- [ ] Implement reactive refs for P1/P2/P3
- [ ] Implement writable computed for `unassignedFields`
- [ ] Implement `loadFromConfig()` method
- [ ] Implement `moveToCategory()` method
- [ ] Implement `removeFromPriority()` method
- [ ] Implement `toConfigObject()` method
- [ ] Add JSDoc comments
- [ ] Test composable independently (optional unit tests)

### Phase 2: Update UserSettings View (2 hours)

- [ ] Import `useFieldPriority` composable
- [ ] Replace inline field management with composable
- [ ] Add fourth draggable container in template
- [ ] Update remove button handlers
- [ ] Add Unassigned category styling (dashed border, grey background)
- [ ] Update token calculation to exclude unassigned
- [ ] Add tooltips for Unassigned category
- [ ] Add empty state messages
- [ ] Test drag-and-drop in browser

### Phase 3: Testing (1 hour)

- [ ] Test initial load with default config
- [ ] Test drag from P1/P2/P3 to Unassigned
- [ ] Test drag from Unassigned to P1/P2/P3
- [ ] Test remove button moves to Unassigned
- [ ] Test token calculation updates
- [ ] Test save/load cycle
- [ ] Test edge case: all fields in Unassigned
- [ ] Test edge case: no fields in Unassigned
- [ ] Cross-browser test (Chrome, Firefox, Edge)
- [ ] Accessibility test (keyboard navigation)

### Phase 4: Polish & Documentation (0.5-1 hour)

- [ ] Add inline code comments
- [ ] Update this handover with completion notes
- [ ] Create commit with descriptive message
- [ ] Test final build (`npm run build`)
- [ ] Verify no console errors

---

## Step-by-Step Instructions

### Step 1: Create useFieldPriority Composable

**File**: `frontend/src/composables/useFieldPriority.js` (NEW FILE)

**Location**: Create file in `frontend/src/composables/` directory

**Full Code**:

```javascript
/**
 * Field Priority Management Composable
 *
 * Manages the four-category field priority system for agent mission context:
 * - Priority 1 (Always Included) - Critical fields, always sent to agents
 * - Priority 2 (High Priority) - Important fields, frequently included
 * - Priority 3 (Medium Priority) - Optional fields, included when token budget allows
 * - Unassigned (Not Included) - Fields not sent to agents (0 tokens)
 *
 * @module useFieldPriority
 */

import { ref, computed } from 'vue'

/**
 * All available configuration fields across product config_data.
 * This is the single source of truth for field inventory.
 */
export const ALL_FIELDS = [
  'tech_stack.languages',
  'tech_stack.backend',
  'tech_stack.frontend',
  'tech_stack.database',
  'tech_stack.infrastructure',
  'architecture.pattern',
  'architecture.api_style',
  'architecture.design_patterns',
  'architecture.notes',
  'features.core',
  'test_config.strategy',
  'test_config.frameworks',
  'test_config.coverage_target'
]

/**
 * Field Priority Management Hook
 *
 * @param {Object} initialConfig - Initial field priority configuration
 * @returns {Object} Field priority state and methods
 */
export function useFieldPriority(initialConfig = null) {
  // Reactive state for each priority category
  const priority1Fields = ref([])
  const priority2Fields = ref([])
  const priority3Fields = ref([])

  // Initialize from config if provided
  if (initialConfig) {
    loadFromConfig(initialConfig)
  }

  /**
   * Computed property for unassigned fields.
   * Unassigned = ALL_FIELDS - (P1 + P2 + P3)
   *
   * Uses writable computed to integrate with vuedraggable:
   * - get(): Computes unassigned fields dynamically
   * - set(): Handles drag-and-drop into Unassigned category
   */
  const unassignedFields = computed({
    get() {
      const assigned = new Set([
        ...priority1Fields.value,
        ...priority2Fields.value,
        ...priority3Fields.value
      ])
      return ALL_FIELDS.filter(field => !assigned.has(field))
    },
    set(newValue) {
      // When vuedraggable adds field to unassigned, remove it from priority categories
      const oldValue = unassignedFields.value
      const added = newValue.filter(f => !oldValue.includes(f))

      // Remove newly added fields from all priority categories
      added.forEach(field => {
        priority1Fields.value = priority1Fields.value.filter(f => f !== field)
        priority2Fields.value = priority2Fields.value.filter(f => f !== field)
        priority3Fields.value = priority3Fields.value.filter(f => f !== field)
      })
    }
  })

  /**
   * Load field assignments from configuration object.
   * Clears existing assignments and populates from config.fields.
   *
   * @param {Object} config - Field priority configuration
   * @param {Object} config.fields - Map of field paths to priority levels (1, 2, or 3)
   */
  function loadFromConfig(config) {
    priority1Fields.value = []
    priority2Fields.value = []
    priority3Fields.value = []

    const fields = config?.fields || {}
    Object.entries(fields).forEach(([field, priority]) => {
      if (priority === 1) priority1Fields.value.push(field)
      else if (priority === 2) priority2Fields.value.push(field)
      else if (priority === 3) priority3Fields.value.push(field)
    })
  }

  /**
   * Move field to specified priority category.
   * Removes field from all categories first, then adds to target.
   *
   * @param {string} field - Field path (e.g., "tech_stack.languages")
   * @param {number|null} targetCategory - Priority level (1, 2, 3, or null for Unassigned)
   */
  function moveToCategory(field, targetCategory) {
    // Remove from all categories
    priority1Fields.value = priority1Fields.value.filter(f => f !== field)
    priority2Fields.value = priority2Fields.value.filter(f => f !== field)
    priority3Fields.value = priority3Fields.value.filter(f => f !== field)

    // Add to target category (null = Unassigned, handled by computed)
    if (targetCategory === 1) priority1Fields.value.push(field)
    else if (targetCategory === 2) priority2Fields.value.push(field)
    else if (targetCategory === 3) priority3Fields.value.push(field)
  }

  /**
   * Remove field from all priority categories.
   * Field automatically appears in Unassigned (via computed property).
   *
   * @param {string} field - Field path to remove
   */
  function removeFromPriority(field) {
    priority1Fields.value = priority1Fields.value.filter(f => f !== field)
    priority2Fields.value = priority2Fields.value.filter(f => f !== field)
    priority3Fields.value = priority3Fields.value.filter(f => f !== field)
  }

  /**
   * Convert current field assignments to configuration object.
   * Unassigned fields are NOT included (implicit exclusion).
   *
   * @returns {Object} Configuration object for API persistence
   */
  function toConfigObject() {
    const config = {
      version: "1.0",
      token_budget: 2000,
      fields: {}
    }

    priority1Fields.value.forEach(field => { config.fields[field] = 1 })
    priority2Fields.value.forEach(field => { config.fields[field] = 2 })
    priority3Fields.value.forEach(field => { config.fields[field] = 3 })

    return config
  }

  /**
   * Get user-friendly display name for field path.
   * Converts "tech_stack.languages" → "Tech Stack > Languages"
   *
   * @param {string} fieldPath - Dot-notation field path
   * @returns {string} Formatted display name
   */
  function formatFieldName(fieldPath) {
    return fieldPath
      .split('.')
      .map(part => part.split('_').map(word =>
        word.charAt(0).toUpperCase() + word.slice(1)
      ).join(' '))
      .join(' > ')
  }

  // Public API
  return {
    // State
    priority1Fields,
    priority2Fields,
    priority3Fields,
    unassignedFields,

    // Methods
    loadFromConfig,
    moveToCategory,
    removeFromPriority,
    toConfigObject,
    formatFieldName,

    // Constants
    ALL_FIELDS
  }
}
```

**Verification**:
```bash
# File should be created at:
F:/GiljoAI_MCP/frontend/src/composables/useFieldPriority.js

# Line count should be ~160 lines
```

---

### Step 2: Update UserSettings.vue

**File**: `frontend/src/views/UserSettings.vue`

**Location**: Modify existing file

#### Change 1: Import Composable

**Find** (at top of `<script setup>`):
```javascript
import { ref, computed, onMounted } from 'vue'
```

**Add After**:
```javascript
import { useFieldPriority } from '@/composables/useFieldPriority'
import draggable from 'vuedraggable'
```

#### Change 2: Replace Inline Field Management

**Find** (inline field management code, ~lines 50-80):
```javascript
const priority1Fields = ref([])
const priority2Fields = ref([])
const priority3Fields = ref([])

// ... existing field management logic
```

**Replace With**:
```javascript
// Use field priority composable
const {
  priority1Fields,
  priority2Fields,
  priority3Fields,
  unassignedFields,
  loadFromConfig,
  removeFromPriority,
  toConfigObject,
  formatFieldName,
  ALL_FIELDS
} = useFieldPriority()
```

#### Change 3: Update onMounted

**Find** (existing onMounted):
```javascript
onMounted(async () => {
  // ... existing code to fetch settings

  // Existing field priority loading
  if (userSettings.value.field_priority_config) {
    // ... manual loading logic
  }
})
```

**Replace Field Priority Loading With**:
```javascript
onMounted(async () => {
  // ... existing code to fetch settings

  // Load field priority config using composable
  if (userSettings.value?.field_priority_config) {
    loadFromConfig(userSettings.value.field_priority_config)
  }
})
```

#### Change 4: Update saveSettings

**Find** (existing saveSettings):
```javascript
async function saveSettings() {
  // ... existing code

  // Manual config building
  const config = {
    fields: {}
  }
  priority1Fields.value.forEach(f => config.fields[f] = 1)
  // ... etc
}
```

**Replace Config Building With**:
```javascript
async function saveSettings() {
  // ... existing validation code

  // Build config using composable
  const fieldPriorityConfig = toConfigObject()

  // Send to API
  await api.users.updateSettings({
    field_priority_config: fieldPriorityConfig
  })

  // ... existing success handling
}
```

#### Change 5: Add Unassigned Category Template

**Find** (in template, after Priority 3 container):
```vue
<!-- Priority 3 container -->
<v-card variant="outlined" class="mb-4">
  <!-- ... Priority 3 content -->
</v-card>

<!-- Save/Cancel buttons -->
<v-card-actions>
```

**Insert Between P3 and Buttons**:
```vue
<!-- Unassigned Category (NEW) -->
<v-card variant="outlined" class="mb-4" color="grey-lighten-4">
  <v-card-title class="d-flex align-center">
    <span>Unassigned</span>
    <v-chip size="small" variant="text" color="grey" class="ml-2">
      Not Included in Missions
    </v-chip>
    <v-tooltip location="top">
      <template #activator="{ props }">
        <v-icon v-bind="props" size="small" class="ml-1" color="grey">
          mdi-information
        </v-icon>
      </template>
      <div style="max-width: 300px;">
        Fields in this category are NOT sent to AI agents during mission generation.
        <br><br>
        Drag a field to Priority 1, 2, or 3 to include it in agent missions.
      </div>
    </v-tooltip>
  </v-card-title>

  <v-card-text>
    <draggable
      v-model="unassignedFields"
      group="fields"
      item-key="field"
      class="field-list field-list--unassigned"
      :component-data="{
        type: 'transition-group',
        name: 'flip-list'
      }"
    >
      <template #item="{ element }">
        <v-chip
          :key="element"
          closable
          @click:close="removeFromPriority(element)"
          class="ma-1"
          variant="tonal"
          color="grey"
        >
          {{ formatFieldName(element) }}
        </v-chip>
      </template>
    </draggable>

    <!-- Empty State -->
    <div
      v-if="unassignedFields.length === 0"
      class="text-center text-grey py-6"
      style="font-size: 0.875rem;"
    >
      <v-icon color="success" size="small" class="mr-1">mdi-check-circle</v-icon>
      All fields assigned to priority categories
    </div>
  </v-card-text>
</v-card>
```

#### Change 6: Add Unassigned Styling

**Find** (in `<style scoped>` section at bottom):
```vue
<style scoped>
/* Existing styles */
</style>
```

**Add Inside `<style scoped>`**:
```css
/* Unassigned category styling */
.field-list--unassigned {
  border: 2px dashed #bdbdbd;
  border-radius: 4px;
  min-height: 80px;
  padding: 12px;
  background-color: #fafafa;
  transition: background-color 0.2s ease;
}

.field-list--unassigned:empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.field-list--unassigned:empty::before {
  content: 'Drag fields here to remove from missions';
  color: #9e9e9e;
  font-size: 0.875rem;
  font-style: italic;
}

/* Drag animation */
.flip-list-move {
  transition: transform 0.3s ease;
}
```

#### Change 7: Update Token Calculation (if needed)

**Find** (token calculation computed property):
```javascript
const estimatedTokens = computed(() => {
  // ... existing calculation
})
```

**Ensure it ONLY counts P1/P2/P3** (not unassigned):
```javascript
const estimatedTokens = computed(() => {
  const p1Count = priority1Fields.value.length * 50  // Rough estimate
  const p2Count = priority2Fields.value.length * 30
  const p3Count = priority3Fields.value.length * 20
  const overhead = 500

  // Unassigned fields contribute 0 tokens
  return p1Count + p2Count + p3Count + overhead
})
```

---

### Step 3: Test Implementation

#### Manual Test 1: Initial Load

1. Open browser: `http://localhost:5173` (or dev server URL)
2. Navigate to: User Settings → General
3. Scroll to Field Priority Configuration section

**Expected**:
- 4 categories visible (P1, P2, P3, Unassigned)
- Unassigned has dashed border and grey background
- All 13 fields visible across categories
- Token count displays correctly

#### Manual Test 2: Drag to Unassigned

1. Drag "Database" field from Priority 2 to Unassigned
2. Observe animation and field movement
3. Check token count decreases

**Expected**:
- Field fades out from P2
- Field appears in Unassigned with animation
- Token count updates (decreases by ~30-50 tokens)
- No console errors

#### Manual Test 3: Drag from Unassigned

1. Drag "Features > Core" from Unassigned to Priority 1
2. Observe animation

**Expected**:
- Field moves to P1
- Token count increases
- Field removed from Unassigned list

#### Manual Test 4: Remove Button

1. Click [✕] button on any field in P1/P2/P3
2. Observe field movement

**Expected**:
- Field immediately moves to Unassigned
- Token count updates
- Smooth transition

#### Manual Test 5: Save and Reload

1. Make changes to field priorities
2. Click "Save Changes"
3. Reload page (F5)

**Expected**:
- Changes persist after reload
- Unassigned fields computed correctly from saved config
- No fields missing or duplicated

#### Manual Test 6: Edge Case - All Unassigned

1. Remove all fields from P1/P2/P3
2. Verify all 13 fields in Unassigned

**Expected**:
- P1/P2/P3 show "Drag fields here" placeholder
- Unassigned shows all 13 fields
- Token count = 500 (structure overhead only)

#### Manual Test 7: Edge Case - No Unassigned

1. Assign all 13 fields to P1/P2/P3
2. Verify Unassigned is empty

**Expected**:
- Unassigned shows green checkmark message
- No fields in Unassigned list
- Token count reflects all fields

---

### Step 4: Cross-Browser Testing

**Browsers to Test**:
1. Chrome (latest) - PRIMARY
2. Firefox (latest) - HIGH
3. Edge (latest) - MEDIUM

**Test Each Browser**:
- Drag-and-drop works smoothly
- Animations render correctly
- No console errors
- Tooltips display properly

**Known Issues**:
- Safari: vuedraggable may have minor visual glitches (acceptable)

---

### Step 5: Accessibility Testing

#### Keyboard Navigation Test

1. Use only keyboard (no mouse)
2. Tab through categories
3. Arrow keys to navigate fields
4. Space to select field for drag
5. Arrow keys to move field
6. Enter to drop field

**Expected**:
- Focus indicators visible
- Logical tab order
- All interactions possible without mouse

#### Screen Reader Test (Optional)

**Tools**: NVDA (Windows), VoiceOver (Mac)

1. Navigate through categories
2. Listen to field announcements
3. Drag-and-drop operations

**Expected**:
- Category names announced
- Field names announced
- Token counts announced
- Drag operations announced ("moved from X to Y")

---

## Code Snippets

### Snippet 1: Debug Logging (Optional)

Add to composable for debugging:

```javascript
// In useFieldPriority.js

import { watch } from 'vue'

// Watch for changes (debugging)
if (import.meta.env.DEV) {
  watch([priority1Fields, priority2Fields, priority3Fields], () => {
    console.log('[FIELD PRIORITY] State changed:', {
      p1: priority1Fields.value,
      p2: priority2Fields.value,
      p3: priority3Fields.value,
      unassigned: unassignedFields.value
    })
  }, { deep: true })
}
```

### Snippet 2: Advanced Token Calculation

Replace simple estimate with actual product data:

```javascript
// In UserSettings.vue

const estimatedTokens = computed(() => {
  if (!activeProduct.value) return 500

  let total = 0

  // Calculate from actual field content
  priority1Fields.value.forEach(field => {
    const value = getNestedValue(activeProduct.value.config_data, field)
    total += value ? Math.ceil(value.length / 4) : 0
  })

  // ... repeat for P2/P3

  return total + 500 // Add structure overhead
})

function getNestedValue(obj, path) {
  return path.split('.').reduce((acc, part) => acc?.[part], obj)
}
```

---

## Testing Guide

### Automated Tests (Optional)

**File**: `frontend/tests/unit/composables/useFieldPriority.spec.js` (NEW)

```javascript
import { describe, it, expect } from 'vitest'
import { useFieldPriority, ALL_FIELDS } from '@/composables/useFieldPriority'

describe('useFieldPriority', () => {
  it('initializes with empty arrays', () => {
    const { priority1Fields, priority2Fields, priority3Fields } = useFieldPriority()

    expect(priority1Fields.value).toEqual([])
    expect(priority2Fields.value).toEqual([])
    expect(priority3Fields.value).toEqual([])
  })

  it('computes unassigned fields correctly', () => {
    const { priority1Fields, unassignedFields } = useFieldPriority()

    priority1Fields.value = ['tech_stack.languages']

    expect(unassignedFields.value).toHaveLength(ALL_FIELDS.length - 1)
    expect(unassignedFields.value).not.toContain('tech_stack.languages')
  })

  it('loads from config correctly', () => {
    const { priority1Fields, priority2Fields, loadFromConfig } = useFieldPriority()

    loadFromConfig({
      fields: {
        'tech_stack.languages': 1,
        'tech_stack.backend': 2
      }
    })

    expect(priority1Fields.value).toContain('tech_stack.languages')
    expect(priority2Fields.value).toContain('tech_stack.backend')
  })

  it('removes field to unassigned', () => {
    const { priority1Fields, unassignedFields, removeFromPriority } = useFieldPriority()

    priority1Fields.value = ['tech_stack.languages']
    removeFromPriority('tech_stack.languages')

    expect(priority1Fields.value).toHaveLength(0)
    expect(unassignedFields.value).toContain('tech_stack.languages')
  })

  it('exports to config object', () => {
    const { priority1Fields, priority2Fields, toConfigObject } = useFieldPriority()

    priority1Fields.value = ['tech_stack.languages']
    priority2Fields.value = ['tech_stack.backend']

    const config = toConfigObject()

    expect(config.fields['tech_stack.languages']).toBe(1)
    expect(config.fields['tech_stack.backend']).toBe(2)
  })
})
```

**Run Tests**:
```bash
cd frontend
npm run test:unit
```

---

## Deployment Steps

### Pre-Deployment Checklist

- [ ] All manual tests pass
- [ ] Cross-browser tests pass
- [ ] No console errors in any scenario
- [ ] Code reviewed by teammate
- [ ] Handover documentation updated

### Build and Deploy

```bash
# 1. Ensure on feature branch
git checkout -b feature/field-priority-unassigned

# 2. Commit changes
git add frontend/src/composables/useFieldPriority.js
git add frontend/src/views/UserSettings.vue
git commit -m "feat: Add Unassigned category to Field Priority Configuration

- Create useFieldPriority composable for reusable field management
- Add fourth draggable category for unassigned fields
- Update UserSettings.vue with Unassigned container
- Add visual styling (dashed border, grey background)
- Ensure token calculation excludes unassigned fields
- Zero backend changes (fully backward compatible)

Handover: 0052
Estimated Implementation Time: 4-6 hours"

# 3. Push to remote
git push origin feature/field-priority-unassigned

# 4. Create pull request (if using PR workflow)
# Navigate to GitHub/GitLab and create PR

# 5. Merge to main (after approval)
git checkout main
git merge feature/field-priority-unassigned

# 6. Build frontend
cd frontend
npm run build

# 7. Restart server (if needed)
cd ../
python startup.py
```

---

## Rollback Procedure

### If Critical Issues Arise

**Step 1: Immediate Rollback**
```bash
# Revert the commit
git revert <commit-hash>
git push origin main
```

**Step 2: Cleanup (if needed)**
```bash
# Remove composable file
rm frontend/src/composables/useFieldPriority.js

# Restore original UserSettings.vue
git checkout HEAD~1 frontend/src/views/UserSettings.vue
```

**Step 3: Rebuild Frontend**
```bash
cd frontend
npm run build
```

**Step 4: Restart Server**
```bash
python startup.py
```

**Data Impact**: NONE (no database changes, no API changes)

---

## Troubleshooting

### Issue 1: Drag-and-Drop Not Working

**Symptoms**: Fields don't move when dragged

**Cause**: vuedraggable not installed or wrong version

**Solution**:
```bash
cd frontend
npm install vuedraggable@4.1.0
npm run dev
```

### Issue 2: Unassigned Fields Not Showing

**Symptoms**: Unassigned category always empty

**Cause**: Computed property not working correctly

**Debug**:
```javascript
// Add to UserSettings.vue
console.log('Unassigned fields:', unassignedFields.value)
console.log('P1:', priority1Fields.value)
console.log('P2:', priority2Fields.value)
console.log('P3:', priority3Fields.value)
console.log('ALL_FIELDS:', ALL_FIELDS)
```

**Solution**: Check that ALL_FIELDS constant is imported correctly

### Issue 3: Token Count Not Updating

**Symptoms**: Token count doesn't change when moving fields

**Cause**: Token calculation not watching unassigned changes

**Solution**: Ensure `estimatedTokens` computed watches all priority arrays

### Issue 4: Fields Disappear on Drag

**Symptoms**: Field vanishes when dragged

**Cause**: Writable computed setter removing field incorrectly

**Debug**: Check `unassignedFields` setter logic in composable

---

## Completion Checklist

### Before Marking Complete

- [ ] All code changes committed
- [ ] All manual tests pass
- [ ] Cross-browser testing complete
- [ ] No console errors
- [ ] Handover README.md updated with completion notes
- [ ] User-facing documentation updated (if needed)
- [ ] Team notified of new feature

### Final Sign-Off

**Developer**: _______________
**Date**: _______________
**Code Review**: _______________
**Tested By**: _______________

---

**Document Status**: Ready for Use
**Estimated Implementation Time**: 4-6 hours
**Actual Implementation Time**: __________ (to be filled in)

**End of IMPLEMENTATION_GUIDE.md**
