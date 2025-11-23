<template>
  <v-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    max-width="800"
    scrollable
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start color="secondary">mdi-code-braces</v-icon>
        How to Configure Codex CLI
      </v-card-title>

      <v-card-text>
        <v-alert type="info" variant="tonal" class="mb-4">
          <v-icon start>mdi-information</v-icon>
          First, generate an API key under your User Profile -> Settings -> API and Integrations
        </v-alert>

        <v-tabs v-model="activeTab" class="mb-4">
          <v-tab value="manual">Manual Configuration</v-tab>
          <v-tab value="download">Download Instructions</v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
          <!-- Manual Configuration -->
          <v-window-item value="manual">
            <h3 class="text-h6 mb-3">Manual Configuration</h3>
            <p class="text-body-2 mb-3">
              Add the following to your Codex CLI configuration file. See
              <a
                href="https://developers.openai.com/codex/local-config#cli"
                target="_blank"
                class="text-primary"
                >Codex CLI Configuration</a
              >
              and
              <a href="https://developers.openai.com/codex/mcp" target="_blank" class="text-primary"
                >Codex MCP Documentation</a
              >
              for complete setup instructions.
            </p>

            <v-alert type="info" variant="tonal" class="mb-3" density="compact">
              <v-icon start size="small">mdi-file-document</v-icon>
              <strong>Configuration File Location:</strong>
              <br />- macOS/Linux: <code>~/.codex/config.toml</code> <br />- Windows:
              <code>%USERPROFILE%\.codex\config.toml</code>
            </v-alert>

            <v-card variant="outlined" class="mb-3">
              <v-card-text>
                <pre class="text-caption"><code>[giljo-mcp]
endpoint = "http://your-server-ip:7272"
api_key = "{your-api-key-here}"
description = "GiljoAI Agent Orchestration MCP Server"

[agents]
orchestrator_enabled = true
subagent_coordination = true
context_sharing = true</code></pre>
              </v-card-text>
              <v-card-actions>
                <v-btn
                  variant="text"
                  size="small"
                  data-test="copy-config-button"
                  @click="copyConfig"
                >
                  <v-icon start>mdi-content-copy</v-icon>
                  Copy Configuration
                </v-btn>
              </v-card-actions>
            </v-card>

            <p class="text-body-2">
              Replace <code>{your-api-key-here}</code> with your actual API key from your user
              profile.
            </p>
          </v-window-item>

          <!-- Download Instructions -->
          <v-window-item value="download">
            <h3 class="text-h6 mb-3">Download Configuration Instructions</h3>
            <p class="text-body-2 mb-3">
              Download a complete setup guide with your server-specific configuration:
            </p>

            <v-btn variant="outlined" color="secondary" @click="downloadInstructions">
              <v-icon start>mdi-download</v-icon>
              Download Codex CLI Setup Guide
            </v-btn>
          </v-window-item>
        </v-window>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" data-test="close-button" @click="$emit('update:modelValue', false)"
          >Close</v-btn
        >
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

const activeTab = ref('manual')

const copyConfig = () => {
  const config = `[giljo-mcp]
endpoint = "http://your-server-ip:7272"
api_key = "{your-api-key-here}"
description = "GiljoAI Agent Orchestration MCP Server"

[agents]
orchestrator_enabled = true
subagent_coordination = true
context_sharing = true`
  navigator.clipboard.writeText(config)
  console.log('[INTEGRATIONS] Codex configuration copied to clipboard')
}

const downloadInstructions = () => {
  const instructions = `# Codex CLI Setup Guide for GiljoAI MCP Server

## Prerequisites
1. Generate an API key from your user profile in GiljoAI dashboard
2. Ensure Codex CLI is installed and configured

## Configuration
**Configuration File Location:**
- macOS/Linux: ~/.codex/config.toml
- Windows: %USERPROFILE%\\.codex\\config.toml

**Documentation:**
- MCP Integration: https://developers.openai.com/codex/mcp
- CLI Configuration: https://developers.openai.com/codex/local-config#cli

Add to your Codex CLI configuration file:

[giljo-mcp]
endpoint = "http://your-server-ip:7272"
api_key = "YOUR_API_KEY_HERE"
description = "GiljoAI Agent Orchestration MCP Server"

[agents]
orchestrator_enabled = true
subagent_coordination = true
context_sharing = true

## Sub-Agent Workflow
1. Codex spawns specialized sub-agents for different tasks
2. GiljoAI MCP coordinates agent state and memory
3. Context sharing enables seamless handoffs
4. context prioritization and orchestration through intelligent coordination

## Verification
- Restart Codex CLI
- Verify GiljoAI MCP connection
- Test sub-agent coordination

## Support
Visit your GiljoAI dashboard for additional configuration help.`

  const blob = new Blob([instructions], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'codex-cli-giljo-mcp-setup.txt'
  a.click()
  URL.revokeObjectURL(url)
  console.log('[INTEGRATIONS] Codex setup instructions downloaded')
}
</script>
