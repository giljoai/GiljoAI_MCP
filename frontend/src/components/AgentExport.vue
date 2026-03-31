<template>
  <v-card variant="flat" class="mb-4 smooth-border">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-icon size="28" class="mr-2" color="primary">mdi-export</v-icon>
        <h3 class="text-h6 mb-0 mr-2">Skills, Commands and Agents Export</h3>
        <v-tooltip location="top" max-width="400">
          <template #activator="{ props }">
            <v-icon v-bind="props" size="small" color="medium-emphasis">mdi-help-circle-outline</v-icon>
          </template>
          <span>Generates a combined bootstrap prompt that installs slash commands and agent templates in one step. Paste into your AI coding agent.</span>
        </v-tooltip>
      </div>

      <div class="mb-5">
        <p class="text-body-2 text-muted-a11y mb-4">
          Generate a setup prompt for your AI coding agents.
        </p>

        <v-card variant="tonal" class="mb-0">
          <v-card-text class="pa-3">
            <div class="d-flex flex-wrap justify-center" style="gap: 25px;">
              <div v-for="p in platforms" :key="p.id" class="d-flex align-center gap-2">
                <button
                  class="export-pill"
                  :class="{ 'export-pill--loading': setupLoading[p.id] }"
                  :disabled="setupLoading[p.id]"
                  :data-testid="`setup-${p.id}`"
                  @click="generateBootstrapPrompt(p.id)"
                >
                  <v-avatar size="20" rounded="0" class="mr-1">
                    <v-img :src="p.icon" :alt="p.label" />
                  </v-avatar>
                  <span>{{ p.buttonLabel }}</span>
                  <v-progress-circular
                    v-if="setupLoading[p.id]"
                    size="14"
                    width="2"
                    indeterminate
                    class="ml-1"
                  />
                </button>
                <v-tooltip v-if="p.experimental" location="top">
                  <template #activator="{ props: ttProps }">
                    <v-icon v-bind="ttProps" size="small" color="warning">mdi-alert</v-icon>
                  </template>
                  <span>Experimental — limited testing. Use with caution.</span>
                </v-tooltip>
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
              <span class="text-caption text-muted-a11y ml-2">(advanced)</span>
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
          <code>/gil_add</code> to create tasks and projects from your AI coding agent.
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
 * Copy text to clipboard using shared composable.
 */
import { useClipboard } from '@/composables/useClipboard'
const { copy: clipboardCopy } = useClipboard()

async function copyToClipboard(text) {
  const ok = await clipboardCopy(text)
  if (!ok) throw new Error('Clipboard copy failed — click the button again')
  return true
}

// Platform definitions
const platforms = [
  { id: 'claude_code', label: 'Claude Code', buttonLabel: 'Claude Prompt', icon: '/claude_pix.svg', color: 'deep-orange', experimental: false },
  { id: 'codex_cli', label: 'Codex CLI', buttonLabel: 'Codex Prompt', icon: '/codex_logo.svg', color: 'green', experimental: true },
  { id: 'gemini_cli', label: 'Gemini CLI', buttonLabel: 'Gemini Prompt', icon: '/gemini-icon.svg', color: 'blue', experimental: true },
]

// Loading states
const setupLoading = reactive({
  claude_code: false,
  codex_cli: false,
  gemini_cli: false,
})

const downloadLoading = reactive({})



/**
 * Generate the combined bootstrap prompt for a platform and copy to clipboard.
 */
async function generateBootstrapPrompt(platform) {
  setupLoading[platform] = true
  try {
    const response = await fetch(
      `/api/download/bootstrap-prompt?platform=${platform}`,
      {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
      },
    )
    if (!response.ok) {
      throw new Error(`Bootstrap prompt generation failed: ${response.status}`)
    }
    const data = await response.json()

    await copyToClipboard(data.prompt)
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

.manual-downloads-title {
  padding: 8px 0 !important;
  min-height: unset !important;
}

.export-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  padding: 6px 16px;
  font-size: 0.78rem;
  font-weight: 500;
  background: rgba(255, 195, 0, 0.12);
  color: #ffc300;
  border: none;
  cursor: pointer;
  transition: background 0.15s, opacity 0.15s;
  white-space: nowrap;
}

.export-pill:hover {
  background: rgba(255, 195, 0, 0.2);
}

.export-pill--loading {
  opacity: 0.7;
  cursor: wait;
}

.export-pill:disabled {
  cursor: wait;
}
</style>
