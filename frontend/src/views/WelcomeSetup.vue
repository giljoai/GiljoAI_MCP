<template>
  <WelcomePasswordStep />
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import setupService from '@/services/setupService'
import api from '@/services/api'
import WelcomePasswordStep from '@/components/WelcomePasswordStep.vue'

const router = useRouter()

// Route guard logic - runs when component mounts
onMounted(async () => {
  try {
    // REMOVED: Auto-login check
    // Always show welcome screen for password setup, no auto-redirect
    console.log('[WelcomeSetup] Showing welcome screen for password setup')

    // Check setup status to determine if password setup is needed
    const status = await setupService.checkStatus()

    // If default password is NOT active (already changed), redirect to login
    if (!status.default_password_active) {
      console.log('[WelcomeSetup] Password already changed, redirecting to login')
      router.push('/login')
      return
    }

    // Otherwise, show the welcome password setup screen (component handles the rest)
    console.log('[WelcomeSetup] Default password active, showing welcome setup')
  } catch (error) {
    // If setup status check fails, assume fresh install and show welcome screen
    console.log('[WelcomeSetup] Setup status check failed, assuming fresh install')
  }
})
</script>

<style scoped>
/* No additional styles needed - WelcomePasswordStep component provides its own styling */
</style>
