<template>
  <v-card class="project-tabs-container" elevation="0">
    <!-- Tab Navigation -->
    <v-tabs
      v-model="activeTabIndex"
      bg-color="transparent"
      color="accent-primary"
      class="tabs-header"
      grow
    >
      <v-tab value="launch">
        <v-icon start>mdi-rocket-launch-outline</v-icon>
        Launch
      </v-tab>

      <v-tab
        value="jobs"
        :disabled="!store.isLaunched"
      >
        <v-icon start>mdi-briefcase-outline</v-icon>
        Jobs
        <v-badge
          v-if="store.unreadCount > 0"
          :content="store.unreadCount"
          color="error"
          inline
        />
      </v-tab>
    </v-tabs>

    <!-- Tab Content -->
    <v-window v-model="activeTabIndex" class="tabs-content">
      <!-- Launch Tab -->
      <v-window-item value="launch">
        <LaunchTab
          :project="project"
          :is-staging="store.isStaging"
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
          @launch-agent="handleLaunchAgent"
          @view-details="emit('view-details', $event)"
          @view-error="emit('view-error', $event)"
          @closeout-project="handleCloseoutProject"
          @send-message="handleSendMessage"
        />
      </v-window-item>
    </v-window>

    <!-- Error Snackbar -->
    <v-snackbar
      v-model="errorVisible"
      color="error"
      :timeout="5000"
      location="top"
    >
      <v-icon start>mdi-alert-circle</v-icon>
      {{ store.error }}
      <template #actions>
        <v-btn
          variant="text"
          @click="errorVisible = false"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </v-card>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useProjectTabsStore } from '@/stores/projectTabs'
import { useWebsocketStore } from '@/stores/websocket'
import LaunchTab from './LaunchTab.vue'
import JobsTab from './JobsTab.vue'

/**
 * Props
 */
const props = defineProps({
  project: {
    type: Object,
    required: true
  }
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
  'send-message'
])

/**
 * Store
 */
const store = useProjectTabsStore()
const wsStore = useWebsocketStore()

/**
 * Local state
 */
const activeTabIndex = computed({
  get: () => store.activeTab,
  set: (value) => store.switchTab(value)
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
  }
)

/**
 * Set project on mount
 */
onMounted(() => {
  store.setProject(props.project)

  // Subscribe to WebSocket updates if project is launched
  if (store.isLaunched) {
    wsStore.subscribeToProject(props.project.project_id)
  }
})

/**
 * Clean up on unmount
 */
onBeforeUnmount(() => {
  // Unsubscribe from WebSocket
  if (props.project) {
    wsStore.unsubscribe('project', props.project.project_id)
  }
})

/**
 * Watch for project changes
 */
watch(
  () => props.project,
  (newProject) => {
    if (newProject) {
      store.setProject(newProject)
    }
  },
  { deep: true }
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
@import '@/styles/variables.scss';
@import '@/styles/agent-colors.scss';

.project-tabs-container {
  background: var(--color-bg-secondary);
  border-radius: $radius-lg;
  overflow: hidden;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tabs-header {
  background: var(--color-bg-primary);
  border-bottom: 2px solid rgba(255, 255, 255, 0.1);

  :deep(.v-tab) {
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.5px;
    font-size: 14px;
    transition: all 0.3s ease;

    &--selected {
      color: var(--color-accent-primary);
    }

    &:hover:not(.v-tab--disabled) {
      background: rgba(255, 255, 255, 0.05);
    }

    &--disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
  }

  :deep(.v-tab__slider) {
    background: var(--color-accent-primary);
    height: 3px;
  }
}

.tabs-content {
  flex: 1;
  overflow: hidden;

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
