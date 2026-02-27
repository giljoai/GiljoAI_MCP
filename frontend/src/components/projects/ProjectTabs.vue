<template>
  <div class="project-tabs-container">
    <!-- Project Header (static, no scroll) -->
    <div class="project-header">
      <div class="d-flex align-center gap-4">
        <h1 class="text-h4">Project:</h1>
        <h2 class="project-name d-flex align-center">
          <!-- Series Chip (Handover 0440c) -->
          <v-chip
            v-if="project?.taxonomy_alias && project?.series_number"
            :color="project?.project_type?.color || '#607D8B'"
            size="small"
            variant="flat"
            class="mr-3"
            :title="project?.project_type?.label || 'Untyped'"
          >
            {{ project.taxonomy_alias }}
          </v-chip>
          <span>{{ project?.name || 'Loading...' }}</span>
        </h2>
      </div>
      <p class="text-subtitle-1 text-medium-emphasis mb-0">
        Project ID: {{ project?.project_id || project?.id || 'N/A' }}
      </p>
    </div>

    <!-- Tabs (connected to bordered content box below) -->
    <v-btn-toggle
      v-model="activeTab"
      mandatory
      variant="outlined"
      divided
      rounded="t-lg"
      color="primary"
      class="tabs-toggle"
    >
      <v-btn value="launch" data-testid="launch-tab">
        <v-icon start size="20">mdi-rocket-launch</v-icon>
        STAGING
      </v-btn>
      <v-btn value="jobs" data-testid="jobs-tab">
        <v-icon start size="20">mdi-code-braces</v-icon>
        IMPLEMENTATION
      </v-btn>
    </v-btn-toggle>

    <!-- Bordered Content Box (tabs connect to this) -->
    <div class="bordered-tabs-content">
      <!-- Execution Mode Radio (above buttons) - only show on Launch tab -->
      <div v-if="activeTab === 'launch'" class="execution-mode-row">
        <div class="execution-mode-radio" :class="{ 'mode-locked': isExecutionModeLocked }">
          <span class="mode-label">Execution Mode:</span>
          <v-radio-group
            v-model="usingClaudeCodeSubagents"
            inline
            hide-details
            density="compact"
            :disabled="isExecutionModeLocked"
            class="mode-radios"
            @update:model-value="handleExecutionModeChange"
          >
            <v-radio :value="false" label="Multi-Terminal" data-testid="radio-multi-terminal" />
            <v-radio :value="true" label="Claude Code CLI" data-testid="radio-claude-cli" />
          </v-radio-group>
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props: tooltipProps }">
              <v-icon v-bind="tooltipProps" size="small" class="help-icon">mdi-help-circle-outline</v-icon>
            </template>
            <span>Multi-Terminal: Manually launch each agent in separate terminals. Claude Code CLI: Orchestrator spawns specialists via Task tool.</span>
          </v-tooltip>
          <v-icon v-if="isExecutionModeLocked" size="small" class="lock-icon">mdi-lock</v-icon>
        </div>
      </div>

      <!-- Action Buttons Row (centered) - Launch tab buttons -->
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
      </div>

      <!-- Close Out Project Button Row (Handover 0361, 0425 - Jobs tab only when all complete) -->
      <div v-if="activeTab === 'jobs' && showCloseoutButton" class="action-buttons-row">
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

      <!-- Tab Content -->
      <v-window v-model="activeTab" class="tabs-content">
        <!-- Launch Tab -->
        <v-window-item value="launch">
          <LaunchTab
            :project="project"
            :orchestrator="orchestrator"
            :is-staging="loadingStageProject"
            :readonly="readonly"
            :git-enabled="gitEnabled"
            :serena-enabled="serenaEnabled"
            @stage-project="handleStageProject"
            @launch-jobs="handleLaunchJobs"
            @cancel-staging="handleCancelStaging"
            @edit-description="emit('edit-description')"
            @edit-mission="emit('edit-mission', $event)"
            @edit-agent-mission="emit('edit-agent-mission', $event)"
          />
        </v-window-item>

        <!-- Jobs Tab -->
        <v-window-item value="jobs">
          <JobsTab
            :project="projectWithUpdatedMode"
            :readonly="readonly"
            @launch-agent="handleLaunchAgent"
            @view-details="emit('view-details', $event)"
            @view-error="emit('view-error', $event)"
            @hand-over="handleHandOver"
            @closeout-project="handleCloseoutProject"
          />
        </v-window-item>
      </v-window>
    </div>

    <!-- Error Snackbar -->
    <v-snackbar v-model="errorVisible" color="error" :timeout="5000" location="top">
      <v-icon start>mdi-alert-circle</v-icon>
      {{ errorMessage }}
      <template #actions>
        <v-btn variant="text" @click="errorVisible = false"> Close </v-btn>
      </template>
    </v-snackbar>

    <!-- Success Toast -->
    <v-snackbar v-model="toastVisible" :color="toastColor" :timeout="toastDuration" location="top">
      <v-icon start>mdi-check-circle</v-icon>
      {{ toastMessage }}
      <template #actions>
        <v-btn variant="text" @click="toastVisible = false"> Close </v-btn>
      </template>
    </v-snackbar>

    <!-- Project Closeout Modal (Handover 0361) -->
    <CloseoutModal
      :show="showCloseoutModal"
      :project-id="project.project_id || project.id"
      :project-name="project.name"
      :product-id="project.product_id"
      @close="showCloseoutModal = false"
      @closeout="handleCloseoutComplete"
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
import { useIntegrationStatus } from '@/composables/useIntegrationStatus'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'
import LaunchTab from './LaunchTab.vue'
import JobsTab from './JobsTab.vue'
import CloseoutModal from '@/components/orchestration/CloseoutModal.vue'

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
  readonly: {
    type: Boolean,
    default: false,
  },
})

