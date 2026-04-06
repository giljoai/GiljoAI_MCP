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
import { getAgentColor } from '@/config/agentColors'
import { hexToRgba } from '@/utils/colorUtils'

const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: (value) =>
      ['inactive', 'active', 'completed', 'cancelled', 'terminated', 'deleted'].includes(value),
  },
})

// Project status colors — traced to design-tokens.scss
const COLOR_IMPLEMENTER = getAgentColor('implementer').hex // #6DB3E4 — $color-agent-implementor
const COLOR_MUTED = '#9e9e9e' // $color-text-muted
const COLOR_SUCCESS = '#67bd6d' // $color-status-complete / $color-accent-success
const COLOR_BLOCKED = '#ff9800' // $color-status-blocked
const COLOR_ANALYZER = getAgentColor('analyzer').hex // #E07872 — $color-agent-analyzer

const STATUS_CONFIG = {
  active: { label: 'Active', color: COLOR_IMPLEMENTER },
  inactive: { label: 'Inactive', color: COLOR_MUTED },
  completed: { label: 'Completed', color: COLOR_SUCCESS },
  cancelled: { label: 'Cancelled', color: COLOR_BLOCKED },
  terminated: { label: 'Terminated', color: COLOR_ANALYZER },
  deleted: { label: 'Deleted', color: COLOR_ANALYZER },
}

const config = computed(() => STATUS_CONFIG[props.status] || { label: props.status, color: COLOR_MUTED })
const statusLabel = computed(() => config.value.label)

const badgeStyle = computed(() => {
  const { color, bg, textColor } = config.value
  if (bg) {
    return { background: bg, color: textColor || color }
  }
  return {
    background: hexToRgba(color, 0.15),
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
