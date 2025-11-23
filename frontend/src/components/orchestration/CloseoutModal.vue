<template>
  <v-dialog
    :model-value="show"
    :fullscreen="isMobile"
    :max-width="isMobile ? undefined : '800'"
    persistent
    role="dialog"
    :aria-labelledby="'closeout-modal-title'"
    @keydown.esc="handleClose"
  >
    <v-card>
      <!-- Modal header -->
      <v-card-title id="closeout-modal-title" class="modal-title bg-primary text-white pa-4">
        <div class="d-flex align-center justify-space-between">
          <div class="d-flex align-center">
            <v-icon icon="mdi-check-circle-outline" size="large" class="mr-2" />
            <span class="text-h6">Close Project: {{ projectName }}</span>
          </div>
          <v-btn icon variant="text" color="white" :aria-label="'Close modal'" @click="handleClose">
            <v-icon icon="mdi-close" />
          </v-btn>
        </div>
      </v-card-title>

      <v-divider />

      <!-- Modal content -->
      <v-card-text class="pa-4">
        <!-- Loading state -->
        <div v-if="loading" class="text-center py-8">
          <v-progress-circular indeterminate color="primary" size="64" />
          <div class="text-body-1 mt-4">Loading closeout checklist...</div>
        </div>

        <!-- Error state -->
        <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
          {{ error }}
        </v-alert>

        <!-- Closeout content -->
        <div v-if="!loading && closeoutData">
          <!-- Closeout checklist -->
          <div class="mb-6">
            <h3 class="text-h6 mb-3">Closeout Checklist</h3>
            <v-list>
              <v-list-item
                v-for="(item, index) in closeoutData.checklist"
                :key="index"
                class="checklist-item px-0"
                :class="{ checked: checkedItems.includes(index) }"
              >
                <template #prepend>
                  <v-checkbox
                    :model-value="checkedItems.includes(index)"
                    class="checklist-checkbox"
                    color="primary"
                    hide-details
                    @update:model-value="toggleChecklistItem(index)"
                  />
                </template>
                <v-list-item-title>{{ item }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </div>

          <!-- Closeout prompt -->
          <div class="mb-6">
            <h3 class="text-h6 mb-3">Closeout Commands</h3>
            <v-textarea
              :model-value="closeoutData.closeout_prompt"
              class="closeout-prompt"
              readonly
              variant="outlined"
              rows="10"
              no-resize
              style="font-family: 'Courier New', monospace; font-size: 0.875rem"
            />

            <!-- Copy closeout prompt button -->
            <v-btn
              class="copy-closeout-btn"
              color="primary"
              variant="outlined"
              prepend-icon="mdi-content-copy"
              :aria-label="'Copy closeout prompt to clipboard'"
              @click="handleCopyCloseout"
            >
              Copy Closeout Prompt
            </v-btn>

            <!-- Copy success message -->
            <v-alert
              v-if="copySuccess"
              type="success"
              variant="tonal"
              density="compact"
              class="copy-success-msg mt-2"
            >
              Copied to clipboard!
            </v-alert>
          </div>

          <!-- Confirmation checkbox -->
          <div class="mb-4">
            <v-checkbox
              v-model="confirmed"
              class="confirm-checkbox"
              color="success"
              label="I have executed the closeout commands and verified completion"
              hide-details
            />
          </div>
        </div>
      </v-card-text>

      <v-divider />

      <!-- Modal actions -->
      <v-card-actions class="pa-4">
        <v-btn
          class="cancel-btn"
          variant="text"
          :aria-label="'Cancel closeout'"
          @click="handleClose"
        >
          Cancel
        </v-btn>
        <v-spacer />
        <v-btn
          class="complete-project-btn"
          color="success"
          variant="elevated"
          :disabled="!confirmed"
          :loading="completing"
          :aria-label="'Complete project'"
          @click="handleComplete"
        >
          <v-icon icon="mdi-check-circle" start />
          Complete Project
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useDisplay } from 'vuetify'
import { useClipboard } from '@/composables/useClipboard'
import api from '@/services/api'

