# Technical Recommendations - Handover 0046 Fixes

## Overview

This document provides specific code fixes for the 4 critical and 5 non-critical issues found in the ProductsView implementation.

---

## Critical Fix 1: Update ProductResponse Schema

**File**: `F:\GiljoAI_MCP\api\endpoints\products.py` lines 35-44

**Current Code**:
```python
class ProductResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    vision_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    project_count: int = 0
    task_count: int = 0
    has_vision: bool = False
```

**Fixed Code**:
```python
class ProductResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    vision_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    project_count: int = 0
    task_count: int = 0
    has_vision: bool = False
    unresolved_tasks: int = 0
    unfinished_projects: int = 0
    vision_documents_count: int = 0
```

**Justification**:
- Frontend expects these fields to display product summary statistics
- Handover spec requires showing: "Unresolved Tasks, Unfinished Projects, Vision Docs"
- Currently these would display as undefined/empty in UI

---

## Critical Fix 2: Update list_products Endpoint Logic

**File**: `F:\GiljoAI_MCP\api\endpoints\products.py` lines 191-236

**Current Code** (lines 218-231):
```python
response = []
for product in products:
    response.append(
        ProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            vision_path=product.vision_path,
            created_at=product.created_at,
            updated_at=product.updated_at,
            project_count=len(product.projects) if product.projects else 0,
            task_count=len(product.tasks) if product.tasks else 0,
            has_vision=bool(product.vision_path),
        )
    )
```

**Fixed Code**:
```python
response = []
for product in products:
    # Calculate unfinished/unresolved counts
    projects = product.projects or []
    tasks = product.tasks or []

    unfinished_projects = sum(1 for p in projects if p.status != 'completed')
    unresolved_tasks = sum(1 for t in tasks if t.status != 'completed')

    # Get vision document count - need to eager load or calculate
    # Option: Use db query if not eager loaded
    # For now, assuming relationship is loaded
    vision_doc_count = len(product.vision_documents) if hasattr(product, 'vision_documents') else 0

    response.append(
        ProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            vision_path=product.vision_path,
            created_at=product.created_at,
            updated_at=product.updated_at,
            project_count=len(projects),
            task_count=len(tasks),
            has_vision=bool(product.vision_path),
            unfinished_projects=unfinished_projects,
            unresolved_tasks=unresolved_tasks,
            vision_documents_count=vision_doc_count,
        )
    )
```

**Required Changes to Query** (line 206-211):
The selectinload should also include vision_documents:
```python
stmt = (
    select(Product)
    .where(Product.tenant_key == tenant_key)
    .options(
        selectinload(Product.projects),
        selectinload(Product.tasks),
        selectinload(Product.vision_documents)  # <- ADD THIS
    )
    .limit(limit)
    .offset(offset)
)
```

**Justification**:
- Need to calculate unfinished vs total projects
- Need to calculate unresolved vs total tasks
- Need to count vision documents per product
- Eager loading prevents N+1 queries

---

## Critical Fix 3: Update get_product Endpoint Logic

**File**: `F:\GiljoAI_MCP\api\endpoints\products.py` lines 239-277

**Current Code** (lines 262-272):
```python
return ProductResponse(
    id=product.id,
    name=product.name,
    description=product.description,
    vision_path=product.vision_path,
    created_at=product.created_at,
    updated_at=product.updated_at,
    project_count=len(product.projects) if product.projects else 0,
    task_count=len(product.tasks) if product.tasks else 0,
    has_vision=bool(product.vision_path),
)
```

**Fixed Code**:
```python
# Calculate unfinished/unresolved counts
projects = product.projects or []
tasks = product.tasks or []

unfinished_projects = sum(1 for p in projects if p.status != 'completed')
unresolved_tasks = sum(1 for t in tasks if t.status != 'completed')

# Get vision document count
vision_doc_count = len(product.vision_documents) if hasattr(product, 'vision_documents') else 0

return ProductResponse(
    id=product.id,
    name=product.name,
    description=product.description,
    vision_path=product.vision_path,
    created_at=product.created_at,
    updated_at=product.updated_at,
    project_count=len(projects),
    task_count=len(tasks),
    has_vision=bool(product.vision_path),
    unfinished_projects=unfinished_projects,
    unresolved_tasks=unresolved_tasks,
    vision_documents_count=vision_doc_count,
)
```

**Required Changes to Query** (line 250-254):
```python
stmt = (
    select(Product)
    .where(Product.id == product_id, Product.tenant_key == tenant_key)
    .options(
        selectinload(Product.projects),
        selectinload(Product.tasks),
        selectinload(Product.vision_documents)  # <- ADD THIS
    )
)
```

**Justification**:
- Consistency with list_products endpoint
- Same calculations needed for details view

---

