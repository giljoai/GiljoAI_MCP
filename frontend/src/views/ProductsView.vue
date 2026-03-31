<template>
  <v-container fluid class="products-container">
    <!-- Fixed Page Header -->
    <div class="products-header">
      <v-row>
        <v-col cols="12">
          <div class="d-flex align-center mb-6">
            <h1 class="text-h4">Products</h1>
            <v-spacer></v-spacer>
            <v-btn color="primary" prepend-icon="mdi-plus" @click="showDialog = true">
              New Product
            </v-btn>
          </div>
        </v-col>
      </v-row>
    </div>

    <!-- Scrollable Products Grid -->
    <div class="products-content">
      <v-row>
        <v-col cols="12">
          <v-card>
            <v-card-title class="d-flex align-center">
              <span>All Products</span>
              <v-spacer></v-spacer>
              <v-btn
                variant="outlined"
                :color="deletedProductsCount > 0 ? 'warning' : 'grey'"
                prepend-icon="mdi-delete-restore"
                :disabled="deletedProductsCount === 0"
                class="mr-3"
                style="height: 40px"
                @click="showDeletedProductsDialog = true"
              >
                Deleted ({{ deletedProductsCount }})
              </v-btn>
              <v-select
                v-model="sortBy"
                :items="sortOptions"
                item-title="label"
                item-value="value"
                prepend-inner-icon="mdi-sort"
                label="Sort by"
                variant="outlined"
                density="compact"
                hide-details
                class="mr-3"
                style="max-width: 200px"
              ></v-select>
              <v-text-field
                v-model="search"
                prepend-inner-icon="mdi-magnify"
                label="Search products..."
                single-line
                hide-details
                variant="outlined"
                density="compact"
                aria-label="Search products by name"
                style="max-width: 300px"
              ></v-text-field>
            </v-card-title>

            <v-card-text>
              <v-row v-if="loading">
                <v-col cols="12" class="text-center py-8">
                  <v-progress-circular indeterminate color="primary"></v-progress-circular>
                  <div class="text-muted-a11y mt-4">Loading products...</div>
                </v-col>
              </v-row>

              <v-row v-else-if="filteredProducts.length === 0">
                <v-col cols="12" class="text-center py-8">
                  <v-icon size="64" color="grey-lighten-2">mdi-package-variant-remove</v-icon>
                  <div class="text-h6 product-text-secondary mt-4">No products found</div>
                  <div class="text-body-2 text-muted-a11y">
                    {{
                      search
                        ? 'Try adjusting your search'
                        : 'Create your first product to get started'
                    }}
                  </div>
                </v-col>
              </v-row>

              <v-row v-else>
                <v-col
                  v-for="product in filteredProducts"
                  :key="product.id"
                  cols="12"
                  sm="6"
                  md="4"
                  lg="3"
                >
                  <v-card :elevation="0" class="product-card h-100 smooth-border" style="border-radius: 12px">
                    <v-card-text>
                      <div class="d-flex align-center justify-space-between mb-2">
                        <div
                          class="text-h6"
                          :class="{ 'text-primary': isProductActive(product) }"
                        >
                          {{ product.name }}
                        </div>
                        <span
                          v-if="isProductActive(product)"
                          class="product-status-chip product-status-active"
                        >
                          Active
                        </span>
                      </div>

                      <div class="text-caption text-muted-a11y mb-3">
                        Created: {{ formatDate(product.created_at) }}
                      </div>

                      <div class="mb-3">
                        <div class="text-caption text-muted-a11y">Product ID:</div>
                        <div
                          class="font-monospace text-muted-a11y"
                          style="font-size: 0.65rem; word-break: break-all; line-height: 1.3"
                        >
                          {{ product.id }}
                        </div>
                      </div>

                      <!-- Statistics -->
                      <v-divider class="my-3 product-divider"></v-divider>
                      <v-row dense>
                        <v-col cols="4" class="text-center">
                          <div class="text-caption text-muted-a11y">Tasks</div>
                          <div class="text-h6 product-text-secondary">
                            {{ product.task_count || 0 }}
                          </div>
                        </v-col>
                        <v-col cols="4" class="text-center">
                          <div class="text-caption text-muted-a11y">Projects</div>
                          <div class="text-h6 product-text-secondary">
                            {{ product.project_count || 0 }}
                          </div>
                        </v-col>
                        <v-col cols="4" class="text-center">
                          <div class="text-caption text-muted-a11y">Completed</div>
                          <div class="text-h6 product-text-secondary">
                            {{ getCompletedProjectsCount(product) }}
                          </div>
                        </v-col>
                      </v-row>

                      <!-- Vision Document Status (Handover 0347) -->
                      <div v-if="product.vision_documents?.length > 0" class="mt-2 d-flex ga-1 flex-wrap">
                        <span
                          class="vision-chip"
                          :style="getVisionChunkedCount(product) > 0 ? 'background: rgba(103,189,109,0.15); color: #67bd6d' : 'background: rgba(255,152,0,0.15); color: #ff9800'"
                        >
                          <v-icon size="12" class="mr-1">mdi-file-document</v-icon>
                          {{ product.vision_documents.length }} docs
                        </span>
                        <span
                          v-if="getVisionChunkedCount(product) > 0"
                          class="vision-chip"
                          style="background: rgba(109,179,228,0.15); color: #6DB3E4"
                        >
                          <v-icon size="12" class="mr-1">mdi-database</v-icon>
                          {{ getVisionTotalChunks(product) }} chunks
                        </span>
                      </div>
                    </v-card-text>

                    <v-card-actions class="justify-center">
                      <v-tooltip location="top" content-class="branded-tooltip">
                        <template v-slot:activator="{ props }">
                          <v-btn
                            icon
                            size="small"
                            variant="text"
                            v-bind="props"
                            aria-label="View product details"
                            :style="
                              product.id === productStore.currentProductId ? 'color: rgb(var(--v-theme-on-surface))' : ''
                            "
                            @click="showProductDetails(product)"
                          >
                            <v-icon>mdi-information-outline</v-icon>
                          </v-btn>
                        </template>
                        <span>View Product Details</span>
                      </v-tooltip>
                      <v-tooltip location="top" content-class="branded-tooltip">
                        <template v-slot:activator="{ props }">
                          <v-badge
                            :model-value="getTuningState(product) !== 'normal'"
                            dot
                            :color="getTuningState(product) === 'proposals' ? 'warning' : 'info'"
                            offset-x="-2"
                            offset-y="-2"
                          >
                            <v-btn
                              icon
                              size="small"
                              variant="text"
                              v-bind="props"
                              aria-label="Tune context"
                              @click="showProductTuning(product)"
                            >
                              <v-icon>mdi-tune</v-icon>
                            </v-btn>
                          </v-badge>
                        </template>
                        <span>{{ getTuningState(product) === 'proposals' ? 'Tuning proposals ready for review' : getTuningState(product) === 'stale' ? 'Context tuning recommended' : 'Tune Context' }}</span>
                      </v-tooltip>
                      <v-tooltip location="top" content-class="branded-tooltip">
                        <template v-slot:activator="{ props }">
                          <v-btn
                            icon
                            size="small"
                            variant="text"
                            v-bind="props"
                            :aria-label="isProductActive(product) ? 'Deactivate product' : 'Activate product'"
                            :class="{ 'text-primary': isProductActive(product) }"
                            @click="toggleProductActivation(product)"
                          >
                            <v-icon>{{
                              isProductActive(product) ? 'mdi-stop' : 'mdi-play'
                            }}</v-icon>
                          </v-btn>
                        </template>
                        <span>{{
                          isProductActive(product) ? 'Deactivate Product' : 'Activate Product'
                        }}</span>
                      </v-tooltip>
                      <v-tooltip location="top" content-class="branded-tooltip">
                        <template v-slot:activator="{ props }">
                          <v-btn
                            icon
                            size="small"
                            variant="text"
                            v-bind="props"
                            aria-label="Edit product"
                            :style="
                              product.id === productStore.currentProductId ? 'color: rgb(var(--v-theme-on-surface))' : ''
                            "
                            @click="editProduct(product)"
                          >
                            <v-icon>mdi-pencil</v-icon>
                          </v-btn>
                        </template>
                        <span>Edit Product</span>
                      </v-tooltip>
                      <v-tooltip location="top" content-class="branded-tooltip">
                        <template v-slot:activator="{ props }">
                          <v-btn
                            icon
                            size="small"
                            variant="text"
                            color="error"
                            v-bind="props"
                            aria-label="Delete product"
                            @click="confirmDelete(product)"
                          >
                            <v-icon>mdi-delete</v-icon>
                          </v-btn>
                        </template>
                        <span>Delete Product</span>
                      </v-tooltip>
                    </v-card-actions>
                  </v-card>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>
    <!-- End products-content -->

    <!-- Extracted Component Dialogs -->

    <!-- Create/Edit Product Dialog -->
    <ProductForm
      v-model="showDialog"
      :product="editingProduct"
      :is-edit="!!editingProduct && !autoSavedForAnalysis"
      :existing-vision-documents="existingVisionDocuments"
      :uploading-vision="uploadingVision"
      :upload-progress="uploadProgress"
      :vision-upload-error="visionUploadError"
      @save="saveProduct"
      @upload-vision-files="uploadVisionFilesOnAttach"
      @cancel="closeDialog"
      @remove-vision="removeVisionDocument"
      @clear-upload-error="visionUploadError = null"
    />

    <!-- Product Details Dialog -->
    <ProductDetailsDialog
      v-model="showDetailsDialog"
      :product="selectedProduct"
      :vision-documents="detailsVisionDocuments"
      :stats="productStats"
      :auto-expand-tuning="autoExpandTuning"
    />

    <!-- Delete Confirmation Dialog -->
    <ProductDeleteDialog
      v-model="showDeleteDialog"
      :product="deletingProduct"
      :cascade-impact="cascadeImpact"
      :loading="loadingCascadeImpact"
      :deleting="deleting"
      @confirm="confirmDeleteProduct"
      @cancel="cancelDelete"
    />

    <!-- Deleted Products Recovery Dialog -->
    <DeletedProductsRecoveryDialog
      v-model="showDeletedProductsDialog"
      :deleted-products="deletedProducts"
      :restoring-product-id="restoringProductId"
      :purging-product-id="purgingProductId"
      :purging-all="purgingAllProducts"
      @restore="restoreProduct"
      @purge="purgeDeletedProduct"
      @purge-all="purgeAllDeletedProducts"
    />

    <!-- Handover 0050: Activation Warning Dialog -->
    <ActivationWarningDialog
      v-model="showActivationWarning"
      :new-product="pendingActivation || {}"
      :current-active="currentActiveProduct || {}"
      @confirm="confirmActivation"
      @cancel="cancelActivation"
    />
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useProductStore } from '@/stores/products'
import { useSettingsStore } from '@/stores/settings'
import { useNotificationStore } from '@/stores/notifications'
import { useToast } from '@/composables/useToast'
import { useFormatDate } from '@/composables/useFormatDate'
import api from '@/services/api'
import ActivationWarningDialog from '@/components/products/ActivationWarningDialog.vue'
import ProductDeleteDialog from '@/components/products/ProductDeleteDialog.vue'
import ProductDetailsDialog from '@/components/products/ProductDetailsDialog.vue'
import DeletedProductsRecoveryDialog from '@/components/products/DeletedProductsRecoveryDialog.vue'
import ProductForm from '@/components/products/ProductForm.vue'

