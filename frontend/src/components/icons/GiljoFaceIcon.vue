<template>
  <v-img :src="src" :width="size" :height="size" :alt="alt" contain class="giljo-face-icon" />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  active: { type: Boolean, default: true },
  size: { type: [Number, String], default: 20 },
  alt: { type: String, default: 'GiljoAI' },
})

const src = computed(() => {
  if (props.active) {
    return '/icons/Giljo_YW_Face.svg'
  }
  return '/icons/Giljo_Inactive_Dark.svg'
})
</script>

<style scoped>
.giljo-face-icon {
  display: block;
}
</style>
