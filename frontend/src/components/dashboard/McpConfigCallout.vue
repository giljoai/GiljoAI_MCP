<template>
  <v-alert
    v-if="shouldShow"
    type="info"
    variant="tonal"
    prominent
    closable
    @click:close="dismissCallout"
    class="mb-6"
  >
    <v-alert-title class="d-flex align-center">
      <v-icon start size="large">mdi-robot-excited</v-icon>
      <span class="text-h6">AI Tool Integration Available</span>
    </v-alert-title>

    <p class="mt-2 mb-3">
      Connect your AI coding tools to this GiljoAI MCP server. Works with
      <strong>Claude Code, Codex, Gemini, Cursor</strong> and more.
    </p>

    <div class="d-flex gap-3 flex-wrap">
      <v-btn
        color="primary"
        size="large"
        @click="navigateToConfig"
        prepend-icon="mdi-auto-fix"
        aria-label="Navigate to AI Tool Configuration settings"
      >
        Configure AI Tools
      </v-btn>

      <v-btn
        variant="text"
        @click="dismissCallout"
        aria-label="Dismiss this notification"
      >
        Maybe Later
      </v-btn>
    </div>
  </v-alert>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const shouldShow = ref(false)

onMounted(async () => {
  // Check if user dismissed callout
  const dismissed = localStorage.getItem('mcp-callout-dismissed')
  if (dismissed === 'true') {
    shouldShow.value = false
    return
  }

  // For now, show callout to all users (in real implementation, check MCP status)
  // In a full implementation, we would check the MCP status API:
  // const response = await api.get('/api/mcp-tools/status')
  // const status = response.data.status
  // if (status === 'not_started' || status === 'pending') {
  shouldShow.value = true
  // }
})

function navigateToConfig() {
  // Navigate to settings page with API tab active
  router.push({
    path: '/settings',
    hash: '#api',
    query: { tab: 'api' }
  })
}

function dismissCallout() {
  localStorage.setItem('mcp-callout-dismissed', 'true')
  shouldShow.value = false
}
</script>