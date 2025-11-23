<template>
  <v-dialog v-model="isOpen" max-width="800" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start color="warning">mdi-delete-restore</v-icon>
        Deleted Products
        <v-spacer></v-spacer>
        <v-btn icon variant="text" @click="closeDialog">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider></v-divider>

      <v-card-text style="max-height: 500px; overflow-y: auto">
        <v-alert type="info" variant="tonal" density="compact" class="mb-4">
          Products are recoverable for 10 days after deletion. After that, they will be permanently
          purged.
        </v-alert>

        <div v-if="loading" class="text-center py-8">
          <v-progress-circular indeterminate color="warning"></v-progress-circular>
          <div class="text-caption mt-2">Loading deleted products...</div>
        </div>

        <div v-else-if="deletedProducts.length === 0" class="text-center py-8">
          <v-icon size="64" color="grey-lighten-2">mdi-delete-empty</v-icon>
          <div class="text-h6 text-medium-emphasis mt-4">No deleted products</div>
        </div>

        <v-list v-else density="compact">
          <v-list-item
            v-for="product in deletedProducts"
            :key="product.id"
            class="border rounded mb-3 pa-3"
          >
            <div class="d-flex flex-column">
              <div class="d-flex align-center justify-space-between mb-2">
                <div>
                  <div class="text-h6">{{ product.name }}</div>
                  <div class="text-caption text-medium-emphasis">
                    {{ product.description || 'No description' }}
                  </div>
                </div>
                <v-chip
                  :color="getDaysPurgeColor(product.days_until_purge)"
                  size="small"
                  variant="flat"
                >
                  {{ formatDaysLeft(product.days_until_purge) }}
                </v-chip>
              </div>

              <v-divider class="my-2"></v-divider>

              <div class="d-flex align-center justify-space-between">
                <div class="text-caption">
                  <v-icon size="16" class="mr-1">mdi-folder-multiple</v-icon>
                  {{ product.project_count }}
                  {{ product.project_count === 1 ? 'project' : 'projects' }}
                  <span class="mx-1">|</span>
                  <v-icon size="16" class="mr-1">mdi-file-document</v-icon>
                  {{ product.vision_documents_count }} vision docs
                  <span class="mx-1">|</span>
                  <v-icon size="16" class="mr-1">mdi-clock-outline</v-icon>
                  Deleted {{ formatDate(product.deleted_at) }}
                </div>
                <v-btn
                  color="success"
                  variant="flat"
                  size="small"
                  prepend-icon="mdi-restore"
                  @click="handleRestore(product.id)"
                  :loading="restoringProductId === product.id"
                  :disabled="restoringProductId !== null"
                >
                  Restore
                </v-btn>
              </div>
            </div>
          </v-list-item>
        </v-list>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="closeDialog">Close</v-btn>
      </v-card-actions>
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
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'restore'])

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

const getDaysPurgeColor = (days) => {
  if (days > 5) return 'success'
  if (days >= 3) return 'warning'
  return 'error'
}

const formatDaysLeft = (days) => {
  if (days === 1) return '1 day left'
  return `${days} days left`
}

const formatDate = (dateString) => {
  if (!dateString) return 'Unknown'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}
</script>

<style scoped>
/* Additional styling if needed */
</style>
