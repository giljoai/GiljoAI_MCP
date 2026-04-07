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
      <div v-if="localEnabled" class="auto-checkin-slider-wrap" data-testid="auto-checkin-interval">
        <v-slider
          v-model="sliderIndex"
          :min="0"
          :max="intervals.length - 1"
          :step="1"
          :ticks="tickLabels"
          show-ticks="always"
          hide-details
          density="compact"
          color="rgb(var(--v-theme-primary))"
          track-color="rgba(255,255,255,0.12)"
          class="auto-checkin-slider"
          data-testid="auto-checkin-slider"
          @update:model-value="onSliderChange"
        />
        <span class="auto-checkin-value">{{ intervals[sliderIndex] }} min</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

/**
 * AutoCheckinControls — auto check-in toggle and interval slider extracted from JobsTab.
 * Parent (JobsTab) manages persistence via API; this component only owns local display state.
 * Handover 0960: Replaced v-btn-toggle (30/60/90s) with mapped-index v-slider (5-60 min).
 */

const intervals = [5, 10, 15, 20, 30, 40, 60]

const props = defineProps({
  enabled: {
    type: Boolean,
    default: false,
  },
  interval: {
    type: Number,
    default: 10,
  },
})

const emit = defineEmits(['toggle-checkin', 'change-interval'])

const localEnabled = ref(props.enabled)

function minutesToIndex(minutes) {
  const idx = intervals.indexOf(minutes)
  return idx >= 0 ? idx : 1
}

const sliderIndex = ref(minutesToIndex(props.interval))

const tickLabels = computed(() => {
  const labels = {}
  for (let i = 0; i < intervals.length; i++) {
    labels[i] = `${intervals[i]}`
  }
  return labels
})

watch(() => props.enabled, (val) => { localEnabled.value = val })
watch(() => props.interval, (val) => { sliderIndex.value = minutesToIndex(val) })

function onToggle(val) {
  emit('toggle-checkin', val)
}

function onSliderChange(idx) {
  emit('change-interval', intervals[idx])
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
    gap: 12px;
  }

  .auto-checkin-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .auto-checkin-toggle {
    flex-shrink: 0;
  }

  .auto-checkin-slider-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
    min-width: 0;
  }

  .auto-checkin-slider {
    flex: 1;
    min-width: 120px;

    :deep(.v-slider-track__tick-label) {
      font-size: 0.62rem;
      color: $color-text-muted;
    }
  }

  .auto-checkin-value {
    font-size: 0.72rem;
    font-weight: 600;
    color: $color-text-secondary;
    white-space: nowrap;
    min-width: 42px;
    text-align: right;
  }
}
</style>
