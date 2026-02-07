<template>
  <div
    class="message-stream"
    role="log"
    aria-live="polite"
    :aria-label="`Message stream for project ${projectId}`"
  >
    <!-- Header -->
    <div class="message-stream__header">
      <h3 class="text-h6 mb-0">Messages</h3>
    </div>

    <!-- Messages Container with Virtual Scrolling -->
    <div ref="messagesContainer" class="message-stream__container" @scroll="handleScroll">
      <!-- Loading State -->
      <div v-if="loading" class="message-stream__loading">
        <v-skeleton-loader
          v-for="i in 3"
          :key="`skeleton-${i}`"
          type="list-item-avatar-two-line"
          class="mb-3"
        />
      </div>

      <!-- Empty State -->
      <div v-else-if="messages.length === 0" class="message-stream__empty">
        <v-icon size="64" color="grey-lighten-1" class="mb-4"> mdi-message-outline </v-icon>
        <p class="text-body-1 text-grey">No messages yet</p>
        <p class="text-caption text-grey-lighten-1">
          Messages will appear here when agents communicate
        </p>
      </div>

      <!-- Messages List -->
      <div v-else class="message-stream__list" data-testid="message-list">
        <div
          v-for="message in messages"
          :key="message.id"
          class="message-stream__message"
          data-testid="message-item"
          :class="{
            'message-stream__message--user': isUserMessage(message),
            'message-stream__message--agent': !isUserMessage(message),
          }"
        >
          <!-- Chat Head Badge (for agent messages) -->
          <ChatHeadBadge
            v-if="!isUserMessage(message)"
            :agent-display-name="getAgentDisplayName(message)"
            size="default"
            class="message-stream__chat-head"
          />

          <!-- User Icon (for user messages) -->
          <div v-else class="message-stream__user-icon">
            <v-icon size="32" color="blue">mdi-account-circle</v-icon>
          </div>

          <!-- Message Content -->
          <div class="message-stream__content">
            <!-- Message Routing -->
            <div class="message-stream__routing">
              <span
                v-if="isUserMessage(message)"
                class="text-subtitle-2 font-weight-bold text-blue"
              >
                {{ developerUsername }}
              </span>
              <span v-if="isBroadcast(message)" class="text-subtitle-2 font-weight-bold">
                → Broadcast:
              </span>
              <span v-else-if="message.to_agent_id || message.to_agent" class="text-subtitle-2 font-weight-bold">
                → To
                <v-tooltip v-if="message.to_agent_id" location="bottom">
                  <template #activator="{ props: tooltipProps }">
                    <span v-bind="tooltipProps" class="agent-id-truncated">{{ truncateUuid(message.to_agent_id) }}</span>
                  </template>
                  <span>{{ message.to_agent_id }}</span>
                </v-tooltip>
                <span v-else>{{ formatAgentName(message.to_agent) }}</span>:
              </span>
            </div>

            <!-- Message Text -->
            <div class="message-stream__text">
              {{ message.content }}
            </div>

            <!-- Message Timestamp -->
            <div class="message-stream__timestamp" :title="formatFullTimestamp(message.timestamp)">
              {{ formatRelativeTime(message.timestamp) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Scroll to Bottom Button (shown when user scrolls up) -->
    <transition name="scroll-button">
      <v-btn
        v-if="showScrollButton"
        class="message-stream__scroll-button"
        icon
        color="primary"
        elevation="4"
        size="small"
        aria-label="Scroll to latest messages"
        @click="scrollToBottom"
      >
        <v-icon>mdi-chevron-down</v-icon>
        <v-badge v-if="unreadCount > 0" :content="unreadCount" color="error" floating />
      </v-btn>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { formatDistanceToNow, format } from 'date-fns'
import ChatHeadBadge from './ChatHeadBadge.vue'

/**
 * MessageStream Component
 *
 * Vertical scrolling message feed for agent-to-agent and user-to-agent communication.
 * Displays messages in chronological order with auto-scroll, manual override, and
 * efficient rendering for large message lists.
 *
 * Features:
 * - Auto-scroll to bottom on new messages
 * - Manual scroll with auto-scroll override
 * - "Scroll to bottom" button with unread count
 * - Chat head badges for agent messages
 * - User icon for developer messages
 * - Relative timestamps with full timestamp on hover
 * - Message routing display (To [agent]: or Broadcast:)
 * - Empty and loading states
 * - Keyboard navigation support
 * - ARIA labels for accessibility
 *
 * @see handovers/0077_launch_jobs_dual_tab_interface.md
 */

const props = defineProps({
  /**
   * Array of message objects
   * Each message should have:
   * - id: unique identifier
   * - from_agent: sender agent type (if agent message)
   * - to_agent: recipient agent type (if targeted message)
   * - type: message type (e.g., 'agent', 'broadcast', 'user')
   * - content: message text
   * - timestamp: ISO timestamp
   * - from: 'agent' | 'developer'
   * - agent_display_name: agent display name (for chat head color)
   */
  messages: {
    type: Array,
    required: true,
    default: () => [],
  },

  /**
   * Project ID (for ARIA label)
   */
  projectId: {
    type: String,
    required: true,
  },

  /**
   * Auto-scroll to bottom on new messages
   */
  autoScroll: {
    type: Boolean,
    default: true,
  },

  /**
   * Current developer username (for displaying on developer messages)
   */
  developerUsername: {
    type: String,
    default: 'Developer',
  },

  /**
   * Loading state (shows skeleton loaders)
   */
  loading: {
    type: Boolean,
    default: false,
  },
})

// Refs
const messagesContainer = ref(null)
const showScrollButton = ref(false)
const unreadCount = ref(0)
const userScrolledUp = ref(false)
const lastMessageCount = ref(0)

/**
 * Check if message is from user/developer
 */
function isUserMessage(message) {
  return message.from === 'developer' || message.from === 'user' || message.type === 'user'
}

/**
 * Check if message is broadcast
 */
function isBroadcast(message) {
  return message.type === 'broadcast' || !message.to_agent
}

/**
 * Get agent type from message
 */
function getAgentDisplayName(message) {
  return message.agent_display_name || message.from_agent || 'orchestrator'
}

/**
 * Format agent name for display
 */
function formatAgentName(displayName) {
  if (!displayName) return 'Unknown'
  return displayName.charAt(0).toUpperCase() + displayName.slice(1)
}

/**
 * Truncate UUID to first 8 characters for display
 * @param {string} uuid - Full UUID
 * @returns {string} Truncated UUID (e.g., "abc12345...")
 */
function truncateUuid(uuid) {
  if (!uuid || typeof uuid !== 'string') return 'unknown'
  return `${uuid.slice(0, 8)  }...`
}

/**
 * Format relative timestamp (e.g., "2 minutes ago")
 */
function formatRelativeTime(timestamp) {
  if (!timestamp) return 'Unknown'

  try {
    const date = new Date(timestamp)
    return formatDistanceToNow(date, { addSuffix: true })
  } catch (error) {
    console.error('[MessageStream] Error formatting relative time:', error)
    return 'Unknown'
  }
}

/**
 * Format full timestamp for hover tooltip
 */
function formatFullTimestamp(timestamp) {
  if (!timestamp) return 'Unknown'

  try {
    const date = new Date(timestamp)
    return format(date, 'PPpp') // e.g., "Apr 29, 2023, 9:30:00 AM"
  } catch (error) {
    console.error('[MessageStream] Error formatting full timestamp:', error)
    return 'Unknown'
  }
}

/**
 * Check if user is scrolled to bottom
 */
function isScrolledToBottom() {
  if (!messagesContainer.value) return true

  const container = messagesContainer.value
  const threshold = 50 // pixels from bottom
  const scrollBottom = container.scrollHeight - container.scrollTop - container.clientHeight

  return scrollBottom <= threshold
}

/**
 * Handle scroll event
 */
function handleScroll() {
  if (!messagesContainer.value) return

  const atBottom = isScrolledToBottom()

  if (atBottom) {
    // User scrolled to bottom, resume auto-scroll
    userScrolledUp.value = false
    showScrollButton.value = false
    unreadCount.value = 0
  } else {
    // User scrolled up, disable auto-scroll
    userScrolledUp.value = true
    showScrollButton.value = true
  }
}

/**
 * Scroll to bottom of messages
 */
function scrollToBottom(smooth = true) {
  if (!messagesContainer.value) return

  nextTick(() => {
    const container = messagesContainer.value
    container.scrollTo({
      top: container.scrollHeight,
      behavior: smooth ? 'smooth' : 'auto',
    })

    // Reset state
    userScrolledUp.value = false
    showScrollButton.value = false
    unreadCount.value = 0
  })
}

/**
 * Watch messages array for new messages
 */
watch(
  () => props.messages.length,
  (newCount, oldCount) => {
    // New message arrived
    if (newCount > oldCount) {
      const newMessagesCount = newCount - oldCount

      // If user scrolled up, increment unread count
      if (userScrolledUp.value) {
        unreadCount.value += newMessagesCount
      } else if (props.autoScroll) {
        // Auto-scroll to bottom
        nextTick(() => {
          scrollToBottom(true)
        })
      }
    }

    lastMessageCount.value = newCount
  },
  { immediate: true },
)

/**
 * Watch loading state
 */
watch(
  () => props.loading,
  (isLoading) => {
    if (!isLoading && props.messages.length > 0) {
      // Data loaded, scroll to bottom
      nextTick(() => {
        scrollToBottom(false)
      })
    }
  },
)

/**
 * Keyboard navigation
 */
function handleKeydown(event) {
  if (!messagesContainer.value) return

  const container = messagesContainer.value

  switch (event.key) {
    case 'Home':
      event.preventDefault()
      container.scrollTo({ top: 0, behavior: 'smooth' })
      break
    case 'End':
      event.preventDefault()
      scrollToBottom(true)
      break
    case 'PageUp':
      event.preventDefault()
      container.scrollBy({ top: -container.clientHeight, behavior: 'smooth' })
      break
    case 'PageDown':
      event.preventDefault()
      container.scrollBy({ top: container.clientHeight, behavior: 'smooth' })
      break
  }
}

/**
 * Lifecycle - Mount
 */
onMounted(() => {
  // Add keyboard event listener
  if (messagesContainer.value) {
    messagesContainer.value.addEventListener('keydown', handleKeydown)
  }

  // Initial scroll to bottom
  if (props.messages.length > 0) {
    nextTick(() => {
      scrollToBottom(false)
    })
  }
})

/**
 * Lifecycle - Unmount
 */
onBeforeUnmount(() => {
  // Remove keyboard event listener
  if (messagesContainer.value) {
    messagesContainer.value.removeEventListener('keydown', handleKeydown)
  }
})
</script>

<style scoped lang="scss">
@use '@/styles/agent-colors.scss' as *;

.message-stream {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-secondary, #f5f5f5);
  border-radius: 8px;
  overflow: hidden;
  position: relative;

  &__header {
    padding: 16px;
    background: var(--color-bg-primary, #ffffff);
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
    flex-shrink: 0;
  }

  &__container {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    max-height: 600px;
    padding: 16px;
    scroll-behavior: smooth;

    /* Custom scrollbar styling */
    &::-webkit-scrollbar {
      width: 8px;
    }

    &::-webkit-scrollbar-track {
      background: transparent;
    }

    &::-webkit-scrollbar-thumb {
      background: rgba(0, 0, 0, 0.2);
      border-radius: 4px;
      transition: background 0.2s ease;

      &:hover {
        background: rgba(0, 0, 0, 0.3);
      }
    }

    /* Firefox */
    scrollbar-color: rgba(0, 0, 0, 0.2) transparent;
    scrollbar-width: thin;
  }

  &__loading {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  &__empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 300px;
    text-align: center;
    padding: 32px;
  }

  &__list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  &__message {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    animation: messageSlideIn 0.3s ease-out;

    &--user {
      .message-stream__content {
        background: rgba(52, 152, 219, 0.1);
        border-left: 3px solid var(--agent-implementor-primary, #3498db);
      }
    }

    &--agent {
      .message-stream__content {
        background: var(--color-bg-primary, #ffffff);
        border-left: none;
      }
    }
  }

  &__chat-head {
    flex-shrink: 0;
    margin-top: 4px;
  }

  &__user-icon {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 4px;
  }

  &__content {
    flex: 1;
    padding: 12px;
    border-radius: 8px;
    min-width: 0;
    word-wrap: break-word;
    overflow-wrap: break-word;
  }

  &__routing {
    margin-bottom: 4px;
    color: var(--color-accent-primary, #ffc300);
    font-size: 13px;
    line-height: 1.4;
  }

  &__text {
    color: var(--color-text-primary, rgba(0, 0, 0, 0.87));
    font-size: 14px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
    margin-bottom: 4px;
  }

  &__timestamp {
    font-size: 12px;
    color: var(--color-text-secondary, rgba(0, 0, 0, 0.6));
    cursor: help;
  }
}

/* Agent ID truncated styling */
.agent-id-truncated {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  cursor: help;
}

  &__scroll-button {
    position: absolute;
    bottom: 16px;
    right: 16px;
    z-index: 10;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }
}

/* Animations */
@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.scroll-button-enter-active,
.scroll-button-leave-active {
  transition: all 0.3s ease;
}

.scroll-button-enter-from,
.scroll-button-leave-to {
  opacity: 0;
  transform: scale(0.8);
}

/* Keyboard focus styling */
.message-stream__container:focus {
  outline: 2px solid var(--color-accent-primary, #ffc300);
  outline-offset: -2px;
}

/* Responsive Design */
@media (max-width: 768px) {
  .message-stream {
    &__container {
      max-height: 400px;
      padding: 12px;
    }

    &__message {
      gap: 8px;
    }

    &__content {
      padding: 10px;
    }

    &__chat-head {
      width: 28px;
      height: 28px;
      font-size: 11px;
    }

    &__user-icon {
      width: 28px;
      height: 28px;

      :deep(.v-icon) {
        font-size: 28px;
      }
    }
  }
}

/* High Contrast Mode Support */
@media (prefers-contrast: high) {
  .message-stream {
    &__content {
      border: 2px solid currentColor;
    }

    &__message--user {
      .message-stream__content {
        border-left-width: 4px;
      }
    }
  }
}

/* Reduced Motion Support */
@media (prefers-reduced-motion: reduce) {
  .message-stream__container {
    scroll-behavior: auto;
  }

  @keyframes messageSlideIn {
    from,
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .scroll-button-enter-active,
  .scroll-button-leave-active {
    transition: none;
  }
}
</style>
