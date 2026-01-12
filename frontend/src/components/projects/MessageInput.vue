<template>
  <div
    class="message-input"
    :class="[`position-${position}`, { 'message-input--disabled': disabled }]"
  >
    <div class="message-input__container">
      <!-- User icon -->
      <div class="message-input__user-icon" aria-hidden="true">
        <v-icon icon="mdi-account-circle" size="32" color="primary" />
      </div>

      <!-- Text area -->
      <v-textarea
        ref="textareaRef"
        v-model="messageText"
        class="message-input__textarea"
        data-testid="message-input"
        placeholder="Type your message... (Shift+Enter for new line, Enter to send)"
        rows="1"
        auto-grow
        :max-rows="8"
        variant="outlined"
        density="comfortable"
        hide-details
        :disabled="disabled"
        @keydown="handleKeydown"
        aria-label="Message input"
      />

      <!-- "To" dropdown -->
      <v-select
        v-model="recipient"
        class="message-input__recipient"
        data-testid="recipient-select"
        :items="recipientOptions"
        item-title="label"
        item-value="value"
        variant="outlined"
        density="comfortable"
        hide-details
        :disabled="disabled"
        label="To"
        aria-label="Select message recipient"
      />

      <!-- Submit button -->
      <v-btn
        class="message-input__submit"
        icon
        color="primary"
        size="large"
        :disabled="!canSend"
        @click="handleSubmit"
        :aria-label="`Send message to ${getRecipientLabel(recipient)}`"
        :title="`Send message to ${getRecipientLabel(recipient)}`"
      >
        <v-icon icon="mdi-chevron-left" size="28" />
      </v-btn>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'

/**
 * MessageInput Component
 *
 * Sticky message input at bottom of message stream for sending messages to agents.
 *
 * Features:
 * - Layout: User icon → Text area → "To" dropdown → Submit button (<)
 * - Auto-expanding text area (1-8 rows)
 * - Submit on Enter (Shift+Enter for newline)
 * - Recipient dropdown: "Orchestrator" (default), "Broadcast"
 * - Disabled state support
 * - Keyboard accessible
 * - Touch-friendly on mobile
 *
 * @see handovers/0077_launch_jobs_dual_tab_interface.md
 */

const props = defineProps({
  /**
   * Job ID for message sending
   */
  jobId: {
    type: String,
    required: true,
  },
  /**
   * Position mode: inline (default), modal (in dialog), sticky (bottom)
   */
  position: {
    type: String,
    default: 'inline',
    validator: (value) => ['inline', 'modal', 'sticky'].includes(value),
  },
  /**
   * Disable input and submission
   */
  disabled: {
    type: Boolean,
    default: false,
  },
  /**
   * Array of active agents
   * Each agent: { agent_id, agent_display_name, instance_number }
   */
  agents: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['send', 'message-sent'])

/**
 * Message text state
 */
const messageText = ref('')

/**
 * Recipient selection state (defaults to 'broadcast')
 */
const recipient = ref('broadcast')

/**
 * Recipient dropdown options (computed dynamically from agents prop)
 */
const recipientOptions = computed(() => {
  const options = [{ label: 'Broadcast', value: 'broadcast' }]

  props.agents.forEach((agent) => {
    const instanceNum = agent.instance_number || 1
    const displayName = agent.agent_display_name || 'Unknown'
    const truncatedId = agent.agent_id ? agent.agent_id.slice(0, 8) + '...' : 'unknown'
    const label = `${displayName} (Instance ${instanceNum}) - ${truncatedId}`
    options.push({ label, value: agent.agent_id })
  })

  return options
})

/**
 * Textarea ref for focus management
 */
const textareaRef = ref(null)

/**
 * Check if message can be sent
 */
const canSend = computed(() => {
  return !props.disabled && messageText.value.trim().length > 0
})

/**
 * Get recipient label for display
 */
function getRecipientLabel(value) {
  const option = recipientOptions.value.find((opt) => opt.value === value)
  return option?.label || 'Unknown'
}

/**
 * Handle keyboard events in textarea
 */
function handleKeydown(event) {
  // Submit on Enter (without Shift)
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSubmit()
  }
  // Allow Shift+Enter for newline (default textarea behavior)
}

/**
 * Handle message submission
 */
