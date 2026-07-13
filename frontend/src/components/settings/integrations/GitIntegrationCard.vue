<template>
  <div class="intg-line smooth-border" :style="{ '--card-accent': cardGitColor }">
    <a
      class="intg-line-icon intg-line-icon--link"
      :style="{ background: cardGitBg, color: cardGitColor }"
      href="https://git-scm.com/book/en/v2/Getting-Started-First-Time-Git-Setup"
      target="_blank"
      rel="noopener"
      title="Git setup instructions"
    >
      <v-icon size="22">mdi-git</v-icon>
    </a>

    <div class="intg-line-main">
      <div class="intg-line-title-row">
        <span class="intg-line-title">Git + 360 Memory</span>
        <v-tooltip location="top" max-width="400">
          <template #activator="{ props }">
            <v-icon v-bind="props" size="small" style="color: var(--text-muted)">mdi-help-circle-outline</v-icon>
          </template>
          <div>
            <strong>Cumulative product knowledge tracking</strong>
            <p class="mt-2 mb-0">
              When enabled, GiljoAI captures git commit history at project closeout and stores
              it in 360 Memory. This provides orchestrators with cumulative context across all
              projects, including what was built, decisions made, and implementation patterns
              used.
            </p>
            <p class="mt-2 mb-0 text-body-small">
              <strong>Note:</strong> Git must be configured on your system with access to your
              repositories. 360 Memory is always added to the project.
            </p>
          </div>
        </v-tooltip>
      </div>
      <div class="intg-line-sub">Link git and 360 memory summaries</div>
    </div>

    <div class="intg-line-action">
      <v-btn
        :color="enabled ? 'success' : 'primary'"
        :variant="enabled ? 'flat' : 'outlined'"
        size="small"
        :loading="loading"
        data-testid="git-integration-toggle"
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
import { COLOR_CARD_GIT } from '@/config/colorTokens'

const cardGitColor = COLOR_CARD_GIT
const cardGitBg = hexToRgba(cardGitColor, 0.12)

defineProps({
  enabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

defineEmits(['update:enabled'])
</script>

<style lang="scss" scoped>
@use '../../../styles/intg-card';
</style>
