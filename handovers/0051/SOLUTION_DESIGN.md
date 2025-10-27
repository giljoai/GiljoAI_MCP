# Solution Design: Product Form Auto-Save & UX Polish

**Date**: 2025-10-27
**Handover**: 0051

## Solution Overview

This handover implements a four-phase approach to prevent data loss and improve UX in the product form:

1. **Phase 1**: Debug and fix current save functionality (if broken)
2. **Phase 2**: Implement auto-save with LocalStorage fallback
3. **Phase 3**: Add UX polish (validation indicators, better placeholders, warnings)
4. **Phase 4**: Comprehensive testing and validation

## Phase 1: Immediate Fix - Debug Current Save

### Objective
Identify and fix any bugs in the current save flow that prevent data persistence.

### Implementation Strategy

#### Step 1.1: Add Diagnostic Logging

**File**: `frontend/src/views/ProductsView.vue`

```javascript
async function saveProduct() {
  if (!formValid.value) {
    console.error('[SAVE] Form validation failed')
    return
  }

  console.log('[SAVE] Starting save process...')
  console.log('[SAVE] Form data:', {
    name: productForm.value.name,
    description: productForm.value.description,
    configData: productForm.value.configData,
    editingProduct: editingProduct.value?.id || 'NEW',
  })

  saving.value = true
  try {
    let product
    if (editingProduct.value) {
      console.log('[SAVE] Updating existing product:', editingProduct.value.id)
      product = await productStore.updateProduct(editingProduct.value.id, {
        name: productForm.value.name,
        description: productForm.value.description,
        configData: productForm.value.configData,
      })
    } else {
      console.log('[SAVE] Creating new product')
      product = await productStore.createProduct({
        name: productForm.value.name,
        description: productForm.value.description,
        configData: productForm.value.configData,
      })
    }

    console.log('[SAVE] Product saved successfully:', product)

    // ... rest of save logic ...
  } catch (error) {
    console.error('[SAVE] Save failed with error:', {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status,
    })
    // ... existing error handling ...
  }
}
```

#### Step 1.2: Add Store Logging

**File**: `frontend/src/stores/products.js`

```javascript
async function createProduct(productData) {
  console.log('[STORE] createProduct called with:', productData)
  loading.value = true
  error.value = null
  try {
    const response = await api.products?.create(productData)
    console.log('[STORE] API response:', response)
    if (response.data) {
      products.value.push(response.data)
      await setCurrentProduct(response.data.id)
    }
    return response.data
  } catch (err) {
    console.error('[STORE] createProduct failed:', err)
    error.value = err.message
    throw err
  } finally {
    loading.value = false
  }
}
```

#### Step 1.3: Verify API Service

**File**: `frontend/src/services/api.js` (assumed location)

```javascript
// Verify that api.products.create is sending data correctly
export default {
  products: {
    async create(productData) {
      console.log('[API] Sending product create request:', productData)

      // Check if configData needs to be stringified
      const formData = new FormData()
      formData.append('name', productData.name)
      if (productData.description) {
        formData.append('description', productData.description)
      }
      if (productData.configData) {
        // IMPORTANT: Backend expects JSON string, not object
        formData.append('config_data', JSON.stringify(productData.configData))
      }

      const response = await axios.post('/api/products/', formData)
      console.log('[API] Response received:', response.data)
      return response
    },
  },
}
```

#### Step 1.4: Add Backend Logging

**File**: `api/endpoints/products.py`

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
    logger.info(f"[PRODUCTS] Creating product: name={name}, has_config_data={bool(config_data)}")

    if config_data:
        logger.info(f"[PRODUCTS] config_data received (length={len(config_data)}): {config_data[:200]}...")

    try:
        config_dict: Dict[str, Any] = {}
        if config_data:
            try:
                config_dict = json.loads(config_data)
                logger.info(f"[PRODUCTS] Parsed config_dict: {config_dict}")
            except json.JSONDecodeError as e:
                logger.error(f"[PRODUCTS] Failed to parse config_data: {e}")
                raise HTTPException(status_code=400, detail=f"Invalid config_data JSON: {str(e)}")

        product = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name=name,
            description=description,
            config_data=config_dict,  # Ensure this is being set
        )

        async with state.db_manager.get_session_async() as db:
            db.add(product)
            await db.commit()
            await db.refresh(product)

            logger.info(f"[PRODUCTS] Product saved: id={product.id}, config_data={product.config_data}")

        # ... rest of logic ...
    except Exception as e:
        logger.error(f"[PRODUCTS] Failed to create product: {e}")
        raise
