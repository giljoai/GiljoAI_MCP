<template>
  <div class="project-tabs-container">
    <!-- Project Header (static, no scroll) -->
    <div class="project-header">
      <h1 class="project-label">Project:</h1>
      <h2 class="project-name">
        <!-- Series Chip (Handover 0440c) -->
        <v-chip
          v-if="project?.project_type_id || project?.series_number"
          :color="project?.project_type?.color || DEFAULT_PROJECT_TYPE_COLOR"
          size="small"
          variant="flat"
          class="project-badge mr-3"
          :title="project?.project_type?.label || 'Untyped'"
        >
          {{ project.taxonomy_alias }}
        </v-chip>
        <span class="project-title">{{ project?.name || 'Loading...' }}</span>
      </h2>
      <p class="text-subtitle-1 text-medium-emphasis mb-0">
        Project ID: {{ project?.project_id || project?.id || 'N/A' }}
      </p>
    </div>

    <!-- Tab Pills -->
    <div class="tab-pills">
      <button
        class="pill-btn smooth-border"
        :class="{ active: activeTab === 'launch' }"
        data-testid="launch-tab"
        @click="activeTab = 'launch'"
      >
        <v-icon size="18">mdi-rocket-launch-outline</v-icon>
        Staging
      </button>
      <button
        class="pill-btn smooth-border"
        :class="{ active: activeTab === 'jobs' }"
        data-testid="jobs-tab"
        @click="activeTab = 'jobs'"
      >
        <v-icon size="18">mdi-code-braces</v-icon>
        Implementation
      </button>
    </div>

    <!-- Execution Mode + Action Buttons (bare, on background, above framed content) -->
    <div v-if="activeTab === 'launch'" class="execution-mode-row">
      <div class="execution-mode-pills" :class="{ 'mode-locked': isExecutionModeLocked }">
        <span class="mode-label">Execution Mode:</span>
        <div class="mode-pill-group">
          <button
            class="pill-btn pill-sm smooth-border"
            :class="{ active: executionPlatform === 'multi_terminal' }"
            :disabled="isExecutionModeLocked"
            data-testid="radio-multi-terminal"
            @click="!isExecutionModeLocked && handleExecutionModeChange('multi_terminal')"
          >
            Multi-Terminal
          </button>
          <button
            class="pill-btn pill-sm smooth-border"
            :class="{ active: executionPlatform === 'claude_code_cli' }"
            :disabled="isExecutionModeLocked"
            data-testid="radio-claude-cli"
            @click="!isExecutionModeLocked && handleExecutionModeChange('claude_code_cli')"
          >
            Subagent: Claude
          </button>
          <button
            class="pill-btn pill-sm smooth-border"
            :class="{ active: executionPlatform === 'codex_cli' }"
            :disabled="isExecutionModeLocked"
            data-testid="radio-codex-cli"
            @click="!isExecutionModeLocked && handleExecutionModeChange('codex_cli')"
          >
            Subagent: Codex
            <v-icon size="x-small" color="warning" class="ml-1" title="Experimental — limited testing">mdi-alert</v-icon>
          </button>
          <button
            class="pill-btn pill-sm smooth-border"
            :class="{ active: executionPlatform === 'gemini_cli' }"
            :disabled="isExecutionModeLocked"
            data-testid="radio-gemini-cli"
            @click="!isExecutionModeLocked && handleExecutionModeChange('gemini_cli')"
          >
            Subagent: Gemini
            <v-icon size="x-small" color="warning" class="ml-1" title="Experimental — limited testing">mdi-alert</v-icon>
          </button>
        </div>
        <v-tooltip location="bottom">
          <template v-slot:activator="{ props: tooltipProps }">
            <v-icon v-bind="tooltipProps" size="small" class="help-icon" aria-label="Execution mode help">mdi-help-circle-outline</v-icon>
          </template>
          <span>Multi-Terminal: Manually launch each agent in separate terminals. Subagent modes: Orchestrator spawns specialists automatically. Codex and Gemini are experimental.</span>
        </v-tooltip>
        <v-icon v-if="isExecutionModeLocked" size="small" class="lock-icon" aria-label="Execution mode locked">mdi-lock</v-icon>
      </div>
    </div>

    <div v-if="activeTab === 'launch'" class="action-buttons-row">
      <v-btn
        class="stage-button"
        variant="outlined"
        :color="executionModeSelected && !hasActiveOrchestrator ? 'yellow-darken-2' : undefined"
        :loading="loadingStageProject"
        :disabled="!executionModeSelected || hasActiveOrchestrator"
        :title="!executionModeSelected ? 'Select an execution mode first' : (hasActiveOrchestrator ? 'An orchestrator is already active for this project' : 'Generate orchestrator prompt')"
        data-testid="stage-project-btn"
        @click="handleStageProject"
      >
        Stage Project
      </v-btn>

      <v-btn
        class="launch-button"
        :disabled="!executionModeSelected || !readyToLaunch"
        :color="executionModeSelected && readyToLaunch ? 'yellow-darken-2' : undefined"
        :variant="executionModeSelected && readyToLaunch ? 'flat' : 'outlined'"
        data-testid="launch-jobs-btn"
        @click="handleLaunchJobs"
      >
        Implement
      </v-btn>

      <v-spacer />

      <!-- Integration icons (moved from LaunchTab, Handover 0875) -->
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
    </div>

    <!-- Bordered Content Box (tabs connect to this) -->
    <div class="bordered-tabs-content">

      <!-- Project Status Area (Jobs tab only) - Handover 0819a -->
      <!-- State A: Project is done -> status banner -->
      <div v-if="activeTab === 'jobs' && projectDoneStatus" class="action-buttons-row">
        <v-chip
          :color="projectDoneStatus === 'completed' ? 'success' : projectDoneStatus === 'terminated' ? 'warning' : 'grey'"
          variant="flat"
          size="large"
          :prepend-icon="projectDoneStatus === 'cancelled' ? 'mdi-cancel' : 'mdi-check-circle'"
          data-testid="project-done-banner"
        >
          {{ projectDoneStatus === 'completed' ? 'Project Completed and Closed'
             : projectDoneStatus === 'terminated' ? 'Project Terminated'
             : 'Project Cancelled' }}
        </v-chip>
      </div>

      <!-- State B: All agents terminal, project NOT done -> closeout button -->
      <div v-else-if="activeTab === 'jobs' && showCloseoutButton" class="action-buttons-row">
        <v-btn
          class="closeout-btn"
          color="yellow-darken-2"
          variant="flat"
          prepend-icon="mdi-check-circle"
          data-testid="close-project-btn"
          @click="openCloseoutModal"
        >
          Close Out Project
        </v-btn>
      </div>

      <!-- State B2: All agents terminal, waiting for 360 memory (Handover 0820) -->
      <div v-else-if="activeTab === 'jobs' && showMemoryPending" class="action-buttons-row">
        <v-chip color="info" variant="tonal" size="large" data-testid="memory-pending-chip">
          <template #prepend>
            <v-progress-circular indeterminate size="16" width="2" />
          </template>
          Saving project memory...
        </v-chip>
      </div>

      <!-- State C: Continue-working guidance -->
      <div v-else-if="activeTab === 'jobs' && showContinueGuidance" class="action-buttons-row">
        <v-chip
          color="info"
          variant="tonal"
          size="large"
          prepend-icon="mdi-information"
          data-testid="continue-guidance"
        >
          Continue working within the agent's terminal session, or use the handover prompt generator next to the orchestrator.
        </v-chip>
      </div>

      <!-- Gemini subagent notice (shown on Jobs tab when Gemini mode active) -->
      <div v-if="activeTab === 'jobs' && isGeminiMode" class="gemini-notice-row">
        <v-chip
          color="warning"
          variant="tonal"
          size="default"
          prepend-icon="mdi-alert-circle-outline"
          class="gemini-notice-chip"
          data-testid="gemini-notice"
          @click="showGeminiNotice = true"
        >
          Gemini subagent: no active orchestrator during execution
          <v-icon end size="x-small">mdi-information-outline</v-icon>
        </v-chip>
      </div>

      <!-- Tab Content -->
      <v-window v-model="activeTab" class="tabs-content">
        <!-- Launch Tab -->
        <v-window-item value="launch">
          <LaunchTab
            :project="projectWithUpdatedMode"
            :orchestrator="orchestrator"
            :is-staging="loadingStageProject"
            :git-enabled="gitEnabled"
            :serena-enabled="serenaEnabled"
            @edit-description="emit('edit-description')"
          />
        </v-window-item>

        <!-- Jobs Tab -->
        <v-window-item value="jobs">
          <JobsTab
            :project="projectWithUpdatedMode"
          />
        </v-window-item>
      </v-window>
    </div>

    <!-- Gemini Subagent Notice Dialog -->
    <v-dialog v-model="showGeminiNotice" max-width="520">
      <v-card class="smooth-border">
        <v-card-title class="d-flex align-center ga-2">
          <v-icon color="warning">mdi-alert-circle</v-icon>
          Gemini Subagent Mode
        </v-card-title>
        <v-card-text class="gemini-dialog-body">
          <p>
            The Gemini CLI does not maintain an active orchestrator while subagents are executing.
            The orchestrator goes idle during team activity, meaning agents work without supervision.
          </p>
          <p>
            In rare cases, a subagent may enter a loop. When this happens, you must manually
            intervene by pressing <kbd>ESC</kbd> in the CLI to stop the looping agent.
            Carefully identify which agent is looping before stopping it, the remaining
            team members will continue normally.
          </p>
          <p class="mb-0">
            This is a limitation of Gemini's subagent architecture, not an MCP server issue.
            Stay attentive during execution so you can intervene quickly and not waste tokens.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showGeminiNotice = false">Got it</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Project Closeout Modal (Handover 0361) -->
    <CloseoutModal
      :show="showCloseoutModal"
      :project-id="project.project_id || project.id"
      :project-name="project.name"
      :product-id="project.product_id"
      :project-status="project.status"
      @close="showCloseoutModal = false"
      @closeout="handleCloseoutComplete"
      @continue="handleContinueWorking"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectTabsStore } from '@/stores/projectTabs'
