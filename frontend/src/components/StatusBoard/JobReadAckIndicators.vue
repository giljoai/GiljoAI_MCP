<template>
  <div class="job-ack-indicator d-flex align-center">
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
 * JobReadAckIndicators Component (Simplified)
 *
 * Displays visual indicator for job mission acknowledged status.
 * Shows green check icon when acknowledged, grey dash icon when pending.
 * Includes tooltip with formatted timestamp.
 *
 * Props:
 * - missionAcknowledgedAt: ISO 8601 timestamp string or null
 *
 * Note: Job Read functionality removed - only Job Acknowledged remains
 */

const props = defineProps({
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
.job-ack-indicator .v-icon {
  transition: color 0.2s ease;
}

.job-ack-indicator .v-icon:hover {
  opacity: 0.8;
}
</style>
