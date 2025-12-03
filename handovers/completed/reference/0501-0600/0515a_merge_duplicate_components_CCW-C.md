# Handover 0515a: Merge Duplicate Components [CCW]

**Execution Environment**: CCW (Claude Code Web)
**Duration**: 1-2 days
**Branch Name**: `ccw-0515a-merge-components`
**Can Run Parallel With**: 0515b

---

## Why CCW?
- Pure frontend Vue component work
- No database access needed
- No backend testing required
- Can leverage cloud tokens for large refactoring

---

## Scope

Consolidate all duplicate Vue components into single, configurable versions.

### Components to Consolidate

#### 1. Agent Cards (5 variants → 1)
**Current Files**:
```
frontend/src/components/agents/
├── AgentCard.vue (KEEP - make configurable)
├── AgentCardMinimal.vue (DELETE - merge into AgentCard)
├── AgentCardDetailed.vue (DELETE - merge into AgentCard)
├── AgentJobCard.vue (DELETE - merge into AgentCard)
└── AgentCardCompact.vue (DELETE if exists)
```

**New AgentCard.vue Props**:
```javascript
props: {
  agent: Object,
  variant: {
    type: String,
    default: 'default',
    validator: (v) => ['minimal', 'detailed', 'compact', 'job'].includes(v)
  },
  showStatus: { type: Boolean, default: true },
  showActions: { type: Boolean, default: true },
  showMetrics: { type: Boolean, default: false }
}
```

#### 2. Status Badges (3 variants → 1)
**Current Files**:
```
frontend/src/components/common/
├── StatusBadge.vue (KEEP - make configurable)
├── ProjectStatusBadge.vue (DELETE)
└── AgentStatusBadge.vue (DELETE)
```

#### 3. Loading Spinners (4 variants → 1)
**Current Files**:
```
frontend/src/components/common/
├── LoadingSpinner.vue (KEEP)
├── LoadingOverlay.vue (DELETE)
├── ProgressSpinner.vue (DELETE)
└── Spinner.vue (DELETE)
```

#### 4. Modal/Dialog Components
**Current Files**:
```
frontend/src/components/common/
├── BaseModal.vue (KEEP as base)
├── ConfirmDialog.vue (KEEP - extends BaseModal)
├── SimpleModal.vue (DELETE)
└── DialogModal.vue (DELETE)
```

### Update All Imports

After consolidation, update ALL component imports across the codebase:

```javascript
// OLD
import AgentCardMinimal from '@/components/agents/AgentCardMinimal.vue'

// NEW
import AgentCard from '@/components/agents/AgentCard.vue'
// Use with variant prop: <AgentCard :agent="agent" variant="minimal" />
```

**Files likely needing import updates**:
- `frontend/src/views/Projects.vue`
- `frontend/src/views/Dashboard.vue`
- `frontend/src/components/projects/*.vue`
- `frontend/src/components/orchestration/*.vue`

---

## Implementation Steps

### Step 1: Analyze Current Usage
```bash
# Find all imports of components to be deleted
grep -r "AgentCardMinimal\|AgentCardDetailed\|AgentJobCard" frontend/src/
grep -r "ProjectStatusBadge\|AgentStatusBadge" frontend/src/
grep -r "LoadingOverlay\|ProgressSpinner\|Spinner" frontend/src/
```

### Step 2: Create Unified Components

**AgentCard.vue Template Structure**:
```vue
<template>
  <v-card :class="cardClasses">
    <!-- Minimal variant -->
    <template v-if="variant === 'minimal'">
      <v-card-title>{{ agent.name }}</v-card-title>
      <StatusBadge :status="agent.status" />
    </template>

    <!-- Detailed variant -->
    <template v-else-if="variant === 'detailed'">
      <!-- Full agent details -->
    </template>

    <!-- Job variant -->
    <template v-else-if="variant === 'job'">
      <!-- Job-specific layout -->
    </template>

    <!-- Default variant -->
    <template v-else>
      <!-- Standard layout -->
    </template>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  agent: Object,
  variant: String,
  // ... other props
})

const cardClasses = computed(() => ({
  'agent-card': true,
  [`agent-card--${props.variant}`]: true
}))
</script>
```

### Step 3: Test Each Consolidation

For each consolidated component:
1. Ensure all variants render correctly
2. Props are properly passed
3. Events still emit correctly
4. Styles apply properly

### Step 4: Update Imports Systematically

Use find-and-replace carefully:
1. Update import statements
2. Update component registrations
3. Add variant props where needed
4. Test each updated component

---

## Success Criteria

- [ ] Zero duplicate component files
- [ ] All imports updated and working
- [ ] All variants accessible via props
- [ ] No visual regressions
- [ ] Component count reduced by ~15 files
- [ ] Build succeeds with no errors
- [ ] No console errors in browser

---

## Testing Commands (Run Locally After Merge)

```bash
# Build should succeed
npm run build

# No lint errors
npm run lint

# Component tests pass (if exist)
npm run test:unit
```

---

## Common Issues & Solutions

**Issue**: Component variant doesn't match original exactly
**Solution**: Add variant-specific props/slots as needed

**Issue**: Import not found errors
**Solution**: Ensure all old imports are updated

**Issue**: Style differences between variants
**Solution**: Use scoped styles with variant classes

---

## Files to Delete After Success

```
frontend/src/components/agents/AgentCardMinimal.vue
frontend/src/components/agents/AgentCardDetailed.vue
frontend/src/components/agents/AgentJobCard.vue
frontend/src/components/common/ProjectStatusBadge.vue
frontend/src/components/common/AgentStatusBadge.vue
frontend/src/components/common/LoadingOverlay.vue
frontend/src/components/common/ProgressSpinner.vue
frontend/src/components/common/Spinner.vue
frontend/src/components/common/SimpleModal.vue
frontend/src/components/common/DialogModal.vue
```

---

**End of 0515a Scope**