import { useWebSocketStore } from '@/stores/websocket'
import { useAgentJobs } from '@/composables/useAgentJobs'
import { useProjectMessages } from '@/composables/useProjectMessages'
import { useProjectStateStore } from '@/stores/projectStateStore'
import { useNotificationStore } from '@/stores/notifications'
import { useIntegrationStatus } from '@/composables/useIntegrationStatus'
import { useToast } from '@/composables/useToast'
import { useClipboard } from '@/composables/useClipboard'
import api from '@/services/api'
import LaunchTab from './LaunchTab.vue'
import JobsTab from './JobsTab.vue'
import CloseoutModal from '@/components/orchestration/CloseoutModal.vue'
import { DEFAULT_PROJECT_TYPE_COLOR } from '@/utils/constants'

const { copy: clipboardCopy } = useClipboard()

/**
 * Props
 */
const props = defineProps({
  project: {
    type: Object,
    required: true,
  },
  orchestrator: {
    type: Object,
    default: null,
  },
})

/**
 * Emits
 */
const emit = defineEmits([
  'edit-description',
  'project-updated',
])

/**
 * Store and Router
 */
const tabsStore = useProjectTabsStore()
const wsStore = useWebSocketStore()
const notificationStore = useNotificationStore()
const route = useRoute()
const router = useRouter()

