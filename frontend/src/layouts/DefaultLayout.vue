<template>
  <v-app>
    <StarField />

    <NavigationDrawer
      v-if="!route.meta.hideDrawer"
      v-model="drawer"
      :rail="isMobile ? false : rail"
      :temporary="isMobile"
      :current-user="currentUser"
      @toggle-rail="rail = !rail"
    />

    <v-main>
      <!-- SaaS Trial Expiry Banner (loaded dynamically, absent in CE) -->
      <component :is="TrialBannerComponent" v-if="TrialBannerComponent" />
      <!-- SAAS-023: Account Deletion Banner (loaded dynamically, absent in CE) -->
      <component :is="AccountDeletionBannerComponent" v-if="AccountDeletionBannerComponent" />
      <SystemStatusBanner />
      <router-view :key="$route.path" :current-user="currentUser" />
    </v-main>

    <!-- Global Toast Notifications -->
    <ToastManager />

    <!-- Community Edition Licensing Reminder -->
    <LicensingDialog />

    <!-- SaaS Trial Expired Overlay (loaded dynamically, absent in CE) -->
    <component :is="TrialExpiredOverlayComponent" v-if="TrialExpiredOverlayComponent" />
  </v-app>
</template>

<script setup>
import { ref, computed, shallowRef, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useProductStore } from '@/stores/products'
import { useProjectStatusesStore } from '@/stores/projectStatusesStore'
import { useWebSocketStore } from '@/stores/websocket'
import { useMessageStore } from '@/stores/messages'
import { initWebsocketEventRouter } from '@/stores/websocketEventRouter'
import StarField from '@/components/StarField.vue'
import NavigationDrawer from '@/components/navigation/NavigationDrawer.vue'
import ToastManager from '@/components/ToastManager.vue'
import { defineAsyncComponent } from 'vue'
const LicensingDialog = defineAsyncComponent(() => import('@/components/LicensingDialog.vue'))
import SystemStatusBanner from '@/components/system/SystemStatusBanner.vue'
import setupService from '@/services/setupService'
import configService from '@/services/configService'

// SaaS trial components -- loaded dynamically so CE export stays clean.
// When the saas/ directory is absent (CE build), the import fails silently.
const TrialBannerComponent = shallowRef(null)
const TrialExpiredOverlayComponent = shallowRef(null)
// SAAS-023: account deletion banner (also lazy-loaded for CE-export safety).
const AccountDeletionBannerComponent = shallowRef(null)

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const productStore = useProductStore()
const projectStatusesStore = useProjectStatusesStore()
const wsStore = useWebSocketStore()
const messageStore = useMessageStore()

const drawer = ref(true)
const rail = ref(false)
const windowWidth = ref(window.innerWidth)
const SIDEBAR_BREAKPOINT = 1024
const isMobile = computed(() => windowWidth.value <= SIDEBAR_BREAKPOINT)

function onResize() {
  windowWidth.value = window.innerWidth
  if (isMobile.value) {
    drawer.value = false
  }
}

window.addEventListener('resize', onResize)
const currentUser = ref(null)

const loadCurrentUser = async () => {
  try {
    const success = await userStore.fetchCurrentUser()
    if (success) {
      currentUser.value = userStore.currentUser
      return true
    }
    // fetchCurrentUser returned false (API failed internally)
    currentUser.value = null
    router.push('/login')
    return false
  } catch (error) {
    console.error('[DefaultLayout] Failed to load user:', error)
    currentUser.value = null
    router.push('/login')
    return false
  }
}

