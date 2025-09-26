<template>
  <v-menu v-model="menu" :close-on-content-click="false" location="bottom" min-width="300">
    <template v-slot:activator="{ props }">
      <v-btn
        v-bind="props"
        variant="tonal"
        prepend-icon="mdi-package-variant"
        :loading="productStore.loading"
        class="product-switcher-btn"
      >
        <div class="text-truncate" style="max-width: 200px">
          {{ productStore.currentProductName }}
        </div>
        <v-icon end>mdi-chevron-down</v-icon>
      </v-btn>
    </template>

    <v-card min-width="350">
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-package-variant</v-icon>
        Product Context
        <v-spacer></v-spacer>
        <v-btn icon variant="text" size="small" @click="menu = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider></v-divider>

      <!-- Current Product Info -->
      <v-card-text v-if="productStore.currentProduct" class="pb-2">
        <div class="text-caption text-medium-emphasis mb-1">Current Product</div>
        <div class="d-flex align-center">
          <v-avatar color="primary" size="32" class="mr-3">
            <span class="text-h6">{{ productInitial }}</span>
          </v-avatar>
          <div>
            <div class="font-weight-medium">{{ productStore.currentProduct.name }}</div>
            <div class="text-caption text-medium-emphasis">
              ID: {{ productStore.currentProductId?.slice(0, 8) }}...
            </div>
          </div>
        </div>

        <!-- Product Metrics -->
        <v-row v-if="productStore.currentProductMetrics" class="mt-2" dense>
          <v-col cols="6">
            <div class="text-caption text-medium-emphasis">Tasks</div>
            <div class="font-weight-medium">
              {{ productStore.currentProductMetrics.completedTasks }} /
              {{ productStore.currentProductMetrics.totalTasks }}
            </div>
          </v-col>
          <v-col cols="6">
            <div class="text-caption text-medium-emphasis">Active Agents</div>
            <div class="font-weight-medium">
              {{ productStore.currentProductMetrics.activeAgents }}
            </div>
          </v-col>
        </v-row>
      </v-card-text>

      <v-divider v-if="productStore.currentProduct"></v-divider>

      <!-- Product List -->
      <v-card-text class="pa-2">
        <div class="text-caption text-medium-emphasis mb-2 px-2">
          Available Products ({{ productStore.productCount }})
        </div>

        <v-list density="compact" class="py-0">
          <v-list-item
            v-for="product in productStore.products"
            :key="product.id"
            :active="product.id === productStore.currentProductId"
            @click="selectProduct(product.id)"
            :prepend-avatar="null"
            rounded
          >
            <template v-slot:prepend>
              <v-avatar
                size="28"
                :color="product.id === productStore.currentProductId ? 'primary' : 'grey-lighten-2'"
              >
                <span class="text-caption">{{ getProductInitial(product) }}</span>
              </v-avatar>
            </template>

            <v-list-item-title>{{ product.name }}</v-list-item-title>
            <v-list-item-subtitle>
              {{ product.description || 'No description' }}
            </v-list-item-subtitle>

            <template v-slot:append v-if="product.id === productStore.currentProductId">
              <v-icon color="primary" size="small">mdi-check</v-icon>
            </template>
          </v-list-item>

          <!-- No Products Message -->
          <v-list-item v-if="!productStore.hasProducts">
            <v-list-item-title class="text-center text-medium-emphasis">
              No products available
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-card-text>

      <v-divider></v-divider>

      <!-- Actions -->
      <v-card-actions>
        <v-btn variant="text" size="small" prepend-icon="mdi-plus" @click="showCreateDialog = true">
          New Product
        </v-btn>
        <v-spacer></v-spacer>
        <v-btn
          variant="text"
          size="small"
          prepend-icon="mdi-refresh"
          @click="refreshProducts"
          :loading="refreshing"
        >
          Refresh
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-menu>

  <!-- Create Product Dialog -->
  <v-dialog v-model="showCreateDialog" max-width="500">
    <v-card>
      <v-card-title>
        <v-icon start>mdi-package-variant-plus</v-icon>
        Create New Product
      </v-card-title>

      <v-card-text>
        <v-form ref="createForm" v-model="formValid">
          <v-text-field
            v-model="newProduct.name"
            label="Product Name"
            :rules="[(v) => !!v || 'Name is required']"
            required
            variant="outlined"
            density="comfortable"
            class="mb-3"
          ></v-text-field>

          <v-textarea
            v-model="newProduct.description"
            label="Description"
            variant="outlined"
            density="comfortable"
            rows="3"
          ></v-textarea>

          <v-text-field
            v-model="newProduct.visionPath"
            label="Vision Document Path (Optional)"
            variant="outlined"
            density="comfortable"
            hint="Path to the product's vision documents"
          ></v-text-field>
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="showCreateDialog = false"> Cancel </v-btn>
        <v-btn
          color="primary"
          variant="flat"
          @click="createProduct"
          :loading="creating"
          :disabled="!formValid"
        >
          Create
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useProductStore } from '@/stores/products'
import { useRouter } from 'vue-router'

const productStore = useProductStore()
const router = useRouter()

const menu = ref(false)
const showCreateDialog = ref(false)
const refreshing = ref(false)
const creating = ref(false)
const formValid = ref(false)

const newProduct = ref({
  name: '',
  description: '',
  visionPath: '',
})

const productInitial = computed(() => {
  if (!productStore.currentProduct?.name) return '?'
  return productStore.currentProduct.name.charAt(0).toUpperCase()
})

function getProductInitial(product) {
  return product.name?.charAt(0).toUpperCase() || '?'
}

async function selectProduct(productId) {
  try {
    await productStore.setCurrentProduct(productId)
    menu.value = false

    // Reload current route to refresh data with new product context
    router.go(0)
  } catch (error) {
    console.error('Failed to switch product:', error)
  }
}

async function refreshProducts() {
  refreshing.value = true
  try {
    await productStore.fetchProducts()
  } finally {
    refreshing.value = false
  }
}

async function createProduct() {
  creating.value = true
  try {
    const product = await productStore.createProduct({
      name: newProduct.value.name,
      description: newProduct.value.description,
      vision_path: newProduct.value.visionPath || null,
    })

    if (product) {
      showCreateDialog.value = false
      // Reset form
      newProduct.value = {
        name: '',
        description: '',
        visionPath: '',
      }
      // Product store automatically switches to new product
    }
  } catch (error) {
    console.error('Failed to create product:', error)
  } finally {
    creating.value = false
  }
}

// Load products on mount
onMounted(async () => {
  await productStore.fetchProducts()
  productStore.initializeFromStorage()
})
</script>

<style scoped>
.product-switcher-btn {
  min-width: 120px;
  max-width: 300px;
}
</style>