const projectStateStore = useProjectStateStore()
const { store: projectMessagesStore, loadMessages } = useProjectMessages()
const { store: agentJobsStore, sortedJobs, loadJobs } = useAgentJobs()

// Integration status for LaunchTab (Handover 0427)
const { gitEnabled, serenaEnabled } = useIntegrationStatus()

// Toast notifications (Handover 0428)
const { showToast } = useToast()

const projectId = computed(() => props.project?.project_id || props.project?.id || null)

/**
 * Active agentic tool badge based on execution mode (moved from LaunchTab, Handover 0875)
 */
const agenticTool = computed(() => {
  const mode = executionMode.value
  if (mode === 'claude_code_cli') return { type: 'img', src: '/claude_pix.svg', label: 'Claude Code', alt: 'Claude Code subagent active' }
  if (mode === 'codex_cli') return { type: 'img', src: '/codex_logo.svg', label: 'Codex CLI', alt: 'Codex CLI subagent active' }
  if (mode === 'gemini_cli') return { type: 'img', src: '/gemini-icon.svg', label: 'Gemini CLI', alt: 'Gemini CLI subagent active' }
  if (mode === 'multi_terminal') return { type: 'icon', icon: 'mdi-monitor-multiple', label: 'Multi Terminal', alt: 'Multi terminal mode active' }
  return null
})

