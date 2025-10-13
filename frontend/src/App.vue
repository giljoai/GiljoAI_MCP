<template>
  <v-app>
    <!-- Skip Navigation Links (Screen Reader Accessible) -->
    <a href="#main-content" class="skip-link">Skip to main content</a>
    <a href="#navigation" class="skip-link">Skip to navigation</a>
    <!-- Navigation Drawer -->
    <v-navigation-drawer
      id="navigation"
      v-model="drawer"
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

    <!-- App Bar -->
    <v-app-bar color="surface" elevation="0" border>
      <div style="display: flex; align-items: center; width: 100%; justify-content: space-between">
        <!-- Left: Sidebar Toggle -->
        <div style="flex: 0 0 auto">
          <v-btn
            v-if="!mobile"
            variant="text"
            :icon="rail ? 'mdi-chevron-right' : 'mdi-chevron-left'"
            @click="rail = !rail"
            :aria-label="rail ? 'Expand navigation' : 'Collapse navigation'"
            class="mr-2"
          ></v-btn>

          <v-app-bar-nav-icon
            @click="drawer = !drawer"
            v-if="mobile"
            aria-label="Toggle navigation drawer"
          ></v-app-bar-nav-icon>
        </div>

        <!-- Center: Title -->
        <div style="flex: 1 1 auto; display: flex; justify-content: center; min-width: 0">
          <v-toolbar-title
            class="text-no-wrap"
            :style="{
              color: theme.global.current.value.dark ? '#ffc300' : '#1e3147',
              fontWeight: 500,
              fontSize: 'clamp(0.875rem, 2vw, 1.25rem)',
            }"
          >
            Agent Orchestration MCP Server
          </v-toolbar-title>
        </div>

        <!-- Right: Product Switcher, Connection Status, User Menu -->
        <div style="flex: 0 0 auto; display: flex; align-items: center">
          <ProductSwitcher class="mr-3" />
          <ConnectionStatus class="mr-2" />
          <v-btn
            icon="mdi-bell"
            variant="text"
            aria-label="View notifications"
            class="mr-2"
          ></v-btn>

          <!-- User Menu -->
          <v-menu offset-y>
            <template v-slot:activator="{ props }">
              <v-btn icon v-bind="props" aria-label="User menu">
                <v-icon>mdi-account-circle</v-icon>
              </v-btn>
            </template>

            <v-list density="compact" min-width="200">
              <v-list-item v-if="currentUser" prepend-icon="mdi-account">
                <v-list-item-title class="font-weight-medium">
                  {{ currentUser.username }}
                </v-list-item-title>
                <v-list-item-subtitle v-if="currentUser.role" class="d-flex align-center mt-1">
                  <v-chip
                    :color="getRoleColor(currentUser.role)"
                    size="small"
                    variant="flat"
                    class="text-caption"
                  >
                    {{ currentUser.role }}
                  </v-chip>
                </v-list-item-subtitle>
              </v-list-item>

              <v-divider v-if="currentUser" />

              <v-list-item :to="{ name: 'UserSettings' }">
                <template v-slot:prepend>
                  <v-icon>mdi-cog</v-icon>
                </template>
                <v-list-item-title>My Settings</v-list-item-title>
              </v-list-item>

              <v-list-item :to="{ name: 'ApiKeys' }">
                <template v-slot:prepend>
                  <v-icon>mdi-key-variant</v-icon>
                </template>
                <v-list-item-title>My API Keys</v-list-item-title>
              </v-list-item>

              <v-divider />

              <v-list-item
                v-if="currentUser"
                prepend-icon="mdi-logout"
                title="Logout"
                @click="handleLogout"
              />
            </v-list>
          </v-menu>
        </div>
      </div>
    </v-app-bar>

    <!-- Main Content -->
    <v-main id="main-content">
      <v-container fluid>
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </v-container>
    </v-main>

    <!-- Footer -->
    <v-footer app color="surface" border>
      <v-row no-gutters align="center">
        <v-col class="text-center" cols="12">
          <span class="text-caption">
            GiljoAI MCP Orchestrator v0.1.0 |
            <span class="text-primary">{{ activeAgents }} agents active</span> |
            <span class="text-secondary">{{ pendingMessages }} messages pending</span>
          </span>
        </v-col>
      </v-row>
    </v-footer>

    <!-- Keyboard Shortcuts Help Modal -->
    <v-dialog v-model="isHelpModalOpen" max-width="600" @click:outside="hideHelp">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-keyboard</v-icon>
          Keyboard Shortcuts
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="text" @click="hideHelp"></v-btn>
        </v-card-title>

        <v-card-text>
          <v-list density="compact">
            <template v-for="(shortcut, index) in shortcuts" :key="index">
              <v-list-item v-if="!shortcut.context || shortcut.context === route.name">
                <template v-slot:prepend>
                  <kbd class="keyboard-shortcut">{{ shortcut.key }}</kbd>
                </template>
                <v-list-item-title>{{ shortcut.description }}</v-list-item-title>
              </v-list-item>
            </template>
          </v-list>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" variant="flat" @click="hideHelp"> Close </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Toast Notifications -->
    <ToastManager ref="toastManager" position="bottom-right" />
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTheme, useDisplay } from 'vuetify'
import { useWebSocketStore } from '@/stores/websocket'
import { useAgentStore } from '@/stores/agents'
import { useMessageStore } from '@/stores/messages'
import { useUserStore } from '@/stores/user'
import { useProductStore } from '@/stores/products'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import ConnectionStatus from '@/components/ConnectionStatus.vue'
import ProductSwitcher from '@/components/ProductSwitcher.vue'
import ToastManager from '@/components/ToastManager.vue'
import api from '@/services/api'

