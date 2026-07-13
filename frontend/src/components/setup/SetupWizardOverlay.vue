<template>
  <Teleport to="body">
    <Transition name="overlay-fade">
      <div
        v-if="modelValue"
        class="setup-wizard-overlay"
        data-testid="setup-wizard-overlay"
        role="dialog"
        aria-modal="true"
        aria-label="Setup GiljoAI MCP"
        @keydown.escape="handleDismiss"
      >
        <!-- Backdrop — click does NOT close -->
        <div class="setup-wizard-backdrop" />

        <!-- ============================================================
             LEARNING MODE — read-only reference guide.
             PRESERVED VERBATIM (single-column panel, unchanged from pre-6259b).
             ============================================================ -->
        <div v-if="mode === 'learning'" class="setup-wizard-panel smooth-border" tabindex="-1">
          <div class="setup-wizard-header">
            <h2 class="setup-wizard-title">
              <span class="setup-wizard-title-gradient">How to Use GiljoAI MCP</span>
            </h2>
            <v-btn
              icon
              variant="text"
              size="small"
              class="setup-wizard-close-btn"
              aria-label="Close guide"
              @click="handleDismiss"
            >
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </div>

          <div class="setup-wizard-content">
            <div class="learning-content">
              <div
                v-for="section in LEARNING_SECTIONS"
                :key="section.id"
                class="learning-section smooth-border"
              >
                <button
                  class="learning-section-header"
                  :aria-expanded="expandedSections[section.id]"
                  :aria-controls="`learning-${section.id}`"
                  @click="toggleSection(section.id)"
                >
                  <v-icon size="20" class="section-icon" :style="{ color: expandedSections[section.id] ? 'var(--color-accent-primary)' : 'var(--color-text-secondary)' }">
                    {{ section.icon }}
                  </v-icon>
                  <span class="section-title">{{ section.title }}</span>
                  <v-icon size="18" :class="['section-chevron', { 'section-chevron--open': expandedSections[section.id] }]">
                    mdi-chevron-down
                  </v-icon>
                </button>
                <Transition name="section-expand">
                  <div
                    v-if="expandedSections[section.id]"
                    :id="`learning-${section.id}`"
                    class="learning-section-body"
                  >
                    <p v-for="(line, i) in section.content" :key="i" class="learning-line">
                      {{ line }}
                    </p>
                  </div>
                </Transition>
              </div>
              <p class="learning-closing">You can reopen this guide any time from User Settings.</p>
            </div>
          </div>

          <div class="setup-wizard-footer setup-wizard-footer--learning">
            <v-spacer />
            <v-btn
              color="primary"
              variant="flat"
              class="footer-btn-gotit"
              @click="handleDismiss"
            >
              Got it
            </v-btn>
          </div>
        </div>

        <!-- ============================================================
             SETUP MODE — Gradient Rail (FE-6259b).
             Left: vertical gradient stepper. Right: step content + footer.
             ============================================================ -->
        <div v-else class="wizard-rail-panel smooth-border" tabindex="-1">
          <v-btn
            icon
            variant="text"
            size="small"
            class="wizard-rail-close-btn"
            aria-label="Close setup wizard"
            @click="handleDismiss"
          >
            <v-icon>mdi-close</v-icon>
          </v-btn>

          <!-- Closing state: all checkmarks, brief confirmation (replaces the whole body) -->
          <div v-if="closingWithCheckmarks" class="closing-confirmation">
            <v-icon size="48" color="success" class="closing-icon">mdi-check-circle</v-icon>
            <div class="closing-text">Setup complete</div>
          </div>

          <template v-else>
            <!-- Left rail: gradient stepper -->
            <aside class="wizard-rail">
              <div class="rail-top">
                <img src="/icons/Giljo_YW_Face.svg" alt="" class="rail-logo" />
                <div>
                  <div class="rail-title">Set up GiljoAI</div>
                  <div class="rail-count">Step {{ Math.min(currentStep, 3) + 1 }} of 4</div>
                </div>
              </div>

              <div class="stepper">
                <div class="spine">
                  <div class="spine-fill" :style="{ height: spineFillPct + '%' }" />
                </div>
                <div
                  v-for="(step, i) in STEPS"
                  :key="step.id"
                  :style="{ '--nodecol': STEP_COLORS[i] }"
                  :class="[
                    'rail-node',
                    {
                      'rail-node--done': i < currentStep,
                      'rail-node--active': i === currentStep,
                      'rail-node--clickable': i < currentStep,
                    },
                  ]"
                  :data-testid="`rail-node-${step.id}`"
                  role="button"
                  :tabindex="i < currentStep ? 0 : -1"
                  :aria-current="i === currentStep ? 'step' : undefined"
                  @click="goToStep(i)"
                  @keydown.enter.prevent="goToStep(i)"
                  @keydown.space.prevent="goToStep(i)"
                >
                  <span class="rail-dot">
                    <v-icon v-if="i < currentStep" size="13">mdi-check</v-icon>
                    <template v-else>{{ i + 1 }}</template>
                  </span>
                  <span class="rail-txt">
                    <span class="rail-node-label">{{ step.label }}</span>
                    <span class="rail-node-desc">{{ STEP_DESC[i] }}</span>
                  </span>
                </div>
              </div>
            </aside>

            <!-- Right: step content + footer -->
            <main class="wizard-main">
              <div class="wizard-content" data-testid="wizard-content">
                <!-- Step 0: Choose Tools -->
                <div v-if="currentStep === 0" class="step-tools">
                  <p class="step-heading-grad">Choose your tools</p>
                  <p class="step-sub">
                    Which AI coding agent(s) do you use? Pick one or more. You can add the rest later.
                  </p>

                  <div class="wiz-center">
                    <div class="tools-grid">
                      <div
                        v-for="tool in TOOLS"
                        :key="tool.id"
                        :class="['tool-card', 'smooth-border', { 'tool-card--sel': isSelected(tool.id) }]"
                        :data-testid="`tool-select-${tool.id}`"
                        role="checkbox"
                        :aria-checked="isSelected(tool.id)"
                        :aria-label="tool.name"
                        tabindex="0"
                        @click="toggleTool(tool.id)"
                        @keydown.enter.prevent="toggleTool(tool.id)"
                        @keydown.space.prevent="toggleTool(tool.id)"
                      >
                        <span v-if="isSelected(tool.id)" class="tool-card-tick"><v-icon size="12">mdi-check</v-icon></span>
                        <img :src="tool.logo" :alt="tool.name" class="tool-card-logo" />
                        <span class="tool-name">{{ tool.name }}</span>
                        <span class="tool-provider">{{ tool.provider }}</span>
                      </div>
                    </div>
                    <p class="step-fineprint">
                      Generic MCP connectivity can be configured later in Settings &gt; Tools &gt; Connect.
                    </p>
                  </div>
                </div>

                <!-- Step 1: Connect (0855d) -->
                <SetupStep2Connect
                  v-else-if="currentStep === 1"
                  :selected-tools="localSelectedTools"
                  @can-proceed="step2CanProceed = $event"
                  @step-data="step2Data = $event"
                />

                <!-- Step 2: Install (0855e) -->
                <SetupStep3Commands
                  v-else-if="currentStep === 2"
                  :selected-tools="localSelectedTools"
                  :connected-tools="step2ConnectedTools"
                  :previously-completed="props.setupStepCompleted >= 3"
                  @can-proceed="step3CanProceed = $event"
                  @step-data="step3Data = $event"
                />

                <!-- Step 3: Launch (0855f) -->
                <SetupStep4Complete v-else-if="currentStep === 3" />
              </div>

              <div class="wz-footer">
                <div class="footer-row">
                  <v-btn
                    v-if="currentStep > 0"
                    variant="text"
                    class="footer-back"
                    @click="handleBack"
                  >
                    Back
                  </v-btn>
                  <span class="footer-spacer" />

                  <template v-if="currentStep === 3">
                    <v-btn
                      v-if="props.isRerun"
                      variant="text"
                      prepend-icon="mdi-restart"
                      class="footer-restart"
                      data-testid="setup-restart-btn"
                      @click="showRestartConfirm = true"
                    >
                      Restart setup
                    </v-btn>
                    <v-btn
                      color="primary"
                      variant="flat"
                      class="footer-next-btn"
                      data-testid="setup-finish-btn"
                      @click="handleFinish"
                    >
                      {{ props.isRerun ? 'Done' : 'Finish' }}
                    </v-btn>
                  </template>
                  <template v-else>
                    <v-btn
                      color="primary"
                      variant="flat"
                      class="footer-next-btn"
                      data-testid="setup-next-btn"
                      :disabled="!canProceed"
                      @click="handleNext"
                    >
                      Next
                    </v-btn>
                  </template>
                </div>

                <div v-if="footerSkipLabel" class="footer-skip">
                  <button
                    type="button"
                    class="skiplink"
                    :data-testid="footerSkipTestId"
                    @click="handleFooterSkip"
                  >
                    {{ footerSkipLabel }}
                  </button>
                </div>
              </div>
            </main>
          </template>
        </div>
      </div>
    </Transition>

    <!-- Restart confirmation dialog -->
    <v-dialog v-model="showRestartConfirm" max-width="380">
      <v-card class="smooth-border">
        <div class="dlg-header dlg-header--warning">
          <v-icon class="dlg-icon">mdi-alert</v-icon>
          <span class="dlg-title">Restart Setup</span>
          <v-btn icon variant="text" size="small" class="dlg-close" @click="showRestartConfirm = false">
            <v-icon icon="mdi-close" size="18" />
          </v-btn>
        </div>
        <v-card-text class="pa-4">
          Setup is already completed. Are you sure you want to restart?
        </v-card-text>
        <div class="dlg-footer">
          <v-spacer />
          <v-btn variant="text" @click="showRestartConfirm = false">Cancel</v-btn>
          <v-btn variant="flat" color="warning" @click="handleRestartConfirmed">Yes</v-btn>
        </div>
      </v-card>
    </v-dialog>
  </Teleport>
