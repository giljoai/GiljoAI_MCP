# Handover 0052: Field Priority Unassigned Category - Technical Architecture

**Document Version**: 1.0
**Date**: 2025-10-27
**Status**: Design Approved

---

## Table of Contents

1. [Current Architecture](#current-architecture)
2. [Proposed Architecture](#proposed-architecture)
3. [Data Flow](#data-flow)
4. [Component Modifications](#component-modifications)
5. [State Management](#state-management)
6. [API Contract](#api-contract)
7. [Testing Strategy](#testing-strategy)

---

## Current Architecture

### System Overview

The Field Priority Configuration system (Handover 0048) allows users to organize 13 product configuration fields into three priority categories. This determines which fields are included in AI agent missions and affects token budget allocation.

```
┌──────────────────────────────────────────────────────────────┐
│                    Current Architecture                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Frontend: UserSettings.vue                                  │
│  ┌────────────────────────────────────────────────────┐     │
│  │                                                    │     │
│  │  ALL_FIELDS (13 fields, constant)                 │     │
│  │         ↓                                          │     │
│  │  User drags fields to P1/P2/P3                    │     │
│  │         ↓                                          │     │
│  │  priority1Fields: ref([...])                      │     │
│  │  priority2Fields: ref([...])                      │     │
│  │  priority3Fields: ref([...])                      │     │
│  │         ↓                                          │     │
│  │  assignedFields = P1 + P2 + P3                    │     │
│  │  removedFields = ALL_FIELDS - assignedFields      │     │
│  │         ↓                                          │     │
│  │  removedFields COMPUTED BUT NOT SHOWN ❌           │     │
│  │                                                    │     │
│  └────────────────────────────────────────────────────┘     │
│                         ↓                                    │
│  Save to Backend:                                            │
│  {                                                           │
│    "field_priority_config": {                                │
│      "fields": {                                             │
│        "tech_stack.languages": 1,                            │
│        "tech_stack.backend": 1,                              │
│        "tech_stack.frontend": 2,                             │
│        ...                                                   │
│      }                                                       │
│    }                                                         │
│  }                                                           │
│  ↓                                                           │
│  Removed fields: NO ENTRY in database (implicit)             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Current Component Structure

**File**: `frontend/src/views/UserSettings.vue`

**State Management**:
```javascript
// Inline reactive state
const priority1Fields = ref([])
const priority2Fields = ref([])
const priority3Fields = ref([])

// Computed (NOT DISPLAYED)
const removedFields = computed(() => {
  const assigned = new Set([
    ...priority1Fields.value,
    ...priority2Fields.value,
    ...priority3Fields.value
  ])
  return ALL_FIELDS.filter(f => !assigned.has(f))
})
```

**Template Structure**:
```vue
<v-card>
  <!-- Priority 1 Container -->
  <draggable v-model="priority1Fields">
    <div v-for="field in priority1Fields">
      {{ field }}
      <v-btn @click="removeField(field, 1)">✕</v-btn>
    </div>
  </draggable>

  <!-- Priority 2 Container -->
  <draggable v-model="priority2Fields">...</draggable>

  <!-- Priority 3 Container -->
  <draggable v-model="priority3Fields">...</draggable>

  <!-- NO UNASSIGNED CONTAINER ❌ -->
</v-card>
```

### Problems with Current Architecture

1. **User Confusion**: Fields disappear when removed (no visual feedback on where they went)
2. **No Recovery Path**: Cannot undo field removal without page reload
3. **Incomplete Field Visibility**: User cannot see which fields are available
4. **Inconsistent UX**: Remove button behaves like "delete" not "move"

---

## Proposed Architecture

### Enhanced System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Proposed Architecture                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Frontend: UserSettings.vue                                  │
│  ┌────────────────────────────────────────────────────┐     │
│  │                                                    │     │
│  │  useFieldPriority() composable                     │     │
│  │  ┌──────────────────────────────────────────┐     │     │
│  │  │                                          │     │     │
│  │  │  ALL_FIELDS (13 fields, constant)       │     │     │
│  │  │         ↓                                │     │     │
│  │  │  priority1Fields: ref([...])            │     │     │
│  │  │  priority2Fields: ref([...])            │     │     │
│  │  │  priority3Fields: ref([...])            │     │     │
│  │  │         ↓                                │     │     │
│  │  │  unassignedFields: computed(() => {     │     │     │
│  │  │    ALL_FIELDS - (P1 + P2 + P3)          │     │     │
│  │  │  })                                      │     │     │
│  │  │         ↓                                │     │     │
│  │  │  DISPLAYED IN UI ✅                       │     │     │
│  │  │                                          │     │     │
│  │  └──────────────────────────────────────────┘     │     │
│  │                                                    │     │
│  └────────────────────────────────────────────────────┘     │
│                         ↓                                    │
│  Template: 4 draggable containers                            │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Priority 1 Container                              │     │
│  │  Priority 2 Container                              │     │
│  │  Priority 3 Container                              │     │
│  │  Unassigned Container (NEW) ✅                      │     │
│  └────────────────────────────────────────────────────┘     │
│                         ↓                                    │
│  Save to Backend: (UNCHANGED)                                │
│  {                                                           │
│    "field_priority_config": {                                │
│      "fields": {                                             │
│        "tech_stack.languages": 1,                            │
│        "tech_stack.backend": 1                               │
│      }                                                       │
│    }                                                         │
│  }                                                           │
│  ↓                                                           │
│  Unassigned fields: NO ENTRY in database (implicit)          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Key Architectural Changes

#### 1. Composable Extraction

**Before**: All logic inline in UserSettings.vue (~300 lines)

**After**: Logic extracted to reusable composable (~120 lines)

**Benefits**:
- Separation of concerns (UI vs logic)
- Testable business logic
- Reusable in other components (if needed)
- Cleaner component code

#### 2. Computed Unassigned Category

**Implementation**:
```javascript
// frontend/src/composables/useFieldPriority.js

const unassignedFields = computed(() => {
  const assigned = new Set([
    ...priority1Fields.value,
    ...priority2Fields.value,
    ...priority3Fields.value
  ])
  return ALL_FIELDS.filter(field => !assigned.has(field))
})
```

**Characteristics**:
- **Always Accurate**: Computed from single source of truth (ALL_FIELDS)
- **No Additional State**: Derived from existing refs
- **Reactive**: Updates automatically when P1/P2/P3 change
- **Performance**: O(n) where n = 13 (trivial)

#### 3. Four Draggable Containers

**Template Structure**:
```vue
<v-card>
  <!-- Priority 1 -->
  <draggable v-model="priority1Fields" group="fields">
    ...
  </draggable>

  <!-- Priority 2 -->
  <draggable v-model="priority2Fields" group="fields">
    ...
  </draggable>

  <!-- Priority 3 -->
  <draggable v-model="priority3Fields" group="fields">
    ...
  </draggable>

  <!-- Unassigned (NEW) -->
  <draggable v-model="unassignedFields" group="fields">
    ...
  </draggable>
</v-card>
```

**Key Properties**:
- **group="fields"**: Allows dragging between all containers
- **v-model binding**: vuedraggable handles array mutations
- **Same UX**: Unassigned behaves like other categories

---

## Data Flow

### 1. Initial Load Flow

```
User opens Settings → General
    ↓
fetchUserSettings() API call
    ↓
GET /api/users/me/settings
    ↓
Response: { field_priority_config: { fields: {...} } }
    ↓
Parse into priority arrays:
  - P1: fields where value = 1
  - P2: fields where value = 2
  - P3: fields where value = 3
    ↓
Compute unassigned:
  - Unassigned = ALL_FIELDS - (P1 + P2 + P3)
    ↓
Render 4 draggable containers
```

### 2. Drag Field Flow

**Scenario**: User drags "Database" from P2 to Unassigned

```
User starts drag (Database field)
    ↓
vuedraggable starts tracking
    ↓
User drops in Unassigned container
    ↓
vuedraggable updates arrays:
  - Remove "tech_stack.database" from priority2Fields
  - Add "tech_stack.database" to unassignedFields
    ↓
Vue reactivity triggers:
  - unassignedFields computed property re-evaluates
  - Token calculation updates (excludes Database tokens)
  - UI re-renders
    ↓
User sees field in Unassigned category
```

**Implementation Detail**: Since `unassignedFields` is computed (not a ref), vuedraggable cannot directly modify it. We must use a **workaround**:

**Solution 1: Make Unassigned a Ref (NOT Recommended)**
```javascript
const unassignedFields = ref([])

// Manually sync after every change
watch([priority1Fields, priority2Fields, priority3Fields], () => {
  unassignedFields.value = computeUnassigned()
}, { deep: true })
```

**Problem**: Duplicate state, can get out of sync

**Solution 2: Use :list Prop Instead of v-model (RECOMMENDED)**
```vue
<draggable
  :list="unassignedFields"
  :move="onUnassignedMove"
  group="fields"
>
```

```javascript
function onUnassignedMove(evt) {
  const { from, to, draggedContext } = evt
  const field = draggedContext.element

  // Remove from source category
  if (from !== to) {
    removeFromCategory(field, getSourceCategory(from))
  }

  return false // Prevent default (we handle manually)
}
```

**Problem**: More complex, requires manual array management

**Solution 3: Hybrid Approach (SELECTED)**

Use `v-model` with a **writable computed**:

```javascript
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
    // When drag-and-drop adds field to unassigned,
    // remove it from its current priority category
    const oldValue = unassignedFields.value
    const added = newValue.filter(f => !oldValue.includes(f))
    const removed = oldValue.filter(f => !newValue.includes(f))

    // Remove added fields from priority categories
    added.forEach(field => {
      priority1Fields.value = priority1Fields.value.filter(f => f !== field)
      priority2Fields.value = priority2Fields.value.filter(f => f !== field)
      priority3Fields.value = priority3Fields.value.filter(f => f !== field)
    })

    // Add removed fields to target category (handled by vuedraggable)
  }
})
```

**Benefits**:
- Works seamlessly with vuedraggable
- No manual event handling
- Reactive and automatic

### 3. Remove Button Flow

**Scenario**: User clicks [x] button on "Frontend" field in P2

```
User clicks [x] button
    ↓
removeField(field, category) called
    ↓
Remove field from priority array:
  priority2Fields.value = priority2Fields.value.filter(f => f !== field)
    ↓
Vue reactivity triggers:
  - unassignedFields re-computes (now includes "Frontend")
  - Token count updates
  - UI re-renders
    ↓
Field appears in Unassigned category
```

**Implementation**:
```javascript
function removeField(field, category) {
  switch(category) {
    case 1: priority1Fields.value = priority1Fields.value.filter(f => f !== field); break;
    case 2: priority2Fields.value = priority2Fields.value.filter(f => f !== field); break;
    case 3: priority3Fields.value = priority3Fields.value.filter(f => f !== field); break;
  }
}
```

### 4. Save Configuration Flow

```
User clicks "Save Changes"
    ↓
Build config object:
  config = {
    version: "1.0",
    token_budget: 2000,
    fields: {}
  }
    ↓
Add P1 fields: config.fields[field] = 1
Add P2 fields: config.fields[field] = 2
Add P3 fields: config.fields[field] = 3
    ↓
Unassigned fields: NO ENTRY (implicit)
    ↓
PATCH /api/users/me/settings
    ↓
Backend saves to database
    ↓
Success response
    ↓
Show toast: "Field priorities saved successfully"
```

**Example Saved Config**:
```json
{
  "field_priority_config": {
    "version": "1.0",
    "token_budget": 2000,
    "fields": {
      "tech_stack.languages": 1,
      "tech_stack.backend": 1,
      "tech_stack.frontend": 2,
      "tech_stack.database": 2,
      "architecture.pattern": 3
    }
  }
}
```

**Unassigned Fields**: Any field NOT in `fields` object (8 fields in this example).

---

## Component Modifications

### 1. New Composable: useFieldPriority.js

**File**: `frontend/src/composables/useFieldPriority.js`

**Structure**:
```javascript
/**
 * Field Priority Management Composable
 *
 * Manages the four-category field priority system:
 * - Priority 1 (Always Included)
 * - Priority 2 (High Priority)
 * - Priority 3 (Medium Priority)
 * - Unassigned (Not Included)
 */
import { ref, computed } from 'vue'

// Constants
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

export function useFieldPriority(initialConfig = null) {
  // State
  const priority1Fields = ref([])
  const priority2Fields = ref([])
  const priority3Fields = ref([])

  // Initialize from config
  if (initialConfig) {
    loadFromConfig(initialConfig)
  }

  // Computed unassigned category
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
      // Handle vuedraggable updates
      const oldValue = unassignedFields.value
      const added = newValue.filter(f => !oldValue.includes(f))

      // Remove from priority categories
      added.forEach(field => {
        priority1Fields.value = priority1Fields.value.filter(f => f !== field)
        priority2Fields.value = priority2Fields.value.filter(f => f !== field)
        priority3Fields.value = priority3Fields.value.filter(f => f !== field)
      })
    }
  })

  // Methods
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

  function moveToCategory(field, targetCategory) {
    // Remove from all categories first
    priority1Fields.value = priority1Fields.value.filter(f => f !== field)
    priority2Fields.value = priority2Fields.value.filter(f => f !== field)
    priority3Fields.value = priority3Fields.value.filter(f => f !== field)

    // Add to target category
    if (targetCategory === 1) priority1Fields.value.push(field)
    else if (targetCategory === 2) priority2Fields.value.push(field)
    else if (targetCategory === 3) priority3Fields.value.push(field)
    // If targetCategory is null/undefined, field goes to Unassigned
  }

  function removeFromPriority(field) {
    priority1Fields.value = priority1Fields.value.filter(f => f !== field)
    priority2Fields.value = priority2Fields.value.filter(f => f !== field)
    priority3Fields.value = priority3Fields.value.filter(f => f !== field)
    // Field automatically appears in Unassigned (computed)
  }

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

    // Constants
    ALL_FIELDS
  }
}
```

**Key Design Decisions**:
- **Writable Computed for Unassigned**: Allows vuedraggable integration
- **Single Source of Truth**: ALL_FIELDS constant
- **Composable Pattern**: Reusable, testable, clean separation of concerns

### 2. Modified Component: UserSettings.vue

**Changes Required**:

#### A. Script Setup
```javascript
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useFieldPriority } from '@/composables/useFieldPriority'
import draggable from 'vuedraggable'

