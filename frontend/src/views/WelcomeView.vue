<template>
  <div class="welcome-wrapper">
    <div class="welcome-atmosphere"></div>
    <div class="welcome-page">

      <!-- HERO -->
      <div class="hero">
        <div class="hero-mascot">
          <div class="hero-mascot-glow"></div>
          <div class="hero-mascot-inner">
            <GilMascot :size="88" :dark-eyes="false" />
          </div>
        </div>
        <h1 class="hero-greeting">{{ fullGreeting }}</h1>
        <p class="hero-subtitle">
          The context engineering platform for AI-assisted development.<br>
          <span class="hero-subtitle-dim">Define your product once — every agent starts with the full picture.</span>
        </p>
      </div>

      <!-- QUICK LAUNCH -->
      <div class="section-label">Quick Launch</div>
      <div class="quick-grid">
        <div
          v-for="(card, i) in quickCards"
          :key="card.title"
          class="quick-card smooth-border"
          :style="{ '--card-accent': card.accent, animationDelay: (0.15 + i * 0.07) + 's' }"
          @click="card.action ? card.action() : $router.push(card.to)"
        >
          <div
            class="quick-card-icon"
            :style="{ background: card.iconBg, color: card.iconColor }"
          >
            <v-icon size="20">{{ card.icon }}</v-icon>
          </div>
          <div class="quick-card-title">{{ card.title }}</div>
          <div class="quick-card-desc">{{ card.description }}</div>
          <span v-if="card.badge" class="quick-card-badge">{{ card.badge }}</span>
        </div>
      </div>

      <!-- YOUR TEAM -->
      <div class="team-section">
        <div class="team-header">
          <div class="section-label mb-0">Your Team</div>
          <div class="d-flex align-center ga-2">
            <span class="team-slots smooth-border">{{ activeTemplates.length + 1 }} / {{ totalSlots }} slots</span>
            <router-link to="/settings?tab=agents" class="team-manage">
              <v-icon size="14">mdi-cog</v-icon> Manage
            </router-link>
          </div>
        </div>
        <div class="team-grid">
          <!-- Orchestrator: system agent, always present -->
          <div class="team-card smooth-border">
            <div class="team-avatar-wrap">
              <div
                class="team-avatar"
                :style="{
                  background: hexToRgba(getAgentColor('orchestrator').hex, 0.15),
                  color: getAgentColor('orchestrator').hex,
                }"
              >
                OR
              </div>
            </div>
            <div class="team-name">orchestrator</div>
            <div class="team-desc">Primary coordinator and mission planner</div>
          </div>
          <div
            v-for="tmpl in activeTemplates"
            :key="tmpl.id"
            class="team-card smooth-border"
          >
            <div class="team-avatar-wrap">
              <div
                class="team-avatar"
                :style="{
                  background: tintedBg(tmpl.color),
                  color: tmpl.color,
                }"
              >
                {{ tmpl.badge }}
              </div>
            </div>
            <div class="team-name">{{ tmpl.name }}</div>
            <div class="team-desc">{{ tmpl.description }}</div>
          </div>
          <div
            v-for="n in emptySlots"
            :key="'empty-' + n"
            class="team-card empty-slot"
          >
            <div class="team-avatar-wrap">
              <div class="team-avatar empty-avatar">
                <v-icon size="16">mdi-plus</v-icon>
              </div>
            </div>
            <div class="team-name" style="color:var(--text-muted);">Empty Slot</div>
            <div class="team-desc">Add an agent</div>
          </div>
        </div>
      </div>

      <!-- CONDITIONAL SECTION: Setup or Recent Projects -->
      <div v-if="!setupComplete" class="setup-cta-section">
        <div class="setup-cta smooth-border" @click="openSetupWithCertGate">
          <v-icon size="24" style="color: var(--color-accent-primary)">mdi-rocket-launch</v-icon>
          <div class="setup-cta-text">
            <div class="setup-cta-title">{{ setupCtaLabel }}</div>
            <div class="setup-cta-desc">Configure AI tools, connect integrations, and learn the basics.</div>
          </div>
          <v-icon size="18" style="color:var(--text-muted);">mdi-chevron-right</v-icon>
        </div>
      </div>
      <div v-else-if="recentProjects.length > 0" class="recent-projects-section">
        <div class="recent-projects-panel smooth-border">
          <div class="rp-header">
            <span class="rp-title">Recent Projects</span>
            <router-link to="/Projects" class="rp-link">All Projects →</router-link>
          </div>
          <RecentProjectsList
            :projects="recentProjects"
            @review-project="handleReviewProject"
          />
        </div>
      </div>

      <!-- FOOTER -->
      <div class="page-footer">
        <span class="footer-item mono">{{ appVersion }}</span>
      </div>
    </div>

    <!-- Certificate trust modal (shown before setup for remote HTTPS clients) -->
    <CertTrustModal
      v-model="showCertModal"
      @continue="handleCertContinue"
    />

    <!-- Setup wizard overlay -->
    <SetupWizardOverlay
      v-model="showSetupOverlay"
      :current-step="setupStep"
      :selected-tools="setupSelectedTools"
      :setup-step-completed="setupStepCompleted"
      :is-rerun="forceSetupMode"
      :mode="setupOverlayMode"
      @update:current-step="setupStep = $event"
      @step-complete="handleStepComplete"
      @dismiss="handleDismiss"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useProductStore } from '@/stores/products'
