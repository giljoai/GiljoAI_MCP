<template>
  <div class="action-icons d-flex align-center ga-1">
    <!-- Launch Action (pulsing during handover pending) -->
    <v-tooltip v-if="availableActions.includes('launch')" location="top">
      <template #activator="{ props }">
        <v-btn
          v-bind="props"
          icon="mdi-rocket-launch"
          :color="handoverPending ? 'success' : getActionColor('launch')"
          size="small"
          variant="text"
          :class="{ 'handover-pending-pulse': handoverPending }"
          :loading="loadingStates.launch"
          :disabled="loadingStates.launch"
          data-test="action-launch"
          @click="handleLaunch"
        />
      </template>
      <span>{{ handoverPending ? 'Copy continuation prompt for new terminal' : getActionTooltip('launch') }}</span>
    </v-tooltip>

    <!-- Copy Prompt Action -->
    <v-tooltip v-if="availableActions.includes('copyPrompt')" location="top">
      <template #activator="{ props }">
        <v-btn
          v-bind="props"
          icon="mdi-content-copy"
          :color="getActionColor('copyPrompt')"
          size="small"
          variant="text"
          :loading="loadingStates.copyPrompt"
          :disabled="loadingStates.copyPrompt"
          data-test="action-copyPrompt"
          @click="handleCopyPrompt"
        />
      </template>
      <span>{{ getActionTooltip('copyPrompt') }}</span>
    </v-tooltip>

    <!-- View Messages Action with Badge -->
    <v-tooltip v-if="availableActions.includes('viewMessages')" location="top">
      <template #activator="{ props }">
        <v-badge
          v-if="job.unread_count > 0"
          :content="job.unread_count"
          color="error"
          data-test="messages-badge"
        >
          <v-btn
            v-bind="props"
            icon="mdi-message-text"
            :color="getActionColor('viewMessages')"
            size="small"
            variant="text"
            data-test="action-viewMessages"
            @click="handleViewMessages"
          />
        </v-badge>
        <v-btn
          v-else
          v-bind="props"
          icon="mdi-message-text"
          :color="getActionColor('viewMessages')"
          size="small"
          variant="text"
          data-test="action-viewMessages"
          @click="handleViewMessages"
        />
      </template>
      <span>{{ getActionTooltip('viewMessages') }}</span>
    </v-tooltip>

    <!-- Hand Over Action (Two-Stage: retirement + continuation) -->
    <v-tooltip v-if="availableActions.includes('handOver')" location="top">
      <template #activator="{ props }">
        <v-btn
          v-bind="props"
          :icon="handoverPending ? 'mdi-check-circle' : 'mdi-refresh'"
          :color="handoverPending ? 'success' : getActionColor('handOver')"
          size="small"
          variant="text"
          :loading="loadingStates.handOver"
          :disabled="loadingStates.handOver || handoverPending"
          data-test="action-handOver"
          @click="handleHandOver"
        />
      </template>
      <span>{{ handoverPending ? 'Retirement prompt copied - paste in old terminal' : getActionTooltip('handOver') }}</span>
    </v-tooltip>

    <!-- Copy Success Snackbar -->
    <v-snackbar v-model="showCopySuccess" color="success" timeout="2000">
      Prompt copied to clipboard!
    </v-snackbar>

    <!-- Handover Instructions Snackbar (persistent until play is clicked) -->
    <v-snackbar
      v-model="showHandoverSnackbar"
      color="info"
      :timeout="-1"
      location="bottom"
      data-test="handover-snackbar"
    >
      <div>
        <strong>Step 1:</strong> Paste the retirement prompt in the OLD terminal.
        <br>
        <strong>Step 2:</strong> Click the pulsing launch button to copy the continuation prompt for a NEW terminal.
      </div>
      <template #actions>
        <v-btn variant="text" size="small" @click="dismissHandover">
          Dismiss
        </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { getAvailableActions, getActionConfig } from '@/utils/actionConfig'
import api from '@/services/api'
import { useClipboard } from '@/composables/useClipboard'

