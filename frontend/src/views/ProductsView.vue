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
                @click="showDeletedProductsDialog = true"
                :disabled="deletedProductsCount === 0"
                class="mr-3"
                style="height: 40px"
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
                style="max-width: 300px"
              ></v-text-field>
            </v-card-title>

            <v-card-text>
              <v-row v-if="loading">
                <v-col cols="12" class="text-center py-8">
                  <v-progress-circular indeterminate color="primary"></v-progress-circular>
                  <div class="text-medium-emphasis mt-4">Loading products...</div>
                </v-col>
              </v-row>

              <v-row v-else-if="filteredProducts.length === 0">
                <v-col cols="12" class="text-center py-8">
                  <v-icon size="64" color="grey-lighten-2">mdi-package-variant-remove</v-icon>
                  <div class="text-h6 text-medium-emphasis mt-4">No products found</div>
                  <div class="text-body-2 text-medium-emphasis">
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
                  <v-card :elevation="0" class="product-card h-100">
                    <v-card-text>
                      <div class="d-flex align-center justify-space-between mb-2">
                        <div
                          class="text-h6"
                          :style="isProductActive(product) ? 'color: #ffc300' : ''"
                        >
                          {{ product.name }}
                        </div>
                        <v-chip
                          v-if="isProductActive(product)"
                          color="success"
                          size="small"
                          variant="flat"
                        >
                          Active
                        </v-chip>
                      </div>

                      <div class="text-caption text-medium-emphasis mb-3">
                        Created: {{ formatDate(product.created_at) }}
                      </div>

                      <div class="mb-3">
                        <div class="text-caption text-medium-emphasis">Product ID:</div>
                        <div
                          class="font-monospace"
                          style="font-size: 0.65rem; word-break: break-all; line-height: 1.3"
                        >
                          {{ product.id }}
                        </div>
                      </div>

                      <!-- Statistics -->
                      <v-divider class="my-3 product-divider"></v-divider>
                      <v-row dense>
                        <v-col cols="4" class="text-center">
                          <div class="text-caption text-medium-emphasis">Tasks</div>
                          <div class="text-h6" style="color: #ffc300">
                            {{ product.task_count || 0 }}
                          </div>
                        </v-col>
                        <v-col cols="4" class="text-center">
                          <div class="text-caption text-medium-emphasis">Projects</div>
                          <div class="text-h6" style="color: #ffc300">
                            {{ product.project_count || 0 }}
                          </div>
                        </v-col>
                        <v-col cols="4" class="text-center">
                          <div class="text-caption text-medium-emphasis">Completed</div>
                          <div class="text-h6" style="color: #ffc300">
                            {{ getCompletedProjectsCount(product) }}
                          </div>
                        </v-col>
                      </v-row>

                      <!-- Vision Document Status (Handover 0347) -->
                      <div v-if="product.vision_documents?.length > 0" class="mt-2">
                        <v-chip
                          size="x-small"
                          variant="tonal"
                          :color="getVisionChunkedCount(product) > 0 ? 'success' : 'warning'"
                          class="mr-1"
                        >
                          <v-icon start size="12">mdi-file-document</v-icon>
                          {{ product.vision_documents.length }} docs
                        </v-chip>
                        <v-chip
                          v-if="getVisionChunkedCount(product) > 0"
                          size="x-small"
                          variant="tonal"
                          color="primary"
                        >
                          <v-icon start size="12">mdi-database</v-icon>
                          {{ getVisionTotalChunks(product) }} chunks
                        </v-chip>
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
                            @click="showProductDetails(product)"
                            :style="
                              product.id === productStore.currentProductId ? 'color: #e1e1e1' : ''
                            "
                          >
                            <v-icon>mdi-information-outline</v-icon>
                          </v-btn>
                        </template>
                        <span>View Product Details</span>
                      </v-tooltip>
                      <v-tooltip location="top" content-class="branded-tooltip">
                        <template v-slot:activator="{ props }">
                          <v-btn
                            icon
                            size="small"
                            variant="text"
                            v-bind="props"
                            @click="toggleProductActivation(product)"
                            :style="isProductActive(product) ? 'color: #ffc300' : ''"
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
                            @click="editProduct(product)"
                            :style="
                              product.id === productStore.currentProductId ? 'color: #e1e1e1' : ''
                            "
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
      :is-edit="!!editingProduct"
      :existing-vision-documents="existingVisionDocuments"
      :auto-save-state="autoSave"
      @save="saveProduct"
      @cancel="closeDialog"
      @upload-vision="uploadVisionDocument"
      @remove-vision="removeVisionDocument"
    />

    <!-- Product Details Dialog -->
    <ProductDetailsDialog
      v-model="showDetailsDialog"
      :product="selectedProduct"
      :vision-documents="detailsVisionDocuments"
      :stats="productStats"
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
      @restore="restoreProduct"
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
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useProductStore } from '@/stores/products'
import { useSettingsStore } from '@/stores/settings'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { useFieldPriority } from '@/composables/useFieldPriority'
import { useAutoSave } from '@/composables/useAutoSave'
import api from '@/services/api'
import ActivationWarningDialog from '@/components/products/ActivationWarningDialog.vue'
import ProductDeleteDialog from '@/components/products/ProductDeleteDialog.vue'
import ProductDetailsDialog from '@/components/products/ProductDetailsDialog.vue'
import DeletedProductsRecoveryDialog from '@/components/products/DeletedProductsRecoveryDialog.vue'
import ProductForm from '@/components/products/ProductForm.vue'

