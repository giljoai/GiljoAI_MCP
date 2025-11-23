<template>
  <v-container>
    <h1 class="text-h4 mb-2">My API Keys</h1>
    <p class="text-subtitle-1 mb-4">
      Manage API keys for MCP tool integrations (Claude Code, Codex CLI, etc.)
    </p>

    <v-alert type="info" variant="tonal" class="mb-4" data-test="api-key-info-alert">
      API keys authenticate your coding tools with the GiljoAI MCP server. These are NOT used for
      dashboard login (use your username/password for that).
    </v-alert>

    <ApiKeyManager />
  </v-container>
</template>

<script setup>
import ApiKeyManager from '@/components/ApiKeyManager.vue'
</script>