</template>

<script setup>
import { ref, computed, reactive, watch } from 'vue'
import SetupStep2Connect from './SetupStep2Connect.vue'
import SetupStep3Commands from './SetupStep3Commands.vue'
import SetupStep4Complete from './SetupStep4Complete.vue'

const LEARNING_SECTIONS = [
  {
    id: 'how-it-works',
    icon: 'mdi-connection',
    title: 'How GiljoAI Works',
    content: [
      'GiljoAI MCP is a passive context server. Your AI coding tool does all reasoning and coding using your own subscription. GiljoAI stores product knowledge, generates focused prompts, and serves coordination data so your agents stay aligned.',
      'Your AI tool connects to GiljoAI as an MCP server over HTTP. Each tool gets its own API key and connection.',
      'Use Claude Code CLI, Codex CLI, Gemini CLI, or any MCP-compatible tool simultaneously. If it can connect to an MCP server, GiljoAI accepts it.',
    ],
  },
  {
    id: 'product',
    icon: 'mdi-package-variant-closed',
    title: 'Define Your Product',
    content: [
      'Create a Product to represent the software you are building. Fill in context fields: description, tech stack, architecture, testing strategy, constraints, and more.',
      'Enter context manually, or use a pre-generated prompt that lets your AI coding tool suggest what to include based on a vision document or product proposal.',
      'Context settings let you toggle fields on or off and adjust depth per source. Keep prompts lean for simple tasks or load full detail for complex missions.',
    ],
  },
  {
    id: 'projects',
    icon: 'mdi-folder-open',
    title: 'Projects and Missions',
    content: [
      'Create Projects inside a product. Each project is a focused unit of work such as a feature, sprint, or scaffolding effort. Stage a series of projects and activate one at a time.',
      'Activate a project and GiljoAI generates a bootstrap prompt. Paste it into your CLI tool to kick off the orchestrator, which plans the mission and assigns agents from your templates.',
      'Context is assembled per session from your product fields, 360 Memory, and optional integrations. Each agent gets exactly what it needs for its role.',
    ],
  },
  {
    id: 'skills',
    icon: 'mdi-slash-forward-box',
    title: 'Skills and Agent Templates',
    content: [
      'One skill is installed on your machine during setup: /giljo (Claude Code CLI, Gemini CLI) or $giljo (Codex CLI). It routes both create and read for projects and tasks.',
      'Use /giljo to capture tasks, create projects, or look up existing projects and tasks mid-session without breaking flow. To install or refresh agent templates, run the giljo_setup tool and choose "Agents only".',
      'The Agent Template Manager lets you browse, customize, and create agent profiles with roles, expertise, and chain strategies. Templates export automatically for the right platform.',
    ],
  },
  {
    id: 'memory',
    icon: 'mdi-brain',
    title: '360 Memory',
    content: [
      'Each completed project writes to 360 Memory automatically: what was built, key decisions, patterns discovered, what worked. This is not a plugin or integration. It is a core product behavior.',
      'Your next project starts with accumulated context from previous ones. The orchestrator reads past memories alongside your product context and project description to plan each mission.',
      'You control how many memories back agents read through the context settings. Optionally enrich memory with git commit history for the complete development timeline.',
    ],
  },
  {
    id: 'dashboard',
    icon: 'mdi-view-dashboard',
    title: 'Dashboard and Monitoring',
    content: [
      'The Products, Projects, Tasks, and Jobs pages let you manage your work and track technical debt across all products.',
      'The Jobs page is where staging begins and agents execute. Watch their planning, to-do lists, and messages in real time.',
      'A message inbox lets you talk directly to the orchestrator or broadcast to the entire agent team. All messages are logged in the MCP message system for auditability.',
    ],
  },
]