```

#### Step 1.5: Manual Testing Protocol

1. **Test 1: Minimal Save**
   - Open product dialog
   - Enter only "Test Product 1" in name field
   - Click Save
   - Check console logs
   - Verify product appears in list
   - Reopen product, verify name persists

2. **Test 2: Full Save (All Tabs)**
   - Open product dialog
   - Fill out all 5 tabs with test data
   - Click Save
   - Check console logs
   - Check Network tab (request/response)
   - Query database: `SELECT * FROM products WHERE name = 'Test Product 2'`
   - Verify configData column contains JSON data
   - Reopen product, verify all fields populated

3. **Test 3: Update Existing**
   - Open existing product for edit
   - Change one field in each tab
   - Click Save
   - Verify changes persist

4. **Test 4: Network Error Simulation**
   - Open DevTools Network tab
   - Right-click → Block request pattern → `*/products/*`
   - Try to save product
   - Verify error message shown
   - Verify data NOT lost (check console for form data)

### Expected Outcomes

- **If save works**: Move to Phase 2 (auto-save implementation)
- **If save fails**: Fix identified bug, then move to Phase 2

## Phase 2: Auto-Save Implementation

### Objective
Implement automatic saving with LocalStorage fallback to prevent data loss.

### Architecture

```
User types in form field
    ↓
Vue reactivity triggers watch on productForm
    ↓
Debounced auto-save function called (500ms delay)
    ↓
Save to LocalStorage (immediate, synchronous)
    ↓
Optional: Save to backend API (background, async)
    ↓
Update save status indicator
```

### Component: Auto-Save Composable

**File**: `frontend/src/composables/useAutoSave.js` (NEW)

```javascript
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { debounce } from 'lodash-es'

export function useAutoSave(options = {}) {
  const {
    key,                          // LocalStorage key (e.g., 'product_form_draft_123')
    data,                         // Ref to watch (e.g., productForm)
    saveFunction,                 // Optional: async function to save to backend
    debounceMs = 500,             // Debounce delay in milliseconds
    enableBackgroundSave = false, // Enable automatic backend saves
  } = options

  // State
  const saveStatus = ref('saved')    // 'saved' | 'saving' | 'unsaved' | 'error'
  const lastSaved = ref(null)        // Timestamp of last save
  const hasUnsavedChanges = ref(false)

  // Save to LocalStorage (synchronous, fast)
  function saveToCache() {
    try {
      if (!key || !data.value) return

      const cacheData = {
        data: data.value,
        timestamp: Date.now(),
      }

      localStorage.setItem(key, JSON.stringify(cacheData))
      console.log('[AUTO-SAVE] Saved to LocalStorage:', key)
    } catch (error) {
      console.error('[AUTO-SAVE] Failed to save to LocalStorage:', error)
      // Handle quota exceeded error
      if (error.name === 'QuotaExceededError') {
        console.warn('[AUTO-SAVE] LocalStorage quota exceeded')
      }
    }
  }

  // Save to backend (asynchronous, optional)
  async function saveToBackend() {
    if (!saveFunction || !enableBackgroundSave) return

    try {
      saveStatus.value = 'saving'
      await saveFunction(data.value)
      saveStatus.value = 'saved'
      lastSaved.value = Date.now()
      hasUnsavedChanges.value = false
      console.log('[AUTO-SAVE] Saved to backend')
    } catch (error) {
      console.error('[AUTO-SAVE] Failed to save to backend:', error)
      saveStatus.value = 'error'
    }
  }

  // Debounced save function
  const debouncedSave = debounce(async () => {
    saveToCache()
    if (enableBackgroundSave) {
      await saveToBackend()
    } else {
      saveStatus.value = 'saved'
      lastSaved.value = Date.now()
    }
  }, debounceMs)

  // Watch for changes
  const stopWatch = watch(
    () => data.value,
    () => {
      hasUnsavedChanges.value = true
      saveStatus.value = 'unsaved'
      debouncedSave()
    },
    { deep: true }
  )

  // Restore from cache
  function restoreFromCache() {
    try {
      if (!key) return null

      const cached = localStorage.getItem(key)
      if (!cached) return null

      const cacheData = JSON.parse(cached)
      console.log('[AUTO-SAVE] Restored from cache:', {
        key,
        age: Date.now() - cacheData.timestamp,
      })

      return cacheData.data
    } catch (error) {
      console.error('[AUTO-SAVE] Failed to restore from cache:', error)
      return null
    }
  }

  // Clear cache
  function clearCache() {
    try {
      if (!key) return
      localStorage.removeItem(key)
      console.log('[AUTO-SAVE] Cleared cache:', key)
    } catch (error) {
      console.error('[AUTO-SAVE] Failed to clear cache:', error)
    }
  }

  // Cleanup on unmount
  onUnmounted(() => {
    stopWatch()
    debouncedSave.cancel()
  })

  return {
    // State
    saveStatus,
    lastSaved,
    hasUnsavedChanges,

    // Methods
    saveToCache,
    saveToBackend,
    restoreFromCache,
    clearCache,
    forceSave: () => {
      debouncedSave.cancel()
      saveToCache()
      if (enableBackgroundSave) saveToBackend()
    },
  }
}
```

### Integration into ProductsView

**File**: `frontend/src/views/ProductsView.vue`

```javascript
import { useAutoSave } from '@/composables/useAutoSave'

// ... existing imports and setup ...

// Auto-save composable
const autoSave = ref(null)

// Watch for dialog open/close
watch(showDialog, (isOpen) => {
  if (isOpen) {
    // Generate cache key
    const cacheKey = editingProduct.value
      ? `product_form_draft_${editingProduct.value.id}`
      : 'product_form_draft_new'

    // Initialize auto-save
    autoSave.value = useAutoSave({
      key: cacheKey,
      data: productForm,
      debounceMs: 500,
      enableBackgroundSave: false, // Only save to LocalStorage for now
    })

    // Try to restore from cache
    const cached = autoSave.value.restoreFromCache()
    if (cached) {
      // Ask user if they want to restore
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

// Modified save function
async function saveProduct() {
  if (!formValid.value) return

  saving.value = true
  try {
    // ... existing save logic ...

    // Clear auto-save cache on successful save
    if (autoSave.value) {
      autoSave.value.clearCache()
    }

    // ... rest of save logic ...
  } catch (error) {
    console.error('Failed to save product:', error)
    showToast({ message: 'Failed to save product', type: 'error' })
  } finally {
    saving.value = false
  }
}
```

### Save Status Indicator UI

**File**: `frontend/src/views/ProductsView.vue` (template section)

```vue
<template>
  <v-dialog v-model="showDialog" max-width="900px" persistent>
    <v-card>
      <!-- Header with save status -->
      <v-card-title class="d-flex align-center">
        <span class="text-h5">
          {{ editingProduct ? 'Edit Product' : 'New Product' }}
        </span>
        <v-spacer></v-spacer>

        <!-- Save status indicator -->
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

      <!-- ... rest of dialog ... -->
    </v-card>
  </v-dialog>
</template>
```

## Phase 3: UX Polish

### Feature 3.1: Unsaved Changes Warning

**Implementation**:

```javascript
// Computed property
const hasUnsavedChanges = computed(() => {
  return autoSave.value?.hasUnsavedChanges.value || false
})

// Close dialog handler
function closeDialog() {
  if (hasUnsavedChanges.value) {
    const confirmed = confirm(
      'You have unsaved changes. Are you sure you want to close without saving?'
    )
    if (!confirmed) return
  }

  // Clear cache
  if (autoSave.value) {
    autoSave.value.clearCache()
  }

  // Reset form
  showDialog.value = false
  editingProduct.value = null
  productForm.value = {
    name: '',
    description: '',
    visionPath: '',
    configData: { /* ... */ },
  }
  visionFiles.value = []
}

