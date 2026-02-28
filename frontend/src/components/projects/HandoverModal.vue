<template>
  <v-dialog
    :model-value="show"
    :fullscreen="isMobile"
    :max-width="isMobile ? undefined : '800'"
    persistent
    class="handover-modal"
    role="dialog"
    :aria-labelledby="'handover-modal-title'"
    data-testid="handover-modal"
    @keydown.esc="handleClose"
  >
    <v-card v-draggable data-testid="handover-modal-card">
      <!-- Modal header -->
      <v-card-title id="handover-modal-title" class="modal-title bg-primary text-white pa-4">
        <div class="d-flex align-center justify-space-between">
          <div class="d-flex align-center">
            <v-icon icon="mdi-refresh" size="large" class="mr-2" />
            <span class="text-h6">Orchestrator Session Handover</span>
            <v-tooltip location="bottom" max-width="360">
              <template #activator="{ props: tooltipProps }">
                <v-icon
                  v-bind="tooltipProps"
                  icon="mdi-information-outline"
                  size="small"
                  class="ml-2"
                  style="opacity: 0.8"
                />
              </template>
              Use this when an orchestrator has exhausted its context budget and you need
              a fresh session to continue the work.
            </v-tooltip>
          </div>
          <v-btn icon variant="text" color="white" aria-label="Close modal" @click="handleClose">
            <v-icon icon="mdi-close" />
          </v-btn>
        </div>
      </v-card-title>

      <v-divider />

      <!-- Modal content -->
      <v-card-text class="pa-4">
        <!-- Warning banner -->
        <v-alert
          type="warning"
          variant="tonal"
          density="compact"
          class="mb-5"
          icon="mdi-alert"
        >
          <span class="text-body-2">
            If the current orchestrator has active subagents, it will wait for them to finish
            before closing out. Do not paste the continuation prompt until the old orchestrator
            confirms: <strong>"Session context saved to 360 Memory."</strong>
          </span>
        </v-alert>

        <!-- Step 1: Retire Current Orchestrator -->
        <v-card variant="outlined" class="mb-4 step-card">
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center pa-4 pb-2">
            <v-avatar color="warning" size="28" class="mr-3">
              <span class="text-caption font-weight-bold" style="color: #000">1</span>
            </v-avatar>
            Retire Current Orchestrator
          </v-card-title>
          <v-card-text class="pa-4 pt-1">
            <p class="text-body-2 mb-3" style="color: rgba(255,255,255,0.7)">
              Copy this prompt and paste it into the current orchestrator's terminal. This instructs
              it to wait for any active subagents to finish, then save its full session context to
              360 Memory.
            </p>
            <div class="prompt-block">
              <div class="prompt-header d-flex align-center justify-space-between">
                <span class="text-caption font-weight-medium">Retirement Prompt</span>
                <v-btn
                  size="small"
                  variant="text"
                  color="warning"
                  prepend-icon="mdi-content-copy"
                  data-testid="copy-retirement-btn"
                  @click="copyRetirementPrompt"
                >
                  {{ retirementCopied ? 'Copied!' : 'Copy' }}
                </v-btn>
              </div>
              <pre class="prompt-code">{{ retirementPrompt }}</pre>
            </div>
          </v-card-text>
        </v-card>

        <!-- Step 2: Continue in New Terminal -->
        <v-card variant="outlined" class="step-card">
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center pa-4 pb-2">
            <v-avatar color="success" size="28" class="mr-3">
              <span class="text-caption font-weight-bold" style="color: #000">2</span>
            </v-avatar>
            Continue in New Terminal
          </v-card-title>
          <v-card-text class="pa-4 pt-1">
            <p class="text-body-2 mb-3" style="color: rgba(255,255,255,0.7)">
              After the old orchestrator confirms it has saved its session, copy this prompt and
              paste it into a fresh terminal to start a new orchestrator.
            </p>
            <div class="prompt-block">
              <div class="prompt-header d-flex align-center justify-space-between">
                <span class="text-caption font-weight-medium">Continuation Prompt</span>
                <v-btn
                  size="small"
                  variant="text"
                  color="success"
                  prepend-icon="mdi-content-copy"
                  data-testid="copy-continuation-btn"
                  @click="copyContinuationPrompt"
                >
                  {{ continuationCopied ? 'Copied!' : 'Copy' }}
                </v-btn>
              </div>
              <pre class="prompt-code">{{ continuationPrompt }}</pre>
            </div>
          </v-card-text>
        </v-card>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDisplay } from 'vuetify'

const props = defineProps({
  show: {
    type: Boolean,
    required: true,
  },
  retirementPrompt: {
    type: String,
    default: '',
  },
  continuationPrompt: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['close'])

const { mobile } = useDisplay()
const isMobile = computed(() => mobile.value)

const retirementCopied = ref(false)
const continuationCopied = ref(false)

async function copyToClipboard(text) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      return await navigator.clipboard.writeText(text)
    }
  } catch (e) {
    // fall through to fallback
  }
  const textArea = document.createElement('textarea')
  textArea.value = text
  textArea.style.position = 'fixed'
  textArea.style.left = '-9999px'
  textArea.style.top = '-9999px'
  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()
  try {
    document.execCommand('copy')
  } finally {
    document.body.removeChild(textArea)
  }
}

async function copyRetirementPrompt() {
  await copyToClipboard(props.retirementPrompt)
  retirementCopied.value = true
  setTimeout(() => { retirementCopied.value = false }, 2000)
}

async function copyContinuationPrompt() {
  await copyToClipboard(props.continuationPrompt)
  continuationCopied.value = true
  setTimeout(() => { continuationCopied.value = false }, 2000)
}

function handleClose() {
  retirementCopied.value = false
  continuationCopied.value = false
  emit('close')
}
</script>

<style scoped>
.modal-title {
  position: sticky;
  top: 0;
  z-index: 1;
}

.step-card {
  border-color: rgba(255, 255, 255, 0.12);
}

.prompt-block {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  overflow: hidden;
}

.prompt-header {
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.prompt-code {
  padding: 12px 16px;
  margin: 0;
  font-family: 'Roboto Mono', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.85);
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 300px;
  overflow-y: auto;
}

/* Mobile optimizations */
@media (max-width: 600px) {
  .modal-title {
    font-size: 1.125rem;
  }

  .prompt-code {
    font-size: 11px;
    max-height: 200px;
  }
}
</style>
