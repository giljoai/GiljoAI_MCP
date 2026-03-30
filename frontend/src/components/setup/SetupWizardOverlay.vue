<template>
  <Teleport to="body">
    <Transition name="overlay-fade">
      <div
        v-if="modelValue"
        class="setup-wizard-overlay"
        role="dialog"
        aria-modal="true"
        aria-label="Setup GiljoAI MCP"
        @keydown.escape="handleDismiss"
      >
        <!-- Backdrop — click does NOT close -->
        <div class="setup-wizard-backdrop" />

        <!-- Content panel -->
        <div class="setup-wizard-panel smooth-border" tabindex="-1">
          <!-- Header -->
          <div class="setup-wizard-header">
            <h2 class="setup-wizard-title">
              <template v-if="mode === 'learning'">How to Use GiljoAI MCP</template>
              <template v-else><span class="setup-wizard-title-gradient">Setup</span></template>
            </h2>
            <v-btn
              icon
              variant="text"
              size="small"
              class="setup-wizard-close-btn"
              :aria-label="mode === 'learning' ? 'Close guide' : 'Close setup wizard'"
              @click="handleDismiss"
            >
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </div>

          <!-- Progress bar (setup mode only) -->
          <div v-if="mode !== 'learning'" class="setup-wizard-progress" role="progressbar" :aria-valuenow="currentStep" aria-valuemin="0" aria-valuemax="3">
            <div class="progress-steps">
              <div
                v-for="(step, index) in STEPS"
                :key="step.id"
                class="progress-step"
              >
                <!-- Step indicator -->
                <div class="step-indicator-wrapper">
                  <div
                    :class="[
                      'step-circle',
                      {
                        'step-circle--active': index === currentStep,
                        'step-circle--completed': index < currentStep,
                        'step-circle--future': index > currentStep,
                      },
                    ]"
                  >
                    <v-icon v-if="index < currentStep" size="14" style="color: var(--color-bg-primary)">
                      mdi-check
                    </v-icon>
                  </div>
                  <span
                    :class="[
                      'step-label',
                      {
                        'step-label--active': index === currentStep,
                        'step-label--completed': index < currentStep,
                        'step-label--future': index > currentStep,
                      },
                    ]"
                  >
                    {{ step.label }}
                  </span>
                </div>

                <!-- Connector bar (not after last step) -->
                <div v-if="index < STEPS.length - 1" class="step-connector">
                  <div
                    class="step-connector-fill"
                    :class="{ 'step-connector-fill--completed': index < currentStep }"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Step content -->
          <div class="setup-wizard-content">
            <!-- Learning mode: read-only reference guide -->
            <template v-if="mode === 'learning'">
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
              </div>
            </template>

            <!-- Setup mode: interactive wizard steps -->
            <template v-else>
              <!-- Step 0: Choose Tools -->
              <div v-if="currentStep === 0" class="step-tools">
                <p class="step-question">Which AI coding agent(s) do you use?</p>

                <div class="tools-grid">
                  <div
                    v-for="tool in TOOLS"
                    :key="tool.id"
                    :class="['tool-card', 'smooth-border']"
                    :style="isSelected(tool.id) ? selectedCardStyle : undefined"
                    role="checkbox"
                    :aria-checked="isSelected(tool.id)"
                    :aria-label="tool.name"
                    tabindex="0"
                    @click="toggleTool(tool.id)"
                    @keydown.enter.prevent="toggleTool(tool.id)"
                    @keydown.space.prevent="toggleTool(tool.id)"
                  >
                    <img :src="tool.logo" :alt="tool.name" class="tool-card-logo" />
                    <span class="tool-name">{{ tool.name }}</span>
                    <span class="tool-provider">{{ tool.provider }}</span>
                  </div>
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
                @can-proceed="step3CanProceed = $event"
                @step-data="step3Data = $event"
                @skip="handleStep3Skip"
              />

              <!-- Step 3: Launch (0855f) -->
              <SetupStep4Complete
                v-else-if="currentStep === 3"
                @complete="handleStep4Complete"
              />
            </template>
          </div>

          <!-- Learning mode footer: single "Got it" button -->
          <div v-if="mode === 'learning'" class="setup-wizard-footer setup-wizard-footer--learning">
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

          <!-- Setup mode footer (hidden on step 3 — Step 4 has its own card-based navigation) -->
          <div v-else-if="currentStep < 3" class="setup-wizard-footer">
            <v-btn
              v-if="currentStep > 0"
              variant="text"
              class="footer-btn-back"
              @click="handleBack"
            >
              Back
            </v-btn>
            <v-spacer />
            <v-btn
              color="primary"
              variant="flat"
              class="footer-btn-next"
              :disabled="!canProceed"
              @click="handleNext"
            >
              Next
            </v-btn>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, reactive, watch } from 'vue'
