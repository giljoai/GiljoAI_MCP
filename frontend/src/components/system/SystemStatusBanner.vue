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

    <v-alert
      v-if="showSkillsDrift"
      type="info"
      variant="tonal"
      density="compact"
      closable
      class="system-banner-alert"
      @click:close="dismissSkills"
    >
      <template #prepend>
        <v-icon>mdi-puzzle-outline</v-icon>
      </template>
      Your CLI skills are out of date. Run
      <code class="banner-code">/giljo_setup</code>
      (or <code class="banner-code">/gil_get_agents</code>) to refresh, then
      <code class="banner-code">git pull</code> for the latest server.
    </v-alert>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { apiClient } from '@/services/api'

const SESSION_KEY_MIGRATION = 'dismissed_migration_banner'
const SESSION_KEY_UPDATE = 'dismissed_update_banner'
const LOCAL_KEY_INSTALLED_SKILLS = 'giljo_skills_version'
const LOCAL_KEY_SKILLS_DISMISS_PREFIX = 'giljo_skills_dismissed_for_'

const userStore = useUserStore()

const pendingMigration = ref(false)
const updateAvailable = ref(false)
const commitsBehind = ref(0)

// Skills version drift state.
//   currentSkillsVersion = the bundled version returned by the server.
//   skillsDriftDetected  = server's drift verdict for the installed version.
//   skillsDismissedForCurrent = true once user has dismissed THIS version's banner.
const currentSkillsVersion = ref(null)
const skillsDriftDetected = ref(false)
const skillsDismissedForCurrent = ref(false)
const installedSkillsKnown = ref(false)

const migrationDismissed = ref(sessionStorage.getItem(SESSION_KEY_MIGRATION) === 'true')
const updateDismissed = ref(sessionStorage.getItem(SESSION_KEY_UPDATE) === 'true')

const isAdmin = computed(() => userStore.currentUser?.role === 'admin')

// Drift banner visibility rule:
//   - admin gate (skills install is admin-only)
//   - server reported drift_detected: true
//   - localStorage has a known installed version (recon Q4: missing key = suppress)
//   - user has not already dismissed THIS specific bundled version
const showSkillsDrift = computed(() => {
  if (!isAdmin.value) return false
  if (!skillsDriftDetected.value) return false
  if (!installedSkillsKnown.value) return false
  if (skillsDismissedForCurrent.value) return false
  return true
})

const showBanner = computed(() => {
  if (!isAdmin.value) return false
  const hasMigration = pendingMigration.value && !migrationDismissed.value
  const hasUpdate = updateAvailable.value && !updateDismissed.value
  return hasMigration || hasUpdate || showSkillsDrift.value
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

// Boot drift check (Phase 1 of Skills version tracking).
// Reads localStorage giljo_skills_version (written by setup:* WS handlers in
// stores/eventRoutes/systemEventRoutes.js), asks the server whether that
// installed version is current, and updates banner state accordingly.
async function fetchSkillsDrift() {
  if (!isAdmin.value) return
  try {
    const installed = localStorage.getItem(LOCAL_KEY_INSTALLED_SKILLS)
    installedSkillsKnown.value = installed !== null && installed !== ''

    const response = await apiClient.get('/api/notifications/check-skills-version', {
      params: { installed_skills_version: installed ?? undefined },
    })
    const data = response.data ?? {}
    currentSkillsVersion.value = data.current ?? null
    skillsDriftDetected.value = data.drift_detected === true

    // Per-version dismissal — read AFTER we know `current` so a fresh drift
    // (newer bundled version) automatically reappears even if the user
    // dismissed a prior drift.
    if (currentSkillsVersion.value) {
      const dismissedKey = `${LOCAL_KEY_SKILLS_DISMISS_PREFIX}${currentSkillsVersion.value}`
      skillsDismissedForCurrent.value = localStorage.getItem(dismissedKey) === 'true'
    }
  } catch {
    // Drift endpoint may not exist on older servers — keep banner hidden.
  }
}

function handleUpdateAvailableEvent(event) {
  const payload = event?.detail ?? event
  if (!payload) return
  updateAvailable.value = true
  if (typeof payload.commits_behind === 'number') {
    commitsBehind.value = payload.commits_behind
  }
  // Skills version may also have advanced server-side — re-check.
  fetchSkillsDrift()
}

function dismissMigration() {
  migrationDismissed.value = true
  sessionStorage.setItem(SESSION_KEY_MIGRATION, 'true')
}

function dismissUpdate() {
  updateDismissed.value = true
  sessionStorage.setItem(SESSION_KEY_UPDATE, 'true')
}

function dismissSkills() {
  skillsDismissedForCurrent.value = true
  if (currentSkillsVersion.value) {
    localStorage.setItem(
      `${LOCAL_KEY_SKILLS_DISMISS_PREFIX}${currentSkillsVersion.value}`,
      'true',
    )
  }
}

defineExpose({ dismissSkills })

onMounted(async () => {
  await Promise.all([fetchSystemStatus(), fetchSkillsDrift()])

  // Listen for WebSocket events dispatched by systemEventRoutes
  window.addEventListener('ws-system-update-available', handleUpdateAvailableEvent)
})

onUnmounted(() => {
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
