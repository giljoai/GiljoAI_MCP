<template>
  <v-app>
    <!-- Navigation Drawer -->
    <v-navigation-drawer
      v-model="drawer"
      :rail="rail"
      permanent
      color="surface"
    >
      <!-- Logo/Mascot -->
      <v-list-item
        prepend-avatar="/icons/Giljo_YW_Face.svg"
        title="GiljoAI MCP"
        subtitle="Orchestrator"
        class="px-2"
      >
        <template v-slot:append>
          <v-btn
            variant="text"
            icon="mdi-chevron-left"
            @click.stop="rail = !rail"
          ></v-btn>
        </template>
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
    <v-app-bar
      color="surface"
      elevation="0"
      border
    >
      <v-app-bar-nav-icon
        @click="drawer = !drawer"
        v-if="mobile"
      ></v-app-bar-nav-icon>

      <v-toolbar-title>{{ currentPageTitle }}</v-toolbar-title>

      <v-spacer></v-spacer>

      <!-- Status Indicators -->
      <v-chip
        v-if="wsConnected"
        color="success"
        variant="tonal"
        size="small"
        class="mr-2"
      >
        <v-icon start size="x-small">mdi-wifi</v-icon>
        Connected
      </v-chip>
      <v-chip
        v-else
        color="error"
        variant="tonal"
        size="small"
        class="mr-2"
      >
        <v-icon start size="x-small">mdi-wifi-off</v-icon>
        Disconnected
      </v-chip>

      <!-- Notifications -->
      <v-btn icon="mdi-bell" variant="text"></v-btn>
    </v-app-bar>

    <!-- Main Content -->
    <v-main>
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
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTheme, useDisplay } from 'vuetify'
import { useWebSocketStore } from '@/stores/websocket'

// Composables
const route = useRoute()
const theme = useTheme()
const { mobile } = useDisplay()
const wsStore = useWebSocketStore()

// State
const drawer = ref(true)
const rail = ref(false)
const activeAgents = ref(0)
const pendingMessages = ref(0)

// Navigation items
const navigationItems = [
  { name: 'Dashboard', path: '/', title: 'Dashboard', icon: 'mdi-view-dashboard' },
  { name: 'Projects', path: '/projects', title: 'Projects', icon: 'mdi-folder-multiple' },
  { name: 'Agents', path: '/agents', title: 'Agents', icon: 'mdi-robot' },
  { name: 'Messages', path: '/messages', title: 'Messages', icon: 'mdi-message-text' },
  { name: 'Tasks', path: '/tasks', title: 'Tasks', icon: 'mdi-clipboard-check' },
  { name: 'Settings', path: '/settings', title: 'Settings', icon: 'mdi-cog' }
]

// Computed
const currentPageTitle = computed(() => route.meta.title || 'GiljoAI MCP')
const wsConnected = computed(() => wsStore.connected)

// Methods
const toggleTheme = () => {
  theme.global.name.value = theme.global.current.value.dark ? 'light' : 'dark'
}

// Lifecycle
onMounted(() => {
  // Connect WebSocket
  wsStore.connect()
  
  // Subscribe to WebSocket events
  wsStore.subscribe('agent:status', (data) => {
    // Update active agents count
    console.log('Agent status update:', data)
  })
  
  wsStore.subscribe('message:new', (data) => {
    // Update pending messages count
    console.log('New message:', data)
  })
})

onUnmounted(() => {
  // Cleanup WebSocket connection
  wsStore.disconnect()
})
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
</style>