import { useProjectStore } from '@/stores/projects'
import { getAgentColor } from '@/config/agentColors'
import { hexToRgba } from '@/utils/colorUtils'
import api from '@/services/api'
import GilMascot from '@/components/GilMascot.vue'
import SetupWizardOverlay from '@/components/setup/SetupWizardOverlay.vue'
import CertTrustModal from '@/components/setup/CertTrustModal.vue'
import RecentProjectsList from '@/components/dashboard/RecentProjectsList.vue'
import configService from '@/services/configService'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const productStore = useProductStore()
const projectStore = useProjectStore()

// Certificate trust modal state
const showCertModal = ref(false)
const certModalDismissed = ref(false)
const pendingSetupOpen = ref(false)

// Setup wizard state
const showSetupOverlay = ref(false)
const setupStep = ref(0)
const forceSetupMode = ref(false)

const setupComplete = computed(() => userStore.currentUser?.setup_complete ?? false)
const learningComplete = computed(() => userStore.currentUser?.learning_complete ?? false)
const setupOverlayMode = computed(() => {
  if (forceSetupMode.value) return 'setup'
  return setupComplete.value ? 'learning' : 'setup'
})
const setupStepCompleted = computed(() => userStore.currentUser?.setup_step_completed ?? 0)
const setupSelectedTools = computed(() => userStore.currentUser?.setup_selected_tools ?? [])

const setupCtaLabel = computed(() => {
  if (setupStepCompleted.value > 0) return 'Resume Setup'
  return 'Getting Started'
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

    // After first-time setup, show the "How to Use" guide automatically
    if (!forceSetupMode.value) {
      setTimeout(() => {
        showSetupOverlay.value = true
      }, 400)
    } else if (data.route) {
      router.push(data.route)
    }
  }
}

async function handleDismiss() {
  const wasFirstTimeFinish = setupStep.value >= 3 && !setupComplete.value && !forceSetupMode.value
  const wasLearningMode = setupOverlayMode.value === 'learning'
  showSetupOverlay.value = false
  forceSetupMode.value = false

  // Mark learning guide as seen
  if (wasLearningMode && !learningComplete.value) {
    await userStore.updateSetupState({ learning_complete: true })
  }

  // If the user reached the final step and dismisses, mark setup as complete
  // so the wizard doesn't reopen on every login
  if (wasFirstTimeFinish || (setupStep.value >= 3 && !setupComplete.value)) {
    await userStore.updateSetupState({
      setup_complete: true,
      setup_step_completed: 4,
    })

    // After first-time setup, show the "How to Use" guide
    if (wasFirstTimeFinish) {
      setTimeout(() => {
        showSetupOverlay.value = true
      }, 600)
    }
  }
}

