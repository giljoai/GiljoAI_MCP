<template>
  <v-container fluid class="fill-height welcome-container">
    <v-row align="center" justify="center">
      <v-col cols="12" md="8" lg="6">
        <v-card elevation="0" class="text-center pa-8">
          <!-- Gil mascot (blinking) on top -->
          <div class="mascot-wrapper mb-4">
            <GilMascot :size="150" :dark-eyes="false" />
          </div>

          <!-- Friendly greeting with user's first name -->
          <h1 class="text-h4 mb-2 font-weight-bold">
            {{ fullGreeting }}
          </h1>
          <p class="text-subtitle-1 text-medium-emphasis mb-6">
            Intelligent multi-agent coordination for complex software development
          </p>

          <!-- Setup wizard CTA -->
          <div class="mb-6">
            <v-btn
              v-if="!setupComplete"
              color="primary"
              size="large"
              prepend-icon="mdi-rocket-launch"
              @click="showSetupOverlay = true"
            >
              {{ setupCtaLabel }}
            </v-btn>
            <v-btn
              v-else
              color="primary"
              variant="outlined"
              size="large"
              prepend-icon="mdi-book-open-variant"
              @click="showSetupOverlay = true"
            >
              How to Use GiljoAI MCP
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
        </v-card>
      </v-col>
    </v-row>

    <!-- Setup wizard overlay -->
    <SetupWizardOverlay
      v-model="showSetupOverlay"
      :current-step="setupStep"
      :selected-tools="setupSelectedTools"
      :mode="setupComplete ? 'learning' : 'setup'"
      @update:current-step="setupStep = $event"
      @step-complete="handleStepComplete"
      @dismiss="handleDismiss"
    />
  </v-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useProductStore } from '@/stores/products'
import GilMascot from '@/components/GilMascot.vue'
import SetupWizardOverlay from '@/components/setup/SetupWizardOverlay.vue'

const router = useRouter()
const userStore = useUserStore()
const productStore = useProductStore()

// Setup wizard state
const showSetupOverlay = ref(false)
const setupStep = ref(0)

const setupComplete = computed(() => userStore.currentUser?.setup_complete ?? false)
const setupStepCompleted = computed(() => userStore.currentUser?.setup_step_completed ?? 0)
const setupSelectedTools = computed(() => userStore.currentUser?.setup_selected_tools ?? [])

const setupCtaLabel = computed(() => {
  if (setupStepCompleted.value > 0) return 'Resume Setup'
  return 'Begin Setup'
})

async function handleStepComplete({ step, data }) {
  if (step === 0 && data.tools) {
    await userStore.updateSetupState({
      setup_selected_tools: data.tools,
      setup_step_completed: 1,
    })
  } else if (step === 1) {
    await userStore.updateSetupState({
      setup_step_completed: 2,
    })
  } else if (step === 2) {
    await userStore.updateSetupState({
      setup_step_completed: 3,
    })
  } else if (step === 3 && data.setup_complete) {
    await userStore.updateSetupState({
      setup_complete: true,
      setup_step_completed: 4,
    })
    showSetupOverlay.value = false
    if (data.route) {
      router.push(data.route)
    }
  }
}

function handleDismiss() {
  showSetupOverlay.value = false
}

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

onMounted(async () => {
  try {
    await productStore.fetchProducts()
  } catch {
    // ignore
  }

  // Auto-launch overlay on first login (setup not complete)
  if (!setupComplete.value) {
    setupStep.value = setupStepCompleted.value
    showSetupOverlay.value = true
  }
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
</style>
