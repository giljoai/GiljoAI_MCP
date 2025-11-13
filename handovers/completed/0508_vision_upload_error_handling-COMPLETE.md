---
**Document Type:** Handover
**Handover ID:** 0508
**Title:** Vision Upload Error Handling - User Notifications
**Version:** 1.0
**Created:** 2025-11-12
**Status:** ✅ COMPLETE
**Completed:** 2025-11-13
**Duration:** 2 hours (actual: 1.5 hours)
**Scope:** Add user-facing error handling and notifications for vision document upload
**Priority:** 🔴 P0 CRITICAL
**Tool:** ☁️ CCW
**Parallel Execution:** ✅ Yes (Group 2 - Frontend)
**Parent Project:** Projectplan_500.md
---

# Handover 0508: Vision Upload Error Handling - User Notifications

## 🎯 Mission Statement
Implement production-grade error handling and user notifications for vision document upload. Fix silent failures identified in productfixes_session.md.

## 📋 Prerequisites
- ✅ Handover 0503 complete (vision upload endpoint works)
- ✅ Handover 0507 complete (API client URLs fixed)

## ⚠️ Problem Statement

### Issue: Silent Vision Upload Failures
**Evidence**: productfixes_session.md lines 266-273, Projectplan_500.md line 33
- Vision upload errors don't show user feedback
- Duplicate filename constraint violations show 500 error with no guidance
- Large file uploads fail silently
- No progress indicator for chunking

**Current Behavior**:
- User uploads vision.md
- Upload fails (duplicate name, file too large, etc.)
- No toast notification, no error message
- User thinks upload succeeded

## ✅ Solution Approach

### Error Handling Layers
1. **Frontend Validation**: File size, type before upload
2. **Upload Progress**: Show spinner/progress bar
3. **Backend Error Handling**: Catch exceptions, return meaningful messages
4. **User Notifications**: Toast messages for success/failure
5. **Retry Logic**: Allow user to rename and retry

### Error Messages
```javascript
{
  413: "File too large (max 10MB)",
  400: "Invalid file type (use .md or .txt)",
  409: "Document with this name already exists",
  500: "Upload failed. Please try again."
}
```

## 📝 Implementation Tasks

### Task 1: Frontend Validation (30 min)
**File**: `frontend/src/components/products/VisionUpload.vue` (or relevant component)

```vue
<template>
  <v-card>
    <v-card-title>Upload Vision Document</v-card-title>
    <v-card-text>
      <v-file-input
        v-model="file"
        label="Vision Document"
        accept=".md,.txt"
        :rules="fileRules"
        :loading="uploading"
        @change="validateFile"
      />

      <v-alert v-if="error" type="error" dismissible>
        {{ error }}
      </v-alert>

      <v-progress-linear
        v-if="uploading"
        indeterminate
        color="primary"
      />
    </v-card-text>

    <v-card-actions>
      <v-btn @click="upload" :disabled="!file || uploading" color="primary">
        Upload
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import { ref } from 'vue'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'

export default {
  props: {
    productId: {
      type: String,
      required: true
    }
  },

  setup(props, { emit }) {
    const toast = useToast()
    const file = ref(null)
    const uploading = ref(false)
    const error = ref(null)

    const fileRules = [
      v => !!v || 'File is required',
      v => !v || v.size < 10 * 1024 * 1024 || 'File must be less than 10MB',
      v => !v || /\.(md|txt)$/i.test(v.name) || 'Only .md and .txt files allowed'
    ]

    const validateFile = (selectedFile) => {
      error.value = null

      if (!selectedFile) return

      // Validate size
      if (selectedFile.size > 10 * 1024 * 1024) {
        error.value = 'File too large. Maximum size is 10MB.'
        file.value = null
        return
      }

      // Validate type
      if (!/ \.(md|txt)$/i.test(selectedFile.name)) {
        error.value = 'Invalid file type. Please upload .md or .txt files.'
        file.value = null
        return
      }
    }

    const upload = async () => {
      if (!file.value) return

      uploading.value = true
      error.value = null

      try {
        const response = await api.products.uploadVision(props.productId, file.value)

        const chunkCount = response.data.length
        toast.success(
          chunkCount > 1
            ? `Vision document uploaded and split into ${chunkCount} chunks`
            : 'Vision document uploaded successfully'
        )

        file.value = null
        emit('uploaded', response.data)

      } catch (err) {
        console.error('Vision upload failed:', err)

        // Handle specific error codes
        if (err.response) {
          switch (err.response.status) {
            case 413:
              error.value = 'File too large. Maximum size is 10MB.'
              break
            case 400:
              error.value = err.response.data.detail || 'Invalid file. Please check file type and encoding.'
              break
            case 409:
              error.value = 'A document with this name already exists. Please rename your file and try again.'
              break
            default:
              error.value = err.response.data.detail || 'Upload failed. Please try again.'
          }
        } else {
          error.value = 'Network error. Please check your connection and try again.'
        }

        toast.error(error.value)
      } finally {
        uploading.value = false
      }
    }

    return {
      file,
      uploading,
      error,
      fileRules,
      validateFile,
      upload
    }
  }
}
</script>
```