// Browser beforeunload handler
onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
})

function handleBeforeUnload(event) {
  if (showDialog.value && hasUnsavedChanges.value) {
    event.preventDefault()
    event.returnValue = '' // Standard way to trigger browser dialog
  }
}
```

### Feature 3.2: Tab Validation Indicators

**Implementation**:

```javascript
// Validation rules per tab
const tabValidation = computed(() => {
  return {
    basic: {
      valid: !!productForm.value.name,
      errors: productForm.value.name ? [] : ['Product name is required'],
    },
    vision: {
      valid: true, // Vision docs are optional
      errors: [],
    },
    tech: {
      valid: true, // All tech stack fields are optional
      errors: [],
      warning: !productForm.value.configData.tech_stack.languages,
      warnings: !productForm.value.configData.tech_stack.languages
        ? ['Consider adding programming languages']
        : [],
    },
    arch: {
      valid: true,
      errors: [],
    },
    features: {
      valid: true,
      errors: [],
    },
  }
})
```

**Template**:

```vue
<v-tabs v-model="dialogTab" class="mb-4">
  <v-tab value="basic">
    Basic Info
    <v-badge
      v-if="!tabValidation.basic.valid"
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
      v-if="tabValidation.tech.warning"
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

### Feature 3.3: Better Testing Strategy Placeholder

