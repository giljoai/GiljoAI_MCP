# Files to Modify: Product Form Auto-Save & UX Polish

**Date**: 2025-10-27
**Handover**: 0051

## Overview

This document lists all files that will be created or modified during Handover 0051 implementation.

## Files to Create (New Files)

### 1. Auto-Save Composable

**File**: `frontend/src/composables/useAutoSave.js`
**Lines**: ~200 lines
**Purpose**: Reusable composable for auto-saving form data to LocalStorage

**Key Functions**:
- `saveToCache()` - Save to LocalStorage
- `restoreFromCache()` - Load from LocalStorage
- `clearCache()` - Remove from LocalStorage
- Watch with debounce
- Save status tracking

**Dependencies**:
- `vue` (ref, watch, onMounted, onUnmounted)
- `lodash-es` (debounce)

**Exports**:
```javascript
export function useAutoSave(options) {
  return {
    saveStatus,        // Ref<'saved' | 'saving' | 'unsaved' | 'error'>
    lastSaved,         // Ref<number | null>
    hasUnsavedChanges, // Ref<boolean>
    saveToCache,       // Function
    saveToBackend,     // Function
    restoreFromCache,  // Function
    clearCache,        // Function
    forceSave,         // Function
  }
}
```

---

## Files to Modify (Existing Files)

### 2. ProductsView Component

**File**: `frontend/src/views/ProductsView.vue`
**Current Lines**: ~1700 lines
**Estimated Changes**: +150 lines

#### Section 2.1: Script Section (Lines 1229-1560)

**Changes**:

1. **Add Import** (Line ~1236):
```javascript
import { useAutoSave } from '@/composables/useAutoSave'
```

2. **Add Auto-Save State** (Line ~1268):
```javascript
const autoSave = ref(null)
```

3. **Add Watch for Dialog Open/Close** (Line ~1400, after existing watches):
```javascript
// Auto-save initialization
watch(showDialog, (isOpen) => {
  if (isOpen) {
    // Generate cache key based on edit mode
    const cacheKey = editingProduct.value
      ? `product_form_draft_${editingProduct.value.id}`
      : 'product_form_draft_new'

    // Initialize auto-save
    autoSave.value = useAutoSave({
      key: cacheKey,
      data: productForm,
      debounceMs: 500,
      enableBackgroundSave: false,
    })

    // Try to restore from cache
    const cached = autoSave.value.restoreFromCache()
    if (cached) {
      const shouldRestore = confirm(
        'Found unsaved changes from a previous session. Do you want to restore them?'
      )
      if (shouldRestore) {
        productForm.value = { ...cached }
        console.log('[PRODUCT] Restored draft from cache')
      } else {
        autoSave.value.clearCache()
      }
    }
  }
})
```

4. **Add Unsaved Changes Computed Property** (Line ~1350):
```javascript
const hasUnsavedChanges = computed(() => {
  return autoSave.value?.hasUnsavedChanges.value || false
})
```

5. **Add Tab Validation Computed Property** (Line ~1360):
```javascript
const tabValidation = computed(() => {
  return {
    basic: {
      valid: !!productForm.value.name,
      hasError: !productForm.value.name,
    },
    vision: {
      valid: true,
      hasError: false,
    },
    tech: {
      valid: true,
      hasError: false,
      hasWarning: !productForm.value.configData.tech_stack.languages,
    },
    arch: {
      valid: true,
      hasError: false,
    },
    features: {
      valid: true,
      hasError: false,
    },
  }
})
```

6. **Add Testing Strategies Data** (Line ~1370):
```javascript
const testingStrategies = [
  {
    value: 'TDD',
    title: 'TDD (Test-Driven Development)',
    subtitle: 'Write tests before implementation code',
  },
  {
    value: 'BDD',
    title: 'BDD (Behavior-Driven Development)',
    subtitle: 'Tests based on user stories and behavior specs',
  },
  {
    value: 'Integration-First',
    title: 'Integration-First',
    subtitle: 'Focus on testing component interactions',
  },
  {
    value: 'E2E-First',
    title: 'E2E-First',
    subtitle: 'Prioritize end-to-end user workflow tests',
  },
  {
    value: 'Manual',
    title: 'Manual Testing',
    subtitle: 'Human-driven QA and exploratory testing',
  },
  {
    value: 'Hybrid',
    title: 'Hybrid Approach',
    subtitle: 'Combination of multiple testing strategies',
  },
]
```

