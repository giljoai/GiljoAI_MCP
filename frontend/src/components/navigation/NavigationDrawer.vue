<template>
  <v-navigation-drawer
    id="navigation"
    :model-value="modelValue"
    :rail="rail"
    :permanent="!temporary"
    :temporary="temporary"
    :mobile="false"
    color="surface"
    width="180"
    class="navigation-drawer-container"
    @update:model-value="$emit('update:model-value', $event)"
  >
    <!-- Edge-Aligned Collapse Tab -->
    <div
      v-if="(!rail || temporary) && modelValue"
      class="edge-toggle-tab"
      :aria-label="temporary ? 'Close navigation' : 'Collapse sidebar'"
      role="button"
      tabindex="0"
      @click="temporary ? $emit('update:model-value', false) : $emit('toggle-rail')"
      @keydown.enter="temporary ? $emit('update:model-value', false) : $emit('toggle-rail')"
      @keydown.space.prevent="temporary ? $emit('update:model-value', false) : $emit('toggle-rail')"
    >
      <v-icon size="20">mdi-chevron-left</v-icon>
    </div>

    <!-- ─── TOP SECTION: Logo + Product ─── -->
    <div class="nav-top">
      <!-- Logo -->
      <div class="nav-logo" :class="{ 'nav-logo--rail': rail }">
        <v-img
          v-if="!rail"
          src="/Giljo_YW.svg"
          alt="GiljoAI"
          height="32"
          width="auto"
          max-width="120"
          class="nav-logo-full"
        />
        <v-img
          v-else
          src="/giljo_YW_Face.svg"
          alt="GiljoAI"
          height="28"
          width="28"
          class="nav-logo-icon"
        />
      </div>

      <!-- Expand chevron (rail/collapsed mode only, inline under logo) -->
      <div
        v-if="rail && !temporary"
        class="nav-expand-btn"
        role="button"
        tabindex="0"
        aria-label="Expand sidebar"
        @click="$emit('toggle-rail')"
        @keydown.enter="$emit('toggle-rail')"
      >
        <v-icon size="22">mdi-chevron-right</v-icon>
      </div>

      <!-- Active Product (subtitle under logo, expanded only) -->
      <router-link
        v-if="!rail"
        :to="{ name: 'Products' }"
        class="nav-product-subtitle"
        :class="{ 'nav-product-subtitle--inactive': !productsStore.activeProduct }"
      >
        {{ productsStore.activeProduct ? productsStore.activeProduct.name : 'No active product' }}
      </router-link>
    </div>

    <!-- ─── NAVIGATION ITEMS ─── -->
    <v-list v-model:selected="selected" density="compact" nav select-strategy="single" class="nav-items">
      <v-list-item
        v-for="item in navigationItems"
        :key="item.name"
        :to="item.path"
        :title="item.title"
        :value="item.name"
        :disabled="item.disabled"
        color="primary"
        role="listitem"
        :exact="true"
      >
        <template v-slot:prepend>
          <v-img
            v-if="item.customIcon"
            :src="item.customIcon"
            width="28"
            height="28"
            :style="{
              marginLeft: '-2px',
              marginRight: '30px',
            }"
          ></v-img>
          <v-icon v-else>{{ item.icon }}</v-icon>
        </template>
      </v-list-item>
    </v-list>

    <!-- ─── BOTTOM SECTION: Bell, Connection, Avatar ─── -->
    <template v-slot:append>
      <div class="nav-bottom">
        <div class="nav-orb-row" :class="{ 'nav-orb-row--stacked': rail }">
          <!-- Notification Bell -->
          <NotificationDropdown :compact="true" />

          <!-- Connection Status -->
          <v-tooltip location="right">
            <template v-slot:activator="{ props: tipProps }">
              <div
                v-bind="tipProps"
                class="nav-orb nav-orb--connection"
                :class="{ 'nav-orb--warning': connectionColor === 'warning', 'nav-orb--error': connectionColor === 'error' }"
                role="button"
                tabindex="0"
                aria-label="Connection status"
                @click="showConnectionDebug = true"
              >
                <v-icon :icon="connectionIcon" size="18" />
              </div>
            </template>
            {{ connectionText }}
          </v-tooltip>

          <!-- User Avatar -->
          <v-menu :close-on-content-click="true" location="right" offset="8">
            <template v-slot:activator="{ props: menuProps }">
              <div v-bind="menuProps" class="nav-orb nav-orb--avatar" role="button" tabindex="0" aria-label="User menu">
                <span v-if="currentUser" class="nav-orb-initials">{{ userInitials }}</span>
                <v-icon v-else size="18">mdi-account</v-icon>
              </div>
            </template>

            <v-list density="compact" min-width="220">
              <v-list-item
                v-if="currentUser"
                prepend-icon="mdi-account"
                class="cursor-pointer"
                @click="profileDialog = true"
              >
                <v-list-item-title class="font-weight-medium">
                  {{ currentUser.username }}
                </v-list-item-title>
                <v-list-item-subtitle v-if="userStore.currentOrg" class="text-caption mt-1">
                  {{ userStore.currentOrg.name }}
                </v-list-item-subtitle>
                <v-list-item-subtitle v-if="currentUser.role" class="d-flex align-center mt-2 gap-2">
                  <v-chip
                    :color="getRoleColor(currentUser.role)"
                    size="small"
                    variant="flat"
                    class="text-caption"
                  >
                    {{ currentUser.role }}
                  </v-chip>
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
        </div>

        <!-- Edition Footer -->
        <div v-if="edition === 'community'" class="edition-footer">
          <span class="edition-label">{{ rail ? 'CE' : 'Community Edition' }}</span>
        </div>
      </div>

      <!-- Profile Dialog -->
      <UserProfileDialog v-if="currentUser" v-model="profileDialog" :user="currentUser" />

      <!-- About Dialog -->
      <v-dialog v-model="aboutDialog" max-width="380">
        <v-card class="smooth-border">
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

      <!-- Connection Debug Panel (from ConnectionStatus) -->
      <ConnectionDebugDialog v-model="showConnectionDebug" />
    </template>
  </v-navigation-drawer>

  <!-- Mobile: floating menu button when drawer is closed -->
  <v-btn
    v-if="temporary && !modelValue"
    icon="mdi-menu"
    size="small"
    variant="flat"
    color="surface"
    class="mobile-menu-fab"
    aria-label="Open navigation"
    @click="$emit('update:model-value', true)"
  />
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projects'
import { useProductStore } from '@/stores/products'
import { useUserStore } from '@/stores/user'
import { useWebSocketStore } from '@/stores/websocket'
import configService from '@/services/configService'
import setupService from '@/services/setupService'
import api from '@/services/api'
import NotificationDropdown from '@/components/navigation/NotificationDropdown.vue'
import ConnectionDebugDialog from '@/components/navigation/ConnectionDebugDialog.vue'
import UserProfileDialog from '@/components/UserProfileDialog.vue'
import RoleBadge from '@/components/common/RoleBadge.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: true,
  },
  rail: {
    type: Boolean,
    default: false,
  },
  temporary: {
    type: Boolean,
    default: false,
  },
  currentUser: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:model-value', 'toggle-rail'])

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const productsStore = useProductStore()
const userStore = useUserStore()
const wsStore = useWebSocketStore()

