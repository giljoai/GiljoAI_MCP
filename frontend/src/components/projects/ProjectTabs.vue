<template>
  <v-card class="project-tabs-container" elevation="0">
    <!-- Tab Navigation with Action Buttons (Handover 0243e: Fixed activation state) -->
    <div class="tabs-header-container">
      <v-tabs
        v-model="activeTab"
        bg-color="transparent"
        class="tabs-header global-tabs"
        align-tabs="start"
      >
        <v-tab value="launch" class="tab-link" data-testid="launch-tab">
          <v-icon start size="20">mdi-rocket-launch</v-icon>
          Launch
        </v-tab>

        <v-tab value="jobs" class="tab-link" data-testid="jobs-tab">
          <v-icon start size="20">mdi-code-braces</v-icon>
          Implement
          <!-- Badge removed (Handover 0289): Messages now tracked per-agent in JobsTab table -->
        </v-tab>
      </v-tabs>

      <!-- Action Buttons (relocated from LaunchTab) -->
      <div class="action-buttons ml-auto d-flex align-center gap-2">
        <!-- Integration Status Icons (Handover 0427) -->
        <div class="integration-icons d-flex align-center gap-2 mr-2" data-testid="integration-status-icons">
          <!-- GitHub Integration -->
          <v-tooltip location="bottom" max-width="300">
            <template #activator="{ props: tooltipProps }">
              <v-icon
                v-bind="tooltipProps"
                :class="{ 'icon-disabled': !gitEnabled }"
                size="40"
                data-testid="github-status-icon"
                @click="goToIntegrations"
                style="cursor: pointer;"
              >
                mdi-github
              </v-icon>
            </template>
            <span v-if="gitEnabled">
              GitHub integration enabled. Commit history will be included in project summaries.
              <a href="#" @click.prevent="goToIntegrations">Settings → Integrations</a>
            </span>
            <span v-else>
              GitHub integration disabled.
              <a href="#" @click.prevent="goToIntegrations">Enable in Settings → Integrations</a>
            </span>
          </v-tooltip>

          <!-- Serena MCP Integration -->
          <v-tooltip location="bottom" max-width="300">
            <template #activator="{ props: tooltipProps }">
              <v-img
                v-bind="tooltipProps"
                src="/Serena.png"
                width="40"
                height="40"
                :class="{ 'icon-disabled': !serenaEnabled }"
                data-testid="serena-status-icon"
                @click="goToIntegrations"
                style="cursor: pointer;"
              />
            </template>
            <span v-if="serenaEnabled">
              Serena MCP enabled. Agents will use semantic code navigation.
              <a href="#" @click.prevent="goToIntegrations">Settings → Integrations</a>
            </span>
            <span v-else>
              Serena MCP disabled.
              <a href="#" @click.prevent="goToIntegrations">Enable in Settings → Integrations</a>
            </span>
          </v-tooltip>
        </div>

        <v-btn
          class="stage-button"
          variant="outlined"
          color="yellow-darken-2"
          rounded
          prepend-icon="mdi-content-copy"
          :loading="loadingStageProject"
          :disabled="hasActiveOrchestrator"
          :title="hasActiveOrchestrator ? 'An orchestrator is already active for this project' : 'Generate orchestrator prompt'"
          data-testid="stage-project-btn"
          @click="handleStageProject"
        >
          Stage Project
        </v-btn>

        <span class="status-text">Waiting:</span>

        <v-btn
          class="launch-button"
          :disabled="!readyToLaunch"
          :color="readyToLaunch ? 'yellow-darken-2' : 'grey'"
          rounded
          data-testid="launch-jobs-btn"
          @click="handleLaunchJobs"
        >
          Launch jobs
        </v-btn>

        <!-- Close Out Project Button (Handover 0361) -->
        <v-btn
          v-if="showCloseoutButton"
          class="closeout-btn"
          color="yellow-darken-2"
          variant="flat"
          prepend-icon="mdi-check-circle"
          rounded
          data-testid="close-project-btn"
          @click="openCloseoutModal"
        >
          Close Out Project
        </v-btn>
      </div>
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
          @execution-mode-changed="handleExecutionModeChanged"
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
      @complete="handleCloseoutComplete"
    />
  </v-card>
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

