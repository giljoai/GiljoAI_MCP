<template>
  <v-container>
    <h1 class="text-h4 mb-6">API & Integrations</h1>
    <p class="text-subtitle-1 mb-6">
      Configure external AI tools to connect with GiljoAI MCP
    </p>

    <!-- MCP Configuration Component -->
    <McpConfigComponent />
  </v-container>
</template>

<script setup>
import McpConfigComponent from '@/components/McpConfigComponent.vue'
</script>
