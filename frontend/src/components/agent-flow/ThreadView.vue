<template>
  <v-card class="thread-view-card" elevation="2">
    <!-- Header -->
    <v-card-title class="d-flex align-center justify-space-between">
      <div class="d-flex align-center">
        <v-icon icon="mdi-message-text" class="mr-2" color="primary" />
        <span>Message Thread</span>
        <v-chip size="small" variant="flat" color="primary" class="ml-3">
          {{ messages.length }}
        </v-chip>
      </div>
      <v-btn
        icon
        size="small"
        variant="text"
        :icon="autoScroll ? 'mdi-arrow-collapse-down' : 'mdi-arrow-expand-down'"
        @click="toggleAutoScroll"
        title="Toggle auto-scroll"
      />
    </v-card-title>

    <v-divider />

    <!-- Filter Bar -->
    <div class="thread-filters">
      <v-text-field
        v-model="searchQuery"
        placeholder="Search messages..."
        prepend-inner-icon="mdi-magnify"
        hide-details
        size="small"
        variant="outlined"
        density="compact"
        class="search-field"
      />

      <v-menu>
        <template v-slot:activator="{ props }">
          <v-btn
            size="small"
            variant="outlined"
            v-bind="props"
            :color="hasActiveFilters ? 'primary' : ''"
            class="filter-btn"
          >
            <v-icon icon="mdi-filter" size="small" />
          </v-btn>
        </template>
        <v-list density="compact">
          <v-list-item
            v-for="status in statuses"
            :key="status"
            @click="toggleStatusFilter(status)"
            :active="statusFilters.has(status)"
          >
            <template v-slot:prepend>
              <v-checkbox :model-value="statusFilters.has(status)" hide-details size="small" />
            </template>
            <v-list-item-title>{{ formatStatus(status) }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </div>

    <!-- Messages Container -->
    <v-card-text class="messages-container" ref="messagesContainer">
      <div v-if="filteredMessages.length === 0" class="empty-messages">
        <v-icon icon="mdi-message-outline" size="64" color="grey" />
        <p>{{ searchQuery ? 'No messages match your search' : 'No messages yet' }}</p>
      </div>

      <transition-group name="list" tag="div" class="messages-list" v-else>
        <div
          v-for="message in filteredMessages"
          :key="message.id"
          class="message-row"
          :class="{
            'is-sent': message.type === 'sent',
            'is-received': message.type === 'received',
            'is-error': message.status === 'error',
          }"
        >
          <!-- Message Card -->
          <div class="message-card">
            <!-- Message Header -->
            <div class="message-header">
              <div class="header-info">
                <span class="sender">{{ message.from || 'Unknown' }}</span>
                <span v-if="message.to" class="recipient">
                  to {{ Array.isArray(message.to) ? message.to.join(', ') : message.to }}
                </span>
              </div>

              <div class="header-meta">
                <v-chip size="x-small" :color="getStatusColor(message.status)" variant="flat">
                  {{ formatStatus(message.status) }}
                </v-chip>
                <span class="message-time">{{ formatTime(message.createdAt) }}</span>
              </div>
            </div>

            <!-- Message Content -->
            <div class="message-content">
              <p>{{ message.content }}</p>
            </div>

            <!-- Message Footer -->
            <div v-if="showMessageFooter(message)" class="message-footer">
              <div
                v-if="message.acknowledged_by && message.acknowledged_by.length > 0"
                class="acks"
              >
                <v-icon icon="mdi-check-circle" size="x-small" color="success" class="mr-1" />
                <span>Acknowledged by: {{ message.acknowledged_by.join(', ') }}</span>
              </div>

              <div v-if="message.result" class="result">
                <v-icon icon="mdi-information-outline" size="x-small" color="info" class="mr-1" />
                <span>{{ truncate(message.result, 80) }}</span>
              </div>
            </div>

            <!-- Message Actions -->
            <div class="message-actions">
              <v-btn
                size="x-small"
                variant="text"
                @click="expandMessage(message.id)"
                title="View details"
              >
                <v-icon icon="mdi-chevron-down" size="x-small" />
              </v-btn>

              <v-menu size="small">
                <template v-slot:activator="{ props }">
                  <v-btn size="x-small" variant="text" v-bind="props">
                    <v-icon icon="mdi-dots-vertical" size="x-small" />
                  </v-btn>
                </template>
                <v-list density="compact">
                  <v-list-item @click="copyToClipboard(message.content)" title="Copy message">
                    <template v-slot:prepend>
                      <v-icon icon="mdi-content-copy" />
                    </template>
                    <v-list-item-title>Copy</v-list-item-title>
                  </v-list-item>

                  <v-list-item @click="openMessageDetails(message)" title="View full details">
                    <template v-slot:prepend>
                      <v-icon icon="mdi-eye" />
                    </template>
                    <v-list-item-title>Details</v-list-item-title>
                  </v-list-item>

                  <v-divider />

                  <v-list-item @click="deleteMessage(message.id)" title="Delete message">
                    <template v-slot:prepend>
                      <v-icon icon="mdi-trash-can" color="error" />
                    </template>
                    <v-list-item-title class="text-error">Delete</v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>
            </div>
          </div>

          <!-- Expand Details -->
          <v-expand-transition>
            <div v-if="expandedMessages.has(message.id)" class="message-details">
              <div class="details-item">
                <span class="label">ID</span>
                <span class="value mono">{{ message.id }}</span>
              </div>

              <div class="details-item">
                <span class="label">Priority</span>
                <v-chip size="x-small" :color="getPriorityColor(message.priority)" variant="flat">
                  {{ message.priority || 'normal' }}
                </v-chip>
              </div>

              <div class="details-item">
                <span class="label">Created</span>
                <span class="value mono">{{ formatFullTime(message.createdAt) }}</span>
              </div>

              <div v-if="message.completedAt" class="details-item">
                <span class="label">Completed</span>
                <span class="value mono">{{ formatFullTime(message.completedAt) }}</span>
              </div>
            </div>
          </v-expand-transition>
        </div>
      </transition-group>

      <div v-if="filteredMessages.length > 0 && !allMessagesLoaded" class="load-more">
        <v-btn size="small" variant="text" @click="loadMore" :loading="loadingMore">
          Load More
        </v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useAgentFlowStore } from '@/stores/agentFlow'
