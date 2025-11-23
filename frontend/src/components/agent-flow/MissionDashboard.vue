<template>
  <v-card class="mission-dashboard" elevation="2">
    <!-- Header -->
    <v-card-title class="d-flex align-center justify-space-between">
      <div class="d-flex align-center">
        <v-icon icon="mdi-target" class="mr-2" color="primary" />
        <span>Mission Overview</span>
      </div>
      <v-chip
        v-if="mission"
        size="small"
        :color="getMissionStatusColor(mission.status)"
        variant="flat"
      >
        {{ formatStatus(mission.status) }}
      </v-chip>
    </v-card-title>

    <v-divider />

    <!-- Empty State -->
    <v-card-text v-if="!mission" class="empty-state">
      <v-icon icon="mdi-briefcase-outline" size="64" color="grey" />
      <p>No active mission</p>
    </v-card-text>

    <!-- Mission Content -->
    <div v-else>
      <!-- Mission Header -->
      <v-card-text class="mission-header">
        <h2 class="mission-title">{{ mission.title }}</h2>
        <p v-if="mission.description" class="mission-description">{{ mission.description }}</p>

        <!-- Quick Stats -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">Agents</div>
            <div class="stat-value">{{ mission.agents?.length || 0 }}</div>
          </div>

          <div class="stat-card">
            <div class="stat-label">Goals</div>
            <div class="stat-value">{{ mission.goals?.length || 0 }}</div>
          </div>

          <div v-if="mission.progress !== undefined" class="stat-card">
            <div class="stat-label">Progress</div>
            <div class="stat-value">{{ mission.progress }}%</div>
          </div>

          <div v-if="mission.completedSteps !== undefined" class="stat-card">
            <div class="stat-label">Steps</div>
            <div class="stat-value">
              {{ mission.completedSteps }} / {{ mission.currentStep || '?' }}
            </div>
          </div>
        </div>
      </v-card-text>

      <v-divider />

      <!-- Progress Bar -->
      <v-card-text v-if="mission.progress !== undefined" class="progress-section">
        <div class="progress-header">
          <span>Overall Progress</span>
          <span class="progress-value">{{ mission.progress }}%</span>
        </div>
        <v-progress-linear
          :model-value="mission.progress"
          height="12"
          rounded
          color="primary"
          striped
          class="progress-bar"
        />
      </v-card-text>

      <!-- Agents List -->
      <v-card-text v-if="mission.agents && mission.agents.length > 0" class="agents-section">
        <div class="section-title">Assigned Agents</div>
        <div class="agents-list">
          <div
            v-for="agentName in mission.agents"
            :key="agentName"
            class="agent-item"
            :class="{ 'is-active': isAgentActive(agentName) }"
          >
            <v-icon
              :icon="getAgentIcon(agentName)"
              size="small"
              :color="isAgentActive(agentName) ? 'success' : 'grey'"
              class="agent-icon"
            />
            <span class="agent-name">{{ agentName }}</span>
            <v-chip size="x-small" :color="getAgentStatusColor(agentName)" variant="flat">
              {{ getAgentStatus(agentName) }}
            </v-chip>
          </div>
        </div>
      </v-card-text>

      <!-- Goals -->
      <v-card-text v-if="mission.goals && mission.goals.length > 0" class="goals-section">
        <div class="section-title">Goals</div>
        <div class="goals-list">
          <div
            v-for="(goal, index) in mission.goals"
            :key="index"
            class="goal-item"
            :class="{ 'is-completed': goal.completed }"
          >
            <v-icon
              :icon="goal.completed ? 'mdi-check-circle' : 'mdi-circle-outline'"
              size="small"
              :color="goal.completed ? 'success' : 'grey'"
            />
            <span class="goal-text">{{ goal.title || goal }}</span>
          </div>
        </div>
      </v-card-text>

      <!-- Timeline -->
      <v-card-text v-if="mission.startedAt" class="timeline-section">
        <div class="section-title">Timeline</div>
        <div class="timeline-info">
          <div class="timeline-item">
            <span class="label">Started</span>
            <span class="value">{{ formatTime(mission.startedAt) }}</span>
          </div>

          <div v-if="mission.completedAt" class="timeline-item">
            <span class="label">Completed</span>
            <span class="value">{{ formatTime(mission.completedAt) }}</span>
          </div>

          <div v-if="mission.duration" class="timeline-item">
            <span class="label">Duration</span>
            <span class="value">{{ formatDuration(mission.duration) }}</span>
          </div>
        </div>
      </v-card-text>

      <!-- Error Message -->
      <v-card-text v-if="mission.status === 'failed' && mission.error" class="error-section">
        <div class="section-title">Error</div>
        <div class="error-message">
          <v-icon icon="mdi-alert-circle" color="error" class="mr-2" size="small" />
          {{ mission.error }}
        </div>
      </v-card-text>

      <!-- Actions -->
      <v-card-text class="actions-section">
        <div class="section-title">Actions</div>
        <div class="actions-group">
          <v-btn
            v-if="mission.status === 'active'"
            size="small"
            variant="outlined"
            color="primary"
            block
            class="action-btn"
          >
            <v-icon icon="mdi-pause" size="small" class="mr-1" />
            Pause Mission
          </v-btn>

          <v-btn
            v-else-if="mission.status === 'paused'"
            size="small"
            variant="outlined"
            color="success"
            block
            class="action-btn"
          >
            <v-icon icon="mdi-play" size="small" class="mr-1" />
            Resume Mission
          </v-btn>

          <v-btn size="small" variant="outlined" color="error" block class="action-btn">
            <v-icon icon="mdi-stop" size="small" class="mr-1" />
            Stop Mission
          </v-btn>
        </div>
      </v-card-text>
    </div>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'