const TOOLS = [
  { id: 'claude_code', name: 'Claude Code CLI', provider: 'by Anthropic', logo: '/claude-color.svg' },
  { id: 'codex_cli', name: 'Codex CLI', provider: 'by OpenAI', logo: '/icons/codex_mark_white.svg' },
  { id: 'gemini_cli', name: 'Gemini CLI', provider: 'by Google', logo: '/gemini-icon.svg' },
  { id: 'antigravity_cli', name: 'Antigravity CLI', provider: 'by Antigravity', logo: '/antigravity-color.svg' },
]

const STEPS = [
  { id: 'tools', label: 'Choose Tools' },
  { id: 'connect', label: 'Connect' },
  { id: 'install', label: 'Install' },
  { id: 'launch', label: 'Launch' },
]

// Rail node descriptions (Gradient Rail pixel spec). One per STEPS entry.
const STEP_DESC = ['Pick your AI agents', 'Attach them to GiljoAI', 'Skills & agent templates', "You're ready"]

// Node colors sampled along the brand gradient (design-tokens.scss / main.scss).
const STEP_COLORS = ['var(--gradient-step-1)', 'var(--gradient-step-2)', 'var(--gradient-step-3)', 'var(--gradient-step-4)']

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  currentStep: {
    type: Number,
    default: 0,
  },
  selectedTools: {
    type: Array,
    default: () => [],
  },
  setupStepCompleted: {
    type: Number,
    default: 0,
  },
  isRerun: {
    type: Boolean,
    default: false,
  },
  mode: {
    type: String,
    default: 'setup',
  },
})