// Track which nav item is selected
const selected = ref([])

// Dialogs
const profileDialog = ref(false)
const aboutDialog = ref(false)
const showConnectionDebug = ref(false)
const licenseStatus = ref('Licensed')

// Edition state
const edition = ref('')

async function checkEdition() {
  try {
    await configService.fetchConfig()
    edition.value = configService.getEdition()
  } catch {
    edition.value = 'community'
  }
}

// User initials for avatar
const userInitials = computed(() => {
  if (!props.currentUser?.username) return '?'
  return props.currentUser.username.substring(0, 2).toUpperCase()
})

// Connection status (simplified from ConnectionStatus.vue)
const connectionIcon = computed(() => {
  switch (wsStore.connectionStatus) {
    case 'connected': return 'mdi-wifi'
    case 'connecting':
    case 'reconnecting': return 'mdi-wifi-sync'
    case 'disconnected': return 'mdi-wifi-off'
    default: return 'mdi-help-circle'
  }
})

const connectionColor = computed(() => {
  switch (wsStore.connectionStatus) {
    case 'connected': return 'success'
    case 'connecting':
    case 'reconnecting': return 'warning'
    case 'disconnected': return 'error'
    default: return 'grey'
  }
})

const connectionText = computed(() => {
  switch (wsStore.connectionStatus) {
    case 'connected': return 'Connected'
    case 'connecting': return 'Connecting...'
    case 'reconnecting': return `Reconnecting (${wsStore.reconnectAttempts}/${wsStore.maxReconnectAttempts})`
    case 'disconnected': return 'Disconnected'
    default: return 'Unknown'
  }
})

