<template>
  <v-navigation-drawer
    id="navigation"
    :model-value="modelValue"
    @update:model-value="$emit('update:model-value', $event)"
    :rail="rail"
    permanent
    color="surface"
    width="180"
  >
    <!-- Logo/Mascot -->
    <v-list-item class="px-2" style="min-height: 64px">
      <div class="d-flex justify-center align-center w-100">
        <!-- Full logo when expanded, small face when collapsed -->
        <v-img
          v-if="!rail"
          :src="theme.global.current.value.dark ? '/Giljo_YW.svg' : '/Giljo_BY.svg'"
          alt="GiljoAI"
          height="40"
          width="auto"
          max-width="160"
        ></v-img>
        <v-avatar v-else size="40">
          <v-img
            :src="
              theme.global.current.value.dark
                ? '/icons/Giljo_YW_Face.svg'
                : '/icons/Giljo_BY_Face.svg'
            "
            alt="GiljoAI"
          ></v-img>
        </v-avatar>
      </div>
    </v-list-item>

    <v-divider></v-divider>

    <!-- Navigation Items -->
    <v-list density="compact" nav>
      <v-list-item
        v-for="item in navigationItems"
        :key="item.name"
        :to="item.path"
        :title="item.title"
        :value="item.name"
        color="primary"
        role="listitem"
      >
        <template v-slot:prepend>
          <v-img
            v-if="item.customIcon"
            :src="item.customIcon"
            width="28"
            height="28"
            style="margin-left: -2px; margin-right: 30px"
          ></v-img>
          <v-icon v-else>{{ item.icon }}</v-icon>
        </template>
      </v-list-item>
    </v-list>

    <!-- Bottom Section -->
    <template v-slot:append>
      <v-list density="compact" nav>
        <v-list-item
          prepend-icon="mdi-theme-light-dark"
          title="Toggle Theme"
          @click="toggleTheme"
        ></v-list-item>
      </v-list>
    </template>
  </v-navigation-drawer>
</template>

<script setup>
import { computed } from 'vue'
import { useTheme } from 'vuetify'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useSettingsStore } from '@/stores/settings'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: true
  },
  rail: {
    type: Boolean,
    default: false
  },
  currentUser: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:model-value'])

const theme = useTheme()
const route = useRoute()
const userStore = useUserStore()
const settingsStore = useSettingsStore()

// Dynamic Giljo icon for Jobs based on route and theme
const jobsIcon = computed(() => {
  const isJobsRoute = route.path === '/jobs'
  const isDark = theme.global.current.value.dark

  if (isJobsRoute) {
    return isDark ? '/icons/Giljo_YW_Face.svg' : '/icons/Giljo_BY_Face.svg'
  }
  return '/icons/Giljo_gray_Face.svg'
})

// Navigation items - filter based on user role
const navigationItems = computed(() => {
  const baseItems = [
    { name: 'Dashboard', path: '/Dashboard', title: 'Dashboard', icon: 'mdi-view-dashboard' },
    { name: 'Products', path: '/Products', title: 'Products', icon: 'mdi-package-variant' },
    { name: 'Projects', path: '/projects', title: 'Projects', icon: 'mdi-folder-multiple' },
    { name: 'Jobs', path: '/jobs', title: 'Jobs', customIcon: jobsIcon.value },
    { name: 'Tasks', path: '/tasks', title: 'Tasks', icon: 'mdi-clipboard-check' },
  ]

  // Note: Admin-only items like Users are now in the avatar dropdown
  // Note: Jobs navigate to /jobs route (Handover 0077 Hybrid Architecture)
  //       /jobs automatically loads active project → Shows dual-tab interface
  return baseItems
})

const toggleTheme = () => {
  // Add transition class for smooth theme switching
  document.documentElement.classList.remove('no-transition')

  // Toggle the theme
  theme.global.name.value = theme.global.current.value.dark ? 'light' : 'dark'  // TODO: Upgrade to theme.change() after Vuetify 3.7+

  // Update data-theme attribute for CSS variables
  document.documentElement.setAttribute('data-theme', theme.global.name.value)

  // CRITICAL: Synchronize BOTH localStorage stores
  // 1. Update theme-preference (source of truth)
  localStorage.setItem('theme-preference', theme.global.name.value)

  // 2. Update settingsStore to keep giljo_settings synchronized
  settingsStore.settings.theme = theme.global.name.value
  // Manually save to localStorage to update giljo_settings
  localStorage.setItem('giljo_settings', JSON.stringify(settingsStore.settings))
}
</script>

<style scoped>
/* NavigationDrawer styling */
</style>
