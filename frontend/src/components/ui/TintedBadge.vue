<template>
  <div
    class="tinted-badge"
    :style="badgeStyle"
  >
    {{ label }}
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { hexToRgba } from '@/utils/colorUtils'

const props = defineProps({
  color: { type: String, required: true },
  label: { type: String, required: true },
  size: { type: Number, default: 36 },
})

const badgeStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  fontSize: `${Math.max(props.size * 0.33, 10)}px`,
  backgroundColor: hexToRgba(props.color, 0.15),
  color: props.color,
}))
</script>

<style scoped>
.tinted-badge {
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
}
</style>