const productStore = useProductStore()
const settingsStore = useSettingsStore()
const notificationStore = useNotificationStore()
const { showToast } = useToast()
const { formatDate } = useFormatDate()
// State
const loading = ref(false)
const search = ref('')
const sortBy = ref('name')
const showDialog = ref(false)
const showDeleteDialog = ref(false)
const showDetailsDialog = ref(false)
const editingProduct = ref(null)
const deletingProduct = ref(null)
const selectedProduct = ref(null)
const deleting = ref(false)
const visionFiles = ref([])
const existingVisionDocuments = ref([])
const autoSavedForAnalysis = ref(null) // Holds product ID if auto-saved for stage-analysis, null otherwise
const uploadingVision = ref(false)
const uploadProgress = ref(0)
const visionUploadError = ref(null)
const detailsVisionDocuments = ref([])
const autoExpandTuning = ref(false)
const cascadeImpact = ref(null)
const loadingCascadeImpact = ref(false)

// Handover 0050: Activation warning dialog state
const showActivationWarning = ref(false)
const pendingActivation = ref(null)
const currentActiveProduct = ref(null)

// Soft delete recovery state
const showDeletedProductsDialog = ref(false)
const deletedProducts = ref([])
const restoringProductId = ref(null)
const purgingProductId = ref(null)
const purgingAllProducts = ref(false)

