<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-2">Attach Coding Tools</h2>
    <p class="text-body-1 mb-6">
      Connect AI coding assistants to GiljoAI MCP using the Model Context Protocol
    </p>

    <!-- Tool Cards -->
    <v-row>
      <!-- Claude Code - Active -->
      <v-col cols="12" md="4">
        <v-card
          variant="outlined"
          class="tool-card h-100"
          :class="{ 'tool-configured': claudeCodeConfigured }"
        >
          <v-card-text class="d-flex flex-column h-100">
            <!-- Tool Header -->
            <div class="text-center mb-4">
              <v-icon size="48" color="primary">mdi-code-braces</v-icon>
              <h3 class="text-h6 mt-2">Claude Code</h3>
              <v-chip v-if="claudeCodeConfigured" size="small" color="success" class="mt-2">
                Configured
              </v-chip>
            </div>

            <!-- Tool Description -->
            <p class="text-body-2 text-medium-emphasis flex-grow-1">
              Anthropic's official CLI for Claude with built-in MCP support
            </p>

            <!-- Action Button -->
            <v-btn
              v-if="!claudeCodeConfigured"
              color="primary"
              variant="flat"
              block
              :loading="attaching"
              @click="attachClaudeCode"
              aria-label="Attach Claude Code"
            >
              Attach
            </v-btn>

            <!-- Verification Instructions -->
            <v-alert
              v-if="claudeCodeConfigured"
              type="success"
              variant="tonal"
              density="compact"
              class="mt-2"
            >
              <div class="text-caption">
                <strong>Next:</strong> Relaunch Claude Code CLI and type <code>/mcp</code> to verify
              </div>
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- ChatGPT - Future -->
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="tool-card h-100 disabled-tool">
          <v-card-text class="d-flex flex-column h-100">
            <!-- Tool Header -->
            <div class="text-center mb-4">
              <v-icon size="48" color="disabled">mdi-robot</v-icon>
              <h3 class="text-h6 mt-2 text-disabled">ChatGPT</h3>
              <v-chip size="small" color="info" class="mt-2">Future</v-chip>
            </div>

            <!-- Tool Description -->
            <p class="text-body-2 text-disabled flex-grow-1">
              OpenAI's ChatGPT with MCP integration (coming soon)
            </p>

            <!-- Disabled Button -->
            <v-btn
              color="grey"
              variant="outlined"
              block
              disabled
              aria-label="ChatGPT not yet available"
            >
              Coming Soon
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Gemini - Future -->
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="tool-card h-100 disabled-tool">
          <v-card-text class="d-flex flex-column h-100">
            <!-- Tool Header -->
            <div class="text-center mb-4">
              <v-icon size="48" color="disabled">mdi-star</v-icon>
              <h3 class="text-h6 mt-2 text-disabled">Gemini</h3>
              <v-chip size="small" color="info" class="mt-2">Future</v-chip>
            </div>

            <!-- Tool Description -->
            <p class="text-body-2 text-disabled flex-grow-1">
              Google's Gemini with MCP integration (coming soon)
            </p>

            <!-- Disabled Button -->
            <v-btn
              color="grey"
              variant="outlined"
              block
              disabled
              aria-label="Gemini not yet available"
            >
              Coming Soon
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Error Alert -->
    <v-alert
      v-if="errorMessage"
      type="error"
      variant="tonal"
      class="mt-4"
      closable
      @click:close="errorMessage = ''"
    >
      {{ errorMessage }}
    </v-alert>

    <!-- Info Alert -->
    <v-alert type="info" variant="tonal" class="mt-6">
      You can configure additional tools later in Settings. At least one tool is recommended but not
      required.
    </v-alert>

    <!-- Progress -->
    <v-card variant="outlined" class="mt-6 mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 1 of 4</span>
          <span class="text-caption">25%</span>
        </div>
        <v-progress-linear :model-value="25" color="primary" />
      </v-card-text>
    </v-card>

    <!-- Navigation -->
    <div class="d-flex justify-end">
      <v-btn color="primary" @click="handleNext" aria-label="Continue to network configuration">
        Continue
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import setupService from '@/services/setupService'

/**
 * AttachToolsStep - Tool attachment step (Step 1 of 3)
 *
 * Allows users to attach Claude Code and shows future tools
 */

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['update:modelValue', 'next'])

// State
const attaching = ref(false)
const claudeCodeConfigured = ref(false)
const errorMessage = ref('')

// Methods
const attachClaudeCode = async () => {
  attaching.value = true
  errorMessage.value = ''

  try {
    // Generate MCP configuration for Claude Code in localhost mode
    const mcpConfig = await setupService.generateMcpConfig('Claude Code', 'localhost')
    console.log('[ATTACH_TOOLS] Generated MCP config:', mcpConfig)

    // Register MCP configuration (writes to .claude.json)
    await setupService.registerMcp('Claude Code', mcpConfig)
    console.log('[ATTACH_TOOLS] Claude Code MCP registered')

    // Mark as configured
    claudeCodeConfigured.value = true

    // Update parent
    const tools = [
      {
        id: 'claude-code',
        name: 'Claude Code',
        configured: true,
      },
    ]
    emit('update:modelValue', tools)

    console.log('[ATTACH_TOOLS] Claude Code attached successfully')
  } catch (error) {
    console.error('[ATTACH_TOOLS] Failed to attach Claude Code:', error)
    errorMessage.value = `Failed to attach Claude Code: ${error.message}`
  } finally {
    attaching.value = false
  }
}

const handleNext = () => {
  console.log('[ATTACH_TOOLS] Moving to next step')
  emit('next')
}

// Lifecycle
onMounted(async () => {
  console.log('[ATTACH_TOOLS] Checking if Claude Code MCP is already configured')
  
  try {
    const status = await setupService.checkMcpConfigured()
    
    if (status.configured) {
      console.log('[ATTACH_TOOLS] Claude Code MCP already configured')
      claudeCodeConfigured.value = true
      
      // Update parent with existing configuration
      const tools = [
        {
          id: 'claude-code',
          name: 'Claude Code',
          configured: true,
        },
      ]
      emit('update:modelValue', tools)
    } else {
      console.log('[ATTACH_TOOLS] Claude Code MCP not configured')
    }
  } catch (error) {
    console.error('[ATTACH_TOOLS] Failed to check MCP status:', error)
    // Non-fatal error, continue with wizard
  }
})
</script>

<style scoped>
h2 {
  color: rgb(var(--v-theme-primary));
}

.tool-card {
  transition: all 0.2s ease;
  border-width: 2px;
}

.tool-card:not(.disabled-tool):hover {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.tool-configured {
  border-color: rgb(var(--v-theme-success));
  background-color: rgba(var(--v-theme-success), 0.05);
}

.disabled-tool {
  opacity: 0.6;
}

code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}
</style>