function handleCertContinue() {
  certModalDismissed.value = true
  sessionStorage.setItem('cert_modal_dismissed', '1')
  if (pendingSetupOpen.value) {
    pendingSetupOpen.value = false
    showSetupOverlay.value = true
  }
}

function openSetupWithCertGate() {
  if (shouldShowCertModal()) {
    pendingSetupOpen.value = true
    showCertModal.value = true
  } else {
    showSetupOverlay.value = true
  }
}

function shouldShowCertModal() {
  if (sessionStorage.getItem('cert_modal_dismissed') === '1') return false
  if (certModalDismissed.value) return false
  const config = configService.getRawConfig()
  if (!config) return false
  return config.api?.ssl_enabled === true && config.api?.is_remote_client === true
}

// Template data
const templates = ref([])
const totalSlots = ref(8)

const activeTemplates = computed(() =>
  templates.value
    .filter(t => t.is_active)
    .map(t => {
      const color = getAgentColor(t.agent_type || t.name)
      return {
        id: t.id,
        name: t.display_name || t.name,
        description: t.short_description || color.description,
        badge: color.badge,
        color: color.hex,
      }
    })
)

const emptySlots = computed(() => Math.max(0, totalSlots.value - activeTemplates.value.length - 1))

function tintedBg(hex) {
  return hexToRgba(hex, 0.15)
}

// Quick-launch cards — adapt to product state
const hasActiveProduct = computed(() => !!productStore.activeProduct)
const activeProjectCount = computed(() => projectStore.activeProjects?.length ?? 0)

// Card accent colors — traced to agentColors.js / design-tokens.scss
const BRAND_YELLOW = '#ffc300' // $color-brand-yellow / var(--color-accent-primary)
const COLOR_DOCUMENTER = getAgentColor('documenter').hex
const COLOR_IMPLEMENTER = getAgentColor('implementer').hex
const COLOR_REVIEWER = getAgentColor('reviewer').hex

// Onboarding-aware quick launch card definitions
const setupCard = {
  title: 'Quick Setup',
  description: 'Connect your AI coding tools and configure GiljoAI MCP.',
  icon: 'mdi-rocket-launch',
  iconBg: hexToRgba(BRAND_YELLOW, 0.1),
  iconColor: 'var(--color-accent-primary)',
  accent: 'var(--color-accent-primary)',
  action: openSetupWithCertGate,
}

const learnCard = {
  title: 'Learn',
  description: 'Understand products, projects, agents, and slash commands.',
  icon: 'mdi-book-open-variant',
  iconBg: hexToRgba(COLOR_DOCUMENTER, 0.12),
  iconColor: COLOR_DOCUMENTER,
  accent: COLOR_DOCUMENTER,
  action: () => { showSetupOverlay.value = true },
}