// Sort options
const sortOptions = [
  { label: 'Name (A-Z)', value: 'name' },
  { label: 'Date Created (Newest)', value: 'date-newest' },
  { label: 'Date Created (Oldest)', value: 'date-oldest' },
]

// Computed
const filteredProducts = computed(() => {
  // Filter by search
  let products = productStore.products
  if (search.value) {
    const searchLower = search.value.toLowerCase()
    products = products.filter(
      (product) =>
        product.name.toLowerCase().includes(searchLower) ||
        product.description?.toLowerCase().includes(searchLower),
    )
  }

  // Sort products - ACTIVE PRODUCTS FIRST (leftmost/top)
  const sorted = [...products]

  // Primary sort: Active products first
  sorted.sort((a, b) => {
    // If one is active and the other isn't, active comes first
    // Use isProductActive for single source of truth (Handover 0320)
    const aActive = isProductActive(a)
    const bActive = isProductActive(b)
    if (aActive && !bActive) return -1
    if (!aActive && bActive) return 1

    // Both active or both inactive - apply secondary sort
    switch (sortBy.value) {
      case 'name':
        return a.name.localeCompare(b.name)
      case 'date-newest':
        return new Date(b.created_at) - new Date(a.created_at)
      case 'date-oldest':
        return new Date(a.created_at) - new Date(b.created_at)
      default:
        return 0
    }
  })

  return sorted
})