const emit = defineEmits([
  'update:modelValue',
  'update:currentStep',
  'dismiss',
  'step-complete',
])

// Learning mode: collapsible sections (first section expanded by default)
const expandedSections = reactive(
  Object.fromEntries(LEARNING_SECTIONS.map((s, i) => [s.id, i === 0])),
)

function toggleSection(sectionId) {
  expandedSections[sectionId] = !expandedSections[sectionId]
}

// Internal state
const localSelectedTools = ref([...props.selectedTools])
const step2CanProceed = ref(false)
const step2Data = ref({})
const step3CanProceed = ref(false)
const step3Data = ref({})
const showRestartConfirm = ref(false)

function handleRestartConfirmed() {
  showRestartConfirm.value = false
  localSelectedTools.value = []
  emit('update:currentStep', 0)
}

// Sync when prop changes externally
watch(
  () => props.selectedTools,
  (newVal) => {
    localSelectedTools.value = [...newVal]
  },
)

// Connected tools from Step 2 data, passed to Step 3
const step2ConnectedTools = computed(() => step2Data.value?.connectedTools || [])

// Rail: spine fill height tracks progress (0 → 100%, 3 gaps for 4 steps).
const spineFillPct = computed(() => (Math.min(props.currentStep, 3) / 3) * 100)

