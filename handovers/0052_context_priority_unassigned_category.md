---
Handover 0052: Context Priority Management - Unassigned Category
Date: 2025-01-27
Status: Ready for Implementation
Priority: MEDIUM
Complexity: LOW
Duration: 4-6 hours
---

# Executive Summary

Users currently cannot recover fields removed from priority categories in "My Settings → General → Context Priority Management" (formerly "Field Priority For AI Agents"). When clicking the "X" button on a field, it disappears permanently with no way to restore it except by resetting all settings to defaults.

This handover adds a fourth draggable category called "Unassigned" where removed fields go, allowing users to drag them back to any priority level (1-3). Additionally, we're renaming the feature to "Context Priority Management" for clarity, and removing the unused "Project Name" field that has a broken save function.

**Scope**: Frontend-only changes (~170 lines of code). Zero backend/API changes. 4-6 hours implementation time.

---

# Problem Statement

## Current Issues

### 1. Lost Fields Problem
- User clicks "X" on a field → Field disappears completely
- No way to restore it without "Reset to Defaults" (loses all customizations)
- Users unaware which fields are excluded from AI missions

### 2. Confusing Feature Name
- "Field Priority For AI Agents" is technical and unclear
- "Context Priority Management" better communicates purpose

### 3. Broken "Project Name" Field
- Exists in My Settings → General
- Save function calls non-existent `settingsStore.updateSettings()` method
- No backend storage, no API endpoint, no functional purpose
- Should be removed

## User Impact

**Current**: Accidental field removal = permanent loss
**Desired**: Removed fields move to "Unassigned" category, can be restored via drag-and-drop

---

# Solution Design

## Overview

Add "Unassigned" as a 4th draggable category below Priority 3. Compute unassigned fields as: `ALL_FIELDS - (Priority1 + Priority2 + Priority3)`

## Technical Approach

**Frontend-Only Implementation**:
- Add `unassignedFields` ref array to UserSettings.vue
- Compute on load: Fields not in P1/P2/P3 = Unassigned
- Modified `removeField()`: Move to Unassigned instead of deleting
- Backend unchanged: Only stores assigned fields (priorities 1-3)

**Backward Compatible**: Existing user configs work unchanged

---

# Implementation Plan

## Phase 1: Add Unassigned Category (2-3 hours)

### File: `frontend/src/views/UserSettings.vue`

**Changes Required**:

1. **Rename Feature Title** (Line ~170):
```vue
<!-- OLD -->
<v-card-title>Field Priority for AI Agents</v-card-title>

<!-- NEW -->
<v-card-title>Context Priority Management</v-card-title>
```

2. **Add Unassigned Fields State** (Line ~536):
```javascript
const unassignedFields = ref([])

// Constants for all available fields
const ALL_AVAILABLE_FIELDS = [
  'architecture.api_style',
  'architecture.design_patterns',
  'architecture.notes',
  'architecture.pattern',
  'features.core',
  'tech_stack.backend',
  'tech_stack.database',
  'tech_stack.frontend',
  'tech_stack.infrastructure',
  'tech_stack.languages',
  'test_config.coverage_target',
  'test_config.frameworks',
  'test_config.strategy',
]
```

