# Handover 0320: ProductsView Componentization

## Problem Statement

ProductsView.vue has grown to 2,582 lines, containing five inline dialogs that should be extracted into reusable components. This creates maintenance burden, reduces code reusability, and makes the file difficult to navigate and test effectively.

## Current State

- **ProductsView.vue**: 2,582 lines
- **Existing extractions in `frontend/src/components/products/`**:
  - `ActivationWarningDialog.vue` (4,787 bytes)
  - `OrchestratorLaunchButton.vue` (16,164 bytes)
  - `OrchestratorLaunchButton.md` (documentation)

- **Inline dialogs needing extraction**:
  1. **Create/Edit Product Dialog** (lines 222-1156) - Multi-tab form with Basic, Vision, Tech Stack, Architecture, Features & Testing tabs; includes auto-save functionality
  2. **Product Details Dialog** (lines 1159-1338) - Read-only view of product information
  3. **Delete Confirmation Dialog** (lines 1341-1447) - Soft delete with cascade impact display
  4. **Deleted Products Recovery Dialog** (lines 1459-1545) - List and restore soft-deleted products

Note: The ActivationWarningDialog has already been extracted as a component.

## Scope

### In Scope
- Extract `ProductForm.vue` - Create/edit dialog with multi-tab wizard (largest extraction, ~934 lines)
- Extract `ProductVisionPanel.vue` - Vision document upload/management section from ProductForm
- Extract `ProductDeleteDialog.vue` - Delete confirmation with cascade impact
- Extract `ProductDetailsDialog.vue` - Read-only product details view
- Extract `DeletedProductsRecoveryDialog.vue` - Trash recovery interface
- Update ProductsView.vue to import and use extracted components
- Maintain all existing functionality, state management, and event handling
- Preserve auto-save functionality in ProductForm

### Out of Scope
- Refactoring business logic or API calls
- Changes to Vuetify components or styling
- Modifications to the products Pinia store
- Backend changes
- New features or functionality
- Test file updates (to be handled in separate handover if needed)

## Success Criteria

- ProductsView.vue reduced to <1,000 lines (target: ~700-800 lines)
- 5 new components created in `frontend/src/components/products/`:
  - `ProductForm.vue`
  - `ProductVisionPanel.vue`
  - `ProductDeleteDialog.vue`
  - `ProductDetailsDialog.vue`
  - `DeletedProductsRecoveryDialog.vue`
- All existing functionality preserved exactly
- No regressions in:
  - Product CRUD operations
  - Auto-save with localStorage
  - Vision document upload and chunk display
  - Cascade impact display
  - Multi-tab navigation
  - Form validation
- Clean component interfaces using props and events
- Frontend builds successfully with no errors

## Technical Approach

### 1. Component Interface Design
Each extracted component should:
- Accept data via props (product data, dialog visibility state)
- Emit events for actions (save, cancel, delete, restore)
- Not directly call API services - parent coordinates data flow
- Use v-model for dialog visibility where appropriate

### 2. Extraction Order (dependency-aware)
1. **ProductVisionPanel.vue** - Can be extracted independently, used within ProductForm
2. **ProductDeleteDialog.vue** - Self-contained, simple interface
3. **ProductDetailsDialog.vue** - Self-contained, read-only
4. **DeletedProductsRecoveryDialog.vue** - Self-contained
5. **ProductForm.vue** - Largest; imports ProductVisionPanel; extract last

### 3. State Management Strategy
- ProductsView.vue remains the controller, managing:
  - Dialog visibility states
  - API calls and data fetching
  - Store interactions
- Child components receive props and emit events
- Auto-save composable stays with ProductForm or becomes shared utility

### 4. Example Component Interface

```vue
<!-- ProductDeleteDialog.vue -->
<template>
  <v-dialog v-model="modelValue" max-width="500" persistent>
    <!-- dialog content -->
  </v-dialog>
</template>

<script setup>
defineProps({
  modelValue: Boolean,
  product: Object,
  cascadeImpact: Object
})

defineEmits(['update:modelValue', 'confirm', 'cancel'])
</script>
```

```vue
<!-- Usage in ProductsView.vue -->
<ProductDeleteDialog
  v-model="showDeleteDialog"
  :product="productToDelete"
  :cascade-impact="cascadeImpact"
  @confirm="handleDelete"
  @cancel="showDeleteDialog = false"
/>
```

## Estimated Effort

- **Total**: 6-8 hours
  - ProductVisionPanel.vue: 1-1.5 hours
  - ProductDeleteDialog.vue: 0.5-1 hour
  - ProductDetailsDialog.vue: 0.5-1 hour
  - DeletedProductsRecoveryDialog.vue: 0.5-1 hour
  - ProductForm.vue: 2-3 hours (largest, most complex)
  - Integration testing and validation: 1-1.5 hours

## Dependencies

None - this is a frontend-only refactoring task with no backend changes required.

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking auto-save functionality | Test auto-save explicitly after ProductForm extraction |
| Event bubbling issues | Use explicit emit definitions, test each action |
| Props drilling complexity | Keep component hierarchy shallow (max 2 levels) |
| Missing state synchronization | Review all v-model bindings and watchers |

## References

- `handovers/013A_code_review_architecture_status.md` - November 16 architecture review recommending componentization
- Section 2.4 (Products) explicitly notes: "ProductsView.vue is very large. Over time, break into smaller components (e.g., ProductForm.vue, ProductVisionPanel.vue, ProductDeleteDialog.vue, etc.)"
- `frontend/src/components/products/ActivationWarningDialog.vue` - Example of already-extracted dialog component