import { formatDistanceToNow, format } from 'date-fns'

const props = defineProps({
  nodeId: {
    type: String,
    default: null,
  },
  agentName: {
    type: String,
    default: null,
  },
  limit: {
    type: Number,
    default: 50,
  },
})

const emit = defineEmits(['message-details', 'load-more'])

const flowStore = useAgentFlowStore()
const messagesContainer = ref(null)
const searchQuery = ref('')
const statusFilters = ref(new Set(['sent', 'received', 'acknowledged', 'completed']))
const expandedMessages = ref(new Set())
const autoScroll = ref(true)
const displayedMessages = ref(props.limit)
const loadingMore = ref(false)
const allMessagesLoaded = ref(false)

const statuses = ['sent', 'received', 'acknowledged', 'completed', 'error']

const messages = computed(() => {
  if (props.nodeId) {
    return flowStore.getThreadMessages(props.nodeId) || []
  }
  return []
})

const filteredMessages = computed(() => {
  let filtered = messages.value.slice(0, displayedMessages.value)

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(
      (m) =>
        (m.content || '').toLowerCase().includes(query) ||
        (m.from || '').toLowerCase().includes(query) ||
        (Array.isArray(m.to) ? m.to.join(',') : m.to || '').toLowerCase().includes(query),
    )
  }

  // Filter by status
  if (statusFilters.value.size > 0) {
    filtered = filtered.filter((m) => statusFilters.value.has(m.status || m.type))
  }

  return filtered.reverse() // Show newest first
})

const hasActiveFilters = computed(
  () => statusFilters.value.size < statuses.length || searchQuery.value.length > 0,
)

function getStatusColor(status) {
  const colorMap = {
    sent: 'primary',
    received: 'info',
    acknowledged: 'success',
    completed: 'secondary',
    error: 'error',
  }
  return colorMap[status] || 'grey'
}

function getPriorityColor(priority) {
  const colorMap = {
    urgent: 'error',
    high: 'warning',
    normal: 'info',
    low: 'grey',
  }
  return colorMap[priority] || 'info'
}

function formatStatus(status) {
  if (!status) return 'Unknown'
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function formatTime(timestamp) {
  if (!timestamp) return 'Never'
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date

  if (diffMs < 60000) {
    return 'Just now'
  }
  return formatDistanceToNow(date, { addSuffix: true })
}

function formatFullTime(timestamp) {
  if (!timestamp) return 'N/A'
  return format(new Date(timestamp), 'yyyy-MM-dd HH:mm:ss')
}

function showMessageFooter(message) {
  return (
    (message.acknowledged_by && message.acknowledged_by.length > 0) ||
    message.result ||
    message.error
  )
}

function truncate(str, length) {
  if (!str) return ''
  return str.length > length ? str.substring(0, length) + '...' : str
}

function toggleStatusFilter(status) {
  if (statusFilters.value.has(status)) {
    statusFilters.value.delete(status)
  } else {
    statusFilters.value.add(status)
  }
}

function toggleAutoScroll() {
  autoScroll.value = !autoScroll.value
}

function expandMessage(messageId) {
  if (expandedMessages.value.has(messageId)) {
    expandedMessages.value.delete(messageId)
  } else {
    expandedMessages.value.add(messageId)
  }
}

function openMessageDetails(message) {
  emit('message-details', message)
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).catch((err) => {
    console.error('Failed to copy:', err)
  })
}

function deleteMessage(messageId) {
  const index = messages.value.findIndex((m) => m.id === messageId)
  if (index !== -1) {
    messages.value.splice(index, 1)
  }
}

