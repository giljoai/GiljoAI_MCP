<!--
  Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
  Licensed under the GiljoAI Community License v1.1.
  See LICENSE in the project root for terms.
  [CE] Community Edition — source-available, single-user use only.
-->
<template>
  <div v-if="showBanner" class="system-status-banner">
    <v-alert
      v-if="pendingMigration && !migrationDismissed"
      type="warning"
      variant="tonal"
      density="compact"
      closable
      class="system-banner-alert"
      @click:close="dismissMigration"
    >
      <template #prepend>
        <v-icon>mdi-database-alert</v-icon>
      </template>
      Database needs updating. Run <code class="banner-code">python update.py</code> to apply pending migrations.
    </v-alert>

    <v-alert
      v-if="updateAvailable && !updateDismissed"
      type="info"
      variant="tonal"
      density="compact"
      closable
      class="system-banner-alert"
      @click:close="dismissUpdate"
    >
      <template #prepend>
        <v-icon>mdi-download</v-icon>
      </template>
      {{ updateMessage }}
    </v-alert>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { useWebSocketStore } from '@/stores/websocket'
import { apiClient } from '@/services/api'

const SESSION_KEY_MIGRATION = 'dismissed_migration_banner'
const SESSION_KEY_UPDATE = 'dismissed_update_banner'

const userStore = useUserStore()
const wsStore = useWebSocketStore()

const pendingMigration = ref(false)
const updateAvailable = ref(false)
const commitsBehind = ref(0)

const migrationDismissed = ref(sessionStorage.getItem(SESSION_KEY_MIGRATION) === 'true')
const updateDismissed = ref(sessionStorage.getItem(SESSION_KEY_UPDATE) === 'true')

const isAdmin = computed(() => userStore.currentUser?.role === 'admin')

const showBanner = computed(() => {
  if (!isAdmin.value) return false
  const hasMigration = pendingMigration.value && !migrationDismissed.value
  const hasUpdate = updateAvailable.value && !updateDismissed.value
  return hasMigration || hasUpdate
})

const updateMessage = computed(() => {
  const behind = commitsBehind.value
  const commitText = behind > 0 ? `(${behind} commit${behind === 1 ? '' : 's'} behind)` : ''
  return `Updates available ${commitText}. Run \`git pull\` then \`python update.py\``.trim()
})

async function fetchSystemStatus() {
  if (!isAdmin.value) return
  try {
    const response = await apiClient.get('/api/system/status')
    const data = response.data
    pendingMigration.value = data?.pending_migrations === true
    updateAvailable.value = data?.update_available === true
    commitsBehind.value = data?.commits_behind ?? 0
  } catch {
    // Status endpoint may not exist yet -- fail silently, banners stay hidden
  }
}

function handleUpdateAvailableEvent(event) {
  const payload = event?.detail ?? event
  if (!payload) return
  updateAvailable.value = true
  if (typeof payload.commits_behind === 'number') {
    commitsBehind.value = payload.commits_behind
  }
}

function dismissMigration() {
  migrationDismissed.value = true
  sessionStorage.setItem(SESSION_KEY_MIGRATION, 'true')
}

function dismissUpdate() {
  updateDismissed.value = true
  sessionStorage.setItem(SESSION_KEY_UPDATE, 'true')
}

let unsubscribeWs = null

onMounted(async () => {
  await fetchSystemStatus()

  // Register WebSocket handler for real-time update notifications
  unsubscribeWs = wsStore.on('system:update_available', (payload) => {
    handleUpdateAvailableEvent(payload)
  })

  // Also listen for the window event dispatched by systemEventRoutes
  window.addEventListener('ws-system-update-available', handleUpdateAvailableEvent)
})

onUnmounted(() => {
  if (typeof unsubscribeWs === 'function') {
    unsubscribeWs()
  }
  window.removeEventListener('ws-system-update-available', handleUpdateAvailableEvent)
})
</script>

<style scoped>
.system-status-banner {
  position: sticky;
  top: 0;
  z-index: 100;
}

.system-banner-alert {
  border-radius: 0;
  margin-bottom: 0;
}

.banner-code {
  background: rgba(255, 255, 255, 0.15);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}
</style>
