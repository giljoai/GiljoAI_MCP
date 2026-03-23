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
            <strong>Core commands:</strong>
            <ul class="mt-2 mb-2 pl-4">
              <li>/gil_get_agents - Download + install agent templates</li>
              <li>/gil_add - Add tasks or projects to the dashboard</li>
            </ul>
            <p class="text-caption mb-0">
              <em>*Available as slash commands (Claude), custom commands (Gemini), or skills (Codex)</em>
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

  </v-card>
</template>

<script setup>
import { ref } from 'vue'
import api from '@/services/api'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'

const { copy: clipboardCopy } = useClipboard()
const { showToast } = useToast()

// State
const copied = ref(false)
const downloading = ref(false)
const generatingInstructions = ref(false)


/**
 * Generate natural language installation instructions with download token
 * and copy to clipboard.
 */
async function copySlashCommandSetup() {
  try {
    generatingInstructions.value = true

    // Call backend to generate timed download URL
    const response = await api.downloads.generateSlashCommandsInstructions()
    const downloadUrl = response.data.download_url

    if (!downloadUrl) {
      throw new Error('No download URL received from server')
    }

    // Construct agent-friendly installation prompt (platform-agnostic)
    const installPrompt = [
      'Download and install the GiljoAI slash commands (/gil_get_claude_agents and /gil_add) from the GiljoAI MCP server.',
      '',
      `Download URL: ${downloadUrl}`,
      'Target directory: ~/.claude/commands/',
      '',
      'Steps:',
      '1. Download the zip file from the URL above.',
      '2. Extract its contents into ~/.claude/commands/ (overwrite existing files).',
      '3. Delete the downloaded zip file.',
      'Adapt the commands for the OS platform you are currently running on.',
      '',
      'After installation is complete, instruct the user to restart Claude Code for the new commands to take effect.',
    ].join('\n')

    // Copy install prompt to clipboard
    await copyToClipboard(installPrompt)

    copied.value = true
    showToast({ message: 'Installation command copied to clipboard!', type: 'success' })

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

    showToast({ message: errorMessage, type: 'error' })
  } finally {
    generatingInstructions.value = false
  }
}

/**
 * Copy text to clipboard using shared composable
 */
async function copyToClipboard(text) {
  const success = await clipboardCopy(text)
  if (!success) {
    throw new Error('All copy methods failed')
  }
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

    showToast({ message: 'Slash commands downloaded successfully!', type: 'success' })
  } catch (error) {
    console.error('[SLASH COMMAND SETUP] Failed to download slash commands:', error)
    showToast({ message: `Download failed: ${error.message}`, type: 'error' })
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
