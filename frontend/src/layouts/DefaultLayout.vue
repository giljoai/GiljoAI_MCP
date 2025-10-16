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
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import AppBar from '@/components/navigation/AppBar.vue'
import NavigationDrawer from '@/components/navigation/NavigationDrawer.vue'
import api from '@/services/api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const drawer = ref(true)
const rail = ref(false)
const currentUser = ref(null)

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
  await loadCurrentUser()
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
