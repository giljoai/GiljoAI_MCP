<template>
  <span
    class="status-badge"
    :style="badgeStyle"
    :aria-label="`Project status: ${statusLabel}`"
  >
    {{ statusLabel }}
  </span>
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

// Status colors unchanged — tinted style (rgba bg + bright text)
const STATUS_CONFIG = {
  active: { label: 'Active', color: '#6DB3E4' },
  inactive: { label: 'Inactive', color: '#9e9e9e' },
  completed: { label: 'Completed', color: '#67bd6d' },
  cancelled: { label: 'Cancelled', color: '#ff9800' },
  terminated: { label: 'Terminated', color: '#e07872' },
  deleted: { label: 'Deleted', color: '#e07872' },
}

function hexToRgb(hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r}, ${g}, ${b}`
}

const config = computed(() => STATUS_CONFIG[props.status] || { label: props.status, color: '#9e9e9e' })
const statusLabel = computed(() => config.value.label)

const badgeStyle = computed(() => {
  const { color, bg, textColor } = config.value
  if (bg) {
    return { background: bg, color: textColor || color }
  }
  return {
    background: `rgba(${hexToRgb(color)}, 0.15)`,
    color,
  }
})
</script>

<style lang="scss" scoped>
@use '../styles/design-tokens' as *;
.status-badge {
  display: inline-flex;
  align-items: center;
  border-radius: $border-radius-default;
  font-size: 0.68rem;
  font-weight: 600;
  padding: 3px 10px;
  white-space: nowrap;
  line-height: 1.4;
  user-select: none;
}
</style>
