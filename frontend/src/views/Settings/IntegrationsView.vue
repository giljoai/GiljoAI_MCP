<template>
  <v-container>
    <h1 class="text-h4 mb-6">API & Integrations</h1>
    <p class="text-subtitle-1 mb-6">
      Configure external AI tools to connect with GiljoAI MCP
    </p>

    <!-- MCP Configuration Component -->
    <McpConfigComponent />

    <!-- Slash Command Setup -->
    <SlashCommandSetup />

    <!-- Claude Code Agent Export -->
    <ClaudeCodeExport />
  </v-container>
</template>

<script setup>
import McpConfigComponent from '@/components/McpConfigComponent.vue'
import SlashCommandSetup from '@/components/SlashCommandSetup.vue'
import ClaudeCodeExport from '@/components/ClaudeCodeExport.vue'
</script>