const {
  priority1Fields,
  priority2Fields,
  priority3Fields,
  unassignedFields,
  loadFromConfig,
  removeFromPriority,
  toConfigObject,
  ALL_FIELDS
} = useFieldPriority()

// Existing state...
const userSettings = ref(null)

onMounted(async () => {
  // Fetch user settings
  const response = await api.users.getSettings()
  userSettings.value = response.data

  // Load field priority config
  if (response.data.field_priority_config) {
    loadFromConfig(response.data.field_priority_config)
  }
})

async function saveSettings() {
  const config = toConfigObject()
  await api.users.updateSettings({
    field_priority_config: config
  })
}
</script>
```

#### B. Template Addition
```vue
<template>
  <!-- Existing P1/P2/P3 containers... -->

  <!-- NEW: Unassigned Category -->
  <v-card variant="outlined" class="mb-4" color="grey-lighten-4">
    <v-card-title class="d-flex align-center">
      <span>Unassigned</span>
      <v-chip size="small" variant="text" class="ml-2">
        Not Included in Missions
      </v-chip>
      <v-tooltip location="top">
        <template #activator="{ props }">
          <v-icon v-bind="props" size="small" class="ml-1">
            mdi-information
          </v-icon>
        </template>
        <span>
          Fields in this category are NOT sent to AI agents.
          Drag to a priority category to include them in missions.
        </span>
      </v-tooltip>
    </v-card-title>

    <v-card-text>
      <draggable
        v-model="unassignedFields"
        group="fields"
        item-key="field"
        class="field-list field-list--unassigned"
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

      <div v-if="unassignedFields.length === 0" class="text-center text-grey">
        All fields assigned to priority categories
      </div>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.field-list--unassigned {
  border: 2px dashed #bdbdbd;
  border-radius: 4px;
  min-height: 60px;
  padding: 8px;
  background-color: #fafafa;
}

