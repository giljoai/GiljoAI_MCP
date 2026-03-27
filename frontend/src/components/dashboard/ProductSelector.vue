<template>
  <div class="product-selector d-flex justify-center flex-wrap ga-2 py-2">
    <v-chip
      color="yellow-darken-2"
      :variant="selectedProductId === null ? 'flat' : 'outlined'"
      size="default"
      class="product-chip"
      role="radio"
      :aria-checked="selectedProductId === null"
      aria-label="All Products"
      @click="$emit('select', null)"
    >
      All Products
    </v-chip>
    <v-chip
      v-for="product in products"
      :key="product.id"
      color="yellow-darken-2"
      :variant="selectedProductId === product.id ? 'flat' : 'outlined'"
      size="default"
      class="product-chip"
      role="radio"
      :aria-checked="selectedProductId === product.id"
      :aria-label="product.name"
      @click="$emit('select', product.id)"
    >
      {{ product.name }}
    </v-chip>
  </div>
</template>

<script setup>
defineProps({
  products: {
    type: Array,
    default: () => [],
  },
  selectedProductId: {
    type: [String, Number, null],
    default: null,
  },
})

defineEmits(['select'])
</script>

<style scoped>
.product-selector {
  min-height: 40px;
}

.product-chip {
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s ease;
}

.product-chip:hover {
  opacity: 0.85;
}
</style>