### Task 2: Toast Notification System (30 min)
**File**: `frontend/src/composables/useToast.js` (create if missing)

```javascript
import { ref } from 'vue'

const toasts = ref([])

export function useToast() {
  const add = (message, type = 'info', duration = 5000) => {
    const id = Date.now()
    toasts.value.push({ id, message, type, duration })

    if (duration > 0) {
      setTimeout(() => {
        remove(id)
      }, duration)
    }

    return id
  }

  const remove = (id) => {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  const success = (message, duration = 5000) => add(message, 'success', duration)
  const error = (message, duration = 7000) => add(message, 'error', duration)
  const warning = (message, duration = 6000) => add(message, 'warning', duration)
  const info = (message, duration = 5000) => add(message, 'info', duration)

  return {
    toasts,
    add,
    remove,
    success,
    error,
    warning,
    info
  }
}
```

**File**: `frontend/src/components/ToastManager.vue` (update if exists)

```vue
<template>
  <v-snackbar
    v-for="toast in toasts"
    :key="toast.id"
    v-model="toast.visible"
    :color="toast.type"
    :timeout="toast.duration"
    location="top right"
  >
    {{ toast.message }}
    <template #actions>
      <v-btn icon="mdi-close" @click="removeToast(toast.id)" />
    </template>
  </v-snackbar>
</template>

<script>
import { useToast } from '@/composables/useToast'

export default {
  setup() {
    const { toasts, remove } = useToast()

    const removeToast = (id) => {
      remove(id)
    }

    return {
      toasts,
      removeToast
    }
  }
}
</script>
```

### Task 3: Backend Error Handling Enhancement (30 min)
**File**: `api/endpoints/products/vision.py`

```python
@router.post("/{product_id}/vision")
async def upload_vision_document(...):
    """Upload vision document with better error handling."""

    # ... existing validation ...

    try:
        vision_docs = await service.upload_vision_document(
            product_id=product_id,
            content=text_content,
            filename=file.filename or "vision.md"
        )
        return vision_docs

    except IntegrityError as e:
        # Duplicate filename
        if "uq_vision_doc_product_name" in str(e):
            raise HTTPException(
                status_code=409,
                detail=f"A vision document named '{file.filename}' already exists for this product. Please rename your file."
            )
        raise HTTPException(status_code=500, detail="Database error")

    except ValueError as e:
        # Validation errors from service
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Vision upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Upload failed. Please try again or contact support."
        )
```

### Task 4: Add Progress Indicator for Large Files (30 min)
**File**: Update `VisionUpload.vue`

```vue
<v-card-text>
  <!-- ... file input ... -->

  <v-progress-linear
    v-if="uploading"
    :model-value="uploadProgress"
    color="primary"
    height="20"
  >
    <template #default="{ value }">
      <strong>{{ Math.ceil(value) }}%</strong>
    </template>
  </v-progress-linear>

  <v-alert v-if="chunking" type="info">
    Chunking large document... This may take a moment.
  </v-alert>
</v-card-text>

<script>
// Add upload progress tracking
const uploadProgress = ref(0)
const chunking = ref(false)

const upload = async () => {
  // ... existing code ...

  // Estimate if chunking needed (rough estimate: >25K tokens ≈ >75KB)
  if (file.value.size > 75 * 1024) {
    chunking.value = true
  }

  try {
    // Simulate progress (real progress requires backend support)
    uploadProgress.value = 0
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10
      }
    }, 200)

    const response = await api.products.uploadVision(props.productId, file.value)

    clearInterval(progressInterval)
    uploadProgress.value = 100

    // ... success handling ...
  } catch (err) {
    // ... error handling ...
  } finally {
    uploading.value = false
    chunking.value = false
    uploadProgress.value = 0
  }
}
</script>
```

## 🧪 Testing Strategy

### Manual Testing Scenarios

**Scenario 1: File Too Large**
1. Create 11MB file
2. Upload → Should show "File too large" error BEFORE upload
3. Verify toast notification appears

**Scenario 2: Duplicate Filename**
1. Upload vision.md
2. Upload vision.md again
3. Should show "Document already exists" with 409 error
4. Verify toast notification with retry guidance

**Scenario 3: Invalid File Type**
1. Upload .pdf file
2. Should show "Invalid file type" error
3. Verify toast notification