// Composables
const route = useRoute()
const router = useRouter()
const theme = useTheme()
const { mobile } = useDisplay()
const wsStore = useWebSocketStore()
const agentStore = useAgentStore()
const messageStore = useMessageStore()
const userStore = useUserStore()
const productStore = useProductStore()
const { isHelpModalOpen, hideHelp, shortcuts } = useKeyboardShortcuts()

// State
const drawer = ref(true)
const rail = ref(false)
const currentUser = ref(null)

// Navigation items - filter based on user role
const navigationItems = computed(() => {
  const baseItems = [
    { name: 'Dashboard', path: '/', title: 'Dashboard', icon: 'mdi-view-dashboard' },
    { name: 'Projects', path: '/projects', title: 'Projects', icon: 'mdi-folder-multiple' },
    { name: 'Agents', path: '/agents', title: 'Agents', customIcon: '/Giljo_gray_Face.svg?v=2' },
    { name: 'Messages', path: '/messages', title: 'Messages', icon: 'mdi-message-text' },
    { name: 'Tasks', path: '/tasks', title: 'Tasks', icon: 'mdi-clipboard-check' },
  ]

  // Add admin-only menu items
  if (userStore.isAdmin) {
    baseItems.push({
      name: 'SystemSettings',
      path: '/admin/settings',
      title: 'System Settings',
      icon: 'mdi-cog-outline',
    })
    baseItems.push({
      name: 'Users',
      path: '/users',
      title: 'Users',
      icon: 'mdi-account-multiple',
    })
  }

  return baseItems
})

// Computed
const currentPageTitle = computed(() => route.meta.title || 'GiljoAI MCP')
const wsConnected = computed(() => wsStore.isConnected)
const activeAgents = computed(() => agentStore.activeAgents.length)
const pendingMessages = computed(() => messageStore.pendingMessages.length)

// Methods
const toggleTheme = () => {
  // Add transition class for smooth theme switching
  document.documentElement.classList.remove('no-transition')

  // Toggle the theme
  theme.global.name.value = theme.global.current.value.dark ? 'light' : 'dark'

  // Update data-theme attribute for CSS variables
  document.documentElement.setAttribute('data-theme', theme.global.name.value)

  // Store preference
  localStorage.setItem('theme-preference', theme.global.name.value)
}

const getRoleColor = (role) => {
  if (!role) return 'grey'
  const roleLower = role.toLowerCase()

  // Color coding: Admin=Red/Pink, Developer=Blue, Viewer=Green
  if (roleLower === 'admin') return 'error'
  if (roleLower === 'developer' || roleLower === 'dev') return 'primary'
  if (roleLower === 'viewer') return 'success'

  return 'grey' // Default for unknown roles
}

const handleLogout = async () => {
  try {
    // Call logout endpoint
    await api.auth.logout()

    // Clear any cached user state
    currentUser.value = null
    localStorage.removeItem('user')

    // Disconnect WebSocket
    wsStore.disconnect()

    // Redirect to login page
    router.push('/login')

    console.log('[Auth] User logged out successfully')
  } catch (error) {
    console.error('[Auth] Logout failed:', error)
    // Even if logout fails, clear local state and redirect
    currentUser.value = null
    localStorage.removeItem('user')
    router.push('/login')
  }
}