/**
 * Navigate to integrations settings (moved from LaunchTab, Handover 0875)
 */
function goToIntegrations() {
  router.push({ path: '/settings', query: { tab: 'integrations' } })
}

/**
 * Execution Mode Toggle (Handover 0428: Moved from LaunchTab)
 * Default to null (unchecked) - user must select before staging
 */
const executionPlatform = ref(null)

/**
 * Check if user has selected an execution mode
 */
const executionModeSelected = computed(() => executionPlatform.value !== null)

/**
 * Mission text from project state store (needed for lock check)
 */
const missionText = computed(
  () => projectStateStore.getProjectState(projectId.value)?.mission || '',
)

/**
 * Check if execution mode is locked (Handover 0428: Moved from LaunchTab)
 * Execution mode is locked when orchestrator has generated a mission
 */
const isExecutionModeLocked = computed(() => {
  return Boolean(missionText.value)
})

/**
 * Local state - Tab activation (Handover 0243e)
 * Initialize from URL query param or default to 'launch'
 */
const activeTab = ref('launch')

// Initialize from URL query param if present
if (route.query.tab && ['launch', 'jobs'].includes(route.query.tab)) {
  activeTab.value = route.query.tab
}

/**
 * Sync URL when tab changes (enables browser back/forward, bookmarking)
 */
watch(activeTab, (newTab) => {
  if (route.query.tab !== newTab) {
    router.replace({
      query: { ...route.query, tab: newTab },
      hash: route.hash
    })
  }
})

/**
 * Local state
 */
const loadingStageProject = ref(false)
const executionMode = ref(props.project?.execution_mode || 'multi_terminal')
const showGeminiNotice = ref(false)
const isGeminiMode = computed(() => executionMode.value === 'gemini_cli')

/**
 * Computed: Project with updated execution_mode
 * Handover 0404: Sync local executionMode ref with project prop for JobsTab
 * JobsTab reads execution_mode from project prop, so we need to merge the updated value
 */
const projectWithUpdatedMode = computed(() => ({
  ...props.project,
  execution_mode: executionMode.value,
}))

// Closeout modal state (Handover 0361)
const showCloseoutModal = ref(false)

// 360 memory gate: prevent closeout button before memory is written (Handover 0820)
const memoryWritten = ref(false)

// Continue-working guidance state (Handover 0819a)
const showContinueGuidance = ref(false)

const projectDoneStatus = computed(() => {
  const status = props.project?.status
  if (['completed', 'terminated', 'cancelled'].includes(status)) return status
  return null
})

/**
 * Computed: Project state (map-based store)
 */