const quickCards = computed(() => {
  // Active product: context-aware cards
  if (hasActiveProduct.value) {
    const productName = productStore.activeProduct?.name || 'your product'
    const cards = []

    // Prepend onboarding cards as needed (replace default slots)
    if (!setupComplete.value) {
      cards.push(setupCard, learnCard)
    } else if (!learningComplete.value) {
      cards.push(learnCard)
    }

    // Fill remaining slots with product-aware defaults
    if (cards.length < 3) {
      cards.push({
        title: 'New Project',
        description: `Launch an orchestrated project with AI agents for ${productName}.`,
        icon: 'mdi-plus-circle-outline',
        iconBg: hexToRgba(BRAND_YELLOW, 0.1),
        iconColor: 'var(--color-accent-primary)',
        accent: 'var(--color-accent-primary)',
        badge: '/gil_add project',
        to: '/Projects',
      })
    }
    if (cards.length < 3) {
      if (activeProjectCount.value > 0) {
        cards.push({
          title: 'Active Projects',
          description: 'Monitor running orchestrations, agent status, and real-time progress.',
          icon: 'mdi-play-circle-outline',
          iconBg: hexToRgba(COLOR_IMPLEMENTER, 0.12),
          iconColor: COLOR_IMPLEMENTER,
          accent: COLOR_IMPLEMENTER,
          badge: `${activeProjectCount.value} active`,
          to: '/launch?via=jobs',
        })
      } else {
        cards.push({
          title: 'New Product',
          description: 'Define another product to give your AI agents full context.',
          icon: 'mdi-package-variant-closed',
          iconBg: hexToRgba(COLOR_DOCUMENTER, 0.12),
          iconColor: COLOR_DOCUMENTER,
          accent: COLOR_DOCUMENTER,
          to: '/Products',
        })
      }
    }
    if (cards.length < 3) {
      cards.push({
        title: 'Task Board',
        description: 'Track technical debt, scope creep captures, and fine-grained tasks.',
        icon: 'mdi-clipboard-check-outline',
        iconBg: hexToRgba(COLOR_REVIEWER, 0.12),
        iconColor: COLOR_REVIEWER,
        accent: COLOR_REVIEWER,
        to: '/Tasks',
      })
    }
    return cards
  }

  // No active product: onboarding + defaults
  const cards = []

  if (!setupComplete.value) {
    cards.push(setupCard, learnCard)
  } else if (!learningComplete.value) {
    cards.push(learnCard)
  }

  if (cards.length < 3) {
    cards.push({
      title: 'New Product',
      description: 'Define a product to give your AI agents full context about what they\'re building.',
      icon: 'mdi-package-variant-closed',
      iconBg: cards.length === 0 ? hexToRgba(BRAND_YELLOW, 0.1) : hexToRgba(COLOR_DOCUMENTER, 0.12),
      iconColor: cards.length === 0 ? 'var(--color-accent-primary)' : COLOR_DOCUMENTER,
      accent: cards.length === 0 ? 'var(--color-accent-primary)' : COLOR_DOCUMENTER,
      to: '/Products',
    })
  }
  if (cards.length < 3) {
    cards.push({
      title: 'Dashboard',
      description: 'View system stats, recent activity, and orchestration metrics at a glance.',
      icon: 'mdi-view-dashboard-outline',
      iconBg: hexToRgba(COLOR_IMPLEMENTER, 0.12),
      iconColor: COLOR_IMPLEMENTER,
      accent: COLOR_IMPLEMENTER,
      to: '/Dashboard',
    })
  }
  if (cards.length < 3) {
    cards.push({
      title: 'Task Board',
      description: 'Track technical debt, scope creep captures, and fine-grained tasks.',
      icon: 'mdi-clipboard-check-outline',
      iconBg: hexToRgba(COLOR_REVIEWER, 0.12),
      iconColor: COLOR_REVIEWER,
      accent: COLOR_REVIEWER,
      to: '/Tasks',
    })
  }
  return cards
})

// Recent projects (from dashboard API)
const recentProjects = ref([])

function handleReviewProject(project) {
  router.push(`/Projects/${project.id}`)
}

// Version
const appVersion = ref('')

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
  } catch { /* ignore */ }

  try {
    await projectStore.fetchProjects()
  } catch { /* ignore */ }

  // Fetch templates
  try {
    const response = await api.templates.list()
    templates.value = response.data || []
  } catch { /* ignore */ }

  // Fetch active count for total slots
  try {
    const response = await api.templates.activeCount()
    if (response.data?.max_slots) {
      totalSlots.value = response.data.max_slots
    }
  } catch { /* ignore */ }

  // Fetch recent projects for the bottom section
  if (setupComplete.value && productStore.effectiveProductId) {
    try {
      const response = await api.stats.getDashboard(productStore.effectiveProductId)
      recentProjects.value = response.data?.recent_projects || []
    } catch { /* ignore */ }
  }

  // Get version from meta or package
  try {
    const response = await api.stats.getSystem()
    appVersion.value = response.data?.version || ''
  } catch {
    appVersion.value = ''
  }

  // Ensure frontend config is loaded before cert modal check (needs ssl_enabled + is_remote_client)
  try {
    await configService.fetchConfig()
  } catch { /* config may fail on first load — cert modal just won't show */ }

  // Open "How to Use" guide when directed from UserSettings
  if (route.query.openGuide === 'true') {
    showSetupOverlay.value = true
    router.replace({ path: '/', query: {} })
  // Auto-launch overlay on first login or when directed from UserSettings
  } else if (route.query.openSetup === 'true' || !setupComplete.value) {
    forceSetupMode.value = route.query.openSetup === 'true'
    setupStep.value = Math.min(setupStepCompleted.value, 3)

    // Gate: show cert modal first for remote HTTPS clients, then open setup after
    if (shouldShowCertModal()) {
      pendingSetupOpen.value = true
      showCertModal.value = true
    } else {
      showSetupOverlay.value = true
    }

    // Clean up query param so refresh doesn't re-trigger
    if (route.query.openSetup) {
      router.replace({ path: '/', query: {} })
    }
  }
})
</script>

