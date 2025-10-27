# Implementation Plan: Product Form Auto-Save & UX Polish

**Date**: 2025-10-27
**Handover**: 0051
**Estimated Duration**: 2-3 days

## Implementation Phases

### Phase 1: Debug & Fix Current Save (Day 1 - 4 hours)

**Priority**: CRITICAL - Must be completed first

#### Task 1.1: Add Diagnostic Logging (1 hour)

**Files to Modify**:
- `frontend/src/views/ProductsView.vue` (lines 1561-1629)
- `frontend/src/stores/products.js` (lines 132-173)
- `api/endpoints/products.py` (lines 115-249)

**Steps**:
1. Add console.log statements to `saveProduct()` function
2. Add console.log statements to store create/update methods
3. Add Python logging to backend endpoint
4. Test logging output with dummy data

**Success Criteria**:
- [ ] Can see complete save flow in browser console
- [ ] Can see backend logging in terminal/logs
- [ ] Can trace data from UI → Store → API → Database

#### Task 1.2: Manual Save Testing (2 hours)

**Steps**:
1. Open product creation dialog
2. Fill only "Product Name" field
3. Click Save and observe:
   - Console logs in browser
   - Network tab (request/response)
   - Database query results
4. Repeat with all 5 tabs filled
5. Test edit existing product
6. Document findings

**Success Criteria**:
- [ ] Can successfully save minimal product (name only)
- [ ] Can successfully save full product (all tabs)
- [ ] configData appears in database
- [ ] Data persists when reopening product

#### Task 1.3: Identify and Fix Bug (1 hour)

**Potential Issues**:
1. **API Service Not Stringifying configData**:
   ```javascript
   // frontend/src/services/api.js
   // Fix: Ensure configData is JSON.stringify'd before sending
   formData.append('config_data', JSON.stringify(productData.configData))
   ```

2. **Backend Not Saving configData**:
   ```python
   # api/endpoints/products.py
   # Verify: product.config_data = config_dict is executed
   ```

3. **Response Not Including configData**:
   ```python
   # api/endpoints/products.py
   # Verify: ProductResponse includes config_data field
   ```

**Steps**:
1. Analyze logs and network traffic
2. Identify root cause
3. Implement fix
4. Test fix thoroughly
5. Remove diagnostic logging (or keep with DEBUG flag)

**Success Criteria**:
- [ ] Product saves successfully every time
- [ ] configData persists to database
- [ ] Data loads correctly when editing

---

### Phase 2: Auto-Save Infrastructure (Day 1-2 - 8 hours)

**Priority**: HIGH

#### Task 2.1: Create Auto-Save Composable (3 hours)

**File to Create**: `frontend/src/composables/useAutoSave.js`

**Steps**:
1. Create new file
2. Implement core functionality:
   - `saveToCache()` - Save to LocalStorage
   - `restoreFromCache()` - Load from LocalStorage
   - `clearCache()` - Clear LocalStorage
   - Watch with debounce (500ms)
   - Save status tracking
3. Add error handling (quota exceeded, parse errors)
4. Add TypeScript types (if project uses TS)
5. Write JSDoc comments

**Code Template**:
```javascript
/**
 * Auto-save composable for form data persistence
 * @param {Object} options - Configuration options
 * @param {string} options.key - LocalStorage key
 * @param {Ref} options.data - Reactive data to watch
 * @param {number} [options.debounceMs=500] - Debounce delay
 * @returns {Object} Auto-save utilities
 */
export function useAutoSave(options = {}) {
  // ... implementation from SOLUTION_DESIGN.md
}
```

**Testing**:
1. Test saveToCache() with sample data
2. Test restoreFromCache() retrieval
3. Test clearCache() removal
4. Test debouncing behavior
5. Test quota exceeded handling

**Success Criteria**:
- [ ] Composable created and exports working functions
- [ ] LocalStorage operations work correctly
- [ ] Debouncing works as expected
- [ ] Error handling prevents crashes

#### Task 2.2: Integrate Auto-Save into ProductsView (3 hours)

**File to Modify**: `frontend/src/views/ProductsView.vue`

**Steps**:
1. Import `useAutoSave` composable
2. Initialize auto-save when dialog opens:
   ```javascript
   watch(showDialog, (isOpen) => {
     if (isOpen) {
       const cacheKey = editingProduct.value
         ? `product_form_draft_${editingProduct.value.id}`
         : 'product_form_draft_new'

       autoSave.value = useAutoSave({
         key: cacheKey,
         data: productForm,
         debounceMs: 500,
       })

       // Try to restore from cache
       const cached = autoSave.value.restoreFromCache()
       if (cached) {
         const shouldRestore = confirm('Found unsaved changes. Restore?')
         if (shouldRestore) {
           productForm.value = { ...cached }
         } else {
           autoSave.value.clearCache()
         }
       }
     }
   })
   ```