/**
 * Emits
 */
const emit = defineEmits([
  'stage-project',
  'launch-jobs',
  'cancel-staging',
  'edit-description',
  'edit-mission',
  'edit-agent-mission',
  'launch-agent',
  'view-details',
  'view-error',
  'closeout-project',
  'send-message',
])

/**
 * Store and Router
 */
const tabsStore = useProjectTabsStore()
const wsStore = useWebSocketStore()
const route = useRoute()
const router = useRouter()

const projectStateStore = useProjectStateStore()
const { store: projectMessagesStore, loadMessages } = useProjectMessages()
const { store: agentJobsStore, sortedJobs, loadJobs } = useAgentJobs()

// Integration status for LaunchTab (Handover 0427)
const { gitEnabled, serenaEnabled } = useIntegrationStatus()

// Toast notifications (Handover 0428)
const { showToast: showToastNotification } = useToast()

const projectId = computed(() => props.project?.project_id || props.project?.id || null)

/**
 * Execution Mode Toggle (Handover 0428: Moved from LaunchTab)
 * Default to null (unchecked) - user must select before staging
 */
const usingClaudeCodeSubagents = ref(null)

/**
 * Check if user has selected an execution mode
 */
const executionModeSelected = computed(() => usingClaudeCodeSubagents.value !== null)

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
const errorVisible = ref(false)
const errorMessage = ref(null)
const loadingStageProject = ref(false)
const executionMode = ref(props.project?.execution_mode || 'multi_terminal')

/**
 * Computed: Project with updated execution_mode
 * Handover 0404: Sync local executionMode ref with project prop for JobsTab
 * JobsTab reads execution_mode from project prop, so we need to merge the updated value
 */
const projectWithUpdatedMode = computed(() => ({
  ...props.project,
  execution_mode: executionMode.value,
}))

// Toast state
const toastVisible = ref(false)
const toastMessage = ref('')
const toastColor = ref('success')
const toastDuration = ref(3000)

// Closeout modal state (Handover 0361)
const showCloseoutModal = ref(false)

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
 * Computed: Show closeout button when all agents complete and orchestrator is done
 * Handover 0361: Moved from JobsTab.vue to header for persistent visibility
 * Handover 0425: Accept both 'complete' and 'completed' status values
 */
const showCloseoutButton = computed(() => {
  const jobs = sortedJobs.value || []
  if (!jobs.length) return false

  // Accept complete, completed, and decommissioned as terminal states (Handover 0498)
  const isTerminal = (status) => status === 'complete' || status === 'completed' || status === 'decommissioned'
  const allTerminal = jobs.every((job) => isTerminal(job.status))
  if (!allTerminal) return false

  const orchestrator = jobs.find((job) => job.agent_display_name === 'orchestrator')
  return Boolean(orchestrator && isTerminal(orchestrator.status))
})

function showError(message) {
  errorMessage.value = message || 'Unexpected error'
  errorVisible.value = true
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
      usingClaudeCodeSubagents.value = newMode === 'claude_code_cli'
    }
  },
  { immediate: true },
)

