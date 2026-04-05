<template>
  <div
    class="intg-card intg-card--clickable smooth-border"
    style="--card-accent: var(--brand-yellow, #ffc300)"
    @click="wizardRef?.open()"
  >
    <div class="intg-card-icon" style="background: rgba(255,195,0,0.1)">
      <v-avatar size="24" rounded="0">
        <v-img src="/giljo_YW_Face.svg" alt="GiljoAI MCP" />
      </v-avatar>
    </div>
    <div class="d-flex align-center" style="gap: 8px; margin-bottom: 5px;">
      <div class="intg-card-title" style="margin-bottom: 0">GiljoAI MCP</div>
      <v-tooltip location="top" max-width="400">
        <template #activator="{ props }">
          <v-icon v-bind="props" size="small" style="color: #8895a8" @click.stop>mdi-help-circle-outline</v-icon>
        </template>
        <span>Connect your AI coding agent to GiljoAI orchestration. Supports Claude Code, Codex CLI, and Gemini CLI. Creates an MCP integration CLI command for your AI coding agent of choice.</span>
      </v-tooltip>
    </div>
    <div class="intg-card-desc">Click to attach GiljoAI MCP to your AI coding agents using the Configurator.</div>
    <div class="d-flex justify-center">
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