**Implementation**:

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

**Template**:

```vue
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
      <v-list-item-subtitle>{{ item.raw.subtitle }}</v-list-item-subtitle>
    </v-list-item>
  </template>
</v-select>
```

## Phase 4: Testing Strategy

See `TESTING.md` for comprehensive testing plan.

## Architecture Decisions

### Decision 1: LocalStorage vs. IndexedDB

**Choice**: LocalStorage
**Rationale**:
- Simpler API
- Sufficient for form data (< 5MB limit)
- Synchronous (better for immediate persistence)
- No need for complex queries

**Trade-offs**:
- Size limit (5-10MB depending on browser)
- Synchronous API (can block UI for large data)

### Decision 2: Background Auto-Save to Backend

**Choice**: LocalStorage only (for now)
**Rationale**:
- Simpler implementation
- Avoids API rate limiting concerns
- User still has control (explicit "Save" button)
- LocalStorage sufficient for data loss prevention

**Future Enhancement**: Enable background API saves as opt-in feature

### Decision 3: Debounce Timing

**Choice**: 500ms
**Rationale**:
- Fast enough for good UX (user types, pauses, saved)
- Slow enough to avoid excessive saves
- Standard debounce timing for form inputs

**Configurable**: Can be adjusted per feedback

### Decision 4: Restore Confirmation

**Choice**: Ask user before restoring cached data
**Rationale**:
- User might have intentionally abandoned previous session
- Transparency about data restoration
- Prevents confusion

**Alternative**: Auto-restore with "Undo restore" option

## Security Considerations

1. **LocalStorage is per-origin**: Data isolated by domain, no cross-site access
2. **No sensitive data**: Product form doesn't contain passwords or tokens
3. **XSS mitigation**: Vue automatically escapes user input
4. **Cache expiration**: Consider adding TTL to cached drafts (e.g., 7 days)

## Performance Considerations

1. **Debouncing**: Prevents excessive saves during rapid typing
2. **Deep watching**: May impact performance for very large forms (current form is small)
3. **LocalStorage sync**: Synchronous API, but fast for small data
4. **Memory**: Each draft stored in memory + LocalStorage (small footprint)

## Accessibility Considerations

1. **Save status indicator**: Use both color and text (not just color)
2. **Keyboard navigation**: Ensure save indicator doesn't trap focus
3. **Screen readers**: Add aria-live region for save status changes

---

**Next**: See `IMPLEMENTATION_PLAN.md` for step-by-step implementation guide.
