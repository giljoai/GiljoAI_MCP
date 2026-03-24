<template>
  <div class="launch-tab-wrapper">
    <!-- Main Container (unified border) - buttons moved to ProjectTabs -->
    <div class="main-container">
      <div class="three-panels">
        <!-- Panel 1: Project Description -->
        <div class="panel project-description-panel" data-testid="description-panel">
          <div class="panel-header">
            <span>Project Description</span>
            <div class="header-actions">
              <v-btn
                icon="mdi-pencil"
                size="x-small"
                variant="text"
                class="header-edit-btn"
                title="Edit description"
                aria-label="Edit description"
                @click="editDescription"
              />
              <AgentTipsDialog />
            </div>
          </div>
          <div class="panel-content">
            <p class="description-text">{{ project.description || 'No description available' }}</p>
          </div>
        </div>

        <!-- Panel 2: Orchestrator Mission -->
        <div class="panel mission-panel" data-testid="mission-panel">
          <div class="panel-header">Orchestrator Generated Mission</div>
          <div class="panel-content">
            <div v-if="!missionText" class="empty-state">
              <v-icon size="80" class="empty-icon">mdi-file-document-outline</v-icon>
            </div>
            <div v-else class="mission-content">
              {{ missionText }}
            </div>
          </div>
        </div>

        <!-- Panel 3: Agents -->
        <div class="panel agents-panel" data-testid="agents-panel">
          <div class="panel-header">
            <span>Agents</span>
            <div class="integration-icons">
              <!-- GitHub Integration -->
              <v-tooltip location="bottom" max-width="300">
                <template #activator="{ props: tooltipProps }">
                  <v-icon
                    v-bind="tooltipProps"
                    :class="{ 'icon-disabled': !gitEnabled }"
                    size="48"
                    color="white"
                    data-testid="github-status-icon"
                    style="cursor: pointer;"
                    aria-label="GitHub integration status"
                    @click="goToIntegrations"
                  >
                    mdi-github
                  </v-icon>
                </template>
                <span v-if="gitEnabled">GitHub integration enabled. Commit history will be included in project summaries.</span>
                <span v-else>GitHub integration disabled. Click to enable in Settings.</span>
              </v-tooltip>
              <!-- Serena MCP Integration -->
              <v-tooltip location="bottom" max-width="300">
                <template #activator="{ props: tooltipProps }">
                  <v-img
                    v-bind="tooltipProps"
                    src="/Serena.png"
                    width="48"
                    height="48"
                    :class="{ 'icon-disabled': !serenaEnabled }"
                    data-testid="serena-status-icon"
                    style="cursor: pointer;"
                    alt="Serena MCP integration status"
                    aria-label="Serena MCP integration status"
                    @click="goToIntegrations"
                  />
                </template>
                <span v-if="serenaEnabled">Serena MCP enabled. Agents will use semantic code navigation.</span>
                <span v-else>Serena MCP disabled. Click to enable in Settings.</span>
              </v-tooltip>
            </div>
          </div>
          <div class="panel-content">
            <div class="agents-list">
              <!-- All agents shown together -->
              <div
                v-for="agent in sortedJobs"
                :key="agent.job_id || agent.agent_id || agent.id"
                class="agent-slim-card"
                :class="{ 'orchestrator-card': agent.agent_display_name === 'orchestrator' }"
                data-testid="agent-card"
                :data-agent-display-name="agent.agent_display_name"
                style="cursor: pointer;"
                @click="handleAgentInfo(agent)"
              >
                <div class="agent-avatar" :style="{ background: getAgentColor(agent.agent_name || agent.agent_display_name) }">
                  {{ getAgentInitials(agent.agent_display_name) }}
                </div>
                <div class="agent-info">
                  <span class="agent-name" data-testid="agent-name">{{ agent.agent_display_name?.toUpperCase() || '' }}</span>
                  <div class="text-caption text-medium-emphasis">
                    <span class="status-text" :class="'status-' + agent.status">
                      {{ agent.status }}
                    </span>
                    <v-tooltip v-if="agent.agent_id || agent.job_id" location="top">
                      <template #activator="{ props: tooltipProps }">
                        <span
                          v-bind="tooltipProps"
                          class="agent-id-link"
                          @click.stop
                        >
                          • ID: {{ (agent.agent_id || agent.job_id || '').slice(0, 8) }}...
                        </span>
                      </template>
                      <span>{{ agent.agent_id || agent.job_id }}</span>
                    </v-tooltip>
                  </div>
                </div>
                <span class="agent-type" data-testid="agent-display-name" style="display: none;">{{ agent.agent_display_name || '' }}</span>
                <span class="status-chip" data-testid="status-chip" style="display: none;">{{ agent.status || 'pending' }}</span>
                <v-icon
                  size="small"
                  class="edit-icon"
                  role="button"
                  tabindex="0"
                  title="Edit agent configuration"
                  aria-label="Edit agent configuration"
                  @click.stop="handleAgentEdit(agent)"
                  @keydown.enter="handleAgentEdit(agent)"
                >mdi-pencil</v-icon>
                <v-icon
                  size="small"
                  class="info-icon"
                  role="button"
                  tabindex="0"
                  title="View agent details"
                  aria-label="View agent details"
                  @click.stop="handleAgentInfo(agent)"
                  @keydown.enter="handleAgentInfo(agent)"
                >mdi-eye</v-icon>
              </div>
              <!-- Empty state when no agents -->
              <div v-if="!sortedJobs || sortedJobs.length === 0" class="empty-agents">
                <v-icon size="48" class="empty-icon">mdi-account-group-outline</v-icon>
                <p class="text-caption text-medium-emphasis">No agents yet - click Stage Project to begin</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Agent Details Modal -->
    <AgentDetailsModal
      v-model="showDetailsModal"
      :agent="selectedAgent"
    />

    <!-- Agent Mission Edit Modal -->
    <AgentMissionEditModal
      v-model="showMissionEditModal"
      :agent="selectedAgentForEdit"
      @mission-updated="handleMissionUpdated"
    />

  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { useAgentJobs } from '@/composables/useAgentJobs'
