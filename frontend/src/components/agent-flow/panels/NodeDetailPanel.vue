<template>
  <div class="node-detail-panel">
    <div class="panel-header">
      <h3 class="panel-title">
        <v-icon :icon="node.data.icon" size="small" class="mr-2" />
        {{ node.data.label }}
      </h3>
      <v-btn icon size="x-small" variant="text" class="close-btn" @click="closePanel">
        <v-icon icon="mdi-close" size="small" />
      </v-btn>
    </div>

    <v-divider class="my-2" />

    <!-- Agent Information -->
    <div class="panel-section">
      <div class="section-title">Agent Information</div>
      <div class="info-item">
        <span class="label">ID</span>
        <span class="value mono">{{ node.data.agentId }}</span>
      </div>
      <div class="info-item">
        <span class="label">Role</span>
        <span class="value">{{ node.data.role || 'Agent' }}</span>
      </div>
      <div class="info-item">
        <span class="label">Status</span>
        <v-chip size="x-small" :color="getStatusColor(node.data.status)" variant="flat">
          {{ formatStatus(node.data.status) }}
        </v-chip>
      </div>
    </div>

    <v-divider class="my-2" />

    <!-- Performance Metrics -->
    <div class="panel-section">
      <div class="section-title">Performance</div>

      <div v-if="node.data.health !== undefined" class="metric-item">
        <div class="metric-header">
          <span class="metric-label">Health</span>
          <span class="metric-value">{{ node.data.health }}%</span>
        </div>
        <v-progress-linear
          :model-value="node.data.health"
          :color="node.data.health > 70 ? 'success' : 'warning'"
          height="6"
          rounded
        />
      </div>

      <div v-if="node.data.contextUsed !== undefined" class="metric-item">
        <div class="metric-header">
          <span class="metric-label">Context Usage</span>
          <span class="metric-value">{{ node.data.contextUsed }}%</span>
        </div>
        <v-progress-linear
          :model-value="node.data.contextUsed"
          :color="getContextColor(node.data.contextUsed)"
          height="6"
          rounded
        />
      </div>

      <div class="info-item">
        <span class="label">Active Jobs</span>
        <span class="value">{{ node.data.activeJobs || 0 }}</span>
      </div>

      <div class="info-item">
        <span class="label">Tokens Used</span>
        <span class="value mono">{{ formatNumber(node.data.tokens) }}</span>
      </div>

      <div class="info-item">
        <span class="label">Duration</span>
        <span class="value mono">{{ formatDuration(node.data.duration) }}</span>
      </div>
    </div>

    <v-divider class="my-2" />

    <!-- Messages -->
    <div class="panel-section">
      <div class="section-title d-flex align-center justify-space-between">
        <span>Messages</span>
        <v-chip size="x-small" variant="flat" color="primary">
          {{ node.data.messages?.length || 0 }}
        </v-chip>
      </div>

      <div v-if="node.data.messages && node.data.messages.length > 0" class="messages-list">
        <div
          v-for="msg in node.data.messages.slice(-10)"
          :key="msg.id"
          class="message-item"
          :class="{ 'is-error': msg.status === 'error' }"
        >
          <div class="message-header">
            <span class="message-status">{{ formatStatus(msg.status) }}</span>
            <span class="message-time">{{ formatTime(msg.createdAt) }}</span>
          </div>
          <div class="message-content">{{ truncate(msg.content, 50) }}</div>
        </div>
      </div>
      <div v-else class="empty-state">No messages</div>
    </div>

    <v-divider class="my-2" />

    <!-- Timestamps -->
    <div class="panel-section">
      <div class="section-title">Timeline</div>
      <div class="info-item">
        <span class="label">Created</span>
        <span class="value time">{{ formatFullTime(node.data.createdAt) }}</span>
      </div>
      <div class="info-item">
        <span class="label">Updated</span>
        <span class="value time">{{ formatFullTime(node.data.updatedAt) }}</span>
      </div>
    </div>

    <v-divider class="my-2" />

    <!-- Actions -->
    <div class="panel-section">
      <div class="section-title">Actions</div>
      <div class="actions-group">
        <v-btn small variant="outlined" color="primary" block class="action-btn">
          <v-icon icon="mdi-eye" size="small" class="mr-1" />
          View Details
        </v-btn>
        <v-btn small variant="outlined" color="secondary" block class="action-btn">
          <v-icon icon="mdi-message" size="small" class="mr-1" />
          Messages
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatDistanceToNow, format } from 'date-fns'

const props = defineProps({
  node: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['close'])

function closePanel() {
  emit('close')
}

function getStatusColor(status) {
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
}

function getContextColor(usage) {
  if (usage < 50) return 'success'
  if (usage < 70) return 'warning'
  if (usage < 85) return 'orange'
  return 'error'
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
.node-detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px;
    background: linear-gradient(135deg, #1e3147 0%, #182739 100%);

    .panel-title {
      display: flex;
      align-items: center;
      font-size: 14px;
      font-weight: 600;
      color: #e1e1e1;
      margin: 0;
    }

    .close-btn {
      transition: all 0.2s ease;

      &:hover {
        color: #ffc300;
      }
    }
  }

  .panel-section {
    padding: 12px;

    .section-title {
      font-size: 12px;
      font-weight: 700;
      color: #8f97b7;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 8px;
    }

    .info-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      padding: 6px 0;
      font-size: 12px;
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

        &.time {
          font-family: 'Roboto Mono', monospace;
          font-size: 11px;
        }
      }
    }

    .metric-item {
      margin-bottom: 12px;

      &:last-child {
        margin-bottom: 0;
      }

      .metric-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;

        .metric-label {
          font-size: 12px;
          color: #8f97b7;
          font-weight: 500;
        }

        .metric-value {
          font-size: 12px;
          color: #e1e1e1;
          font-weight: 600;
          font-family: 'Roboto Mono', monospace;
        }
      }
    }

    .messages-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      max-height: 200px;
      overflow-y: auto;

      .message-item {
        background: rgba(49, 80, 116, 0.2);
        border-left: 3px solid #67bd6d;
        padding: 8px;
        border-radius: 4px;
        font-size: 11px;

        &.is-error {
          border-left-color: #c6298c;
          background: rgba(198, 41, 140, 0.1);
        }

        .message-header {
          display: flex;
          justify-content: space-between;
          gap: 6px;
          margin-bottom: 4px;

          .message-status {
            font-weight: 600;
            color: #67bd6d;
            text-transform: capitalize;
          }

          .message-time {
            color: #8f97b7;
            font-family: 'Roboto Mono', monospace;
            font-size: 10px;
          }
        }

        .message-content {
          color: #e1e1e1;
          word-break: break-word;
        }
      }
    }

    .empty-state {
      text-align: center;
      padding: 16px 8px;
      color: #8f97b7;
      font-size: 12px;
    }

    .actions-group {
      display: flex;
      flex-direction: column;
      gap: 6px;

      .action-btn {
        font-size: 12px;
      }
    }
  }

  > :deep(.v-divider) {
    border-color: rgba(49, 80, 116, 0.3);
  }

  // Scrollbar styling
  ::-webkit-scrollbar {
    width: 6px;
  }

  ::-webkit-scrollbar-track {
    background: transparent;
  }

  ::-webkit-scrollbar-thumb {
    background: rgba(49, 80, 116, 0.5);
    border-radius: 3px;

    &:hover {
      background: rgba(49, 80, 116, 0.7);
    }
  }
}
</style>
