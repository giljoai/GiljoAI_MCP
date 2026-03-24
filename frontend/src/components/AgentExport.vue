<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-icon size="28" class="mr-2" color="primary">mdi-export</v-icon>
        <h3 class="text-h6 mb-0 mr-2">Skills, Commands and Agents Export</h3>
        <v-tooltip location="top" max-width="400">
          <template #activator="{ props }">
            <v-icon v-bind="props" size="small" color="medium-emphasis">mdi-help-circle-outline</v-icon>
          </template>
          <span>Generates a combined bootstrap prompt that installs slash commands and agent templates in one step. Paste into your CLI tool.</span>
        </v-tooltip>
      </div>

      <div class="mb-5">
        <p class="text-body-2 text-medium-emphasis mb-4">
          Generate a setup prompt for your AI coding agents.
        </p>

        <v-card variant="tonal" class="mb-0">
          <v-card-text class="pa-3">
            <div class="d-flex flex-wrap justify-center" style="gap: 25px;">
              <div v-for="p in platforms" :key="p.id" class="d-flex align-center gap-2">
                <v-avatar size="24" rounded="0">
                  <v-img :src="p.icon" :alt="p.label" />
                </v-avatar>
                <v-btn
                  variant="flat"
                  color="primary"
                  :loading="setupLoading[p.id]"
                  :disabled="setupLoading[p.id]"
                  :data-testid="`setup-${p.id}`"
                  @click="generateBootstrapPrompt(p.id)"
                >
                  {{ p.buttonLabel }}
                </v-btn>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </div>

      <!-- Section 2: Manual Downloads (collapsed) -->
      <v-expansion-panels variant="accordion" class="mb-4">
        <v-expansion-panel>
          <v-expansion-panel-title class="manual-downloads-title">
            <div class="d-flex align-center text-light-blue" style="font-size: 0.8125rem;">
              <v-icon start size="small">mdi-download</v-icon>
              Manual Downloads
              <span class="text-caption text-medium-emphasis ml-2">(advanced)</span>
            </div>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <!-- Agent Templates -->
            <div class="mb-3">
              <div class="text-subtitle-2 mb-2">Agent Templates</div>
              <div class="d-flex flex-wrap gap-2">
                <v-btn
                  v-for="p in platforms"
                  :key="`agent-${p.id}`"
                  variant="text"
                  size="small"
                  :loading="downloadLoading[`agents_${p.id}`]"
                  @click="downloadZip('agent_templates', p.id)"
                >
                  <v-avatar size="18" rounded="0" class="mr-1">
                    <v-img :src="p.icon" :alt="p.label" />
                  </v-avatar>
                  {{ p.label }}
                </v-btn>
              </div>
            </div>

            <!-- Slash Commands -->
            <div>
              <div class="text-subtitle-2 mb-2">Slash Commands / Skills</div>
              <div class="d-flex flex-wrap gap-2">
                <v-btn
                  v-for="p in platforms"
                  :key="`slash-${p.id}`"
                  variant="text"
                  size="small"
                  :loading="downloadLoading[`slash_${p.id}`]"
                  @click="downloadZip('slash_commands', p.id)"
                >
                  <v-avatar size="18" rounded="0" class="mr-1">
                    <v-img :src="p.icon" :alt="p.label" />
                  </v-avatar>
                  {{ p.label }}
                </v-btn>
              </div>
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <!-- Section 3: After Setup -->
      <v-alert type="info" variant="tonal" density="compact">
        <div class="text-body-2">
          After setup, use <code>/gil_get_agents</code> to update agent templates and
          <code>/gil_add</code> to create tasks and projects from your CLI tool.
        </div>
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { reactive } from 'vue'
import { useToast } from '@/composables/useToast'

const { showToast } = useToast()

/**
 * Copy text to clipboard. Tries Clipboard API first, falls back to textarea.
 * Both methods can fail on first click (gesture expired after async token fetches),
 * so errors are caught and re-thrown with a clear message.
 */
async function copyToClipboard(text) {
  // Try Clipboard API first
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // Clipboard API rejected (gesture expired, no focus, permission denied) — fall through
    }
  }
  // Fallback: hidden textarea + execCommand
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.left = '-999999px'
  document.body.appendChild(ta)
  ta.focus()
  ta.select()
  const ok = document.execCommand('copy')
  document.body.removeChild(ta)
  if (!ok) throw new Error('Clipboard copy failed — click the button again')
  return true
}

// Platform definitions
const platforms = [
  { id: 'claude_code', label: 'Claude Code', buttonLabel: 'Claude Prompt', icon: '/claude_pix.svg', color: 'deep-orange' },
  { id: 'codex_cli', label: 'Codex CLI', buttonLabel: 'Codex Prompt', icon: '/codex_logo.svg', color: 'green' },
  { id: 'gemini_cli', label: 'Gemini CLI', buttonLabel: 'Gemini Prompt', icon: '/gemini-icon.svg', color: 'blue' },
]

