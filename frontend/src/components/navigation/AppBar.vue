<template>
  <v-app-bar color="surface" elevation="0" border>
    <div style="display: flex; align-items: center; width: 100%; justify-content: space-between">
      <!-- Left: Logo and Mobile Nav Toggle -->
      <div style="flex: 0 0 auto; display: flex; align-items: center">
        <v-app-bar-nav-icon
          @click="$emit('toggle-drawer')"
          v-if="mobile"
          aria-label="Toggle navigation drawer"
        ></v-app-bar-nav-icon>

        <!-- GiljoAI Logo -->
        <v-img
          :src="theme.global.current.value.dark ? '/Giljo_YW.svg' : '/Giljo_BY.svg'"
          alt="GiljoAI"
          height="36"
          width="auto"
          max-width="140"
          class="ml-2"
        ></v-img>
      </div>

      <!-- Spacer -->
      <v-spacer></v-spacer>

      <!-- Right: Product Switcher, Connection Status, User Menu -->
      <div style="flex: 0 0 auto; display: flex; align-items: center">
        <ActiveProductDisplay class="mr-3" />
        <ConnectionStatus class="mr-2" />
        <NotificationDropdown class="mr-2" />

        <!-- User Menu -->
        <v-menu offset-y>
          <template v-slot:activator="{ props }">
            <v-btn icon v-bind="props" aria-label="User menu">
              <v-icon>mdi-account-circle</v-icon>
            </v-btn>
          </template>

          <v-list density="compact" min-width="200">
            <v-list-item
              v-if="currentUser"
              prepend-icon="mdi-account"
              @click="profileDialog = true"
              style="cursor: pointer"
            >
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

            <!-- Admin Settings - Only visible to admin users -->
            <v-list-item
              v-if="currentUser && currentUser.role === 'admin'"
              :to="{ name: 'SystemSettings' }"
            >
              <template v-slot:prepend>
                <v-icon color="error">mdi-cog</v-icon>
              </template>
              <v-list-item-title>Admin Settings</v-list-item-title>
            </v-list-item>

            <!-- Users Management - Only visible to admin users -->
            <v-list-item v-if="currentUser && currentUser.role === 'admin'" :to="{ name: 'Users' }">
              <template v-slot:prepend>
                <v-icon color="error">mdi-account-multiple</v-icon>
              </template>
              <v-list-item-title>Users</v-list-item-title>
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
        <UserProfileDialog v-if="currentUser" v-model="profileDialog" :user="currentUser" />
      </div>
    </div>
  </v-app-bar>
</template>

<script setup>
import { ref } from 'vue'
import { useTheme, useDisplay } from 'vuetify'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useWebSocketStore } from '@/stores/websocket'
import ConnectionStatus from '@/components/ConnectionStatus.vue'
import ActiveProductDisplay from '@/components/ActiveProductDisplay.vue'
import UserProfileDialog from '@/components/UserProfileDialog.vue'
import NotificationDropdown from '@/components/navigation/NotificationDropdown.vue'
import api from '@/services/api'

const props = defineProps({
  currentUser: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['toggle-drawer'])

const theme = useTheme()
const { mobile } = useDisplay()
const router = useRouter()
const userStore = useUserStore()
const wsStore = useWebSocketStore()
const profileDialog = ref(false)

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
    localStorage.removeItem('user')

    // Also clear store
    userStore.currentUser = null

    // Disconnect WebSocket
    wsStore.disconnect()

    // Redirect to login page
    router.push('/login')

    console.log('[Auth] User logged out successfully')
  } catch (error) {
    console.error('[Auth] Logout failed:', error)
    // Even if logout fails, clear local state and redirect
    userStore.currentUser = null
    localStorage.removeItem('user')
    router.push('/login')
  }
}
</script>

<style scoped>
/* AppBar styling */
</style>