const deletedProductsCount = computed(() => {
  return deletedProducts.value.length
})

// Product stats for details dialog
const productStats = computed(() => {
  if (!selectedProduct.value) {
    return {
      unresolved_tasks: 0,
      unfinished_projects: 0,
    }
  }
  return {
    unresolved_tasks: selectedProduct.value.unresolved_tasks || 0,
    unfinished_projects: selectedProduct.value.unfinished_projects || 0,
  }
})

// Methods

// Handover 0320: Single source of truth for active product detection
// Uses productStore.activeProduct.id instead of product.is_active from array
function isProductActive(product) {
  return productStore.activeProduct?.id === product.id
}

function getCompletedProjectsCount(product) {
  // Calculate completed projects: total - unfinished
  const totalProjects = product.project_count || 0
  const unfinishedProjects = product.unfinished_projects || 0
  return Math.max(0, totalProjects - unfinishedProjects)
}

// Handover 0347: Vision document chunk helpers
function getVisionChunkedCount(product) {
  if (!product.vision_documents) return 0
  return product.vision_documents.filter(doc => doc.chunked).length
}

function getVisionTotalChunks(product) {
  if (!product.vision_documents) return 0
  return product.vision_documents.reduce((sum, doc) => sum + (doc.chunk_count || 0), 0)
}

// Handover 0050: Enhanced activation with warning dialog
async function toggleProductActivation(product) {
  try {
    // Handover 0320: Use store as single source of truth for active product
    if (isProductActive(product)) {
      // Deactivating - no warning needed
      await api.products.deactivate(product.id)
      await productStore.fetchActiveProduct()

      showToast({
        message: `${product.name} deactivated`,
        type: 'info',
        duration: 3000,
      })

      await loadProducts()
    } else {
      // Activating - check if there's currently an active product FIRST
      // Use store as single source of truth (Handover 0320)
      const currentActive = productStore.activeProduct

      if (currentActive && currentActive.id !== product.id) {
        // There's already an active product - show warning BEFORE activating
        currentActiveProduct.value = currentActive
        pendingActivation.value = product
        showActivationWarning.value = true
        // Don't proceed yet - wait for user confirmation via confirmActivation()
        return
      }

      // No active product - proceed with activation
      await api.products.activate(product.id)
      await productStore.fetchActiveProduct()

      showToast({
        message: `${product.name} activated`,
        type: 'success',
        duration: 3000,
      })

      await loadProducts()
    }
  } catch (error) {
    console.error('Failed to toggle product activation:', error)
    showToast({
      message: 'Failed to change product status',
      type: 'error',
      duration: 5000,
    })
  }
}

