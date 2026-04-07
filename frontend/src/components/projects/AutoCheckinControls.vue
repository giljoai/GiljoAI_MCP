<template>
  <div class="auto-checkin-section" data-testid="auto-checkin">
    <div class="auto-checkin-row">
      <span class="auto-checkin-label">
        Auto Check-in
        <v-tooltip location="top" max-width="260">
          <template #activator="{ props: tip }">
            <v-icon v-bind="tip" size="14" class="auto-checkin-help">mdi-help-circle-outline</v-icon>
          </template>
          When enabled, the orchestrator automatically checks in on agent progress at the selected interval and coordinates as needed.
        </v-tooltip>
      </span>
      <v-slider
        v-model="sliderIndex"
        :min="0"
        :max="steps.length - 1"
        :step="1"
        thumb-label="always"
        hide-details
        density="compact"
        :color="isEnabled ? 'rgb(var(--v-theme-primary))' : 'grey'"
        track-color="rgba(255,255,255,0.12)"
        class="auto-checkin-slider"
        data-testid="auto-checkin-slider"
        @update:model-value="onSliderChange"
      >
        <template #thumb-label="{ modelValue }">
          {{ steps[modelValue].label }}
        </template>
      </v-slider>
      <span v-if="isEnabled" class="auto-checkin-value">min</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

/**
 * AutoCheckinControls — combined off/interval slider for orchestrator auto check-in.
 * Index 0 = Off, indices 1-7 = minute intervals. No separate toggle needed.
 * Handover 0960: Replaced v-btn-toggle (30/60/90s) with unified slider.
 */

const steps = [
  { label: 'Off', minutes: null },
  { label: '5',   minutes: 5 },
  { label: '10',  minutes: 10 },
  { label: '15',  minutes: 15 },
  { label: '20',  minutes: 20 },
  { label: '30',  minutes: 30 },
  { label: '40',  minutes: 40 },
  { label: '60',  minutes: 60 },
]

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

const emit = defineEmits(['update:checkin'])

function toIndex(enabled, minutes) {
  if (!enabled) return 0
  const idx = steps.findIndex(s => s.minutes === minutes)
  return idx >= 1 ? idx : 2
}

const sliderIndex = ref(toIndex(props.enabled, props.interval))
const isEnabled = computed(() => sliderIndex.value > 0)

watch(() => props.enabled, () => { sliderIndex.value = toIndex(props.enabled, props.interval) })
watch(() => props.interval, () => { sliderIndex.value = toIndex(props.enabled, props.interval) })

function onSliderChange(idx) {
  if (idx === 0) {
    emit('update:checkin', { enabled: false })
  } else {
    emit('update:checkin', { enabled: true, interval: steps[idx].minutes })
  }
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
    justify-content: center;
    gap: 12px;
  }

  .auto-checkin-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-muted);
    white-space: nowrap;

    .auto-checkin-help {
      color: $color-text-muted;
      margin-left: 4px;
      vertical-align: middle;
      cursor: help;
    }
  }

  .auto-checkin-slider {
    flex: 0 1 250px;
    min-width: 100px;

    // Render the thumb-label value inside the thumb dot
    :deep(.v-slider-thumb) {
      .v-slider-thumb__surface {
        width: 25px;
        height: 25px;
        box-shadow: none !important;

        &::before {
          display: none !important;
        }

        &::after {
          display: none !important;
        }
      }

      // Kill ripple/focus glow on the thumb itself
      .v-slider-thumb__ripple {
        display: none !important;
      }

      // Collapse the label container so it doesn't float above
      .v-slider-thumb__label-container {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
      }

      .v-slider-thumb__label {
        position: static;
        background: transparent !important;
        color: $color-background-primary;
        font-size: 0.6rem;
        font-weight: 800;
        width: auto;
        height: auto;
        min-width: 0;
        padding: 0;
        transform: none;
        display: flex;
        align-items: center;
        justify-content: center;

        // Hide the default tooltip arrow/shape
        &::before {
          display: none;
        }
      }
    }
  }

  .auto-checkin-value {
    font-size: 0.72rem;
    font-weight: 600;
    color: $color-text-secondary;
    white-space: nowrap;
  }
}
</style>