const readyToLaunch = computed(() => {
  const state = projectStateStore.getProjectState(projectId.value)
  return Boolean(state?.stagingComplete && !state?.isStaging)
})

/**
 * Computed: Check if orchestrator is already active (staging complete)
 *
 * Handover 0291: Unified toggle - first message in project triggers both:
 * - "Stage Project" button disables (stays labeled "Stage Project")
 * - "Launch Jobs" button enables
 */
const hasActiveOrchestrator = computed(() => {
  const state = projectStateStore.getProjectState(projectId.value)
  return Boolean(state?.stagingComplete)
})

/**
 * Computed: All agent jobs (including orchestrator) have reached terminal status
 * Handover 0361, 0425, 0820: Extracted from showCloseoutButton for reuse
 */
const allJobsTerminal = computed(() => {
  if (['completed', 'terminated', 'cancelled'].includes(props.project?.status)) return false
  const jobs = sortedJobs.value || []
  if (!jobs.length) return false
  const isTerminal = (status) => status === 'complete' || status === 'completed' || status === 'decommissioned'
  const allTerminal = jobs.every((job) => isTerminal(job.status))
  if (!allTerminal) return false
  const orchestrator = jobs.find((job) => job.agent_display_name === 'orchestrator')
  return Boolean(orchestrator && isTerminal(orchestrator.status))
})

/**
 * Computed: Show closeout button only after 360 memory has been written
 * Handover 0820: Gate on memoryWritten to prevent "No 360 memory entries found"
 */
const showCloseoutButton = computed(() => {
  if (!allJobsTerminal.value) return false
  // No product association means no 360 memory can be written - skip gate
  if (!props.project?.product_id) return true
  return memoryWritten.value
})

const showMemoryPending = computed(() => {
  if (!allJobsTerminal.value) return false
  if (!props.project?.product_id) return false
  return !memoryWritten.value
})

function showError(message) {
  showToast({ message: message || 'Unexpected error', type: 'error' })
}

async function loadProjectData(pid, { fetchProject = false } = {}) {
  if (!pid) return

  tabsStore.currentProject = props.project
  projectStateStore.setProject(props.project)

  if (fetchProject) {
    try {
      const response = await api.projects.get(pid)
      projectStateStore.setProject(response?.data)
    } catch (error) {
      console.warn('[ProjectTabs] Failed to refresh project state:', error)
    }
  }

  try {
    const [messages] = await Promise.all([loadMessages(pid), loadJobs(pid)])

    if (Array.isArray(messages) && messages.length > 0) {
      projectStateStore.setStagingComplete(pid, true)
    }
  } catch (error) {
    console.warn('[ProjectTabs] Failed to load project data:', error)
  }
}

watch(
  () => props.project?.execution_mode,
  (newMode) => {
    executionMode.value = newMode || 'multi_terminal'
    // Handover 0428: Sync UI toggle state
    // Only sync if project has been staged (has mission) - fresh projects should have no selection
    // Backend defaults execution_mode to 'multi_terminal', so we can't rely on newMode alone
    if (newMode && missionText.value) {
      executionPlatform.value = newMode
    }
  },
  { immediate: true },
)

// Sync radio selection once mission is loaded (for previously staged projects)
watch(
  missionText,
  (newMission) => {
    if (newMission && executionPlatform.value === null) {
      // Project was previously staged, restore execution mode selection
      const mode = props.project?.execution_mode
      if (mode) {
        executionPlatform.value = mode
      }
    }
  },
)

watch(
  projectId,
  async (pid, oldPid) => {
    if (oldPid) {
      wsStore.unsubscribe('project', oldPid)
    }

    if (!pid) return

    if (oldPid && oldPid !== pid) {
      tabsStore.isLaunched = false
      projectStateStore.setLaunched(pid, false)
      clearTimeout(memoryCheckTimeout)
      memoryWritten.value = false
    }

    wsStore.subscribeToProject(pid)
    await loadProjectData(pid)
  },
  { immediate: true },
)

