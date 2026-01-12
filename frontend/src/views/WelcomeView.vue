<template>
  <v-container fluid class="fill-height welcome-container">
    <v-row align="center" justify="center">
      <v-col cols="12" md="8" lg="6">
        <v-card elevation="0" class="text-center pa-8">
          <!-- Gil mascot (blinking) on top -->
          <div class="mascot-wrapper mb-4">
            <GilMascot :size="150" :dark-eyes="!theme.global.current.value.dark" />
          </div>

          <!-- Friendly greeting with user's first name -->
          <h1 class="text-h4 mb-2 font-weight-bold">
            {{ fullGreeting }}
          </h1>
          <p class="text-subtitle-1 text-medium-emphasis mb-6">
            Intelligent multi-agent coordination for complex software development
          </p>

          <!-- Contextual CTA: Get Started or Relaunch Tutorial -->
          <div class="mb-6" v-if="showTutorialCta">
            <v-btn
              color="primary"
              size="large"
              @click="handleTutorialCta"
              prepend-icon="mdi-play-circle"
            >
              {{ tutorialCtaLabel }}
            </v-btn>
          </div>

          <v-divider class="my-6"></v-divider>

          <!-- Quick navigation -->
          <v-row class="mt-2">
            <v-col cols="12" md="4">
              <v-btn
                to="/Dashboard"
                color="primary"
                size="large"
                block
                prepend-icon="mdi-view-dashboard"
              >
                Dashboard
              </v-btn>
            </v-col>
            <v-col cols="12" md="4">
              <v-btn
                to="/Products"
                color="primary"
                variant="outlined"
                size="large"
                block
                prepend-icon="mdi-package-variant"
              >
                Products
              </v-btn>
            </v-col>
            <v-col cols="12" md="4">
              <v-btn
                to="/Projects"
                color="primary"
                variant="outlined"
                size="large"
                block
                prepend-icon="mdi-folder-multiple"
              >
                Projects
              </v-btn>
            </v-col>
          </v-row>

          <v-row class="mt-3" justify="center">
            <v-col cols="12" md="8">
              <v-btn
                :to="{ name: 'UserSettings', query: { tab: 'startup' } }"
                color="secondary"
                variant="flat"
                size="large"
                block
                prepend-icon="mdi-rocket-launch"
                class="startup-cta"
              >
                Setup Quick Start
              </v-btn>
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useTheme } from 'vuetify'
import { useUserStore } from '@/stores/user'
import { useProductStore } from '@/stores/products'
import GilMascot from '@/components/GilMascot.vue'

const theme = useTheme()
const userStore = useUserStore()
const productStore = useProductStore()

// Mascot handled by inline component (no iframe to avoid background issues)

// User name and greeting
const firstName = computed(() => {
  const name = userStore.currentUser?.full_name || userStore.currentUser?.username || 'Friend'
  return String(name).split(' ')[0]
})

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)]
}

const fullGreeting = computed(() => {
  const name = firstName.value
  const hour = new Date().getHours()

  // Prefer messages with name placeholders for correct grammar
  const morning = ['Good morning, {name}!', 'Morning, {name}!', 'Rise and shine, {name}!']
  const afternoon = [
    'Good afternoon, {name}!',
    'Hello there, {name}!',
    'Hope your day’s going well, {name}!',
  ]
  const evening = ['Good evening, {name}!', 'Great to see you, {name}!', 'Nice to see you, {name}!']
  // Generic messages without punctuation; we will add ", {name}!"
  const general = [
    'Welcome back',
    'Here you are again',
    'Glad you’re here',
    'Let’s get rolling',
    'Ready when you are',
    'Let’s build something great',
    'Howdy',
    'Hi again',
    'Welcome',
    'Back in action',
    'Let’s make progress',
  ]

  function choose(arr) {
    return arr[Math.floor(Math.random() * arr.length)]
  }

  const pool = hour < 12 ? morning : hour < 17 ? afternoon : hour < 22 ? evening : general
  let msg = choose(pool)
  if (msg.includes('{name}')) {
    return msg.replace('{name}', name)
  }
  // Ensure no trailing punctuation before appending name
  msg = msg.replace(/[!?.]+$/, '')
  return `${msg}, ${name}!`
})

// Tutorial CTA logic
const tutorialKey = 'giljo_tutorial_launched'
const tutorialLaunched = ref(false)
const showTutorialCta = computed(() => {
  // Show when there are no products OR user wants to relaunch
  return !productStore.hasProducts || tutorialLaunched.value
})
const tutorialCtaLabel = computed(() =>
  tutorialLaunched.value || productStore.hasProducts ? 'Relaunch Tutorial' : 'Get Started',
)

function handleTutorialCta() {
  tutorialLaunched.value = true
  localStorage.setItem(tutorialKey, 'true')
  // Placeholder for tutorial launch hook
  // For now: take the user to Products to create their first product
  window.location.href = '/Products'
}

onMounted(async () => {
  try {
    await productStore.fetchProducts()
  } catch (e) {
    // ignore
  }
  tutorialLaunched.value = localStorage.getItem(tutorialKey) === 'true'
})
</script>

<style scoped>
.welcome-container {
  background: linear-gradient(
    135deg,
    rgba(var(--v-theme-primary), 0.05) 0%,
    rgba(var(--v-theme-surface), 1) 100%
  );
}
.mascot-wrapper {
  display: flex;
  justify-content: center;
}
.mascot-frame {
  background: transparent;
}

.startup-cta {
  color: rgb(var(--v-theme-primary)) !important;
  font-weight: 700;
}
</style>