7. **Add Browser Beforeunload Handler** (Line ~1550):
```javascript
function handleBeforeUnload(event) {
  if (showDialog.value && hasUnsavedChanges.value) {
    event.preventDefault()
    event.returnValue = '' // Standard way to trigger browser dialog
  }
}

onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
  // ... existing onMounted code
})

onUnmounted(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
})
```

8. **Modify `saveProduct()` Function** (Lines 1561-1629):
```javascript
async function saveProduct() {
  if (!formValid.value) return

  saving.value = true
  try {
    // Step 1: Create/Update product
    let product
    if (editingProduct.value) {
      product = await productStore.updateProduct(editingProduct.value.id, {
        name: productForm.value.name,
        description: productForm.value.description,
        configData: productForm.value.configData,
      })
    } else {
      product = await productStore.createProduct({
        name: productForm.value.name,
        description: productForm.value.description,
        configData: productForm.value.configData,
      })
    }

    // Step 2: Upload vision files (if any)
    // ... existing upload logic ...

    // Step 3: Clear auto-save cache on success (NEW)
    if (autoSave.value) {
      autoSave.value.clearCache()
    }

    // Step 4: Refresh products
    await loadProducts()

    // Step 5: Close dialog
    closeDialog()

    // Step 6: Show success message
    showToast({
      message: editingProduct.value
        ? 'Product updated successfully'
        : 'Product created successfully',
      type: 'success',
      duration: 3000,
    })
  } catch (error) {
    console.error('Failed to save product:', error)
    showToast({
      message: 'Failed to save product',
      type: 'error',
      duration: 5000,
    })
  } finally {
    saving.value = false
  }
}
```

9. **Modify `closeDialog()` Function** (Line ~1450):
```javascript
function closeDialog() {
  // Check for unsaved changes (NEW)
  if (hasUnsavedChanges.value) {
    const confirmed = confirm(
      'You have unsaved changes. Are you sure you want to close without saving?'
    )
    if (!confirmed) return
  }

  // Clear auto-save cache (NEW)
  if (autoSave.value) {
    autoSave.value.clearCache()
  }

  // Existing cleanup
  showDialog.value = false
  editingProduct.value = null
  productForm.value = {
    name: '',
    description: '',
    visionPath: '',
    configData: {
      tech_stack: {
        languages: '',
        frontend: '',
        backend: '',
        database: '',
        infrastructure: '',
      },
      architecture: {
        pattern: '',
        design_patterns: '',
        api_style: '',
        notes: '',
      },
      features: {
        core: '',
      },
      test_config: {
        strategy: 'TDD',
        coverage_target: 80,
        frameworks: '',
      },
    },
  }
  visionFiles.value = []
  existingVisionDocuments.value = []
  dialogTab.value = 'basic'
  formValid.value = false
}
```

#### Section 2.2: Template Section (Lines 1-1228)

**Changes**:

1. **Modify Dialog Header** (Lines ~250-260):
```vue
<v-card-title class="d-flex align-center">
  <span class="text-h5">
    {{ editingProduct ? 'Edit Product' : 'New Product' }}
  </span>
  <v-spacer></v-spacer>

  <!-- Save status indicator (NEW) -->
  <v-chip
    v-if="autoSave && autoSave.saveStatus.value !== 'saved'"
    :color="autoSave.saveStatus.value === 'saving' ? 'info' : 'warning'"
    size="small"
    variant="flat"
    class="mr-2"
  >
    <v-icon start size="small">
      {{ autoSave.saveStatus.value === 'saving' ? 'mdi-loading mdi-spin' : 'mdi-content-save-alert' }}
    </v-icon>
    {{ autoSave.saveStatus.value === 'saving' ? 'Saving...' : 'Unsaved changes' }}
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

2. **Modify Dialog Component** (Line ~240):
```vue
<!-- Change from max-width="900px" to max-width="900px" persistent -->
<v-dialog v-model="showDialog" max-width="900px" persistent>
```

3. **Add Tab Validation Indicators** (Lines ~270-290):
```vue
<v-tabs v-model="dialogTab" class="mb-4">
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

  <v-tab value="vision">Vision Docs</v-tab>

  <v-tab value="tech">
    Tech Stack
    <v-badge
      v-if="tabValidation.tech.hasWarning"
      color="warning"
      dot
      inline
      class="ml-2"
    ></v-badge>
  </v-tab>

  <v-tab value="arch">Architecture</v-tab>

  <v-tab value="features">Features & Testing</v-tab>
