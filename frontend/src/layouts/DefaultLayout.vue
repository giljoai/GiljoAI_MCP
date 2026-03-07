<template>
  <v-app>
    <AppBar
      v-if="!route.meta.hideAppBar"
      :current-user="currentUser"
      @toggle-drawer="drawer = !drawer"
    />

    <NavigationDrawer
      v-if="!route.meta.hideDrawer"
      v-model="drawer"
      :rail="rail"
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
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useWebSocketStore } from '@/stores/websocket'
import { useMessageStore } from '@/stores/messages'
import { initWebsocketEventRouter } from '@/stores/websocketEventRouter'
import AppBar from '@/components/navigation/AppBar.vue'
import NavigationDrawer from '@/components/navigation/NavigationDrawer.vue'
import ToastManager from '@/components/ToastManager.vue'
import LicensingDialog from '@/components/LicensingDialog.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const wsStore = useWebSocketStore()
const messageStore = useMessageStore()

const drawer = ref(true)
const rail = ref(false)
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
    const apiBaseUrl =
      window.API_BASE_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:7272'
    const setupResponse = await fetch(`${apiBaseUrl}/api/setup/status`, {
      method: 'GET',
      cache: 'no-cache',
    })

    if (setupResponse.ok) {
      const setupData = await setupResponse.json()

      if (setupData.is_fresh_install) {
        // Fresh install (0 users) - redirect to create admin account
        router.push('/welcome')
        return
      }
    }
  } catch (setupError) {
    console.warn('[DefaultLayout] Failed to check fresh install status:', setupError)
    // Continue with auth check (secure fallback)
  }

  // Normal operation: load current user
  const userLoaded = await loadCurrentUser()

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
  // Disconnect WebSocket
  wsStore.disconnect()
})

// Reload user after login (navigation from /login)
router.afterEach(async (to, from) => {
  if (to.meta.layout === 'default' && from.path === '/login') {
    await loadCurrentUser()
  }
})
</script>

<style scoped>
/* Application layout styling */
</style>
