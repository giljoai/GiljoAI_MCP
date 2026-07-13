<template>
  <div class="intg-line smooth-border" style="--card-accent: var(--color-accent-primary)">
    <div
      class="intg-line-icon intg-line-icon--link"
      style="background: rgba(255,195,0,0.1)"
      title="Open the Configurator"
      @click="wizardRef?.open()"
    >
      <v-img src="/giljo_YW_Face.svg" alt="GiljoAI MCP" width="26" height="26" />
    </div>

    <div class="intg-line-main">
      <div class="intg-line-title-row">
        <span class="intg-line-title">Connect GiljoAI MCP</span>
        <v-tooltip location="top" max-width="400">
          <template #activator="{ props }">
            <v-icon v-bind="props" size="small" style="color: var(--text-muted)" @click.stop>mdi-help-circle-outline</v-icon>
          </template>
          <span>Connect your AI coding agent to GiljoAI orchestration. Supports Claude Code CLI, Claude Desktop, Codex CLI, and Gemini CLI. Creates an MCP integration CLI command for your AI coding agent of choice.</span>
        </v-tooltip>
      </div>
      <div class="intg-line-sub">Attach your AI coding agents.</div>
    </div>

    <div class="intg-line-action">
      <AiToolConfigWizard ref="wizardRef" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AiToolConfigWizard from '@/components/AiToolConfigWizard.vue'

const wizardRef = ref(null)
</script>

<style lang="scss" scoped>
@use '../../../styles/intg-card';
</style>