// Handover 0050: Confirm activation after warning
async function confirmActivation(_productId) {
  try {
    // User confirmed - NOW actually activate the product
    await api.products.activate(pendingActivation.value.id)
    await productStore.fetchActiveProduct()

    showToast({
      message: `${pendingActivation.value?.name} activated`,
      type: 'success',
      duration: 3000,
    })

    await loadProducts()

    // Close dialog
    showActivationWarning.value = false
    pendingActivation.value = null
    currentActiveProduct.value = null
  } catch (error) {
    console.error('Failed to confirm activation:', error)
    showToast({
      message: 'Failed to activate product',
      type: 'error',
      duration: 5000,
    })
  }
}

// Handover 0050: Cancel activation
function cancelActivation() {
  // User cancelled - just close dialog, activation never happened
  showActivationWarning.value = false
  pendingActivation.value = null
  currentActiveProduct.value = null
}


// Handover 0320: Handler for ProductForm remove-vision event (delete existing document)
async function removeVisionDocument(doc) {
  try {
    await api.visionDocuments.delete(doc.id)

    // Remove from existing documents list
    const index = existingVisionDocuments.value.findIndex((d) => d.id === doc.id)
    if (index > -1) {
      existingVisionDocuments.value.splice(index, 1)
    }

    showToast({
      message: `Deleted vision document: ${doc.document_name}`,
      type: 'success',
      duration: 3000,
    })
  } catch (error) {
    console.error('Failed to delete vision document:', error)
    showToast({
      message: 'Failed to delete vision document',
      type: 'error',
      duration: 5000,
    })
  }
}

// Handover 0508: Validate vision files before upload
function validateVisionFile(file) {
  const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB
  const ALLOWED_EXTENSIONS = ['.md', '.txt', '.markdown']

  // Validate file size
  if (file.size > MAX_FILE_SIZE) {
    return `File too large. Maximum size is 10MB (${(file.size / 1024 / 1024).toFixed(1)}MB provided).`
  }

  // Validate file type
  const hasValidExtension = ALLOWED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext))

  if (!hasValidExtension) {
    return `Invalid file type. Please upload .md or .txt files.`
  }

  return null // Valid
}

function validateVisionFiles() {
  if (!visionFiles.value || visionFiles.value.length === 0) {
    return true // No files to validate
  }

  for (const file of visionFiles.value) {
    const error = validateVisionFile(file)
    if (error) {
      showToast({
        message: error,
        type: 'error',
        duration: 7000,
      })
      return false
    }
  }

  return true
}

function getTuningState(product) {
  if (product.tuning_state?.pending_proposals) return 'proposals'
  const hasUnread = notificationStore.notifications.some(
    (n) => !n.read && n.type === 'context_tuning' && n.metadata?.product_id === product.id,
  )
  if (hasUnread) return 'stale'
  return 'normal'
}

async function showProductDetails(product) {
  selectedProduct.value = product
  autoExpandTuning.value = false

  // Fetch vision documents
  try {
    const response = await api.visionDocuments.listByProduct(product.id)
    detailsVisionDocuments.value = response.data || []
  } catch (error) {
    console.error('Failed to load vision documents:', error)
    detailsVisionDocuments.value = []
  }

  showDetailsDialog.value = true
}

async function showProductTuning(product) {
  selectedProduct.value = product
  autoExpandTuning.value = true

  try {
    const response = await api.visionDocuments.listByProduct(product.id)
    detailsVisionDocuments.value = response.data || []
  } catch (error) {
    console.error('Failed to load vision documents:', error)
    detailsVisionDocuments.value = []
  }

  showDetailsDialog.value = true
}

