<template>
  <v-dialog v-model="showDialog" max-width="520" persistent>
    <v-card>
      <v-card-title class="d-flex align-center pa-4">
        <v-icon color="warning" class="mr-2">mdi-license</v-icon>
        Commercial License Required
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-5">
        <p class="text-body-1 mb-4">
          This GiljoAI MCP installation has
          <strong>{{ userCount }} user accounts</strong>.
        </p>
        <p class="text-body-2 mb-4">
          The <strong>Community Edition</strong> is licensed for single-user use.
          Multi-user deployments require a Commercial License from GiljoAI LLC.
        </p>
        <p class="text-body-2 text-medium-emphasis">
          Commercial Licenses may be obtained at no cost at GiljoAI LLC's discretion.
        </p>

        <v-alert type="info" variant="tonal" density="compact" class="mt-4">
          <template v-slot:text>
            Contact <strong>licensing@giljoai.com</strong> to obtain a Commercial License.
          </template>
        </v-alert>
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn color="primary" variant="flat" @click="dismiss">
          I Understand
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const STORAGE_KEY = 'giljo_license_dismissed_at'
const REMINDER_DAYS = 30

const showDialog = ref(false)
const userCount = ref(0)

async function checkLicensing() {
  try {
    const apiBaseUrl =
      window.API_BASE_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:7272'
    const response = await fetch(`${apiBaseUrl}/api/setup/status`, {
      method: 'GET',
      cache: 'no-cache',
    })

    if (!response.ok) return

    const data = await response.json()
    const totalUsers = data.total_users_count || 0

    if (totalUsers <= 1) return

    userCount.value = totalUsers

    // Check if dismissed within the last 30 days
    const dismissedAt = localStorage.getItem(STORAGE_KEY)
    if (dismissedAt) {
      const dismissedDate = new Date(dismissedAt)
      const now = new Date()
      const daysSince = (now - dismissedDate) / (1000 * 60 * 60 * 24)
      if (daysSince < REMINDER_DAYS) return
    }

    showDialog.value = true
  } catch {
    // Silently fail - don't block the app over licensing check
  }
}

function dismiss() {
  localStorage.setItem(STORAGE_KEY, new Date().toISOString())
  showDialog.value = false
}

onMounted(() => {
  checkLicensing()
})
</script>