## Critical Fix 4: Fix API Endpoint URL Paths

**File**: `F:\GiljoAI_MCP\frontend\src\services\api.js` line 114

**Current Code**:
```javascript
getCascadeImpact: (id) => apiClient.get(`/api/v1/products/${id}/cascade-impact`),
```

**Fixed Code**:
```javascript
getCascadeImpact: (id) => apiClient.get(`/api/products/${id}/cascade-impact`),
```

**Reason**:
Backend endpoint is registered at `/api/products/{product_id}/cascade-impact` (products.py line 343), NOT `/api/v1/products/`

**Verification**:
Check router prefix in `api/app.py` to confirm the endpoint registration path.

---

## High Priority Fix 1: Add Toast Notifications

**File**: `F:\GiljoAI_MCP\frontend\src\views\ProductsView.vue`

**Locations Needing Feedback**:
1. Line 451: Product created successfully
2. Line 845: Product updated successfully
3. Line 876: Product deleted successfully
4. Line 777: Vision document deleted successfully
5. Line 707: Product activated successfully

**Implementation Pattern**:

```javascript
// At top with other imports
import { useNotificationStore } from '@/stores/notifications' // Or use Vuetify snackbar

// Inside script setup
const notifications = useNotificationStore()

// In saveProduct function (after line 845)
try {
  // ... existing code ...
  closeDialog()

  // Add success notification
  notifications.show({
    message: editingProduct.value ? 'Product updated successfully' : 'Product created successfully',
    type: 'success',
    duration: 3000
  })
} catch (error) {
  notifications.show({
    message: 'Failed to save product: ' + error.message,
    type: 'error',
    duration: 5000
  })
}
```

**Alternative Using Vuetify Snackbar**:
If notification store doesn't exist, add a simple snackbar:

```javascript
const snackbar = ref(false)
const snackbarMessage = ref('')
const snackbarType = ref('success')

function showSnackbar(message, type = 'success') {
  snackbarMessage.value = message
  snackbarType.value = type
  snackbar.value = true
}

// In template
<v-snackbar
  v-model="snackbar"
  :color="snackbarType"
  timeout="3000"
>
  {{ snackbarMessage }}
</v-snackbar>
```

---

## High Priority Fix 2: Add Vision Document Deletion Confirmation

**File**: `F:\GiljoAI_MCP\frontend\src\views\ProductsView.vue` lines 290-298

**Current Code**:
```vue
<v-btn
  icon
  size="small"
  variant="text"
  color="error"
  @click="deleteVisionDocument(doc)"
>
  <v-icon size="20">mdi-delete</v-icon>
</v-btn>
```

**Fixed Code**:
```vue
<v-btn
  icon
  size="small"
  variant="text"
  color="error"
  @click="confirmDeleteVisionDocument(doc)"
>
  <v-icon size="20">mdi-delete</v-icon>
</v-btn>
```

**Add to script**:
```javascript
const docToDelete = ref(null)
const showDeleteDocumentConfirmDialog = ref(false)

function confirmDeleteVisionDocument(doc) {
  docToDelete.value = doc
  showDeleteDocumentConfirmDialog.value = true
}

async function deleteConfirmedVisionDocument() {
  if (!docToDelete.value) return

  try {
    await api.visionDocuments.delete(docToDelete.value.id)

    // Remove from list
    existingVisionDocuments.value = existingVisionDocuments.value.filter(
      d => d.id !== docToDelete.value.id
    )

    // Close dialog
    showDeleteDocumentConfirmDialog.value = false

    // Show success notification
    showSnackbar('Vision document deleted successfully', 'success')
  } catch (error) {
    console.error('Failed to delete vision document:', error)
    showSnackbar('Failed to delete vision document: ' + error.message, 'error')
  } finally {
    docToDelete.value = null
  }
}
```

**Add Dialog**:
```vue
<v-dialog v-model="showDeleteDocumentConfirmDialog" max-width="400" persistent>
  <v-card>
    <v-card-title class="text-error">Delete Vision Document?</v-card-title>

    <v-divider></v-divider>

    <v-card-text>
      Are you sure you want to delete <strong>{{ docToDelete?.filename || docToDelete?.document_name }}</strong>?
      This action cannot be undone.
    </v-card-text>

    <v-divider></v-divider>

    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn variant="text" @click="showDeleteDocumentConfirmDialog = false">
        Cancel
      </v-btn>
      <v-btn color="error" variant="flat" @click="deleteConfirmedVisionDocument">
        Delete
      </v-btn>
    </v-card-actions>
  </v-card>
</v-dialog>
```

---

## High Priority Fix 3: Improved File Upload Error Handling

**File**: `F:\GiljoAI_MCP\frontend\src\views\ProductsView.vue` lines 819-839

