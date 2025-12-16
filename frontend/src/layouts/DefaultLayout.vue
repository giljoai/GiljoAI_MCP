<template>
  <v-app>
    <AppBar
      v-if="!route.meta.hideAppBar"
      :current-user="currentUser"
      :rail="rail"
      @toggle-drawer="drawer = !drawer"
      @toggle-rail="rail = !rail"
    />

    <NavigationDrawer
      v-if="!route.meta.hideDrawer"
      v-model="drawer"
      :rail="rail"
      :current-user="currentUser"
    />

    <v-main>
      <router-view :current-user="currentUser" />
    </v-main>

    <!-- Global Toast Notifications -->
    <ToastManager position="top center" />
  </v-app>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useWebSocketStore } from '@/stores/websocket'
import { useMessageStore } from '@/stores/messages'
import { setupWebSocketIntegrations } from '@/stores/websocketIntegrations'
import AppBar from '@/components/navigation/AppBar.vue'
import NavigationDrawer from '@/components/navigation/NavigationDrawer.vue'
import ToastManager from '@/components/ToastManager.vue'
import api from '@/services/api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const wsStore = useWebSocketStore()
const messageStore = useMessageStore()

const drawer = ref(true)
const rail = ref(false)
const currentUser = ref(null)
let messagePollingInterval = null

const loadCurrentUser = async () => {
  try {
    const response = await api.auth.me()
    console.log('[DefaultLayout] API /auth/me response:', response)
    currentUser.value = response.data
    userStore.currentUser = response.data
    console.log('[DefaultLayout] Current user loaded:', currentUser.value?.username)
    return true
  } catch (error) {
    console.error('[DefaultLayout] Failed to load user:', error)
    currentUser.value = null
    userStore.currentUser = null

    // If auth fails in app context, redirect to login
    router.push('/login')
    return false
  }
}

onMounted(async () => {
  console.log('[DefaultLayout] Loading user data on mount')

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
        console.log('[DefaultLayout] Fresh install detected, redirecting to /welcome')
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
      console.log('[DefaultLayout] WebSocket connected with automatic cookie authentication')

      // Setup WebSocket V2 integrations (store-to-store message routing)
      setupWebSocketIntegrations()
      console.log('[DefaultLayout] WebSocket integrations setup complete')

      // Load initial data (remove legacy /api/v1/agents call)
      await Promise.all([messageStore.fetchMessages()])

      // Set up 10-second message polling interval
      messagePollingInterval = setInterval(async () => {
        try {
          await messageStore.fetchMessages()
          console.log('[DefaultLayout] Messages refreshed at', new Date().toLocaleTimeString())
        } catch (error) {
          console.error('[DefaultLayout] Failed to fetch messages:', error)
        }
      }, 10000) // Poll every 10 seconds

      console.log('[DefaultLayout] Application initialized successfully')
    } catch (error) {
      console.error('[DefaultLayout] Failed to initialize WebSocket:', error)
    }
  }
})

onUnmounted(() => {
  // Clear message polling interval
  if (messagePollingInterval) {
    clearInterval(messagePollingInterval)
  }

  // Disconnect WebSocket
  wsStore.disconnect()
  console.log('[DefaultLayout] Cleanup complete')
})

// Reload user after login (navigation from /login)
router.afterEach(async (to, from) => {
  if (to.meta.layout === 'default' && from.path === '/login') {
    console.log('[DefaultLayout] Navigated from login, reloading user')
    await loadCurrentUser()
  }
})
</script>

<style scoped>
/* Application layout styling */
</style>