// Sync radio selection once mission is loaded (for previously staged projects)
watch(
  missionText,
  (newMission) => {
    if (newMission && usingClaudeCodeSubagents.value === null) {
      // Project was previously staged, restore execution mode selection
      const mode = props.project?.execution_mode
      if (mode) {
        usingClaudeCodeSubagents.value = mode === 'claude_code_cli'
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
    }

    wsStore.subscribeToProject(pid)
    await loadProjectData(pid)
  },
  { immediate: true },
)

let unsubscribeConnectionListener = null
onMounted(() => {
  unsubscribeConnectionListener = wsStore.onConnectionChange((connectionEvent) => {
    if (connectionEvent?.state === 'connected' && connectionEvent?.isReconnect) {
      loadProjectData(projectId.value, { fetchProject: true })
    }
  })
})

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
  // Handover 0440c: Reset browser tab title
  document.title = 'GiljoAI MCP'
})

/**
 * Production-grade clipboard copy function
 */
async function copyPromptToClipboard(text) {
  if (!text) {
    return false
  }

  try {
    // Try modern Clipboard API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch (clipErr) {
    console.warn('[ProjectTabs] Clipboard API failed, trying fallback:', clipErr)
  }

  // Fallback for HTTP
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '0'
    document.body.appendChild(textarea)

    textarea.focus()
    textarea.select()
    textarea.setSelectionRange(0, textarea.value.length)

    const success = document.execCommand('copy')
    document.body.removeChild(textarea)

    if (success) return true
  } catch (err) {
    console.error('[ProjectTabs] All copy methods failed:', err)
  }

  return false
}

/**
 * Handle execution mode change from radio buttons (Handover 0428)
 */
async function handleExecutionModeChange(newValue) {
  const newMode = newValue ? 'claude_code_cli' : 'multi_terminal'

  try {
    // Persist to backend
    await api.projects.update(projectId.value, { execution_mode: newMode })

    // Update local executionMode ref for handleStageProject
    executionMode.value = newMode

    showToastNotification({
      message: newValue
        ? 'Claude Code CLI mode enabled'
        : 'Multi-Terminal mode enabled',
      type: 'info',
      timeout: 3000
    })
  } catch (error) {
    // Revert on failure
    usingClaudeCodeSubagents.value = !newValue
    console.error('Failed to update execution mode:', error)
    showToastNotification({
      message: 'Failed to save execution mode',
      type: 'error',
      timeout: 3000
    })
  }
}

/**
 * Navigate to integrations settings (Handover 0427)
 */
