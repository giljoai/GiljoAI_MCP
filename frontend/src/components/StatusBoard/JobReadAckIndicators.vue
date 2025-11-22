<template>
  <div class="job-read-ack-indicators d-flex align-center gap-2">
    <!-- Job Read indicator -->
    <v-icon
      class="read-indicator"
      :color="missionReadAt ? 'success' : 'grey'"
      size="small"
      :title="readTooltip"
    >
      {{ missionReadAt ? 'mdi-check-circle' : 'mdi-minus-circle-outline' }}
    </v-icon>

    <!-- Job Acknowledged indicator -->
    <v-icon
      class="ack-indicator"
      :color="missionAcknowledgedAt ? 'success' : 'grey'"
      size="small"
      :title="ackTooltip"
    >
      {{ missionAcknowledgedAt ? 'mdi-check-circle' : 'mdi-minus-circle-outline' }}
    </v-icon>
  </div>
</template>

<script setup>
import { computed } from 'vue'

/**
 * JobReadAckIndicators Component
 *
 * Displays visual indicators for job mission read and acknowledged status.
 * Shows green check icons when status is met, grey dash icons when pending.
 * Includes tooltips with formatted timestamps.
 *
 * Props:
 * - missionReadAt: ISO 8601 timestamp string or null
 * - missionAcknowledgedAt: ISO 8601 timestamp string or null
 *
 * Handover 0233: Frontend job read/acknowledged indicators
 */

const props = defineProps({
  missionReadAt: {
    type: String,
    default: null,
  },
  missionAcknowledgedAt: {
    type: String,
    default: null,
  },
})

/**
 * Format a timestamp for display in tooltip
 * Handles null values and invalid dates gracefully
 */
function formatTimestamp(timestamp) {
  if (!timestamp) {
    return null
  }

  try {
    const date = new Date(timestamp)
    // Check if date is valid
    if (isNaN(date.getTime())) {
      return null
    }
    // Use toLocaleString for user-friendly format
    return date.toLocaleString()
  } catch (error) {
    console.warn('[JobReadAckIndicators] Invalid timestamp:', timestamp, error)
    return null
  }
}

/**
 * Compute tooltip text for mission read status
 */
const readTooltip = computed(() => {
  if (!props.missionReadAt) {
    return 'Not yet read'
  }

  const formattedTime = formatTimestamp(props.missionReadAt)
  return formattedTime ? `Read at ${formattedTime}` : 'Not yet read'
})

/**
 * Compute tooltip text for mission acknowledged status
 */
const ackTooltip = computed(() => {
  if (!props.missionAcknowledgedAt) {
    return 'Not yet acknowledged'
  }

  const formattedTime = formatTimestamp(props.missionAcknowledgedAt)
  return formattedTime ? `Acknowledged at ${formattedTime}` : 'Not yet acknowledged'
})
</script>

<style scoped>
.job-read-ack-indicators {
  gap: 0.5rem;
}

.job-read-ack-indicators .v-icon {
  transition: color 0.2s ease;
}

.job-read-ack-indicators .v-icon:hover {
  opacity: 0.8;
}
</style>
