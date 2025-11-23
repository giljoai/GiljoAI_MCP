<template>
  <v-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    max-width="800"
    scrollable
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start color="success">mdi-sparkles</v-icon>
        How to Configure Gemini CLI
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
              Add the following to your Gemini CLI settings file. See
              <a
                href="https://github.com/google-gemini/gemini-cli"
                target="_blank"
                class="text-primary"
                >Gemini CLI Documentation</a
              >
              for complete setup instructions.
            </p>

            <v-alert type="info" variant="tonal" class="mb-3" density="compact">
              <v-icon start size="small">mdi-file-document</v-icon>
              <strong>Configuration File Location:</strong>
              <br />- All platforms: <code>~/.gemini/settings.json</code>
            </v-alert>

            <v-card variant="outlined" class="mb-3">
              <v-card-text>
                <pre class="text-caption"><code>{
  "mcpServers": {
    "giljo-mcp": {
      "url": "http://your-server-ip:7272",
      "apiKey": "{your-api-key-here}",
      "description": "GiljoAI Agent Orchestration MCP Server",
      "capabilities": [
        "agent_coordination",
        "context_sharing",
        "memory_persistence"
      ]
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

            <v-btn variant="outlined" color="success" @click="downloadInstructions">
              <v-icon start>mdi-download</v-icon>
              Download Gemini CLI Setup Guide
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
  const config = `{
  "mcpServers": {
    "giljo-mcp": {
      "url": "http://your-server-ip:7272",
      "apiKey": "{your-api-key-here}",
      "description": "GiljoAI Agent Orchestration MCP Server",
      "capabilities": [
        "agent_coordination",
        "context_sharing",
        "memory_persistence"
      ]
    }
  }
}`
  navigator.clipboard.writeText(config)
  console.log('[INTEGRATIONS] Gemini configuration copied to clipboard')
}

const downloadInstructions = () => {
  const instructions = `# Gemini CLI Setup Guide for GiljoAI MCP Server

## Prerequisites
1. Generate an API key from your user profile in GiljoAI dashboard
2. Install Gemini CLI following official instructions
3. Ensure Gemini CLI is properly configured

## Installation
Install Gemini CLI using one of these methods:
- NPX: npx https://github.com/google-gemini/gemini-cli
- NPM global: npm install -g @google/gemini-cli
- Homebrew: brew install gemini-cli

## Configuration
**Configuration File Location:**
- All platforms: ~/.gemini/settings.json

**Documentation:**
- Gemini CLI: https://github.com/google-gemini/gemini-cli

Add to your Gemini CLI settings.json file:

{
  "mcpServers": {
    "giljo-mcp": {
      "url": "http://your-server-ip:7272",
      "apiKey": "YOUR_API_KEY_HERE",
      "description": "GiljoAI Agent Orchestration MCP Server",
      "capabilities": [
        "agent_coordination",
        "context_sharing",
        "memory_persistence"
      ]
    }
  }
}

## Sub-Agent Workflow
1. Gemini CLI spawns specialized sub-agents for different tasks
2. GiljoAI MCP coordinates agent state and memory
3. Enhanced reasoning with multi-modal capabilities
4. Context sharing enables seamless handoffs
5. context prioritization and orchestration through intelligent coordination

## Multi-Modal Features
- Code analysis with visual diagrams
- Image processing for UI development
- Document analysis and generation
- Advanced reasoning capabilities

## Verification
- Restart Gemini CLI
- Verify GiljoAI MCP connection
- Test sub-agent coordination
- Validate multi-modal capabilities

## Support
Visit your GiljoAI dashboard for additional configuration help.`

  const blob = new Blob([instructions], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'gemini-cli-giljo-mcp-setup.txt'
  a.click()
  URL.revokeObjectURL(url)
  console.log('[INTEGRATIONS] Gemini setup instructions downloaded')
}
</script>
