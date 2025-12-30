<template>
  <BaseDialog
    v-model="isOpen"
    type="warning"
    title="Move Product to Trash?"
    icon="mdi-delete"
    confirm-label="Move to Trash"
    confirm-checkbox
    confirm-checkbox-label="I understand this product will be recoverable for 10 days"
    :loading="deleting"
    @confirm="handleConfirm"
    @cancel="handleCancel"
  >
    <!-- Loading State -->
    <div v-if="loading" class="text-center py-4">
      <v-progress-circular indeterminate color="warning"></v-progress-circular>
      <div class="text-caption mt-2">Calculating impact...</div>
    </div>

    <!-- Warning Content -->
    <template v-else>
      <v-alert type="info" variant="tonal" density="compact" class="mb-4">
        <div class="text-subtitle-1 font-weight-bold mb-2">Move to Trash?</div>
        <div>
          <strong>{{ product?.name }}</strong> will be moved to trash and can be recovered for 10
          days. After 10 days, it will be permanently deleted.
        </div>
      </v-alert>

      <!-- Cascade Impact -->
      <div v-if="cascadeImpact" class="mb-4">
        <div class="text-subtitle-2 mb-2">This will delete:</div>

        <v-list density="compact">
          <v-list-item>
            <template v-slot:prepend>
              <v-icon color="warning">mdi-folder-multiple</v-icon>
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
              <v-icon color="warning">mdi-checkbox-marked-circle</v-icon>
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
              <v-icon color="warning">mdi-file-document-multiple</v-icon>
            </template>
            <v-list-item-title>
              <strong>{{ cascadeImpact.vision_documents_count }}</strong> vision documents
            </v-list-item-title>
          </v-list-item>

          <v-list-item>
            <template v-slot:prepend>
              <v-icon color="warning">mdi-database</v-icon>
            </template>
            <v-list-item-title>
              <strong>{{ cascadeImpact.total_chunks }}</strong> context chunks
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </div>
    </template>
  </BaseDialog>
</template>

<script setup>
import { computed, watch } from 'vue'
import BaseDialog from '@/components/common/BaseDialog.vue'

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
</script>
