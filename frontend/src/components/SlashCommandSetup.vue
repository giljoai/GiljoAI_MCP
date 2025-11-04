<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-icon size="40" class="mr-2" color="primary">mdi-slash-forward</v-icon>
        <h3 class="text-h6 mb-0">Slash Command Setup</h3>
      </div>

      <p class="text-body-2 text-medium-emphasis mb-4">
        Install slash commands to your CLI tool (one-time setup)
      </p>

      <!-- Info Alert -->
      <v-alert
        type="info"
        variant="tonal"
        density="compact"
        class="mb-4"
        :icon="false"
      >
        <div class="d-flex align-center">
          <v-icon start size="small">mdi-information</v-icon>
          <div class="text-body-2">
            Run this command after adding the MCP server above.
            It installs 3 slash commands to your local CLI.
          </div>
        </div>
      </v-alert>

      <!-- Command Display -->
      <div class="d-flex align-center gap-2 mb-4">
        <v-text-field
          :model-value="setupCommand"
          readonly
          variant="outlined"
          density="compact"
          hide-details
          class="command-field"
        />
        <v-btn
          color="primary"
          variant="flat"
          size="default"
          @click="copySlashCommandSetup"
          :prepend-icon="copied ? 'mdi-check' : 'mdi-content-copy'"
        >
          {{ copied ? 'Copied!' : 'Copy Command' }}
        </v-btn>
      </div>

      <!-- Expansion Panel - What does this install? -->
      <v-expansion-panels variant="accordion">
        <v-expansion-panel>
          <v-expansion-panel-title class="text-subtitle-2">
            <v-icon start size="small">mdi-information-outline</v-icon>
            What does this install?
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-list density="compact" class="pa-0">
              <v-list-item class="px-0">
                <template v-slot:prepend>
                  <v-icon size="small" color="primary">mdi-slash-forward</v-icon>
                </template>
                <v-list-item-title>
                  <code class="command-code">/gil_import_productagents</code>
                </v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  Import agents to product folder
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item class="px-0">
                <template v-slot:prepend>
                  <v-icon size="small" color="primary">mdi-slash-forward</v-icon>
                </template>
                <v-list-item-title>
                  <code class="command-code">/gil_import_personalagents</code>
                </v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  Import agents to ~/.claude/agents
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item class="px-0">
                <template v-slot:prepend>
                  <v-icon size="small" color="primary">mdi-slash-forward</v-icon>
                </template>
                <v-list-item-title>
                  <code class="command-code">/gil_handover</code>
                </v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  Trigger orchestrator succession
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <!-- Restart Warning -->
            <v-alert
              type="warning"
              variant="text"
              density="compact"
              class="mt-3"
              :icon="false"
            >
              <div class="d-flex align-center">
                <v-icon start size="small">mdi-restart</v-icon>
                <div class="text-body-2">
                  <strong>Restart required:</strong> Restart your CLI after installation.
                </div>
              </div>
            </v-alert>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>

    <!-- Copy Feedback Snackbar -->
    <v-snackbar v-model="showCopyFeedback" timeout="3000" color="success" location="bottom right">
      <v-icon class="mr-2">mdi-check-circle</v-icon>
      {{ copyFeedbackMessage }}
      <template v-slot:actions>
        <v-btn variant="text" icon="mdi-close" @click="showCopyFeedback = false" />
      </template>
    </v-snackbar>
  </v-card>
</template>

<script setup>
import { ref } from 'vue'

// State
const setupCommand = '/setup_slash_commands'
const copied = ref(false)
const showCopyFeedback = ref(false)
const copyFeedbackMessage = ref('')

// Production-grade cross-platform clipboard copy (matching ClaudeCodeExport pattern)
function fallbackCopyToClipboard(text) {
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.position = 'absolute'
    ta.style.left = '-9999px'
    ta.style.top = '0'
    document.body.appendChild(ta)

    // Select and copy
    ta.focus()
    ta.select()

    // For iOS compatibility
    if (navigator.userAgent.match(/ipad|iphone/i)) {
      const range = document.createRange()
      range.selectNodeContents(ta)
      const selection = window.getSelection()
      selection.removeAllRanges()
      selection.addRange(range)
      ta.setSelectionRange(0, text.length)
    }

    const success = document.execCommand('copy')
    document.body.removeChild(ta)
    return success
  } catch (err) {
    console.error('[SLASH COMMAND SETUP] Fallback copy failed:', err)
    return false
  }
}

async function copySlashCommandSetup() {
  // Try Clipboard API first, fallback to execCommand
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(setupCommand)
      copied.value = true
      showCopyFeedback.value = true
      copyFeedbackMessage.value = 'Slash command setup copied! Paste in Claude Code/Codex/Gemini.'
      console.log('[SLASH COMMAND SETUP] Command copied via Clipboard API')

      // Reset copied state after 2 seconds
      setTimeout(() => {
        copied.value = false
      }, 2000)
      return
    } catch (error) {
      console.warn('[SLASH COMMAND SETUP] Clipboard API failed, using fallback:', error)
    }
  }

  // Fallback method
  const success = fallbackCopyToClipboard(setupCommand)
  if (success) {
    copied.value = true
    showCopyFeedback.value = true
    copyFeedbackMessage.value = 'Slash command setup copied! Paste in Claude Code/Codex/Gemini.'
    console.log('[SLASH COMMAND SETUP] Command copied via fallback')

    // Reset copied state after 2 seconds
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } else {
    showCopyFeedback.value = true
    copyFeedbackMessage.value = 'Failed to copy. Please copy manually.'
    console.error('[SLASH COMMAND SETUP] All copy methods failed')
  }
}
</script>

<style scoped>
.command-field {
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
}

.command-field :deep(input) {
  font-family: 'Courier New', monospace;
  color: rgb(var(--v-theme-primary));
  font-weight: 500;
}

.command-code {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875em;
  color: rgb(var(--v-theme-primary));
}

.gap-2 {
  gap: 8px;
}

/* Ensure expansion panel text has proper spacing */
:deep(.v-expansion-panel-text__wrapper) {
  padding: 12px 16px;
}
</style>
