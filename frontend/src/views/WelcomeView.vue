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

const fullGreeting = computed(() => {
  const name = firstName.value
  const hour = new Date().getHours()

  // WITH COMMA - Direct address greetings (vocative case)
  const withComma = {
    morning: [
      'Good morning, {name}!',
      'Morning, {name}!',
      'Rise and shine, {name}!',
      'Top of the morning, {name}!',
      'Wakey wakey, {name}!',
    ],
    afternoon: [
      'Good afternoon, {name}!',
      'Hello there, {name}!',
      'Hey there, {name}!',
      'Howdy, {name}!',
      'Greetings, {name}!',
    ],
    evening: [
      'Good evening, {name}!',
      'Evening, {name}!',
      'Hey there, {name}!',
      'Salutations, {name}!',
    ],
    general: [
      'Welcome back, {name}!',
      'Hey, {name}!',
      'Howdy, {name}!',
      'Ahoy, {name}!',
      'Yo, {name}!',
      'Greetings, {name}!',
    ],
  }

  // WITHOUT COMMA - Name flows naturally into phrase
  const withoutComma = {
    morning: [
      'Ready to conquer the day {name}?',
      'Time to shine {name}!',
      'Another beautiful morning awaits {name}!',
    ],
    afternoon: [
      'Great to see you {name}!',
      'Nice to have you back {name}!',
      'Good to see you {name}!',
    ],
    evening: [
      'Great to see you {name}!',
      'Nice to see you {name}!',
      'Glad you stopped by {name}!',
    ],
    general: [
      'Great to see you {name}!',
      'Good to have you back {name}!',
      'Look who showed up... {name}!',
      'There you are {name}!',
    ],
  }

  // FUN CASUAL - Energetic oddball greetings
  const funCasual = [
    "Let's get crackalackin' {name}!",
    "Let's do this {name}!",
    "Ready to rock {name}?",
    "Let's roll {name}!",
    "Game on {name}!",
    "Let's crush it {name}!",
    "Time to make magic {name}!",
    "Adventure awaits {name}!",
    "Buckle up {name}!",
    "Let's build something awesome {name}!",
    "Ready to rumble {name}?",
    "Let's make it happen {name}!",
    "Fire it up {name}!",
    "Here we go {name}!",
    "Showtime {name}!",
  ]

  function choose(arr) {
    return arr[Math.floor(Math.random() * arr.length)]
  }

  // Determine time-based category
  const timeKey = hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : hour < 22 ? 'evening' : 'general'

  // Build pool: 40% with comma, 30% without comma, 30% fun casual
  const pool = [
    ...withComma[timeKey],
    ...withComma[timeKey],  // Double weight for time-appropriate
    ...withoutComma[timeKey],
    ...funCasual,
  ]

  const msg = choose(pool)
  return msg.replace('{name}', name)
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
