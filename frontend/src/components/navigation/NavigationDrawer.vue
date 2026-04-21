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
          :class="{ 'nav-logo-full--attention': !hasProduct }"
        />
        <v-img
          v-else
          src="/giljo_YW_Face.svg"
          alt="GiljoAI"
          height="28"
          width="28"
          class="nav-logo-icon"
          :class="{ 'nav-logo-icon--attention': !hasProduct }"
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
        :class="{ 'nav-item--attention': item.attention }"
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

          <!-- Log Download (CE only) -->
          <v-menu
            v-if="giljoMode === 'ce'"
            v-model="logMenuOpen"
            :close-on-content-click="false"
            location="right"
            offset="8"
            @update:model-value="onLogMenuToggle"
          >
            <template v-slot:activator="{ props: logMenuProps }">
              <v-tooltip location="right">
                <template v-slot:activator="{ props: tipProps }">
                  <div
                    v-bind="{ ...logMenuProps, ...tipProps }"
                    class="nav-orb nav-orb--logs"
                    role="button"
                    tabindex="0"
                    aria-label="Download server logs"
                  >
                    <v-icon icon="mdi-file-document-outline" size="18" />
                  </div>
                </template>
                Server logs
              </v-tooltip>
            </template>

            <v-card class="smooth-border log-download-menu" min-width="240">
              <v-list density="compact">
                <v-list-item
                  prepend-icon="mdi-download"
                  title="Download Current Log"
                  @click="downloadCurrentLog"
                />

                <v-divider class="my-1" />

                <v-list-subheader class="log-menu-subheader">Archives</v-list-subheader>

                <template v-if="logArchivesLoading">
                  <v-list-item>
                    <v-progress-linear indeterminate color="primary" class="my-2" />
                  </v-list-item>
                </template>

                <template v-else-if="logArchives.length === 0">
                  <v-list-item disabled title="No archives available" />
                </template>

                <template v-else>
                  <v-list-item
                    v-for="archive in logArchives"
                    :key="archive.filename"
                    @click="downloadArchive(archive.filename)"
                  >
                    <v-list-item-title>{{ formatArchiveDate(archive.date) }}</v-list-item-title>
                    <v-list-item-subtitle class="log-archive-size">{{ archive.size_kb }} KB</v-list-item-subtitle>
                    <template v-slot:prepend>
                      <v-icon size="18">mdi-file-clock-outline</v-icon>
                    </template>
                  </v-list-item>
                </template>
              </v-list>
            </v-card>
          </v-menu>

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

              <v-list-item :to="{ name: 'UserGuide' }">
                <template v-slot:prepend>
                  <v-icon>mdi-book-open-variant</v-icon>
                </template>
                <v-list-item-title>User Guide</v-list-item-title>
              </v-list-item>

              <!-- Reset Password (SaaS/demo only) -->
              <v-list-item
                v-if="giljoMode !== 'ce'"
                @click="handleResetPassword"
              >
                <template v-slot:prepend>
                  <v-icon>mdi-lock-reset</v-icon>
                </template>
                <v-list-item-title>Reset Password</v-list-item-title>
              </v-list-item>

              <v-divider v-if="currentUser && currentUser.role === 'admin' && giljoMode === 'ce'" />

              <v-list-item
                v-if="currentUser && currentUser.role === 'admin' && giljoMode === 'ce'"
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
        <div class="edition-footer">
          <span class="edition-label">{{ editionFooterLabel }}</span>
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
              href="https://github.com/giljoai/GiljoAI_MCP/blob/master/LICENSE"
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
import axios from 'axios'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projects'
import { useProductStore } from '@/stores/products'
import { useUserStore } from '@/stores/user'
import { useWebSocketStore } from '@/stores/websocket'
import { useToast } from '@/composables/useToast'
import configService from '@/services/configService'
import setupService from '@/services/setupService'
import api, { apiClient } from '@/services/api'
import NotificationDropdown from '@/components/navigation/NotificationDropdown.vue'
import { defineAsyncComponent } from 'vue'
const ConnectionDebugDialog = defineAsyncComponent(() => import('@/components/navigation/ConnectionDebugDialog.vue'))
const UserProfileDialog = defineAsyncComponent(() => import('@/components/UserProfileDialog.vue'))
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
const { showToast } = useToast()

// Track which nav item is selected
const selected = ref([])

// Dialogs
const profileDialog = ref(false)
const aboutDialog = ref(false)
const showConnectionDebug = ref(false)
const licenseStatus = ref('Licensed')