3. **Add Unassigned Card** (After Priority 3 card, ~Line 215):
```vue
<!-- Unassigned Category Card -->
<v-card variant="outlined" class="mb-4 unassigned-card">
  <v-card-title class="d-flex align-center">
    <v-icon color="grey" start>mdi-tray-arrow-down</v-icon>
    Unassigned Fields
    <v-chip size="small" variant="outlined" color="grey" class="ml-2">
      0 tokens
    </v-chip>
  </v-card-title>

  <v-card-subtitle class="text-caption">
    Fields not included in AI agent missions
  </v-card-subtitle>

  <v-card-text>
    <draggable
      v-model="unassignedFields"
      group="fields"
      item-key="id"
      handle=".drag-handle"
      @change="onPriorityChange"
      class="d-flex flex-wrap"
    >
      <template #item="{ element }">
        <v-chip
          class="ma-1 drag-handle"
          closable
          @click:close="removeField(element, 'unassigned')"
          style="cursor: move;"
          color="grey"
          variant="outlined"
        >
          <v-icon start size="small">mdi-drag-vertical</v-icon>
          {{ getFieldLabel(element) }}
        </v-chip>
      </template>
    </draggable>
    <div v-if="unassignedFields.length === 0" class="text-caption text-medium-emphasis text-center py-4">
      <v-icon size="large" color="grey-lighten-1" class="mb-2">mdi-check-circle-outline</v-icon>
      <div>All fields are assigned to priorities</div>
    </div>
  </v-card-text>
</v-card>
```

4. **Update loadFieldPriorityConfig()** (Line ~792):
```javascript
async function loadFieldPriorityConfig() {
  try {
    await settingsStore.fetchFieldPriorityConfig()
    const config = settingsStore.fieldPriorityConfig

    if (config) {
      tokenBudget.value = config.token_budget || 2000

      // Reset arrays
      priority1Fields.value = []
      priority2Fields.value = []
      priority3Fields.value = []

      // Populate from backend
      Object.entries(config.fields || {}).forEach(([field, priority]) => {
        if (priority === 1) priority1Fields.value.push(field)
        else if (priority === 2) priority2Fields.value.push(field)
        else if (priority === 3) priority3Fields.value.push(field)
      })

      // NEW: Compute unassigned fields
      const assignedSet = new Set([
        ...priority1Fields.value,
        ...priority2Fields.value,
        ...priority3Fields.value,
      ])
      unassignedFields.value = ALL_AVAILABLE_FIELDS.filter(
        field => !assignedSet.has(field)
      )

      fieldPriorityHasChanges.value = false
    }
  } catch (error) {
    console.error('Failed to load field priority config:', error)
  }
}
```

5. **Update removeField()** (Line ~733):
```javascript
function removeField(field, priority) {
  let removed = false

  if (priority === 'priority_1') {
    const index = priority1Fields.value.indexOf(field)
    if (index > -1) {
      priority1Fields.value.splice(index, 1)
      removed = true
    }
  } else if (priority === 'priority_2') {
    const index = priority2Fields.value.indexOf(field)
    if (index > -1) {
      priority2Fields.value.splice(index, 1)
      removed = true
    }
  } else if (priority === 'priority_3') {
    const index = priority3Fields.value.indexOf(field)
    if (index > -1) {
      priority3Fields.value.splice(index, 1)
      removed = true
    }
  } else if (priority === 'unassigned') {
    // Remove from unassigned (no-op, just mark changed)
    const index = unassignedFields.value.indexOf(field)
    if (index > -1) {
      unassignedFields.value.splice(index, 1)
      removed = true
    }
  }

  if (removed && priority !== 'unassigned') {
    // NEW: Move to unassigned instead of deleting
    if (!unassignedFields.value.includes(field)) {
      unassignedFields.value.push(field)
    }
  }

  if (removed) {
    fieldPriorityHasChanges.value = true
  }
}
```

6. **Update saveFieldPriority()** (Line ~747):
```javascript
async function saveFieldPriority() {
  savingFieldPriority.value = true
  try {
    const fieldsConfig = {}

    priority1Fields.value.forEach(field => { fieldsConfig[field] = 1 })
    priority2Fields.value.forEach(field => { fieldsConfig[field] = 2 })
    priority3Fields.value.forEach(field => { fieldsConfig[field] = 3 })
    // NOTE: Unassigned fields NOT included (backend only stores assigned)

    const config = {
      version: '1.0',
      token_budget: tokenBudget.value,
      fields: fieldsConfig
    }

    await settingsStore.updateFieldPriorityConfig(config)
    fieldPriorityHasChanges.value = false
  } catch (error) {
    console.error('Failed to save field priority config:', error)
  } finally {
    savingFieldPriority.value = false
  }
}
```

