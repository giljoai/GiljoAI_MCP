<template>
  <v-dialog v-model="dialog" max-width="900" persistent scrollable>
    <template v-slot:activator="{ props }">
      <v-btn
        color="primary"
        variant="flat"
        v-bind="props"
        :prepend-icon="'mdi-connection'"
      >
        Connect AI Tools
      </v-btn>
    </template>

    <v-card>
      <v-card-title class="d-flex align-center bg-primary">
        <v-icon start>mdi-robot-outline</v-icon>
        Connect AI Tools to GiljoAI MCP
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" @click="closeDialog" />
      </v-card-title>

      <v-card-text class="pt-6">
        <!-- Tool Selection -->
        <v-alert type="info" variant="tonal" class="mb-6">
          <div class="d-flex align-center">
            <v-icon start>mdi-information</v-icon>
            <div>
              Generate configuration for your AI tool to connect to this GiljoAI MCP server.
              Copy and paste the configuration, or download a complete setup guide.
            </div>
          </div>
        </v-alert>

        <v-select
          v-model="selectedTool"
          :items="supportedTools"
          item-title="name"
          item-value="id"
          label="Select AI Tool"
          variant="outlined"
          prepend-icon="mdi-robot"
          hint="Choose the AI tool you want to connect"
          persistent-hint
          @update:model-value="generateConfig"
        >
          <template v-slot:item="{ props, item }">
            <v-list-item v-bind="props">
              <template v-slot:prepend>
                <v-icon :icon="getToolIcon(item.raw.id)" />
              </template>
            </v-list-item>
          </template>
        </v-select>

        <!-- Loading State -->
        <div v-if="loading" class="text-center my-8">
          <v-progress-circular indeterminate color="primary" size="64" />
          <p class="mt-4 text-body-1">Generating configuration...</p>
        </div>

        <!-- Error State -->
        <v-alert v-if="error" type="error" variant="tonal" class="mt-6">
          <div class="d-flex align-center">
            <v-icon start>mdi-alert-circle</v-icon>
            <div>
              <strong>Error:</strong> {{ error }}
            </div>
          </div>
        </v-alert>

        <!-- Configuration Display -->
        <div v-if="configData && !loading" class="mt-6">
          <!-- File Location -->
          <v-alert type="success" variant="tonal" class="mb-4">
            <div class="d-flex align-center">
              <v-icon start>mdi-file-document</v-icon>
              <div>
                <strong>Configuration File:</strong>
                <code class="ml-2 text-primary">{{ configData.file_location }}</code>
              </div>
            </div>
          </v-alert>

          <!-- Configuration Content -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="bg-grey-darken-3 d-flex align-center">
              <v-icon start>mdi-code-json</v-icon>
              Configuration Content
              <v-spacer />
              <v-btn
                size="small"
                variant="text"
                :prepend-icon="copied ? 'mdi-check' : 'mdi-content-copy'"
                @click="copyToClipboard"
              >
                {{ copied ? 'Copied!' : 'Copy' }}
              </v-btn>
            </v-card-title>
            <v-card-text class="pa-0">
              <pre class="config-code"><code>{{ configData.config_content }}</code></pre>
            </v-card-text>
          </v-card>

          <!-- Instructions -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="bg-grey-darken-3 d-flex align-center">
              <v-icon start>mdi-list-box-outline</v-icon>
              Setup Instructions
            </v-card-title>
            <v-card-text>
              <v-list density="compact">
                <v-list-item
                  v-for="(instruction, index) in configData.instructions"
                  :key="index"
                  class="px-0"
                >
                  <template v-slot:prepend>
                    <v-icon
                      :icon="index === configData.instructions.length - 1 ? 'mdi-check-circle' : 'mdi-numeric-' + (index + 1) + '-circle'"
                      :color="index === configData.instructions.length - 1 ? 'success' : 'primary'"
                    />
                  </template>
                  <v-list-item-title>{{ instruction }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>

          <!-- Download Button -->
          <v-btn
            block
            color="success"
            variant="flat"
            size="large"
            :prepend-icon="'mdi-download'"
            @click="downloadMarkdownGuide"
          >
            Download Complete Setup Guide (Markdown)
          </v-btn>
        </div>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="closeDialog">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { API_CONFIG } from '@/config/api'

// State
const dialog = ref(false)
const selectedTool = ref(null)
const supportedTools = ref([])
const configData = ref(null)
const loading = ref(false)
const error = ref(null)
const copied = ref(false)

// Methods
async function loadSupportedTools() {
  try {
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/ai-tools/supported`)

    if (!response.ok) {
      throw new Error('Failed to load supported tools')
    }

    const data = await response.json()
    supportedTools.value = data.tools.filter(tool => tool.supported)
  } catch (err) {
    console.error('[AIToolSetup] Failed to load supported tools:', err)
    error.value = 'Failed to load supported tools. Please try again.'
  }
}

async function generateConfig() {
  if (!selectedTool.value) {
    return
  }

  loading.value = true
  error.value = null
  configData.value = null

  try {
    const response = await fetch(
      `${API_CONFIG.REST_API.baseURL}/api/ai-tools/config-generator/${selectedTool.value}`
    )

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to generate configuration')
    }

    configData.value = await response.json()
    console.log('[AIToolSetup] Configuration generated successfully for', selectedTool.value)
  } catch (err) {
    console.error('[AIToolSetup] Failed to generate config:', err)
    error.value = err.message || 'Failed to generate configuration. Please try again.'
  } finally {
    loading.value = false
  }
}

async function copyToClipboard() {
  if (!configData.value) return

  try {
    await navigator.clipboard.writeText(configData.value.config_content)
    copied.value = true
    console.log('[AIToolSetup] Configuration copied to clipboard')

    // Reset copied state after 2 seconds
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('[AIToolSetup] Failed to copy to clipboard:', err)
    error.value = 'Failed to copy to clipboard. Please copy manually.'
  }
}

async function downloadMarkdownGuide() {
  if (!configData.value || !selectedTool.value) return

  try {
    const response = await fetch(
      `${API_CONFIG.REST_API.baseURL}/api/ai-tools/config-generator/${selectedTool.value}/markdown`
    )

    if (!response.ok) {
      throw new Error('Failed to download setup guide')
    }

    const markdown = await response.text()

    // Create blob and download
    const blob = new Blob([markdown], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = configData.value.download_filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    console.log('[AIToolSetup] Setup guide downloaded successfully')
  } catch (err) {
    console.error('[AIToolSetup] Failed to download guide:', err)
    error.value = 'Failed to download setup guide. Please try again.'
  }
}

function getToolIcon(toolId) {
  const icons = {
    claude: 'mdi-chat-processing',
    codex: 'mdi-code-braces',
    gemini: 'mdi-diamond-stone'
  }
  return icons[toolId] || 'mdi-robot'
}

function closeDialog() {
  dialog.value = false
  // Reset state after dialog closes
  setTimeout(() => {
    selectedTool.value = null
    configData.value = null
    error.value = null
    copied.value = false
  }, 300)
}

// Lifecycle
onMounted(() => {
  loadSupportedTools()
})
</script>

<style scoped>
.config-code {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  margin: 0;
  overflow-x: auto;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  border-radius: 0;
  max-height: 400px;
}

.config-code code {
  background: transparent;
  color: inherit;
  padding: 0;
}

/* Syntax highlighting for JSON */
.config-code :deep(.token.property) {
  color: #9cdcfe;
}

.config-code :deep(.token.string) {
  color: #ce9178;
}

.config-code :deep(.token.number) {
  color: #b5cea8;
}

.config-code :deep(.token.boolean) {
  color: #569cd6;
}

.config-code :deep(.token.null) {
  color: #569cd6;
}
</style>
