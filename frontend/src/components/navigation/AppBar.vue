<template>
  <v-app-bar color="surface" elevation="0" border>
    <div style="display: flex; align-items: center; width: 100%; justify-content: space-between">
      <!-- Left: Logo and Mobile Nav Toggle -->
      <div style="flex: 0 0 auto; display: flex; align-items: center">
        <v-app-bar-nav-icon
          v-if="mobile"
          aria-label="Toggle navigation drawer"
          @click="$emit('toggle-drawer')"
        ></v-app-bar-nav-icon>

        <!-- GiljoAI Logo -->
        <v-img
          src="/Giljo_YW.svg"
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

          <v-list density="compact" min-width="220">
            <v-list-item
              v-if="currentUser"
              prepend-icon="mdi-account"
              style="cursor: pointer"
              @click="profileDialog = true"
            >
              <v-list-item-title class="font-weight-medium">
                {{ currentUser.username }}
              </v-list-item-title>
              <!-- Workspace subtitle (Handover 0424i) -->
              <v-list-item-subtitle v-if="userStore.currentOrg" class="text-caption mt-1">
                {{ userStore.currentOrg.name }}
              </v-list-item-subtitle>
              <!-- System role chip -->
              <v-list-item-subtitle v-if="currentUser.role" class="d-flex align-center mt-2 gap-2">
                <v-chip
                  :color="getRoleColor(currentUser.role)"
                  size="small"
                  variant="flat"
                  class="text-caption"
                >
                  {{ currentUser.role }}
                </v-chip>
                <!-- Workspace role badge (Handover 0424i) -->
                <RoleBadge
                  v-if="userStore.orgRole"
                  :role="userStore.orgRole"
                  size="small"
                />
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
            <v-divider v-if="currentUser && currentUser.role === 'admin'" />

            <v-list-item
              v-if="currentUser && currentUser.role === 'admin'"
              :to="{ name: 'SystemSettings' }"
            >
              <template v-slot:prepend>
                <v-icon color="error">mdi-cog</v-icon>
              </template>
              <v-list-item-title>Admin Settings</v-list-item-title>
            </v-list-item>

            <v-divider />

            <v-list-item
              prepend-icon="mdi-information-outline"
              title="About"
              @click="aboutDialog = true"
            />

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

        <!-- About Dialog -->
        <v-dialog v-model="aboutDialog" max-width="460">
          <v-card>
            <v-card-title class="d-flex align-center pa-4">
              <v-img
                src="/Giljo_YW.svg"
                alt="GiljoAI"
                height="28"
                width="auto"
                max-width="120"
                class="mr-3"
              ></v-img>
              <span class="text-h6">About</span>
            </v-card-title>

            <v-divider />

            <v-card-text class="pa-5">
              <v-list density="compact" class="pa-0">
                <v-list-item class="px-0">
                  <template v-slot:prepend>
                    <v-icon size="small" class="mr-3">mdi-tag</v-icon>
                  </template>
                  <v-list-item-title class="text-body-2">Edition</v-list-item-title>
                  <template v-slot:append>
                    <span class="text-body-2 edition-value">Community Edition</span>
                  </template>
                </v-list-item>

                <v-list-item class="px-0">
                  <template v-slot:prepend>
                    <v-icon size="small" class="mr-3">mdi-application-brackets</v-icon>
                  </template>
                  <v-list-item-title class="text-body-2">Version</v-list-item-title>
                  <template v-slot:append>
                    <span class="text-body-2">3.0.0</span>
                  </template>
                </v-list-item>

                <v-list-item class="px-0">
                  <template v-slot:prepend>
                    <v-icon size="small" class="mr-3">mdi-license</v-icon>
                  </template>
                  <v-list-item-title class="text-body-2">License</v-list-item-title>
                  <template v-slot:append>
                    <v-chip
                      :color="licenseStatus === 'Licensed' ? 'success' : 'warning'"
                      size="small"
                      variant="flat"
                    >
                      {{ licenseStatus }}
                    </v-chip>
                  </template>
                </v-list-item>
              </v-list>

              <v-divider class="my-4" />

              <p class="text-body-2 text-medium-emphasis mb-3">
                GiljoAI Community License v1.0 &mdash; free for single-user use.
                Multi-user deployments require a Commercial License.
              </p>

              <div class="d-flex ga-2">
                <v-btn
                  variant="outlined"
                  size="small"
                  href="https://github.com/patrik-giljoai/GiljoAI_MCP/blob/master/LICENSE"
                  target="_blank"
                  prepend-icon="mdi-open-in-new"
                >
                  View License
                </v-btn>
                <v-btn
                  v-if="licenseStatus === 'Unlicensed'"
                  variant="outlined"
                  size="small"
                  href="mailto:licensing@giljoai.com"
                  prepend-icon="mdi-email-outline"
                >
                  Get License
                </v-btn>
              </div>
            </v-card-text>

            <v-divider />

            <v-card-actions class="pa-3">
              <v-spacer />
              <v-btn variant="text" @click="aboutDialog = false">Close</v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>
      </div>
    </div>
  </v-app-bar>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useDisplay } from 'vuetify'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useWebSocketStore } from '@/stores/websocket'
import ConnectionStatus from '@/components/ConnectionStatus.vue'
import ActiveProductDisplay from '@/components/ActiveProductDisplay.vue'
import UserProfileDialog from '@/components/UserProfileDialog.vue'
import NotificationDropdown from '@/components/navigation/NotificationDropdown.vue'
import RoleBadge from '@/components/common/RoleBadge.vue'
import api from '@/services/api'
import configService from '@/services/configService'

const props = defineProps({
  currentUser: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['toggle-drawer'])

const { mobile } = useDisplay()
const router = useRouter()
const userStore = useUserStore()
const wsStore = useWebSocketStore()
const profileDialog = ref(false)
const aboutDialog = ref(false)
const licenseStatus = ref('Licensed')

onMounted(async () => {
  try {
    await configService.fetchConfig()
    const edition = configService.getEdition()
    if (edition === 'community') {
      const apiBaseUrl =
        window.API_BASE_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:7272'
      const response = await fetch(`${apiBaseUrl}/api/setup/status`, {
        method: 'GET',
        cache: 'no-cache',
      })
      if (response.ok) {
        const data = await response.json()
        if ((data.total_users_count || 0) > 1) {
          licenseStatus.value = 'Unlicensed'
        }
      }
    }
  } catch {
    // Silently fail
  }
})

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

.edition-value {
  color: #ffc300;
  font-weight: 500;
}
</style>