3. Clear cache on successful save:
   ```javascript
   async function saveProduct() {
     // ... existing save logic ...

     // On success:
     if (autoSave.value) {
       autoSave.value.clearCache()
     }
   }
   ```

4. Handle cleanup on unmount

**Testing**:
1. Open dialog, type in fields, verify LocalStorage updated
2. Close dialog, reopen, verify restore prompt appears
3. Save successfully, verify cache cleared
4. Test with multiple products (different cache keys)

**Success Criteria**:
- [ ] Auto-save activates when dialog opens
- [ ] LocalStorage updates as user types (debounced)
- [ ] Restore prompt appears when cached data exists
- [ ] Cache cleared after successful save
- [ ] No memory leaks

#### Task 2.3: Add Save Status Indicator UI (2 hours)

**File to Modify**: `frontend/src/views/ProductsView.vue` (template)

**Steps**:
1. Add status chip to dialog header:
   ```vue
   <v-card-title class="d-flex align-center">
     <span>{{ editingProduct ? 'Edit Product' : 'New Product' }}</span>
     <v-spacer></v-spacer>

     <v-chip
       v-if="autoSave && autoSave.saveStatus.value === 'unsaved'"
       color="warning"
       size="small"
       variant="flat"
       class="mr-2"
     >
       <v-icon start size="small">mdi-content-save-alert</v-icon>
       Unsaved changes
     </v-chip>

     <v-chip
       v-else-if="autoSave && autoSave.saveStatus.value === 'saved'"
       color="success"
       size="small"
       variant="flat"
       class="mr-2"
     >
       <v-icon start size="small">mdi-check</v-icon>
       Saved
     </v-chip>
   </v-card-title>
   ```

2. Add optional timestamp display (last saved)
3. Add accessibility attributes (aria-live)

**Testing**:
1. Verify chip appears when typing
2. Verify chip color changes based on status
3. Verify chip shows correct icon
4. Test with screen reader (if possible)

**Success Criteria**:
- [ ] Status indicator visible and updates in real-time
- [ ] Colors and icons are correct
- [ ] Accessible to screen readers
- [ ] Doesn't interfere with dialog layout

---

### Phase 3: UX Polish (Day 2 - 6 hours)

**Priority**: MEDIUM

#### Task 3.1: Unsaved Changes Warning (2 hours)

**File to Modify**: `frontend/src/views/ProductsView.vue`

**Steps**:
1. Add computed property for unsaved changes:
   ```javascript
   const hasUnsavedChanges = computed(() => {
     return autoSave.value?.hasUnsavedChanges.value || false
   })
   ```

2. Update `closeDialog()` function:
   ```javascript
   function closeDialog() {
     if (hasUnsavedChanges.value) {
       const confirmed = confirm(
         'You have unsaved changes. Close without saving?'
       )
       if (!confirmed) return
     }

     // Clear cache and reset form
     if (autoSave.value) {
       autoSave.value.clearCache()
     }

     showDialog.value = false
     // ... rest of cleanup
   }
   ```

3. Add browser beforeunload handler:
   ```javascript
   onMounted(() => {
     window.addEventListener('beforeunload', handleBeforeUnload)
   })

   function handleBeforeUnload(event) {
     if (showDialog.value && hasUnsavedChanges.value) {
       event.preventDefault()
       event.returnValue = ''
     }
   }
   ```

4. Add persistent prop to v-dialog:
   ```vue
   <v-dialog v-model="showDialog" max-width="900px" persistent>
   ```

**Testing**:
1. Type in form, try to close dialog → should show warning
2. Type in form, refresh browser → should show browser warning
3. Save successfully, close dialog → no warning
4. Test ESC key behavior

**Success Criteria**:
- [ ] Warning appears when closing with unsaved changes
- [ ] Browser warning appears on refresh/close with unsaved changes
- [ ] No warning after successful save
- [ ] Dialog can't be closed by clicking outside (persistent)

#### Task 3.2: Tab Validation Indicators (2 hours)

**File to Modify**: `frontend/src/views/ProductsView.vue`