function loadMore() {
  loadingMore.value = true
  displayedMessages.value += props.limit

  if (displayedMessages.value >= messages.value.length) {
    allMessagesLoaded.value = true
  }

  emit('load-more', displayedMessages.value)

  nextTick(() => {
    loadingMore.value = false
  })
}

function scrollToBottom() {
  if (!autoScroll.value || !messagesContainer.value) return

  nextTick(() => {
    const container = messagesContainer.value.$el || messagesContainer.value
    container.scrollTop = container.scrollHeight
  })
}

watch(filteredMessages, () => {
  scrollToBottom()
})

onMounted(() => {
  scrollToBottom()
})
</script>

<style scoped lang="scss">
.thread-view-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #182739;

  :deep(.v-card-title) {
    padding: 12px 16px;
    background: linear-gradient(135deg, #1e3147 0%, #182739 100%);
    border-bottom: 1px solid #315074;
  }

  :deep(.v-card-text) {
    padding: 0;
  }

  .thread-filters {
    display: flex;
    gap: 8px;
    padding: 12px;
    background: rgba(30, 49, 71, 0.5);
    border-bottom: 1px solid rgba(49, 80, 116, 0.3);

    .search-field {
      flex: 1;
    }

    .filter-btn {
      min-width: 36px;
    }
  }

  .messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;

    .empty-messages {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #8f97b7;

      p {
        margin-top: 12px;
      }
    }

    .messages-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .message-row {
      animation: fadeIn 0.3s ease;

      .message-card {
        background: linear-gradient(135deg, rgba(30, 49, 71, 0.8) 0%, rgba(24, 39, 57, 0.8) 100%);
        border: 1px solid rgba(49, 80, 116, 0.4);
        border-left: 4px solid #315074;
        border-radius: 6px;
        padding: 12px;
        transition: all 0.2s ease;

        &:hover {
          background: linear-gradient(
            135deg,
            rgba(30, 49, 71, 0.95) 0%,
            rgba(24, 39, 57, 0.95) 100%
          );
          border-color: rgba(49, 80, 116, 0.6);
        }

        .message-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 8px;

          .header-info {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            font-size: 12px;

            .sender {
              font-weight: 600;
              color: #67bd6d;
            }

            .recipient {
              color: #8f97b7;
            }
          }

          .header-meta {
            display: flex;
            align-items: center;
            gap: 8px;

            .message-time {
              font-size: 11px;
              color: #8f97b7;
              font-family: 'Roboto Mono', monospace;
              white-space: nowrap;
            }
          }
        }

        .message-content {
          color: #e1e1e1;
          font-size: 13px;
          line-height: 1.4;
          word-break: break-word;
          margin-bottom: 8px;

          p {
            margin: 0;
          }
        }

        .message-footer {
          font-size: 11px;
          border-top: 1px solid rgba(49, 80, 116, 0.3);
          padding-top: 8px;
          display: flex;
          flex-direction: column;
          gap: 4px;

          .acks,
          .result {
            display: flex;
            align-items: center;
            gap: 4px;
            color: #8f97b7;
          }

          .acks {
            color: #67bd6d;
          }

          .result {
            color: #8b5cf6;
          }
        }

        .message-actions {
          display: flex;
          gap: 4px;
          justify-content: flex-end;
          margin-top: 8px;
        }
      }

      &.is-sent .message-card {
        border-left-color: #67bd6d;
      }

      &.is-received .message-card {
        border-left-color: #8b5cf6;
      }

      &.is-error .message-card {
        border-left-color: #c6298c;
        background: linear-gradient(
          135deg,
          rgba(198, 41, 140, 0.1) 0%,
          rgba(198, 41, 140, 0.05) 100%
        );
      }

      .message-details {
        margin-top: 8px;
        background: rgba(49, 80, 116, 0.2);
        border-radius: 4px;
        padding: 8px;
        font-size: 11px;

        .details-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
          padding: 4px 0;
          border-bottom: 1px solid rgba(49, 80, 116, 0.3);

          &:last-child {
            border-bottom: none;
          }

          .label {
            color: #8f97b7;
            font-weight: 500;
          }

          .value {
            color: #e1e1e1;
            font-weight: 600;

            &.mono {
              font-family: 'Roboto Mono', monospace;
            }
          }
        }
      }
    }

    .load-more {
      display: flex;
      justify-content: center;
      padding: 12px 0;
    }
  }

  // Scrollbar styling
  ::-webkit-scrollbar {
    width: 8px;
  }

  ::-webkit-scrollbar-track {
    background: rgba(30, 49, 71, 0.3);
  }

  ::-webkit-scrollbar-thumb {
    background: rgba(49, 80, 116, 0.5);
    border-radius: 4px;

    &:hover {
      background: rgba(49, 80, 116, 0.7);
    }
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}

.list-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.list-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
