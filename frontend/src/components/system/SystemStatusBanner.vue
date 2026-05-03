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
      type="warning"
      variant="tonal"
      density="compact"
      closable
      class="system-banner-alert"
      @click:close="dismissSkills"
    >
      <template #prepend>
        <v-icon>mdi-puzzle-outline</v-icon>
      </template>
      <span>{{ skillsDriftCopy }}</span>
    </v-alert>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { apiClient } from '@/services/api'
import setupService from '@/services/setupService'

const SESSION_KEY_MIGRATION = 'dismissed_migration_banner'
const SESSION_KEY_UPDATE = 'dismissed_update_banner'
const LOCAL_KEY_SKILLS_DISMISS_PREFIX = 'giljo_skills_dismissed_for_'

const userStore = useUserStore()

const pendingMigration = ref(false)
const updateAvailable = ref(false)
const commitsBehind = ref(0)

// Skills version drift state -- now driven entirely by the server contract
// `{ current, announced, drift_detected, message }`. The frontend no longer
// caches an "installed" version locally; the server alone decides drift.
const currentSkillsVersion = ref(null)
const skillsDriftDetected = ref(false)
const skillsDismissedForCurrent = ref(false)
const editionMode = ref('ce')

const migrationDismissed = ref(sessionStorage.getItem(SESSION_KEY_MIGRATION) === 'true')
const updateDismissed = ref(sessionStorage.getItem(SESSION_KEY_UPDATE) === 'true')

const isAdmin = computed(() => userStore.currentUser?.role === 'admin')

// Drift banner visibility: admin AND server says drift AND not dismissed for
// THIS specific bundled version. Per-version dismissal lives in localStorage
// under `giljo_skills_dismissed_for_<current>` and is the only client-side
// suppression input.
const showSkillsDrift = computed(() => {
  if (!isAdmin.value) return false
  if (!skillsDriftDetected.value) return false
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
  return `Updates available ${commitText}. Run \`git pull\`, then restart your server.`.trim()
})

// Edition-aware copy. CE users self-host (need git pull); demo/saas users
// run on the GiljoAI-hosted server and only need to refresh their CLI skills.
const skillsDriftCopy = computed(() => {
  const version = currentSkillsVersion.value ?? 'latest'
  if (editionMode.value === 'ce') {
    return `Skills updated to v${version}. Run /giljo_setup then git pull to install.`
  }
  return `Skills updated to v${version}. Run /giljo_setup to install.`
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

// Boot drift check. The server returns `{ current, announced, drift_detected,
// message }`. We trust `drift_detected` directly; per-user installed-version
// tracking is server-side state, not localStorage.
async function fetchSkillsDrift() {
  if (!isAdmin.value) return
  try {
    const response = await apiClient.get('/api/notifications/check-skills-version')
    const data = response.data ?? {}
    currentSkillsVersion.value = data.current ?? null
    skillsDriftDetected.value = data.drift_detected === true

    // Per-version dismissal — read AFTER we know `current` so a fresh drift
    // (newer bundled version) automatically reappears even if the user
    // dismissed a prior drift.
    if (currentSkillsVersion.value) {
      const dismissedKey = `${LOCAL_KEY_SKILLS_DISMISS_PREFIX}${currentSkillsVersion.value}`
      skillsDismissedForCurrent.value = localStorage.getItem(dismissedKey) === '1'
    } else {
      skillsDismissedForCurrent.value = false
    }
  } catch {
    // Drift endpoint may not exist on older servers — keep banner hidden.
    skillsDriftDetected.value = false
  }
}

// Read the edition mode from the authoritative source (setupService) on
// mount so banner copy adapts to CE vs demo/saas. Per ADR-002 we never read
// mode from configService.getGiljoMode() in first-paint code paths.
async function fetchEditionMode() {
  try {
    const status = await setupService.checkEnhancedStatus()
    if (status?.mode) {
      editionMode.value = status.mode
    }
  } catch {
    // Default ('ce') already set; safest fallback for self-hosted users.
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
      '1',
    )
  }
}

defineExpose({ dismissSkills })

onMounted(async () => {
  await Promise.all([fetchSystemStatus(), fetchSkillsDrift(), fetchEditionMode()])

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
