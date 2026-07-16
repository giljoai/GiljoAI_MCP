<template>
  <v-container fluid class="hub-view pa-0" data-testid="hub-view">
    <!-- Header bar -->
    <div class="hub-view__header">
      <div class="hub-view__title">
        <v-icon size="22" class="mr-2">mdi-forum</v-icon>
        <h1 class="text-headline-small font-weight-bold">Message Hub</h1>
      </div>
      <div class="d-flex align-center ga-2">
        <v-btn
          variant="text"
          size="small"
          prepend-icon="mdi-delete-restore"
          data-testid="deleted-threads-btn"
          @click="openDeletedThreads"
        >
          Deleted
        </v-btn>
        <v-btn
          variant="tonal"
          size="small"
          prepend-icon="mdi-plus"
          class="hub-view__new-btn"
          data-testid="new-thread-btn"
          @click="showNewThread = true"
        >
          New Thread
        </v-btn>
      </div>
    </div>

    <!-- Main layout: thread list | timeline + composer -->
    <div class="hub-view__body">
      <!-- Left: two-tab thread list — "Project threads" (project-bound threads) +
           "General threads" (standalone), replacing the old top/bottom split (FE-9012c D2). -->
      <div class="hub-view__sidebar">
        <div class="tab-pills hub-view__tabs" role="tablist">
          <button
            type="button"
            class="pill-btn"
            :class="{ active: activeTab === 'project' }"
            role="tab"
            :aria-selected="activeTab === 'project' ? 'true' : 'false'"
            data-testid="hub-tab-project"
            @click="activeTab = 'project'"
          >
            Project threads
            <span
              v-if="commHub.projectUnreadTotal > 0"
              class="hub-view__tab-badge smooth-border"
              :style="tabBadgeStyle"
              data-testid="hub-tab-project-unread"
            >{{ commHub.projectUnreadTotal }}</span>
          </button>
          <button
            type="button"
            class="pill-btn"
            :class="{ active: activeTab === 'town' }"
            role="tab"
            :aria-selected="activeTab === 'town' ? 'true' : 'false'"
            data-testid="hub-tab-town"
            @click="activeTab = 'town'"
          >
            General threads
            <span
              v-if="commHub.townSquareUnreadTotal > 0"
              class="hub-view__tab-badge smooth-border"
              :style="tabBadgeStyle"
              data-testid="hub-tab-town-unread"
            >{{ commHub.townSquareUnreadTotal }}</span>
          </button>
        </div>
        <ThreadList class="hub-view__thread-list" :scope="activeTab" @select="onThreadSelect" />
      </div>

      <!-- Right: timeline + composer -->
      <div class="hub-view__main">
        <div v-if="!commHub.selectedThreadId" class="hub-view__no-thread">
          <v-icon size="48" class="mb-3" color="grey-darken-1">mdi-forum-outline</v-icon>
          <p class="text-body-medium" style="color: var(--text-muted)">
            Select a thread from the list to view messages and reply.
          </p>
        </div>

        <template v-else>
          <ThreadTimeline class="hub-view__timeline" />
          <HubComposer class="hub-view__composer" />
        </template>
      </div>
    </div>

    <!-- New thread dialog -->
    <NewThreadDialog
      v-model="showNewThread"
      @created="onThreadCreated"
    />

    <!-- Post-create hint: thread id + copy affordance -->
    <ThreadCreatedDialog
      v-model="showThreadCreated"
      :thread="createdThread"
    />

    <!-- Deleted threads: recover surface -->
    <ThreadDeletedDialog
      v-model="showDeletedThreads"
      :deleted-threads="deletedThreads"
      :restoring-id="restoringId"
      @restore="onRestoreThread"
    />
  </v-container>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { useCommHubStore } from '@/stores/commHubStore'
import { registerReconnectResync } from '@/stores/websocketEventRouter'
import { useHubNotifications } from '@/composables/useHubNotifications'
import { useToast } from '@/composables/useToast'
import { getAgentColor } from '@/config/agentColors'
import { hexToRgba } from '@/utils/colorUtils'
import api from '@/services/api'
import ThreadList from '@/components/hub/ThreadList.vue'
import ThreadTimeline from '@/components/hub/ThreadTimeline.vue'
import HubComposer from '@/components/hub/HubComposer.vue'
import NewThreadDialog from '@/components/hub/NewThreadDialog.vue'
import ThreadCreatedDialog, { isThreadCreatedHintHidden } from '@/components/hub/ThreadCreatedDialog.vue'
import ThreadDeletedDialog from '@/components/hub/ThreadDeletedDialog.vue'