function goToIntegrations() {
  router.push({ path: '/settings', query: { tab: 'integrations' } })
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

    const response = await api.prompts.staging(pid, {
      tool: 'claude-code',
      execution_mode: executionMode.value || 'multi_terminal',
    })

    if (!response.data?.prompt) {
      throw new Error('Invalid response from staging endpoint')
    }

    const { prompt } = response.data

    // Copy to clipboard immediately
    const copied = await copyPromptToClipboard(prompt)

    if (copied) {
      // Show success toast
      toastMessage.value = 'Orchestrator prompt copied - paste into ANY terminal (fresh or existing)'
      toastColor.value = 'success'
      toastDuration.value = 4000
      toastVisible.value = true
    } else {
      alert(`Please manually copy this prompt:\n\n${prompt}`)
    }

    emit('stage-project')
  } catch (error) {
    console.error('Stage project failed:', error)

    // Check if error is about existing orchestrator
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to stage project'

    if (errorMsg.toLowerCase().includes('orchestrator already exists')) {
      // Show informative message about existing orchestrator
      toastMessage.value = 'An orchestrator is already active for this project. The existing orchestrator will be reused.'
      toastColor.value = 'info'
      toastDuration.value = 4000
      toastVisible.value = true
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
    emit('launch-jobs')

    // Auto-switch to Jobs/Implement tab after launch (Handover 0243e)
    activeTab.value = 'jobs'
  } catch (error) {
    console.error('Launch jobs failed:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to launch jobs'
    showError(msg)
  }
}

/**
 * Handle cancel staging
 */
async function handleCancelStaging() {
  try {
    if (!projectId.value) return

    await api.projects.cancelStaging(projectId.value)

    projectStateStore.setMission(projectId.value, '')
    projectStateStore.setStagingComplete(projectId.value, false)
    projectStateStore.setIsStaging(projectId.value, false)
    projectStateStore.setLaunched(projectId.value, false)
    projectMessagesStore.setMessages(projectId.value, [])
    agentJobsStore.$reset?.()

    emit('cancel-staging')
  } catch (error) {
    console.error('Cancel staging failed:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to cancel staging'
    showError(msg)
  }
}

/**
 * Handle launch agent
 */
async function handleLaunchAgent(agent) {
  try {
    const jobId = agent?.job_id || agent?.agent_id || agent?.id
    if (!jobId) {
      showError('Agent job missing ID')
      return
    }

    await api.agentJobs.acknowledge(jobId)
    emit('launch-agent', agent)
  } catch (error) {
    console.error('Launch agent failed:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to launch agent'
    showError(msg)
  }
}

/**
 * Handle closeout project
 */
async function handleCloseoutProject(closeoutData) {
  try {
    emit('closeout-project', closeoutData)
    // Navigate to projects list after closeout
    router.push('/projects')
  } catch (error) {
    console.error('Closeout project failed:', error)
  }
}

/**
 * Handle orchestrator session refresh result from ActionIcons.
 * ActionIcons handles the API call internally and emits the result.
 */
function handleHandOver(event) {
  if (event.success) {
    toastMessage.value = event.message || 'Session refreshed! Continuation prompt copied to clipboard.'
    toastColor.value = 'success'
    toastDuration.value = 4000
    toastVisible.value = true
  } else {
    console.error('Session refresh failed:', event.error)
    toastMessage.value = event.error || 'Failed to refresh session'
    toastColor.value = 'error'
    toastDuration.value = 5000
    toastVisible.value = true
  }
}

/**
 * Open closeout modal (Handover 0361)
 */
function openCloseoutModal() {
  showCloseoutModal.value = true
}

/**
 * Handle project closeout completion (Handover 0361)
 */
function handleCloseoutComplete(closeoutData) {
  const normalized =
    typeof closeoutData === 'string'
      ? { project_id: closeoutData, sequence_number: 0 }
      : closeoutData || {}

  toastMessage.value = `Project closed out successfully (Memory entry #${normalized.sequence_number ?? 0})`
  toastColor.value = 'success'
  toastDuration.value = 5000
  toastVisible.value = true

  showCloseoutModal.value = false
  emit('closeout-project', normalized)

  // Navigate to projects list after closeout
  router.push('/projects')
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

  h1.text-h4 {
    font-size: 1.5rem;
    font-weight: 400;
    margin: 0;
  }

  .project-name {
    color: #ffc300;
    font-size: 2rem;
    font-weight: 400;
    margin: 0;
  }
}

/* Tabs - connect to bordered content box */
.tabs-toggle {
  align-self: flex-start;
  margin-bottom: -1px; /* Overlap border to connect visually */
  position: relative;
  z-index: 1;
}

/* Bordered content box - tabs connect to top */
.bordered-tabs-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.2);
  border-radius: 0 8px 8px 8px; /* No top-left radius where tabs connect */
  background: rgb(var(--v-theme-surface));
  overflow: hidden;
}

/* Action buttons row inside the box (centered) */
.action-buttons-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 8px 16px 8px 16px;
  flex-shrink: 0;
}

/* Action buttons styling */
.stage-button {
  text-transform: none;
  font-weight: 500;
}

.status-text {
  color: #ffd700;
  font-style: italic;
  font-size: 16px;
  font-weight: 400;
  white-space: nowrap;
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
    background: #ffed4e !important;
  }
}

/* Execution mode row (above buttons, centered) */
.execution-mode-row {
  display: flex;
  justify-content: center;
  padding: 0 16px 12px 16px;
}

/* Execution mode radio buttons */
.execution-mode-radio {
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
  }

  .mode-radios {
    :deep(.v-selection-control-group) {
      gap: 16px;
    }

    :deep(.v-label) {
      font-size: 14px;
      color: rgba(var(--v-theme-on-surface), 0.7);
    }

    :deep(.v-selection-control--dirty .v-label) {
      color: #ffc300;
      font-weight: 500;
    }
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

/* Mobile Responsive */
@media (max-width: 600px) {
  .project-tabs-container {
    padding: 16px;
  }

  .project-header {
    .project-name {
      font-size: 1.5rem;
    }
  }

  .action-buttons-row {
    flex-wrap: wrap;
    gap: 8px;

    .status-text {
      font-size: 14px;
    }
  }
}
</style>
