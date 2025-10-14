<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-2">Serena MCP - Advanced Code Analysis (Optional)</h2>
    <p class="text-body-1 mb-6">Enhance your coding agents with semantic code tools</p>

    <!-- What is Serena? Explanation -->
    <v-card variant="outlined" class="mb-4">
      <v-card-text>
        <div class="d-flex align-start">
          <v-img src="/Serena.png" alt="Serena MCP" max-width="64" class="mr-4" />
          <div class="flex-grow-1">
            <h3 class="text-h6 mb-2">What is Serena MCP?</h3>
            <p class="text-body-2 mb-3">
              Serena is an advanced Model Context Protocol server that enhances AI coding assistants
              with deep semantic code understanding and intelligent refactoring capabilities.
            </p>
          </div>
        </div>

        <!-- Benefits Expansion Panel -->
        <v-expansion-panels variant="accordion" class="mt-3">
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon start>mdi-feature-search</v-icon>
              <strong>Key Features & Benefits</strong>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-list density="compact" class="bg-transparent">
                <v-list-item>
                  <template #prepend>
                    <v-icon color="success">mdi-code-braces</v-icon>
                  </template>
                  <v-list-item-title>Symbol-level code understanding</v-list-item-title>
                  <v-list-item-subtitle class="text-wrap">
                    Navigate and analyze code by classes, methods, functions, and variables
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template #prepend>
                    <v-icon color="success">mdi-find-replace</v-icon>
                  </template>
                  <v-list-item-title>Smart find and replace operations</v-list-item-title>
                  <v-list-item-subtitle class="text-wrap">
                    Perform context-aware code transformations across your entire codebase
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template #prepend>
                    <v-icon color="success">mdi-graph-outline</v-icon>
                  </template>
                  <v-list-item-title>Code relationship mapping</v-list-item-title>
                  <v-list-item-subtitle class="text-wrap">
                    Understand dependencies, references, and call hierarchies automatically
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template #prepend>
                    <v-icon color="success">mdi-file-document-multiple</v-icon>
                  </template>
                  <v-list-item-title>Cross-file refactoring support</v-list-item-title>
                  <v-list-item-subtitle class="text-wrap">
                    Safely refactor code across multiple files while maintaining consistency
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </v-card>

    <!-- Installation Warning -->
    <AppAlert type="warning" variant="tonal" prominent class="mb-4">
      <v-alert-title class="text-h6">Important: Separate Installation Required</v-alert-title>
      <div class="text-body-2 mt-2">
        <p class="mb-2">
          <strong>Serena MCP is a separate MCP server</strong> and is not included with GiljoAI. You
          must install it separately in your Claude Code CLI configuration.
        </p>
        <p class="mb-3">
          Enabling Serena here only adds guidance to agent prompts. The actual Serena tools will
          only be available after you install Serena MCP.
        </p>
        <div class="d-flex flex-wrap gap-2">
          <v-btn
            href="https://github.com/oraios/serena"
            target="_blank"
            color="primary"
            variant="flat"
            size="small"
            aria-label="Visit Serena GitHub repository"
          >
            <v-icon start>mdi-github</v-icon>
            View on GitHub
          </v-btn>
          <v-btn
            variant="outlined"
            size="small"
            @click="showInstallGuide = true"
            aria-label="View installation guide"
          >
            <v-icon start>mdi-book-open-variant</v-icon>
            Installation Guide
          </v-btn>
        </div>
      </div>
    </v-alert>

    <!-- Main Choice Card -->
    <v-card variant="outlined" class="serena-card">
      <v-card-text class="text-center">
        <h3 class="text-h6 mb-3">Enable Serena Instructions?</h3>

        <p class="text-body-2 mb-4">
          When enabled, coding agents receive guidance on using Serena MCP tools for semantic code
          analysis and intelligent refactoring.
        </p>

        <!-- Simple Choice -->
        <v-radio-group v-model="choice" class="mt-4">
          <v-radio
            label="Yes, enable Serena instructions (I have installed Serena separately)"
            value="enabled"
            color="primary"
          />
          <v-radio
            label="No, skip Serena (can enable later in Settings)"
            value="disabled"
            color="primary"
          />
        </v-radio-group>

        <AppAlert
          v-if="choice === 'enabled'"
          type="info"
          variant="tonal"
          density="compact"
          class="mt-3"
        >
          Remember to install Serena MCP separately for the tools to work
        </AppAlert>
      </v-card-text>
    </v-card>

    <!-- Progress Indicator -->
    <v-card variant="outlined" class="mt-6 mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 3 of 5</span>
          <span class="text-caption">60%</span>
        </div>
        <v-progress-linear :model-value="60" color="warning" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <v-card variant="outlined" class="mt-6 mb-0">
      <v-card-text class="d-flex justify-space-between">
        <v-btn variant="outlined" @click="$emit('back')">
          <v-icon start>mdi-arrow-left</v-icon>
          Back
        </v-btn>
        <v-btn color="primary" @click="handleNext">
          Continue
          <v-icon end>mdi-arrow-right</v-icon>
        </v-btn>
      </v-card-text>
    </v-card>

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

              <p class="mb-3">The simplest method - uvx automatically manages the installation:</p>

              <v-code class="mb-3"> uvx --from git+https://github.com/oraios/serena serena </v-code>

              <h4 class="text-h6 mt-4 mb-3">Configure in Claude Code</h4>

              <p class="mb-2">Edit <code>~/.claude.json</code>:</p>

              <v-code>
                { "mcpServers": { "serena": { "command": "uvx", "args": ["serena"] } } }
              </v-code>
            </v-tabs-window-item>

            <v-tabs-window-item value="local">
              <h4 class="text-h6 mb-3">Local Installation</h4>

              <p class="mb-3">Clone and run locally:</p>

              <v-code class="mb-3">
                git clone https://github.com/oraios/serena cd serena uv run serena start-mcp-server
              </v-code>

              <h4 class="text-h6 mt-4 mb-3">Configure in Claude Code</h4>

              <p class="mb-2">Edit <code>~/.claude.json</code>:</p>

              <v-code>
                { "mcpServers": { "serena": { "command": "path/to/serena/venv/bin/python", "args":
                ["-m", "serena"] } } }
              </v-code>
            </v-tabs-window-item>
          </v-tabs-window>

          <AppAlert type="success" variant="tonal" class="mt-4">
            After installation, restart Claude Code and verify with <code>/mcp</code>
          </AppAlert>
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
import { ref, onMounted } from 'vue'
import setupService from '@/services/setupService'
import AppAlert from '@/components/ui/AppAlert.vue'

const emit = defineEmits(['next', 'back'])

// Simple state
const choice = ref('disabled')
const showInstallGuide = ref(false)
const installTab = ref('uvx')

// Simple handler - just emit choice
const handleNext = () => {
  emit('next', {
    serenaEnabled: choice.value === 'enabled',
  })
}

// Lifecycle - check if Serena is already enabled
onMounted(async () => {
  console.log('[SERENA_STEP] Checking Serena status')

  try {
    const status = await setupService.getSerenaStatus()

    if (status.enabled) {
      console.log('[SERENA_STEP] Serena is already enabled')
      choice.value = 'enabled'
    } else {
      console.log('[SERENA_STEP] Serena is disabled')
      choice.value = 'disabled'
    }
  } catch (error) {
    console.error('[SERENA_STEP] Failed to check Serena status:', error)
    // Default to disabled on error
    choice.value = 'disabled'
  }
})
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