**Steps**:
1. Create tab validation computed property:
   ```javascript
   const tabValidation = computed(() => {
     return {
       basic: {
         valid: !!productForm.value.name,
         hasError: !productForm.value.name,
       },
       vision: { valid: true, hasError: false },
       tech: {
         valid: true,
         hasWarning: !productForm.value.configData.tech_stack.languages,
       },
       arch: { valid: true, hasError: false },
       features: { valid: true, hasError: false },
     }
   })
   ```

2. Add badges to tabs:
   ```vue
   <v-tab value="basic">
     Basic Info
     <v-badge
       v-if="tabValidation.basic.hasError"
       color="error"
       dot
       inline
       class="ml-2"
     ></v-badge>
   </v-tab>
   ```

3. Add validation summary below tabs (optional):
   ```vue
   <v-alert
     v-if="Object.values(tabValidation).some(t => t.hasError)"
     type="error"
     density="compact"
     class="mb-4"
   >
     Please fix errors in: {{ errorTabs.join(', ') }}
   </v-alert>
   ```

**Testing**:
1. Leave name empty → error badge on "Basic Info" tab
2. Fill name → badge disappears
3. Test all tabs for appropriate indicators

**Success Criteria**:
- [ ] Error badges appear on tabs with validation issues
- [ ] Badges disappear when issues fixed
- [ ] User can easily identify which tabs need attention

#### Task 3.3: Better Testing Strategy Placeholder (1 hour)

**File to Modify**: `frontend/src/views/ProductsView.vue`

**Steps**:
1. Define testing strategies array:
   ```javascript
   const testingStrategies = [
     {
       value: 'TDD',
       title: 'TDD (Test-Driven Development)',
       subtitle: 'Write tests before implementation code',
     },
     // ... other strategies
   ]
   ```

2. Update v-select:
   ```vue
   <v-select
     v-model="productForm.configData.test_config.strategy"
     :items="testingStrategies"
     item-title="title"
     item-value="value"
     label="Testing Strategy"
     variant="outlined"
   >
     <template #item="{ props, item }">
       <v-list-item v-bind="props">
         <v-list-item-title>{{ item.raw.title }}</v-list-item-title>
         <v-list-item-subtitle>{{ item.raw.subtitle }}</v-list-item-subtitle>
       </v-list-item>
     </template>
   </v-select>
   ```

3. Add helpful hints to other fields as needed

**Testing**:
1. Open dropdown → verify descriptions visible
2. Select strategy → verify selection works
3. Check other fields for improved placeholders

**Success Criteria**:
- [ ] Testing strategy dropdown shows helpful descriptions
- [ ] All placeholders are clear and helpful
- [ ] Fields have appropriate hints

#### Task 3.4: Tab Completion Progress (1 hour - Optional)

**File to Modify**: `frontend/src/views/ProductsView.vue`

**Steps**:
1. Calculate completion percentage per tab:
   ```javascript
   const tabCompletion = computed(() => {
     return {
       basic: calculateBasicCompletion(),
       vision: calculateVisionCompletion(),
       tech: calculateTechCompletion(),
       arch: calculateArchCompletion(),
       features: calculateFeaturesCompletion(),
     }
   })

   function calculateTechCompletion() {
     const fields = productForm.value.configData.tech_stack
     const filledFields = Object.values(fields).filter(v => v).length
     const totalFields = Object.keys(fields).length
     return (filledFields / totalFields) * 100
   }
   ```

2. Add progress indicator to tabs:
   ```vue
   <v-tab value="tech">
     Tech Stack
     <v-chip
       v-if="tabCompletion.tech < 100"
       size="x-small"
       variant="outlined"
       class="ml-2"
     >
       {{ Math.round(tabCompletion.tech) }}%
     </v-chip>
   </v-tab>
   ```

**Testing**:
1. Fill fields gradually, watch percentage increase
2. Verify calculation is accurate
3. Check visual appearance

**Success Criteria**:
- [ ] Completion percentage accurate
- [ ] Visual indicator clear and helpful
- [ ] Doesn't clutter UI

---

### Phase 4: Testing & Validation (Day 2-3 - 4 hours)

**Priority**: CRITICAL

See `TESTING.md` for comprehensive test plan.

**Key Test Scenarios**:
1. Create new product with all tabs filled
2. Edit existing product
3. Auto-save and restore workflow
4. Network failure handling
5. Browser refresh with unsaved changes
6. Multiple products (different cache keys)
7. LocalStorage quota exceeded (simulate with large data)
8. Concurrent editing (same product in two windows)

