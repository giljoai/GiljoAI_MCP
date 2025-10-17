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
      <span class="text-h6">🚀 Revolutionary AI Tool Integration</span>
    </v-alert-title>

    <p class="mt-2 mb-3">
      Your AI coding tool can now configure itself automatically! Works with 
      <strong>Claude Code, Codex, Gemini, Cursor</strong> and more.
    </p>

    <div class="d-flex gap-3 flex-wrap">
      <v-btn
        color="primary"
        size="large"
        @click="navigateToConfig"
        prepend-icon="mdi-auto-fix"
      >
        Auto-Configure (Recommended)
      </v-btn>

      <v-btn
        variant="outlined"
        @click="navigateToConfig"
        prepend-icon="mdi-cog"
      >
        Manual Setup
      </v-btn>

      <v-btn
        variant="text"
        @click="dismissCallout"
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
  router.push({
    path: '/settings',
    query: { from: 'dashboard', step: 'mcp' }
  })
}

function dismissCallout() {
  localStorage.setItem('mcp-callout-dismissed', 'true')
  shouldShow.value = false
}
</script>