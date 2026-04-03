<template>
  <v-dialog v-model="isOpen" max-width="760" scrollable>
    <v-card v-draggable class="smooth-border">
      <div class="dlg-header dlg-header--primary">
        <v-icon class="dlg-icon" icon="mdi-tune" />
        <span class="dlg-title">Tune Context</span>
        <v-spacer />
        <v-btn icon variant="text" size="small" class="dlg-close" @click="handleClose">
          <v-icon icon="mdi-close" size="18" />
        </v-btn>
      </div>

      <v-divider />

      <v-card-text v-if="product" class="pa-4 dialog-body-scroll">
        <div class="text-h6 mb-2">{{ product.name }}</div>
        <div class="text-caption mb-4 text-muted-a11y font-mono tuning-product-id">
          ID: {{ product.id }}
        </div>

        <div v-if="product.tuning_state?.pending_proposals" class="mb-4">
          <div class="text-subtitle-2 mb-2">Tuning Proposals</div>
          <div class="text-caption text-muted-a11y mb-3">
            Review proposed updates detected from product context drift.
          </div>
          <ProductTuningReview
            :product-id="product.id"
            :proposals="product.tuning_state.pending_proposals"
            @proposals-updated="emit('refresh-product')"
          />
        </div>

        <div class="text-subtitle-2 mb-2">Generate Tuning Prompt</div>
        <div class="text-caption text-muted-a11y mb-3">
          Select the product sections you want to retune and generate a prompt for the next pass.
        </div>
        <ProductTuningMenu
          :product-id="product.id"
          hide-trigger
          initially-open
        />
      </v-card-text>

      <v-divider />

      <div class="dlg-footer">
        <v-spacer />
        <v-btn variant="text" @click="handleClose">Close</v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed } from 'vue'
import ProductTuningMenu from './ProductTuningMenu.vue'
import ProductTuningReview from './ProductTuningReview.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  product: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['update:modelValue', 'refresh-product'])

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

function handleClose() {
  emit('update:modelValue', false)
}
</script>

<style lang="scss" scoped>
.tuning-product-id {
  font-size: 0.65rem;
}
</style>