// Rail nodes: only completed (done) steps are clickable — mirrors the
// authoritative pixel spec (internal/design/onboarding-gradient-rail).
function goToStep(i) {
  if (i < props.currentStep) {
    emit('update:currentStep', i)
  }
}

// Footer skip control (steps 1 & 2 only). Centralized here so both steps
// share one footer element instead of each child owning its own skip link.
const footerSkipLabel = computed(() => {
  if (props.currentStep === 1) return 'Skip for now'
  if (props.currentStep === 2) return "Skip, I'll do this later"
  return ''
})

const footerSkipTestId = computed(() => {
  if (props.currentStep === 1) return 'connect-skip'
  if (props.currentStep === 2) return 'install-skip'
  return null
})

function handleFooterSkip() {
  if (props.currentStep === 1) handleStep2Skip()
  else if (props.currentStep === 2) handleStep3Skip()
}

function toggleTool(toolId) {
  const index = localSelectedTools.value.indexOf(toolId)
  if (index === -1) {
    localSelectedTools.value.push(toolId)
  } else {
    localSelectedTools.value.splice(index, 1)
  }
}

function isSelected(toolId) {
  return localSelectedTools.value.includes(toolId)
}

const canProceed = computed(() => {
  if (props.currentStep === 0) {
    return localSelectedTools.value.length > 0
  }
  if (props.currentStep === 1) {
    return step2CanProceed.value
  }
  if (props.currentStep === 2) {
    return step3CanProceed.value
  }
  // Step 3 (Launch) has its own card-based navigation
  return false
})

function handleNext() {
  if (!canProceed.value) return

  if (props.currentStep === 0) {
    emit('step-complete', { step: 0, data: { tools: [...localSelectedTools.value] } })
  } else if (props.currentStep === 1) {
    emit('step-complete', { step: 1, data: { ...step2Data.value } })
  } else if (props.currentStep === 2) {
    emit('step-complete', { step: 2, data: { ...step3Data.value } })
  } else {
    emit('step-complete', { step: props.currentStep, data: {} })
  }

  if (props.currentStep < STEPS.length - 1) {
    emit('update:currentStep', props.currentStep + 1)
  }
}

function handleBack() {
  if (props.currentStep > 0) {
    emit('update:currentStep', props.currentStep - 1)
  }
}

function handleStep2Skip() {
  // User opts out of connecting now (e.g. OAuth-incapable harness, HTTP-on-LAN,
  // or they'll wire it up later). Advance past the MCP-attach step without
  // requiring a live connection. Mirrors the Install step's skip.
  emit('step-complete', { step: 1, data: { connectedTools: [], skipped: true } })
  if (props.currentStep < STEPS.length - 1) {
    emit('update:currentStep', props.currentStep + 1)
  }
}

function handleStep3Skip() {
  emit('step-complete', { step: 2, data: { installedTools: [], skipped: true } })
  if (props.currentStep < STEPS.length - 1) {
    emit('update:currentStep', props.currentStep + 1)
  }
}

function handleFinish() {
  emit('step-complete', { step: 3, data: { action: 'home', route: '/home', setup_complete: true } })
  handleDismiss()
}

