<template>
  <v-app>
    <!-- Skip Navigation Links (Screen Reader Accessible) -->
    <a href="#main-content" class="skip-link">Skip to main content</a>
    <a href="#navigation" class="skip-link">Skip to navigation</a>
    <!-- Navigation Drawer -->
    <v-navigation-drawer id="navigation" v-model="drawer" :rail="rail" permanent color="surface" width="180">
      <!-- Logo/Mascot -->
      <v-list-item class="px-2" style="min-height: 64px;">
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
              :src="theme.global.current.value.dark ? '/icons/Giljo_YW_Face.svg' : '/icons/Giljo_BY_Face.svg'"
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
          :prepend-icon="item.icon"
          :title="item.title"
          :value="item.name"
          color="primary"
        ></v-list-item>
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
      <!-- Sidebar Toggle -->
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

      <v-spacer></v-spacer>

      <v-toolbar-title style="color: #ffc300; font-weight: 600;">Agent Orchestration MCP Server</v-toolbar-title>

      <v-spacer></v-spacer>

      <!-- Product Switcher -->
      <ProductSwitcher class="mr-3" />

      <!-- WebSocket Connection Status -->
      <ConnectionStatus class="mr-2" />

      <!-- Notifications -->
      <v-btn icon="mdi-bell" variant="text" aria-label="View notifications"></v-btn>
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
import { useRoute } from 'vue-router'
import { useTheme, useDisplay } from 'vuetify'
import { useWebSocketStore } from '@/stores/websocket'
import { useAgentStore } from '@/stores/agents'
import { useMessageStore } from '@/stores/messages'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import ConnectionStatus from '@/components/ConnectionStatus.vue'
import ProductSwitcher from '@/components/ProductSwitcher.vue'
import ToastManager from '@/components/ToastManager.vue'

// Composables
const route = useRoute()
const theme = useTheme()
const { mobile } = useDisplay()
const wsStore = useWebSocketStore()
const agentStore = useAgentStore()
const messageStore = useMessageStore()
const { isHelpModalOpen, hideHelp, shortcuts } = useKeyboardShortcuts()

// State
const drawer = ref(true)
const rail = ref(false)

// Navigation items
const navigationItems = [
  { name: 'Dashboard', path: '/', title: 'Dashboard', icon: 'mdi-view-dashboard' },
  { name: 'Projects', path: '/projects', title: 'Projects', icon: 'mdi-folder-multiple' },
  { name: 'Agents', path: '/agents', title: 'Agents', icon: 'mdi-robot' },
  { name: 'Messages', path: '/messages', title: 'Messages', icon: 'mdi-message-text' },
  { name: 'Tasks', path: '/tasks', title: 'Tasks', icon: 'mdi-clipboard-check' },
  { name: 'Settings', path: '/settings', title: 'Settings', icon: 'mdi-cog' },
]

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

  // Connect WebSocket with optional authentication
  // You can pass { apiKey: 'your-key' } or { token: 'your-token' } if needed
  try {
    await wsStore.connect()
    console.log('WebSocket connected successfully')

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