async function editProduct(product) {
  editingProduct.value = product

  // Fetch existing vision documents
  await loadExistingVisionDocuments(product.id)

  showDialog.value = true
}

async function loadExistingVisionDocuments(productId) {
  try {
    const response = await api.visionDocuments.listByProduct(productId)
    existingVisionDocuments.value = response.data || []
  } catch (error) {
    console.error('Failed to load vision documents:', error)
    existingVisionDocuments.value = []
  }
}

async function confirmDelete(product) {
  deletingProduct.value = product
  showDeleteDialog.value = true

  // Fetch cascade impact
  loadingCascadeImpact.value = true
  try {
    const response = await api.products.getCascadeImpact(product.id)
    cascadeImpact.value = response.data
  } catch (error) {
    if (error?.response?.status === 404) {
      // Product already gone from DB — let user confirm removal of ghost card
      cascadeImpact.value = null
    } else {
      console.error('Failed to get cascade impact:', error)
      showToast({
        message: 'Failed to load deletion impact',
        type: 'error',
        duration: 5000,
      })
    }
  } finally {
    loadingCascadeImpact.value = false
  }
}

async function saveProduct(payload) {
  const { productData } = payload

  try {
    // Create or update — vision files already uploaded on attach
    if (editingProduct.value) {
      await productStore.updateProduct(editingProduct.value.id, productData)
    } else {
      await productStore.createProduct(productData)
    }

    // Product is now permanent — clear auto-save cleanup flag
    autoSavedForAnalysis.value = null

    // Refresh products
    await loadProducts()

    // Close dialog
    showDialog.value = false

    showToast({
      message: editingProduct.value
        ? 'Product updated successfully'
        : 'Product created successfully',
      type: 'success',
      duration: 3000,
    })

    // Reset state
    editingProduct.value = null
    visionFiles.value = []
    existingVisionDocuments.value = []
    uploadingVision.value = false
    uploadProgress.value = 0
    visionUploadError.value = null
  } catch (error) {
    console.error('Failed to save product:', error)
    showToast({
      message: 'Failed to save product',
      type: 'error',
      duration: 5000,
    })
    // Handover 0051: Do NOT close dialog on error - keep form data visible
  }
}

// Upload vision files immediately on attachment
// In create mode: silently creates the product first to get a UUID
async function uploadVisionFilesOnAttach(payload) {
  const { productName, files } = payload

  if (!files || files.length === 0) return

  // Validate files
  visionFiles.value = files
  if (!validateVisionFiles()) {
    visionFiles.value = []
    return
  }

  try {
    // In create mode, silently create the product to get a UUID
    let productId
    if (editingProduct.value) {
      productId = editingProduct.value.id
    } else {
      const product = await productStore.createProduct({ name: productName })
      editingProduct.value = product
      autoSavedForAnalysis.value = product.id
      productId = product.id
    }

    // Upload files with progress UI
    uploadingVision.value = true
    uploadProgress.value = 0
    visionUploadError.value = null

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      try {
        const formData = new FormData()
        formData.append('product_id', productId)
        formData.append('document_name', file.name.replace(/\.[^/.]+$/, ''))
        formData.append('document_type', 'vision')
        formData.append('vision_file', file)
        formData.append('auto_chunk', 'true')

        const response = await api.visionDocuments.upload(formData)
        uploadProgress.value = ((i + 1) / files.length) * 100

        const chunkCount = response.data?.chunk_count || 0
        const isSummarized = response.data?.is_summarized || false
        const statusParts = []
        if (isSummarized) statusParts.push('summarized')
        if (chunkCount > 0) statusParts.push(`${chunkCount} chunks`)

        showToast({
          message: `${file.name} uploaded${statusParts.length ? ` (${statusParts.join(', ')})` : ''}`,
          type: 'success',
          duration: 3000,
        })
      } catch (uploadError) {
        console.error(`Failed to upload ${file.name}:`, uploadError)

        let errorMessage = `Failed to upload ${file.name}`
        if (uploadError.response) {
          switch (uploadError.response.status) {
            case 413:
              errorMessage = `${file.name}: File too large (max 10MB)`
              break
            case 400:
              errorMessage = `${file.name}: ${uploadError.response.data.detail || 'Invalid file'}`
              break
            case 409:
              errorMessage = `${file.name}: Document already exists. Please rename and try again.`
              break
            default:
              errorMessage = `${file.name}: ${uploadError.response.data.detail || 'Upload failed'}`
          }
        }

        visionUploadError.value = errorMessage
        showToast({ message: errorMessage, type: 'error', duration: 7000 })
      }
    }

    uploadingVision.value = false
    visionFiles.value = []

    // Refresh existing docs list so the form shows them
    await loadExistingVisionDocuments(productId)
  } catch (error) {
    console.error('Failed to upload vision files:', error)
    uploadingVision.value = false
    showToast({
      message: 'Failed to upload files',
      type: 'error',
      duration: 5000,
    })
  }
}

