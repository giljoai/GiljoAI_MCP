<template>
  <v-tooltip location="top">
    <template v-slot:activator="{ props: tooltipProps }">
      <v-chip
        v-bind="tooltipProps"
        :color="statusConfig.color"
        :prepend-icon="statusConfig.icon"
        size="small"
        class="status-chip"
        :class="{ 'status-chip--stale': isStale, 'smooth-border': isStale }"
      >
        <!-- Health indicator overlay -->
        <span
          v-if="healthConfig.showIndicator"
          class="health-indicator smooth-border"
          :class="{ 'pulse-animation': healthConfig.pulse }"
          :style="{ backgroundColor: healthConfig.dotColor }"
        ></span>

        <!-- Status label -->
        {{ statusConfig.label }}

        <!-- Staleness indicator -->
        <v-icon v-if="isStale" size="x-small" class="ml-1" color="warning">
          mdi-clock-alert
        </v-icon>
      </v-chip>
    </template>

    <!-- Tooltip content -->
    <div class="status-tooltip">
      <div class="font-weight-bold mb-1">{{ statusConfig.label }}</div>
      <div class="text-caption">{{ statusConfig.description }}</div>

      <v-divider class="my-2" />

      <div class="text-caption">
        <div>Last activity: {{ formattedLastActivity }}</div>

        <div v-if="isStale" class="warning--text mt-1">
          <v-icon size="x-small" class="mr-1">mdi-alert</v-icon>
          Warning: No activity for {{ minutesSinceProgress }} minutes
        </div>

        <div v-if="healthConfig.showIndicator" class="mt-1">
          <v-icon size="x-small" :color="healthConfig.color" class="mr-1">
            {{ healthConfig.icon }}
          </v-icon>
          Health: {{ healthConfig.label }}
        </div>
      </div>
    </div>
  </v-tooltip>
</template>

<script setup>
import { computed } from 'vue'
import {
  getStatusConfig,
  getHealthConfig,
  isJobStale,
  formatLastActivity,
} from '@/utils/statusConfig'

const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: (value) =>
      [
        'waiting',
        'working',
        'blocked',
        'complete',
        'silent',
        'decommissioned',
        'handed_over',
      ].includes(value),
  },
  healthStatus: {
    type: String,
    default: 'healthy',
    validator: (value) => ['healthy', 'warning', 'critical', 'timeout', 'unknown'].includes(value),
  },
  lastProgressAt: {
    type: String,
    default: null,
  },
  minutesSinceProgress: {
    type: Number,
    default: null,
  },
})

const statusConfig = computed(() => getStatusConfig(props.status))
const healthConfig = computed(() => getHealthConfig(props.healthStatus))

const isStale = computed(() => {
  return isJobStale(props.lastProgressAt, props.status)
})

const formattedLastActivity = computed(() => {
  return formatLastActivity(props.lastProgressAt)
})
</script>

<style scoped>
.status-chip {
  position: relative;
  font-weight: 500;
}

.status-chip--stale {
  border: none !important;
  --smooth-border-color: rgba(255, 152, 0, 0.5);
}

.health-indicator {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: none !important;
  --smooth-border-color: rgba(255, 255, 255, 0.8);
}

.pulse-animation {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.2);
  }
}

.status-tooltip {
  max-width: 300px;
}
</style>
