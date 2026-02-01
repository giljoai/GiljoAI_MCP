<template>
  <v-chip :color="roleColor" :size="size" variant="flat" class="text-capitalize">
    {{ roleLabel }}
  </v-chip>
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

const roleColor = computed(() => {
  if (!props.role) return 'grey'

  const roleLower = props.role.toLowerCase()

  switch (roleLower) {
    case 'owner':
      return 'purple'
    case 'admin':
      return 'blue'
    case 'member':
      return 'green'
    case 'viewer':
      return 'grey'
    default:
      return 'grey'
  }
})

const roleLabel = computed(() => {
  if (!props.role) return 'Unknown'

  return props.role.charAt(0).toUpperCase() + props.role.slice(1).toLowerCase()
})
</script>

<style scoped>
/* Component styling */
</style>