.field-list--unassigned:empty::before {
  content: 'Drag fields here to remove from missions';
  color: #9e9e9e;
  font-size: 0.875rem;
}
</style>
```

---

## State Management

### Reactivity Graph

```
ALL_FIELDS (constant)
    ↓
priority1Fields (ref) ───┐
priority2Fields (ref) ───┼──→ unassignedFields (computed)
priority3Fields (ref) ───┘         ↓
    ↓                          UI Rendering
Token Calculation
```

### State Transitions

**Initial State**:
```javascript
P1: ['tech_stack.languages', 'tech_stack.backend']
P2: ['tech_stack.frontend', 'tech_stack.database']
P3: ['architecture.pattern']
Unassigned: [8 remaining fields]
```

**After Drag "Database" from P2 to Unassigned**:
```javascript
P1: ['tech_stack.languages', 'tech_stack.backend']
P2: ['tech_stack.frontend']  // Database removed
P3: ['architecture.pattern']
Unassigned: [9 fields]  // Database added (computed)
```

**After Drag "Features.Core" from Unassigned to P1**:
```javascript
P1: ['tech_stack.languages', 'tech_stack.backend', 'features.core']
P2: ['tech_stack.frontend']
P3: ['architecture.pattern']
Unassigned: [8 fields]  // Features.Core removed (computed)
```

---

## API Contract

### No Backend Changes Required

This implementation is **fully backward compatible** with existing API (Handover 0048).

**Existing Endpoints Used**:

#### GET /api/v1/users/me/settings

**Response** (unchanged):
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "field_priority_config": {
    "version": "1.0",
    "token_budget": 2000,
    "fields": {
      "tech_stack.languages": 1,
      "tech_stack.backend": 1,
      "tech_stack.frontend": 2,
      "tech_stack.database": 2
    }
  }
}
```

