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
      <p class="text-body-2 text-muted-a11y mb-4">
        Attach GiljoAI MCP to your AI coding agents.
      </p>

      <div class="d-flex justify-center">
        <AiToolConfigWizard />
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import AiToolConfigWizard from '@/components/AiToolConfigWizard.vue'
</script>

<style lang="scss" scoped>
@use '../../../styles/design-tokens' as *;
.integration-card {
  background: $elevation-raised;
  border-radius: $border-radius-rounded;
}
</style>
