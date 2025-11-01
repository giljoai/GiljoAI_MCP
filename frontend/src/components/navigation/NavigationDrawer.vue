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
        :disabled="item.disabled"
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
import { computed, onMounted, ref, watch } from 'vue'
import { useTheme } from 'vuetify'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useSettingsStore } from '@/stores/settings'
import { useProductStore } from '@/stores/products'
import { useProjectStore } from '@/stores/projects'
import { api } from '@/services/api'

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
const productStore = useProductStore()
const projectStore = useProjectStore()

// Active project tracking for Jobs button
const activeProjectId = ref(null)

// Fetch active project
async function fetchActiveProject() {
  try {
    const response = await api.projects.getActive()
    if (response.data) {
      activeProjectId.value = response.data.id
      console.log('[NavigationDrawer] Active project loaded:', response.data.name)
    } else {
      activeProjectId.value = null
      console.log('[NavigationDrawer] No active project')
    }
  } catch (err) {
    activeProjectId.value = null
    console.warn('[NavigationDrawer] No active project:', err.message)
  }
}

// Fetch active project on mount
onMounted(async () => {
  await fetchActiveProject()
})

// Watch for product changes - clear active project when product switches
watch(
  () => productStore.activeProduct,
  async (newProduct, oldProduct) => {
    // Product changed (including activation/deactivation)
    if (newProduct?.id !== oldProduct?.id) {
      console.log('[NavigationDrawer] Product changed, refreshing active project')
      await fetchActiveProject()
    }
  },
  { deep: true }
)

// Watch for project changes within the same product
watch(
  () => projectStore.projects.find(p => p.status === 'active')?.id,
  async (newActiveProjectId, oldActiveProjectId) => {
    if (newActiveProjectId !== oldActiveProjectId) {
      console.log('[NavigationDrawer] Active project changed, updating Jobs button')
      await fetchActiveProject()
    }
  }
)

// Dynamic Giljo icon for Jobs based on route and theme
const jobsIcon = computed(() => {
  const isJobsRoute = route.path.includes('/projects/')
  const isDark = theme.global.current.value.dark
  
  if (isJobsRoute) {
    return isDark ? '/icons/Giljo_YW_Face.svg' : '/icons/Giljo_BY_Face.svg'
  }
  return '/icons/Giljo_gray_Face.svg'
})

// Jobs button path - routes to active project
const jobsPath = computed(() => {
  return activeProjectId.value ? `/projects/${activeProjectId.value}` : null
})

const jobsTitle = computed(() => {
  return activeProjectId.value ? 'Jobs' : 'No active project'
})

// Navigation items
const navigationItems = computed(() => {
  const baseItems = [
    { name: 'Dashboard', path: '/Dashboard', title: 'Dashboard', icon: 'mdi-view-dashboard' },
    { name: 'Products', path: '/Products', title: 'Products', icon: 'mdi-package-variant' },
    { name: 'Projects', path: '/projects', title: 'Projects', icon: 'mdi-folder-multiple' },
    { name: 'Jobs', path: jobsPath.value, title: jobsTitle.value, customIcon: jobsIcon.value, disabled: !activeProjectId.value },
    { name: 'Tasks', path: '/tasks', title: 'Tasks', icon: 'mdi-clipboard-check' },
  ]

  return baseItems
})

const toggleTheme = () => {
  document.documentElement.classList.remove('no-transition')
  theme.global.name.value = theme.global.current.value.dark ? 'light' : 'dark'
  document.documentElement.setAttribute('data-theme', theme.global.name.value)
  localStorage.setItem('theme-preference', theme.global.name.value)
  settingsStore.settings.theme = theme.global.name.value
  localStorage.setItem('giljo_settings', JSON.stringify(settingsStore.settings))
}
</script>

<style scoped>
/* NavigationDrawer styling */
</style>
