<template>
  <BaseDialog
    v-model="isOpen"
    type="warning"
    title="Switch Active Product?"
    size="lg"
    :confirm-label="confirmLabel"
    :loading="isActivating"
    @confirm="handleConfirm"
    @cancel="handleCancel"
  >
    <v-alert type="info" variant="tonal" density="compact" class="mb-4">
      <div class="text-body-1">
        Switching the active product will change the context for all new AI agent operations.
      </div>
    </v-alert>

    <div class="mb-3">
      <div class="text-subtitle-2 activation-text-muted">Current Active Product:</div>
      <div class="text-h6 ml-2 mt-1">
        {{ currentActive?.name || 'None' }}
      </div>
    </div>

    <div class="mb-4">
      <div class="text-subtitle-2 activation-text-muted">New Active Product:</div>
      <div class="text-h6 ml-2 mt-1 text-primary">
        {{ newProduct?.name || 'Unknown' }}
      </div>
    </div>

    <!-- Handover 0050b: Show project deactivation impact -->
    <v-alert
      v-if="currentActive?.active_projects_count > 0"
      type="warning"
      variant="tonal"
      class="mb-4"
    >
      <div class="font-weight-bold mb-2">Project Impact:</div>
      <strong>{{ currentActive.active_projects_count }}</strong>
      active project{{ currentActive.active_projects_count > 1 ? 's' : '' }} under
      <strong>{{ currentActive.name }}</strong> will be deactivated.

      <div class="text-caption mt-2">
        Only one project can be active at a time. You can reactivate projects after switching
        back to this product.
      </div>
    </v-alert>

    <v-expansion-panels class="mt-4">
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-information</v-icon>
          What will happen?
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <ul class="text-body-2">
            <li class="mb-2">
              <strong>{{ newProduct?.name }}</strong> becomes the active product
            </li>
            <li class="mb-2">
              All new agent jobs will use <strong>{{ newProduct?.name }}</strong>
            </li>
            <li class="mb-2">
              The Orchestrator switches context to <strong>{{ newProduct?.name }}</strong>
            </li>
            <li class="mb-2">
              Running agent jobs for <strong>{{ currentActive?.name }}</strong> continue but
              cannot spawn new jobs
            </li>
          </ul>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </BaseDialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import BaseDialog from '@/components/common/BaseDialog.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  newProduct: {
    type: Object,
    required: false,
    default: () => ({}),
    validator: (val) => {
      // Allow empty object or object with name
      return !val || typeof val.name === 'string' || Object.keys(val).length === 0
    },
  },
  currentActive: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const isActivating = ref(false)

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const confirmLabel = computed(() => `Switch to ${props.newProduct?.name || 'product'}`)

const handleConfirm = () => {
  isActivating.value = true
  emit('confirm', props.newProduct.id)
}

const handleCancel = () => {
  if (!isActivating.value) {
    emit('cancel')
    isOpen.value = false
  }
}

// Reset loading state when dialog closes
watch(
  () => props.modelValue,
  (newVal) => {
    if (!newVal) {
      isActivating.value = false
    }
  },
)
</script>

<style scoped>
.activation-text-muted {
  color: #8895a8 !important;
}
</style>