let unsubscribeConnectionListener = null
let unsubscribeMemory = null
let memoryCheckTimeout = null
onMounted(() => {
  unsubscribeConnectionListener = wsStore.onConnectionChange((connectionEvent) => {
    if (connectionEvent?.state === 'connected' && connectionEvent?.isReconnect) {
      loadProjectData(projectId.value, { fetchProject: true })
    }
  })

  // Handover 0820: Listen for 360 memory writes to ungate closeout button
  try {
    unsubscribeMemory = wsStore.on('product:memory:updated', (payload) => {
      const entryProjectId = payload?.entry?.project_id
      if (entryProjectId === projectId.value) {
        memoryWritten.value = true
      }
    })
  } catch {
    console.warn('[ProjectTabs] Failed to subscribe to memory events')
  }
})

// Auto-dismiss continue-working guidance when orchestrator starts working (Handover 0819a)
watch(() => sortedJobs.value, (jobs) => {
  if (showContinueGuidance.value && jobs?.length) {
    const orchestrator = jobs.find((j) => j.agent_display_name === 'orchestrator')
    if (orchestrator && orchestrator.status === 'working') {
      showContinueGuidance.value = false
    }
  }
})

// Handover 0820: Check API for existing 360 memory when all jobs become terminal (handles page refresh)
watch(allJobsTerminal, async (terminal) => {
  clearTimeout(memoryCheckTimeout)
  if (!terminal || memoryWritten.value) return
  const productId = props.project?.product_id
  if (!productId) return
  try {
    const res = await api.products.getMemoryEntries(productId, {
      project_id: projectId.value,
      limit: 1,
    })
    if (res.data?.entries?.length > 0) {
      memoryWritten.value = true
      return
    }
  } catch {
    memoryWritten.value = true
    return
  }
  // Memory not yet written - retry once after 60s, then fail open
  memoryCheckTimeout = setTimeout(async () => {
    if (memoryWritten.value) return
    try {
      await api.products.getMemoryEntries(productId, {
        project_id: projectId.value,
        limit: 1,
      })
      memoryWritten.value = true  // fail open regardless of result
    } catch {
      memoryWritten.value = true
    }
  }, 60_000)
}, { immediate: true })