// Role color helper
const getRoleColor = (role) => {
  if (!role) return 'grey'
  const r = role.toLowerCase()
  if (r === 'admin') return 'error'
  if (r === 'developer' || r === 'dev') return 'primary'
  if (r === 'viewer') return 'success'
  return 'grey'
}

// Logout
const handleLogout = async () => {
  try {
    await api.auth.logout()
    localStorage.removeItem('user')
    userStore.currentUser = null
    wsStore.disconnect()
    router.push('/login')
  } catch {
    userStore.currentUser = null
    localStorage.removeItem('user')
    router.push('/login')
  }
}

// Dynamic Giljo icon for Jobs based on route
const jobsIcon = computed(() => {
  const isJobsRoute = route.path.includes('/projects/')
  if (isJobsRoute) return '/icons/Giljo_YW_Face.svg'
  return '/icons/Giljo_Inactive_Dark.svg'
})

// Navigation items
const navigationItems = computed(() => {
  const activeProj = projectStore.activeProject
  const jobsPath = activeProj
    ? `/projects/${activeProj.id}?via=jobs`
    : '/launch?via=jobs'

  return [
    { name: 'Home', path: '/home', title: 'Home', icon: 'mdi-home' },
    { name: 'Dashboard', path: '/Dashboard', title: 'Dashboard', icon: 'mdi-view-dashboard' },
    { name: 'Products', path: '/Products', title: 'Products', icon: 'mdi-package-variant' },
    { name: 'Projects', path: '/projects', title: 'Projects', icon: 'mdi-folder-multiple' },
    { name: 'Jobs', path: jobsPath, title: 'Jobs', customIcon: jobsIcon.value },
    { name: 'Tasks', path: '/tasks', title: 'Tasks', icon: 'mdi-clipboard-check' },
  ]
})

// Route-based selection logic
const updateSelectedFromRoute = () => {
  const items = navigationItems.value
  const currentPath = route.path

  if (route?.query?.via === 'jobs') {
    selected.value = ['Jobs']
    return
  }
  if (currentPath.startsWith('/projects/')) {
    selected.value = ['Jobs']
    return
  }

  let best = null
  for (const item of items) {
    if (!item.path) continue
    if (currentPath === item.path || currentPath.startsWith(`${item.path}/`)) {
      if (!best || item.path.length > best.path.length) {
        best = item
      }
    }
  }
  selected.value = best ? [best.name] : []
}

onMounted(async () => {
  updateSelectedFromRoute()
  checkEdition()

  // Check license status
  try {
    await configService.fetchConfig()
    const ed = configService.getEdition()
    if (ed === 'community') {
      const data = await setupService.checkEnhancedStatus()
      if ((data.total_users_count || 0) > 1) {
        licenseStatus.value = 'Unlicensed'
      }
    }
  } catch {
    // Silently fail
  }
})

watch(
  () => route.path,
  () => updateSelectedFromRoute(),
)
</script>

<style scoped lang="scss">
@use '../../styles/design-tokens' as *;

.navigation-drawer-container {
  overflow: visible;
}

