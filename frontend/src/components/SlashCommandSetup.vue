<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-icon size="40" class="mr-2" color="primary">mdi-slash-forward-box</v-icon>
        <h3 class="text-h6 mb-0 mr-3">Slash Commands</h3>
        <v-tooltip location="top" max-width="400" class="ml-2">
          <template #activator="{ props }">
            <v-icon v-bind="props" size="small" color="medium-emphasis"
              >mdi-help-circle-outline</v-icon
            >
          </template>
          <div>
            <strong>Core slash commands:</strong>
            <ul class="mt-2 mb-2 pl-4">
              <li>/gil_get_claude_agents - Download + install agent templates</li>
              <li>/gil_task - Punt technical debt to Tasks dashboard</li>
              <li>/gil_activate - Activate a project for staging</li>
              <li>/gil_launch - Launch a staged project</li>
              <li>/gil_handover - Trigger orchestrator succession</li>
            </ul>
            <p class="text-caption mb-0">
              <em>*Only supported slash commands will be imported</em>
            </p>
          </div>
        </v-tooltip>
      </div>

      <p class="text-body-2 text-medium-emphasis mb-3">
        Install slash commands to your CLI tool for agent import and orchestrator succession
      </p>

      <!-- Download Installation -->
      <div class="d-flex align-center mb-4">
        <v-btn
          variant="text"
          size="small"
          color="light-blue"
          :loading="downloading"
          class="d-flex align-center"
          style="margin-left: -5px"
          @click="downloadSlashCommands"
        >
          <v-icon size="20" class="mr-2">mdi-slash-forward-box</v-icon>
          Download slash commands
        </v-btn>
        <span class="text-caption text-medium-emphasis ml-3">
          Download slash command files (includes install scripts)
        </span>
      </div>

      <!-- Manual Installation Badge -->
      <v-card variant="tonal" class="mb-3">
        <v-card-text class="pa-3">
          <div class="d-flex align-center justify-between">
            <div class="flex-grow-1">
              <div class="text-subtitle-2 font-weight-medium">
                MCP installation for slash commands
              </div>
              <div class="text-body-2 text-medium-emphasis">
                Installs slash commands in your CLI Agent tool with MCP
              </div>
            </div>
            <v-btn
              color="primary"
              variant="flat"
              size="small"
              width="120"
              :loading="generatingInstructions"
              :disabled="generatingInstructions"
              @click="copySlashCommandSetup"
            >
              Copy Command
            </v-btn>
          </div>
        </v-card-text>
      </v-card>
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
import api from '@/services/api'

// State
const copied = ref(false)
const downloading = ref(false)
const generatingInstructions = ref(false)
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

/**
 * Generate natural language installation instructions with download token
 * and copy to clipboard.
 */
async function copySlashCommandSetup() {
  try {
    generatingInstructions.value = true
    console.log('[SLASH COMMAND SETUP] Generating download instructions...')

    // Call backend to generate timed download URL
    const response = await api.downloads.generateSlashCommandsInstructions()
    const downloadUrl = response.data.download_url

    if (!downloadUrl) {
      throw new Error('No download URL received from server')
    }

    // Construct curl command for CLI installation
    const curlCommand = `curl -O ${downloadUrl} && unzip -o slash_commands.zip -d ~/.claude/commands/ && rm slash_commands.zip`

    // Copy curl command to clipboard
    await copyToClipboard(curlCommand)

    copied.value = true
    showCopyFeedback.value = true
    copyFeedbackMessage.value = 'Installation command copied to clipboard!'
    console.log('[SLASH COMMAND SETUP] Curl command copied successfully')

    // Reset copied state after 2 seconds
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (error) {
    console.error('[SLASH COMMAND SETUP] Failed to generate instructions:', error)

    let errorMessage = 'Failed to generate installation instructions. '
    if (error.response?.status === 401) {
      errorMessage += 'Please log in and try again.'
    } else if (error.response?.status === 500) {
      errorMessage += 'Server error - please contact administrator.'
    } else if (!error.response) {
      errorMessage += 'Network error - please check your connection.'
    } else {
      errorMessage += 'Please try again or use the Download button below.'
    }

    showCopyFeedback.value = true
    copyFeedbackMessage.value = errorMessage
  } finally {
    generatingInstructions.value = false
  }
}

/**
 * Production-grade clipboard copy with fallback support
 */
async function copyToClipboard(text) {
  // Try Clipboard API first
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(text)
      console.log('[SLASH COMMAND SETUP] Text copied via Clipboard API')
      return
    } catch (error) {
      console.warn('[SLASH COMMAND SETUP] Clipboard API failed, using fallback:', error)
    }
  }

  // Fallback method
  const success = fallbackCopyToClipboard(text)
  if (!success) {
    throw new Error('All copy methods failed')
  }
  console.log('[SLASH COMMAND SETUP] Text copied via fallback')
}

async function downloadSlashCommands() {
  try {
    downloading.value = true
    const response = await fetch('/api/download/slash-commands.zip', {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
      },
    })

    if (!response.ok) {
      throw new Error(`Download failed with status ${response.status}`)
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'slash-commands.zip'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    showCopyFeedback.value = true
    copyFeedbackMessage.value = 'Slash commands downloaded successfully!'
    console.log('[SLASH COMMAND SETUP] Download successful')
  } catch (error) {
    console.error('[SLASH COMMAND SETUP] Failed to download slash commands:', error)
    showCopyFeedback.value = true
    copyFeedbackMessage.value = `Download failed: ${error.message}`
  } finally {
    downloading.value = false
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