function handleSubmit() {
  if (!canSend.value) return

  const trimmedMessage = messageText.value.trim()
  if (trimmedMessage.length === 0) return

  // Determine if recipient is an agent_id (UUID format) or keyword (broadcast)
  const isAgentId = recipient.value !== 'broadcast' && recipient.value.length > 10

  // Emit send event with message and recipient (backward compatible)
  emit('send', trimmedMessage, recipient.value)

  // Also emit message-sent for modal usage with to_agent_id field
  emit('message-sent', {
    content: trimmedMessage,
    to_agent_id: isAgentId ? recipient.value : null,
    recipient: recipient.value,
    jobId: props.jobId,
  })

  // Clear input after sending
  messageText.value = ''

  // Focus textarea for next message
  nextTick(() => {
    textareaRef.value?.focus()
  })
}
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.message-input {
  position: sticky;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--color-bg-primary);
  border-top: 2px solid var(--color-border);
  padding: 16px;
  z-index: 10;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);

  &--disabled {
    opacity: 0.6;
    pointer-events: none;
  }

  &__container {
    display: flex;
    align-items: flex-end;
    gap: 12px;
    max-width: 1400px;
    margin: 0 auto;
  }

  &__user-icon {
    flex-shrink: 0;
    padding-bottom: 8px;
  }

  &__textarea {
    flex: 1;
    min-width: 200px;

    :deep(.v-field) {
      background: var(--color-bg-secondary);
    }

    :deep(.v-field__input) {
      min-height: 44px;
      padding: 12px 16px;
      font-size: 14px;
      line-height: 1.5;
    }

    :deep(textarea) {
      resize: none;
    }
  }

  &__recipient {
    flex-shrink: 0;
    width: 160px;

    :deep(.v-field) {
      background: var(--color-bg-secondary);
    }

    :deep(.v-field__input) {
      min-height: 44px;
      font-size: 14px;
    }
  }

  &__submit {
    flex-shrink: 0;
    min-width: 44px !important;
    min-height: 44px !important;

    &:disabled {
      opacity: 0.4;
    }
  }
}

/* Focus styles for accessibility */
.message-input__textarea:deep(.v-field--focused) {
  box-shadow: 0 0 0 2px var(--color-accent-primary);
}

.message-input__recipient:deep(.v-field--focused) {
  box-shadow: 0 0 0 2px var(--color-accent-primary);
}

/* Responsive: Tablet layout */
@media (max-width: 960px) {
  .message-input {
    padding: 12px;

    &__container {
      gap: 10px;
    }

    &__recipient {
      width: 140px;
    }
  }
}

/* Responsive: Mobile layout */
@media (max-width: 600px) {
  .message-input {
    padding: 12px 8px;

    &__container {
      flex-wrap: wrap;
      gap: 8px;
    }

    &__user-icon {
      display: none; /* Hide user icon on mobile to save space */
    }

    &__textarea {
      flex: 1 1 100%;
      min-width: 100%;
      order: 1;
    }

    &__recipient {
      flex: 1 1 auto;
      width: auto;
      min-width: 120px;
      order: 2;
    }

    &__submit {
      flex-shrink: 0;
      order: 3;
      min-width: 48px !important;
      min-height: 48px !important;
    }
  }
}

/* Responsive: Very small screens */
@media (max-width: 400px) {
  .message-input {
    &__recipient {
      flex: 1 1 100%;
      width: 100%;
      order: 2;
    }

    &__submit {
      flex: 1 1 100%;
      width: 100%;
      order: 3;
    }
  }
}

/* Accessibility: High contrast mode */
@media (prefers-contrast: high) {
  .message-input {
    border-top-width: 3px;
  }

  .message-input__textarea:deep(.v-field),
  .message-input__recipient:deep(.v-field) {
    border-width: 2px;
  }
}

/* Dark theme optimization */
.v-theme--dark {
  .message-input {
    background: var(--color-bg-primary);

    &__textarea:deep(.v-field),
    &__recipient:deep(.v-field) {
      background: var(--color-bg-elevated);
    }
  }
}

/* Light theme optimization */
.v-theme--light {
  .message-input {
    background: var(--color-bg-primary);
    border-top-color: var(--color-border);

    &__textarea:deep(.v-field),
    &__recipient:deep(.v-field) {
      background: #f8f9fa;
    }
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .message-input__submit {
    transition: none;
  }
}

/* Position-specific styling (Handover 0231 Phase 4) */
.message-input.position-inline {
  /* Default - uses existing sticky positioning */
}

.message-input.position-modal {
  position: static;
  width: 100%;
  border-top: 1px solid rgba(0, 0, 0, 0.12);
  padding: 16px;
  background: white;
  box-shadow: none;
}

.message-input.position-sticky {
  position: sticky;
  bottom: 0;
  background: white;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
  z-index: 100;
  padding: 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.12);
}
</style>
