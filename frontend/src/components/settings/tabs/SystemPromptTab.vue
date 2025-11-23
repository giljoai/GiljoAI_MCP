<template>
  <v-card>
    <v-card-title>System Orchestrator Prompt</v-card-title>
    <v-card-subtitle
      >Core instructions for the Giljo Orchestrator (admin override only)</v-card-subtitle
    >

    <v-card-text>
      <v-alert type="warning" variant="tonal" class="mb-4">
        <v-icon start>mdi-alert</v-icon>
        Editing this prompt can break orchestrator coordination. Only proceed if you understand the
        full impact. Always keep a backup and verify flows after saving.
      </v-alert>

      <v-alert
        v-if="promptError"
        type="error"
        variant="tonal"
        class="mb-4"
        closable
        data-test="error-alert"
        @click:close="promptError = null"
      >
        {{ promptError }}
      </v-alert>

      <v-alert
        v-if="promptFeedback"
        type="success"
        variant="tonal"
        class="mb-4"
        closable
        data-test="success-alert"
        @click:close="promptFeedback = null"
      >
        {{ promptFeedback }}
      </v-alert>

      <v-textarea
        v-model="prompt"
        :loading="loading"
        :readonly="loading"
        label="Orchestrator Prompt"
        class="mono-textarea"
        rows="18"
        auto-grow
        variant="outlined"
        spellcheck="false"
      />

      <div class="text-caption mt-2">
        {{ promptStatus }}
      </div>
    </v-card-text>

    <v-card-actions>
      <v-btn
        variant="text"
        color="warning"
        :disabled="loading || saving"
        data-test="restore-prompt-btn"
        @click="restorePrompt"
      >
        <v-icon start>mdi-backup-restore</v-icon>
        Restore Default
      </v-btn>
      <v-spacer />
      <v-btn
        color="primary"
        :loading="saving"
        :disabled="!promptDirty || saving"
        data-test="save-prompt-btn"
        @click="savePrompt"
      >
        <v-icon start>mdi-content-save</v-icon>
        Save Override
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import api from '@/services/api'

// State
const prompt = ref('')
const promptBaseline = ref('')
const loading = ref(false)
const saving = ref(false)
const promptDirty = ref(false)
const promptMetadata = ref({
  isOverride: false,
  updatedAt: null,
  updatedBy: null,
})
const promptError = ref(null)
const promptFeedback = ref(null)

// Computed
const promptStatus = computed(() => {
  if (promptMetadata.value.isOverride && promptMetadata.value.updatedAt) {
    const timestamp = promptMetadata.value.updatedAt.toLocaleString()
    const actor = promptMetadata.value.updatedBy || 'admin'
    return `Override saved ${timestamp} by ${actor}`
  }
  return 'Using default system prompt'
})

// Methods
async function loadPrompt() {
  loading.value = true
  promptError.value = null
  promptFeedback.value = null

  try {
    const response = await api.system.getOrchestratorPrompt()
    const data = response.data || {}
    prompt.value = data.content || ''
    promptBaseline.value = prompt.value
    promptMetadata.value = {
      isOverride: Boolean(data.is_override),
      updatedAt: data.updated_at ? new Date(data.updated_at) : null,
      updatedBy: data.updated_by || null,
    }
    promptDirty.value = false
  } catch (error) {
    console.error('[SYSTEM] Failed to load orchestrator prompt:', error)
    promptError.value = error.response?.data?.detail || 'Failed to load orchestrator prompt.'
  } finally {
    loading.value = false
  }
}

async function savePrompt() {
  if (!promptDirty.value) return
  saving.value = true
  promptError.value = null
  promptFeedback.value = null

  try {
    const response = await api.system.updateOrchestratorPrompt(prompt.value)
    const data = response.data || {}
    prompt.value = data.content || prompt.value
    promptBaseline.value = prompt.value
    promptMetadata.value = {
      isOverride: Boolean(data.is_override),
      updatedAt: data.updated_at ? new Date(data.updated_at) : null,
      updatedBy: data.updated_by || null,
    }
    promptDirty.value = false
    promptFeedback.value = 'Override saved successfully.'
  } catch (error) {
    console.error('[SYSTEM] Failed to save orchestrator prompt:', error)
    promptError.value = error.response?.data?.detail || 'Failed to save orchestrator prompt.'
  } finally {
    saving.value = false
  }
}

async function restorePrompt() {
  saving.value = true
  promptError.value = null
  promptFeedback.value = null

  try {
    const response = await api.system.resetOrchestratorPrompt()
    const data = response.data || {}
    prompt.value = data.content || ''
    promptBaseline.value = prompt.value
    promptMetadata.value = {
      isOverride: Boolean(data.is_override),
      updatedAt: data.updated_at ? new Date(data.updated_at) : null,
      updatedBy: data.updated_by || null,
    }
    promptDirty.value = false
    promptFeedback.value = 'Reverted to default orchestrator prompt.'
  } catch (error) {
    console.error('[SYSTEM] Failed to reset orchestrator prompt:', error)
    promptError.value = error.response?.data?.detail || 'Failed to restore default prompt.'
  } finally {
    saving.value = false
  }
}

// Watch for changes
watch(prompt, (value) => {
  promptDirty.value = value !== promptBaseline.value
})

// Lifecycle
onMounted(() => {
  loadPrompt()
})
</script>

<style scoped>
.mono-textarea :deep(textarea) {
  font-family: 'Roboto Mono', monospace;
}
</style>