**Unassigned Fields**: Computed by frontend as `ALL_FIELDS - Object.keys(fields)`

#### PATCH /api/v1/users/me/settings

**Request** (unchanged):
```json
{
  "field_priority_config": {
    "version": "1.0",
    "token_budget": 2000,
    "fields": {
      "tech_stack.languages": 1,
      "tech_stack.backend": 1
    }
  }
}
```

**Unassigned Fields**: Any field NOT in request body is implicitly unassigned.

---

## Testing Strategy

### Unit Tests (Optional)

**File**: `tests/unit/composables/useFieldPriority.spec.js`

**Test Cases**:
1. Initial load from config
2. Computed unassigned fields
3. Move field between categories
4. Remove field to unassigned
5. Export to config object

**Example Test**:
```javascript
import { describe, it, expect } from 'vitest'
import { useFieldPriority, ALL_FIELDS } from '@/composables/useFieldPriority'

describe('useFieldPriority', () => {
  it('computes unassigned fields correctly', () => {
    const { priority1Fields, priority2Fields, priority3Fields, unassignedFields } = useFieldPriority()

    priority1Fields.value = ['tech_stack.languages']
    priority2Fields.value = ['tech_stack.backend']
    priority3Fields.value = []

    expect(unassignedFields.value).toHaveLength(ALL_FIELDS.length - 2)
    expect(unassignedFields.value).not.toContain('tech_stack.languages')
    expect(unassignedFields.value).not.toContain('tech_stack.backend')
  })

  it('removes field to unassigned', () => {
    const { priority1Fields, unassignedFields, removeFromPriority } = useFieldPriority()

    priority1Fields.value = ['tech_stack.languages']
    removeFromPriority('tech_stack.languages')

    expect(priority1Fields.value).toHaveLength(0)
    expect(unassignedFields.value).toContain('tech_stack.languages')
  })
})
```

