<template>
  <!-- Active Product Chip (Handover 0049) -->
  <div v-if="!loading">
    <!-- Active Product Exists -->
    <v-chip
      v-if="productsStore.activeProduct"
      :to="{ name: 'Products' }"
      prepend-icon="mdi-package-variant-closed"
      color="primary"
      variant="flat"
      size="small"
      class="active-product-chip"
      aria-label="Click to view active product"
    >
      <span class="font-weight-medium">Active: {{ productsStore.activeProduct.name }}</span>
    </v-chip>

    <!-- No Active Product -->
    <v-chip
      v-else
      prepend-icon="mdi-package-variant"
      color="grey"
      variant="text"
      size="small"
      disabled
      aria-label="No active product"
    >
      <span class="text-caption">No Active Product</span>
    </v-chip>
  </div>

  <!-- Loading State -->
  <v-chip v-else variant="text" size="small" class="active-product-chip-loading">
    <v-progress-circular indeterminate size="18" width="2" class="mr-2"></v-progress-circular>
    <span class="text-caption">Loading...</span>
  </v-chip>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useProductStore } from '@/stores/products'
import { useWebSocketStore } from '@/stores/websocket'

const productsStore = useProductStore()
const wsStore = useWebSocketStore()

// Loading state for initial fetch
const loading = ref(true)
let unsubscribe = null

// Listen for product status changes via WebSocket (tenant-scoped)
// Whenever a product is activated/deactivated, refresh the display
const handleProductStatusChanged = async (_payload) => {
  try {
    await productsStore.fetchActiveProduct()
  } catch (err) {
    console.error('[ActiveProductDisplay] Failed to refresh active product:', err)
  }
}

// Single onMounted hook for all initialization
onMounted(async () => {
  // 1. Subscribe to WebSocket events first
  try {
    unsubscribe = wsStore.on('product:status:changed', handleProductStatusChanged)
  } catch (_e) {
    console.warn('[ActiveProductDisplay] Failed to register WS handler')
  }

  // 2. Fetch initial active product
  loading.value = true
  try {
    await productsStore.fetchActiveProduct()
  } catch (err) {
    console.error('[ActiveProductDisplay] Failed to fetch active product:', err)
  } finally {
    loading.value = false
  }
})

// Watch for changes to activeProduct (for debugging and reactivity)
watch(
  () => productsStore.activeProduct,
  (_newProduct, _oldProduct) => {
    // Active product changed
  },
  { immediate: false },
)

onUnmounted(() => {
  // Cleanup WebSocket subscription
  try {
    if (typeof unsubscribe === 'function') {
      unsubscribe()
    }
  } catch (_e) {
    // no-op
  }
})
</script>

<style scoped>
.active-product-chip {
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.active-product-chip:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.active-product-chip-loading {
  white-space: nowrap;
}
</style>