const closingWithCheckmarks = ref(false)

function handleDismiss() {
  // If setup is already done and we're on the final step, show all-complete state then auto-close
  if (props.mode === 'setup' && props.currentStep === 3 && !closingWithCheckmarks.value) {
    closingWithCheckmarks.value = true
    // Force all steps to show as completed visually
    emit('update:currentStep', 4)
    setTimeout(() => {
      closingWithCheckmarks.value = false
      emit('dismiss')
      emit('update:modelValue', false)
      // Reset back to step 3 for next open
      emit('update:currentStep', 3)
    }, 1200)
    return
  }
  emit('dismiss')
  emit('update:modelValue', false)
}
</script>

<style scoped lang="scss">
@use '../../styles/variables' as *;
@use '../../styles/design-tokens' as *;
@use '../../styles/setup-wizard-shared' as wiz;

// Steps 0/2/3 float their body vertically below the (top-pinned) title.
// Step 1 (Connect) has no wrapper — content-heavy, flows top-down.
@include wiz.setup-wiz-center;

/* Overlay transition */
.overlay-fade-enter-active {
  transition: opacity 250ms ease-out;
}

.overlay-fade-leave-active {
  transition: opacity 200ms ease-in;
}

.overlay-fade-enter-from,
.overlay-fade-leave-to {
  opacity: 0;
}

/* Full viewport overlay */
.setup-wizard-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

/* Semi-transparent backdrop */
.setup-wizard-backdrop {
  position: absolute;
  inset: 0;
  background: rgba($color-background-primary, 0.85);
}

/* ── Learning mode panel (unchanged single-column) ── */
.setup-wizard-panel {
  position: relative;
  width: 100%;
  max-width: 810px;
  max-height: calc(100vh - 48px);
  overflow: hidden;
  background: $elevation-raised;
  border-radius: $border-radius-rounded;
  display: flex;
  flex-direction: column;
}

.setup-wizard-header {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 20px 24px 12px;
}

.setup-wizard-title {
  font-size: 3rem;
  font-weight: 700;
  color: $color-text-primary;
  margin: 0;
  line-height: 1.2;
  letter-spacing: 0.5px;
  text-align: center;
}

.setup-wizard-title-gradient {
  background: var(--gradient-brand);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.setup-wizard-close-btn {
  position: absolute;
  right: 24px;
  top: 50%;
  transform: translateY(-50%);
}

.setup-wizard-content {
  flex: 1;
  padding: 0 24px 16px;
  min-height: 0;
  overflow-y: auto;
}

.setup-wizard-footer {
  display: flex;
  align-items: center;
  padding: 12px 24px 20px;
}

.footer-btn-gotit {
  border-radius: $border-radius-default;
  min-width: 120px;
  font-weight: 600;
}

.setup-wizard-footer--learning {
  justify-content: flex-end;
}

/* Learning mode sections */
.learning-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.learning-section {
  background: $elevation-elevated;
  border-radius: $border-radius-default;
  overflow: hidden;
}

.learning-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 14px 16px;
  background: none;
  border: none;
  cursor: pointer;
  color: $color-text-primary;
  font-size: 0.9375rem;
  font-weight: 600;
  text-align: left;
  transition: background-color 150ms ease-out;
}

.learning-section-header:hover {
  background: rgba($color-brand-yellow, 0.05);
}

.learning-section-header:focus-visible {
  outline: 2px solid $color-brand-yellow;
  outline-offset: -2px;
}

.section-icon {
  flex-shrink: 0;
}

.section-title {
  flex: 1;
}

.section-chevron {
  color: $lightest-blue;
  transition: transform 250ms ease-out;
  flex-shrink: 0;
}

.section-chevron--open {
  transform: rotate(180deg);
}

.learning-section-body {
  padding: 0 16px 14px 46px;
}

.learning-line {
  font-size: 0.8125rem;
  color: $lightest-blue; /* design-token-exempt: closest match, original #b0b8d0 */
  line-height: 1.6;
  margin: 0 0 6px;
}