// Handover 0440c: Update browser tab title when project loads
watch(
  () => props.project,
  (project) => {
    if (project) {
      const prefix = project.taxonomy_alias && project.series_number ? `${project.taxonomy_alias} ` : ''
      document.title = `${prefix}${project.name} - GiljoAI`
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (projectId.value) {
    wsStore.unsubscribe('project', projectId.value)
  }
  unsubscribeConnectionListener?.()
  unsubscribeMemory?.()
  clearTimeout(memoryCheckTimeout)
  // Handover 0440c: Reset browser tab title
  document.title = 'GiljoAI MCP'
})

/**
 * Copy text to clipboard using shared composable
 */
async function copyPromptToClipboard(text) {
  if (!text) {
    return false
  }
  return await clipboardCopy(text)
}

/**
 * Handle execution mode change from radio buttons (Handover 0428)
 */
async function handleExecutionModeChange(newValue) {
  const previousValue = executionPlatform.value
  executionPlatform.value = newValue

  const _modeLabels = {
    multi_terminal: 'Multi-Terminal mode enabled',
    claude_code_cli: 'Claude Code CLI selected',
    codex_cli: 'Codex CLI selected (experimental)',
    gemini_cli: 'Gemini CLI selected (experimental)',
  }

  try {
    // Persist to backend
    await api.projects.update(projectId.value, { execution_mode: newValue })

    // Update local executionMode ref for handleStageProject
    executionMode.value = newValue

    showToast({
      message: _modeLabels[newValue] || 'Execution mode updated',
      type: 'info',
      timeout: 3000
    })
  } catch (error) {
    // Revert on failure
    executionPlatform.value = previousValue
    console.error('Failed to update execution mode:', error)
    showToast({
      message: 'Failed to save execution mode. Please try again.',
      type: 'error',
      timeout: 3000
    })
  }
}

/**
 * Handle stage project
 */
async function handleStageProject() {
  loadingStageProject.value = true
  if (projectId.value) {
    projectStateStore.setIsStaging(projectId.value, true)
  }

  try {
    // Generate thin client staging prompt
    // Pass execution_mode from project configuration (Handover 0333 Phase 2)
    const pid = projectId.value
    if (!pid) {
      throw new Error('Project missing ID')
    }

    const _platformToTool = {
      multi_terminal: 'claude-code',
      claude_code_cli: 'claude-code',
      codex_cli: 'codex',
      gemini_cli: 'gemini',
    }
    const currentMode = executionMode.value || 'multi_terminal'
    const response = await api.prompts.staging(pid, {
      tool: _platformToTool[currentMode] || 'claude-code',
      execution_mode: currentMode,
    })

    if (!response.data?.prompt) {
      throw new Error('Invalid response from staging endpoint')
    }

    const { prompt } = response.data

    // Copy to clipboard immediately
    const copied = await copyPromptToClipboard(prompt)

    if (copied) {
      const _pasteLabels = {
        multi_terminal: 'Orchestrator prompt copied - paste into ANY terminal (fresh or existing)',
        claude_code_cli: 'Orchestrator prompt copied - paste into Claude Code CLI',
        codex_cli: 'Orchestrator prompt copied - paste into Codex CLI',
        gemini_cli: 'Orchestrator prompt copied - paste into Gemini CLI',
      }
      showToast({ message: _pasteLabels[currentMode] || _pasteLabels.multi_terminal, type: 'success' })
    } else {
      showToast({ message: 'Copy failed — select the prompt text and press Ctrl+C', type: 'warning', timeout: 6000 })
    }
  } catch (error) {
    console.error('Stage project failed:', error)

    // Check if error is about existing orchestrator
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to stage project'

    if (errorMsg.toLowerCase().includes('orchestrator already exists')) {
      showToast({ message: 'An orchestrator is already active for this project. The existing orchestrator will be reused.', type: 'info' })
    } else {
      // Show error for other failures
      showError(errorMsg)
    }
  } finally {
    loadingStageProject.value = false
    if (projectId.value) {
      projectStateStore.setIsStaging(projectId.value, false)
    }
  }
}

/**
 * Handle launch jobs
 */
async function handleLaunchJobs() {
  try {
    if (!readyToLaunch.value) {
      showError('Project not ready to launch')
      return
    }

    await api.orchestrator.launchProject({ project_id: projectId.value })
    tabsStore.isLaunched = true
    tabsStore.currentProject = props.project
    projectStateStore.setLaunched(projectId.value, true)

    // Auto-switch to Jobs/Implement tab after launch (Handover 0243e)
    activeTab.value = 'jobs'
  } catch (error) {
    console.error('Launch jobs failed:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to launch jobs'
    showError(msg)
  }
}

/**
 * Open closeout modal (Handover 0361)
 */
function openCloseoutModal() {
  showCloseoutModal.value = true
}

/**
 * Handle project closeout completion (Handover 0819a)
 * Stays on page and refreshes data so status banner appears
 */
async function handleCloseoutComplete() {
  showCloseoutModal.value = false
  notificationStore.clearForProject(projectId.value)
  showToast({ message: 'Project closed out successfully', type: 'success' })
  emit('project-updated')
}

/**
 * Handle continue working from CloseoutModal (Handover 0819a)
 * Shows guidance text, refreshes agent statuses
 */
async function handleContinueWorking() {
  showCloseoutModal.value = false
  showContinueGuidance.value = true
  showToast({ message: 'Project resumed - agents ready for work', type: 'success' })
  emit('project-updated')
}
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;
@use '@/styles/agent-colors.scss' as *;
@use '@/styles/design-tokens.scss' as *;

.project-tabs-container {
  background: rgb(var(--v-theme-background));
  height: 100%;
  padding: 24px;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* Page doesn't scroll - only individual panels do */
}

/* Project Header - Title and ID */
.project-header {
  margin-bottom: 16px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;

  .project-label {
    font-size: 1.5rem;
    font-weight: 400;
    margin: 0;
  }

  .project-name {
    display: flex;
    align-items: center;
    color: rgb(var(--v-theme-primary));
    font-size: 2rem;
    font-weight: 400;
    margin: 0;
  }

  .project-badge {
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .text-subtitle-1 {
    width: 100%;
  }
}

/* Tab Pills */
.tab-pills {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-shrink: 0;
}

/* Shared pill button style */
.pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: $border-radius-pill;
  padding: 8px 18px;
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  transition: $transition-all-fast;
  background: transparent;
  color: var(--text-muted);
  border: none;
  --smooth-border-color: rgba(var(--v-theme-on-surface), 0.15);

  &:hover:not(:disabled) {
    color: var(--text-secondary);
    --smooth-border-color: rgba(var(--v-theme-on-surface), 0.25);
  }

  &.active,
  &.active:hover {
    background: rgba(255, 195, 0, 0.12);
    color: #ffc300;
    box-shadow: none;
  }

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
}

.pill-sm {
  padding: 5px 14px;
  font-size: 0.73rem;
}

/* Tab content container (bare, no frame) */
.bordered-tabs-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Action buttons row inside the box (centered) */
.action-buttons-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-shrink: 0;
}

/* Action buttons styling */
.stage-button {
  text-transform: none;
  font-weight: 500;
}

.launch-button {
  text-transform: none;
  font-weight: 500;
}


.closeout-btn {
  text-transform: none;
  font-weight: 600;
  letter-spacing: 0.5px;

  &:hover {
    background: rgb(var(--v-theme-highlight-hover));
  }
}

/* Gemini subagent notice */
.gemini-notice-row {
  display: flex;
  justify-content: center;
  padding: 6px 16px 2px 16px;
}

.gemini-notice-chip {
  cursor: pointer;
  font-size: 12px;
}

.gemini-dialog-body {
  p {
    margin-bottom: 12px;
    line-height: 1.6;
  }

  kbd {
    background: rgba(var(--v-theme-on-surface), 0.08);
    border-radius: $border-radius-sharp;
    padding: 1px 6px;
    font-family: monospace;
    font-size: 13px;
  }
}

/* Execution mode row (above buttons, centered) */
.execution-mode-row {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

/* Execution mode pills */
.execution-mode-pills {
  display: flex;
  align-items: center;
  gap: 8px;

  &.mode-locked {
    opacity: 0.6;
  }

  .mode-label {
    font-weight: 500;
    color: white;
    font-size: 14px;
    margin-right: 4px;
  }

  .mode-pill-group {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }

  .help-icon {
    color: rgba(var(--v-theme-on-surface), 0.5);
    cursor: help;
  }

  .lock-icon {
    color: rgba(var(--v-theme-on-surface), 0.5);
    margin-left: 4px;
  }
}

/* Tab content fills remaining space */
.tabs-content {
  flex: 1;
  min-height: 0; /* Critical for flex overflow */
  overflow: hidden;

  :deep(.v-window__container) {
    height: 100%;
  }

  :deep(.v-window-item) {
    height: 100%;
  }
}

/* Mobile / Portrait Responsive */
@media (max-width: 1024px) {
  .project-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;

    .project-label {
      font-size: 1.2rem;
    }

    .project-name {
      font-size: 1.1rem;
    }
  }
}

@media (max-width: 600px) {
  .project-tabs-container {
    padding: 16px;
  }

  .action-buttons-row {
    flex-wrap: wrap;
    gap: 8px;
  }
}
</style>
