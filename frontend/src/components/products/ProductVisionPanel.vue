<template>
  <div class="product-vision-panel">
    <!-- Vision Documents Section -->
    <div class="text-subtitle-1 mb-4">
      Vision Documents
      <v-chip v-if="hasPriorityBadge" :color="priorityColor" size="x-small" class="ml-2">
        {{ priorityLabel }}
      </v-chip>
    </div>

    <!-- Upload error alert -->
    <v-alert
      v-if="uploadError"
      type="error"
      variant="tonal"
      density="compact"
      dismissible
      @click:close="$emit('clearError')"
      class="mb-4"
    >
      {{ uploadError }}
    </v-alert>

    <!-- Upload progress indicator -->
    <v-alert v-if="uploading" type="info" variant="tonal" density="compact" class="mb-4">
      <div class="d-flex align-center mb-2">
        <v-progress-circular indeterminate size="20" width="2" class="mr-2" />
        <span>Uploading vision documents...</span>
      </div>
      <v-progress-linear :model-value="uploadProgress" color="primary" height="6" class="mt-2" />
    </v-alert>

    <!-- Summarization indicator for large files -->
    <v-alert v-if="isChunking" type="info" variant="tonal" density="compact" class="mb-4">
      <v-icon start>mdi-text-box-check</v-icon>
      Generating summaries... This may take a moment.
    </v-alert>

    <!-- Existing Documents (Edit Mode Only) -->
    <div v-if="productId && existingDocuments.length > 0" class="mb-4">
      <div class="text-subtitle-2 mb-2">Existing Documents ({{ existingDocuments.length }})</div>

      <v-list density="compact" class="mb-3">
        <v-list-item v-for="doc in existingDocuments" :key="doc.id" class="border rounded mb-2">
          <template v-slot:prepend>
            <v-icon :color="doc.is_summarized ? 'success' : 'warning'">
              {{ doc.is_summarized ? 'mdi-check-circle' : 'mdi-clock-outline' }}
            </v-icon>
          </template>

          <v-list-item-title>{{ doc.filename || doc.document_name }}</v-list-item-title>
          <v-list-item-subtitle>
            {{ doc.is_summarized ? 'Summarized' : 'Processing' }} {{ formatDate(doc.created_at) }}
          </v-list-item-subtitle>

          <template v-slot:append>
            <v-btn
              icon
              size="small"
              variant="text"
              color="error"
              :disabled="disabled"
              @click="$emit('removeExisting', doc)"
            >
              <v-icon size="20">mdi-delete</v-icon>
            </v-btn>
          </template>
        </v-list-item>
      </v-list>
    </div>

    <!-- File Upload Component -->
    <div class="text-caption text-medium-emphasis mb-3">
      Upload product requirements, proposals, specifications (.md, .txt files)
    </div>

    <v-file-input
      v-model="localFiles"
      accept=".txt,.md,.markdown"
      label="Choose files"
      variant="outlined"
      density="comfortable"
      multiple
      show-size
      clearable
      prepend-icon="mdi-folder-open"
      hint="Select multiple files (Ctrl/Cmd + Click)"
      persistent-hint
      class="mb-3"
      :disabled="disabled"
      @update:modelValue="handleFilesUpdate"
    ></v-file-input>

    <!-- File List -->
    <div v-if="visionFiles && visionFiles.length > 0">
      <div class="text-subtitle-2 mb-2">Files to Upload ({{ visionFiles.length }})</div>

      <v-list density="compact" class="mb-3">
        <v-list-item v-for="(file, index) in visionFiles" :key="index" class="border rounded mb-2">
          <template v-slot:prepend>
            <v-icon color="primary">mdi-file-document</v-icon>
          </template>

          <v-list-item-title>{{ file.name }}</v-list-item-title>
          <v-list-item-subtitle>
            {{ formatFileSize(file.size) }}
          </v-list-item-subtitle>

          <template v-slot:append>
            <v-btn
              icon
              size="small"
              variant="text"
              :disabled="disabled"
              @click="handleRemoveFile(index)"
            >
              <v-icon size="20">mdi-close</v-icon>
            </v-btn>
          </template>
        </v-list-item>
      </v-list>

      <v-alert type="info" variant="tonal" density="compact">
        Large files will be auto-summarized (light 33%, medium 66%)
      </v-alert>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useFieldPriority } from '@/composables/useFieldPriority'

const props = defineProps({
  visionFiles: {
    type: Array,
    default: () => [],
  },
  existingDocuments: {
    type: Array,
    default: () => [],
  },
  productId: {
    type: String,
    default: null,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  uploadError: {
    type: String,
    default: null,
  },
  uploading: {
    type: Boolean,
    default: false,
  },
  uploadProgress: {
    type: Number,
    default: 0,
  },
  isChunking: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:files', 'upload', 'remove', 'removeExisting', 'clearError'])

// Field priority composable
const {
  getPriorityForField,
  getPriorityLabel: getFieldPriorityLabel,
  getPriorityColor: getFieldPriorityColor,
} = useFieldPriority()

// Local state for v-file-input binding
const localFiles = ref([])

// Sync localFiles with visionFiles prop
watch(
  () => props.visionFiles,
  (newFiles) => {
    localFiles.value = newFiles || []
  },
  { immediate: true },
)

// Priority badge computed properties
const fieldPriority = computed(() => getPriorityForField('vision_documents'))
const hasPriorityBadge = computed(() => fieldPriority.value !== null)
const priorityColor = computed(() => getFieldPriorityColor(fieldPriority.value))
const priorityLabel = computed(() => getFieldPriorityLabel(fieldPriority.value))

/**
 * Handle file input update
 * @param {Array} files - Selected files
 */
function handleFilesUpdate(files) {
  emit('update:files', files || [])
}

/**
 * Handle remove file button click
 * @param {number} index - File index to remove
 */
function handleRemoveFile(index) {
  emit('remove', index)
}

/**
 * Format file size for display
 * @param {number} bytes - File size in bytes
 * @returns {string} - Formatted file size
 */
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

/**
 * Format date for display
 * @param {string} dateString - ISO date string
 * @returns {string} - Formatted date
 */
function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

/**
 * Validate file type
 * @param {File} file - File to validate
 * @returns {boolean} - True if valid
 */
function validateFileType(file) {
  const validExtensions = ['.md', '.txt', '.markdown']
  const fileName = file.name.toLowerCase()
  return validExtensions.some((ext) => fileName.endsWith(ext))
}

// Expose helper functions for testing
defineExpose({
  formatFileSize,
  formatDate,
  validateFileType,
})
</script>

<style scoped>
.product-vision-panel {
  width: 100%;
}
</style>
