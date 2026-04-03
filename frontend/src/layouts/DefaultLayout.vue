<template>
  <v-app>
    <StarField />

    <NavigationDrawer
      v-if="!route.meta.hideDrawer"
      v-model="drawer"
      :rail="isMobile ? false : rail"
      :temporary="isMobile"
      :current-user="currentUser"
      @toggle-rail="rail = !rail"
    />

    <v-main>
      <router-view :current-user="currentUser" />
    </v-main>

    <!-- Global Toast Notifications -->
    <ToastManager />

    <!-- Community Edition Licensing Reminder -->
    <LicensingDialog />
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useProductStore } from '@/stores/products'
import { useWebSocketStore } from '@/stores/websocket'
import { useMessageStore } from '@/stores/messages'
import { initWebsocketEventRouter } from '@/stores/websocketEventRouter'
import StarField from '@/components/StarField.vue'
import NavigationDrawer from '@/components/navigation/NavigationDrawer.vue'
import ToastManager from '@/components/ToastManager.vue'
import LicensingDialog from '@/components/LicensingDialog.vue'
import setupService from '@/services/setupService'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const productStore = useProductStore()
const wsStore = useWebSocketStore()
const messageStore = useMessageStore()

const drawer = ref(true)
const rail = ref(false)
const windowWidth = ref(window.innerWidth)
const SIDEBAR_BREAKPOINT = 1024
const isMobile = computed(() => windowWidth.value <= SIDEBAR_BREAKPOINT)

function onResize() {
  windowWidth.value = window.innerWidth
  if (isMobile.value) {
    drawer.value = false
  }
}

window.addEventListener('resize', onResize)
const currentUser = ref(null)

const loadCurrentUser = async () => {
  try {
    const success = await userStore.fetchCurrentUser()
    if (success) {
      currentUser.value = userStore.currentUser
      return true
    }
    // fetchCurrentUser returned false (API failed internally)
    currentUser.value = null
    router.push('/login')
    return false
  } catch (error) {
    console.error('[DefaultLayout] Failed to load user:', error)
    currentUser.value = null
    router.push('/login')
    return false
  }
}

onMounted(async () => {
  // CRITICAL FIX (Handover 0034): Check fresh install status FIRST
  // This prevents race condition where DefaultLayout redirects to /login
  // before router guard can redirect to /welcome
  try {
    const setupData = await setupService.checkEnhancedStatus()
    if (setupData.is_fresh_install) {
      router.push('/welcome')
      return
    }
  } catch (setupError) {
    console.warn('[DefaultLayout] Failed to check fresh install status:', setupError)
  }

  // Normal operation: load current user
  const userLoaded = await loadCurrentUser()

  // Restore active product state from localStorage + backend
  if (userLoaded && currentUser.value) {
    await productStore.initializeFromStorage()
  }

  // Initialize WebSocket and data polling only if user is authenticated
  if (userLoaded && currentUser.value) {
    try {
      // Connect WebSocket - browser will automatically send httpOnly access_token cookie
      await wsStore.connect()

      // Initialize the centralized router once (0379a)
      initWebsocketEventRouter({
        onReconnectResync: async () => {
          await messageStore.fetchMessages()
        },
      })

      // Load initial data (remove legacy /api/v1/agents call)
      await Promise.all([messageStore.fetchMessages()])
    } catch (error) {
      console.error('[DefaultLayout] Failed to initialize WebSocket:', error)
    }
  }
})

onUnmounted(() => {
  wsStore.disconnect()
  window.removeEventListener('resize', onResize)
})

// Reload user after login (navigation from /login)
router.afterEach(async (to, from) => {
  if (to.meta.layout === 'default' && from.path === '/login') {
    await loadCurrentUser()
  }
})
</script>

<style scoped>
/* Mobile: add top padding to clear the hamburger FAB */
@media (max-width: 1024px) {
  :deep(.v-main) {
    padding-top: 48px !important;
  }
}
</style>