// Bootstrap prompt templates (must match backend slash_command_templates.py)
const bootstrapTemplates = {
  claude_code: `Install the GiljoAI CLI integration. This is a one-time setup.

Step 1 — Install slash commands:
Download: {SLASH_COMMANDS_URL}
Extract to: ~/.claude/commands/ (create if needed, overwrite existing)
Delete the downloaded zip.

Adapt all commands for the OS you are running on.
After installation, instruct the user to restart Claude Code, then run /gil_get_agents to install agent templates.
Note: Download link expires in 15 minutes.`,

  gemini_cli: `Install the GiljoAI CLI integration. This is a one-time setup.

Step 1 — Install custom commands:
Download: {SLASH_COMMANDS_URL}
Extract to: ~/.gemini/commands/ (create if needed, overwrite existing)
Delete the downloaded zip.

Adapt all commands for the OS you are running on.
After installation, instruct the user to restart Gemini CLI, then run /gil_get_agents to install agent templates.
Note: Download link expires in 15 minutes.`,

  codex_cli: `Install the GiljoAI CLI integration. This is a one-time setup.

Step 1 — Install skills:
Download: {SKILLS_URL}
Extract to: ~/.codex/skills/ (create if needed, overwrite existing)
Delete the downloaded zip.

Adapt all commands for the OS you are running on.
After installation, instruct the user to restart Codex CLI, then run $gil-get-agents to install agent templates.
Note: Download link expires in 15 minutes.`,
}

// Loading states
const setupLoading = reactive({
  claude_code: false,
  codex_cli: false,
  gemini_cli: false,
})

const downloadLoading = reactive({})

/**
 * Generate a download token for a given content type and platform.
 * Returns the download_url from the server response.
 */
async function generateToken(contentType, platform) {
  const response = await fetch(
    `/api/download/generate-token?content_type=${contentType}&platform=${platform}`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
      },
    },
  )
  if (!response.ok) {
    throw new Error(`Token generation failed: ${response.status}`)
  }
  const data = await response.json()
  return data.download_url
}

/**
 * Generate the combined bootstrap prompt for a platform and copy to clipboard.
 */
async function generateBootstrapPrompt(platform) {
  setupLoading[platform] = true
  try {
    const template = bootstrapTemplates[platform]
    if (!template) throw new Error(`Unknown platform: ${platform}`)

    // Two-phase install: bootstrap only installs commands/skills.
    // Agent templates are installed later via the slash command/skill itself.
    const url = await generateToken('slash_commands', platform)
    const placeholder = platform === 'codex_cli' ? '{SKILLS_URL}' : '{SLASH_COMMANDS_URL}'
    const prompt = template.replace(placeholder, url)

    await copyToClipboard(prompt)
    const label = platforms.find((p) => p.id === platform)?.label || platform
    showToast({ message: `${label} setup prompt copied to clipboard`, type: 'success' })
  } catch (error) {
    console.error(`[AGENT EXPORT] Bootstrap prompt failed for ${platform}:`, error)
    showToast({ message: `Failed to generate setup prompt: ${error.message}`, type: 'error' })
  } finally {
    setupLoading[platform] = false
  }
}

/**
 * Download a ZIP file directly for a content type and platform.
 */
async function downloadZip(contentType, platform) {
  const key = `${contentType === 'slash_commands' ? 'slash' : 'agents'}_${platform}`
  downloadLoading[key] = true
  try {
    const endpoint =
      contentType === 'slash_commands'
        ? `/api/download/slash-commands.zip?platform=${platform}`
        : `/api/download/agent-templates.zip?active_only=true&platform=${platform}`

    const response = await fetch(endpoint, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
      },
    })

    if (!response.ok) {
      throw new Error(`Download failed with status ${response.status}`)
    }

    const blob = await response.blob()
    const filename =
      contentType === 'slash_commands'
        ? `slash-commands-${platform}.zip`
        : `agent-templates-${platform}.zip`

    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    showToast({ message: 'Download complete', type: 'success' })
  } catch (error) {
    console.error(`[AGENT EXPORT] Download failed:`, error)
    showToast({ message: `Download failed: ${error.message}`, type: 'error' })
  } finally {
    downloadLoading[key] = false
  }
}
</script>

<style scoped>
code {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875em;
}

.gap-2 {
  gap: 8px;
}

.gap-3 {
  gap: 12px;
}

.manual-downloads-title {
  padding: 8px 0 !important;
  min-height: unset !important;
}
</style>