// Log download state
const logMenuOpen = ref(false)
const logArchives = ref([])
const logArchivesLoading = ref(false)

async function onLogMenuToggle(open) {
  if (open) {
    logArchivesLoading.value = true
    try {
      const response = await apiClient.get('/api/download/logs/archives')
      logArchives.value = response.data || []
    } catch {
      logArchives.value = []
      showToast({ message: 'Failed to load log archives', type: 'error' })
    } finally {
      logArchivesLoading.value = false
    }
  }
}

function downloadCurrentLog() {
  window.open('/api/download/logs/current', '_blank')
  logMenuOpen.value = false
}

function downloadArchive(filename) {
  window.open(`/api/download/logs/archive/${encodeURIComponent(filename)}`, '_blank')
  logMenuOpen.value = false
}

function formatArchiveDate(dateStr) {
  if (!dateStr) return 'Unknown'
  const date = new Date(`${dateStr}T00:00:00`)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

// Edition state
const edition = ref('')
const giljoMode = ref('ce')

async function checkEdition() {
  try {
    await configService.fetchConfig()
    edition.value = configService.getEdition()
    giljoMode.value = configService.getGiljoMode()
  } catch {
    edition.value = 'community'
    giljoMode.value = 'ce'
  }
}

// Edition footer label
const editionFooterLabel = computed(() => {
  switch (giljoMode.value) {
    case 'demo': return props.rail ? 'Demo' : 'Demo Edition'
    case 'saas': return props.rail ? 'SaaS' : 'SaaS Edition'
    default: return props.rail ? 'CE' : 'Community Edition'
  }
})

// Reset password (SaaS/demo mode)
async function handleResetPassword() {
  try {
    const email = props.currentUser?.email
    if (!email) return

    let baseUrl = ''
    if (!import.meta.env.DEV && configService.config) {
      const { host, port } = configService.config.api
      const protocol = configService.config.api?.protocol || (window.location.protocol === 'https:' ? 'https' : 'http')
      baseUrl = `${protocol}://${host}:${port}`
    }

    await axios.post(`${baseUrl}/api/saas/password-reset/request`, { email })
    showToast({ message: 'Password reset email sent. Check your inbox.', type: 'success' })
  } catch (err) {
    const detail = err?.response?.data?.detail
    showToast({ message: detail || 'Unable to send reset email. Please try again later.', type: 'error' })
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
const hasProduct = computed(() => !!productsStore.activeProduct)
const hasProject = computed(() => (projectStore.projects?.length ?? 0) > 0)

const navigationItems = computed(() => {
  const activeProj = projectStore.activeProject
  const jobsPath = activeProj
    ? `/projects/${activeProj.id}?via=jobs`
    : '/launch?via=jobs'

  return [
    { name: 'Home', path: '/home', title: 'Home', icon: 'mdi-home' },
    { name: 'Dashboard', path: '/Dashboard', title: 'Dashboard', icon: 'mdi-view-dashboard' },
    { name: 'Products', path: '/Products', title: 'Products', icon: 'mdi-package-variant', attention: !hasProduct.value },
    { name: 'Projects', path: '/projects', title: 'Projects', icon: 'mdi-folder-multiple', attention: hasProduct.value && !hasProject.value },
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

// ─── ATTENTION ANIMATIONS ───
@keyframes navAttentionNudge {
  0%, 100% {
    transform: translateX(0);
    background: transparent;
  }
  50% {
    transform: translateX(2px);
    background: rgba(255, 195, 0, 0.09);
  }
}

@keyframes logoAttention {
  0%, 100% {
    transform: scale(1);
    filter: drop-shadow(0 0 0 transparent);
  }
  50% {
    transform: scale(1.08);
    filter: drop-shadow(0 0 8px rgba(255, 195, 0, 0.45));
  }
}

.nav-logo-full--attention {
  animation: logoAttention 2.8s ease-in-out 1s infinite;
}

.nav-logo-icon--attention {
  animation: logoAttention 2.8s ease-in-out 1s infinite;
}

.nav-item--attention {
  animation: navAttentionNudge 2.8s ease-in-out 1s infinite;
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

// Logs: muted color, same orb style
.nav-orb--logs {
  background: rgba(136, 149, 168, 0.15);
  color: var(--text-muted);

  &:hover {
    background: rgba(136, 149, 168, 0.25);
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

// ─── LOG DOWNLOAD MENU ───
.log-download-menu {
  max-height: 320px;
  overflow-y: auto;
}

.log-menu-subheader {
  color: var(--text-muted);
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.log-archive-size {
  color: var(--text-muted);
  font-size: 0.75rem;
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