export default {
  name: 'ActionIcons',

  props: {
    job: {
      type: Object,
      required: true,
      default: () => ({
        job_id: '',
        status: 'waiting',
        agent_display_name: 'implementer',
        unread_count: 0,
      }),
    },
    claudeCodeCliMode: {
      type: Boolean,
      default: false,
    },
  },

  emits: ['launch', 'copy-prompt', 'view-messages', 'hand-over'],

  setup(props, { emit }) {
    const { copy: clipboardCopy } = useClipboard()

    const loadingStates = ref({
      launch: false,
      copyPrompt: false,
      handOver: false,
    })

    const showCopySuccess = ref(false)

    // Two-stage handover state
    const handoverPending = ref(false)
    const storedContinuationPrompt = ref('')
    const showHandoverSnackbar = ref(false)

    const availableActions = computed(() => {
      return getAvailableActions(props.job, props.claudeCodeCliMode)
    })

    const getActionColor = (action) => {
      const config = getActionConfig(action)
      return config?.color || 'grey'
    }

    const getActionTooltip = (action) => {
      const config = getActionConfig(action)
      return config?.tooltip || ''
    }

    const handleLaunch = async () => {
      // Two-stage handover: if pending, copy continuation prompt instead of normal launch
      if (handoverPending.value && storedContinuationPrompt.value) {
        loadingStates.value.launch = true
        try {
          await clipboardCopy(storedContinuationPrompt.value)
          showCopySuccess.value = true

          // Reset handover state
          handoverPending.value = false
          storedContinuationPrompt.value = ''
          showHandoverSnackbar.value = false

          emit('hand-over', {
            type: 'handOver',
            job: props.job,
            success: true,
            stage: 'continuation',
            message: 'Continuation prompt copied! Paste in a new terminal.',
          })
        } finally {
          loadingStates.value.launch = false
        }
        return
      }

      loadingStates.value.launch = true
      try {
        emit('launch', props.job)
      } finally {
        loadingStates.value.launch = false
      }
    }

    const handleCopyPrompt = async () => {
      loadingStates.value.copyPrompt = true
      try {
        emit('copy-prompt', props.job)
        showCopySuccess.value = true
      } finally {
        loadingStates.value.copyPrompt = false
      }
    }

    const handleViewMessages = () => {
      emit('view-messages', props.job)
    }

    const handleHandOver = async () => {
      try {
        loadingStates.value.handOver = true

        // Call simple-handover endpoint - returns both retirement + continuation prompts
        const response = await api.agentJobs.simpleHandover(props.job.job_id)

        if (response.data.success) {
          // Stage 1: Copy RETIREMENT prompt to clipboard (for old terminal)
          await clipboardCopy(response.data.retirement_prompt)

          // Store continuation prompt for Stage 2 (play button click)
          storedContinuationPrompt.value = response.data.continuation_prompt
          handoverPending.value = true
          showHandoverSnackbar.value = true

          // Emit stage 1 event
          emit('hand-over', {
            type: 'handOver',
            job: props.job,
            success: true,
            stage: 'retirement',
            message: 'Retirement prompt copied! Paste in old terminal, then click the pulsing launch button.',
          })
        } else {
          throw new Error(response.data.error || 'Session refresh failed')
        }
      } catch (error) {
        // Emit action event with failure info
        emit('hand-over', {
          type: 'handOver',
          job: props.job,
          success: false,
          error: error.message,
        })
      } finally {
        loadingStates.value.handOver = false
      }
    }

    const dismissHandover = () => {
      // Allow dismissing the snackbar without resetting state
      // The pulsing button remains as visual cue
      showHandoverSnackbar.value = false
    }

    return {
      availableActions,
      loadingStates,
      showCopySuccess,
      handoverPending,
      showHandoverSnackbar,
      getActionColor,
      getActionTooltip,
      handleLaunch,
      handleCopyPrompt,
      handleViewMessages,
      handleHandOver,
      dismissHandover,
    }
  },
}
</script>

<style scoped>
/* ============================================================
   PHASE 4: VISUAL POLISH & HOVER STATES
   Enhanced styling with smooth animations and transitions
   ============================================================ */

.action-icons {
  min-width: 120px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ============================================================
   4.1 HOVER STATES - Enhanced visual feedback
   ============================================================ */

.action-icons .v-btn {
  opacity: 0.75;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Hover effect - opacity and scale increase */
.action-icons .v-btn:hover:not(:disabled) {
  opacity: 1;
  transform: scale(1.1);
  filter: brightness(1.15);
}

/* Active/click effect - scale down */
.action-icons .v-btn:active:not(:disabled) {
  transform: scale(0.95);
}

/* ============================================================
   4.2 DISABLED STATE - Visual indication
   ============================================================ */

/* Disabled state styling */
.action-icons .v-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Remove hover effects from disabled buttons */
.action-icons .v-btn:disabled:hover {
  transform: none;
  filter: none;
  opacity: 0.4;
}

/* ============================================================
   4.3 LOADING STATE - Prevent interaction
   ============================================================ */

/* Loading state - prevent pointer events */
.action-icons .v-btn--loading {
  pointer-events: none;
  opacity: 0.85;
}

/* ============================================================
   4.4 FOCUS & ACCESSIBILITY
   ============================================================ */

/* Ensure buttons remain accessible */
.action-icons .v-btn:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

/* ============================================================
   4.5 BADGE STYLING
   ============================================================ */

.action-icons .v-badge {
  margin: 0;
  transition: all 0.2s ease;
}

.action-icons .v-badge:hover .v-btn {
  opacity: 1;
  transform: scale(1.1);
}

/* ============================================================
   4.6 ANIMATIONS - CSS keyframe animations
   ============================================================ */

/* Handover pending - pulsing ring around launch button */
@keyframes pulse-ring {
  0% {
    box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.5);
  }
  70% {
    box-shadow: 0 0 0 8px rgba(76, 175, 80, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(76, 175, 80, 0);
  }
}

.handover-pending-pulse {
  animation: pulse-ring 1.5s ease infinite;
  border-radius: 50%;
}

/* Copy success animation - checkmark appears with scale */
@keyframes checkmark-pop {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  50% {
    transform: scale(1.2);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

.copy-success-icon {
  animation: checkmark-pop 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

/* Snackbar slide-in animation */
.v-snackbar {
  animation: snackbar-slide 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

@keyframes snackbar-slide {
  from {
    transform: translateY(100px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

/* ============================================================
   4.7 RESPONSIVE BEHAVIOR
   ============================================================ */

/* Ensure proper spacing on smaller screens */
@media (max-width: 600px) {
  .action-icons {
    gap: 4px;
  }

  .action-icons .v-btn {
    /* Slightly reduced size on mobile */
    font-size: 0.9rem;
  }
}

/* Larger screens - more spacing */
@media (min-width: 1200px) {
  .action-icons {
    gap: 12px;
  }
}

/* ============================================================
   4.8 TOOLTIP STYLING
   ============================================================ */

/* Ensure tooltips are properly positioned */
.action-icons :deep(.v-tooltip__content) {
  font-size: 0.875rem;
  background-color: rgba(0, 0, 0, 0.87);
  color: white;
  padding: 8px 12px;
  border-radius: 4px;
  max-width: 200px;
}
</style>
