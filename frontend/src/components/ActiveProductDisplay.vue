<template>
  <v-chip
    :to="{ name: 'Products' }"
    prepend-icon="mdi-package-variant"
    color="primary"
    variant="tonal"
    size="default"
    class="active-product-chip"
  >
    <span class="text-caption font-weight-medium">Active:</span>
    <span class="ml-1 text-truncate" style="max-width: 150px">
      {{ productStore.currentProductName }}
    </span>
  </v-chip>
</template>

<script setup>
import { useProductStore } from '@/stores/products'

const productStore = useProductStore()
</script>

<style scoped>
.active-product-chip {
  cursor: pointer;
  transition: all 0.2s ease;
}

.active-product-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>
