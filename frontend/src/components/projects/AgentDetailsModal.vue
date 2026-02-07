<template>
  <v-dialog v-model="isOpen" max-width="800" persistent>
    <v-card>
      <!-- Header -->
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-information-outline</v-icon>
        <span v-if="isOrchestrator">System Orchestrator Prompt</span>
        <span v-else>Agent Details: {{ agent?.agent_name || 'Unknown Agent' }}</span>
        <v-spacer></v-spacer>
        <v-btn icon variant="text" aria-label="Close dialog" @click="handleClose">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider></v-divider>

      <!-- Content -->
      <v-card-text v-if="agent">
        <!-- Agent Info Section (non-orchestrator) -->
        <div v-if="!isOrchestrator" class="mb-4">
          <div class="d-flex align-center gap-2 mb-2">
            <v-chip size="small" :color="getAgentDisplayNameColor(agent.agent_display_name)" label>
              {{ agent.agent_display_name }}
            </v-chip>
            <span class="text-caption text-medium-emphasis">Agent ID: {{ agent.agent_id || agent.id || '—' }}</span>
          </div>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="text-center py-8">
          <v-progress-circular indeterminate color="primary"></v-progress-circular>
          <div class="text-body-2 text-medium-emphasis mt-3">Loading...</div>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="py-4">
          <v-alert type="error" variant="tonal" density="compact">
            <strong>Failed to load:</strong> {{ error }}
          </v-alert>
        </div>

        <!-- Template Content (Regular Agents) -->
        <div v-else-if="!isOrchestrator && templateData">
          <!-- Template Overview Card -->
          <v-card variant="outlined" class="mb-4">
            <v-list density="compact">
              <!-- Name (with Role suffix if different) - Handover 0358: giljo yellow -->
              <v-list-item>
                <template #prepend>
                  <v-icon color="#FFD700">mdi-account-badge</v-icon>
                </template>
                <v-list-item-title class="font-weight-bold">Name</v-list-item-title>
                <v-list-item-subtitle>
                  {{ templateData.name }}
                  <span v-if="templateData.role && templateData.role !== templateData.name" class="text-medium-emphasis">
                    ({{ templateData.role }})
                  </span>
                </v-list-item-subtitle>
              </v-list-item>

              <v-divider></v-divider>

              <!-- CLI Tool (Handover 0358: use actual tool icons) -->
              <v-list-item v-if="templateData.cli_tool">
                <template #prepend>
                  <img
                    v-if="getCliToolIcon(templateData.cli_tool)"
                    :src="getCliToolIcon(templateData.cli_tool)"
                    alt="CLI Tool"
                    class="cli-tool-icon"
                  />
                  <v-icon v-else color="secondary">mdi-console</v-icon>
                </template>
                <v-list-item-title class="font-weight-bold">CLI Tool</v-list-item-title>
                <v-list-item-subtitle>{{ templateData.cli_tool }}</v-list-item-subtitle>
              </v-list-item>

              <v-divider v-if="templateData.cli_tool"></v-divider>

              <!-- Model (Handover 0358: use giljo face icon) -->
              <v-list-item v-if="templateData.model">
                <template #prepend>
                  <img
                    :src="giljoFaceIcon"
                    alt="Model"
                    class="giljo-face-icon"
                  />
                </template>
                <v-list-item-title class="font-weight-bold">Model</v-list-item-title>
                <v-list-item-subtitle>{{ templateData.model }}</v-list-item-subtitle>
              </v-list-item>

              <v-divider v-if="templateData.model"></v-divider>

              <!-- Description - Handover 0358: giljo yellow -->
              <v-list-item v-if="templateData.description">
                <template #prepend>
                  <v-icon color="#FFD700">mdi-text</v-icon>
                </template>
                <v-list-item-title class="font-weight-bold">Description</v-list-item-title>
                <v-list-item-subtitle class="text-wrap">
                  {{ templateData.description }}
                </v-list-item-subtitle>
              </v-list-item>

              <v-divider v-if="templateData.description"></v-divider>

              <!-- Custom Suffix -->
              <v-list-item v-if="templateData.custom_suffix">
                <template #prepend>
                  <v-icon color="warning">mdi-tag</v-icon>
                </template>
                <v-list-item-title class="font-weight-bold">Custom Suffix</v-list-item-title>
                <v-list-item-subtitle>{{ templateData.custom_suffix }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card>

          <!-- Tools Section -->
          <div v-if="templateData.tools?.length > 0" class="mb-4">
            <div class="text-subtitle-2 mb-2">
              <v-icon start size="small">mdi-wrench</v-icon>
              MCP Tools ({{ templateData.tools.length }})
            </div>
            <div class="d-flex flex-wrap gap-1">
              <v-chip
                v-for="tool in templateData.tools"
                :key="tool"
                size="small"
                color="secondary"
                variant="tonal"
                label
              >
                {{ tool }}
              </v-chip>
            </div>
          </div>

          <!-- Instructions Expansion Panels -->
          <v-expansion-panels variant="accordion" class="mb-3">
            <!-- System Instructions -->
            <v-expansion-panel v-if="templateData.system_instructions">
              <v-expansion-panel-title>
                <div class="d-flex align-center">
                  <v-icon start size="small">mdi-cog</v-icon>
                  <span class="font-weight-medium">System Instructions</span>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div class="d-flex justify-end mb-2">
                  <v-btn
                    size="small"
                    variant="tonal"
                    prepend-icon="mdi-content-copy"
                    @click="copyToClipboard(templateData.system_instructions)"
                  >
                    Copy
                  </v-btn>
                </div>
                <v-card variant="outlined" class="template-content-card">
                  <pre class="template-content">{{ templateData.system_instructions }}</pre>
                </v-card>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- User Instructions -->
            <v-expansion-panel v-if="templateData.user_instructions">
              <v-expansion-panel-title>
                <div class="d-flex align-center">
                  <v-icon start size="small">mdi-account</v-icon>
                  <span class="font-weight-medium">User Instructions</span>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div class="d-flex justify-end mb-2">
                  <v-btn
                    size="small"
                    variant="tonal"
                    prepend-icon="mdi-content-copy"
                    @click="copyToClipboard(templateData.user_instructions)"
                  >
                    Copy
                  </v-btn>
                </div>
                <v-card variant="outlined" class="template-content-card">
                  <pre class="template-content">{{ templateData.user_instructions }}</pre>
                </v-card>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Template Content (for backward compatibility) -->
            <v-expansion-panel v-if="templateData.system_instructions">
              <v-expansion-panel-title>
                <div class="d-flex align-center">
                  <v-icon start size="small">mdi-file-document</v-icon>
                  <span class="font-weight-medium">Template Content</span>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div class="d-flex justify-end mb-2">
                  <v-btn
                    size="small"
                    variant="tonal"
                    prepend-icon="mdi-content-copy"
                    @click="copyToClipboard(templateData.system_instructions)"
                  >
                    Copy
                  </v-btn>
                </div>
                <v-card variant="outlined" class="template-content-card">
                  <pre class="template-content">{{ templateData.system_instructions }}</pre>
                </v-card>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </div>

        <!-- Orchestrator Prompt Content -->
        <div v-else-if="isOrchestrator && orchestratorPrompt">
          <div class="mb-3">
            <div class="d-flex align-center justify-space-between mb-2">
              <div class="text-subtitle-2">Orchestrator System Prompt</div>
              <v-btn
                size="small"
                variant="tonal"
                prepend-icon="mdi-content-copy"
                @click="copyToClipboard(orchestratorPrompt)"
              >
                Copy
              </v-btn>
            </div>
            <v-card variant="outlined" class="template-content-card">
              <pre class="template-content">{{ orchestratorPrompt }}</pre>
            </v-card>
          </div>
        </div>

        <!-- No Template Data (after attempting fetch) - Handover 0358 -->
        <div v-else-if="!isOrchestrator && !templateData && !loading">
          <v-alert type="info" variant="tonal" density="compact">
            No template information available for this agent.
          </v-alert>
        </div>

        <!-- Copy Success Feedback -->
        <v-snackbar v-model="copySuccess" :timeout="2000" color="success" location="top">
          <v-icon start>mdi-check-circle</v-icon>
          Copied to clipboard!
        </v-snackbar>
      </v-card-text>

      <!-- No Agent Data -->
      <v-card-text v-else>
        <v-alert type="warning" variant="tonal" density="compact">
          No agent information available.
        </v-alert>
      </v-card-text>

      <v-divider></v-divider>

      <!-- Actions -->
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="handleClose">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch, getCurrentInstance } from 'vue'
import { useTheme } from 'vuetify'
import api from '@/services/api'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  agent: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:modelValue'])

