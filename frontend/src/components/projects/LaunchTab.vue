<template>
  <div class="launch-tab-wrapper">
    <!-- 3-column grid: Description | Mission | Agents -->
    <div class="content-grid">
      <!-- Description Card -->
      <div class="content-card smooth-border" data-testid="description-panel">
        <div class="section-label">
          <span>Project Description</span>
          <div class="header-actions">
            <v-btn
              icon="mdi-pencil"
              size="x-small"
              variant="text"
              class="header-edit-btn icon-interactive"
              title="Edit description"
              aria-label="Edit description"
              @click="editDescription"
            />
            <AgentTipsDialog />
          </div>
        </div>
        <div class="card-body scrollbar-standard">
          <p class="description-text">{{ project.description || 'No description available' }}</p>
        </div>
      </div>

      <!-- Mission Card -->
      <div class="content-card smooth-border" data-testid="mission-panel">
        <div class="section-label">Orchestrator Generated Mission</div>
        <div class="card-body scrollbar-standard">
          <EmptyState
            v-if="!missionText"
            icon="mdi-file-document-outline"
            title="No mission generated"
          />
          <div v-else class="mission-content">
            {{ missionText }}
          </div>
        </div>
      </div>

      <!-- Agents Column (bare, no card) -->
      <div class="agents-column" data-testid="agents-panel">
        <!-- Integration icons -->
        <div class="integrations-row">
      <!-- GitHub Integration -->
      <v-tooltip location="bottom" max-width="300">
        <template #activator="{ props: tooltipProps }">
          <v-icon
            v-bind="tooltipProps"
            :class="{ 'icon-disabled': !gitEnabled }"
            size="36"
            color="white"
            data-testid="github-status-icon"
            class="cursor-pointer integration-icon"
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
            width="36"
            height="36"
            :class="{ 'icon-disabled': !serenaEnabled }"
            data-testid="serena-status-icon"
            class="cursor-pointer integration-icon"
            alt="Serena MCP integration status"
            aria-label="Serena MCP integration status"
            @click="goToIntegrations"
          />
        </template>
        <span v-if="serenaEnabled">Serena MCP enabled. Agents will use semantic code navigation.</span>
        <span v-else>Serena MCP disabled. Click to enable in Settings.</span>
      </v-tooltip>
      <!-- Agentic Tool Badge -->
      <v-tooltip v-if="agenticTool" location="bottom" max-width="300">
        <template #activator="{ props: tooltipProps }">
          <v-icon
            v-if="agenticTool.type === 'icon'"
            v-bind="tooltipProps"
            size="36"
            color="primary"
            data-testid="agentic-tool-icon"
            class="cursor-pointer integration-icon"
            :aria-label="agenticTool.alt"
            @click="goToIntegrations"
          >
            {{ agenticTool.icon }}
          </v-icon>
          <v-img
            v-else
            v-bind="tooltipProps"
            :src="agenticTool.src"
            width="36"
            height="36"
            data-testid="agentic-tool-icon"
            class="cursor-pointer integration-icon"
            :alt="agenticTool.alt"
            :aria-label="agenticTool.alt"
            @click="goToIntegrations"
          />
        </template>
        <span>{{ agenticTool.label }} mode active.</span>
      </v-tooltip>
        </div>

        <!-- Agents label -->
        <div class="section-label section-label--standalone">Agents</div>

        <!-- Agents list (bare, no card wrapper) -->
        <div class="agents-list">
      <!-- All agents shown together -->
      <div
        v-for="agent in sortedJobs"
        :key="agent.job_id || agent.agent_id || agent.id"
        class="agent-slim-card"
        data-testid="agent-card"
        :data-agent-display-name="agent.agent_display_name"
        @click="handleAgentInfo(agent)"
      >
        <div class="agent-badge" :style="getAgentBadgeStyle(agent.agent_name || agent.agent_display_name)">
          {{ getAgentInitials(agent.agent_display_name) }}
        </div>
        <div class="agent-info">
          <span class="agent-name" data-testid="agent-name">{{ agent.agent_display_name?.toUpperCase() || '' }}</span>
          <div class="text-caption agent-meta">
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
          v-if="agent.agent_display_name !== 'orchestrator'"
          size="small"
          class="icon-interactive mr-1"
          role="button"
          tabindex="0"
          title="Edit agent configuration"
          aria-label="Edit agent configuration"
          @click.stop="handleAgentEdit(agent)"
          @keydown.enter="handleAgentEdit(agent)"
        >mdi-pencil</v-icon>
        <v-icon
          size="small"
          class="icon-interactive"
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
        <p class="text-caption text-muted-a11y">No agents yet - click Stage Project to begin</p>
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
import EmptyState from '@/components/common/EmptyState.vue'
import { getAgentColor as getAgentColorConfig } from '@/config/agentColors'
import { hexToRgba, getAgentBadgeStyle } from '@/utils/colorUtils'

