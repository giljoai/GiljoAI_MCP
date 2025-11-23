<template>
  <div
    class="agent-node"
    :class="{
      'is-selected': selected,
      'is-error': data.status === 'error',
      'is-active': data.status === 'active' || data.status === 'running',
      'is-completed': data.status === 'completed' || data.status === 'complete',
    }"
    :style="{ '--node-color': data.color }"
  >
    <!-- Status Indicator Ring -->
    <div class="node-status-ring" :class="`status-${data.status}`" />

    <!-- Node Header -->
    <div class="node-header">
      <v-icon :icon="data.icon || 'mdi-robot'" size="small" class="node-icon" />
      <div class="node-title">{{ data.label }}</div>
      <v-icon
        v-if="data.status === 'active' || data.status === 'running'"
        icon="mdi-motion-play"
        size="x-small"
        class="pulse-icon"
      />
    </div>

    <!-- Node Body - Status Info -->
    <div class="node-body">
      <!-- Status Chip -->
      <v-chip
        size="x-small"
        :color="getStatusColor(data.status)"
        variant="flat"
        class="status-chip"
      >
        {{ formatStatus(data.status) }}
      </v-chip>

      <!-- Metrics Row -->
      <div class="metrics-row">
        <div v-if="data.health !== undefined" class="metric">
          <v-icon icon="mdi-heart-pulse" size="x-small" />
          <span class="metric-value">{{ data.health }}%</span>
        </div>
        <div v-if="data.activeJobs !== undefined && data.activeJobs > 0" class="metric">
          <v-icon icon="mdi-briefcase" size="x-small" />
          <span class="metric-value">{{ data.activeJobs }}</span>
        </div>
      </div>

      <!-- Context Usage -->
      <div v-if="data.contextUsed !== undefined" class="progress-section">
        <div class="progress-label">
          <span>Context</span>
          <span class="metric-value">{{ data.contextUsed }}%</span>
        </div>
        <v-progress-linear
          :model-value="data.contextUsed"
          :color="getContextColor(data.contextUsed)"
          height="4"
          class="progress-bar"
        />
      </div>
    </div>

    <!-- Node Footer - Timestamps -->
    <div v-if="data.createdAt" class="node-footer">
      <span class="timestamp">{{ formatTime(data.updatedAt || data.createdAt) }}</span>
    </div>

    <!-- Message Count Badge -->
    <div v-if="data.messages && data.messages.length > 0" class="message-badge">
      <span>{{ data.messages.length }}</span>
    </div>

    <!-- Hover Panel -->
    <transition name="fade">
      <div v-if="showHover" class="node-hover-panel">
        <div class="hover-content">
          <div class="hover-section">
            <div class="hover-label">Role</div>
            <div class="hover-value">{{ data.role || 'Agent' }}</div>
          </div>

          <div v-if="data.tokens !== undefined" class="hover-section">
            <div class="hover-label">Tokens Used</div>
            <div class="hover-value">{{ formatNumber(data.tokens) }}</div>
          </div>

          <div v-if="data.duration !== undefined" class="hover-section">
            <div class="hover-label">Duration</div>
            <div class="hover-value">{{ formatDuration(data.duration) }}</div>
          </div>

          <div v-if="data.messages && data.messages.length > 0" class="hover-section">
            <div class="hover-label">Recent Messages</div>
            <div class="message-list">
              <div
                v-for="msg in data.messages.slice(-3)"
                :key="msg.id"
                class="message-item"
                :title="msg.content"
              >
                {{ truncate(msg.content, 30) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- Vue Flow Handle -->
    <Handle type="target" position="top" />
    <Handle type="source" position="bottom" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Handle } from '@vue-flow/core'
import { formatDistanceToNow } from 'date-fns'

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
  selected: {
    type: Boolean,
    default: false,
  },
})

const showHover = ref(false)

const getStatusColor = computed(() => (status) => {
  const statusColorMap = {
    active: 'success',
    running: 'success',
    waiting: 'warning',
    pending: 'info',
    completed: 'secondary',
    complete: 'secondary',
    error: 'error',
    failed: 'error',
  }
  return statusColorMap[status] || 'grey'
})

const getContextColor = computed(() => (usage) => {
  if (usage < 50) return 'success'
  if (usage < 70) return 'warning'
  if (usage < 85) return 'orange'
  return 'error'
})

function formatStatus(status) {
  if (!status) return 'Unknown'
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date

  if (diffMs < 60000) {
    return 'Just now'
  } else if (diffMs < 3600000) {
    return formatDistanceToNow(date, { addSuffix: false })
  } else {
    return formatDistanceToNow(date, { addSuffix: false })
  }
}