<style lang="scss" scoped>
@use '../styles/design-tokens' as *;
.welcome-wrapper {
  position: relative;
  min-height: 100%;
}

.welcome-atmosphere {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(ellipse 700px 500px at 50% 15%, rgba(255,195,0,0.04) 0%, transparent 60%),
    radial-gradient(ellipse 500px 500px at 80% 60%, rgba(109,179,228,0.03) 0%, transparent 60%);
}

.welcome-page {
  position: relative;
  z-index: 1;
  max-width: 960px;
  margin: 0 auto;
  padding: 40px 32px 48px;
}

/* ═══ HERO ═══ */
.hero {
  text-align: center;
  margin-bottom: 36px;
  animation: fadeSlideDown 0.6s ease-out;
}

.hero-mascot {
  position: relative;
  display: inline-block;
  width: 88px;
  height: 100px;
  margin-bottom: 20px;
}

.hero-mascot-inner {
  position: relative;
  z-index: 1;
  filter: drop-shadow(0 0 14px rgba(255,195,0,0.35)) drop-shadow(0 0 36px rgba(107,207,127,0.15));
  animation: mascotFloat 4s ease-in-out infinite;
}

.hero-mascot-glow {
  position: absolute;
  inset: -20px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,217,61,0.14) 0%, rgba(107,207,127,0.06) 50%, transparent 70%);
  z-index: 0;
  animation: glowPulse 4s ease-in-out infinite;
}

.hero-greeting {
  font-size: 1.65rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 6px;
  color: var(--color-text-primary);
}

.hero-subtitle {
  font-size: 0.88rem;
  color: var(--text-secondary);
  font-weight: 300;
  max-width: 480px;
  margin: 0 auto;
  line-height: 1.55;
}

.hero-subtitle-dim {
  opacity: 0.7;
}

/* ═══ SECTION LABEL ═══ */
.section-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 12px;
  font-weight: 500;
}

/* ═══ QUICK LAUNCH ═══ */
.quick-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 36px;
}

.quick-card {
  background: rgb(var(--v-theme-surface));
  border-radius: $border-radius-rounded;
  padding: 20px;
  cursor: pointer;
  transition: all $transition-normal;
  position: relative;
  overflow: hidden;
  animation: fadeSlideUp 0.45s ease-out both;
}

.quick-card:hover {
  transform: translateY(-3px);
  box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255,255,255,0.10)), 0 10px 20px -6px rgba(0,0,0,0.25);
}

.quick-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--card-accent, rgba(255,255,255,0.10));
  opacity: 0;
  transition: opacity $transition-normal;
}

.quick-card:hover::before {
  opacity: 1;
}

.quick-card-icon {
  width: 40px;
  height: 40px;
  border-radius: $border-radius-default;
  display: grid;
  place-items: center;
  margin-bottom: 12px;
}

.quick-card-title {
  font-size: 0.92rem;
  font-weight: 600;
  margin-bottom: 5px;
}