### Integration Tests (Manual)

See **TESTING_GUIDE.md** for comprehensive test scenarios.

---

## Performance Considerations

### Computational Complexity

**Unassigned Computation**:
```javascript
O(n) where n = 13 (ALL_FIELDS.length)
```

**Worst Case**: 13 iterations per reactive update

**Impact**: Negligible (<1ms on modern browsers)

### Reactivity Performance

**Vue 3 Reactivity**: Optimized for small arrays (13 fields trivial)

**Expected Performance**:
- Drag operation: <50ms
- Remove button: <20ms
- Token recalculation: <30ms
- Total user-perceived latency: <100ms ✅

### Memory Overhead

**Additional State**:
- `unassignedFields` computed: No additional memory (computed on-the-fly)
- Total memory: ~500 bytes (negligible)

---

## Backward Compatibility

### Existing User Configurations

**Scenario**: User has saved field priority config before this handover.

**Load Behavior**:
```javascript
// Existing config (database)
{
  "fields": {
    "tech_stack.languages": 1,
    "tech_stack.backend": 2
  }
}

// Frontend loading
loadFromConfig(config)
  → P1: ['tech_stack.languages']
  → P2: ['tech_stack.backend']
  → P3: []
  → Unassigned: [11 remaining fields] ✅ (computed correctly)
```

