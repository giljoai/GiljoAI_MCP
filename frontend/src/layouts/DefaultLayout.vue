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
  </v-app>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useWebSocketStore } from '@/stores/websocket'
import { useAgentStore } from '@/stores/agents'
import { useMessageStore } from '@/stores/messages'
import AppBar from '@/components/navigation/AppBar.vue'
import NavigationDrawer from '@/components/navigation/NavigationDrawer.vue'
import api from '@/services/api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const wsStore = useWebSocketStore()
const agentStore = useAgentStore()
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
  const userLoaded = await loadCurrentUser()

  // Initialize WebSocket and data polling only if user is authenticated
  if (userLoaded && currentUser.value) {
    try {
      // Connect WebSocket with cookie-based authentication
      await wsStore.connect()
      console.log('[DefaultLayout] WebSocket connected successfully')

      // Load initial data
      await Promise.all([agentStore.fetchAgents(), messageStore.fetchMessages()])

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