const loadCurrentUser = async () => {
  try {
    const response = await api.auth.me()
    currentUser.value = response.data
    
    // Also update user store for consistency
    userStore.currentUser = response.data
    
    console.log('[Auth] Current user loaded:', currentUser.value.username)
    return true
  } catch (error) {
    // Not authenticated or error occurred
    console.log('[Auth] Not authenticated or error loading user')
    currentUser.value = null
    userStore.currentUser = null
    const currentRoute = router.currentRoute.value
    const requiresAuth = currentRoute ? currentRoute.meta?.requiresAuth !== false : true

    // v3.0 Unified: Redirect to login only when the current route requires auth
    if (requiresAuth) {
      console.log('[Auth] Not authenticated, redirecting to login')
      router.push({
        path: '/login',
        query: { redirect: window.location.pathname + window.location.search }
      })
    }

    return false
  }
}

// Lifecycle
let messagePollingInterval = null

onMounted(async () => {
  // Prevent transitions on initial load
  document.documentElement.classList.add('no-transition')

  // Restore theme preference
  const savedTheme = localStorage.getItem('theme-preference')
  if (savedTheme) {
    theme.global.name.value = savedTheme
    document.documentElement.setAttribute('data-theme', savedTheme)
  } else {
    document.documentElement.setAttribute('data-theme', 'dark')
  }

  // Enable transitions after a short delay
  setTimeout(() => {
    document.documentElement.classList.remove('no-transition')
  }, 100)

  // Wait for router to resolve initial navigation (ensures meta flags are accurate)
  await router.isReady()

  // Load current user (if authenticated)
  await loadCurrentUser()

  // Only connect WebSocket and start polling if user is authenticated
  if (currentUser.value) {
    // Connect WebSocket with authentication credentials
    try {
      // Get auth token from localStorage for WebSocket authentication
      const authToken = localStorage.getItem('auth_token')
      const wsOptions = authToken ? { token: authToken } : {}

      await wsStore.connect(wsOptions)
      console.log('WebSocket connected successfully')

      // Post-auth initialization: Initialize product store first
      await productStore.initializeFromStorage()

      // Load initial data
      await Promise.all([agentStore.fetchAgents(), messageStore.fetchMessages()])

      // Set up 10-second message polling interval
      messagePollingInterval = setInterval(async () => {
        try {
          await messageStore.fetchMessages()
          console.log('Messages refreshed at', new Date().toLocaleTimeString())
        } catch (error) {
          console.error('Failed to fetch messages:', error)
        }
      }, 10000) // Poll every 10 seconds

      // Subscribe to relevant updates for the whole app
      // Individual views will subscribe to specific entities

      // Listen for notifications
      window.addEventListener('ws-notification', handleNotification)
      window.addEventListener('new-message', handleNewMessage)
    } catch (error) {
      console.error('Failed to initialize WebSocket:', error)
    }
  } else {
    console.log('[Auth] User not authenticated, skipping WebSocket connection and message polling')
  }
})

onUnmounted(() => {
  // Clear message polling interval
  if (messagePollingInterval) {
    clearInterval(messagePollingInterval)
  }

  // Cleanup WebSocket connection and event listeners
  wsStore.disconnect()
  window.removeEventListener('ws-notification', handleNotification)
  window.removeEventListener('new-message', handleNewMessage)
})

// Event handlers
const handleNotification = (event) => {
  const notification = event.detail
  console.log('Notification received:', notification)
  // Could show a toast/snackbar here
}

const handleNewMessage = (event) => {
  const message = event.detail
  console.log('New message received:', message)
  // Could show a notification or update UI
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.keyboard-shortcut {
  display: inline-block;
  padding: 2px 6px;
  margin-right: 8px;
  background: rgba(var(--v-theme-surface-variant), 0.5);
  border: 1px solid rgba(var(--v-theme-on-surface), 0.2);
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
  font-weight: 600;
  min-width: 60px;
  text-align: center;
}

.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  padding: 8px 16px;
  text-decoration: none;
  z-index: 100;
  border-radius: 0 0 4px 0;
}

.skip-link:focus {
  top: 0;
}
</style>