.learning-line:last-child {
  margin-bottom: 0;
}

.learning-closing {
  font-size: 0.8125rem;
  color: $lightest-blue;
  text-align: center;
  margin-top: 16px;
}

.section-expand-enter-active {
  transition: max-height 250ms ease-out, opacity 250ms ease-out;
  max-height: 300px;
  overflow: hidden;
}

.section-expand-leave-active {
  transition: max-height 200ms ease-in, opacity 200ms ease-in;
  max-height: 300px;
  overflow: hidden;
}

.section-expand-enter-from,
.section-expand-leave-to {
  max-height: 0;
  opacity: 0;
}

/* ============================================================
   SETUP MODE — Gradient Rail (FE-6259b)
   ============================================================ */

.wizard-rail-panel {
  position: relative;
  width: 100%;
  max-width: 900px;
  min-height: 540px;
  max-height: calc(100vh - 48px);
  overflow: hidden;
  background: $elevation-raised;
  border-radius: $border-radius-rounded;
  display: grid;
  grid-template-columns: 258px 1fr;
}

.wizard-rail-close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 5;
}

/* ── Closing state (all-complete checkmark) ── */
.closing-confirmation {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  gap: 12px;
  animation: closing-fade-in 0.4s ease;
}

.closing-icon {
  animation: closing-scale 0.5s ease;
}

.closing-text {
  font-size: 1.1rem;
  font-weight: 500;
  color: rgb(var(--v-theme-success));
}

