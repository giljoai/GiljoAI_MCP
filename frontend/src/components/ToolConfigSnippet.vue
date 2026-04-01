<template>
  <v-card variant="flat" class="config-snippet-card smooth-border">
    <v-card-text class="pa-0 position-relative">
      <!-- Copy Button (Floating top-right) -->
      <v-btn
        icon="mdi-content-copy"
        size="small"
        variant="text"
        color="primary"
        class="copy-button"
        data-test="copy-button"
        :aria-label="`Copy ${language} configuration to clipboard`"
        @click="copyToClipboard"
      >
        <v-icon>mdi-content-copy</v-icon>
        <v-tooltip activator="parent" location="top">Copy to clipboard</v-tooltip>
      </v-btn>

      <!-- Code Block -->
      <pre
        class="code-block"
        data-test="config-snippet"
        :aria-label="`${language} configuration code snippet`"
      ><code :class="`language-${language}`">{{ config }}</code></pre>

      <!-- Success Message (Snackbar-style) -->
      <v-slide-y-transition>
        <div
          v-if="copySuccess"
          class="copy-success-message"
          data-test="copy-success"
          role="status"
          aria-live="polite"
        >
          <v-icon size="small" class="mr-1">mdi-check-circle</v-icon>
          Copied!
        </div>
      </v-slide-y-transition>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref } from 'vue'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'

const { copy: clipboardCopy } = useClipboard()
const { showToast } = useToast()

// Props
const props = defineProps({
  config: {
    type: String,
    required: true,
    default: '',
  },
  language: {
    type: String,
    default: 'json',
  },
})

// State
const copySuccess = ref(false)

// Methods
async function copyToClipboard() {
  const success = await clipboardCopy(props.config)
  if (success) {
    copySuccess.value = true
    setTimeout(() => {
      copySuccess.value = false
    }, 2000)
    showToast({ message: 'Configuration copied to clipboard', type: 'success' })
  } else {
    showToast({ message: 'Copy failed — select the text and press Ctrl+C', type: 'warning' })
  }
}
</script>

<style lang="scss" scoped>
@use '../styles/design-tokens' as *;
.config-snippet-card {
  background-color: rgb(var(--v-theme-surface-variant));
  border-radius: $border-radius-default;
  position: relative;
}

.copy-button {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 1;
}

.code-block {
  margin: 0;
  padding: 48px 16px 16px 16px;
  background-color: rgb(var(--v-theme-surface-variant));
  border-radius: $border-radius-default;
  overflow-x: auto;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  color: rgb(var(--v-theme-on-surface));
}

.code-block code {
  font-family: inherit;
  white-space: pre;
  word-wrap: normal;
}

.copy-success-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: rgb(var(--v-theme-success));
  color: rgb(var(--v-theme-on-success));
  padding: 12px 24px;
  border-radius: $border-radius-pill;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: center;
  font-weight: 500;
  z-index: 2;
}

/* Accessibility: Focus indicators */
.copy-button:focus-visible {
  outline: 2px solid rgba(var(--v-theme-primary), 0.5);
  outline-offset: 2px;
}
</style>
