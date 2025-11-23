<template>
  <v-card class="project-tabs-container" elevation="0">
    <!-- Tab Navigation -->
    <v-tabs
      v-model="activeTabIndex"
      bg-color="transparent"
      color="white"
      class="tabs-header"
      align-tabs="start"
    >
      <v-tab value="launch"> Launch </v-tab>

      <v-tab value="jobs" :disabled="!store.isLaunched">
        Implementation
        <v-badge v-if="store.unreadCount > 0" :content="store.unreadCount" color="error" inline />
      </v-tab>
    </v-tabs>

    <!-- Tab Content -->
    <v-window v-model="activeTabIndex" class="tabs-content">
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
          v-if="store.isLaunched"
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
import { useProjectTabsStore } from '@/stores/projectTabs'
import { useWebSocketStore } from '@/stores/websocket'
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
 * Store
 */
const store = useProjectTabsStore()
const wsStore = useWebSocketStore()

/**
 * Local state
 */
const activeTabIndex = computed({
  get: () => store.activeTab,
  set: (value) => store.switchTab(value),
})

const errorVisible = ref(false)

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
 * Handle stage project
 */
async function handleStageProject() {
  try {
    await store.stageProject()
    emit('stage-project')
  } catch (error) {
    console.error('Stage project failed:', error)
  }
}

/**
 * Handle launch jobs
 */
async function handleLaunchJobs() {
  try {
    await store.launchJobs()
    emit('launch-jobs')

    // Auto-switch to Jobs tab
    store.switchTab('jobs')
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

.tabs-header {
  background: transparent;
  border-bottom: 1px solid rgba(158, 158, 158, 0.5);

  :deep(.v-tab) {
    text-transform: none;
    font-weight: 500;
    letter-spacing: 0;
    font-size: 16px;
    transition: all 0.3s ease;
    min-width: auto;
    padding: 0 16px;
  }

  :deep(.v-tab--selected) {
    color: white;
  }

  :deep(.v-tab:hover:not(.v-tab--disabled)) {
    background: transparent;
  }

  :deep(.v-tab--disabled) {
    opacity: 0.4;
    cursor: not-allowed;
  }

  :deep(.v-tab__slider) {
    background: white;
    height: 2px;
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
  .tabs-header {
    :deep(.v-tab) {
      font-size: 12px;
      padding: 0 12px;

      .v-icon {
        font-size: 18px;
      }
    }
  }
}
</style>
