<template>
  <div class="mascot-loader" :style="containerStyle">
    <iframe
      :src="mascotSrc"
      :style="iframeStyle"
      frameborder="0"
      scrolling="no"
      @load="onLoad"
    ></iframe>
    <p v-if="showText && text" class="mascot-text">{{ text }}</p>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'loader',
    validator: (value) => ['loader', 'working', 'thinker', 'active'].includes(value)
  },
  size: {
    type: Number,
    default: 60
  },
  text: {
    type: String,
    default: ''
  },
  showText: {
    type: Boolean,
    default: true
  },
  type: {
    type: String,
    default: 'spinner'
  }
})

const loaded = ref(false)

const mascotSrc = computed(() => {
  const variantMap = {
    'loader': '/mascot/giljo_mascot_loader.html',
    'working': '/mascot/giljo_mascot_working.html',
    'thinker': '/mascot/giljo_mascot_thinker.html',
    'active': '/mascot/giljo_mascot_active.html'
  }
  return variantMap[props.variant] || variantMap.loader
})

const containerStyle = computed(() => ({
  width: `${props.size}px`,
  minHeight: props.showText && props.text ? `${props.size + 30}px` : `${props.size}px`
}))

const iframeStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  opacity: loaded.value ? 1 : 0,
  transition: 'opacity 0.3s'
}))

const onLoad = () => {
  loaded.value = true
}
</script>

<style scoped>
.mascot-loader {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: transparent;
}

iframe {
  border: none;
  background: transparent;
  pointer-events: none;
  overflow: hidden;
}

.mascot-text {
  margin: 0;
  color: var(--text-secondary, #666);
  font-size: 0.875rem;
  text-align: center;
}
</style>