</v-tabs>
```

4. **Modify Testing Strategy Field** (Lines ~700-720, in Features tab):
```vue
<!-- Replace v-select with enhanced version -->
<v-select
  v-model="productForm.configData.test_config.strategy"
  :items="testingStrategies"
  item-title="title"
  item-value="value"
  label="Testing Strategy"
  variant="outlined"
  density="comfortable"
  class="mb-4"
>
  <template #item="{ props, item }">
    <v-list-item v-bind="props">
      <v-list-item-title>{{ item.raw.title }}</v-list-item-title>
      <v-list-item-subtitle class="text-wrap">{{ item.raw.subtitle }}</v-list-item-subtitle>
    </v-list-item>
  </template>
</v-select>
```

---

### 3. Products Store (Optional - for debugging)

**File**: `frontend/src/stores/products.js`
**Current Lines**: 296 lines
**Estimated Changes**: +10 lines (logging only)

**Changes**:

1. **Add Logging to createProduct** (Lines 132-148):
```javascript
async function createProduct(productData) {
  console.log('[STORE] createProduct called with:', productData) // NEW
  loading.value = true
  error.value = null
  try {
    const response = await api.products?.create(productData)
    console.log('[STORE] API response:', response) // NEW
    if (response.data) {
      products.value.push(response.data)
      await setCurrentProduct(response.data.id)
    }
    return response.data
  } catch (err) {
    console.error('[STORE] createProduct failed:', err) // NEW
    error.value = err.message
    throw err
  } finally {
    loading.value = false
  }
}
```

2. **Add Logging to updateProduct** (Lines 151-173):
```javascript
async function updateProduct(productId, updates) {
  console.log('[STORE] updateProduct called:', { productId, updates }) // NEW
  loading.value = true
  error.value = null
  try {
    const response = await api.products?.update(productId, updates)
    console.log('[STORE] API response:', response) // NEW
    if (response.data) {
      const index = products.value.findIndex((p) => p.id === productId)
      if (index !== -1) {
        products.value[index] = response.data
      }
      if (productId === currentProductId.value) {
        currentProduct.value = response.data
      }
    }
    return response.data
  } catch (err) {
    console.error('[STORE] updateProduct failed:', err) // NEW
    error.value = err.message
    throw err
  } finally {
    loading.value = false
  }
}
```

**Note**: These logging statements can be removed after Phase 1 debugging is complete, or kept behind a `DEBUG` flag.

---

### 4. API Service (If configData Not Being Stringified)

**File**: `frontend/src/services/api.js` (assumed location)
**Current Lines**: Unknown
**Estimated Changes**: +5 lines

**Potential Fix** (if bug found in Phase 1):

```javascript
export default {
  products: {
    async create(productData) {
      const formData = new FormData()
      formData.append('name', productData.name)

      if (productData.description) {
        formData.append('description', productData.description)
      }

      // FIX: Ensure configData is JSON string (NEW)
      if (productData.configData) {
        formData.append('config_data', JSON.stringify(productData.configData))
      }

      const response = await axios.post('/api/products/', formData)
      return response
    },

    async update(productId, updates) {
      const formData = new FormData()

      if (updates.name !== undefined) {
        formData.append('name', updates.name)
      }

      if (updates.description !== undefined) {
        formData.append('description', updates.description)
      }

      // FIX: Ensure configData is JSON string (NEW)
      if (updates.configData !== undefined) {
        formData.append('config_data', JSON.stringify(updates.configData))
      }

      const response = await axios.put(`/api/products/${productId}`, formData)
      return response
    },
  },
}
```

**Note**: Only modify if Phase 1 debugging identifies this as the issue.

---

### 5. Backend Products Endpoint (Optional - for debugging)

**File**: `api/endpoints/products.py`
**Current Lines**: ~750 lines
**Estimated Changes**: +15 lines (logging only)

**Changes**:

1. **Add Logging to create_product** (Lines 115-249):
```python
@router.post("/", response_model=ProductResponse)
async def create_product(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    vision_file: Optional[UploadFile] = File(None),
    config_data: Optional[str] = Form(None),
    tenant_key: str = Depends(get_tenant_key),
):
    """Create a new product with optional vision document upload"""
    from api.app import state
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"[PRODUCTS] Creating product: name={name}, has_config_data={bool(config_data)}")  # NEW

    if config_data:
        logger.info(f"[PRODUCTS] config_data received (length={len(config_data)})")  # NEW
        logger.debug(f"[PRODUCTS] config_data: {config_data[:500]}...")  # NEW

    try:
        config_dict: Dict[str, Any] = {}
        if config_data:
            try:
                config_dict = json.loads(config_data)
                logger.info(f"[PRODUCTS] Parsed config_dict keys: {config_dict.keys()}")  # NEW
            except json.JSONDecodeError as e:
                logger.error(f"[PRODUCTS] Failed to parse config_data: {e}")  # NEW
                raise HTTPException(status_code=400, detail=f"Invalid config_data JSON: {str(e)}")

        product = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name=name,
            description=description,
            config_data=config_dict,
        )

        async with state.db_manager.get_session_async() as db:
            db.add(product)
            await db.commit()
            await db.refresh(product)

            logger.info(f"[PRODUCTS] Product saved: id={product.id}, has_config_data={bool(product.config_data)}")  # NEW

        # ... rest of function
