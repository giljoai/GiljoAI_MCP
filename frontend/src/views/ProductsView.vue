<template>
  <v-container fluid>
    <!-- Page Header -->
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center mb-6">
          <v-icon size="32" color="primary" class="mr-3">mdi-package-variant</v-icon>
          <div>
            <h1 class="text-h4 font-weight-bold">Products Overview</h1>
            <p class="text-body-2 text-medium-emphasis mt-1">
              Manage and monitor all products across the system
            </p>
          </div>
          <v-spacer></v-spacer>
          <v-btn color="primary" prepend-icon="mdi-plus" @click="showCreateDialog = true">
            New Product
          </v-btn>
        </div>
      </v-col>
    </v-row>

    <!-- Summary Cards -->
    <v-row>
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon size="40" color="primary" class="mr-3">mdi-package-variant</v-icon>
              <div>
                <div class="text-h5 font-weight-bold">{{ totalProducts }}</div>
                <div class="text-caption text-medium-emphasis">Total Products</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon size="40" color="success" class="mr-3">mdi-check-circle</v-icon>
              <div>
                <div class="text-h5 font-weight-bold">{{ activeProducts }}</div>
                <div class="text-caption text-medium-emphasis">Active Products</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon size="40" color="info" class="mr-3">mdi-clipboard-list</v-icon>
              <div>
                <div class="text-h5 font-weight-bold">{{ totalTasks }}</div>
                <div class="text-caption text-medium-emphasis">Total Tasks</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon size="40" color="warning" class="mr-3">mdi-robot</v-icon>
              <div>
                <div class="text-h5 font-weight-bold">{{ totalAgents }}</div>
                <div class="text-caption text-medium-emphasis">Active Agents</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Products Grid -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center">
            <span>All Products</span>
            <v-spacer></v-spacer>
            <v-text-field
              v-model="search"
              prepend-inner-icon="mdi-magnify"
              label="Search products..."
              single-line
              hide-details
              variant="outlined"
              density="compact"
              class="ml-4"
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
                <v-card
                  :elevation="product.id === productStore.currentProductId ? 8 : 2"
                  :color="product.id === productStore.currentProductId ? 'primary' : undefined"
                  :variant="product.id === productStore.currentProductId ? 'tonal' : 'elevated'"
                  class="product-card h-100"
                >
                  <v-card-text>
                    <div class="d-flex align-center mb-3">
                      <v-avatar
                        size="48"
                        :color="
                          product.id === productStore.currentProductId
                            ? 'primary'
                            : 'grey-lighten-2'
                        "
                      >
                        <span class="text-h6">{{ getProductInitial(product) }}</span>
                      </v-avatar>
                      <div class="ml-3 flex-grow-1">
                        <div class="font-weight-medium text-truncate">{{ product.name }}</div>
                        <div class="text-caption text-medium-emphasis">
                          ID: {{ product.id.slice(0, 8) }}...
                        </div>
                      </div>
                      <v-chip
                        v-if="product.id === productStore.currentProductId"
                        color="primary"
                        size="small"
                        variant="flat"
                      >
                        Current
                      </v-chip>
                    </div>

                    <div class="text-body-2 text-medium-emphasis mb-3" style="min-height: 40px">
                      {{ product.description || 'No description available' }}
                    </div>

                    <!-- Product Metrics -->
                    <v-divider class="my-3"></v-divider>
                    <v-row dense>
                      <v-col cols="6">
                        <div class="text-center">
                          <div class="text-h6 font-weight-bold">
                            {{ getProductMetric(product.id, 'totalTasks') }}
                          </div>
                          <div class="text-caption text-medium-emphasis">Tasks</div>
                        </div>
                      </v-col>
                      <v-col cols="6">
                        <div class="text-center">
                          <div class="text-h6 font-weight-bold">
                            {{ getProductMetric(product.id, 'activeAgents') }}
                          </div>
                          <div class="text-caption text-medium-emphasis">Agents</div>
                        </div>
                      </v-col>
                    </v-row>

                    <!-- Progress Bar -->
                    <v-progress-linear
                      :model-value="getTaskProgress(product.id)"
                      color="success"
                      height="6"
                      rounded
                      class="mt-3"
                    ></v-progress-linear>
                    <div class="text-caption text-center text-medium-emphasis mt-1">
                      {{ getProductMetric(product.id, 'completedTasks') }} /
                      {{ getProductMetric(product.id, 'totalTasks') }} tasks complete
                    </div>
                  </v-card-text>

                  <v-card-actions>
                    <v-btn
                      variant="text"
                      size="small"
                      @click="selectProduct(product.id)"
                      :disabled="product.id === productStore.currentProductId"
                    >
                      {{ product.id === productStore.currentProductId ? 'Active' : 'Switch To' }}
                    </v-btn>
                    <v-spacer></v-spacer>
                    <v-btn icon size="small" variant="text" @click="showProductDetails(product)">
                      <v-icon>mdi-information-outline</v-icon>
                    </v-btn>
                    <v-btn icon size="small" variant="text" @click="editProduct(product)">
                      <v-icon>mdi-pencil</v-icon>
                    </v-btn>
                    <v-btn
                      icon
                      size="small"
                      variant="text"
                      color="error"
                      @click="confirmDelete(product)"
                    >
                      <v-icon>mdi-delete</v-icon>
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Create/Edit Product Dialog -->
    <v-dialog v-model="showDialog" max-width="600" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">{{ editingProduct ? 'mdi-pencil' : 'mdi-plus' }}</v-icon>
          <span>{{ editingProduct ? 'Edit Product' : 'Create New Product' }}</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" @click="closeDialog" aria-label="Close" />
        </v-card-title>

        <v-card-text>
          <v-form ref="productForm" v-model="formValid">
            <v-text-field
              v-model="productForm.name"
              label="Product Name"
              :rules="[(v) => !!v || 'Name is required']"
              required
              variant="outlined"
              density="comfortable"
              class="mb-3"
            ></v-text-field>

            <v-textarea
              v-model="productForm.description"
              label="Description"
              variant="outlined"
              density="comfortable"
              rows="3"
              class="mb-3"
            ></v-textarea>

            <v-text-field
              v-model="productForm.visionPath"
              label="Vision Document Path"
              variant="outlined"
              density="comfortable"
              hint="Path to the product's vision documents"
              persistent-hint
            ></v-text-field>
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="closeDialog">Cancel</v-btn>
          <v-btn
            color="primary"
            variant="flat"
            @click="saveProduct"
            :loading="saving"
            :disabled="!formValid"
          >
            {{ editingProduct ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="400" persistent retain-focus>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="error">mdi-alert</v-icon>
          <span>Confirm Delete</span>
          <v-spacer />
          <v-btn
            icon="mdi-close"
            variant="text"
            @click="showDeleteDialog = false"
            aria-label="Close"
          />
        </v-card-title>
        <v-card-text>
          Are you sure you want to delete the product "{{ deletingProduct?.name }}"? This action
          cannot be undone and will remove all associated data.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showDeleteDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="flat" @click="deleteProduct" :loading="deleting">
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useProductStore } from '@/stores/products'
import { useRouter } from 'vue-router'

const productStore = useProductStore()
const router = useRouter()

// State
const loading = ref(false)
const search = ref('')
const showDialog = ref(false)
const showDeleteDialog = ref(false)
const showCreateDialog = ref(false)
const editingProduct = ref(null)
const deletingProduct = ref(null)
const saving = ref(false)
const deleting = ref(false)
const formValid = ref(false)

const productForm = ref({
  name: '',
  description: '',
  visionPath: '',
})

// Computed
const filteredProducts = computed(() => {
  if (!search.value) return productStore.products

  const searchLower = search.value.toLowerCase()
  return productStore.products.filter(
    (product) =>
      product.name.toLowerCase().includes(searchLower) ||
      product.description?.toLowerCase().includes(searchLower),
  )
})

const totalProducts = computed(() => productStore.productCount)
const activeProducts = computed(
  () => productStore.products.filter((p) => p.status === 'active').length,
)

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

// Methods
function getProductInitial(product) {
  return product.name?.charAt(0).toUpperCase() || '?'
}

function getProductMetric(productId, metric) {
  return productStore.productMetrics[productId]?.[metric] || 0
}

function getTaskProgress(productId) {
  const metrics = productStore.productMetrics[productId]
  if (!metrics || !metrics.totalTasks) return 0
  return (metrics.completedTasks / metrics.totalTasks) * 100
}

async function selectProduct(productId) {
  try {
    await productStore.setCurrentProduct(productId)
    router.push('/dashboard')
  } catch (error) {
    console.error('Failed to switch product:', error)
  }
}

function showProductDetails(product) {
  // Navigate to product detail view or show modal
  router.push(`/products/${product.id}`)
}

function editProduct(product) {
  editingProduct.value = product
  productForm.value = {
    name: product.name,
    description: product.description || '',
    visionPath: product.vision_path || '',
  }
  showDialog.value = true
}

function confirmDelete(product) {
  deletingProduct.value = product
  showDeleteDialog.value = true
}

async function saveProduct() {
  if (!formValid.value) return

  saving.value = true
  try {
    if (editingProduct.value) {
      await productStore.updateProduct(editingProduct.value.id, {
        name: productForm.value.name,
        description: productForm.value.description,
        vision_path: productForm.value.visionPath,
      })
    } else {
      await productStore.createProduct({
        name: productForm.value.name,
        description: productForm.value.description,
        vision_path: productForm.value.visionPath,
      })
    }
    closeDialog()
    await loadProducts()
  } catch (error) {
    console.error('Failed to save product:', error)
  } finally {
    saving.value = false
  }
}

async function deleteProduct() {
  if (!deletingProduct.value) return

  deleting.value = true
  try {
    await productStore.deleteProduct(deletingProduct.value.id)
    showDeleteDialog.value = false
    deletingProduct.value = null
    await loadProducts()
  } catch (error) {
    console.error('Failed to delete product:', error)
  } finally {
    deleting.value = false
  }
}

function closeDialog() {
  showDialog.value = false
  editingProduct.value = null
  productForm.value = {
    name: '',
    description: '',
    visionPath: '',
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
  } finally {
    loading.value = false
  }
}

// Auto-refresh metrics
let refreshInterval = null

onMounted(async () => {
  await loadProducts()

  // Refresh metrics every 30 seconds
  refreshInterval = setInterval(async () => {
    for (const product of productStore.products) {
      await productStore.fetchProductMetrics(product.id)
    }
  }, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.product-card {
  transition: all 0.3s ease;
}

.product-card:hover {
  transform: translateY(-2px);
}
</style>