@keyframes closing-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes closing-scale {
  0% { transform: scale(0.5); opacity: 0; }
  60% { transform: scale(1.15); }
  100% { transform: scale(1); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .closing-confirmation,
  .closing-icon {
    animation: none;
  }
}

/* ── Left rail ── */
.wizard-rail {
  background: $color-background-tertiary;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  padding: 26px 20px;
  position: relative;
  overflow-y: auto;
}

.rail-top {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-bottom: 28px;
}

.rail-logo {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
}

.rail-title {
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 700;
  font-size: 1.05rem;
  line-height: 1.1;
  background: var(--gradient-brand);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.rail-count {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.62rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-top: 3px;
}

.stepper {
  position: relative;
  padding-left: 4px;
}

.spine {
  position: absolute;
  left: 19px;
  top: 12px;
  bottom: 12px;
  width: 3px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.spine-fill {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 0;
  border-radius: 3px;
  background: var(--gradient-brand);
  transition: height 0.4s cubic-bezier(0.4, 0.9, 0.3, 1);
}

@media (prefers-reduced-motion: reduce) {
  .spine-fill {
    transition: none;
  }
}

.rail-node {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 13px;
  padding: 11px 8px 11px 0;
  border-radius: 10px;
  cursor: default;
}

.rail-node--clickable {
  cursor: pointer;
}

.rail-node--clickable:hover {
  background: rgba(255, 255, 255, 0.03);
}

.rail-node--clickable:focus-visible {
  outline: 2px solid rgba(255, 195, 0, 0.55);
  outline-offset: 2px;
}

.rail-dot {
  position: relative;
  z-index: 1;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: $elevation-raised;
  box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.12);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--text-muted);
  transition: box-shadow 0.25s, background 0.25s, color 0.25s;
}

@media (prefers-reduced-motion: reduce) {
  .rail-dot {
    transition: none;
  }
}

.rail-node--active .rail-dot {
  box-shadow: inset 0 0 0 2px var(--nodecol), 0 0 0 4px color-mix(in srgb, var(--nodecol) 22%, transparent);
  color: var(--nodecol);
  background: color-mix(in srgb, var(--nodecol) 12%, $elevation-raised);
}

.rail-node--done .rail-dot {
  background: var(--nodecol);
  color: $color-on-brand-ink;
  box-shadow: none;
}

.rail-node-label {
  display: block;
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 600;
  font-size: 0.88rem;
  color: $lightest-blue;
  transition: color 0.2s;
}

.rail-node--active .rail-node-label,
.rail-node--done .rail-node-label {
  color: $color-text-primary;
}

.rail-node-desc {
  display: block;
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-top: 1px;
}

/* ── Right: main content + footer ── */
.wizard-main {
  display: flex;
  flex-direction: column;
  padding: 26px 30px 22px;
  min-width: 0;
}

.wizard-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.step-heading-grad {
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 600;
  font-size: 1.2rem;
  text-align: center;
  margin: 4px 0 4px;
  letter-spacing: -0.01em;
  background: var(--gradient-brand);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.step-sub {
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.88rem;
  margin: 0 auto 20px;
  max-width: 40rem;
}

.step-fineprint {
  text-align: center;
  font-size: 0.74rem;
  color: var(--text-muted);
  margin: 16px auto 0;
  max-width: 46rem;
  line-height: 1.5;
}

/* Tools grid: single 4-up row (step 0) */
.tools-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

@media (max-width: 640px) {
  .tools-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.tool-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 9px;
  padding: 20px 10px 16px;
  border-radius: $border-radius-md;
  background: $elevation-elevated;
  cursor: pointer;
  user-select: none;
  transition: transform 0.15s, box-shadow 0.15s;
}

.tool-card:hover {
  transform: translateY(-2px);
  --smooth-border-color: #{rgba($color-brand-yellow, 0.4)};
}

.tool-card:focus-visible {
  outline: 2px solid $color-brand-yellow;
  outline-offset: 2px;
}

.tool-card--sel {
  --smooth-border-color: #{$color-brand-yellow};
  box-shadow: inset 0 0 0 2px $color-brand-yellow, 0 0 16px rgba($color-brand-yellow, 0.12) !important;
  background: rgba($color-brand-yellow, 0.05);
}

.tool-card-tick {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: $color-brand-yellow;
  color: $color-on-yellow-ink;
}

.tool-card-logo {
  width: 38px;
  height: 38px;
  object-fit: contain;
}

.tool-name {
  font-family: 'Outfit', $typography-font-primary;
  font-size: 0.9rem;
  font-weight: 600;
  color: $color-text-primary;
  text-align: center;
}

.tool-provider {
  font-size: 0.74rem;
  color: var(--text-muted);
}

/* ── Footer ── */
.wz-footer {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 14px;
  margin-top: 4px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.footer-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.footer-spacer {
  flex: 1;
}

.footer-back {
  color: $lightest-blue !important;
}

.footer-restart {
  color: var(--text-muted) !important;
}

.footer-next-btn {
  border-radius: $border-radius-default;
  min-width: 100px;
  font-weight: 600;
  // Gradient Next/Finish per the locked spec (mockup .btn-grad): brand ramp
  // fill with dark on-brand ink. !important overrides Vuetify's flat surface.
  background: var(--gradient-brand) !important;
  color: $color-on-brand-ink !important;
}

// Preserve Vuetify's disabled dimming for the gradient Next button.
.footer-next-btn.v-btn--disabled {
  opacity: 0.4;
}

.footer-skip {
  text-align: right;
}

.skiplink {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--text-muted);
  padding: 2px 0;
  font-family: inherit;
  transition: color 150ms ease-out;
}

.skiplink:hover,
.skiplink:focus-visible {
  color: $color-brand-yellow;
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* Responsive: rail collapses above content on narrow viewports */
@media (max-width: 720px) {
  .wizard-rail-panel {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }

  .wizard-rail {
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  .spine,
  .spine-fill {
    display: none;
  }
}

/* Responsive: mobile */
@media (max-width: 599px) {
  .setup-wizard-overlay {
    padding: 12px;
  }

  .setup-wizard-header {
    padding: 16px 16px 8px;
  }

  .setup-wizard-content {
    padding: 0 16px 12px;
  }

  .setup-wizard-footer {
    padding: 8px 16px 16px;
  }

  .wizard-rail {
    padding: 18px 16px;
  }

  .wizard-main {
    padding: 18px 16px 16px;
  }
}
</style>