// Get API instance (use injected $api if available, otherwise use imported api)
const instance = getCurrentInstance()
const apiClient = instance?.appContext.config.globalProperties.$api || api

// Giljo face icon (dark theme only)
const giljoFaceIcon = computed(() => {
  return '/giljo_YW_Face.svg'
})

// State
const loading = ref(false)
const error = ref(null)
const templateData = ref(null)
const orchestratorPrompt = ref(null)
const copySuccess = ref(false)

// Computed
const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const isOrchestrator = computed(() => {
  return props.agent?.agent_display_name === 'orchestrator'
})

// Methods
const handleClose = () => {
  emit('update:modelValue', false)
}

/**
 * Get agent avatar color - matches BRANDING_GUIDE.md (Handover 0358)
 */
const getAgentDisplayNameColor = (displayName) => {
  const colors = {
    orchestrator: '#D4A574', // Tan/Beige - Project coordination
    analyzer: '#E74C3C', // Red - Analysis & research
    implementer: '#3498DB', // Blue - Code implementation
    implementor: '#3498DB', // Blue - Code implementation (alias)
    tester: '#FFC300', // Yellow - Testing & QA
    reviewer: '#9B59B6', // Purple - Code review
    documenter: '#27AE60', // Green - Documentation
    researcher: '#27AE60', // Green - Research (alias)
  }
  return colors[displayName] || 'grey'
}

