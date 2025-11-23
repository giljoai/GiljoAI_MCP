<template>
  <v-dialog v-model="isOpen" max-width="500" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start color="warning">mdi-delete</v-icon>
        Move Product to Trash?
      </v-card-title>

      <v-divider></v-divider>

      <v-card-text v-if="product">
        <!-- Loading State -->
        <div v-if="loading" class="text-center py-4">
          <v-progress-circular indeterminate color="error"></v-progress-circular>
          <div class="text-caption mt-2">Calculating impact...</div>
        </div>

        <!-- Warning Content -->
        <div v-else>
          <v-alert type="warning" variant="tonal" density="compact" class="mb-4">
            <div class="text-subtitle-1 font-weight-bold mb-2">Move to Trash?</div>
            <div>
              <strong>{{ product.name }}</strong> will be moved to trash and can be recovered for 10
              days. After 10 days, it will be permanently deleted.
            </div>
          </v-alert>

          <!-- Cascade Impact -->
          <div v-if="cascadeImpact" class="mb-4">
            <div class="text-subtitle-2 mb-2">This will delete:</div>

            <v-list density="compact">
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="error">mdi-folder-multiple</v-icon>
                </template>
                <v-list-item-title>
                  <strong>{{ cascadeImpact.unfinished_projects }}</strong> unfinished projects
                </v-list-item-title>
                <v-list-item-subtitle>
                  ({{ cascadeImpact.projects_count }} total projects)
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="error">mdi-checkbox-marked-circle</v-icon>
                </template>
                <v-list-item-title>
                  <strong>{{ cascadeImpact.unresolved_tasks }}</strong> unresolved tasks
                </v-list-item-title>
                <v-list-item-subtitle>
                  ({{ cascadeImpact.tasks_count }} total tasks)
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="error">mdi-file-document-multiple</v-icon>
                </template>
                <v-list-item-title>
                  <strong>{{ cascadeImpact.vision_documents_count }}</strong> vision documents
                </v-list-item-title>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="error">mdi-database</v-icon>
                </template>
                <v-list-item-title>
                  <strong>{{ cascadeImpact.total_chunks }}</strong> context chunks
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </div>

          <!-- Simplified Confirmation -->
          <v-divider class="my-4"></v-divider>

          <v-checkbox v-model="deleteConfirmationCheck" density="compact" hide-details>
            <template #label>
              <span>I understand this product will be recoverable for 10 days</span>
            </template>
          </v-checkbox>
        </div>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="handleCancel" :disabled="deleting"> Cancel </v-btn>
        <v-btn
          color="warning"
          variant="flat"
          @click="handleConfirm"
          :disabled="!deleteConfirmationCheck || deleting"
          :loading="deleting"
        >
          Move to Trash
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  product: {
    type: Object,
    default: () => ({}),
  },
  cascadeImpact: {
    type: Object,
    default: () => ({
      unfinished_projects: 0,
      projects_count: 0,
      unresolved_tasks: 0,
      tasks_count: 0,
      vision_documents_count: 0,
      total_chunks: 0,
    }),
  },
  loading: {
    type: Boolean,
    default: false,
  },
  deleting: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const deleteConfirmationCheck = ref(false)

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const handleConfirm = () => {
  emit('confirm')
}

const handleCancel = () => {
  if (!props.deleting) {
    emit('cancel')
    isOpen.value = false
  }
}

// Reset state when dialog opens or closes
watch(
  () => props.modelValue,
  (newVal) => {
    deleteConfirmationCheck.value = false
  },
)
</script>

<style scoped>
/* Additional styling if needed */
</style>
