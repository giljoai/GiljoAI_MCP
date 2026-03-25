<template>
  <v-chip
    :color="statusColor"
    :text-color="statusTextColor"
    variant="flat"
    size="small"
    class="status-badge-chip"
    :aria-label="`Project status: ${statusLabel}`"
  >
    <span class="text-caption font-weight-bold" :style="statusTextColor ? { color: statusTextColor } : {}">{{ statusLabel }}</span>
  </v-chip>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: (value) =>
      ['inactive', 'active', 'completed', 'cancelled', 'terminated', 'deleted'].includes(value),
  },
})

// Status Configuration
const statusConfig = {
  active: {
    label: 'Active',
    color: 'success',
    icon: 'mdi-play-circle',
  },
  inactive: {
    label: 'Inactive',
    color: 'grey',
    textColor: '#1a237e',
    icon: 'mdi-stop-circle-outline',
  },
  completed: {
    label: 'Completed',
    color: 'info',
    icon: 'mdi-check-circle',
  },
  cancelled: {
    label: 'Cancelled',
    color: 'warning',
    icon: 'mdi-cancel',
  },
  terminated: {
    label: 'Terminated',
    color: 'error',
    icon: 'mdi-stop-circle',
  },
  deleted: {
    label: 'Deleted',
    color: 'error',
    icon: 'mdi-delete',
  },
}

// Computed
const statusLabel = computed(() => statusConfig[props.status]?.label || props.status)
const statusColor = computed(() => statusConfig[props.status]?.color || 'grey')
const statusTextColor = computed(() => statusConfig[props.status]?.textColor || undefined)
const statusIcon = computed(() => statusConfig[props.status]?.icon || 'mdi-circle')
</script>

<style scoped>
.status-badge-chip {
  user-select: none;
}
</style>