**Result**: Fully backward compatible. No migration needed.

### Future Extensibility

**If Field Count Grows (e.g., to 20+ fields)**:

Current architecture supports:
- Search/filter fields
- Virtualized scrolling (if needed)
- Bulk operations

**No architectural changes needed** - system scales naturally.

---

## Security Considerations

### Client-Side Only

**No Security Risks**:
- No sensitive data exposed (field names are static, known constants)
- No new API endpoints (zero attack surface)
- No user input validation needed (drag-and-drop of known values)

### XSS Protection

Vue 3 automatic escaping handles field name rendering safely.

---

## Accessibility Considerations

### Keyboard Navigation

**Required**:
- Tab through priority categories
- Arrow keys to navigate fields within category
- Enter/Space to select field for drag
- Escape to cancel drag operation

**Implementation**: vuedraggable supports keyboard navigation by default.

### Screen Reader Support

**ARIA Labels**:
```vue
<draggable
  v-model="unassignedFields"
  role="list"
  aria-label="Unassigned fields - not included in AI missions"
>
  <template #item="{ element }">
    <v-chip
      role="listitem"
      :aria-label="`Field: ${formatFieldName(element)}`"
    >
      {{ formatFieldName(element) }}
    </v-chip>
  </template>
</draggable>
```

### Focus Indicators

**Requirement**: Visible focus ring when navigating with keyboard.

**Implementation**: Vuetify default styles (no additional work).

---

## Rollback Plan

**If Critical Issues Arise**:

1. **Immediate Rollback**:
   ```bash
   git revert <commit-hash>
   ```

2. **Cleanup**:
   ```bash
   rm frontend/src/composables/useFieldPriority.js
   ```

3. **Restore Original**:
   ```bash
   git checkout HEAD~1 frontend/src/views/UserSettings.vue
   ```

**Data Impact**: NONE (no database changes)

**User Impact**: Users revert to previous behavior (fields disappear when removed)

---

## Deployment Checklist

- [ ] Create `frontend/src/composables/useFieldPriority.js`
- [ ] Update `frontend/src/views/UserSettings.vue`
- [ ] Test all drag-and-drop scenarios
- [ ] Test token calculation accuracy
- [ ] Test save/load cycle
- [ ] Cross-browser testing (Chrome, Firefox, Edge)
- [ ] Accessibility testing (keyboard navigation)
- [ ] Performance profiling (ensure <100ms latency)
- [ ] Code review
- [ ] Commit with descriptive message
- [ ] Update handover with completion notes

---

**Document Status**: Approved for Implementation
**Next Document**: See `IMPLEMENTATION_GUIDE.md` for step-by-step instructions

**End of ARCHITECTURE.md**