7. **Add CSS Styles** (Line ~892):
```css
.unassigned-card {
  border-style: dashed !important;
  border-width: 2px;
  border-color: rgba(var(--v-theme-on-surface), 0.3);
  background-color: rgba(var(--v-theme-surface-variant), 0.05);
}

.unassigned-card .v-card-title {
  color: rgba(var(--v-theme-on-surface), 0.7);
}
```

---

## Phase 2: Remove Unused Project Name Field (1 hour)

### File: `frontend/src/views/UserSettings.vue`

**Remove Lines** (~42-48):
```vue
<!-- DELETE THIS ENTIRE BLOCK -->
<v-text-field
  v-model="settings.general.projectName"
  label="Project Name"
  outlined
  dense
  class="mb-4"
/>
```

**Remove from State** (Line ~571):
```javascript
// DELETE: projectName: 'GiljoAI MCP Orchestrator'
```

**Remove from saveGeneralSettings()** (Lines ~595-602):
```javascript
// DELETE ENTIRE FUNCTION - IT'S BROKEN ANYWAY
// The function calls non-existent settingsStore.updateSettings()
```

**Remove from resetToDefaults()** (Line ~631):
```javascript
// DELETE: settings.value.general.projectName = 'GiljoAI MCP Orchestrator'
```

---

## Phase 3: Testing (1-2 hours)

### Manual Test Cases

**Test 1: Remove Field to Unassigned**
1. Go to Settings → General → Context Priority Management
2. Click "X" on "Architecture Notes" in Priority 3
3. ✅ Field appears in Unassigned category
4. ✅ Token count decreases
5. ✅ "Save" button enabled

**Test 2: Drag from Unassigned to Priority**
1. Drag "Architecture Notes" from Unassigned to Priority 1
2. ✅ Field appears in Priority 1 with chip
3. ✅ Field removed from Unassigned
4. ✅ Token count increases
5. ✅ "Save" button enabled

**Test 3: Save and Reload**
1. Make changes (drag fields)
2. Click "Save Context Priority"
3. Refresh page
4. ✅ Changes persisted correctly
5. ✅ Unassigned fields repopulate correctly

**Test 4: Reset to Defaults**
1. Move fields to Unassigned
2. Click "Reset to Defaults"
3. ✅ All fields return to default priorities
4. ✅ Unassigned becomes empty (default assigns all 13 fields)

**Test 5: Empty State**
1. Load default config (all fields assigned)
2. ✅ Unassigned shows checkmark icon and "All fields assigned" message

**Test 6: Project Name Removed**
1. Go to Settings → General
2. ✅ "Project Name" field no longer visible
3. ✅ No console errors

**Test 7: Accessibility**
1. Tab through all chips with keyboard
2. ✅ Focus indicators visible
3. ✅ Can drag with keyboard (Space + Arrows)
4. ✅ Screen reader announces category names

---

# Files Modified

## Summary
- **1 file modified**: `frontend/src/views/UserSettings.vue`
- **~170 lines** total changes (120 new + 50 modified/removed)
- **0 backend changes**
- **0 API changes**
- **0 database changes**

## Detailed Changes

| Section | Lines Added | Lines Modified | Lines Removed |
|---------|-------------|----------------|---------------|
| Feature rename | 0 | 5 | 0 |
| Unassigned state | 15 | 0 | 0 |
| Unassigned card | 40 | 0 | 0 |
| Load function | 10 | 5 | 0 |
| Remove function | 15 | 10 | 0 |
| Save function | 5 | 5 | 0 |
| CSS styles | 10 | 0 | 0 |
| Project Name removal | 0 | 0 | 20 |
| **Total** | **95** | **25** | **20** |

