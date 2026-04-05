<template>
  <div
    class="intg-card smooth-border"
    style="--card-accent: #CE93D8"
  >
    <div class="intg-card-icon" style="background: rgba(206,147,216,0.12)">
      <v-avatar size="24" rounded="0">
        <v-img src="/Serena.png" alt="Serena MCP" />
      </v-avatar>
    </div>
    <div class="d-flex align-center" style="gap: 8px; margin-bottom: 5px;">
      <div class="intg-card-title" style="margin-bottom: 0">Serena MCP</div>
      <v-tooltip location="top" max-width="400">
        <template #activator="{ props }">
          <v-icon v-bind="props" size="small" style="color: #8895a8">mdi-help-circle-outline</v-icon>
        </template>
        <div>
          <strong>Intelligent codebase understanding and navigation</strong>
          <p class="mt-2 mb-0">
            Serena provides deep semantic code analysis, intelligent symbol navigation, and
            contextual understanding of your codebase. It enables agents to efficiently
            explore and understand project structure without reading unnecessary code,
            significantly improving performance and reducing token usage.
          </p>
          <p class="mt-2 mb-0 text-caption">
            <strong>Note:</strong> Serena must be installed separately in your AI coding agent.
          </p>
        </div>
      </v-tooltip>
    </div>
    <div class="intg-card-desc">Add Serena MCP tool instructions to agent prompts.</div>

    <div class="intg-card-body d-flex flex-column align-center">
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
      <v-btn
        variant="text"
        size="small"
        color="light-blue"
        href="https://github.com/oraios/serena"
        target="_blank"
        class="mt-2"
      >
        <v-icon start>mdi-github</v-icon>
        GitHub Repository
      </v-btn>
      <span class="text-caption mt-1" style="color: #8895a8">Credit: Oraios</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  enabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

defineEmits(['update:enabled'])
</script>

<style lang="scss" scoped>
@import '../../../styles/intg-card';
</style>
