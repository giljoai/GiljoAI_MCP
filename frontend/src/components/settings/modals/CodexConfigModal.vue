<template>
  <v-dialog
    :model-value="modelValue"
    max-width="800"
    scrollable
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card v-draggable>
      <v-card-title class="d-flex align-center">
        <v-icon start color="secondary">mdi-code-braces</v-icon>
        How to Configure Codex CLI
      </v-card-title>

      <v-card-text>
        <v-alert type="info" variant="tonal" class="mb-4">
          <v-icon start>mdi-information</v-icon>
          First, generate an API key under your User Profile -> Settings -> API and Integrations, then set it as environment variable <code>GILJO_API_KEY</code>
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
                <pre class="text-caption"><code>codex mcp add giljo-mcp --url http://your-server-ip:7272/mcp --bearer-token-env-var GILJO_API_KEY</code></pre>
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
              Replace <code>your-api-key-here</code> with your actual API key from your user
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
import { useClipboard } from '@/composables/useClipboard'

const { copy: clipboardCopy } = useClipboard()

defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

const activeTab = ref('manual')

const copyConfig = () => {
  const config = `codex mcp add giljo-mcp --url http://your-server-ip:7272/mcp --bearer-token-env-var GILJO_API_KEY`
  clipboardCopy(config)
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

Set environment variable GILJO_API_KEY to your API key, then run:

codex mcp add giljo-mcp --url http://your-server-ip:7272/mcp --bearer-token-env-var GILJO_API_KEY

## Verification
- Verify GiljoAI MCP connection with: codex mcp list

## Support
Visit your GiljoAI dashboard for additional configuration help.`

  const blob = new Blob([instructions], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'codex-cli-giljo-mcp-setup.txt'
  a.click()
  URL.revokeObjectURL(url)
}
</script>