const props = defineProps({
  show: {
    type: Boolean,
    required: true,
  },
  projectId: {
    type: String,
    required: true,
  },
  projectName: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['close', 'complete'])

// Vuetify display breakpoints
const { mobile } = useDisplay()
const isMobile = computed(() => mobile.value)

// Composables
const { copy } = useClipboard()

// Reactive state
const loading = ref(false)
const error = ref(null)
const closeoutData = ref(null)
const checkedItems = ref([])
const confirmed = ref(false)
const copySuccess = ref(false)
const completing = ref(false)

// Watch for modal open to load data
watch(
  () => props.show,
  (newValue) => {
    if (newValue) {
      loadCloseoutData()
    } else {
      resetState()
    }
  },
)

// Methods
const loadCloseoutData = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await api.get(`/api/projects/${props.projectId}/closeout`)
    closeoutData.value = {
      project_id: props.projectId,
      project_name: props.projectName,
      checklist: response.data.checklist || [],
      closeout_prompt: response.data.closeout_prompt || '',
    }
  } catch (err) {
    console.error('[CloseoutModal] Failed to load closeout data:', err)
    error.value = err.response?.data?.message || 'Failed to load closeout data'
  } finally {
    loading.value = false
  }
}

const toggleChecklistItem = (index) => {
  const itemIndex = checkedItems.value.indexOf(index)
  if (itemIndex > -1) {
    checkedItems.value.splice(itemIndex, 1)
  } else {
    checkedItems.value.push(index)
  }
}

const handleCopyCloseout = async () => {
  copySuccess.value = false

  try {
    const success = await copy(closeoutData.value.closeout_prompt)

    if (success) {
      copySuccess.value = true
      setTimeout(() => {
        copySuccess.value = false
      }, 3000)
    } else {
      // Try fallback method
      await fallbackCopy(closeoutData.value.closeout_prompt)
      copySuccess.value = true
      setTimeout(() => {
        copySuccess.value = false
      }, 3000)
    }
  } catch (err) {
    console.error('[CloseoutModal] Failed to copy closeout prompt:', err)
  }
}

const fallbackCopy = async (text) => {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.left = '-999999px'
  document.body.appendChild(textarea)
  textarea.select()
  const successful = document.execCommand('copy')
  document.body.removeChild(textarea)

  if (!successful) {
    throw new Error('Fallback copy failed')
  }
}

const handleClose = () => {
  emit('close')
}

const handleComplete = async () => {
  if (!confirmed.value) return

  completing.value = true
  error.value = null

  try {
    await api.post(`/api/projects/${props.projectId}/complete`, {
      confirm_closeout: true,
    })

    emit('complete', props.projectId)
  } catch (err) {
    console.error('[CloseoutModal] Failed to complete project:', err)
    error.value = err.response?.data?.message || 'Failed to complete project'
  } finally {
    completing.value = false
  }
}

const resetState = () => {
  checkedItems.value = []
  confirmed.value = false
  copySuccess.value = false
  error.value = null
}
</script>

<style scoped>
.modal-title {
  position: sticky;
  top: 0;
  z-index: 1;
}

.checklist-item {
  transition: background-color 0.2s ease;
}

.checklist-item.checked {
  opacity: 0.7;
}

.checklist-item:hover {
  background-color: rgba(0, 0, 0, 0.04);
}

.closeout-prompt {
  font-family: 'Courier New', Courier, monospace;
}

/* Focus trap for accessibility */
.v-dialog {
  outline: none;
}

/* Ensure proper spacing */
.v-list-item {
  min-height: 48px;
}

/* Mobile optimizations */
@media (max-width: 600px) {
  .modal-title {
    font-size: 1.125rem;
  }

  .closeout-prompt {
    font-size: 0.75rem;
  }
}
</style>
