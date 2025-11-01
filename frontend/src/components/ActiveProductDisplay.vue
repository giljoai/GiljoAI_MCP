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
      class="active-product-chip text-white"
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
  <v-chip
    v-else
    variant="text"
    size="small"
    class="active-product-chip-loading"
  >
    <v-progress-circular
      indeterminate
      size="18"
      width="2"
      class="mr-2"
    ></v-progress-circular>
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

// Fetch active product on mount
onMounted(async () => {
  loading.value = true
  try {
    await productsStore.fetchActiveProduct()
    console.log('[ActiveProductDisplay] Initial active product:', productsStore.activeProduct)
  } catch (err) {
    console.error('[ActiveProductDisplay] Failed to fetch active product:', err)
  } finally {
    loading.value = false
  }
})

// Watch for changes to activeProduct (for debugging)
watch(
  () => productsStore.activeProduct,
  (newProduct, oldProduct) => {
    console.log('[ActiveProductDisplay] Active product changed:', {
      from: oldProduct?.name || 'null',
      to: newProduct?.name || 'null'
    })
  }
)

// Listen for product activation events via WebSocket (when implemented)
// Whenever a product is activated, refresh the display
const handleProductActivated = async () => {
  try {
    await productsStore.fetchActiveProduct()
  } catch (err) {
    console.error('[ActiveProductDisplay] Failed to refresh active product:', err)
  }
}

// Subscribe to product activation events if available
onMounted(() => {
  // This can be enhanced with WebSocket listeners when available
  // wsStore.subscribe('product:activated', handleProductActivated)
})

onUnmounted(() => {
  // Cleanup WebSocket subscription if needed
  // wsStore.unsubscribe('product:activated', handleProductActivated)
})
</script>

<style scoped>
.active-product-chip {
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  color: #fff !important; /* Ensure white indicator text when active */
}

.active-product-chip:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.active-product-chip-loading {
  white-space: nowrap;
}
</style>
