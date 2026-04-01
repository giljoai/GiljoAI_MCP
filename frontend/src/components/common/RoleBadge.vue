<template>
  <span class="role-badge" :style="badgeStyle">
    {{ roleLabel }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  role: {
    type: String,
    required: true,
  },
  size: {
    type: String,
    default: 'small',
  },
})

const ROLE_COLORS = {
  owner: '#AC80CC',
  admin: '#6DB3E4',
  member: '#5EC48E',
  viewer: '#8895a8',
}

const SIZE_CONFIG = {
  'x-small': { fontSize: '0.6rem', padding: '2px 6px' },
  small: { fontSize: '0.68rem', padding: '3px 10px' },
  default: { fontSize: '0.78rem', padding: '4px 12px' },
}

function hexToRgb(hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r}, ${g}, ${b}`
}

const roleColor = computed(() => {
  if (!props.role) return ROLE_COLORS.viewer
  return ROLE_COLORS[props.role.toLowerCase()] || ROLE_COLORS.viewer
})

const badgeStyle = computed(() => {
  const color = roleColor.value
  const sizeConf = SIZE_CONFIG[props.size] || SIZE_CONFIG.small
  return {
    background: `rgba(${hexToRgb(color)}, 0.15)`,
    color,
    fontSize: sizeConf.fontSize,
    padding: sizeConf.padding,
  }
})

const roleLabel = computed(() => {
  if (!props.role) return 'Unknown'
  return props.role.charAt(0).toUpperCase() + props.role.slice(1).toLowerCase()
})
</script>

<style scoped>
.role-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 8px;
  font-weight: 600;
  text-transform: capitalize;
  white-space: nowrap;
  line-height: 1.4;
}
</style>
