<template>
  <div class="edge-detail-panel">
    <div class="panel-header">
      <h3 class="panel-title">
        <v-icon icon="mdi-connection" size="small" class="mr-2" />
        Message Channel
      </h3>
      <v-btn icon size="x-small" variant="text" class="close-btn" @click="closePanel">
        <v-icon icon="mdi-close" size="small" />
      </v-btn>
    </div>

    <v-divider class="my-2" />

    <!-- Channel Information -->
    <div class="panel-section">
      <div class="section-title">Channel Info</div>
      <div class="info-item">
        <span class="label">From</span>
        <span class="value">{{ getNodeLabel(edge.source) }}</span>
      </div>
      <div class="info-item">
        <span class="label">To</span>
        <span class="value">{{ getNodeLabel(edge.target) }}</span>
      </div>
      <div class="info-item">
        <span class="label">Messages</span>
        <v-chip size="x-small" variant="flat" color="primary">
          {{ edge.data?.messageCount || 0 }}
        </v-chip>
      </div>
      <div class="info-item">
        <span class="label">Status</span>
        <v-chip size="x-small" :color="edge.data?.animated ? 'success' : 'grey'" variant="flat">
          {{ edge.data?.animated ? 'Active' : 'Idle' }}
        </v-chip>
      </div>
    </div>

    <v-divider class="my-2" />

    <!-- Message Flow -->
    <div class="panel-section">
      <div class="section-title d-flex align-center justify-space-between">
        <span>Message Flow</span>
        <v-chip size="x-small" variant="flat">{{ messages.length }}</v-chip>
      </div>

      <div v-if="messages.length > 0" class="messages-flow">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="flow-message"
          :class="{ 'is-pending': msg.status === 'pending' }"
        >
          <div class="flow-message-header">
            <span class="message-id">{{ truncate(msg.id, 12) }}</span>
            <span class="message-status">{{ formatStatus(msg.status) }}</span>
            <span class="message-time">{{ formatTime(msg.createdAt) }}</span>
          </div>

          <div class="flow-message-content">
            <p class="message-preview">{{ truncate(msg.content, 60) }}</p>
          </div>

          <div
            v-if="msg.acknowledged_by && msg.acknowledged_by.length > 0"
            class="flow-message-acks"
          >
            <v-chip
              v-for="agent in msg.acknowledged_by"
              :key="agent"
              size="x-small"
              variant="flat"
              color="success"
              class="ack-chip"
            >
              <v-icon icon="mdi-check-circle" size="x-small" class="mr-1" />
              {{ truncate(agent, 10) }}
            </v-chip>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">No messages in this channel</div>
    </div>

    <v-divider class="my-2" />

    <!-- Statistics -->
    <div class="panel-section">
      <div class="section-title">Statistics</div>

      <div class="stat-row">
        <span class="stat-label">Total Messages</span>
        <span class="stat-value">{{ stats.total }}</span>
      </div>

      <div class="stat-row">
        <span class="stat-label">Completed</span>
        <span class="stat-value">{{ stats.completed }}</span>
      </div>

      <div class="stat-row">
        <span class="stat-label">Acknowledged</span>
        <span class="stat-value">{{ stats.acknowledged }}</span>
      </div>

      <div class="stat-row">
        <span class="stat-label">Pending</span>
        <span class="stat-value error">{{ stats.pending }}</span>
      </div>

      <div class="stat-row">
        <span class="stat-label">Success Rate</span>
        <span class="stat-value success">{{ stats.successRate }}%</span>
      </div>
    </div>

    <v-divider class="my-2" />

    <!-- Actions -->
    <div class="panel-section">
      <div class="section-title">Actions</div>
      <div class="actions-group">
        <v-btn small variant="outlined" color="primary" block class="action-btn">
          <v-icon icon="mdi-eye" size="small" class="mr-1" />
          View All Messages
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAgentFlowStore } from '@/stores/agentFlow'
import { formatDistanceToNow, format } from 'date-fns'

const props = defineProps({
  edge: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['close'])

const flowStore = useAgentFlowStore()

const messages = computed(() => props.edge.data?.messages || [])

const stats = computed(() => {
  const total = messages.value.length
  const completed = messages.value.filter((m) => m.status === 'completed').length
  const acknowledged = messages.value.filter((m) => m.acknowledged_by?.length > 0).length
  const pending = messages.value.filter((m) => m.status === 'pending').length
  const successRate = total === 0 ? 0 : Math.round(((completed + acknowledged) / total) * 100)

  return {
    total,
    completed,
    acknowledged,
    pending,
    successRate,
  }
})

function closePanel() {
  emit('close')
}

function getNodeLabel(nodeId) {
  const node = flowStore.nodes.find((n) => n.id === nodeId)
  return node?.data?.label || nodeId
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

function truncate(str, length) {
  if (!str) return ''
  return str.length > length ? str.substring(0, length) + '...' : str
}
</script>

<style scoped lang="scss">
.edge-detail-panel {
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
    overflow-y: auto;

    &:last-child {
      border-bottom: none;
    }

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
      }
    }

    .messages-flow {
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: 300px;
      overflow-y: auto;

      .flow-message {
        background: rgba(49, 80, 116, 0.2);
        border-left: 3px solid #315074;
        border-radius: 4px;
        padding: 8px;
        font-size: 11px;
        transition: all 0.2s ease;

        &.is-pending {
          border-left-color: #ffc300;
          background: rgba(255, 195, 0, 0.05);
          animation: pending-pulse 1.5s ease-in-out infinite;
        }

        &:hover {
          background: rgba(49, 80, 116, 0.3);
        }

        .flow-message-header {
          display: flex;
          justify-content: space-between;
          gap: 6px;
          margin-bottom: 4px;
          flex-wrap: wrap;

          .message-id {
            font-family: 'Roboto Mono', monospace;
            color: #8f97b7;
            font-size: 10px;
          }

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

        .flow-message-content {
          margin-bottom: 6px;

          .message-preview {
            margin: 0;
            color: #e1e1e1;
            word-break: break-word;
            line-height: 1.3;
          }
        }

        .flow-message-acks {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;

          .ack-chip {
            font-size: 10px !important;
          }
        }
      }
    }

    .empty-state {
      text-align: center;
      padding: 16px 8px;
      color: #8f97b7;
      font-size: 12px;
    }

    .stat-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid rgba(49, 80, 116, 0.3);
      font-size: 12px;

      &:last-child {
        border-bottom: none;
      }

      .stat-label {
        color: #8f97b7;
        font-weight: 500;
      }

      .stat-value {
        color: #e1e1e1;
        font-weight: 600;
        font-family: 'Roboto Mono', monospace;

        &.success {
          color: #67bd6d;
        }

        &.error {
          color: #c6298c;
        }
      }
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

@keyframes pending-pulse {
  0%,
  100% {
    background: rgba(255, 195, 0, 0.05);
  }
  50% {
    background: rgba(255, 195, 0, 0.15);
  }
}
</style>