```

2. **Add Similar Logging to update_product** (Lines 251-320):
```python
@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    config_data: Optional[str] = Form(None),
    tenant_key: str = Depends(get_tenant_key),
):
    """Update an existing product (Handover 0042)"""
    from api.app import state
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"[PRODUCTS] Updating product: id={product_id}, has_config_data={bool(config_data)}")  # NEW

    try:
        async with state.db_manager.get_session_async() as db:
            # ... fetch product ...

            if config_data is not None:
                try:
                    config_dict = json.loads(config_data)
                    logger.info(f"[PRODUCTS] Updating config_data: {config_dict.keys()}")  # NEW
                    product.config_data = config_dict
                except json.JSONDecodeError as e:
                    logger.error(f"[PRODUCTS] Failed to parse config_data: {e}")  # NEW
                    raise HTTPException(status_code=400, detail=f"Invalid config_data JSON: {str(e)}")

            # ... rest of update logic ...
```

**Note**: These logging statements can be removed after Phase 1 debugging, or kept behind a `DEBUG` flag.

---

## Files NOT to Modify

### Database Models
**File**: `src/giljo_mcp/models.py`
**Reason**: No database schema changes required. Product model already has `config_data` JSONB column.

### Database Migrations
**File**: `alembic/versions/*`
**Reason**: No migrations needed. Schema supports existing functionality.

### API Routes Registration
**File**: `api/app.py`
**Reason**: No new routes added. Existing `/api/products/` routes used.

---

## Summary of Changes

| File | Type | Lines Added | Lines Modified | Priority |
|------|------|-------------|----------------|----------|
| `frontend/src/composables/useAutoSave.js` | NEW | ~200 | 0 | HIGH |
| `frontend/src/views/ProductsView.vue` | MODIFY | ~150 | ~50 | HIGH |
| `frontend/src/stores/products.js` | MODIFY | ~10 | 0 | LOW (debug only) |
| `frontend/src/services/api.js` | MODIFY | ~5 | ~10 | MEDIUM (if needed) |
| `api/endpoints/products.py` | MODIFY | ~15 | 0 | LOW (debug only) |

**Total Estimated Changes**: ~380 new lines, ~60 modified lines

---

## Rollback Plan

If issues arise, rollback is straightforward:

1. **Phase 1**: Remove logging statements (git revert or manual removal)
2. **Phase 2**: Remove auto-save integration from ProductsView.vue
3. **Phase 3**: Remove UX polish changes (revert template changes)
4. **Complete Rollback**: `git revert <commit-hash>` for entire feature branch

**No database rollback needed** - this is purely frontend changes.

---

## Dependencies to Add

### Frontend Dependencies

**File**: `frontend/package.json`

```json
{
  "dependencies": {
    "lodash-es": "^4.17.21"  // For debounce function
  }
}
```

**Installation**:
```bash
cd frontend
npm install lodash-es
```

**Note**: Most projects already have lodash installed. Verify first:
```bash
npm list lodash-es
```

---

## Configuration Changes

None required. Auto-save behavior is hardcoded (500ms debounce).

**Future Enhancement**: Add to user preferences:
```javascript
// Future: User-configurable auto-save settings
{
  "autoSave": {
    "enabled": true,
    "debounceMs": 500,
    "enableBackgroundSave": false
  }
}
```

---

**Next**: Proceed with implementation following IMPLEMENTATION_PLAN.md.
