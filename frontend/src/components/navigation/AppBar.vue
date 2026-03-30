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

        <!-- GiljoAI Logo (full on wide, mascot icon on narrow) -->
        <v-img
          src="/Giljo_YW.svg"
          alt="GiljoAI"
          height="36"
          width="auto"
          max-width="140"
          class="ml-2 app-logo-full"
        ></v-img>
        <v-img
          src="/giljo_YW_Face.svg"
          alt="GiljoAI"
          height="28"
          width="28"
          class="ml-2 app-logo-icon"
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
        <v-dialog v-model="aboutDialog" max-width="380">
          <v-card>
            <v-btn
              icon="mdi-close"
              size="x-small"
              variant="text"
              style="position: absolute; right: 8px; top: 8px;"
              @click="aboutDialog = false"
            />
            <v-card-text class="pa-5 text-body-2">
              <div class="font-weight-bold mb-3">GiljoAI MCP</div>
              Beta 1.0.0<br />
              Community Edition<br />
              License: {{ licenseStatus }}<br /><br />
              GiljoAI Community License v1.1<br />
              Free for single-user use. Multi-user deployments require a Commercial License.
              Commercial Licenses may be obtained at no cost at GiljoAI LLC's discretion.<br /><br />
              <a
                href="https://www.giljo.ai"
                target="_blank"
                class="about-link"
              >giljo.ai</a>
              &nbsp;&middot;&nbsp;
              <a
                href="https://github.com/patrik-giljoai/GiljoAI_MCP/blob/master/LICENSE"
                target="_blank"
                class="about-link"
              >View License</a>
              <template v-if="licenseStatus === 'Unlicensed'">
                &nbsp;&middot;&nbsp;
                <a href="mailto:sales@giljo.ai" class="about-link">Get a License</a>
              </template>
            </v-card-text>
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
import setupService from '@/services/setupService'

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
      const data = await setupService.checkEnhancedStatus()
      if ((data.total_users_count || 0) > 1) {
        licenseStatus.value = 'Unlicensed'
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

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;

/* AppBar styling */

.about-link {
  color: $color-brand-yellow;
}

/* Logo toggle: full logo on wide, mascot icon on narrow */
.app-logo-icon {
  display: none;
}

@media (max-width: 1024px) {
  .app-logo-full {
    display: none;
  }

  .app-logo-icon {
    display: block;
  }
}
</style>