onMounted(async () => {
  // CRITICAL FIX (Handover 0034): Check fresh install status FIRST
  // This prevents race condition where DefaultLayout redirects to /login
  // before router guard can redirect to /welcome
  try {
    const setupData = await setupService.checkEnhancedStatus()
    if (setupData.is_fresh_install) {
      router.push('/welcome')
      return
    }
  } catch (setupError) {
    console.warn('[DefaultLayout] Failed to check fresh install status:', setupError)
  }

  // Normal operation: load current user
  const userLoaded = await loadCurrentUser()

  // Restore active product state from localStorage + backend
  if (userLoaded && currentUser.value) {
    await productStore.initializeFromStorage()
  }

  // BE-5039: prime the canonical project-status metadata cache once per
  // session. ensureLoaded() is idempotent and rejects on transport
  // failure so we only catch + log here; consumers (StatusBadge,
  // useProjectFilters) degrade gracefully when the cache is empty.
  if (userLoaded && currentUser.value) {
    projectStatusesStore.ensureLoaded().catch((error) => {
      console.warn('[DefaultLayout] Failed to load project statuses:', error)
    })
  }

  // Load SaaS trial components when in SaaS/Demo mode
  if (userLoaded && currentUser.value) {
    const mode = configService.getGiljoMode()
    if (mode !== 'ce') {
      try {
        // Vite-aware lazy load via import.meta.glob (CE export safe).
        // CE builds have saas/ stripped → glob returns empty → silently skip.
        // SaaS/private builds → Vite bundles each into a lazy chunk.
        // Replaces an earlier @vite-ignore + runtime-URL pattern that 404'd
        // into the SPA fallback in production builds and broke trial UI.
        const bannerLoaders = import.meta.glob('@/saas/components/TrialBanner.vue')
        const overlayLoaders = import.meta.glob('@/saas/components/TrialExpiredOverlay.vue')
        const guardLoaders = import.meta.glob('@/saas/composables/useTrialGuard.js')
        // SAAS-023: deletion banner + account-state store (lazy, CE-stripped).
        const deletionBannerLoaders = import.meta.glob('@/saas/components/AccountDeletionBanner.vue')
        const accountStateStoreLoaders = import.meta.glob('@/saas/stores/useAccountStateStore.js')
        const [bannerLoader] = Object.values(bannerLoaders)
        const [overlayLoader] = Object.values(overlayLoaders)
        const [guardLoader] = Object.values(guardLoaders)
        const [deletionBannerLoader] = Object.values(deletionBannerLoaders)
        const [accountStateStoreLoader] = Object.values(accountStateStoreLoaders)
        if (bannerLoader && overlayLoader && guardLoader) {
          const [bannerMod, overlayMod, guardMod] = await Promise.all([
            bannerLoader(),
            overlayLoader(),
            guardLoader(),
          ])
          TrialBannerComponent.value = bannerMod.default
          TrialExpiredOverlayComponent.value = overlayMod.default
          guardMod.installTrialGuardInterceptor()
        }
        // SAAS-023: wire deletion banner + start polling combined account state.
        if (deletionBannerLoader && accountStateStoreLoader) {
          const [deletionBannerMod, storeMod] = await Promise.all([
            deletionBannerLoader(),
            accountStateStoreLoader(),
          ])
          AccountDeletionBannerComponent.value = deletionBannerMod.default
          const accountStateStore = storeMod.useAccountStateStore()
          accountStateStore.startPolling()
        }
      } catch (error) {
        console.warn('[DefaultLayout] SaaS trial UI failed to load:', error)
      }
    }
  }

  // Initialize WebSocket and data polling only if user is authenticated
  if (userLoaded && currentUser.value) {
    try {
      // Connect WebSocket - browser will automatically send httpOnly access_token cookie
      await wsStore.connect()

      // Initialize the centralized router once (0379a)
      initWebsocketEventRouter({
        onReconnectResync: async () => {
          await messageStore.fetchMessages()
        },
      })

      // Load initial data (remove legacy /api/v1/agents call)
      await Promise.all([messageStore.fetchMessages()])
    } catch (error) {
      console.error('[DefaultLayout] Failed to initialize WebSocket:', error)
    }
  }
})

onUnmounted(async () => {
  wsStore.disconnect()
  window.removeEventListener('resize', onResize)
  // SAAS-023: stop polling when leaving the authenticated layout.
  try {
    const storeLoaders = import.meta.glob('@/saas/stores/useAccountStateStore.js')
    const [loader] = Object.values(storeLoaders)
    if (loader) {
      const mod = await loader()
      mod.useAccountStateStore().stopPolling()
    }
  } catch {
    // CE bundle has no store module — silent skip.
  }
})

// Reload user after login (navigation from /login)
router.afterEach(async (to, from) => {
  if (to.meta.layout === 'default' && from.path === '/login') {
    await loadCurrentUser()
  }
})
</script>

<style scoped>
/* Mobile: add top padding to clear the hamburger FAB */
@media (max-width: 1024px) {
  :deep(.v-main) {
    padding-top: 48px !important;
  }
}
</style>
