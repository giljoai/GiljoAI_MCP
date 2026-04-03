<template>
  <v-dialog v-model="isOpen" max-width="800" persistent retain-focus scrollable>
    <v-card v-draggable class="smooth-border">
      <div class="dlg-header">
        <v-icon class="dlg-icon" icon="mdi-delete-restore" />
        <span class="dlg-title">Deleted Products ({{ deletedProducts.length }})</span>
        <v-btn icon variant="text" size="small" class="dlg-close" aria-label="Close dialog" @click="closeDialog">
          <v-icon icon="mdi-close" size="18" />
        </v-btn>
      </div>

      <v-divider />

      <v-card-text class="pa-4">
        <v-alert
          v-if="deletedProducts.length > 0"
          type="warning"
          variant="tonal"
          density="compact"
          class="mb-3"
        >
          Permanently deleting items will remove all related data immediately. This action cannot
          be undone.
        </v-alert>

        <v-list v-if="deletedProducts.length > 0" class="border rounded">
          <v-list-item v-for="(product, index) in deletedProducts" :key="product.id">
            <template v-slot:prepend>
              <v-icon icon="mdi-package-variant-closed"></v-icon>
            </template>

            <div class="flex-grow-1">
              <div class="font-weight-bold">{{ product.name }}</div>
              <div class="text-caption text-muted-a11y">
                {{ product.description || product.id }}
              </div>
            </div>

            <template v-slot:append>
              <div class="d-flex align-center ga-1">
                <v-btn
                  icon="mdi-delete-restore"
                  size="small"
                  variant="text"
                  :loading="restoringProductId === product.id"
                  :disabled="purgingProductId === product.id || purgingAll"
                  title="Restore product"
                  aria-label="Restore deleted product"
                  @click="handleRestore(product.id)"
                ></v-btn>
                <v-btn
                  icon="mdi-delete-forever"
                  size="small"
                  variant="text"
                  color="error"
                  :loading="purgingProductId === product.id"
                  :disabled="restoringProductId === product.id || purgingAll"
                  title="Permanently delete product"
                  aria-label="Permanently delete product"
                  @click="handlePurge(product.id)"
                ></v-btn>
              </div>
            </template>

            <v-divider v-if="index < deletedProducts.length - 1" class="my-2" />
          </v-list-item>
        </v-list>

        <div v-else class="text-center py-8 text-muted-a11y">
          <v-icon size="48" class="mb-4">mdi-package-variant</v-icon>
          <p>No deleted products</p>
        </div>
      </v-card-text>

      <v-divider />

      <div class="dlg-footer">
        <v-spacer />
        <v-btn variant="text" @click="closeDialog">Close</v-btn>
        <v-btn
          color="error"
          variant="flat"
          prepend-icon="mdi-delete-forever"
          :disabled="deletedProducts.length === 0 || purgingAll"
          :loading="purgingAll"
          @click="handlePurgeAll"
        >
          Delete All
        </v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  deletedProducts: {
    type: Array,
    default: () => [],
  },
  restoringProductId: {
    type: String,
    default: null,
  },
  purgingProductId: {
    type: String,
    default: null,
  },
  purgingAll: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'restore', 'purge', 'purge-all'])

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const closeDialog = () => {
  emit('update:modelValue', false)
}

const handleRestore = (productId) => {
  emit('restore', productId)
}

const handlePurge = (productId) => {
  emit('purge', productId)
}

const handlePurgeAll = () => {
  emit('purge-all')
}
</script>
