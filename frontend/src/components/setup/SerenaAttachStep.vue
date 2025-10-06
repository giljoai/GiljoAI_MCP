<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-2">Serena MCP - Advanced Code Analysis (Optional)</h2>
    <p class="text-body-1 mb-6">
      Enhance your coding agents with semantic code tools
    </p>

    <!-- Main Card -->
    <v-card variant="outlined" class="serena-card">
      <v-card-text class="text-center">
        <v-icon size="64" color="primary" class="mb-4">mdi-code-braces-box</v-icon>

        <h3 class="text-h6 mb-3">Enable Serena Instructions?</h3>

        <p class="text-body-2 mb-4">
          When enabled, coding agents receive guidance on using Serena MCP tools
          for semantic code analysis and intelligent refactoring.
        </p>

        <v-alert type="info" variant="tonal" class="text-left mb-4">
          <div class="d-flex align-center">
            <v-icon start>mdi-information</v-icon>
            <div>
              <strong>Installation Required:</strong> Serena must be installed in your coding tool
              separately.
              <v-btn
                variant="text"
                size="small"
                color="primary"
                @click="showInstallGuide = true"
                class="ml-2"
              >
                Installation Guide
              </v-btn>
            </div>
          </div>
        </v-alert>

        <!-- Simple Choice -->
        <v-radio-group v-model="choice" class="mt-4">
          <v-radio
            label="Yes, enable Serena instructions in agent prompts"
            value="enabled"
            color="primary"
          />
          <v-radio
            label="No, skip Serena (can enable later in Settings)"
            value="disabled"
            color="primary"
          />
        </v-radio-group>
      </v-card-text>
    </v-card>

    <!-- Progress Indicator -->
    <v-card variant="outlined" class="mt-6 mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 2 of 4</span>
          <span class="text-caption">50%</span>
        </div>
        <v-progress-linear :model-value="50" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <div class="d-flex justify-space-between">
      <v-btn variant="text" @click="$emit('back')">
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <v-btn color="primary" @click="handleNext">
        Continue
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>

    <!-- Installation Guide Dialog -->
    <v-dialog v-model="showInstallGuide" max-width="700">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start color="primary">mdi-book-open-variant</v-icon>
          Install Serena MCP
        </v-card-title>

        <v-card-text>
          <v-tabs v-model="installTab">
            <v-tab value="uvx">Using uvx (Recommended)</v-tab>
            <v-tab value="local">Local Installation</v-tab>
          </v-tabs>

          <v-tabs-window v-model="installTab" class="mt-4">
            <v-tabs-window-item value="uvx">
              <h4 class="text-h6 mb-3">Install with uvx</h4>

              <p class="mb-3">
                The simplest method - uvx automatically manages the installation:
              </p>

              <v-code class="mb-3">
uvx --from git+https://github.com/oraios/serena serena
              </v-code>

              <h4 class="text-h6 mt-4 mb-3">Configure in Claude Code</h4>

              <p class="mb-2">Edit <code>~/.claude.json</code>:</p>

              <v-code>
{
  "mcpServers": {
    "serena": {
      "command": "uvx",
      "args": ["serena"]
    }
  }
}
              </v-code>
            </v-tabs-window-item>

            <v-tabs-window-item value="local">
              <h4 class="text-h6 mb-3">Local Installation</h4>

              <p class="mb-3">Clone and run locally:</p>

              <v-code class="mb-3">
git clone https://github.com/oraios/serena
cd serena
uv run serena start-mcp-server
              </v-code>

              <h4 class="text-h6 mt-4 mb-3">Configure in Claude Code</h4>

              <p class="mb-2">Edit <code>~/.claude.json</code>:</p>

              <v-code>
{
  "mcpServers": {
    "serena": {
      "command": "path/to/serena/venv/bin/python",
      "args": ["-m", "serena"]
    }
  }
}
              </v-code>
            </v-tabs-window-item>
          </v-tabs-window>

          <v-alert type="success" variant="tonal" class="mt-4">
            <v-icon start>mdi-check-circle</v-icon>
            After installation, restart Claude Code and verify with <code>/mcp</code>
          </v-alert>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn @click="showInstallGuide = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card-text>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['next', 'back'])

// Simple state
const choice = ref('disabled')
const showInstallGuide = ref(false)
const installTab = ref('uvx')

// Simple handler - just emit choice
const handleNext = () => {
  emit('next', {
    serenaEnabled: choice.value === 'enabled'
  })
}
</script>

<style scoped>
h2 {
  color: rgb(var(--v-theme-primary));
}

.serena-card {
  transition: all 0.2s ease;
  border-width: 2px;
}

.serena-card:hover {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

v-code {
  display: block;
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 12px;
  border-radius: 8px;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  white-space: pre-wrap;
  overflow-x: auto;
}

code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}
</style>