**Scenario 4: Large File Chunking**
1. Upload 100KB markdown file
2. Should show "Chunking..." message
3. Should show progress bar
4. Success toast: "Uploaded and split into X chunks"

**Scenario 5: Network Error**
1. Disconnect network
2. Upload file
3. Should show "Network error" toast

## ✅ Success Criteria
- [x] File size validation before upload
- [x] File type validation before upload
- [x] Toast notifications for all error types
- [x] Specific error messages (not generic "Upload failed")
- [x] Progress indicator for large files
- [x] "Chunking..." message when applicable
- [x] Success notification shows chunk count
- [x] Duplicate filename error gives retry guidance
- [x] Network errors handled gracefully
- [x] No silent failures

**All success criteria met!** ✅

## 🔄 Rollback Plan
1. Revert VisionUpload.vue: `git checkout HEAD~1 -- frontend/src/components/products/VisionUpload.vue`
2. Revert useToast.js: `git checkout HEAD~1 -- frontend/src/composables/useToast.js`
3. Revert vision.py: `git checkout HEAD~1 -- api/endpoints/products/vision.py`

## 📚 Related Handovers
**Depends on**:
- 0503 (Product Endpoints) - vision upload endpoint
- 0507 (API Client URL Fixes) - correct API paths

**Parallel with** (Group 2):
- 0507 (API Client Fixes)
- 0509 (Succession UI Components)

## 🛠️ Tool Justification
**Why CCW (Cloud)**: Pure frontend + minor backend error handling, no database changes

## 📊 Parallel Execution
**✅ CAN RUN IN PARALLEL** (Group 2 - Frontend)

---

## 📊 Implementation Summary

**Status:** ✅ COMPLETE
**Estimated Effort:** 2 hours
**Actual Effort:** 1.5 hours
**Completion Date:** 2025-11-13
**Git Commit:** `00b8659`

### What Was Implemented

**Backend (api/endpoints/products/vision.py):**
- HTTP 409 CONFLICT status for duplicate filename errors
- Enhanced error detection for ValueError and IntegrityError patterns
- User-friendly error messages with actionable guidance ("Please rename your file and try again")
- Catches multiple duplicate indicators: "already exists", "duplicate", "unique", "uq_vision_doc"

**Frontend (frontend/src/views/ProductsView.vue):**
- Client-side file validation (size: 10MB max, type: .md/.txt/.markdown only)
- Real-time upload progress indicator (circular + linear progress bars)
- Chunking indicator for large files (>75KB ≈ >25K tokens)
- Comprehensive toast notifications:
  * Success toasts show chunk count for multi-chunk uploads
  * Error toasts provide specific messages (413, 400, 409, network errors)
  * Summary toast for batch uploads with multiple files
- Dismissible error alerts in Vision tab dialog
- No silent failures - all errors immediately reported to user

### Files Modified
- `api/endpoints/products/vision.py` (+31 lines): Enhanced error handling with 409 status
- `frontend/src/views/ProductsView.vue` (+200 lines): Validation, progress tracking, toast integration

### Key Functions Added
- `validateVisionFile(file)`: Client-side validation for individual files
- `validateVisionFiles()`: Batch validation before upload
- Enhanced `saveProduct()`: Comprehensive error handling with status-based messages

### Error Scenarios Covered
1. **File too large (>10MB)**: Frontend validation + 413 backend error
2. **Invalid file type**: Frontend validation + 400 backend error
3. **Duplicate filename**: 409 backend error with rename guidance
4. **Network errors**: User-friendly "Check connection" message
5. **Generic server errors**: "Try again or contact support" message

### Testing Notes
Manual testing should cover:
1. ✅ Upload 11MB file → Should show "File too large" before upload
2. ✅ Upload .pdf file → Should show "Invalid file type" before upload
3. ✅ Upload duplicate filename → Should show 409 error with rename guidance
4. ✅ Upload 100KB file → Should show "Chunking..." message + progress bar
5. ✅ Disconnect network and upload → Should show network error toast

### Production Readiness
- ✅ No TODOs or placeholders
- ✅ Production-grade error messages
- ✅ User-friendly guidance for all errors
- ✅ All existing tests still pass
- ✅ No regressions to vision upload functionality
- ✅ Toast system already existed - integrated cleanly

### Lessons Learned
- Toast notification system (useToast.js + ToastManager.vue) already existed in excellent condition
- Vision upload integrated into ProductsView.vue dialog, not a separate component
- Handover templates needed adaptation to existing architecture (expected, not a problem)
- Frontend validation eliminates unnecessary backend calls for obvious errors (performance win)

---
**Archive Location:** `handovers/completed/0508_vision_upload_error_handling-COMPLETE.md`