// Force width in temporary mode
.navigation-drawer-container.v-navigation-drawer--temporary {
  width: 180px !important; /* !important: override Vuetify v-navigation-drawer inline width */
}

// ─── EDGE TOGGLE TAB ───
.edge-toggle-tab {
  position: absolute;
  right: -16px;
  top: 20px;
  width: 32px;
  height: 32px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-border-color), 0.15) !important; /* !important: ensure border visibility over adjacent elevated surfaces */
  border-radius: $border-radius-sharp;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 100;
  transition: all $transition-normal ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.edge-toggle-tab:hover {
  background: rgba(var(--v-theme-primary), 0.1);
  box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgb(var(--v-theme-primary)));
}

.edge-toggle-tab:focus {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.edge-toggle-tab:active {
  transform: scale(0.95);
}

// ─── TOP SECTION ───
.nav-top {
  padding: 16px 12px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.nav-logo {
  display: flex;
  justify-content: center;
  width: 100%;
}

.nav-logo--rail {
  padding: 4px 0;
}

.nav-expand-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 36px;
  cursor: pointer;
  color: rgba(var(--v-theme-on-surface), 0.6);
  transition: all $transition-normal ease;
  margin-bottom: -4px;

  &:hover {
    color: rgb(var(--v-theme-primary));
  }
}

.nav-product-subtitle {
  font-size: 0.8rem;
  color: $color-brand-yellow;
  text-decoration: none;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
  padding: 0 4px;
  transition: color $transition-normal ease;
  display: block;
  font-weight: 500;

  &:hover {
    color: $color-brand-yellow-hover;
  }

  &--inactive {
    font-size: 0.7rem;
    color: var(--text-muted);
    font-weight: 400;

    &:hover {
      color: $color-brand-yellow;
    }
  }
}

// ─── NAV ITEMS ───
.nav-items {
  flex: 1;
}


// ─── BOTTOM SECTION ───
.nav-bottom {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0 16px;
  gap: 8px;
}

.nav-orb-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;

  &--stacked {
    flex-direction: column;
    gap: 6px;
  }
}

// ─── ORBS: unified round icons ───
.nav-orb {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all $transition-normal ease;
}

.nav-orb:hover {
  transform: scale(1.08);
}

.nav-orb:active {
  transform: scale(0.95);
}

// Connection: opaque green background, bright green icon
.nav-orb--connection {
  background: rgba($color-accent-success, 0.15);
  color: $color-accent-success;

  &:hover {
    background: rgba($color-accent-success, 0.25);
  }
}

.nav-orb--connection.nav-orb--warning {
  background: rgba($color-brand-yellow, 0.15);
  color: $color-brand-yellow;

  &:hover {
    background: rgba($color-brand-yellow, 0.25);
  }
}

.nav-orb--connection.nav-orb--error {
  background: rgba($color-accent-danger, 0.15);
  color: $color-accent-danger;

  &:hover {
    background: rgba($color-accent-danger, 0.25);
  }
}

// Avatar: brand yellow background, dark initials
.nav-orb--avatar {
  background: rgba($color-brand-yellow, 0.15);
  color: $color-brand-yellow;

  &:hover {
    background: rgba($color-brand-yellow, 0.25);
  }
}

.nav-orb-initials {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.edition-footer {
  padding: 8px 0 0;
  text-align: center;
  border-top: 1px solid rgba(var(--v-border-color), 0.15);
  width: 100%;
  margin-top: 4px;
}

.edition-label {
  color: $color-brand-yellow;
  font-weight: 500;
  letter-spacing: 0.02em;
}

.about-link {
  color: $color-brand-yellow;
}

// ─── MOBILE FAB ───
.mobile-menu-fab {
  position: fixed;
  top: 12px;
  left: 12px;
  z-index: 100;
  border-radius: 50%;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

// Mobile: bigger touch targets for orbs
@media (max-width: 1024px) {
  .nav-orb {
    width: 44px;
    height: 44px;
  }

  .nav-orb-initials {
    font-size: 0.8rem;
  }
}

</style>