const projectId = computed(() => props.project?.project_id || props.project?.id || null)

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
 */
const showCloseoutButton = computed(() => {
  const jobs = sortedJobs.value || []
  if (!jobs.length) return false

  const allComplete = jobs.every((job) => job.status === 'complete')
  if (!allComplete) return false

  const orchestrator = jobs.find((job) => job.agent_display_name === 'orchestrator')
  return Boolean(orchestrator && orchestrator.status === 'complete')
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
  },
  { immediate: true },
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

onBeforeUnmount(() => {
  if (projectId.value) {
    wsStore.unsubscribe('project', projectId.value)
  }
  unsubscribeConnectionListener?.()
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
 * Handle execution mode changed from LaunchTab (Handover 0335)
 * Updates local project prop to ensure handleStageProject uses fresh value
 */
function handleExecutionModeChanged(newMode) {
  console.log('[ProjectTabs] Execution mode changed to:', newMode)
  executionMode.value = newMode || 'multi_terminal'
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
      console.log('[ProjectTabs] Orchestrator prompt copied to clipboard')
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
    activeTab.value = 'launch'
  } catch (error) {
    console.error('Closeout project failed:', error)
  }
}

/**
 * Handle orchestrator handover (Handover 0506)
 * Calls initiate-handover endpoint and copies prompt to clipboard
 * User pastes prompt into current orchestrator terminal
 */
async function handleHandOver(agent) {
  try {
    const jobId = agent?.job_id || agent?.agent_id || agent?.id
    if (!jobId) {
      throw new Error('Orchestrator job_id missing')
    }

    console.log('[ProjectTabs] Initiating handover for orchestrator:', jobId)

    const response = await api.agentJobs.initiateHandover(jobId)
    const prompt = response?.data?.prompt

    if (!prompt) {
      throw new Error('No handover prompt returned')
    }

    // Copy handover prompt to clipboard
    await navigator.clipboard.writeText(prompt)

    // Show success notification
    console.log('[ProjectTabs] Handover prompt copied to clipboard')
    alert('📋 Handover prompt copied!\n\nPaste into your current orchestrator terminal to trigger handover.')

  } catch (error) {
    console.error('Initiate handover failed:', error)
    alert(`❌ Failed to initiate handover: ${error.message}`)
  }
}

/**
 * Open closeout modal (Handover 0361)
 */
function openCloseoutModal() {
  showCloseoutModal.value = true
  console.log('[ProjectTabs] Opening closeout modal for project:', props.project.project_id || props.project.id)
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
}
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;
@use '@/styles/agent-colors.scss' as *;

.project-tabs-container {
  background: var(--color-bg-secondary);
  border-radius: $radius-lg;
  overflow: hidden;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tabs-header-container {
  display: flex;
  align-items: center;
  border-bottom: 2px solid rgba(255, 255, 255, 0.1);
  padding-right: 16px;
}

.tabs-header {
  background: transparent;
  flex: 0 0 auto;
  /* Custom tab styling is handled by global-tabs class */
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;

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

  /* Integration Status Icons (Handover 0427) */
  .integration-icons {
    .icon-disabled {
      opacity: 0.3;
      filter: grayscale(100%);
    }

    .v-icon:hover,
    .v-img:hover {
      transform: scale(1.1);
      transition: transform 0.2s ease;
    }
  }
}

.tabs-content {
  flex: 1;
  overflow: hidden;
  padding-top: 10px;

  :deep(.v-window-item) {
    height: 100%;
  }
}

/* Mobile Responsive */
@media (max-width: 600px) {
  .tabs-header-container {
    flex-wrap: wrap;
    padding-right: 8px;
  }

  .tabs-header {
    :deep(.v-tab) {
      font-size: 12px;
      padding: 0 12px;

      .v-icon {
        font-size: 18px;
      }
    }
  }

  .action-buttons {
    flex-wrap: wrap;
    gap: 8px;
    width: 100%;
    justify-content: flex-end;
    margin-top: 8px;

    .status-text {
      font-size: 14px;
    }
  }
}
</style>
