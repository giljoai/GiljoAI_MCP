<template>
  <span v-if="label" class="harness-chip" data-testid="harness-chip">
    detected: {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /**
   * Raw resolved_harness token from OrchestratorJobResponse.detected_harness
   * (TSK-9038 / BE-9035c). One of the concrete harness_resolver tokens, the
   * "generic" fail-safe, or null/undefined when nothing has been detected yet.
   */
  harness: {
    type: String,
    default: null,
  },
})

// ADR-010: rendering-only, never an input/auth signal. "generic" and absent
// both mean "nothing useful to show" -- no taxonomy is invented for either.
const HARNESS_LABELS = {
  'claude-code': 'Claude Code',
  codex: 'Codex',
  gemini: 'Gemini',
  antigravity: 'Antigravity',
  opencode: 'opencode',
}

const label = computed(() => HARNESS_LABELS[props.harness] || null)
</script>

<style scoped lang="scss">
@use '@/styles/design-tokens.scss' as *;

.harness-chip {
  display: inline-flex;
  align-items: center;
  border-radius: $border-radius-pill;
  padding: 3px 10px;
  font-size: 0.68rem;
  font-weight: 600;
  white-space: nowrap;
  background: rgba(var(--v-theme-on-surface), 0.08);
  color: var(--text-muted);
}
</style>