.quick-card-desc {
  font-size: 0.75rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.quick-card-badge {
  display: inline-block;
  margin-top: 10px;
  padding: 2px 8px;
  background: rgba(255,255,255,0.05);
  border-radius: $border-radius-sharp;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.6rem;
  color: var(--text-muted);
}

/* ═══ YOUR TEAM ═══ */
.team-section {
  margin-bottom: 36px;
  animation: fadeSlideUp 0.45s ease-out 0.35s both;
}

.team-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.team-slots {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  color: var(--text-muted);
  padding: 2px 8px;
  border-radius: $border-radius-pill;
}

.team-manage {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.7rem;
  color: $color-brand-yellow;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity $transition-normal;
  text-decoration: none;
}

.team-manage:hover {
  opacity: 1;
}

.team-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.team-card {
  background: rgb(var(--v-theme-surface));
  border-radius: $border-radius-rounded;
  padding: 16px 14px 20px;
  cursor: pointer;
  transition: all $transition-normal;
  text-align: center;
}

.team-card:hover {
  transform: translateY(-2px);
  box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255,255,255,0.10)), 0 6px 16px -4px rgba(0,0,0,0.25);
}

.team-avatar-wrap {
  width: 44px;
  margin: 0 auto 8px;
}

.team-avatar {
  width: 44px;
  height: 44px;
  border-radius: $border-radius-md;
  display: grid;
  place-items: center;
  font-size: 0.78rem;
  font-weight: 700;
  transition: box-shadow $transition-normal;
}

.empty-avatar {
  background: rgba(255,255,255,0.05);
  color: var(--text-muted);
}

.team-name {
  font-size: 0.75rem;
  font-weight: 500;
  margin-bottom: 2px;
}

.team-desc {
  font-size: 0.62rem;
  color: var(--text-muted);
  line-height: 1.3;
}

.team-card.empty-slot {
  border: 1px dashed rgba(255,255,255,0.1);
  box-shadow: none;
  background: transparent;
  opacity: 0.4;
}

.team-card.empty-slot:hover {
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

/* ═══ SETUP CTA ═══ */
.setup-cta-section {
  margin-bottom: 36px;
  animation: fadeSlideUp 0.45s ease-out 0.42s both;
}

.setup-cta {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  background: rgb(var(--v-theme-surface));
  border-radius: $border-radius-rounded;
  cursor: pointer;
  transition: all $transition-normal;
}

.setup-cta:hover {
  transform: translateY(-2px);
  box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255,255,255,0.10)), 0 6px 16px -4px rgba(0,0,0,0.25);
}

.setup-cta-text {
  flex: 1;
}

.setup-cta-title {
  font-size: 0.92rem;
  font-weight: 600;
  margin-bottom: 2px;
}

.setup-cta-desc {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

/* ═══ RECENT PROJECTS ═══ */
.recent-projects-section {
  margin-bottom: 36px;
  animation: fadeSlideUp 0.45s ease-out 0.42s both;
}

.recent-projects-panel {
  background: rgb(var(--v-theme-surface));
  border-radius: $border-radius-rounded;
  overflow: hidden;
}

.rp-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.rp-title {
  font-size: 0.92rem;
  font-weight: 600;
}

.rp-link {
  font-size: 0.68rem;
  color: $color-brand-yellow;
  cursor: pointer;
  font-weight: 500;
  opacity: 0.7;
  text-decoration: none;
}

.rp-link:hover {
  opacity: 1;
}

/* ═══ FOOTER ═══ */
.page-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding-top: 20px;
  border-top: 1px solid rgba(255,255,255,0.04);
  animation: fadeSlideUp 0.45s ease-out 0.55s both;
}

.footer-item {
  font-size: 0.68rem;
  color: var(--text-muted);
}

.footer-item.mono {
  font-family: 'IBM Plex Mono', monospace;
}

.footer-dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--text-muted);
  opacity: 0.5;
}

/* ═══ ANIMATIONS ═══ */
@keyframes fadeSlideDown {
  from { opacity: 0; transform: translateY(-14px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes mascotFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

@keyframes glowPulse {
  0%, 100% { opacity: 0.8; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.06); }
}

/* ═══ RESPONSIVE ═══ */
@media (max-width: 960px) {
  .welcome-page {
    padding: 32px 20px 40px;
  }
  .quick-grid {
    grid-template-columns: 1fr;
  }
  .team-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