const commHub = useCommHubStore()
const route = useRoute()
const { showToast } = useToast()
const showNewThread = ref(false)
const showThreadCreated = ref(false)
const createdThread = ref(null)
const showDeletedThreads = ref(false)
const deletedThreads = ref([])
const restoringId = ref(null)

// FE-9012c (D2): which tab is active. 'project' (project-bound) is primary — the
// /jobs message icon deep-links here to a project's bound thread (D3).
const activeTab = ref('project')

// Per-tab unread badge: tinted implementer sky-blue (matches ThreadList's per-row badge).
const tabBadgeStyle = (() => {
  const hex = getAgentColor('implementer')?.hex
  return { backgroundColor: hexToRgba(hex, 0.2), color: hex, borderRadius: '8px' }
})()

// Wire hub notifications (away alerts, browser push, baton signalling)
useHubNotifications()

let unregisterResync = null

onMounted(async () => {
  // Initial load
  await commHub.loadThreads()

  // FE-9012c (D3): the /jobs message icon deep-links via ?thread=<id>&tab=project.
  // Honor an explicit tab, then pre-select the thread and align the tab to its
  // binding (project_id present => Project threads, else General threads).
  if (route.query.tab === 'project' || route.query.tab === 'town') {
    activeTab.value = route.query.tab
  }
  const deepLinkThreadId = route.query.thread
  if (deepLinkThreadId) {
    await onThreadSelect(deepLinkThreadId)
    const t = commHub.threadsById.get(deepLinkThreadId)
    if (t) activeTab.value = t.project_id != null ? 'project' : 'town'
  }

  // Register reconnect-resync: reload threads and re-fetch selected thread on WS reconnect
  unregisterResync = registerReconnectResync(async () => {
    await commHub.loadThreads(commHub.filters)
    if (commHub.selectedThreadId) {
      await commHub.loadThread(commHub.selectedThreadId)
    }
  })
})

onBeforeUnmount(() => {
  if (typeof unregisterResync === 'function') unregisterResync()
})

async function onThreadSelect(threadId) {
  await commHub.loadThread(threadId)
  await commHub.loadParticipants(threadId)
}

function onThreadCreated(thread) {
  if (thread?.thread_id) {
    commHub.selectThread(thread.thread_id)
    commHub.loadThread(thread.thread_id)
    commHub.loadParticipants(thread.thread_id)
    // Surface the copyable thread id once, unless the operator opted out forever.
    if (!isThreadCreatedHintHidden()) {
      createdThread.value = thread
      showThreadCreated.value = true
    }
  }
}

async function openDeletedThreads() {
  showDeletedThreads.value = true
  try {
    const res = await api.threads.getDeleted()
    deletedThreads.value = res.data.threads ?? []
  } catch (err) {
    const msg = err?.response?.data?.detail ?? 'Failed to load deleted threads.'
    showToast({ type: 'error', message: msg })
  }
}

async function onRestoreThread(thread) {
  restoringId.value = thread.thread_id
  try {
    await api.threads.restore(thread.thread_id)
    deletedThreads.value = deletedThreads.value.filter((t) => t.thread_id !== thread.thread_id)
    showToast({ type: 'success', message: `Thread ${thread.chat_id || thread.thread_id} restored.` })
    await commHub.loadThreads(commHub.filters)
  } catch (err) {
    const msg = err?.response?.data?.detail ?? 'Failed to restore thread.'
    showToast({ type: 'error', message: msg })
  } finally {
    restoringId.value = null
  }
}
</script>

<style scoped lang="scss">
@use '../styles/variables' as v;

.hub-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px); // subtract top nav
  overflow: hidden;

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: v.$spacing-md v.$spacing-lg;
    flex-shrink: 0;
  }

  &__title {
    display: flex;
    align-items: center;
  }

  &__body {
    display: flex;
    flex: 1;
    gap: v.$spacing-md;
    padding: 0 v.$spacing-md v.$spacing-md;
    overflow: hidden;
  }

  &__sidebar {
    width: 300px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  // FE-9012c (D2): the two-tab toggle sits above the thread list.
  &__tabs {
    flex-shrink: 0;
    padding: v.$spacing-xs 0 v.$spacing-sm;
  }

  &__tab-badge {
    font-size: 0.62rem;
    font-weight: 700;
    line-height: 1;
    padding: 2px 6px;
    margin-left: 2px;
  }

  &__thread-list {
    flex: 1;
    min-height: 0;
  }

  &__main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  &__no-thread {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: v.$spacing-xl;
  }

  &__timeline {
    flex: 1;
    overflow-y: auto;
  }

  &__composer {
    flex-shrink: 0;
  }
}
</style>