const productStore = useProductStore()
const settingsStore = useSettingsStore()
const router = useRouter()
const { showToast } = useToast()
const { getPriorityForField, getPriorityLabel, getPriorityColor, getPriorityTooltip } =
  useFieldPriority()

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
const saving = ref(false)
const deleting = ref(false)
const formValid = ref(false)
const formRef = ref(null)
const visionFiles = ref([])
const existingVisionDocuments = ref([])
const detailsVisionDocuments = ref([])
// Handover 0508: Vision upload error handling and progress tracking
const uploadingVision = ref(false)
const uploadProgress = ref(0)
const isChunking = ref(false)
const visionUploadError = ref(null)
const cascadeImpact = ref(null)
const loadingCascadeImpact = ref(false)
const deleteConfirmationCheck = ref(false)
const dialogTab = ref('basic') // Handover 0042: Tab for product dialog (basic, tech, arch, features)
const autoSave = ref(null) // Handover 0051: Auto-save composable instance

// Handover 0050: Activation warning dialog state
const showActivationWarning = ref(false)
const pendingActivation = ref(null)
const currentActiveProduct = ref(null)

// Soft delete recovery state
const showDeletedProductsDialog = ref(false)
const deletedProducts = ref([])
const loadingDeletedProducts = ref(false)
const restoringProductId = ref(null)

// Wizard tab order and navigation helpers
const tabOrder = ['basic', 'vision', 'tech', 'arch', 'features']
const isFirstTab = computed(() => tabOrder.indexOf(dialogTab.value) === 0)
const isLastTab = computed(() => tabOrder.indexOf(dialogTab.value) === tabOrder.length - 1)

function goNextTab() {
  const idx = tabOrder.indexOf(dialogTab.value)
  if (idx >= 0 && idx < tabOrder.length - 1) {
    dialogTab.value = tabOrder[idx + 1]
  }
}

function goPrevTab() {
  const idx = tabOrder.indexOf(dialogTab.value)
  if (idx > 0) {
    dialogTab.value = tabOrder[idx - 1]
  }
}

const productForm = ref({
  name: '',
  description: '',
  visionPath: '',
  projectPath: '', // Handover 0084: Project path for agent export
  // Handover 0042: Rich configuration data
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
      quality_standards: '', // Handover 0316: New field
    },
  },
})

// Sort options
const sortOptions = [
  { label: 'Name (A-Z)', value: 'name' },
  { label: 'Date Created (Newest)', value: 'date-newest' },
  { label: 'Date Created (Oldest)', value: 'date-oldest' },
]

// Handover 0051: Testing strategies with enhanced dropdown
const testingStrategies = [
  {
    value: 'TDD',
    title: 'TDD (Test-Driven Development)',
    subtitle: 'Write tests before implementation code',
    icon: 'mdi-test-tube',
  },
  {
    value: 'BDD',
    title: 'BDD (Behavior-Driven Development)',
    subtitle: 'Tests based on user stories and behavior specs',
    icon: 'mdi-comment-text-multiple',
  },
  {
    value: 'Integration-First',
    title: 'Integration-First',
    subtitle: 'Focus on testing component interactions',
    icon: 'mdi-connection',
  },
  {
    value: 'E2E-First',
    title: 'E2E-First',
    subtitle: 'Prioritize end-to-end user workflow tests',
    icon: 'mdi-path',
  },
  {
    value: 'Manual',
    title: 'Manual Testing',
    subtitle: 'User-driven QA and exploratory testing',
    icon: 'mdi-human-male',
  },
  {
    value: 'Hybrid',
    title: 'Hybrid Approach',
    subtitle: 'Combination of multiple testing strategies',
    icon: 'mdi-view-grid-plus',
  },
]

