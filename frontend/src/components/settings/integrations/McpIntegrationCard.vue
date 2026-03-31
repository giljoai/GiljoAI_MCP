<template>
  <v-card variant="flat" class="smooth-border mb-4 integration-card">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-avatar size="40" rounded="0" class="mr-2">
          <v-img
            src="/giljo_YW_Face.svg"
            alt="GiljoAI MCP"
          />
        </v-avatar>
        <h3 class="text-h6 mb-0 mr-2">GiljoAI MCP Integration</h3>
        <v-tooltip location="top" max-width="400">
          <template #activator="{ props }">
            <v-icon v-bind="props" size="small" color="medium-emphasis">mdi-help-circle-outline</v-icon>
          </template>
          <span>Connect your AI coding agent to GiljoAI orchestration. Supports Claude Code, Codex CLI, and Gemini CLI. Creates an MCP integration CLI command for your AI coding agent of choice.</span>
        </v-tooltip>
      </div>
      <p class="text-body-2 mcp-text-muted mb-4">
        Attach GiljoAI MCP to your AI coding agents.
      </p>

      <!-- MCP Configuration Tool -->
      <v-card variant="tonal" class="mb-0">
        <v-card-text class="pa-3">
          <div class="d-flex align-center justify-between">
            <div class="flex-grow-1">
              <div class="text-subtitle-2 font-weight-medium">MCP Configuration Tool</div>
            </div>
            <AiToolConfigWizard />
          </div>
        </v-card-text>
      </v-card>
    </v-card-text>
  </v-card>
</template>

<script setup>
import AiToolConfigWizard from '@/components/AiToolConfigWizard.vue'
</script>

<style scoped>
.integration-card {
  background: var(--bg-raised, #1e3147);
  border-radius: 16px;
}

.mcp-text-muted {
  color: #8895a8;
}
</style>
