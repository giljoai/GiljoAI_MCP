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
            <h2 class="setup-wizard-title">Setup GiljoAI MCP</h2>
            <v-btn
              icon
              variant="text"
              size="small"
              aria-label="Close setup wizard"
              @click="handleDismiss"
            >
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </div>

          <!-- Progress bar -->
          <div class="setup-wizard-progress" role="progressbar" :aria-valuenow="currentStep" aria-valuemin="0" aria-valuemax="3">
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
                    <v-icon v-if="index < currentStep" size="14" color="#6bcf7f">
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
                  <v-icon size="36" :color="isSelected(tool.id) ? '#ffc300' : '#8f97b7'">
                    {{ tool.icon }}
                  </v-icon>
                  <span class="tool-name">{{ tool.name }}</span>
                  <span class="tool-provider">{{ tool.provider }}</span>
                </div>
              </div>

              <p class="tools-learn-more">
                Don't have one yet?
                <a href="#" class="learn-more-link" @click.prevent>Learn more</a>
              </p>
            </div>

            <!-- Step 1: Connect (0855d) -->
            <SetupStep2Connect
              v-else-if="currentStep === 1"
              :selected-tools="localSelectedTools"
              @can-proceed="step2CanProceed = $event"
              @step-data="step2Data = $event"
            />

            <!-- Step 2: Install (placeholder) -->
            <div v-else-if="currentStep === 2" class="step-placeholder">
              <p class="placeholder-text">Step 3 content will be added by handover 0855e</p>
            </div>

            <!-- Step 3: Launch (placeholder) -->
            <div v-else-if="currentStep === 3" class="step-placeholder">
              <p class="placeholder-text">Step 4 content will be added by handover 0855f</p>
            </div>
          </div>

          <!-- Footer -->
          <div class="setup-wizard-footer">
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
              {{ currentStep === STEPS.length - 1 ? 'Finish' : 'Next' }}
            </v-btn>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import SetupStep2Connect from './SetupStep2Connect.vue'

const TOOLS = [
  { id: 'claude_code', name: 'Claude Code', provider: 'by Anthropic', icon: 'mdi-console' },
  { id: 'codex_cli', name: 'Codex CLI', provider: 'by OpenAI', icon: 'mdi-code-braces' },
  { id: 'gemini_cli', name: 'Gemini CLI', provider: 'by Google', icon: 'mdi-google' },
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

// Internal state
const localSelectedTools = ref([...props.selectedTools])
const step2CanProceed = ref(false)
const step2Data = ref({})

// Sync when prop changes externally
watch(
  () => props.selectedTools,
  (newVal) => {
    localSelectedTools.value = [...newVal]
  },
)

const selectedCardStyle = {
  '--smooth-border-color': '#ffc300',
  'box-shadow': 'inset 0 0 0 1px #ffc300, 0 0 12px rgba(255, 195, 0, 0.15)',
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
  // Placeholder steps: always allow proceeding
  return true
})

function handleNext() {
  if (!canProceed.value) return

  if (props.currentStep === 0) {
    emit('step-complete', { step: 0, data: { tools: [...localSelectedTools.value] } })
  } else if (props.currentStep === 1) {
    emit('step-complete', { step: 1, data: { ...step2Data.value } })
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

function handleDismiss() {
  emit('dismiss')
  emit('update:modelValue', false)
}
</script>

<style scoped>
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
  background: rgba(14, 28, 45, 0.85);
}

/* Centered content panel */
.setup-wizard-panel {
  position: relative;
  width: 100%;
  max-width: 800px;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  background: #182739;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
}

/* Header */
.setup-wizard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 12px;
}

.setup-wizard-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #e1e1e1;
  margin: 0;
  line-height: 1.4;
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
  background: #ffc300;
}

.step-circle--completed {
  background: #6bcf7f;
}

.step-circle--future {
  background: transparent;
  box-shadow: inset 0 0 0 2px #315074;
}

.step-label {
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
  transition: color 250ms ease-out;
}

.step-label--active {
  color: #ffc300;
}

.step-label--completed {
  color: #6bcf7f;
}

.step-label--future {
  color: #8f97b7;
}

/* Connector bar between steps */
.step-connector {
  flex: 1;
  height: 4px;
  background: #315074;
  border-radius: 2px;
  margin: 0 8px;
  margin-bottom: 22px;
  overflow: hidden;
}

.step-connector-fill {
  height: 100%;
  width: 0;
  border-radius: 2px;
  background: linear-gradient(45deg, #ffd93d, #6bcf7f);
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
  font-size: 1rem;
  font-weight: 500;
  color: #e1e1e1;
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
  background: #1e3147;
  border-radius: 12px;
  cursor: pointer;
  user-select: none;
  transition: box-shadow 250ms ease-out, transform 150ms ease-out;
}

.tool-card:hover {
  transform: translateY(-2px);
}

.tool-card:focus-visible {
  outline: 2px solid #ffc300;
  outline-offset: 2px;
}

.tool-name {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #e1e1e1;
}

.tool-provider {
  font-size: 0.8125rem;
  color: #8f97b7;
}

.tools-learn-more {
  text-align: center;
  margin-top: 20px;
  font-size: 0.8125rem;
  color: #8f97b7;
}

.learn-more-link {
  color: #8f97b7;
  text-decoration: underline;
  text-underline-offset: 2px;
  transition: color 250ms ease-out;
}

.learn-more-link:hover {
  color: #ffc300;
}

/* Placeholder steps */
.step-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.placeholder-text {
  color: #8f97b7;
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
  color: #8f97b7 !important;
}

.footer-btn-next {
  border-radius: 8px;
  min-width: 100px;
  font-weight: 600;
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
