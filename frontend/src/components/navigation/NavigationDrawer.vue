<template>
  <v-navigation-drawer
    id="navigation"
    :model-value="modelValue"
    @update:model-value="$emit('update:model-value', $event)"
    :rail="rail"
    permanent
    color="surface"
    width="180"
    class="navigation-drawer-container"
  >
    <!-- Edge-Aligned Collapse/Expand Tab -->
    <div
      class="edge-toggle-tab"
      @click="$emit('toggle-rail')"
      :aria-label="rail ? 'Expand sidebar' : 'Collapse sidebar'"
      role="button"
      tabindex="0"
      @keydown.enter="$emit('toggle-rail')"
      @keydown.space.prevent="$emit('toggle-rail')"
    >
      <v-icon size="20">{{ rail ? 'mdi-chevron-right' : 'mdi-chevron-left' }}</v-icon>
    </div>

    <!-- Spacer to align with AppBar height -->
    <div style="height: 8px"></div>

    <!-- Navigation Items -->
    <v-list density="compact" nav v-model:selected="selected" select-strategy="single">
      <v-list-item
        v-for="item in navigationItems"
        :key="item.name"
        :to="item.path"
        :title="item.title"
        :value="item.name"
        :disabled="item.disabled"
        color="primary"
        role="listitem"
        :exact="true"
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
import { computed, ref, watch, onMounted } from 'vue'
import { useTheme } from 'vuetify'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useSettingsStore } from '@/stores/settings'
import { useProjectStore } from '@/stores/projects'  // Product/Project State Fix

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: true,
  },
  rail: {
    type: Boolean,
    default: false,
  },
  currentUser: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:model-value', 'toggle-rail'])

const theme = useTheme()
const route = useRoute()
const userStore = useUserStore()
const settingsStore = useSettingsStore()
const projectStore = useProjectStore()  // Product/Project State Fix

// Track which nav item is selected (ensure single active item)
const selected = ref([])

// Dynamic Giljo icon for Jobs based on route and theme
const jobsIcon = computed(() => {
  const isJobsRoute = route.path.includes('/projects/')
  const isDark = theme.global.current.value.dark

  if (isJobsRoute) {
    // Active state: Yellow/White for dark theme, Blue/Yellow for light theme
    return isDark ? '/icons/Giljo_YW_Face.svg' : '/icons/Giljo_BY_Face.svg'
  }
  // Inactive state: Light gray for dark theme, Dark gray for light theme
  return isDark ? '/icons/Giljo_Inactive_Dark.svg' : '/icons/Giljo_Inactive_Light.svg'
})

// Navigation items
const navigationItems = computed(() => {
  // Product/Project State Fix: Dynamic Jobs link based on active project
  const activeProj = projectStore.activeProject
  const jobsPath = activeProj
    ? `/projects/${activeProj.id}?via=jobs`  // Link to active project
    : '/launch?via=jobs'  // Fallback to LaunchRedirectView (shows "No Active Project")

  const baseItems = [
    { name: 'Home', path: '/home', title: 'Home', icon: 'mdi-home' },
    { name: 'Dashboard', path: '/Dashboard', title: 'Dashboard', icon: 'mdi-view-dashboard' },
    { name: 'Products', path: '/Products', title: 'Products', icon: 'mdi-package-variant' },
    { name: 'Projects', path: '/projects', title: 'Projects', icon: 'mdi-folder-multiple' },
    // Dynamic path: Links to active project or projects list
    { name: 'Jobs', path: jobsPath, title: 'Jobs', customIcon: jobsIcon.value },
    { name: 'Tasks', path: '/tasks', title: 'Tasks', icon: 'mdi-clipboard-check' },
  ]

  return baseItems
})

// Derive the active sidebar item from current route; prefer the longest matching path
const updateSelectedFromRoute = () => {
  const items = navigationItems.value
  const currentPath = route.path

  // If navigation explicitly came via Jobs, force Jobs active
  if (route?.query?.via === 'jobs') {
    selected.value = ['Jobs']
    return
  }

  // Treat dynamic project routes as Jobs workspace (clean separation)
  // Example: /projects/:projectId -> highlight Jobs
  if (currentPath.startsWith('/projects/')) {
    selected.value = ['Jobs']
    return
  }

  // Find best match by longest path prefix match or exact match
  let best = null
  for (const item of items) {
    if (!item.path) continue
    if (currentPath === item.path || currentPath.startsWith(item.path + '/')) {
      if (!best || item.path.length > best.path.length) {
        best = item
      }
    }
  }

  // Fallback: highlight nothing if no match
  selected.value = best ? [best.name] : []
}

onMounted(updateSelectedFromRoute)
watch(
  () => route.path,
  () => updateSelectedFromRoute(),
)

const toggleTheme = () => {
  document.documentElement.classList.remove('no-transition')
  const newTheme = theme.global.current.value.dark ? 'light' : 'dark'
  theme.change(newTheme)
  document.documentElement.setAttribute('data-theme', newTheme)
  localStorage.setItem('theme-preference', newTheme)
  settingsStore.settings.theme = newTheme
  localStorage.setItem('giljo_settings', JSON.stringify(settingsStore.settings))
}
</script>

<style scoped>
/* NavigationDrawer styling */

.navigation-drawer-container {
  overflow: visible !important;
}

.edge-toggle-tab {
  position: absolute;
  right: -16px;
  top: 10%;
  transform: translateY(0);
  width: 32px;
  height: 32px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-border-color), 0.2);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 100;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.edge-toggle-tab:hover {
  background: rgba(var(--v-theme-primary), 0.1);
  border-color: rgb(var(--v-theme-primary));
}

.edge-toggle-tab:focus {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.edge-toggle-tab:active {
  transform: scale(0.95);
}
</style>
