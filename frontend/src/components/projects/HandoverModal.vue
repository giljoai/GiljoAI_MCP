<template>
  <v-dialog
    :model-value="show"
    :fullscreen="isMobile"
    :max-width="isMobile ? undefined : '480'"
    persistent
    class="handover-modal"
    role="dialog"
    :aria-labelledby="'handover-modal-title'"
    data-testid="handover-modal"
    @keydown.esc="handleClose"
  >
    <v-card v-draggable data-testid="handover-modal-card" class="smooth-border">
      <!-- Modal header -->
      <v-card-title id="handover-modal-title" class="modal-title bg-primary text-white pa-4">
        <div class="d-flex align-center justify-space-between">
          <div class="d-flex align-center">
            <v-icon icon="mdi-refresh" size="large" class="mr-2" />
            <span class="text-h6">Session Handover</span>
            <v-tooltip location="bottom" max-width="300">
              <template #activator="{ props: tooltipProps }">
                <v-icon
                  v-bind="tooltipProps"
                  icon="mdi-information-outline"
                  size="small"
                  class="ml-2"
                  style="opacity: 0.8"
                  aria-label="Handover information"
                />
              </template>
              Refreshes the orchestrator's context by retiring the current session
              and starting a new one.
            </v-tooltip>
          </div>
          <v-btn icon variant="text" color="white" aria-label="Close modal" @click="handleClose">
            <v-icon icon="mdi-close" />
          </v-btn>
        </div>
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-4">
        <!-- Checkbox gate -->
        <v-checkbox
          v-model="subagentsConfirmed"
          color="warning"
          density="compact"
          hide-details
          class="mb-4"
          data-testid="subagents-checkbox"
        >
          <template #label>
            <span class="text-body-2" style="color: rgba(255,255,255,0.85)">
              I confirm all subagents have finished their work
            </span>
          </template>
        </v-checkbox>

        <!-- Step 1: Retire -->
        <div class="step-row mb-3" data-testid="step-1">
          <v-avatar :color="step1Done ? 'success' : 'grey-darken-1'" size="26" class="mr-3 flex-shrink-0">
            <span class="text-caption font-weight-bold" style="color: white">1</span>
          </v-avatar>
          <span class="step-label text-body-2">Copy and paste this prompt to the current terminal window running the orchestrator</span>
          <v-spacer />
          <v-btn
            size="small"
            :variant="step1Done ? 'tonal' : 'elevated'"
            :color="step1Done ? 'success' : 'warning'"
            :disabled="!subagentsConfirmed"
            :prepend-icon="step1Done ? 'mdi-check' : 'mdi-content-copy'"
            data-testid="copy-retirement-btn"
            class="ml-3 flex-shrink-0"
            @click="copyRetirementPrompt"
          >
            {{ step1Done ? 'Copied' : 'Copy' }}
          </v-btn>
        </div>

        <!-- Step 2: Continue -->
        <div class="step-row" data-testid="step-2">
          <v-avatar :color="step2Done ? 'success' : 'grey-darken-1'" size="26" class="mr-3 flex-shrink-0">
            <span class="text-caption font-weight-bold" style="color: white">2</span>
          </v-avatar>
          <span class="step-label text-body-2">Copy and paste this prompt into a fresh terminal to continue</span>
          <v-spacer />
          <v-btn
            size="small"
            :variant="step2Done ? 'tonal' : 'elevated'"
            :color="step2Done ? 'success' : 'warning'"
            :disabled="!step1Done"
            :prepend-icon="step2Done ? 'mdi-check' : 'mdi-content-copy'"
            data-testid="copy-continuation-btn"
            class="ml-3 flex-shrink-0"
            @click="copyContinuationPrompt"
          >
            {{ step2Done ? 'Copied' : 'Copy' }}
          </v-btn>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useDisplay } from 'vuetify'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'

const { copy: clipboardCopy } = useClipboard()
const { showToast } = useToast()

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

const subagentsConfirmed = ref(false)
const step1Done = ref(false)
const step2Done = ref(false)

// Reset state when modal opens/closes
watch(() => props.show, (val) => {
  if (!val) {
    subagentsConfirmed.value = false
    step1Done.value = false
    step2Done.value = false
  }
})

async function copyRetirementPrompt() {
  const success = await clipboardCopy(props.retirementPrompt)
  if (success) {
    step1Done.value = true
    showToast({ message: 'Retirement prompt copied to clipboard', type: 'success' })
  } else {
    showToast({ message: 'Copy failed — select the text and press Ctrl+C', type: 'warning' })
  }
}

async function copyContinuationPrompt() {
  const success = await clipboardCopy(props.continuationPrompt)
  if (success) {
    step2Done.value = true
    showToast({ message: 'Continuation prompt copied to clipboard', type: 'success' })
  } else {
    showToast({ message: 'Copy failed — select the text and press Ctrl+C', type: 'warning' })
  }
}

function handleClose() {
  emit('close')
}
</script>

<style lang="scss" scoped>
@use '../../styles/design-tokens' as *;
.modal-title {
  position: sticky;
  top: 0;
  z-index: 1;
}

.step-row {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: $border-radius-default;
  background: rgba(255, 255, 255, 0.04);
}

.step-label {
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.4;
}
</style>