/**
 * Get CLI tool icon path (Handover 0358)
 */
const getCliToolIcon = (cliTool) => {
  const icons = {
    claude: '/Claude_AI_symbol.svg',
    'claude-code': '/Claude_AI_symbol.svg',
    codex: '/codex_logo.svg',
    gemini: '/gemini-icon.svg',
    openai: '/openai-logo.svg',
  }
  return icons[cliTool?.toLowerCase()] || null // null = use mdi-console for generic
}

const fetchTemplateData = async () => {
  // Handover 0358: Support fetching by template_id OR agent_display_name/agent_name
  const hasTemplateId = !!props.agent?.template_id
  const displayName = props.agent?.agent_display_name
  const agentName = props.agent?.agent_name

  if (!hasTemplateId && !displayName && !agentName) {
    error.value = null
    return
  }

  loading.value = true
  error.value = null
  templateData.value = null

  try {
    if (hasTemplateId) {
      // Fetch by template_id directly
      const response = await apiClient.templates.get(props.agent.template_id)
      templateData.value = response.data
    } else {
      // Fetch all active templates and find matching one by name
      const response = await apiClient.templates.list({ is_active: true })
      const templates = Array.isArray(response.data) ? response.data : (response.data?.templates || [])

      console.log('[AgentDetailsModal] Searching for template matching:', { displayName, agentName })
      console.log('[AgentDetailsModal] Available templates:', templates.map(t => t.name))

      // Find matching template by name (case-insensitive)
      const searchTerms = [displayName, agentName].filter(Boolean).map(s => s.toLowerCase())
      const match = templates.find(t => {
        const templateName = (t.name || '').toLowerCase()
        const templateRole = (t.role || '').toLowerCase()
        return searchTerms.some(term =>
          templateName === term ||
          templateRole === term ||
          templateName.includes(term) ||
          term.includes(templateName)
        )
      })

      if (match) {
        console.log('[AgentDetailsModal] Found matching template:', match.name)
        templateData.value = match
      } else {
        console.log('[AgentDetailsModal] No matching template found')
      }
    }
  } catch (err) {
    console.error('[AgentDetailsModal] Failed to fetch template:', err)
    error.value = err.response?.data?.detail || err.message || 'Failed to fetch template data'
  } finally {
    loading.value = false
  }
}

const fetchOrchestratorPrompt = async () => {
  loading.value = true
  error.value = null
  orchestratorPrompt.value = null

  try {
    const response = await apiClient.system.getOrchestratorPrompt()
    orchestratorPrompt.value = response.data.content
  } catch (err) {
    console.error('[AgentDetailsModal] Failed to fetch orchestrator prompt:', err)
    error.value =
      err.response?.data?.detail || err.message || 'Failed to fetch orchestrator prompt'
  } finally {
    loading.value = false
  }
}

const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    copySuccess.value = true
  } catch (err) {
    console.error('[AgentDetailsModal] Failed to copy to clipboard:', err)
  }
}

// Watchers
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue && props.agent) {
      // Reset state
      templateData.value = null
      orchestratorPrompt.value = null
      error.value = null

      // Fetch appropriate data
      if (isOrchestrator.value) {
        fetchOrchestratorPrompt()
      } else {
        // Handover 0358: Fetch template by template_id OR agent_display_name/agent_name
        fetchTemplateData()
      }
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.template-content-card {
  max-height: 500px;
  overflow-y: auto;
  background-color: rgb(var(--v-theme-surface-variant));
}

.template-content {
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  line-height: 1.6;
  padding: 16px;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: rgb(var(--v-theme-on-surface-variant));
}

.gap-2 {
  gap: 8px;
}

/* Handover 0358: Icon styling for CLI tools and giljo face */
.cli-tool-icon {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.giljo-face-icon {
  width: 24px;
  height: 24px;
  object-fit: contain;
}
</style>
