<template>
  <div class="auto-checkin-section" data-testid="auto-checkin">
    <div class="auto-checkin-row">
      <span class="auto-checkin-label">Orchestrator Auto Check-in</span>
      <v-switch
        v-model="localEnabled"
        density="compact"
        hide-details
        color="rgb(var(--v-theme-primary))"
        class="auto-checkin-toggle"
        data-testid="auto-checkin-toggle"
        @update:model-value="onToggle"
      />
    </div>
    <div v-if="localEnabled" class="auto-checkin-interval" data-testid="auto-checkin-interval">
      <span class="auto-checkin-interval-label">Check-in every:</span>
      <v-btn-toggle
        v-model="localInterval"
        mandatory
        density="compact"
        class="auto-checkin-btn-group"
        @update:model-value="onIntervalChange"
      >
        <v-btn :value="30" size="small" variant="outlined">0:30</v-btn>
        <v-btn :value="60" size="small" variant="outlined">1:00</v-btn>
        <v-btn :value="90" size="small" variant="outlined">1:30</v-btn>
      </v-btn-toggle>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

/**
 * AutoCheckinControls — auto check-in toggle and interval selector extracted from JobsTab.
 * Parent (JobsTab) manages persistence via API; this component only owns local display state.
 */

const props = defineProps({
  enabled: {
    type: Boolean,
    default: false,
  },
  interval: {
    type: Number,
    default: 60,
  },
})

const emit = defineEmits(['toggle-checkin', 'change-interval'])

const localEnabled = ref(props.enabled)
const localInterval = ref(props.interval)

watch(() => props.enabled, (val) => { localEnabled.value = val })
watch(() => props.interval, (val) => { localInterval.value = val })

function onToggle(val) {
  emit('toggle-checkin', val)
}

function onIntervalChange(val) {
  emit('change-interval', val)
}
</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;

.auto-checkin-section {
  padding: 10px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);

  .auto-checkin-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .auto-checkin-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-muted);
  }

  .auto-checkin-toggle {
    flex-shrink: 0;
  }

  .auto-checkin-interval {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 6px;
  }

  .auto-checkin-interval-label {
    font-size: 0.72rem;
    color: var(--text-muted);
  }

  .auto-checkin-btn-group {
    :deep(.v-btn) {
      font-size: 0.72rem;
      min-width: 48px;
      height: 28px;
      text-transform: none;
    }
  }
}
</style>