function formatDuration(ms) {
  if (!ms || ms === 0) return '0s'
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`
  } else {
    return `${seconds}s`
  }
}

function formatNumber(num) {
  if (!num) return '0'
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

function truncate(str, length) {
  if (!str) return ''
  return str.length > length ? str.substring(0, length) + '...' : str
}
</script>

<style scoped lang="scss">
.agent-node {
  width: 220px;
  background: linear-gradient(135deg, #1e3147 0%, #182739 100%);
  border: 2px solid var(--node-color, #315074);
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(circle at top left, rgba(255, 255, 255, 0.1) 0%, transparent 50%);
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  &:hover {
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    transform: translateY(-4px);

    &::before {
      opacity: 1;
    }
  }

  &.is-selected {
    border-color: #ffc300;
    box-shadow:
      0 0 20px rgba(255, 195, 0, 0.5),
      0 4px 12px rgba(0, 0, 0, 0.3);
  }

  &.is-error {
    border-color: #c6298c;
    background: linear-gradient(135deg, rgba(198, 41, 140, 0.1) 0%, rgba(198, 41, 140, 0.05) 100%);
  }

  &.is-active {
    animation: node-pulse 2s ease-in-out infinite;
  }

  &.is-completed {
    opacity: 0.8;
  }

  .node-status-ring {
    position: absolute;
    top: 2px;
    right: 2px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--node-color, #315074);
    box-shadow: 0 0 8px var(--node-color, #315074);

    &.status-active,
    &.status-running {
      animation: status-pulse 1.5s ease-in-out infinite;
    }

    &.status-error {
      animation: status-error-pulse 0.5s ease-in-out infinite;
    }
  }

  .node-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(49, 80, 116, 0.5);

    .node-icon {
      color: var(--node-color, #315074);
      flex-shrink: 0;
    }

    .node-title {
      flex: 1;
      font-size: 13px;
      font-weight: 600;
      color: #e1e1e1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .pulse-icon {
      animation: icon-pulse 1s ease-in-out infinite;
      color: #67bd6d;
    }
  }

  .node-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 8px;

    .status-chip {
      align-self: flex-start;
      font-size: 11px !important;
    }

    .metrics-row {
      display: flex;
      gap: 12px;
      font-size: 11px;

      .metric {
        display: flex;
        align-items: center;
        gap: 4px;
        color: #8f97b7;

        :deep(.v-icon) {
          color: var(--node-color, #315074);
        }

        .metric-value {
          font-weight: 600;
          color: #e1e1e1;
          font-family: 'Roboto Mono', monospace;
        }
      }
    }

    .progress-section {
      .progress-label {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 10px;
        color: #8f97b7;
        margin-bottom: 4px;

        .metric-value {
          color: #e1e1e1;
          font-weight: 600;
          font-family: 'Roboto Mono', monospace;
        }
      }

      .progress-bar {
        border-radius: 2px;
      }
    }
  }

  .node-footer {
    font-size: 10px;
    color: #8f97b7;
    text-align: right;

    .timestamp {
      font-family: 'Roboto Mono', monospace;
    }
  }

  .message-badge {
    position: absolute;
    bottom: 6px;
    left: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    background: linear-gradient(135deg, #67bd6d 0%, #5aa85e 100%);
    border-radius: 50%;
    font-size: 11px;
    font-weight: 700;
    color: #0e1c2d;
    box-shadow: 0 2px 8px rgba(103, 189, 109, 0.4);
  }

  .node-hover-panel {
    position: absolute;
    bottom: 100%;
    left: 0;
    right: 0;
    background: linear-gradient(135deg, #0e1c2d 0%, #182739 100%);
    border: 1px solid var(--node-color, #315074);
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    padding: 12px;
    margin-bottom: -2px;
    z-index: 100;
    box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.3);

    .hover-content {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .hover-section {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      font-size: 11px;

      .hover-label {
        color: #8f97b7;
        font-weight: 500;
      }

      .hover-value {
        color: #e1e1e1;
        font-weight: 600;
        font-family: 'Roboto Mono', monospace;
      }

      .message-list {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 4px;

        .message-item {
          font-size: 10px;
          color: #8f97b7;
          padding: 2px 4px;
          background: rgba(49, 80, 116, 0.3);
          border-radius: 2px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
    }
  }

  :deep(.vue-flow-handle) {
    background: var(--node-color, #315074);
    border: 2px solid #0e1c2d;
    opacity: 0;
    transition: opacity 0.3s ease;

    &.connectable {
      background: var(--node-color, #315074);
    }
  }

  &:hover :deep(.vue-flow-handle) {
    opacity: 1;
  }
}

// Animations
@keyframes node-pulse {
  0%,
  100% {
    box-shadow:
      0 4px 12px rgba(0, 0, 0, 0.3),
      0 0 0 0 rgba(103, 189, 109, 0.4);
  }
  50% {
    box-shadow:
      0 4px 12px rgba(0, 0, 0, 0.3),
      0 0 0 8px rgba(103, 189, 109, 0);
  }
}

@keyframes status-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes status-error-pulse {
  0%,
  100% {
    box-shadow: 0 0 8px #c6298c;
  }
  50% {
    box-shadow: 0 0 16px #c6298c;
  }
}

@keyframes icon-pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(0.9);
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