import SetupStep2Connect from './SetupStep2Connect.vue'
import SetupStep3Commands from './SetupStep3Commands.vue'
import SetupStep4Complete from './SetupStep4Complete.vue'

const LEARNING_SECTIONS = [
  {
    id: 'hierarchy',
    icon: 'mdi-sitemap',
    title: 'Product Hierarchy',
    content: [
      'Products are the top level — they represent a software product or system you are building.',
      'Projects live inside Products. Each project is a focused unit of work (a feature, sprint, or initiative).',
      'Jobs are created when you run an agent within a project. They track each AI coding session.',
      'Agents execute inside jobs. Multiple agents can collaborate on a single job using chain strategies.',
    ],
  },
  {
    id: 'tools',
    icon: 'mdi-console',
    title: 'AI Coding Tools',
    content: [
      'GiljoAI MCP works with Claude Code, Codex CLI, and Gemini CLI via the MCP protocol.',
      'Each tool connects to GiljoAI as an MCP server — your orchestration commands become tool calls.',
      'You can use multiple tools simultaneously. Each gets its own API key and connection.',
      'The MCP connection gives your AI agent access to project context, agent templates, and coordination tools.',
    ],
  },
  {
    id: 'commands',
    icon: 'mdi-slash-forward-box',
    title: 'Slash Commands',
    content: [
      '/gil_add — Add tasks or projects to the dashboard directly from your coding agent.',
      '/gil_get_agents — Download agent templates with orchestration protocols into your workspace.',
      'Slash commands are the primary way to interact with GiljoAI from within your AI coding tool.',
      'Commands are context-aware: they know which product and project you are working in.',
    ],
  },
  {
    id: 'agents',
    icon: 'mdi-robot',
    title: 'Agent Templates',
    content: [
      'Agent templates are pre-configured protocols that tell your AI coding tool how to work on a task.',
      'Templates include chain strategies (sequential handovers, parallel work, orchestrator-gated flows).',
      'The Agent Lab lets you browse, customize, and download templates for different workflow patterns.',
      'Templates are tool-agnostic — the same strategy works with Claude Code, Codex CLI, or Gemini CLI.',
    ],
  },
  {
    id: 'dashboard',
    icon: 'mdi-view-dashboard',
    title: 'Dashboard',
    content: [
      'The Products page shows all your software products and their vision documents.',
      'The Projects page lists active projects with status, progress, and linked jobs.',
      'The Tasks page tracks technical debt, TODOs, and action items across all products.',
      'Each page offers filtering, search, and quick actions to manage your development workflow.',
    ],
  },
]

const TOOLS = [
  { id: 'claude_code', name: 'Claude Code', provider: 'by Anthropic', logo: '/claude_pix.svg' },
  { id: 'codex_cli', name: 'Codex CLI', provider: 'by OpenAI', logo: '/icons/codex_mark_white.svg' },
  { id: 'gemini_cli', name: 'Gemini CLI', provider: 'by Google', logo: '/gemini-icon.svg' },
]

const STEPS = [
  { id: 'tools', label: 'Choose Tools' },
  { id: 'connect', label: 'Connect' },
  { id: 'install', label: 'Install' },
  { id: 'launch', label: 'Launch' },
]

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

// Sync when prop changes externally
watch(
  () => props.selectedTools,
  (newVal) => {
    localSelectedTools.value = [...newVal]
  },
)

// Connected tools from Step 2 data, passed to Step 3
const step2ConnectedTools = computed(() => step2Data.value?.connectedTools || [])

const selectedCardStyle = {
  '--smooth-border-color': 'var(--color-accent-primary)',
  'box-shadow': 'inset 0 0 0 1px var(--color-accent-primary), 0 0 12px rgba(255, 195, 0, 0.15)',
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

function handleStep3Skip() {
  emit('step-complete', { step: 2, data: { installedTools: [], skipped: true } })
  if (props.currentStep < STEPS.length - 1) {
    emit('update:currentStep', props.currentStep + 1)
  }
}

function handleStep4Complete({ action, route }) {
  emit('step-complete', { step: 3, data: { action, route, setup_complete: true } })
  emit('update:modelValue', false)
}

function handleDismiss() {
  emit('dismiss')
  emit('update:modelValue', false)
}
</script>

<style scoped lang="scss">
@use '../../styles/variables' as *;
@use '../../styles/design-tokens' as *;

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

/* Centered content panel */
.setup-wizard-panel {
  position: relative;
  width: 100%;
  max-width: 800px;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  background: $elevation-raised;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
}

/* Header */
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

/* Progress bar */
.setup-wizard-progress {
  padding: 8px 24px 20px;
}

.progress-steps {
  display: flex;
  align-items: flex-start;
}

.progress-step {
  display: flex;
  align-items: center;
  flex: 1;
}

.progress-step:last-child {
  flex: 0 0 auto;
}

.step-indicator-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-width: 72px;
}

