<template>
  <v-card class="orchestrator-card full-width-mobile" elevation="3">
    <!-- Purple gradient header -->
    <v-card-title class="orchestrator-header purple-gradient white--text pa-4">
      <div class="d-flex align-center">
        <v-icon icon="mdi-brain" color="white" size="large" class="mr-2" />
        <span class="orchestrator-title text-h6 font-weight-bold">ORCHESTRATOR</span>
      </div>
    </v-card-title>

    <v-divider />

    <!-- Card content -->
    <v-card-text class="pa-4">
      <!-- Status message (fixed) -->
      <div class="orchestrator-status mb-3 text-subtitle-2 text-grey-darken-1">
        Context Management & Project Coordination
      </div>

      <!-- Mission summary (truncated to 150 chars) -->
      <div class="mission-summary text-body-2 mb-4">
        {{ truncatedMission }}
      </div>

      <!-- Message count badge -->
      <v-chip v-if="unreadMessageCount > 0" class="message-badge mb-3" color="error" size="small">
        <v-icon icon="mdi-message" size="small" start />
        {{ unreadMessageCount }} unread
      </v-chip>

      <!-- Copy prompt buttons (dual buttons for different tools) -->
      <div class="button-container" :class="{ 'flex-column': isMobile }">
        <v-btn
          class="copy-prompt-btn mb-2"
          color="primary"
          variant="outlined"
          size="small"
          :block="isMobile"
          :aria-label="'Copy orchestrator prompt for Claude Code'"
          @click="handleCopyPrompt('claude-code')"
        >
          <v-icon icon="mdi-content-copy" size="small" start />
          Copy Prompt (Claude Code)
        </v-btn>

        <v-btn
          class="copy-prompt-btn mb-2"
          :class="{ 'ml-2': !isMobile }"
          color="secondary"
          variant="outlined"
          size="small"
          :block="isMobile"
          :aria-label="'Copy orchestrator prompt for Codex/Gemini'"
          @click="handleCopyPrompt('codex-gemini')"
        >
          <v-icon icon="mdi-content-copy" size="small" start />
          Copy Prompt (Codex/Gemini)
        </v-btn>
      </div>

      <!-- Close project button (only shown when canClose is true) -->
      <v-btn
        v-if="project.can_close"
        class="close-project-btn mt-3"
        color="success"
        variant="elevated"
        size="small"
        block
        :aria-label="'Close project'"
        @click="handleCloseProject"
      >
        <v-icon icon="mdi-check-circle" size="small" start />
        Close Project
      </v-btn>
    </v-card-text>

    <!-- Copy success snackbar -->
    <v-snackbar v-model="showCopySuccess" :timeout="2000" location="top" color="success">
      <div role="status">Copied to clipboard!</div>
    </v-snackbar>

    <!-- Copy error snackbar -->
    <v-snackbar v-model="showCopyError" :timeout="4000" location="top" color="error">
      <div role="alert">{{ copyErrorMessage }}</div>
    </v-snackbar>

    <!-- Close confirmation dialog -->
    <v-dialog v-model="showCloseConfirmation" max-width="500">
      <v-card>
        <v-card-title class="text-h6">Confirm Project Closure</v-card-title>
        <v-card-text>
          Are you sure you want to close this project? This will initiate the closeout workflow.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn text @click="showCloseConfirmation = false"> Cancel </v-btn>
          <v-btn color="success" variant="elevated" @click="confirmCloseProject"> Confirm </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDisplay } from 'vuetify'
import { useClipboard } from '@/composables/useClipboard'
import api from '@/services/api'

const props = defineProps({
  orchestrator: {
    type: Object,
    required: true,
  },
  project: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['copy-prompt', 'close-project'])

// Vuetify display breakpoints
const { mobile } = useDisplay()
const isMobile = computed(() => mobile.value || window.innerWidth < 600)

// Composables
const { copy, copied } = useClipboard()

// Reactive state
const showCopySuccess = ref(false)
const showCopyError = ref(false)
const copyErrorMessage = ref('')
const showCloseConfirmation = ref(false)

// Computed properties
const truncatedMission = computed(() => {
  const mission = props.orchestrator.mission_summary || ''
  if (mission.length <= 150) return mission
  return mission.substring(0, 150) + '...'
})

const unreadMessageCount = computed(() => {
  if (!props.orchestrator.messages) return 0
  return props.orchestrator.messages.filter((msg) => !msg.read).length
})

// Methods
// MIGRATION NOTE (Handover 0119): Updated to use /api/v1/prompts instead of /api/prompts
const handleCopyPrompt = async (tool) => {
  emit('copy-prompt', tool)

  try {
    // Fetch prompt from API
    const response = await api.get(`/api/v1/prompts/orchestrator/${tool}`, {
      params: { project_id: props.project.id },
    })
    const promptText = response.data.prompt || 'Prompt not available'

    // Copy to clipboard
    const success = await copy(promptText)

    if (success) {
      showCopySuccess.value = true
      showCopyError.value = false
      copyErrorMessage.value = ''
    } else {
      throw new Error('Clipboard copy failed')
    }
  } catch (err) {
    console.error('[OrchestratorCard] Failed to copy prompt:', err)

    // Determine error message
    let errorMsg = 'Failed to copy prompt to clipboard'
    if (err.response?.status === 404) {
      errorMsg = 'Project not found or not accessible'
    } else if (err.response?.status === 403) {
      errorMsg = 'Not authorized to access this project'
    } else if (err.response?.data?.detail) {
      errorMsg = err.response.data.detail
    } else if (err.message) {
      errorMsg = err.message
    }

    // Still try textarea fallback method
    try {
      const fallbackText = err.response?.data?.prompt || promptText || 'Error fetching prompt'
      await fallbackCopy(fallbackText)
      showCopySuccess.value = true
      showCopyError.value = false
    } catch (fallbackErr) {
      console.error('[OrchestratorCard] Fallback copy also failed:', fallbackErr)
      // Show error to user
      copyErrorMessage.value = errorMsg
      showCopyError.value = true
      showCopySuccess.value = false
    }
  }
}

const fallbackCopy = async (text) => {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.left = '-999999px'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
}

const handleCloseProject = () => {
  showCloseConfirmation.value = true
}

const confirmCloseProject = () => {
  showCloseConfirmation.value = false
  emit('close-project')
}
</script>

<style scoped>
.orchestrator-card {
  position: relative;
  transition: all 0.3s ease;
}

.orchestrator-card:hover {
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
}

.purple-gradient {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.orchestrator-title {
  letter-spacing: 1px;
}

.orchestrator-status {
  font-style: italic;
}

.mission-summary {
  line-height: 1.6;
  min-height: 3em;
}

.button-container {
  display: flex;
  gap: 8px;
}

.button-container.flex-column {
  flex-direction: column;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .full-width-mobile {
    width: 100%;
  }

  .button-container {
    flex-direction: column;
  }
}

/* Ensure proper spacing */
.copy-prompt-btn {
  flex: 1;
}

@media (min-width: 601px) {
  .copy-prompt-btn {
    flex: 0 1 auto;
    min-width: 200px;
  }
}
</style>