import { useAgentFlowStore } from '@/stores/agentFlow'
import { formatDistanceToNow, format, differenceInSeconds } from 'date-fns'

const flowStore = useAgentFlowStore()

const mission = computed(() => flowStore.missionData)

function getMissionStatusColor(status) {
  const statusColorMap = {
    active: 'success',
    paused: 'warning',
    completed: 'secondary',
    failed: 'error',
  }
  return statusColorMap[status] || 'grey'
}

function formatStatus(status) {
  if (!status) return 'Unknown'
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function isAgentActive(agentName) {
  const agentNode = flowStore.nodes.find((n) => n.data.agentName === agentName)
  return agentNode && (agentNode.data.status === 'active' || agentNode.data.status === 'running')
}

function getAgentIcon(agentName) {
  const lowerName = agentName.toLowerCase()
  if (lowerName.includes('designer')) return 'mdi-palette'
  if (lowerName.includes('developer')) return 'mdi-code-tags'
  if (lowerName.includes('tester')) return 'mdi-test-tube'
  if (lowerName.includes('implementer')) return 'mdi-hammer'
  if (lowerName.includes('orchestrator')) return 'mdi-account-supervisor'
  return 'mdi-robot'
}

function getAgentStatus(agentName) {
  const agentNode = flowStore.nodes.find((n) => n.data.agentName === agentName)
  return agentNode?.data?.status || 'unknown'
}

function getAgentStatusColor(agentName) {
  const status = getAgentStatus(agentName)
  const statusColorMap = {
    active: 'success',
    running: 'success',
    waiting: 'warning',
    pending: 'info',
    completed: 'secondary',
    complete: 'secondary',
    error: 'error',
  }
  return statusColorMap[status] || 'grey'
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
</script>

<style scoped lang="scss">
.mission-dashboard {
  background: #182739;

  :deep(.v-card-title) {
    padding: 12px 16px;
    background: linear-gradient(135deg, #1e3147 0%, #182739 100%);
    border-bottom: 1px solid #315074;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 300px;
    color: #8f97b7;

    p {
      margin-top: 12px;
    }
  }

  :deep(.v-card-text) {
    padding: 16px;
  }

  .mission-header {
    .mission-title {
      font-size: 20px;
      font-weight: 700;
      color: #e1e1e1;
      margin: 0 0 8px 0;
    }

    .mission-description {
      color: #8f97b7;
      font-size: 13px;
      margin: 0 0 16px 0;
      line-height: 1.4;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 12px;

      .stat-card {
        background: rgba(49, 80, 116, 0.2);
        border: 1px solid rgba(49, 80, 116, 0.3);
        border-radius: 6px;
        padding: 12px;
        text-align: center;

        .stat-label {
          font-size: 11px;
          color: #8f97b7;
          font-weight: 500;
          margin-bottom: 4px;
        }

        .stat-value {
          font-size: 24px;
          font-weight: 700;
          color: #e1e1e1;
          font-family: 'Roboto Mono', monospace;
        }
      }
    }
  }

  .progress-section {
    .progress-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      font-size: 12px;

      .progress-value {
        color: #e1e1e1;
        font-weight: 600;
        font-family: 'Roboto Mono', monospace;
      }
    }

    .progress-bar {
      background: rgba(49, 80, 116, 0.3);
    }
  }

  .agents-section,
  .goals-section,
  .timeline-section,
  .error-section,
  .actions-section {
    .section-title {
      font-size: 12px;
      font-weight: 700;
      color: #8f97b7;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 12px;
    }
  }

  .agents-list {
    display: flex;
    flex-direction: column;
    gap: 8px;

    .agent-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px;
      background: rgba(49, 80, 116, 0.15);
      border-radius: 6px;
      border-left: 3px solid #315074;
      transition: all 0.2s ease;

      &.is-active {
        border-left-color: #67bd6d;
        background: rgba(103, 189, 109, 0.05);
      }

      .agent-icon {
        flex-shrink: 0;
      }

      .agent-name {
        flex: 1;
        font-size: 13px;
        font-weight: 500;
        color: #e1e1e1;
      }
    }
  }

  .goals-list {
    display: flex;
    flex-direction: column;
    gap: 8px;

    .goal-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px;
      background: rgba(49, 80, 116, 0.15);
      border-radius: 6px;
      transition: all 0.2s ease;

      &.is-completed {
        background: rgba(103, 189, 109, 0.1);
        opacity: 0.7;
      }

      .goal-text {
        font-size: 13px;
        color: #e1e1e1;
      }
    }
  }

  .timeline-info {
    display: flex;
    flex-direction: column;
    gap: 8px;

    .timeline-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid rgba(49, 80, 116, 0.3);

      &:last-child {
        border-bottom: none;
      }

      .label {
        font-size: 12px;
        color: #8f97b7;
        font-weight: 500;
      }

      .value {
        font-size: 13px;
        color: #e1e1e1;
        font-weight: 600;
        font-family: 'Roboto Mono', monospace;
      }
    }
  }

  .error-section {
    .error-message {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      color: #c6298c;
      font-size: 12px;
      padding: 12px;
      background: rgba(198, 41, 140, 0.1);
      border-left: 3px solid #c6298c;
      border-radius: 4px;
      line-height: 1.4;
    }
  }

  .actions-section {
    .actions-group {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .action-btn {
        font-size: 12px;
      }
    }
  }

  > :deep(.v-divider) {
    border-color: rgba(49, 80, 116, 0.3);
  }
}
</style>