async function confirmDeleteProduct() {
  deleting.value = true
  try {
    await productStore.deleteProduct(deletingProduct.value.id)

    // If was active product, clear active state
    if (productStore.currentProductId === deletingProduct.value.id) {
      productStore.currentProductId = null
      productStore.currentProduct = null
      localStorage.removeItem('currentProductId')
    }

    // Close dialog
    showDeleteDialog.value = false
    const productName = deletingProduct.value.name
    deletingProduct.value = null

    // Refresh products (includes deleted products list)
    await loadProducts()

    // Show success message
    showToast({
      message: `${productName} moved to trash. Recoverable for 10 days.`,
      type: 'info',
      duration: 4000,
    })
  } catch (error) {
    if (error?.response?.status === 404) {
      // Product already gone from DB (orphan card) — clean up UI
      showDeleteDialog.value = false
      const productName = deletingProduct.value?.name || 'Product'
      deletingProduct.value = null
      await loadProducts()
      showToast({ message: `${productName} was already removed.`, type: 'info', duration: 3000 })
    } else {
      console.error('Failed to delete product:', error)
      showToast({
        message: 'Failed to move product to trash',
        type: 'error',
        duration: 5000,
      })
    }
  } finally {
    deleting.value = false
  }
}

function cancelDelete() {
  showDeleteDialog.value = false
  deletingProduct.value = null
  cascadeImpact.value = null
}

async function closeDialog() {
  // Clean up auto-saved product if user never did a real save (404 = already gone, ignore)
  if (autoSavedForAnalysis.value) {
    try {
      await productStore.deleteProduct(autoSavedForAnalysis.value)
    } catch {
      // Silently ignore — product may already be deleted
    }
    autoSavedForAnalysis.value = null
  }

  showDialog.value = false
  editingProduct.value = null
  visionFiles.value = []
  existingVisionDocuments.value = []
  uploadingVision.value = false
  uploadProgress.value = 0
  visionUploadError.value = null

  // Refresh product list on close
  loadProducts()
}

async function loadProducts() {
  loading.value = true
  try {
    await productStore.fetchProducts()
    // Fetch metrics for all products
    for (const product of productStore.products) {
      await productStore.fetchProductMetrics(product.id)
    }
    // Also load deleted products count
    await loadDeletedProducts()
  } finally {
    loading.value = false
  }
}

async function loadDeletedProducts() {
  try {
    const response = await api.products.getDeletedProducts()
    deletedProducts.value = response.data || []
  } catch (error) {
    console.error('Failed to load deleted products:', error)
    deletedProducts.value = []
  }
}

async function restoreProduct(productId) {
  if (restoringProductId.value) return // Prevent double-click

  const product = deletedProducts.value.find((p) => p.id === productId)
  restoringProductId.value = productId
  try {
    await api.products.restoreProduct(productId)

    showToast({
      message: `${product?.name || 'Product'} restored successfully`,
      type: 'success',
      duration: 3000,
    })

    // Reload both lists
    await loadProducts()
    await loadDeletedProducts()

    // Close dialog if no more deleted products
    if (deletedProducts.value.length === 0) {
      showDeletedProductsDialog.value = false
    }
  } catch (error) {
    console.error('Failed to restore product:', error)
    showToast({
      message: 'Failed to restore product',
      type: 'error',
      duration: 5000,
    })
  } finally {
    restoringProductId.value = null
  }
}

