# Code Examples: Product Form Auto-Save & UX Polish

**Date**: 2025-10-27
**Handover**: 0051

## Table of Contents

1. [Auto-Save Composable (Complete Implementation)](#1-auto-save-composable)
2. [ProductsView Integration](#2-productsview-integration)
3. [Save Status Indicator UI](#3-save-status-indicator-ui)
4. [Tab Validation Indicators](#4-tab-validation-indicators)
5. [Unsaved Changes Warning](#5-unsaved-changes-warning)
6. [Enhanced Testing Strategy Dropdown](#6-enhanced-testing-strategy-dropdown)
7. [API Service Fix (If Needed)](#7-api-service-fix)
8. [Testing Examples](#8-testing-examples)

---

## 1. Auto-Save Composable

**File**: `frontend/src/composables/useAutoSave.js` (NEW FILE)

```javascript
/**
 * Auto-Save Composable
 *
 * Provides automatic form data persistence to LocalStorage with debouncing.
 * Prevents data loss from browser crashes, accidental closes, or navigation.
 *
 * @example
 * const autoSave = useAutoSave({
 *   key: 'product_form_draft_123',
 *   data: productForm,
 *   debounceMs: 500,
 * })
 *
 * // Check save status
 * console.log(autoSave.saveStatus.value) // 'saved' | 'saving' | 'unsaved' | 'error'
 *
 * // Restore from cache
 * const cached = autoSave.restoreFromCache()
 * if (cached) {
 *   productForm.value = cached
 * }
 */

import { ref, watch, onUnmounted } from 'vue'
import { debounce } from 'lodash-es'

/**
 * Auto-save composable for form data persistence
 *
 * @param {Object} options - Configuration options
 * @param {string} options.key - LocalStorage key for caching
 * @param {Ref} options.data - Reactive data reference to watch and save
 * @param {Function} [options.saveFunction] - Optional async function for backend saves
 * @param {number} [options.debounceMs=500] - Debounce delay in milliseconds
 * @param {boolean} [options.enableBackgroundSave=false] - Enable automatic backend saves
 * @returns {Object} Auto-save utilities and state
 */
export function useAutoSave(options = {}) {
  const {
    key,
    data,
    saveFunction,
    debounceMs = 500,
    enableBackgroundSave = false,
  } = options

  // Validate required options
  if (!key) {
    console.warn('[AUTO-SAVE] No key provided, auto-save disabled')
  }
  if (!data) {
    console.warn('[AUTO-SAVE] No data ref provided, auto-save disabled')
  }

  // State
  const saveStatus = ref('saved')           // 'saved' | 'saving' | 'unsaved' | 'error'
  const lastSaved = ref(null)               // Timestamp of last save
  const hasUnsavedChanges = ref(false)      // Flag for unsaved changes
  const errorMessage = ref(null)            // Last error message

  /**
   * Save data to LocalStorage (synchronous, fast)
   * Includes timestamp for cache age tracking
   */
  function saveToCache() {
    if (!key || !data.value) return

    try {
      const cacheData = {
        data: data.value,
        timestamp: Date.now(),
        version: '1.0', // For future cache format migrations
      }

      localStorage.setItem(key, JSON.stringify(cacheData))
      console.log('[AUTO-SAVE] Saved to LocalStorage:', {
        key,
        size: JSON.stringify(cacheData).length,
        timestamp: cacheData.timestamp,
      })

      return true
    } catch (error) {
      console.error('[AUTO-SAVE] Failed to save to LocalStorage:', error)

      // Handle quota exceeded error
      if (error.name === 'QuotaExceededError') {
        console.warn('[AUTO-SAVE] LocalStorage quota exceeded')
        errorMessage.value = 'Storage quota exceeded. Changes saved in memory only.'
        saveStatus.value = 'error'
      } else {
        errorMessage.value = 'Failed to save draft. Changes saved in memory only.'
        saveStatus.value = 'error'
      }

      return false
    }
  }

  /**
   * Save data to backend (asynchronous, optional)
   * Only used if enableBackgroundSave is true
   */
  async function saveToBackend() {
    if (!saveFunction || !enableBackgroundSave) return

    try {
      saveStatus.value = 'saving'
      await saveFunction(data.value)
      saveStatus.value = 'saved'
      lastSaved.value = Date.now()
      hasUnsavedChanges.value = false
      errorMessage.value = null

      console.log('[AUTO-SAVE] Saved to backend successfully')
      return true
    } catch (error) {
      console.error('[AUTO-SAVE] Failed to save to backend:', error)
      saveStatus.value = 'error'
      errorMessage.value = 'Failed to save to server. Changes cached locally.'
      return false
    }
  }

  /**
   * Debounced save function
   * Triggers after user stops typing for debounceMs milliseconds
   */
  const debouncedSave = debounce(async () => {
    if (!key || !data.value) return

    // Always save to LocalStorage (fast, synchronous)
    const cacheSuccess = saveToCache()

    // Optionally save to backend (slow, asynchronous)
    if (enableBackgroundSave && cacheSuccess) {
      await saveToBackend()
    } else if (cacheSuccess) {
      // LocalStorage save succeeded, update status
      saveStatus.value = 'saved'
      lastSaved.value = Date.now()
      hasUnsavedChanges.value = false
      errorMessage.value = null
    }
  }, debounceMs)

  /**
   * Watch for changes in data
   * Triggers debounced save on any change
   */
  const stopWatch = watch(
    () => data.value,
    () => {
      hasUnsavedChanges.value = true
      saveStatus.value = 'unsaved'
      debouncedSave()
    },
    { deep: true } // Watch nested properties
  )

  /**
   * Restore data from LocalStorage cache
   * Returns cached data if exists, null otherwise
   *
   * @returns {Object|null} Cached data or null
   */
  function restoreFromCache() {
    if (!key) return null

    try {
      const cached = localStorage.getItem(key)
      if (!cached) {
        console.log('[AUTO-SAVE] No cached data found:', key)
        return null
      }

      const cacheData = JSON.parse(cached)

      // Validate cache structure
      if (!cacheData.data || !cacheData.timestamp) {
        console.warn('[AUTO-SAVE] Invalid cache format, clearing:', key)
        clearCache()
        return null
      }

      // Calculate cache age
      const ageMs = Date.now() - cacheData.timestamp
      const ageMinutes = Math.round(ageMs / 60000)

      console.log('[AUTO-SAVE] Restored from cache:', {
        key,
        age: `${ageMinutes} minutes ago`,
        size: cached.length,
      })

      return cacheData.data
    } catch (error) {
      console.error('[AUTO-SAVE] Failed to restore from cache:', error)

      // Clear corrupted cache
      try {
        clearCache()
      } catch (clearError) {
        console.error('[AUTO-SAVE] Failed to clear corrupted cache:', clearError)
      }

      return null
    }
  }

  /**
   * Clear cache from LocalStorage
   * Should be called after successful explicit save
   */
  function clearCache() {
    if (!key) return

    try {
      localStorage.removeItem(key)
      console.log('[AUTO-SAVE] Cleared cache:', key)
      hasUnsavedChanges.value = false
      saveStatus.value = 'saved'
      errorMessage.value = null
    } catch (error) {
      console.error('[AUTO-SAVE] Failed to clear cache:', error)
    }
  }

  /**
   * Force immediate save (bypass debounce)
   * Useful before navigation or explicit save
   */
  function forceSave() {
    // Cancel pending debounced save
    debouncedSave.cancel()

    // Save immediately
    const cacheSuccess = saveToCache()

    if (enableBackgroundSave && cacheSuccess) {
      return saveToBackend()
    } else {
      saveStatus.value = 'saved'
      lastSaved.value = Date.now()
      hasUnsavedChanges.value = false
      return Promise.resolve(cacheSuccess)
    }
  }

  /**
   * Get cache metadata without loading full data
   * Useful for showing cache age or checking existence
   *
   * @returns {Object|null} Cache metadata or null
   */
  function getCacheMetadata() {
    if (!key) return null

    try {
      const cached = localStorage.getItem(key)
      if (!cached) return null

      const cacheData = JSON.parse(cached)
      const ageMs = Date.now() - cacheData.timestamp

      return {
        exists: true,
        timestamp: cacheData.timestamp,
        ageMs,
        ageMinutes: Math.round(ageMs / 60000),
        ageHours: Math.round(ageMs / 3600000),
        version: cacheData.version || 'unknown',
        sizeBytes: cached.length,
      }
    } catch (error) {
      console.error('[AUTO-SAVE] Failed to get cache metadata:', error)
      return null
    }
  }

  // Cleanup on unmount
  onUnmounted(() => {
    stopWatch()
    debouncedSave.cancel()
    console.log('[AUTO-SAVE] Cleanup complete:', key)
  })

  // Return public API
  return {
    // State (reactive refs)
    saveStatus,
    lastSaved,
    hasUnsavedChanges,
    errorMessage,

    // Methods
    saveToCache,
    saveToBackend,
    restoreFromCache,
    clearCache,
    forceSave,
    getCacheMetadata,

    // Internal (for testing)
    _stopWatch: stopWatch,
    _debouncedSave: debouncedSave,
  }
}
```

---

## 2. ProductsView Integration

**File**: `frontend/src/views/ProductsView.vue` (MODIFY)

### Script Section Changes

```javascript
<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useProductStore } from '@/stores/products'
import { useSettingsStore } from '@/stores/settings'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { useFieldPriority } from '@/composables/useFieldPriority'
import { useAutoSave } from '@/composables/useAutoSave' // NEW IMPORT
import api from '@/services/api'

const productStore = useProductStore()
const settingsStore = useSettingsStore()
const router = useRouter()
const { showToast } = useToast()
const { getPriorityForField, getPriorityLabel, getPriorityColor, getPriorityTooltip } =
  useFieldPriority()

// Existing state...
const loading = ref(false)
const search = ref('')
const sortBy = ref('name')
const showDialog = ref(false)
const showDeleteDialog = ref(false)
const showDetailsDialog = ref(false)
const editingProduct = ref(null)
const deletingProduct = ref(null)
const selectedProduct = ref(null)
const saving = ref(false)
const deleting = ref(false)
const formValid = ref(false)
const formRef = ref(null)
const visionFiles = ref([])
const existingVisionDocuments = ref([])
const detailsVisionDocuments = ref([])
const cascadeImpact = ref(null)
const loadingCascadeImpact = ref(false)
const deleteConfirmationName = ref('')
const deleteConfirmationCheck = ref(false)
const deleteConfirmationError = ref(false)
const dialogTab = ref('basic')

// NEW: Auto-save state
const autoSave = ref(null)

// NEW: Unsaved changes computed property
const hasUnsavedChanges = computed(() => {
  return autoSave.value?.hasUnsavedChanges.value || false
})

// NEW: Tab validation computed property
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

// NEW: Testing strategies data
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

// Existing productForm...
const productForm = ref({
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
})

// NEW: Watch for dialog open/close to initialize auto-save
watch(showDialog, (isOpen) => {
  if (isOpen) {
    // Generate unique cache key
    const cacheKey = editingProduct.value
      ? `product_form_draft_${editingProduct.value.id}`
      : 'product_form_draft_new'

    console.log('[PRODUCT] Initializing auto-save with key:', cacheKey)

    // Initialize auto-save composable
    autoSave.value = useAutoSave({
      key: cacheKey,
      data: productForm,
      debounceMs: 500,
      enableBackgroundSave: false, // Only LocalStorage for now
    })

    // Check for cached draft
    const cached = autoSave.value.restoreFromCache()
    if (cached) {
      const metadata = autoSave.value.getCacheMetadata()
      const ageMinutes = metadata?.ageMinutes || 0

      const shouldRestore = confirm(
        `Found unsaved changes from ${ageMinutes} minute(s) ago. Do you want to restore them?`
      )

      if (shouldRestore) {
        productForm.value = { ...cached }
        console.log('[PRODUCT] Restored draft from cache')
        showToast({
          message: 'Draft restored successfully',
          type: 'info',
          duration: 3000,
        })
      } else {
        autoSave.value.clearCache()
        console.log('[PRODUCT] User declined draft restoration, cache cleared')
      }
    }
  }
})

// Modified saveProduct function
async function saveProduct() {
  if (!formValid.value) {
    console.warn('[PRODUCT] Form validation failed')
    return
  }

  saving.value = true
  try {
    console.log('[PRODUCT] Saving product with data:', {
      name: productForm.value.name,
      description: productForm.value.description,
      hasConfigData: !!productForm.value.configData,
    })

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

    console.log('[PRODUCT] Product saved successfully:', product)

    // Step 2: Upload vision files (if any)
    if (visionFiles.value && visionFiles.value.length > 0) {
      const productId = product?.id || editingProduct.value.id

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
    }

    // Step 3: Clear auto-save cache on successful save (NEW)
    if (autoSave.value) {
      autoSave.value.clearCache()
      console.log('[PRODUCT] Auto-save cache cleared after successful save')
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
    console.error('[PRODUCT] Failed to save product:', error)

    // Enhanced error messaging
    let errorMessage = 'Failed to save product'
    if (error.response) {
      if (error.response.status === 400) {
        errorMessage = 'Invalid form data: ' + (error.response.data.detail || 'Unknown error')
      } else if (error.response.status === 401) {
        errorMessage = 'Session expired. Please login again.'
      } else if (error.response.status === 500) {
        errorMessage = 'Server error. Please try again.'
      }
    } else if (error.request) {
      errorMessage = 'Network error. Please check your connection.'
    }

    showToast({
      message: errorMessage,
      type: 'error',
      duration: 5000,
    })

    // IMPORTANT: Don't close dialog on error so user can retry
  } finally {
    saving.value = false
  }
}

// Modified closeDialog function
function closeDialog() {
  // Check for unsaved changes (NEW)
  if (hasUnsavedChanges.value) {
    const confirmed = confirm(
      'You have unsaved changes. Are you sure you want to close without saving?'
    )
    if (!confirmed) {
      console.log('[PRODUCT] User cancelled dialog close due to unsaved changes')
      return
    }
  }

  // Clear auto-save cache (NEW)
  if (autoSave.value) {
    autoSave.value.clearCache()
    console.log('[PRODUCT] Auto-save cache cleared on dialog close')
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

// NEW: Browser beforeunload handler
function handleBeforeUnload(event) {
  if (showDialog.value && hasUnsavedChanges.value) {
    event.preventDefault()
    event.returnValue = '' // Standard way to trigger browser warning
  }
}

onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
  // ... existing onMounted code
})

onUnmounted(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
})

// ... rest of existing functions ...
</script>
```

---

## 3. Save Status Indicator UI

**File**: `frontend/src/views/ProductsView.vue` (MODIFY - Template Section)

```vue
<template>
  <!-- Product Dialog -->
  <v-dialog v-model="showDialog" max-width="900px" persistent>
    <v-card>
      <!-- Dialog Header with Save Status -->
      <v-card-title class="d-flex align-center py-4">
        <span class="text-h5 font-weight-bold">
          {{ editingProduct ? 'Edit Product' : 'New Product' }}
        </span>
        <v-spacer></v-spacer>

        <!-- Save Status Indicator (NEW) -->
        <v-fade-transition>
          <v-chip
            v-if="autoSave && autoSave.saveStatus.value === 'saving'"
            color="info"
            size="small"
            variant="flat"
            class="mr-2"
          >
            <v-icon start size="small" class="mdi-spin">mdi-loading</v-icon>
            Saving...
          </v-chip>

          <v-chip
            v-else-if="autoSave && autoSave.saveStatus.value === 'unsaved'"
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

          <v-chip
            v-else-if="autoSave && autoSave.saveStatus.value === 'error'"
            color="error"
            size="small"
            variant="flat"
            class="mr-2"
          >
            <v-icon start size="small">mdi-alert-circle</v-icon>
            Save error
          </v-chip>
        </v-fade-transition>

        <!-- Optional: Last Saved Timestamp -->
        <v-tooltip v-if="autoSave && autoSave.lastSaved.value" location="bottom">
          <template #activator="{ props }">
            <v-chip
              v-bind="props"
              size="x-small"
              variant="text"
              class="text-caption text-medium-emphasis"
            >
              {{ formatLastSaved(autoSave.lastSaved.value) }}
            </v-chip>
          </template>
          <span>Last saved at {{ new Date(autoSave.lastSaved.value).toLocaleTimeString() }}</span>
        </v-tooltip>

        <v-btn icon="mdi-close" variant="text" @click="closeDialog"></v-btn>
      </v-card-title>

      <!-- Rest of dialog... -->
    </v-card>
  </v-dialog>
</template>

<script setup>
// ... existing script ...

// Helper function for last saved timestamp
function formatLastSaved(timestamp) {
  const seconds = Math.floor((Date.now() - timestamp) / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ago`
}
</script>

<style scoped>
/* Optional: Spin animation for loading icon */
.mdi-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
```

---

## 4. Tab Validation Indicators

**File**: `frontend/src/views/ProductsView.vue` (MODIFY - Template Section)

```vue
<template>
  <v-dialog v-model="showDialog" max-width="900px" persistent>
    <v-card>
      <v-card-title><!-- ... --></v-card-title>

      <v-divider></v-divider>

      <v-card-text>
        <v-form ref="formRef" v-model="formValid">
          <!-- Tabs with Validation Indicators (MODIFIED) -->
          <v-tabs v-model="dialogTab" class="mb-4" color="primary">
            <v-tab value="basic">
              <span class="d-flex align-center">
                Basic Info
                <v-badge
                  v-if="tabValidation.basic.hasError"
                  color="error"
                  dot
                  inline
                  class="ml-2"
                >
                  <template #badge>
                    <v-icon size="x-small">mdi-alert-circle</v-icon>
                  </template>
                </v-badge>
              </span>
            </v-tab>

            <v-tab value="vision">
              Vision Docs
            </v-tab>

            <v-tab value="tech">
              <span class="d-flex align-center">
                Tech Stack
                <v-badge
                  v-if="tabValidation.tech.hasWarning"
                  color="warning"
                  dot
                  inline
                  class="ml-2"
                >
                  <template #badge>
                    <v-icon size="x-small">mdi-information</v-icon>
                  </template>
                </v-badge>
              </span>
            </v-tab>

            <v-tab value="arch">
              Architecture
            </v-tab>

            <v-tab value="features">
              Features & Testing
            </v-tab>
          </v-tabs>

          <!-- Optional: Validation Summary Alert (NEW) -->
          <v-alert
            v-if="Object.values(tabValidation).some(t => t.hasError)"
            type="error"
            variant="tonal"
            density="compact"
            class="mb-4"
            closable
          >
            <template #prepend>
              <v-icon>mdi-alert-circle</v-icon>
            </template>
            <div class="text-body-2">
              Please fix errors in:
              <strong>{{ errorTabs.join(', ') }}</strong>
            </div>
          </v-alert>

          <!-- Tab Content Panels -->
          <v-window v-model="dialogTab">
            <!-- ... existing tab panels ... -->
          </v-window>
        </v-form>
      </v-card-text>

      <!-- ... rest of dialog ... -->
    </v-card>
  </v-dialog>
</template>

<script setup>
// ... existing script ...

// Computed property for error tab names
const errorTabs = computed(() => {
  const tabs = []
  if (tabValidation.value.basic.hasError) tabs.push('Basic Info')
  if (tabValidation.value.vision.hasError) tabs.push('Vision Docs')
  if (tabValidation.value.tech.hasError) tabs.push('Tech Stack')
  if (tabValidation.value.arch.hasError) tabs.push('Architecture')
  if (tabValidation.value.features.hasError) tabs.push('Features & Testing')
  return tabs
})
</script>
```

---

## 5. Unsaved Changes Warning

Already covered in Section 2 (ProductsView Integration), but here's a standalone example:

```javascript
// Computed property
const hasUnsavedChanges = computed(() => {
  return autoSave.value?.hasUnsavedChanges.value || false
})

// Modified close dialog with confirmation
function closeDialog() {
  if (hasUnsavedChanges.value) {
    const confirmed = confirm(
      'You have unsaved changes that will be lost. Are you sure you want to close?'
    )
    if (!confirmed) return
  }

  // Clear cache and cleanup
  if (autoSave.value) {
    autoSave.value.clearCache()
  }

  // Reset form and close
  showDialog.value = false
  // ... rest of cleanup
}

// Browser beforeunload handler
function handleBeforeUnload(event) {
  if (showDialog.value && hasUnsavedChanges.value) {
    event.preventDefault()
    event.returnValue = '' // Triggers browser's default "Leave site?" dialog
  }
}

// Register event listener
onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
})
```

---

## 6. Enhanced Testing Strategy Dropdown

**File**: `frontend/src/views/ProductsView.vue` (MODIFY - Features Tab)

```vue
<template>
  <!-- Inside Features & Testing tab window item -->
  <v-window-item value="features">
    <div class="py-4">
      <!-- Core Features Field -->
      <v-textarea
        v-model="productForm.configData.features.core"
        label="Core Features"
        placeholder="User authentication, Product CRUD, Real-time notifications, File uploads"
        hint="List the main features and capabilities of this product"
        persistent-hint
        variant="outlined"
        density="comfortable"
        rows="4"
        auto-grow
        class="mb-4"
      ></v-textarea>

      <v-divider class="my-6"></v-divider>

      <!-- Testing Configuration -->
      <div class="text-h6 mb-4">Testing Configuration</div>

      <!-- Testing Strategy Dropdown (ENHANCED) -->
      <v-select
        v-model="productForm.configData.test_config.strategy"
        :items="testingStrategies"
        item-title="title"
        item-value="value"
        label="Testing Strategy"
        hint="Choose the primary testing methodology for this product"
        persistent-hint
        variant="outlined"
        density="comfortable"
        class="mb-4"
      >
        <!-- Custom item template with subtitle -->
        <template #item="{ props, item }">
          <v-list-item
            v-bind="props"
            :title="item.raw.title"
            :subtitle="item.raw.subtitle"
          >
            <template #prepend>
              <v-avatar color="primary" size="32">
                <v-icon size="small">
                  {{ getStrategyIcon(item.raw.value) }}
                </v-icon>
              </v-avatar>
            </template>
          </v-list-item>
        </template>

        <!-- Custom selection template -->
        <template #selection="{ item }">
          <div class="d-flex align-center">
            <v-icon start size="small" :icon="getStrategyIcon(item.raw.value)"></v-icon>
            <span>{{ item.raw.title }}</span>
          </div>
        </template>
      </v-select>

      <!-- Coverage Target Slider -->
      <div class="mb-4">
        <v-slider
          v-model="productForm.configData.test_config.coverage_target"
          :min="0"
          :max="100"
          :step="5"
          label="Coverage Target"
          hint="Target percentage for code coverage"
          persistent-hint
          thumb-label="always"
          color="primary"
          class="mt-2"
        >
          <template #append>
            <v-chip size="small" variant="flat" color="primary">
              {{ productForm.configData.test_config.coverage_target }}%
            </v-chip>
          </template>
        </v-slider>
      </div>

      <!-- Testing Frameworks -->
      <v-textarea
        v-model="productForm.configData.test_config.frameworks"
        label="Testing Frameworks"
        placeholder="pytest, pytest-asyncio, pytest-cov, Playwright, Jest, Vitest"
        hint="List the testing frameworks and tools used"
        persistent-hint
        variant="outlined"
        density="comfortable"
        rows="3"
        auto-grow
        class="mb-4"
      ></v-textarea>
    </div>
  </v-window-item>
</template>

<script setup>
// ... existing script ...

// Testing strategies with icons
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

// Helper function for strategy icons
function getStrategyIcon(strategy) {
  const icons = {
    'TDD': 'mdi-test-tube',
    'BDD': 'mdi-script-text',
    'Integration-First': 'mdi-puzzle',
    'E2E-First': 'mdi-monitor-screenshot',
    'Manual': 'mdi-account-check',
    'Hybrid': 'mdi-cog-sync',
  }
  return icons[strategy] || 'mdi-test-tube'
}
</script>
```

---

## 7. API Service Fix

**File**: `frontend/src/services/api.js` (MODIFY IF NEEDED)

```javascript
import axios from 'axios'

// Create axios instance with base config
const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:7272',
  timeout: 30000,
})

// Add auth token to requests
axiosInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default {
  products: {
    /**
     * Create a new product
     * @param {Object} productData - Product data
     * @param {string} productData.name - Product name
     * @param {string} [productData.description] - Product description
     * @param {Object} [productData.configData] - Rich configuration object
     * @returns {Promise} API response
     */
    async create(productData) {
      console.log('[API] Creating product:', productData)

      const formData = new FormData()
      formData.append('name', productData.name)

      if (productData.description) {
        formData.append('description', productData.description)
      }

      // CRITICAL FIX: Backend expects config_data as JSON STRING, not object
      if (productData.configData) {
        const configDataString = JSON.stringify(productData.configData)
        formData.append('config_data', configDataString)
        console.log('[API] Serialized config_data:', {
          length: configDataString.length,
          preview: configDataString.substring(0, 100) + '...',
        })
      }

      const response = await axiosInstance.post('/api/products/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      console.log('[API] Product created:', response.data)
      return response
    },

    /**
     * Update an existing product
     * @param {string} productId - Product ID
     * @param {Object} updates - Fields to update
     * @returns {Promise} API response
     */
    async update(productId, updates) {
      console.log('[API] Updating product:', { productId, updates })

      const formData = new FormData()

      if (updates.name !== undefined) {
        formData.append('name', updates.name)
      }

      if (updates.description !== undefined) {
        formData.append('description', updates.description)
      }

      // CRITICAL FIX: Backend expects config_data as JSON STRING, not object
      if (updates.configData !== undefined) {
        const configDataString = JSON.stringify(updates.configData)
        formData.append('config_data', configDataString)
        console.log('[API] Serialized config_data:', {
          length: configDataString.length,
          preview: configDataString.substring(0, 100) + '...',
        })
      }

      const response = await axiosInstance.put(`/api/products/${productId}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      console.log('[API] Product updated:', response.data)
      return response
    },

    /**
     * Get product by ID
     * @param {string} productId - Product ID
     * @returns {Promise} API response
     */
    async get(productId) {
      const response = await axiosInstance.get(`/api/products/${productId}`)
      return response
    },

    /**
     * List all products (with optional filters)
     * @param {Object} [params] - Query parameters
     * @returns {Promise} API response
     */
    async list(params = {}) {
      const response = await axiosInstance.get('/api/products/', { params })
      return response
    },

    /**
     * Delete a product
     * @param {string} productId - Product ID
     * @returns {Promise} API response
     */
    async delete(productId) {
      const response = await axiosInstance.delete(`/api/products/${productId}`)
      return response
    },
  },

  // ... other API endpoints ...
}
```

---

## 8. Testing Examples

### Unit Test for Auto-Save Composable

**File**: `frontend/tests/unit/composables/useAutoSave.spec.js` (NEW)

```javascript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref } from 'vue'
import { useAutoSave } from '@/composables/useAutoSave'

describe('useAutoSave', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should save to LocalStorage after debounce delay', async () => {
    const formData = ref({ name: '', description: '' })
    const autoSave = useAutoSave({
      key: 'test_form',
      data: formData,
      debounceMs: 500,
    })

    // Modify data
    formData.value.name = 'Test Product'

    // Advance timers to trigger debounced save
    vi.advanceTimersByTime(500)

    // Wait for next tick
    await vi.runAllTicks()

    // Verify data saved to LocalStorage
    const cached = localStorage.getItem('test_form')
    expect(cached).toBeTruthy()

    const parsed = JSON.parse(cached)
    expect(parsed.data.name).toBe('Test Product')
    expect(parsed.timestamp).toBeDefined()
  })

  it('should update save status correctly', async () => {
    const formData = ref({ name: '' })
    const autoSave = useAutoSave({
      key: 'test_form',
      data: formData,
      debounceMs: 500,
    })

    expect(autoSave.saveStatus.value).toBe('saved')

    // Modify data
    formData.value.name = 'Test'

    // Status should immediately change to unsaved
    expect(autoSave.saveStatus.value).toBe('unsaved')
    expect(autoSave.hasUnsavedChanges.value).toBe(true)

    // Advance timers to complete save
    vi.advanceTimersByTime(500)
    await vi.runAllTicks()

    // Status should be saved
    expect(autoSave.saveStatus.value).toBe('saved')
    expect(autoSave.hasUnsavedChanges.value).toBe(false)
  })

  it('should restore from cache', () => {
    // Pre-populate LocalStorage
    const cachedData = {
      data: { name: 'Cached Product', description: 'From cache' },
      timestamp: Date.now(),
      version: '1.0',
    }
    localStorage.setItem('test_form', JSON.stringify(cachedData))

    const formData = ref({ name: '', description: '' })
    const autoSave = useAutoSave({
      key: 'test_form',
      data: formData,
    })

    // Restore from cache
    const restored = autoSave.restoreFromCache()

    expect(restored).toBeTruthy()
    expect(restored.name).toBe('Cached Product')
    expect(restored.description).toBe('From cache')
  })

  it('should clear cache', () => {
    // Pre-populate LocalStorage
    localStorage.setItem('test_form', JSON.stringify({ data: { name: 'Test' } }))

    const formData = ref({ name: '' })
    const autoSave = useAutoSave({
      key: 'test_form',
      data: formData,
    })

    // Clear cache
    autoSave.clearCache()

    // Verify cache removed
    const cached = localStorage.getItem('test_form')
    expect(cached).toBeNull()
  })

  it('should handle quota exceeded error gracefully', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    // Mock localStorage.setItem to throw quota exceeded error
    const originalSetItem = localStorage.setItem
    localStorage.setItem = vi.fn(() => {
      const error = new Error('QuotaExceededError')
      error.name = 'QuotaExceededError'
      throw error
    })

    const formData = ref({ name: 'Test' })
    const autoSave = useAutoSave({
      key: 'test_form',
      data: formData,
    })

    // Trigger save
    formData.value.name = 'Test Product'
    vi.advanceTimersByTime(500)
    await vi.runAllTicks()

    // Verify error handling
    expect(autoSave.saveStatus.value).toBe('error')
    expect(autoSave.errorMessage.value).toContain('quota exceeded')

    // Restore original localStorage
    localStorage.setItem = originalSetItem
  })

  it('should cancel debounced save on forceSave', async () => {
    const formData = ref({ name: '' })
    const autoSave = useAutoSave({
      key: 'test_form',
      data: formData,
      debounceMs: 500,
    })

    // Modify data
    formData.value.name = 'Test'

    // Force immediate save (before debounce completes)
    await autoSave.forceSave()

    // Verify data saved immediately
    const cached = localStorage.getItem('test_form')
    expect(cached).toBeTruthy()

    const parsed = JSON.parse(cached)
    expect(parsed.data.name).toBe('Test')
  })
})
```

### Manual Testing Script

**File**: `frontend/tests/manual/auto-save-test.md`

```markdown
# Manual Testing Script for Auto-Save Feature

## Prerequisites
- Backend server running
- Frontend dev server running
- Browser DevTools open
- User logged in

## Test 1: Basic Auto-Save
1. Navigate to Products page
2. Click "New Product"
3. Open DevTools → Application → LocalStorage
4. Type in "Product Name" field: "Auto-Save Test"
5. Wait 1 second
6. Check LocalStorage for key: `product_form_draft_new`
7. ✅ Verify data saved
8. ✅ Verify save status chip shows "Saved"

## Test 2: Draft Recovery
1. With dialog open from Test 1
2. Click "Cancel" (don't save)
3. Click "New Product" again
4. ✅ Verify restore prompt appears
5. Click "OK" to restore
6. ✅ Verify "Product Name" field shows "Auto-Save Test"
7. ✅ Verify toast shows "Draft restored successfully"

## Test 3: Unsaved Changes Warning
1. Fill form fields
2. Click "Cancel" button
3. ✅ Verify confirmation dialog appears
4. ✅ Message: "You have unsaved changes..."
5. Click "Cancel" in confirmation
6. ✅ Verify dialog remains open
7. Click "Cancel" again, then "OK"
8. ✅ Verify dialog closes

## Test 4: Browser Refresh Warning
1. Open dialog, fill fields
2. Press F5 or Ctrl+R
3. ✅ Verify browser shows "Leave site?" warning
4. Cancel refresh
5. ✅ Verify page doesn't refresh, data intact

## Test 5: Successful Save Clears Cache
1. Fill form completely
2. Verify LocalStorage has draft
3. Click "Save"
4. Wait for success toast
5. Check LocalStorage
6. ✅ Verify draft key removed

## Test 6: Tab Validation Indicators
1. Open "New Product" dialog
2. ✅ Verify "Basic Info" tab has red error badge (name required)
3. Fill "Product Name"
4. ✅ Verify error badge disappears
5. Navigate to "Tech Stack" tab
6. Leave all fields empty
7. ✅ Verify warning badge appears (languages recommended)

## Test 7: Testing Strategy Dropdown
1. Navigate to "Features & Testing" tab
2. Click "Testing Strategy" dropdown
3. ✅ Verify each option shows title + subtitle
4. ✅ Verify icons appear for each strategy
5. Select "BDD"
6. ✅ Verify selection updates
7. ✅ Verify auto-save triggers

## Test 8: Network Error Handling
1. Open dialog, fill fields
2. Open DevTools → Network tab
3. Right-click → Block request pattern → `*/products/*`
4. Click "Save"
5. ✅ Verify error toast: "Network error..."
6. ✅ Verify dialog remains open
7. ✅ Verify data preserved
8. Unblock requests, click "Save" again
9. ✅ Verify save succeeds

## Test 9: Edit Existing Product
1. Create a product (save successfully)
2. Click "Edit" on product card
3. ✅ Verify form populated with existing data
4. Check LocalStorage
5. ✅ Verify key is `product_form_draft_{product_id}`
6. Modify a field
7. Wait 1 second
8. ✅ Verify LocalStorage updated
9. Click "Save"
10. ✅ Verify changes persisted

## Test 10: Multiple Products (Cache Isolation)
1. Start creating "Product A" (don't save)
2. LocalStorage key: `product_form_draft_new`
3. Close dialog
4. Create and save "Product B"
5. Edit "Product B"
6. LocalStorage key: `product_form_draft_{product_b_id}`
7. ✅ Verify two separate cache keys
8. Close dialog
9. Open "New Product" again
10. ✅ Verify "Product A" draft restored (not "Product B")
```

---

**End of Code Examples**

These examples provide complete, production-ready code for implementing the auto-save feature. Copy and adapt as needed for your implementation.