import { useAgentJobsStore } from '@/stores/agentJobsStore'
import { useProjectStateStore } from '@/stores/projectStateStore'
import AgentDetailsModal from '@/components/projects/AgentDetailsModal.vue'
import AgentMissionEditModal from '@/components/projects/AgentMissionEditModal.vue'
import AgentTipsDialog from '@/components/common/AgentTipsDialog.vue'
import { getAgentColor as getAgentColorConfig } from '@/config/agentColors'

/**
 * LaunchTab Component - Complete Rewrite (Handover 0241)
 * Execution Mode Toggle moved to ProjectTabs (Handover 0428)
 *
 * Exact match to screenshot design:
 * - Main container with unified border and rounded corners
 * - Three equal panels: Project Description, Orchestrator Mission, Default Agent
 * - Dark navy background, tan orchestrator avatar, yellow buttons
 */

const props = defineProps({
  project: {
    type: Object,
    required: true,
    validator: (value) => {
      return value && typeof value === 'object' && ('id' in value || 'project_id' in value)
    },
  },
  orchestrator: {
    type: Object,
    default: null,
  },
  isStaging: {
    type: Boolean,
    default: false,
  },
  gitEnabled: {
    type: Boolean,
    default: false,
  },
  serenaEnabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits([
  'edit-description',
])

/**
 * Project ID from props
 */
const projectId = computed(() => {
  const id = props.project?.project_id || props.project?.id
  if (!id) {
    console.error('[LaunchTab] Project missing ID field')
    throw new Error('Invalid project: missing ID')
  }
  return id
})

/**
 * Get agent color based on type
 */
const getAgentColor = (displayName) => {
  return getAgentColorConfig(displayName).hex
}

/**
 * Get agent initials - uses word initials
 * Split by dash, space, or underscore and use first letter of each part
 * e.g., "Backend-Implementer" → "BI", "Backend-Tester" → "BT"
 */
const getAgentInitials = (displayName) => {
  if (!displayName) return '??'

  // Split by dash, space, or underscore
  const parts = displayName.split(/[-_\s]+/).filter(Boolean)

  if (parts.length >= 2) {
    // Use first letter of first two parts: "Backend-Implementer" → "BI"
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }

  // Single word fallback: use first two letters
  return displayName.substring(0, 2).toUpperCase()
}

const router = useRouter()

/**
 * Navigate to integrations settings
 */
function goToIntegrations() {
  router.push({ path: '/settings', query: { tab: 'integrations' } })
}

const projectStateStore = useProjectStateStore()
const missionText = computed(
  () => projectStateStore.getProjectState(projectId.value)?.mission || '',
)

const { sortedJobs } = useAgentJobs()
const agentJobsStore = useAgentJobsStore()

/**
 * Component State
 */
const { showToast } = useToast()
const showDetailsModal = ref(false)
const selectedAgent = ref(null)
const showMissionEditModal = ref(false)
const selectedAgentForEdit = ref(null)

/**
 * Handle Edit Description button
 */
function editDescription() {
  emit('edit-description')
}

/**
 * Handle Info icon click for Agent Team members
 */
function handleAgentInfo(agent) {
  selectedAgent.value = {
    ...agent,
    id: agent.id || agent.job_id,
  }
  showDetailsModal.value = true
}

/**
 * Handle Edit icon click for Agent Team members
 */
function handleAgentEdit(agent) {
  if (agent.agent_display_name === 'orchestrator') {
    // Orchestrators don't have editable missions
    showToast({ message: 'Orchestrator configuration cannot be edited here', type: 'info' })
    return
  }

  selectedAgentForEdit.value = agent
  showMissionEditModal.value = true
}

/**
 * Handle mission updated event from modal
 */
function handleMissionUpdated({ jobId, mission }) {
  agentJobsStore.upsertJob?.({ job_id: jobId, mission })

  showToast({ message: 'Agent mission updated successfully', type: 'success' })
}

/**
 * Watchers
 */
watch(missionText, (next, previous) => {
  if (next && !previous) {
    showToast({ message: 'Mission generated', type: 'success' })
  }
})
</script>

<style scoped lang="scss">
@use '@/styles/design-tokens.scss' as *;

.launch-tab-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
  background: transparent; /* Already inside bordered box */

  .main-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0; /* Critical for flex overflow */
    /* No border - already inside bordered content box */

    .three-panels {
      flex: 1;
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: $spacing-panel-gap;
      min-height: 0; /* Critical for grid overflow */

      .panel {
        display: flex;
        flex-direction: column;
        min-height: 0; /* Critical for flex overflow */

        .panel-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: $typography-panel-header-size;
          color: rgba(var(--v-theme-on-surface), 0.6);
          height: 28px; /* Fixed height so all headers align */
          margin-bottom: 16px;
          font-weight: $typography-font-weight-bold;
          text-transform: capitalize;
          flex-shrink: 0;

          .header-actions {
            display: flex;
            align-items: center;
            margin-left: 4px;
          }

          .header-edit-btn {
            color: white;
            margin-left: 4px;
            height: 32px;
            width: 32px;

            &:hover {
              color: rgb(var(--v-theme-primary));
            }
          }

          .integration-icons {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-left: auto;

            .v-icon, .v-img {
              opacity: 0.8;
              transition: opacity 0.2s ease;
              border: 2px solid white;
              border-radius: 50%;
              padding: 4px;

              &:hover {
                opacity: 1;
              }

              &.icon-disabled {
                opacity: 0.3;
              }
            }
          }
        }

        .panel-content {
          background: rgba(var(--v-theme-on-surface), 0.05);
          border-radius: $radius-medium;
          padding: $spacing-panel-content-padding;
          height: 550px; /* Fixed height for uniform panels */
          position: relative;
          color: rgb(var(--v-theme-on-surface));
          font-size: $typography-panel-content-size;
          line-height: 1.6;
          overflow-y: auto; /* Each panel scrolls independently */

          /* Custom Scrollbar for all panels */
          &::-webkit-scrollbar {
            width: 8px;
          }

          &::-webkit-scrollbar-track {
            background: $color-scrollbar-track-background;
            border-radius: $radius-scrollbar;
          }

          &::-webkit-scrollbar-thumb {
            background: $color-scrollbar-thumb-background;
            border-radius: $radius-scrollbar;

            &:hover {
              background: $color-scrollbar-thumb-hover-background;
            }
          }

          /* Firefox scrollbar */
          scrollbar-color: $color-scrollbar-thumb-background $color-scrollbar-track-background;
          scrollbar-width: thin;

          .empty-state {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);

            .empty-icon {
              color: rgba(var(--v-theme-on-surface), 0.15);
            }
          }

          .mission-content {
            white-space: pre-wrap;
            word-break: break-word;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.875rem;
          }

          .description-text {
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
          }
        }
      }
    }
  }

  /* Unified Agents List */
  .agents-list {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .empty-agents {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 32px;
      text-align: center;

      .empty-icon {
        color: rgba(var(--v-theme-on-surface), 0.15);
        margin-bottom: 8px;
      }
    }
  }

  /* Agent card - unified style for all agents */
  .agent-slim-card {
    display: flex;
    align-items: center;
    gap: 12px;
    border: 2px solid rgb(var(--v-theme-primary));
    border-radius: $border-radius-pill;
    padding: 10px 16px;
    background: transparent;

    /* Orchestrator gets green border */
    &.orchestrator-card {
      border-color: rgb(var(--v-theme-success));
    }

    .agent-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: $typography-font-weight-bold;
      font-size: 13px;
      flex-shrink: 0;
    }

    .agent-info {
      flex: 1;
      min-width: 0;

      .agent-name {
        color: rgb(var(--v-theme-on-surface));
        font-size: $typography-font-size-body;
        font-weight: 500;
      }
    }

    .status-text {
      text-transform: capitalize;
      font-weight: 500;

      &.status-waiting { color: rgb(var(--v-theme-highlight)); }
      &.status-working { color: var(--agent-orchestrator-primary); }
      &.status-complete { color: rgb(var(--v-theme-success)); }
      &.status-handed_over { color: rgb(var(--v-theme-on-surface-variant)); }
      &.status-blocked { color: var(--status-blocked); }
      &.status-silent { color: var(--status-blocked); }
      &.status-pending { color: var(--status-waiting); }
    }

    .agent-id-link {
      cursor: pointer;
      text-decoration: underline;
      text-decoration-style: dotted;

      &:hover {
        color: rgb(var(--v-theme-primary));
      }
    }

    &:hover {
      background: rgba(var(--v-theme-on-surface), 0.05);
    }

    .edit-icon,
    .info-icon {
      color: rgba(var(--v-theme-on-surface), 0.6);
      flex-shrink: 0;
      cursor: pointer;
      transition: color 0.2s ease;

      &:hover {
        color: $color-text-highlight;
      }
    }

    .edit-icon {
      margin-right: 4px;
    }
  }

}
</style>