.step-circle {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 250ms ease-out, box-shadow 250ms ease-out;
}

.step-circle--active {
  background: $color-brand-yellow;
}

.step-circle--completed {
  background: $color-brand-yellow;
}

.step-circle--future {
  background: transparent;
  box-shadow: inset 0 0 0 2px $med-blue;
}

.step-label {
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
  transition: color 250ms ease-out;
}

.step-label--active {
  color: $color-brand-yellow;
}

.step-label--completed {
  color: $color-brand-yellow;
}

.step-label--future {
  color: $lightest-blue;
}

/* Connector bar between steps */
.step-connector {
  flex: 1;
  height: 4px;
  background: $med-blue;
  border-radius: 2px;
  margin: 0 8px;
  margin-bottom: 22px;
  overflow: hidden;
}

.step-connector-fill {
  height: 100%;
  width: 0;
  border-radius: 2px;
  background: $color-brand-yellow;
  transition: width 250ms ease-out;
}

.step-connector-fill--completed {
  width: 100%;
}

/* Step content area */
.setup-wizard-content {
  flex: 1;
  padding: 0 24px 16px;
  min-height: 240px;
}

.step-question {
  font-family: "Roboto", "Segoe UI", system-ui, -apple-system, sans-serif;
  font-size: 1rem;
  font-weight: 500;
  color: $color-text-primary;
  margin-bottom: 20px;
  text-align: center;
}

/* Tools grid */
.tools-grid {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

.tool-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 24px 20px;
  min-width: 180px;
  max-width: 220px;
  flex: 1;
  background: $elevation-elevated;
  border-radius: 12px;
  cursor: pointer;
  user-select: none;
  transition: box-shadow 250ms ease-out, transform 150ms ease-out;
}

.tool-card:hover {
  transform: translateY(-2px);
}

.tool-card:focus-visible {
  outline: 2px solid $color-brand-yellow;
  outline-offset: 2px;
}

.tool-name {
  font-family: "Roboto", "Segoe UI", system-ui, -apple-system, sans-serif;
  font-size: 0.9375rem;
  font-weight: 600;
  color: $color-text-primary;
}

.tool-provider {
  font-size: 0.8125rem;
  color: $lightest-blue;
}

.tool-card-logo {
  width: 36px;
  height: 36px;
  object-fit: contain;
}

/* Placeholder steps */
.step-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.placeholder-text {
  color: $lightest-blue;
  font-size: 0.875rem;
  font-style: italic;
}

/* Footer */
.setup-wizard-footer {
  display: flex;
  align-items: center;
  padding: 12px 24px 20px;
}

.footer-btn-back {
  color: $lightest-blue !important;
}

.footer-btn-next {
  border-radius: 8px;
  min-width: 100px;
  font-weight: 600;
}

.footer-btn-gotit {
  border-radius: 8px;
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
  border-radius: 10px;
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

/* Section expand transition */
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

.section-expand-enter-from {
  max-height: 0;
  opacity: 0;
}

.section-expand-leave-to {
  max-height: 0;
  opacity: 0;
}

/* Responsive: mobile */
@media (max-width: 599px) {
  .setup-wizard-overlay {
    padding: 12px;
  }

  .setup-wizard-header {
    padding: 16px 16px 8px;
  }

  .setup-wizard-progress {
    padding: 8px 16px 16px;
  }

  .setup-wizard-content {
    padding: 0 16px 12px;
  }

  .setup-wizard-footer {
    padding: 8px 16px 16px;
  }

  .tools-grid {
    flex-direction: column;
    align-items: stretch;
  }

  .tool-card {
    max-width: 100%;
    flex-direction: row;
    padding: 16px;
    gap: 12px;
  }

  .step-label {
    font-size: 0.6875rem;
  }

  .step-indicator-wrapper {
    min-width: 56px;
  }
}

/* Responsive: tablet */
@media (min-width: 600px) and (max-width: 959px) {
  .tool-card {
    min-width: 150px;
    padding: 20px 16px;
  }
}
</style>
