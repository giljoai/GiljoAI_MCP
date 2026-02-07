<template>
  <v-dialog
    :model-value="modelValue"
    max-width="800"
    scrollable
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start color="primary">mdi-robot-outline</v-icon>
        How to Configure Claude Code
      </v-card-title>

      <v-card-text>
        <v-alert type="info" variant="tonal" class="mb-4">
          <v-icon start>mdi-information</v-icon>
          First, generate an API key under your User Profile -> Settings -> API and Integrations
        </v-alert>

        <v-tabs v-model="activeTab" class="mb-4">
          <v-tab value="marketplace">Marketplace Configuration</v-tab>
          <v-tab value="manual">Manual Configuration</v-tab>
          <v-tab value="download">Download Instructions</v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
          <!-- Marketplace Configuration -->
          <v-window-item value="marketplace">
            <h3 class="text-h6 mb-3">Claude Code Marketplace Configuration</h3>
            <ol class="text-body-2 mb-3">
              <li class="mb-2">Open Claude Code and navigate to the MCP Tools Marketplace</li>
              <li class="mb-2">Search for "GiljoAI Agent Orchestration MCP Server"</li>
              <li class="mb-2">Click "Install" and follow the marketplace prompts</li>
              <li class="mb-2">
                When prompted for the API endpoint, enter: <code>http://your-server-ip:7272</code>
              </li>
              <li class="mb-2">Enter your API key from your user profile</li>
              <li class="mb-2">Test the connection and confirm installation</li>
            </ol>
          </v-window-item>

          <!-- Manual Configuration -->
          <v-window-item value="manual">
            <h3 class="text-h6 mb-3">Manual Configuration</h3>
            <p class="text-body-2 mb-3">
              Add the following to your Claude Code MCP configuration file. See
              <a
                href="https://docs.claude.com/en/docs/claude-code/mcp"
                target="_blank"
                class="text-primary"
                >Claude Code MCP Documentation</a
              >
              for complete setup instructions.
            </p>

            <v-alert type="info" variant="tonal" class="mb-3" density="compact">
              <v-icon start size="small">mdi-file-document</v-icon>
              <strong>Configuration File Location:</strong>
              <br />- macOS/Linux: <code>~/.claude.json</code> <br />- Windows:
              <code>%USERPROFILE%\.claude.json</code>
            </v-alert>

            <v-card variant="outlined" class="mb-3">
              <v-card-text>
                <pre class="text-caption"><code>{
  "servers": {
    "giljo-mcp": {
      "command": "mcp-client",
      "args": [
        "--server-url", "http://your-server-ip:7272",
        "--api-key", "{your-api-key-here}"
      ],
      "description": "GiljoAI Agent Orchestration MCP Server"
    }
  }
}</code></pre>
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

            <v-btn variant="outlined" color="primary" @click="downloadInstructions">
              <v-icon start>mdi-download</v-icon>
              Download Claude Code Setup Guide
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

const activeTab = ref('marketplace')

const copyConfig = () => {
  const config = `{
  "servers": {
    "giljo-mcp": {
      "command": "mcp-client",
      "args": [
        "--server-url", "http://your-server-ip:7272",
        "--api-key", "{your-api-key-here}"
      ],
      "description": "GiljoAI Agent Orchestration MCP Server"
    }
  }
}`
  navigator.clipboard.writeText(config)
  console.log('[INTEGRATIONS] Claude configuration copied to clipboard')
}

const downloadInstructions = () => {
  const instructions = `# Claude Code Setup Guide for GiljoAI MCP Server

## Prerequisites
1. Generate an API key from your user profile in GiljoAI dashboard
2. Ensure Claude Code is installed and configured

## Marketplace Configuration (Recommended)
1. Open Claude Code
2. Navigate to MCP Tools Marketplace
3. Search for "GiljoAI Agent Orchestration MCP Server"
4. Click "Install"
5. Enter endpoint: http://your-server-ip:7272
6. Enter your API key
7. Test connection

## Manual Configuration

**Configuration File Location:**
- macOS/Linux: ~/.claude.json
- Windows: %USERPROFILE%\\.claude.json

**Documentation:** https://docs.claude.com/en/docs/claude-code/mcp

Add the following to your Claude Code MCP configuration file:

{
  "servers": {
    "giljo-mcp": {
      "command": "mcp-client",
      "args": [
        "--server-url", "http://your-server-ip:7272",
        "--api-key", "YOUR_API_KEY_HERE"
      ],
      "description": "GiljoAI Agent Orchestration MCP Server"
    }
  }
}

## Verification
- Restart Claude Code
- Verify GiljoAI MCP tools are available
- Test agent coordination functionality

## Support
Visit your GiljoAI dashboard for additional configuration help.`

  const blob = new Blob([instructions], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'claude-code-giljo-mcp-setup.txt'
  a.click()
  URL.revokeObjectURL(url)
  console.log('[INTEGRATIONS] Claude setup instructions downloaded')
}
</script>
