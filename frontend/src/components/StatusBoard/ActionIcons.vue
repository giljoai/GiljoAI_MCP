<template>
  <div class="action-icons d-flex align-center ga-1">
    <!-- Launch Action -->
    <v-tooltip v-if="availableActions.includes('launch')" location="top">
      <template #activator="{ props }">
        <v-btn
          v-bind="props"
          icon="mdi-rocket-launch"
          :color="getActionColor('launch')"
          size="small"
          variant="text"
          :loading="loadingStates.launch"
          :disabled="loadingStates.launch"
          data-test="action-launch"
          @click="handleLaunch"
        />
      </template>
      <span>{{ getActionTooltip('launch') }}</span>
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

    <!-- Hand Over Action (Handover 0506) -->
    <v-tooltip v-if="availableActions.includes('handOver')" location="top">
      <template #activator="{ props }">
        <v-btn
          v-bind="props"
          icon="mdi-hand-wave"
          :color="getActionColor('handOver')"
          size="small"
          variant="text"
          :loading="loadingStates.handOver"
          :disabled="loadingStates.handOver"
          data-test="action-handOver"
          @click="handleHandOver"
        />
      </template>
      <span>{{ getActionTooltip('handOver') }}</span>
    </v-tooltip>

    <!-- Confirmation Dialog -->
    <v-dialog v-model="showConfirmDialog" max-width="500" data-test="confirm-dialog">
      <v-card>
        <v-card-title class="text-h5">
          {{ confirmationConfig.title }}
        </v-card-title>
        <v-card-text>
          {{ confirmationConfig.message }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            color="grey"
            variant="text"
            data-test="confirm-dialog-cancel"
            @click="cancelConfirmation"
          >
            Cancel
          </v-btn>
          <v-btn
            :color="confirmationConfig.color || 'error'"
            variant="text"
            data-test="confirm-dialog-confirm"
            @click="executeConfirmedAction"
            :loading="confirmationLoading"
          >
            {{ confirmationConfig.confirmText }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Copy Success Snackbar -->
    <v-snackbar v-model="showCopySuccess" color="success" timeout="2000">
      Prompt copied to clipboard!
    </v-snackbar>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { getAvailableActions, getActionConfig } from '@/utils/actionConfig'
import api from '@/services/api'

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
        context_used: 0,
        context_budget: 0,
      }),
    },
    claudeCodeCliMode: {
      type: Boolean,
      default: false,
    },
  },

  emits: ['launch', 'copy-prompt', 'view-messages', 'hand-over'],

  setup(props, { emit }) {
    const loadingStates = ref({
      launch: false,
      copyPrompt: false,
      handOver: false,
    })

    const showConfirmDialog = ref(false)
    const confirmationConfig = ref({})
    const confirmationLoading = ref(false)
    const pendingAction = ref(null)
    const showCopySuccess = ref(false)

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

        // Call simple-handover endpoint (Handover 0461d)
        const response = await api.post(`/agent-jobs/${props.job.job_id}/simple-handover`)

        if (response.data.success) {
          // Copy continuation prompt to clipboard
          await navigator.clipboard.writeText(response.data.continuation_prompt)

          // Emit action event with success info
          emit('hand-over', {
            type: 'handOver',
            job: props.job,
            success: true,
            message: 'Session refreshed! Continuation prompt copied to clipboard.',
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

    const showConfirmation = (action, config) => {
      confirmationConfig.value = {
        title: config.confirmationTitle,
        message: config.confirmationMessage,
        color: config.color,
        confirmText: config.label,
      }
      pendingAction.value = action
      showConfirmDialog.value = true
    }

    const cancelConfirmation = () => {
      showConfirmDialog.value = false
      pendingAction.value = null
      confirmationLoading.value = false
    }

    const executeConfirmedAction = async () => {
      confirmationLoading.value = true
      try {
        if (pendingAction.value === 'handOver') {
          await handleHandOver()
        }
      } finally {
        confirmationLoading.value = false
        showConfirmDialog.value = false
        pendingAction.value = null
      }
    }

    return {
      availableActions,
      loadingStates,
      showConfirmDialog,
      confirmationConfig,
      confirmationLoading,
      showCopySuccess,
      getActionColor,
      getActionTooltip,
      handleLaunch,
      handleCopyPrompt,
      handleViewMessages,
      handleHandOver,
      cancelConfirmation,
      executeConfirmedAction,
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

/* Confirmation dialog slide-in animation */
.v-dialog {
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
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