**Success Criteria**:
- [ ] All critical test scenarios pass
- [ ] No data loss in any scenario
- [ ] User experience is smooth and intuitive
- [ ] No console errors or warnings

---

## Development Workflow

### Daily Checklist

**Day 1 Morning** (4 hours):
- [ ] Phase 1 complete (debug and fix save)
- [ ] Verified save works end-to-end
- [ ] Documented fix in devlog

**Day 1 Afternoon** (4 hours):
- [ ] Task 2.1 complete (auto-save composable)
- [ ] Task 2.2 started (integration)

**Day 2 Morning** (4 hours):
- [ ] Task 2.2 complete (integration)
- [ ] Task 2.3 complete (UI indicator)
- [ ] Phase 2 fully tested

**Day 2 Afternoon** (4 hours):
- [ ] Phase 3 tasks 3.1-3.3 complete (UX polish)
- [ ] Phase 4 started (testing)

**Day 3** (2-4 hours):
- [ ] Phase 4 complete (comprehensive testing)
- [ ] All edge cases tested
- [ ] Documentation updated
- [ ] Handover closed

### Code Review Checklist

Before marking Phase complete:
- [ ] Code follows project style guide
- [ ] No console.log statements (or behind DEBUG flag)
- [ ] TypeScript types added (if applicable)
- [ ] JSDoc comments added
- [ ] Error handling is comprehensive
- [ ] No memory leaks (watch/listeners cleaned up)
- [ ] Accessibility considered (ARIA attributes)
- [ ] Performance is acceptable (no UI blocking)

### Git Workflow

**Branches**:
- `feature/0051-product-form-autosave` (main feature branch)
- `feature/0051-phase1-fix-save` (optional sub-branch)

**Commits**:
```bash
# Phase 1
git commit -m "debug: Add diagnostic logging to product save flow (0051)"
git commit -m "fix: Resolve configData not persisting to database (0051)"

# Phase 2
git commit -m "feat: Add useAutoSave composable for form data persistence (0051)"
git commit -m "feat: Integrate auto-save into ProductsView (0051)"
git commit -m "feat: Add save status indicator to product form (0051)"

# Phase 3
git commit -m "feat: Add unsaved changes warning to product form (0051)"
git commit -m "feat: Add tab validation indicators (0051)"
git commit -m "feat: Improve testing strategy field UX (0051)"

# Phase 4
git commit -m "test: Add comprehensive testing for auto-save feature (0051)"
git commit -m "docs: Update user guide with auto-save behavior (0051)"
```

---

## Risk Mitigation

### Risk 1: Breaking Existing Functionality
**Mitigation**:
- Test existing save flow thoroughly before changes
- Add feature flag to disable auto-save if issues arise
- Keep diagnostic logging available (DEBUG mode)

### Risk 2: LocalStorage Quota Exceeded
**Mitigation**:
- Add try-catch for quota exceeded errors
- Show user-friendly error message
- Fall back to memory-only mode

### Risk 3: Performance Impact
**Mitigation**:
- Use debouncing (500ms)
- Profile with Vue DevTools
- Optimize deep watching if needed

### Risk 4: Concurrent Edit Conflicts
**Mitigation**:
- Document limitation in user guide
- Future enhancement: Add conflict detection

---

## Documentation Updates

**Files to Update**:
- `docs/user-guide/PRODUCTS.md` - Add auto-save section
- `handovers/0051/COMPLETION_REPORT.md` - Create upon completion
- `CHANGELOG.md` - Add feature entry

**User Guide Section**:
```markdown
## Auto-Save

The product form automatically saves your changes to prevent data loss:

- **Auto-save**: Your work is saved every 500ms as you type
- **Draft Recovery**: Unsaved changes are preserved if you close the dialog
- **Restore Prompt**: You'll be asked if you want to restore drafts when reopening
- **Save Indicator**: Watch the status chip in the dialog header:
  - 🟢 "Saved" = All changes are saved
  - 🟡 "Unsaved changes" = Changes not yet persisted

**Tip**: You still need to click "Save" to finalize and close the dialog. Auto-save is a safety net, not a replacement for explicit saving.
```

---

## Success Metrics

**Quantitative**:
- 0 data loss incidents reported after deployment
- < 500ms save latency (debounce + LocalStorage)
- 100% test coverage for auto-save composable
- 0 console errors during normal operation

**Qualitative**:
- User feedback on improved confidence
- Reduced support tickets about lost data
- Positive sentiment in user surveys

---

**Next**: Proceed with Phase 1 implementation.
