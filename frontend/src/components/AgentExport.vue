<template>
  <div
    class="intg-card smooth-border"
    style="--card-accent: var(--agent-documenter-primary)"
  >
    <div class="intg-card-icon" style="background: rgba(255,195,0,0.1); color: var(--color-accent-primary)">
      <v-icon size="20">mdi-export</v-icon>
    </div>
    <div class="d-flex align-center" style="gap: 8px; margin-bottom: 5px;">
      <div class="intg-card-title" style="margin-bottom: 0">Skills and Agents Export</div>
      <v-tooltip location="top" max-width="400">
        <template #activator="{ props }">
          <v-icon v-bind="props" size="small" style="color: var(--text-muted)">mdi-help-circle-outline</v-icon>
        </template>
        <div>
          Once the MCP server is registered in your AI coding tool, run <code>giljo_setup</code> to install agents and skills in one step.
          <br /><br />
          After setup, use <code>/gil_get_agents</code> to update agent templates and
          <code>/gil_add</code> to create tasks and projects from your AI coding agent.
        </div>
      </v-tooltip>
    </div>
    <div class="intg-card-body">
      <div class="d-flex align-center flex-wrap justify-center" style="gap: 8px; margin-bottom: 12px;">
        <span class="intg-card-desc" style="margin-bottom: 0">run</span>
        <span class="setup-cmd">giljo_setup</span>
        <span class="intg-card-desc" style="margin-bottom: 0">or</span>
        <div v-for="p in platforms" :key="p.id">
          <v-tooltip location="top">
            <template #activator="{ props: btnProps }">
              <button
                v-bind="btnProps"
                class="export-icon-btn smooth-border"
                :class="{ 'export-icon-btn--loading': setupLoading[p.id] }"
                :disabled="setupLoading[p.id]"
                :data-testid="`setup-${p.id}`"
                @click="generateBootstrapPrompt(p.id)"
              >
                <v-progress-circular
                  v-if="setupLoading[p.id]"
                  size="18"
                  width="2"
                  indeterminate
                />
                <v-avatar v-else size="24" rounded="0">
                  <v-img :src="p.icon" :alt="p.label" />
                </v-avatar>
              </button>
            </template>
            <span>{{ p.label }}{{ p.experimental ? ' (experimental)' : '' }}</span>
          </v-tooltip>
        </div>
      </div>

      <!-- Manual Downloads (collapsed) -->
      <v-expansion-panels variant="accordion">
        <v-expansion-panel>
          <v-expansion-panel-title class="manual-downloads-title">
            <div class="d-flex align-center text-light-blue" style="font-size: 0.8125rem;">
              <v-icon start size="small">mdi-download</v-icon>
              Manual Downloads
              <span class="text-caption ml-2" style="color: var(--text-muted)">(advanced)</span>
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
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { useToast } from '@/composables/useToast'
import { useClipboard } from '@/composables/useClipboard'

const { showToast } = useToast()
const { copy: clipboardCopy } = useClipboard()

async function copyToClipboard(text) {
  const ok = await clipboardCopy(text)
  if (!ok) throw new Error('Clipboard copy failed — click the button again')
  return true
}

const platforms = [
  { id: 'claude_code', label: 'Claude Code', buttonLabel: 'Claude Prompt', icon: '/claude_pix.svg', color: 'deep-orange', experimental: false },
  { id: 'codex_cli', label: 'Codex CLI', buttonLabel: 'Codex Prompt', icon: '/codex_logo.svg', color: 'green', experimental: true },
  { id: 'gemini_cli', label: 'Gemini CLI', buttonLabel: 'Gemini Prompt', icon: '/gemini-icon.svg', color: 'blue', experimental: true },
  { id: 'generic', label: 'Generic MCP', buttonLabel: 'Generic', icon: '/logo-mcp.svg', color: 'grey', experimental: false },
]

const setupLoading = reactive({
  claude_code: false,
  codex_cli: false,
  gemini_cli: false,
  generic: false,
})

const downloadLoading = reactive({})

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

    showToast({ message: 'Agent export downloaded successfully', type: 'success' })
  } catch (error) {
    console.error(`[AGENT EXPORT] Download failed:`, error)
    showToast({ message: `Download failed: ${error.message}`, type: 'error' })
  } finally {
    downloadLoading[key] = false
  }
}
</script>

<style lang="scss" scoped>
@use '../styles/design-tokens' as *;
@use '../styles/intg-card';

.gap-2 {
  gap: 8px;
}

.manual-downloads-title {
  padding: 8px 0 !important;
  min-height: unset !important;
}

.export-icon-btn {
  --smooth-border-color: #{$color-brand-yellow};
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: $border-radius-rounded;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background $transition-fast, opacity $transition-fast;
}

.export-icon-btn:hover {
  background: rgba(255, 195, 0, 0.12);
}

.export-icon-btn--loading {
  opacity: 0.7;
  cursor: wait;
}

.export-icon-btn:disabled {
  cursor: wait;
}

.setup-cmd {
  color: var(--brand-yellow, #ffc300);
  font-family: monospace;
  font-weight: 600;
  font-size: 0.875rem;
}
</style>
