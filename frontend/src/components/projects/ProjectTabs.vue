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
        <v-tab value="launch" class="tab-link">
          <v-icon start size="20">mdi-rocket-launch</v-icon>
          Launch
        </v-tab>

        <v-tab value="jobs" class="tab-link">
          <v-icon start size="20">mdi-code-braces</v-icon>
          Implement
          <v-badge v-if="store.unreadCount > 0" :content="store.unreadCount" color="error" inline />
        </v-tab>
      </v-tabs>

      <!-- Action Buttons (relocated from LaunchTab) -->
      <div class="action-buttons ml-auto d-flex align-center gap-2">
        <v-btn
          class="stage-button"
          variant="outlined"
          color="yellow-darken-2"
          rounded
          :loading="loadingStageProject"
          @click="handleStageProject"
        >
          Stage project
        </v-btn>

        <span class="status-text">Waiting:</span>

        <v-btn
          class="launch-button"
          :disabled="!readyToLaunch"
          :color="readyToLaunch ? 'yellow-darken-2' : 'grey'"
          rounded
          @click="handleLaunchJobs"
        >
          Launch jobs
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
          :is-staging="store.isStaging"
          :readonly="readonly"
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
          :project="project"
          :agents="store.sortedAgents"
          :messages="store.messages"
          :all-agents-complete="store.allAgentsComplete"
          :readonly="readonly"
          @launch-agent="handleLaunchAgent"
          @view-details="emit('view-details', $event)"
          @view-error="emit('view-error', $event)"
          @hand-over="handleHandOver"
          @closeout-project="handleCloseoutProject"
          @send-message="handleSendMessage"
        />
      </v-window-item>
    </v-window>

    <!-- Error Snackbar -->
    <v-snackbar v-model="errorVisible" color="error" :timeout="5000" location="top">
      <v-icon start>mdi-alert-circle</v-icon>
      {{ store.error }}
      <template #actions>
        <v-btn variant="text" @click="errorVisible = false"> Close </v-btn>
      </template>
    </v-snackbar>
  </v-card>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectTabsStore } from '@/stores/projectTabs'
import { useWebSocketStore } from '@/stores/websocket'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'
import LaunchTab from './LaunchTab.vue'
import JobsTab from './JobsTab.vue'

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
const store = useProjectTabsStore()
const wsStore = useWebSocketStore()
const route = useRoute()
const router = useRouter()

/**
 * Toast composable
 */
const { showToast } = useToast()

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
 * Backward compatibility with store
 */
const activeTabIndex = computed({
  get: () => store.activeTab,
  set: (value) => store.switchTab(value),
})

const errorVisible = ref(false)
const loadingStageProject = ref(false)

/**
 * Computed: Ready to launch (based on store state)
 */
const readyToLaunch = computed(() => {
  return store.readyToLaunch
})

/**
 * Watch for errors
 */
watch(
  () => store.error,
  (newError) => {
    if (newError) {
      errorVisible.value = true
    }
  },
)

/**
 * Set project on mount
 */
onMounted(async () => {
  store.setProject(props.project)

  // Load existing messages from database
  if (props.project) {
    const pid = props.project.project_id || props.project.id
    if (pid) {
      await store.loadMessages(pid)
    }
  }

  // Subscribe to WebSocket updates if project is launched
  if (store.isLaunched && props.project) {
    const pid = props.project.project_id || props.project.id
    if (pid) wsStore.subscribeToProject(pid)
  }
})

/**
 * Clean up on unmount
 */
onBeforeUnmount(() => {
  // Unsubscribe from WebSocket
  if (props.project) {
    const pid = props.project.project_id || props.project.id
    if (pid) wsStore.unsubscribe('project', pid)
  }
})

/**
 * Watch for project changes
 */
watch(
  () => props.project,
  async (newProject) => {
    if (newProject) {
      store.setProject(newProject)
      // Load messages for the new project
      const pid = newProject.project_id || newProject.id
      if (pid) {
        await store.loadMessages(pid)
      }
    }
  },
  { deep: true },
)

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
 * Handle stage project
 */
async function handleStageProject() {
  loadingStageProject.value = true

  try {
    // Generate thin client staging prompt
    const response = await api.prompts.staging(props.project.id, {
      tool: 'claude-code',
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
      showToast({
        message: 'Launch prompt copied to clipboard',
        type: 'success',
        duration: 3000
      })
    } else {
      alert(`Please manually copy this prompt:\n\n${prompt}`)
    }

    emit('stage-project')
  } catch (error) {
    console.error('Stage project failed:', error)
    store.error = error.message || 'Failed to stage project'
  } finally {
    loadingStageProject.value = false
  }
}

/**
 * Handle launch jobs
 */
async function handleLaunchJobs() {
  try {
    await store.launchJobs()
    emit('launch-jobs')

    // Auto-switch to Jobs/Implement tab after launch (Handover 0243e)
    activeTab.value = 'jobs'
  } catch (error) {
    console.error('Launch jobs failed:', error)
  }
}

/**
 * Handle cancel staging
 */
async function handleCancelStaging() {
  try {
    await store.cancelStaging()
    emit('cancel-staging')
  } catch (error) {
    console.error('Cancel staging failed:', error)
  }
}

/**
 * Handle launch agent
 */
async function handleLaunchAgent(agent) {
  try {
    await store.acknowledgeAgent(agent.job_id)
    emit('launch-agent', agent)
  } catch (error) {
    console.error('Launch agent failed:', error)
  }
}

/**
 * Handle closeout project
 */
async function handleCloseoutProject() {
  try {
    await store.closeoutProject()
    emit('closeout-project')
  } catch (error) {
    console.error('Closeout project failed:', error)
  }
}

/**
 * Handle orchestrator handover (Handover 0080a)
 */
async function handleHandOver(agent) {
  try {
    console.log('[ProjectTabs] Triggering succession for orchestrator:', agent.job_id)

    // Call trigger_succession API endpoint
    const response = await fetch(`/api/agent-jobs/${agent.job_id}/trigger_succession`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to trigger succession')
    }

    const result = await response.json()

    // Show success notification with launch prompt
    console.log('[ProjectTabs] Succession triggered successfully:', result)

    // TODO: Show LaunchSuccessorDialog with result.launch_prompt
    // For now, show simple confirmation
    alert(
      `✅ ${result.message}\n\n📋 Launch Prompt (copy to clipboard):\n\n${result.launch_prompt}`,
    )

    // Refresh agents to show new successor
    await store.loadAgents(project.value.id)
  } catch (error) {
    console.error('Hand over failed:', error)
    alert(`❌ Failed to trigger succession: ${error.message}`)
  }
}

/**
 * Handle send message
 */
async function handleSendMessage(message, recipient) {
  try {
    await store.sendMessage(message, recipient)
    emit('send-message', message, recipient)
  } catch (error) {
    console.error('Send message failed:', error)
  }
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