// Handover 0051: Unsaved changes computed
const hasUnsavedChanges = computed(() => {
  return autoSave.value?.hasUnsavedChanges.value || false
})

// Handover 0051: Tab validation indicators
const tabValidation = computed(() => {
  return {
    basic: {
      valid: !!productForm.value.name,
      hasError: !productForm.value.name,
      hasWarning: false,
    },
    vision: {
      valid: true,
      hasError: false,
      hasWarning: visionFiles.value.length === 0 && existingVisionDocuments.value.length === 0,
    },
    tech: {
      valid: true,
      hasError: false,
      hasWarning: !productForm.value.configData.tech_stack.languages,
    },
    arch: {
      valid: true,
      hasError: false,
      hasWarning: !productForm.value.configData.architecture.pattern,
    },
    features: {
      valid: true,
      hasError: false,
      hasWarning: !productForm.value.configData.features.core,
    },
  }
})

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

const totalProducts = computed(() => productStore.productCount)
// Handover 0320: Use store as single source of truth
const activeProducts = computed(() => (productStore.activeProduct ? 1 : 0))

const totalTasks = computed(() => {
  return Object.values(productStore.productMetrics).reduce(
    (sum, metrics) => sum + (metrics.totalTasks || 0),
    0,
  )
})

const totalAgents = computed(() => {
  return Object.values(productStore.productMetrics).reduce(
    (sum, metrics) => sum + (metrics.activeAgents || 0),
    0,
  )
})

