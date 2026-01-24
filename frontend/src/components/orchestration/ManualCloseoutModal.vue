<template>
  <v-dialog
    :model-value="show"
    :fullscreen="isMobile"
    :max-width="isMobile ? undefined : '600'"
    persistent
    class="manual-closeout-modal"
    role="dialog"
    aria-labelledby="manual-closeout-title"
    data-testid="manual-closeout-modal"
    @keydown.esc="handleClose"
  >
    <v-card>
      <!-- Modal header -->
      <v-card-title id="manual-closeout-title" class="bg-primary text-white pa-4">
        <div class="d-flex align-center justify-space-between">
          <div class="d-flex align-center">
            <v-icon icon="mdi-check-circle-outline" size="large" class="mr-2" />
            <span class="text-h6">Complete Project: {{ projectName }}</span>
          </div>
          <v-btn icon variant="text" color="white" aria-label="Close modal" @click="handleClose">
            <v-icon icon="mdi-close" />
          </v-btn>
        </div>
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-4">
        <!-- 360 Memory Info Banner -->
        <v-alert
          type="info"
          variant="tonal"
          density="compact"
          class="mb-4"
          icon="mdi-information"
        >
          <template #title>
            <span class="text-body-2 font-weight-medium">Why detailed closeout matters</span>
          </template>
          <span class="text-body-2">
            This closeout data becomes part of your product's <strong>360 Memory</strong> and provides
            context for future projects. The more detailed your summary, the better future orchestrators
            can learn from this work.
          </span>
        </v-alert>

        <!-- Error state -->
        <v-alert v-if="error" type="error" variant="tonal" class="mb-4" closable @click:close="error = null">
          {{ error }}
        </v-alert>

        <!-- 360 Memory Summary Field -->
        <div class="mb-4">
          <v-textarea
            v-model="summary"
            label="Project Summary (360 Memory)"
            placeholder="Describe what was accomplished in this project, key outcomes, decisions made, and any learnings for future projects..."
            variant="outlined"
            rows="6"
            counter
            :rules="[v => v.length >= 50 || 'Please provide at least 50 characters']"
            hint="This summary will be stored in 360 Memory for future project context"
            persistent-hint
          />
        </div>

        <!-- Manual confirmation checkbox -->
        <div class="mt-4">
          <v-checkbox
            v-model="confirmed"
            color="primary"
            hide-details
            data-testid="manual-confirm-checkbox"
          >
            <template #label>
              <span class="text-body-2">I am manually completing this project</span>
            </template>
          </v-checkbox>
        </div>
      </v-card-text>

      <v-divider />

      <!-- Modal actions -->
      <v-card-actions class="pa-4">
        <v-btn variant="text" @click="handleClose">
          Cancel
        </v-btn>
        <v-spacer />
        <v-btn
          color="success"
          variant="elevated"
          :disabled="!canSubmit"
          :loading="completing"
          data-testid="manual-complete-btn"
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
import { ref, computed } from 'vue'
import { useDisplay } from 'vuetify'
import api from '@/services/api'

const props = defineProps({
  show: {
    type: Boolean,
    required: true,
  },
  projectId: {
    type: [String, null],
    default: null,
  },
  projectName: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['close', 'completed'])

// Vuetify display breakpoints
const { mobile } = useDisplay()
const isMobile = computed(() => mobile.value)

// Reactive state
const summary = ref('')
const confirmed = ref(false)
const completing = ref(false)
const error = ref(null)

// Computed
const canSubmit = computed(() => {
  return confirmed.value && summary.value.length >= 50
})

// Methods
const handleClose = () => {
  resetState()
  emit('close')
}

const handleComplete = async () => {
  if (!canSubmit.value) return

  completing.value = true
  error.value = null

  try {
    const payload = {
      summary: summary.value,
      key_outcomes: ['Manually completed by user'],
      decisions_made: [],
      confirm_closeout: true,
    }

    const response = await api.projects.completeWithData(props.projectId, payload)

    emit('completed', response.data || { project_id: props.projectId })
    resetState()
  } catch (err) {
    console.error('[ManualCloseoutModal] Failed to complete project:', err)
    error.value = err.response?.data?.detail || err.response?.data?.message || 'Failed to complete project'
  } finally {
    completing.value = false
  }
}

const resetState = () => {
  summary.value = ''
  confirmed.value = false
  error.value = null
}
</script>

<style scoped>
.manual-closeout-modal .v-card-title {
  position: sticky;
  top: 0;
  z-index: 1;
}
</style>