/**
 * LaunchTab Component - Complete Rewrite (Handover 0241)
 * Execution Mode Toggle moved to ProjectTabs (Handover 0428)
 * Flattened layout (Handover 0873): 2-col grid for cards, bare agents list
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
 * Active agentic tool based on project execution_mode
 */
const agenticTool = computed(() => {
  const mode = props.project?.execution_mode
  if (mode === 'claude_code_cli') return { type: 'img', src: '/claude_pix.svg', label: 'Claude Code', alt: 'Claude Code subagent active' }
  if (mode === 'codex_cli') return { type: 'img', src: '/codex_logo.svg', label: 'Codex CLI', alt: 'Codex CLI subagent active' }
  if (mode === 'gemini_cli') return { type: 'img', src: '/gemini-icon.svg', label: 'Gemini CLI', alt: 'Gemini CLI subagent active' }
  if (mode === 'multi_terminal') return { type: 'icon', icon: 'mdi-monitor-multiple', label: 'Multi Terminal', alt: 'Multi terminal mode active' }
  return null
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
 * e.g., "Backend-Implementer" -> "BI", "Backend-Tester" -> "BT"
 */
const getAgentInitials = (displayName) => {
  if (!displayName) return '??'

  // Split by dash, space, or underscore
  const parts = displayName.split(/[-_\s]+/).filter(Boolean)

  if (parts.length >= 2) {
    // Use first letter of first two parts: "Backend-Implementer" -> "BI"
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
    showToast({ message: 'Agent mission generated', type: 'success' })
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
  background: transparent;
}

/* Two-column grid for Description + Mission cards */
.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

/* Agents column (bare, no card frame) */
.agents-column {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* Individual content cards (Description, Mission) */
.content-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: $elevation-raised;
  border-radius: $border-radius-rounded;
  padding: 20px;

  .card-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    font-size: 0.8rem;
    line-height: 1.5;
    color: $color-text-primary;
    margin-top: 12px;

    .mission-content {
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 0.78rem;
      line-height: 1.5;
      color: $color-text-secondary;
      font-style: italic;
    }

    .description-text {
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }
  }
}

/* Section label — IBM Plex Mono uppercase (matches integrations page) */
.section-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.62rem;
  color: $color-text-muted;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;

  .header-actions {
    display: flex;
    align-items: center;
    gap: 2px;
  }

  .header-edit-btn {
    width: 26px;
    height: 26px;
  }

  &--standalone {
    margin-bottom: 8px;
  }
}

/* Integration icons row (bare, no frame) */
.integrations-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;

  .integration-icon {
    opacity: 1;
    transition: opacity $transition-normal ease;
    object-fit: contain;

    &.icon-disabled {
      opacity: 0.3;

      &:hover {
        opacity: 0.5;
      }
    }
  }
}

/* Agents List — bare, no background/border/shadow */
.agents-list {
  display: flex;
  flex-direction: column;
  gap: 4px;

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

/* Agent card — tinted square badge pattern (0870j) */
.agent-slim-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: $border-radius-default;
  background: transparent;
  border: none;
  transition: background $transition-fast;
  cursor: pointer;

  &:hover {
    background: rgba(255, 255, 255, 0.03);
  }

  .agent-badge {
    width: 36px;
    height: 36px;
    border-radius: $border-radius-default;
    display: grid;
    place-items: center;
    font-size: 0.7rem;
    font-weight: 700;
    flex-shrink: 0;
  }

  .agent-info {
    flex: 1;
    min-width: 0;

    .agent-name {
      font-size: 0.78rem;
      font-weight: 500;
      color: $color-text-primary;
    }
  }

  // Meta line: status + id
  .agent-meta {
    font-size: 0.62rem;
    color: $color-text-muted;
    margin-top: 1px;
  }

  .status-text {
    text-transform: capitalize;
    font-size: 0.62rem;
    font-style: italic;

    &.status-waiting { color: $color-status-waiting; }
    &.status-working { color: $color-status-working; font-style: italic; }
    &.status-complete { color: $color-status-complete; }
    &.status-handed_over { color: $color-status-handed-over; }
    &.status-blocked { color: $color-status-blocked; }
    &.status-silent { color: $color-status-blocked; }
    &.status-pending { color: $color-status-waiting; }
  }

  .agent-id-link {
    cursor: pointer;
    font-family: 'IBM Plex Mono', monospace;
    background: rgba(255, 255, 255, 0.05);
    padding: 0 4px;
    border-radius: $border-radius-sharp;
    text-decoration: none;

    &:hover {
      color: $color-brand-yellow;
    }
  }

  .icon-interactive {
    flex-shrink: 0;
    width: 26px;
    height: 26px;
  }
}

@media (max-width: 1100px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>
