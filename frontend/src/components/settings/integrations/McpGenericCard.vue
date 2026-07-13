<template>
  <div class="intg-line smooth-border" style="--card-accent: rgba(255,255,255,0.32)">
    <div class="intg-line-icon intg-line-icon--mcp">
      <v-img class="mcp-logo-white" src="/logo-mcp.svg" alt="MCP" width="24" height="24" />
    </div>

    <div class="intg-line-main">
      <div class="intg-line-title-row">
        <span class="intg-line-title">MCP Generic</span>
        <v-tooltip location="top" max-width="360">
          <template #activator="{ props }">
            <v-icon v-bind="props" size="small" style="color: var(--text-muted)">mdi-help-circle-outline</v-icon>
          </template>
          <div>
            Due to the wide variety of MCP-compatible coding tools available, we provide
            <strong>generic</strong> agent templates and slash-command files for manual installation.
            <br /><br />
            These need adapting to your specific platform — refer to your tool's documentation for
            where to place agent definitions and slash commands.
          </div>
        </v-tooltip>
      </div>
      <div class="intg-line-sub">Tools for manual agent and skill import.</div>
    </div>

    <div class="intg-line-action">
      <v-btn
        variant="text"
        size="small"
        color="light-blue"
        class="intg-card-sublink"
        @click="expanded = !expanded"
      >
        <v-icon start size="small">mdi-download</v-icon>
        Downloads
        <v-icon end size="small">{{ expanded ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
      </v-btn>
      <v-expand-transition>
        <div v-if="expanded" class="d-flex flex-column align-end" style="gap: 4px;">
          <v-btn
            variant="text"
            size="small"
            color="grey-lighten-1"
            class="mcp-dl-btn"
            :loading="downloadLoading.agents"
            @click="downloadZip('agent_templates')"
          >
            <v-icon start size="small">mdi-file-download-outline</v-icon>
            Agent Templates
          </v-btn>
          <v-btn
            variant="text"
            size="small"
            color="grey-lighten-1"
            class="mcp-dl-btn"
            :loading="downloadLoading.slash"
            @click="downloadZip('slash_commands')"
          >
            <v-icon start size="small">mdi-file-download-outline</v-icon>
            Slash Commands / Skills
          </v-btn>
        </div>
      </v-expand-transition>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useToast } from '@/composables/useToast'

const { showToast } = useToast()

const expanded = ref(false)
const downloadLoading = reactive({ agents: false, slash: false })

// Generic platform only — Claude/Codex/Gemini users run giljo_setup instead.
async function downloadZip(contentType) {
  const key = contentType === 'slash_commands' ? 'slash' : 'agents'
  downloadLoading[key] = true
  try {
    const endpoint =
      contentType === 'slash_commands'
        ? '/api/download/slash-commands.zip?platform=generic'
        : '/api/download/agent-templates.zip?active_only=true&platform=generic'

    const response = await fetch(endpoint, {
      headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
    })
    if (!response.ok) {
      throw new Error(`Download failed with status ${response.status}`)
    }

    const blob = await response.blob()
    const filename =
      contentType === 'slash_commands'
        ? 'slash-commands-generic.zip'
        : 'agent-templates-generic.zip'

    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    showToast({
      message: 'Generic bundle downloaded. Unzip and adapt it to your MCP-compatible tool.',
      type: 'success',
    })
  } catch (error) {
    console.error('[MCP GENERIC] Download failed:', error)
    showToast({ message: `Download failed: ${error.message}`, type: 'error' })
  } finally {
    downloadLoading[key] = false
  }
}
</script>

<style lang="scss" scoped>
@use '../../../styles/intg-card';

/* White "inactive" nuance — icon and fade behind it */
.intg-line-icon--mcp {
  background: rgba(255, 255, 255, 0.08);
}

.mcp-logo-white {
  filter: brightness(0) invert(1);
  opacity: 0.85;
}

.mcp-dl-btn {
  text-transform: none;
  font-weight: 500;
  letter-spacing: normal;
}
</style>