**Current Code**:
```javascript
for (let i = 0; i < visionFiles.value.length; i++) {
  const file = visionFiles.value[i]

  try {
    const formData = new FormData()
    formData.append('product_id', productId)
    formData.append('document_name', file.name.replace(/\.[^/.]+$/, ''))
    formData.append('document_type', 'vision')
    formData.append('vision_file', file)
    formData.append('auto_chunk', 'true')

    await api.visionDocuments.upload(formData)
  } catch (uploadError) {
    console.error(`Failed to upload ${file.name}:`, uploadError)
    // Continue uploading other files
  }
}
```

**Fixed Code**:
```javascript
const uploadErrors = []

for (let i = 0; i < visionFiles.value.length; i++) {
  const file = visionFiles.value[i]

  // Validate file type on client side
  const allowedExtensions = ['.md', '.txt', '.markdown']
  const fileExtension = '.' + file.name.split('.').pop().toLowerCase()

  if (!allowedExtensions.includes(fileExtension)) {
    uploadErrors.push(`${file.name}: Invalid file type. Allowed: .md, .txt`)
    continue
  }

  try {
    const formData = new FormData()
    formData.append('product_id', productId)
    formData.append('document_name', file.name.replace(/\.[^/.]+$/, ''))
    formData.append('document_type', 'vision')
    formData.append('vision_file', file)
    formData.append('auto_chunk', 'true')

    await api.visionDocuments.upload(formData)
  } catch (uploadError) {
    const errorMsg = uploadError.response?.data?.detail || uploadError.message
    uploadErrors.push(`${file.name}: ${errorMsg}`)
  }
}

// Show aggregated feedback
if (uploadErrors.length > 0) {
  showSnackbar(
    'Some files failed to upload:\n' + uploadErrors.join('\n'),
    'error'
  )
}
```

---

## Medium Priority Fix 1: Improve Vision Document Field Handling

**File**: `F:\GiljoAI_MCP\frontend\src\views\ProductsView.vue` lines 284, 351, 459

**Current Code** (multiple locations):
```vue
{{ doc.filename || doc.document_name }}
```

**Issue**: Need to verify backend field names

**Recommended Fix**:
1. Check VisionDocument model in `src/giljo_mcp/models.py` for actual field names
2. Update consistently across component

**If field name is `document_name`**:
Replace all instances of `{{ doc.filename || doc.document_name }}` with `{{ doc.document_name }}`

**If field name is `filename`**:
Replace all instances with `{{ doc.filename }}`

**Best Practice**:
```vue
<!-- For robustness, handle both with fallback to ID -->
{{ doc.filename || doc.document_name || `Document-${doc.id}` }}
```

---

## Implementation Timeline

### Phase 1: Critical Fixes (1 hour)
1. Update ProductResponse schema
2. Fix list_products endpoint
3. Fix get_product endpoint
4. Fix API endpoint URLs
5. Test API calls with Postman/curl

### Phase 2: High Priority Fixes (45 minutes)
1. Add toast notifications
2. Add vision document deletion confirmation
3. Improve file upload error handling
4. Test all notifications appear

### Phase 3: QA & Testing (1 hour)
1. Full manual testing with all fixes
2. Verify product metrics display correctly
3. Test cascade delete with accurate counts
4. Test all error scenarios
5. Accessibility audit

### Phase 4: Documentation (15 minutes)
1. Update API documentation
2. Document new response fields
3. Update handover notes

**Total Estimated Time**: 3 hours

---

## Testing Checklist After Fixes

- [ ] Product list shows correct unresolved_tasks count
- [ ] Product list shows correct unfinished_projects count
- [ ] Product list shows correct vision_documents_count
- [ ] Product details dialog shows accurate statistics
- [ ] Cascade delete shows accurate impact counts
- [ ] Create product success notification appears
- [ ] Update product success notification appears
- [ ] Delete product success notification appears
- [ ] Delete vision document shows confirmation dialog
- [ ] Delete vision document success notification appears
- [ ] Invalid file type upload shows error
- [ ] All keyboard interactions work (Tab, Enter, Escape)
- [ ] Responsive design works on mobile/tablet
- [ ] No console errors or warnings

---

## Database Relationships to Verify

Before implementing, verify these relationships exist in models:

```python
# In Product model
projects = relationship("Project", cascade="all, delete-orphan")
tasks = relationship("Task", cascade="all, delete-orphan")
vision_documents = relationship("VisionDocument", cascade="all, delete-orphan")

# Task.status should have options: 'pending', 'in_progress', 'completed', etc.
# Project.status should have options: 'pending', 'active', 'completed', etc.
```

Check: `F:\GiljoAI_MCP\src\giljo_mcp\models.py`

---

**Prepared By**: Frontend Tester Agent
**Date**: 2025-10-25
**Status**: Ready for Developer Implementation