// Vision document aggregate stats for product details (Handover 0246b: removed totalChunks)
const totalFileSize = computed(() => {
  const bytes = detailsVisionDocuments.value.reduce((sum, doc) => sum + (doc.file_size || 0), 0)
  return formatFileSize(bytes)
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

function getProductInitial(product) {
  return product.name?.charAt(0).toUpperCase() || '?'
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

function getProductMetric(productId, metric) {
  return productStore.productMetrics[productId]?.[metric] || 0
}

function getTaskProgress(productId) {
  const metrics = productStore.productMetrics[productId]
  if (!metrics || !metrics.totalTasks) return 0
  return (metrics.completedTasks / metrics.totalTasks) * 100
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
async function confirmActivation(productId) {
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

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function removeVisionFile(index) {
  visionFiles.value.splice(index, 1)
  visionUploadError.value = null // Clear error when file is removed
}

// Handover 0320: Handler for ProductForm upload-vision event
// Note: Vision files are now managed internally by ProductForm and passed via save event
// This handler is kept for potential future use (e.g., immediate upload)
function uploadVisionDocument(file) {
  // Currently not used - ProductForm passes files via save event
  console.log('[ProductsView] uploadVisionDocument called:', file)
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

// Handover 0508: Validate all vision files
function validateVisionFiles() {
  visionUploadError.value = null

  if (!visionFiles.value || visionFiles.value.length === 0) {
    return true // No files to validate
  }

  for (const file of visionFiles.value) {
    const error = validateVisionFile(file)
    if (error) {
      visionUploadError.value = error
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

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function showProductDetails(product) {
  selectedProduct.value = product

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

async function editProduct(product) {
  editingProduct.value = product

  // Handover 0042: Default config structure
  const defaultConfig = {
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
      quality_standards: '', // Handover 0316: New field
    },
  }

  productForm.value = {
    name: product.name,
    description: product.description || '',
    visionPath: product.vision_path || '',
    projectPath: product.project_path || '', // Handover 0084: Project path for agent export
    // Handover 0042: Merge with existing config_data
    configData: product.config_data ? { ...defaultConfig, ...product.config_data } : defaultConfig,
  }

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

async function deleteVisionDocument(doc) {
  try {
    await api.visionDocuments.delete(doc.id)

    // Remove from list
    existingVisionDocuments.value = existingVisionDocuments.value.filter((d) => d.id !== doc.id)

    showToast({
      message: `${doc.filename} deleted`,
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

async function confirmDelete(product) {
  deletingProduct.value = product
  deleteConfirmationCheck.value = false
  showDeleteDialog.value = true

  // Fetch cascade impact
  loadingCascadeImpact.value = true
  try {
    const response = await api.products.getCascadeImpact(product.id)
    cascadeImpact.value = response.data
  } catch (error) {
    console.error('Failed to get cascade impact:', error)
    showToast({
      message: 'Failed to load deletion impact',
      type: 'error',
      duration: 5000,
    })
  } finally {
    loadingCascadeImpact.value = false
  }
}

async function saveProduct(payload) {
  // Receive data from ProductForm component
  const { productData, visionFiles: uploadFiles } = payload

  // Handover 0508: Validate vision files before saving
  if (uploadFiles && uploadFiles.length > 0) {
    // Update local ref for validation function
    visionFiles.value = uploadFiles
    if (!validateVisionFiles()) {
      return // Validation failed - error already shown via toast
    }
  }

  saving.value = true
  try {
    // Step 1: Create/Update product
    let product
    if (editingProduct.value) {
      product = await productStore.updateProduct(editingProduct.value.id, {
        name: productData.name,
        description: productData.description,
        projectPath: productData.project_path, // Handover 0084: Project path for agent export
        configData: productData.config_data, // Handover 0042
      })
    } else {
      product = await productStore.createProduct({
        name: productData.name,
        description: productData.description,
        projectPath: productData.project_path, // Handover 0084: Project path for agent export
        configData: productData.config_data, // Handover 0042
      })
    }

    // Step 2: Upload vision files (if any) - Handover 0508: Enhanced error handling
    if (visionFiles.value && visionFiles.value.length > 0) {
      const productId = product?.id || editingProduct.value.id
      uploadingVision.value = true
      uploadProgress.value = 0
      visionUploadError.value = null

      let successCount = 0
      let totalChunks = 0

      for (let i = 0; i < visionFiles.value.length; i++) {
        const file = visionFiles.value[i]

        try {
          // Handover 0347: Show chunking indicator for large files (>75KB ≈ >25K tokens)
          if (file.size > 75 * 1024) {
            isChunking.value = true
          }

          // Simulate upload progress
          const progressInterval = setInterval(() => {
            if (uploadProgress.value < 90) {
              uploadProgress.value += 10
            }
          }, 200)

          const formData = new FormData()
          formData.append('product_id', productId)
          formData.append('document_name', file.name.replace(/\.[^/.]+$/, ''))
          formData.append('document_type', 'vision')
          formData.append('vision_file', file)
          formData.append('auto_chunk', 'true')

          const response = await api.visionDocuments.upload(formData)

          clearInterval(progressInterval)
          uploadProgress.value = 100

          successCount++
          const chunkCount = response.data?.chunk_count || 0
          totalChunks += chunkCount

          // Handover 0347: Show chunk count and summarization status
          const isSummarized = response.data?.is_summarized || false
          const isChunked = response.data?.chunked || chunkCount > 0
          let statusParts = []
          if (isSummarized) statusParts.push('summarized')
          if (isChunked) statusParts.push(`${chunkCount} chunks`)

          showToast({
            message: `${file.name} uploaded${statusParts.length ? ' (' + statusParts.join(', ') + ')' : ''}`,
            type: 'success',
            duration: 3000,
          })
        } catch (uploadError) {
          console.error(`Failed to upload ${file.name}:`, uploadError)

          // Handover 0508: Show specific error messages based on status code
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
          } else if (uploadError.request) {
            errorMessage = `${file.name}: Network error. Check connection and try again.`
          }

          visionUploadError.value = errorMessage

          showToast({
            message: errorMessage,
            type: 'error',
            duration: 7000,
          })

          // Continue uploading other files
        } finally {
          isChunking.value = false
        }
      }

      uploadingVision.value = false

      // Handover 0347: Show summary toast with chunk count if multiple files uploaded
      if (successCount > 1) {
        showToast({
          message: `Successfully uploaded ${successCount}/${visionFiles.value.length} vision documents${totalChunks > 0 ? ` (${totalChunks} total chunks)` : ''}`,
          type: 'success',
          duration: 5000,
        })
      }
    }

    // Step 3: Clear auto-save cache (Handover 0051)
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
    // Handover 0051: Do NOT close dialog on error - keep form data visible
  } finally {
    saving.value = false
    uploadingVision.value = false
    uploadProgress.value = 0
    isChunking.value = false
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
    console.error('Failed to delete product:', error)
    showToast({
      message: 'Failed to move product to trash',
      type: 'error',
      duration: 5000,
    })
  } finally {
    deleting.value = false
  }
}

function cancelDelete() {
  showDeleteDialog.value = false
  deletingProduct.value = null
  cascadeImpact.value = null
  deleteConfirmationCheck.value = false
}

function closeDialog() {
  // Handover 0051: Check for unsaved changes before closing
  if (hasUnsavedChanges.value) {
    const confirmed = confirm('You have unsaved changes. Close anyway?')
    if (!confirmed) {
      return // User cancelled - keep dialog open
    }
  }

  // Handover 0051: Clear auto-save cache
  if (autoSave.value) {
    autoSave.value.clearCache()
  }

  showDialog.value = false
  editingProduct.value = null
  visionFiles.value = []
  existingVisionDocuments.value = []
  dialogTab.value = 'basic' // Handover 0042: Reset tab
  productForm.value = {
    name: '',
    description: '',
    visionPath: '',
    projectPath: '', // Handover 0084: Project path for agent export
    // Handover 0042: Reset config_data
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
        quality_standards: '', // Handover 0316: New field
      },
    },
  }
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

async function restoreProduct(product) {
  if (restoringProductId.value) return // Prevent double-click

  restoringProductId.value = product.id
  try {
    await api.products.restoreProduct(product.id)

    showToast({
      message: `${product.name} restored successfully`,
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

// Handover 0049: Helper to check if a field has priority
function hasFieldPriority(fieldPath) {
  return getPriorityForField(fieldPath) !== null
}

// Handover 0051: Watch for dialog open/close to initialize auto-save
watch(showDialog, (isOpen) => {
  if (isOpen) {
    // Generate unique cache key based on edit mode
    const cacheKey = editingProduct.value
      ? `product_form_draft_${editingProduct.value.id}`
      : 'product_form_draft_new'

    // Initialize auto-save composable
    autoSave.value = useAutoSave({
      key: cacheKey,
      data: productForm,
      debounceMs: 500,
      enableBackgroundSave: false, // LocalStorage only (no API saves during typing)
    })

    // Check for existing cache
    const cached = autoSave.value.restoreFromCache()
    if (cached) {
      const metadata = autoSave.value.getCacheMetadata()
      const ageMinutes = metadata?.ageMinutes ?? 0
      const TTL_MINUTES = 15
      // Snapshot current initial state for comparison
      const initialSnapshot = JSON.parse(JSON.stringify(productForm.value))
      const differs = JSON.stringify(cached) !== JSON.stringify(initialSnapshot)

      // Updated policy:
      // - Editing existing product: DO NOT restore cached drafts at all. Always
      //   trust the latest values loaded from the backend to avoid wiping valid
      //   config_data (architecture, features, test_config) when only tech stack
      //   was edited previously.
      // - New product: still do not auto-restore (clean slate).
      autoSave.value.clearCache()
    }
  } else {
    // Dialog closed - cleanup auto-save
    if (autoSave.value) {
      autoSave.value = null
    }
  }
})

// Handover 0051: Browser beforeunload handler (warn on refresh/close with unsaved changes)
function handleBeforeUnload(event) {
  if (showDialog.value && hasUnsavedChanges.value) {
    event.preventDefault()
    event.returnValue = '' // Required for Chrome
  }
}

onMounted(async () => {
  await loadProducts()
  // Load field priority configuration for badge display (Handover 0049)
  try {
    await settingsStore.fetchFieldPriorityConfig()
  } catch (error) {
    console.log('Field priority config not available:', error)
  }
  // Handover 0051: Add beforeunload listener
  window.addEventListener('beforeunload', handleBeforeUnload)
  // Product metrics updates via WebSocket (product:updated events)
})

onUnmounted(() => {
  // Handover 0051: Remove beforeunload listener
  window.removeEventListener('beforeunload', handleBeforeUnload)
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
  border: 2px solid white;
  border-radius: 12px;
}

.product-card:hover {
  transform: translateY(-2px);
}

/* Lighter divider line (25% closer to white) */
.product-divider {
  opacity: 0.3;
  border-color: rgba(255, 255, 255, 0.6) !important;
}

/* Reduce spacing above card actions by 50% */
.product-card :deep(.v-card-actions) {
  padding-top: 4px;
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
  color: #000 !important;
  font-weight: 500;
  font-size: 0.875rem;
  padding: 6px 12px;
  border-radius: 6px;
}
</style>
