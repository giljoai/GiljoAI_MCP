# Handover 0816: Vision Upload Progress UX Fix

**Date:** 2026-03-14
**From Agent:** Code Cleanup Audit (cleaning_march_14 branch)
**To Agent:** ux-designer or tdd-implementor
**Priority:** Medium
**Estimated Complexity:** 1-2 hours
**Status:** Completed
**Edition Scope:** CE

## Task Summary

Fix the disconnected vision document upload progress UI. ProductForm has a progress bar and error alert for vision uploads (lines 198-229), but the actual upload logic lives in ProductsView.saveProduct (lines 777-855). The two are never connected — the dialog closes before uploads finish, and ProductForm's progress refs are never updated by the parent.

## Context and Background

Discovered during the March 2026 dead code audit on branch `cleaning_march_14`. ProductForm.vue contains:
- `uploadingVision` ref (line 792) — never set to `true`
- `uploadProgress` ref (line 793) — never incremented
- `visionUploadError` ref (line 794) — never populated

These refs were initially flagged as dead code, but the template UI they drive (progress bar, error alert) represents a valid UX feature that was never wired up. The refs were **not** removed during cleanup — they remain in ProductForm ready to be connected.

The `@upload-vision` event listener on ProductForm (ProductsView line 268) points to an empty stub function (line 585-587) with a comment "Currently not used - ProductForm passes files via save event."

## Technical Details

### Current Architecture (Broken)

```
ProductsView (parent)
  ├── saveProduct() at line 745 receives { productData, visionFiles } from ProductForm
  ├── Uploads files sequentially in a for-loop (lines 784-844)
  ├── Shows per-file toast messages on success/error
  ├── Calls closeDialog() AFTER all uploads complete (line 866)
  └── ProductForm has NO visibility into upload progress

ProductForm (child)
  ├── Has progress bar UI (lines 211-229) — v-if="uploadingVision"
  ├── Has error alert UI (lines 198-209) — v-if="visionUploadError"
  ├── Local refs: uploadingVision, uploadProgress, visionUploadError (lines 792-794)
  └── These refs are NEVER updated — UI is permanently hidden
```

### Key Problem

The dialog stays open during uploads (closeDialog is called at line 866, after uploads), but the user sees no feedback because ProductForm's progress state is local and undriven. Users uploading multiple large vision documents have zero visual indication that anything is happening.

### Files to Modify

| File | Change |
|------|--------|
| `frontend/src/views/ProductsView.vue` | Add reactive refs for upload state, pass as props to ProductForm |
| `frontend/src/components/products/ProductForm.vue` | Accept new props, wire to existing template UI, remove local dead refs |

### Proposed Fix

**Option A (Recommended): Props-down pattern**

1. In ProductsView, add 3 refs:
   ```js
   const uploadingVision = ref(false)
   const uploadProgress = ref(0)
   const visionUploadError = ref(null)
   ```

2. Pass them as props to ProductForm:
   ```html
   <ProductForm
     ...
     :uploading-vision="uploadingVision"
     :upload-progress="uploadProgress"
     :vision-upload-error="visionUploadError"
   />
   ```

3. In saveProduct(), update these refs during the upload loop:
   ```js
   uploadingVision.value = true
   uploadProgress.value = 0
   // In the for-loop:
   uploadProgress.value = ((i + 1) / visionFiles.value.length) * 100
   // On error:
   visionUploadError.value = errorMessage
   // After loop:
   uploadingVision.value = false
   ```

4. In ProductForm, replace local refs with props:
   - Remove local `uploadingVision`, `uploadProgress`, `visionUploadError` refs
   - Add to defineProps: `uploadingVision` (Boolean), `uploadProgress` (Number), `visionUploadError` (String|null)
   - Template already binds to these names — no template changes needed
   - The dismiss button on visionUploadError alert needs an emit to parent (e.g., `@click:close="emit('clear-upload-error')"`)

5. Clean up the empty `uploadVisionDocument()` stub in ProductsView (line 585-587) and its `@upload-vision` listener (line 268) if confirmed unused.

**Option B: Event-up pattern (alternative)**

ProductsView emits upload-state events, ProductForm listens. More complex, less Vue-idiomatic.

## Implementation Plan

### Phase 1: Wire up progress (30 min)
- Add upload state refs to ProductsView
- Pass as props to ProductForm
- Update saveProduct() upload loop to drive the refs
- Remove dead local refs from ProductForm, accept props instead

### Phase 2: Error handling (15 min)
- Wire visionUploadError prop and dismiss emit
- Ensure error alert dismissal clears parent state

### Phase 3: Clean dead code (10 min)
- Remove empty `uploadVisionDocument()` stub and its `@upload-vision` event binding if no longer needed
- Verify `@remove-vision` is still needed (it IS — it handles deleting existing docs)

### Phase 4: Test (15 min)
- Manual: Create product with 2+ vision documents, verify progress bar appears and advances
- Manual: Upload an invalid file, verify error alert shows and is dismissable
- Manual: Upload succeeds, verify progress resets on next dialog open
- Write unit test for ProductForm rendering progress bar when props are truthy

## Testing Requirements

**Manual Testing:**
1. Open Create Product dialog
2. Attach 2-3 vision documents (.md or .txt files)
3. Click Save
4. Verify: progress bar appears with "Uploading vision documents..." message
5. Verify: progress bar advances as each file completes
6. Verify: on completion, dialog closes normally
7. Test error case: upload a .pdf (unsupported), verify error alert appears

**Unit Tests:**
- ProductForm renders progress bar when `uploadingVision=true`
- ProductForm hides progress bar when `uploadingVision=false`
- ProductForm shows error alert when `visionUploadError` is set
- Error alert dismiss emits `clear-upload-error`

## Dependencies and Blockers

- None. This is a standalone frontend fix.
- No backend changes required.
- No database changes.

## Success Criteria

- Users see a progress bar during vision document uploads
- Users see error alerts for failed uploads, dismissable
- Progress state resets cleanly when dialog reopens
- No regressions to product create/edit flow
- Empty stub function removed

## Rollback Plan

Revert the 2 frontend files. No backend or database impact.

## Implementation Summary

### 2026-03-14 - Completed

**Commits:**
- `2c8c921e` fix: Wire up vision upload progress bar and error alert in ProductForm
- `73c3fa35` test: Add vision upload progress tests and fix watcher ReferenceError

**What was done:**
- ProductsView: Added 3 refs (uploadingVision, uploadProgress, visionUploadError), passed as props to ProductForm, driven during saveProduct() upload loop, reset in closeDialog()
- ProductForm: Removed 3 dead local refs, accepted as props, updated defineEmits (removed upload-vision, added clear-upload-error), changed v-model to :model-value on progress bar, error dismiss emits to parent
- Removed empty uploadVisionDocument() stub and its @upload-vision event binding
- Fixed watcher ReferenceError that wrote to props as if they were local refs
- 12 new unit tests covering progress bar rendering, error alert, dismiss emit, prop defaults
- Updated v-alert test stub to support Boolean dismissible prop and click:close emit
- Fixed stale test referencing removed upload-vision emit

**Files modified:** ProductsView.vue, ProductForm.vue, ProductForm.spec.js
**Build:** Passes. **Tests:** 91 passing (12 new + 1 pre-existing fix), 9 pre-existing failures unchanged.
