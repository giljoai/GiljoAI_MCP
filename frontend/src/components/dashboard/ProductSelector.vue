<template>
  <div class="product-selector d-flex justify-center flex-wrap ga-2 py-2" role="radiogroup" aria-label="Product filter">
    <button
      :class="['pill-filter', 'smooth-border', { active: selectedProductId === null }]"
      role="radio"
      :aria-checked="selectedProductId === null"
      aria-label="All Products"
      @click="$emit('select', null)"
    >
      All Products
    </button>
    <button
      v-for="product in products"
      :key="product.id"
      :class="['pill-filter', 'smooth-border', { active: selectedProductId === product.id }]"
      role="radio"
      :aria-checked="selectedProductId === product.id"
      :aria-label="product.name"
      @click="$emit('select', product.id)"
    >
      {{ product.name }}
    </button>
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

<style lang="scss" scoped>
@use '../../styles/design-tokens' as *;
.product-selector {
  min-height: 40px;
}

.pill-filter {
  display: inline-flex;
  align-items: center;
  border-radius: $border-radius-pill;
  padding: 8px 18px;
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  transition: $transition-all-fast;
  background: transparent;
  color: var(--text-muted);
  border: none;
  --smooth-border-color: rgba(var(--v-theme-on-surface), 0.15);
}

.pill-filter:hover {
  color: var(--text-secondary);
  --smooth-border-color: rgba(var(--v-theme-on-surface), 0.25);
}

.pill-filter.active,
.pill-filter.active:hover {
  background: rgba(255, 195, 0, 0.12);
  color: #ffc300;
  box-shadow: none;
}
</style>
