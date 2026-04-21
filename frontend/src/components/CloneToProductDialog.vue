<template>
  <v-dialog
    :model-value="modelValue"
    max-width="480"
    persistent
    retain-focus
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card v-if="modelValue" class="clone-dialog smooth-border">
      <div class="dlg-header dlg-header--primary">
        <v-icon class="dlg-icon">mdi-content-copy</v-icon>
        <span class="dlg-title">Clone "{{ template?.name }}"</span>
        <v-btn
          icon
          variant="text"
          class="dlg-close"
          aria-label="Close"
          @click="$emit('update:modelValue', false)"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </div>

      <v-card-text class="pa-0">
        <div v-if="otherProducts.length === 0" class="clone-empty pa-6 text-center">
          <v-icon size="40" color="grey-lighten-1" class="mb-3">mdi-package-variant</v-icon>
          <div class="text-body-2 text-muted-a11y">No other products available</div>
          <div class="text-caption text-muted-a11y mt-1">
            Create another product first to clone templates across products.
          </div>
        </div>

        <v-list v-else density="compact" class="clone-product-list pa-0">
          <div class="clone-subtitle pa-3 pb-1 text-caption text-muted-a11y">
            Select target product:
          </div>
          <v-list-item
            v-for="product in otherProducts"
            :key="product.id"
            :data-testid="`clone-target-${product.id}`"
            class="clone-product-item"
            :disabled="cloning"
            @click="handleClone(product)"
          >
            <template #prepend>
              <v-icon size="20" color="primary">mdi-package-variant</v-icon>
            </template>
            <v-list-item-title class="text-body-2 font-weight-medium">
              {{ product.name }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-card-text>

      <div v-if="otherProducts.length > 0" class="dlg-footer">
        <v-spacer />
        <v-btn variant="text" @click="$emit('update:modelValue', false)">Cancel</v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import api from '@/services/api'
import { useToast } from '@/composables/useToast'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  template: {
    type: Object,
    default: null,
  },
  products: {
    type: Array,
    default: () => [],
  },
  currentProductId: {
    type: [Number, String],
    default: null,
  },
})

const emit = defineEmits(['update:modelValue', 'cloned'])

const { showToast } = useToast()
const cloning = ref(false)

const otherProducts = computed(() => {
  if (!props.currentProductId) return props.products
  return props.products.filter(
    (p) => String(p.id) !== String(props.currentProductId)
  )
})

async function handleClone(targetProduct) {
  if (!props.template?.id || cloning.value) return

  cloning.value = true
  try {
    await api.templates.cloneToProduct(props.template.id, targetProduct.id)

    showToast({
      message: `Template cloned to ${targetProduct.name}`,
      type: 'success',
    })

    emit('cloned', {
      templateId: props.template.id,
      targetProductId: targetProduct.id,
      targetProductName: targetProduct.name,
    })

    emit('update:modelValue', false)
  } catch (error) {
    const detail =
      error.response?.data?.detail || 'Failed to clone template. Please try again.'
    showToast({
      message: detail,
      type: 'error',
    })
  } finally {
    cloning.value = false
  }
}
</script>

<style scoped lang="scss">
@use '../styles/design-tokens' as *;

.clone-dialog {
  overflow: hidden;
}

.clone-product-list {
  max-height: 320px;
  overflow-y: auto;
}

.clone-product-item {
  cursor: pointer;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: rgba(var(--v-theme-primary), 0.08);
  }
}

.clone-empty {
  min-height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
</style>