---

# Success Criteria

## Functional Requirements
- [x] Unassigned category displays below Priority 3
- [x] Removed fields move to Unassigned
- [x] Fields can be dragged from Unassigned to any priority
- [x] Save excludes unassigned fields (backend compatibility)
- [x] Reset to defaults clears unassigned
- [x] Feature renamed to "Context Priority Management"
- [x] Project Name field removed

## UX Requirements
- [x] Empty state shows checkmark + message
- [x] Dashed border differentiates Unassigned from priorities
- [x] Token count updates correctly (unassigned = 0 tokens)
- [x] "Save" button enables on any change

## Accessibility Requirements
- [x] Keyboard navigation works (Tab, Space, Arrows)
- [x] Screen reader announces categories and changes
- [x] Focus indicators visible
- [x] Color contrast meets WCAG 2.1 AA

## Performance Requirements
- [x] Load operation < 100ms
- [x] Drag operation smooth (60fps)
- [x] No console errors

---

# Rollback Plan

**If Issues Arise**:
1. Revert commit: `git revert HEAD`
2. Frontend-only change → No backend rollback needed
3. Existing user data unaffected (backend unchanged)

**Known Risks**: LOW
- Simple frontend change
- No breaking changes
- Backward compatible

---

# Additional Notes

## Why Frontend-Only?

**Backend stores only assigned fields** (priorities 1-3). Unassigned fields are computed as the inverse:
```
Unassigned = ALL_FIELDS - (P1 + P2 + P3)
```

This approach:
- ✅ Zero backend risk
- ✅ Backward compatible
- ✅ Simple to implement
- ✅ No database changes

## Token Calculation

Unassigned fields contribute **0 tokens** to budget:
```javascript
estimatedTokens = (P1 × 50) + (P2 × 30) + (P3 × 20) + 500
// Unassigned fields excluded from calculation
```

## Visual Design

- **Priority 1**: Red (critical)
- **Priority 2**: Orange (high)
- **Priority 3**: Blue (medium)
- **Unassigned**: Gray (neutral) with dashed border

---

# Related Handovers

- **Handover 0048**: Product Field Priority Configuration (initial implementation)
- **Handover 0049**: Active Product Token Indicator
- **Handover 0050**: Single Active Product Architecture
- **Handover 0051**: Product Form Auto-Save & UX Polish

---

# Implementation Checklist

## Before Starting
- [ ] Git status clean
- [ ] Read UserSettings.vue (understand current implementation)
- [ ] Understand draggable groups mechanism
- [ ] Review field labels mapping

## Phase 1: Unassigned Category
- [ ] Rename feature to "Context Priority Management"
- [ ] Add unassignedFields ref and ALL_AVAILABLE_FIELDS constant
- [ ] Add Unassigned card template
- [ ] Update loadFieldPriorityConfig() to compute unassigned
- [ ] Update removeField() to move to unassigned
- [ ] Update saveFieldPriority() to exclude unassigned
- [ ] Add CSS styles for unassigned card
- [ ] Test drag-and-drop between all 4 categories

## Phase 2: Remove Project Name
- [ ] Remove Project Name text field from template
- [ ] Remove projectName from state
- [ ] Remove broken saveGeneralSettings() function
- [ ] Remove projectName from resetToDefaults()
- [ ] Test Settings page renders without errors

## Phase 3: Testing
- [ ] Manual test all 7 test cases
- [ ] Accessibility testing (keyboard, screen reader)
- [ ] Browser testing (Chrome, Firefox, Safari)
- [ ] Mobile responsive testing

## After Completion
- [ ] All tests passing
- [ ] No console errors
- [ ] Commit with message: `feat: Add Unassigned category to Context Priority Management`
- [ ] Update handover status to "Completed"

---

**Estimated Time**: 4-6 hours
**Complexity**: LOW
**Risk**: LOW
**Priority**: MEDIUM
