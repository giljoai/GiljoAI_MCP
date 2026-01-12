<template>
  <v-img :src="src" :width="size" :height="size" :alt="alt" contain class="giljo-face-icon" />
</template>

<script setup>
import { computed } from 'vue'
import { useTheme } from 'vuetify'

const props = defineProps({
  active: { type: Boolean, default: true },
  size: { type: [Number, String], default: 20 },
  alt: { type: String, default: 'GiljoAI' },
})

const theme = useTheme()

const src = computed(() => {
  const isDark = theme.global.current.value.dark
  if (props.active) {
    return isDark ? '/icons/Giljo_YW_Face.svg' : '/icons/Giljo_BY_Face.svg'
  }
  return isDark ? '/icons/Giljo_Inactive_Dark.svg' : '/icons/Giljo_Inactive_Light.svg'
})
</script>

<style scoped>
.giljo-face-icon {
  display: block;
}
</style>
