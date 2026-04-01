<template>
  <span
    class="tinted-chip"
    :class="{ 'tinted-chip--sm': size === 'sm', 'tinted-chip--pill': pill }"
    :style="chipStyle"
  >
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { hexToRgba } from '@/utils/colorUtils'

const props = defineProps({
  color: { type: String, required: true },
  label: { type: String, required: true },
  size: { type: String, default: 'default', validator: (v) => ['sm', 'default'].includes(v) },
  pill: { type: Boolean, default: true },
})

const chipStyle = computed(() => ({
  backgroundColor: hexToRgba(props.color, 0.15),
  color: props.color,
}))
</script>

<style scoped>
.tinted-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1.4;
  white-space: nowrap;
  border-radius: 8px;
}

.tinted-chip--pill {
  border-radius: 9999px;
}

.tinted-chip--sm {
  padding: 2px 8px;
  font-size: 0.68rem;
}
</style>
