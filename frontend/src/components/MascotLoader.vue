<template>
  <div class="mascot-loader-container" :style="containerStyle">
    <iframe
      v-if="type === 'iframe'"
      :src="mascotSrc"
      :width="size"
      :height="size"
      frameborder="0"
      scrolling="no"
      :title="title"
      :aria-label="ariaLabel"
      class="mascot-iframe"
    />
    <div
      v-else
      class="mascot-loading"
      :aria-label="ariaLabel"
      role="status"
    >
      <img
        :src="mascotSrc"
        :alt="title"
        :width="size"
        :height="size"
        class="mascot-image"
      />
      <span class="sr-only">{{ ariaLabel }}</span>
    </div>
    <p v-if="showText" class="mascot-text mt-2">{{ text }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useTheme } from 'vuetify'

const props = defineProps({
  type: {
    type: String,
    default: 'iframe',
    validator: (value) => ['iframe', 'image'].includes(value)
  },
  variant: {
    type: String,
    default: 'loader',
    validator: (value) => ['loader', 'active', 'thinker', 'working'].includes(value)
  },
  size: {
    type: [Number, String],
    default: 100
  },
  text: {
    type: String,
    default: 'Loading...'
  },
  showText: {
    type: Boolean,
    default: true
  },
  centered: {
    type: Boolean,
    default: true
  },
  useBlue: {
    type: Boolean,
    default: false
  }
})

const theme = useTheme()

const mascotSrc = computed(() => {
  if (props.type === 'image') {
    // Use static SVG for image type
    const isBlue = props.useBlue || theme.global.current.value.dark === false
    return isBlue ? '/mascot/Giljo_BY_Face.svg' : '/mascot/giljo_YW_Face.svg'
  }
  
  // Use HTML animations for iframe type
  const isBlue = props.useBlue || theme.global.current.value.dark === false
  const colorVariant = isBlue ? '_blue' : ''
  return `/mascot/giljo_mascot_${props.variant}${colorVariant}.html`
})

const title = computed(() => {
  const titles = {
    loader: 'Loading',
    active: 'Active',
    thinker: 'Thinking',
    working: 'Working'
  }
  return titles[props.variant] || 'Loading'
})

const ariaLabel = computed(() => {
  const labels = {
    loader: 'Loading, please wait',
    active: 'System is active',
    thinker: 'Processing your request',
    working: 'Working on task'
  }
  return labels[props.variant] || 'Loading'
})

const containerStyle = computed(() => {
  return {
    display: props.centered ? 'flex' : 'inline-flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    width: props.centered ? '100%' : 'auto'
  }
})
</script>

<style scoped>
.mascot-loader-container {
  position: relative;
}

.mascot-iframe {
  border: none;
  background: transparent;
  display: block;
}

.mascot-image {
  display: block;
  animation: pulse 2s ease-in-out infinite;
}

.mascot-loading {
  display: inline-block;
  position: relative;
}

.mascot-text {
  text-align: center;
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.875rem;
  opacity: 0.8;
  animation: fadeInOut 2s ease-in-out infinite;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(0.95);
    opacity: 0.9;
  }
}

@keyframes fadeInOut {
  0%, 100% {
    opacity: 0.6;
  }
  50% {
    opacity: 1;
  }
}

/* Theme transition for smooth switching */
.mascot-iframe,
.mascot-image {
  transition: opacity 0.3s ease;
}
</style>