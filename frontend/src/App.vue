<template>
  <component :is="layout">
    <router-view />
  </component>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AuthLayout from '@/layouts/AuthLayout.vue'
import DefaultLayout from '@/layouts/DefaultLayout.vue'

const route = useRoute()

// Determine layout based on route meta
const layout = computed(() => {
  return route.meta.layout === 'auth' ? AuthLayout : DefaultLayout
})
</script>

<style>
/* Global styles */
html,
body {
  margin: 0;
  padding: 0;
  overflow-x: hidden;
}

html {
  /* Disable transitions during theme initialization */
  transition: background-color 0.3s, color 0.3s;
}

html.no-transition,
html.no-transition * {
  transition: none !important;
}

/* Theme-aware CSS variables */
[data-theme='dark'] {
  color-scheme: dark;
}

[data-theme='light'] {
  color-scheme: light;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