async function purgeDeletedProduct(productId) {
  if (purgingProductId.value) return

  const product = deletedProducts.value.find((p) => p.id === productId)
  purgingProductId.value = productId
  try {
    await api.products.purge(productId)

    showToast({
      message: `${product?.name || 'Product'} permanently deleted.`,
      type: 'warning',
      duration: 3000,
    })

    await loadProducts()
    await loadDeletedProducts()

    if (deletedProducts.value.length === 0) {
      showDeletedProductsDialog.value = false
    }
  } catch (error) {
    console.error('Failed to purge product:', error)
    showToast({
      message: 'Failed to permanently delete product',
      type: 'error',
      duration: 5000,
    })
  } finally {
    purgingProductId.value = null
  }
}

async function purgeAllDeletedProducts() {
  if (purgingAllProducts.value) return

  purgingAllProducts.value = true
  try {
    const ids = deletedProducts.value.map((p) => p.id)
    for (const id of ids) {
      await api.products.purge(id)
    }

    showToast({
      message: `${ids.length} product(s) permanently deleted.`,
      type: 'warning',
      duration: 3000,
    })

    await loadProducts()
    await loadDeletedProducts()
    showDeletedProductsDialog.value = false
  } catch (error) {
    console.error('Failed to purge all products:', error)
    showToast({
      message: 'Failed to delete all products',
      type: 'error',
      duration: 5000,
    })
  } finally {
    purgingAllProducts.value = false
  }
}

onMounted(async () => {
  await loadProducts()
  // Load field toggle configuration (Handover 0049, 0820)
  try {
    await settingsStore.fetchFieldToggleConfig()
  } catch {
    // Field toggle config not available
  }
})
</script>

<style scoped>
/* Fixed header and scrollable content layout */
.products-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.products-header {
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: inherit;
  padding-top: 16px;
}

.products-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding-bottom: 24px;
}

.product-card {
  transition: all 0.3s ease;
}

.product-card:hover {
  transform: translateY(-2px);
}

/* Lighter divider line (25% closer to white) */
.product-divider {
  opacity: 0.3;
  border-color: rgba(255, 255, 255, 0.6);
}

/* Reduce spacing above card actions by 50% */
.product-card :deep(.v-card-actions) {
  padding-top: 4px;
}

/* Tinted status chip for Active badge */
.product-status-chip {
  display: inline-flex;
  align-items: center;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 9999px;
  line-height: 1.4;
  letter-spacing: 0.02em;
}

.product-status-active {
  background: rgba(103, 189, 109, 0.15);
  color: #67bd6d;
}

.product-text-secondary {
  color: #a3aac4 !important;
}

/* Vision doc tinted chips */
.vision-chip {
  display: inline-flex;
  align-items: center;
  font-size: 0.65rem;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 4px;
  line-height: 1.5;
}

/* Handover 0051: Spinning icon animation for save status */
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

/* Bright (white) when enabled, dim when disabled; arrows no longer overlay tabs */
.tabs-with-arrows :deep(.v-slide-group__prev .v-btn .v-icon),
.tabs-with-arrows :deep(.v-slide-group__next .v-btn .v-icon) {
  color: white;
}
.tabs-with-arrows :deep(.v-slide-group__prev .v-btn.v-btn--disabled .v-icon),
.tabs-with-arrows :deep(.v-slide-group__next .v-btn.v-btn--disabled .v-icon) {
  opacity: 0.4;
}
</style>

<style>
/* Global branded tooltips - must be unscoped to affect tooltip overlays */
.branded-tooltip {
  background-color: rgba(255, 195, 0, 0.95) !important;
  color: rgb(var(--v-theme-on-primary)) !important;
  font-weight: 500;
  font-size: 0.875rem;
  padding: 6px 12px;
  border-radius: 6px;
}
</style>
