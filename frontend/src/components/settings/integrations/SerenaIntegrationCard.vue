<template>
  <div class="intg-line smooth-border" :style="{ '--card-accent': cardSerenaColor }">
    <a
      class="intg-line-icon intg-line-icon--link"
      :style="{ background: hexToRgba(cardSerenaColor, 0.12) }"
      href="https://github.com/oraios/serena"
      target="_blank"
      rel="noopener"
      title="Serena on GitHub (credit: Oraios)"
    >
      <v-img src="/Serena.png" alt="Serena MCP" width="26" height="26" />
    </a>

    <div class="intg-line-main">
      <div class="intg-line-title-row">
        <span class="intg-line-title">Serena MCP</span>
        <v-tooltip location="top" max-width="400">
          <template #activator="{ props }">
            <v-icon v-bind="props" size="small" style="color: var(--text-muted)">mdi-help-circle-outline</v-icon>
          </template>
          <div>
            <strong>Intelligent codebase understanding and navigation</strong>
            <p class="mt-2 mb-0">
              Serena provides deep semantic code analysis, intelligent symbol navigation, and
              contextual understanding of your codebase. It enables agents to efficiently
              explore and understand project structure without reading unnecessary code,
              significantly improving performance and reducing token usage.
            </p>
            <p class="mt-2 mb-0 text-body-small">
              <strong>Note:</strong> Serena must be installed separately in your AI coding agent.
            </p>
          </div>
        </v-tooltip>
      </div>
      <div class="intg-line-sub">Connect Serena MCP code tools</div>
    </div>

    <div class="intg-line-action">
      <v-btn
        :color="enabled ? 'success' : 'primary'"
        :variant="enabled ? 'flat' : 'outlined'"
        size="small"
        :loading="loading"
        class="intg-toggle-pill"
        @click="$emit('update:enabled', !enabled)"
      >
        <v-icon v-if="enabled" start size="16">mdi-check</v-icon>
        {{ enabled ? 'Enabled' : 'Disabled' }}
      </v-btn>
    </div>
  </div>
</template>

<script setup>
import { hexToRgba } from '@/utils/colorUtils'
import { COLOR_CARD_SERENA } from '@/config/colorTokens'

const cardSerenaColor = COLOR_CARD_SERENA

defineProps({
  enabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

defineEmits(['update:enabled'])
</script>

<style lang="scss" scoped>
@use '../../../styles/intg-card';
</style>
