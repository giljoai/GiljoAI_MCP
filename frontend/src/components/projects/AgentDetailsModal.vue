<template>
  <v-dialog v-model="isOpen" max-width="800" persistent>
    <v-card>
      <!-- Header -->
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-information-outline</v-icon>
        <span v-if="isOrchestrator">System Orchestrator Prompt</span>
        <span v-else>Agent Details: {{ agent?.agent_name || 'Unknown Agent' }}</span>
        <v-spacer></v-spacer>
        <v-btn icon variant="text" @click="handleClose" aria-label="Close dialog">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider></v-divider>

      <!-- Content -->
      <v-card-text v-if="agent">
        <!-- Agent Info Section (non-orchestrator) -->
        <div v-if="!isOrchestrator" class="mb-4">
          <div class="d-flex align-center gap-2 mb-2">
            <v-chip size="small" :color="getAgentTypeColor(agent.agent_type)" label>
              {{ agent.agent_type }}
            </v-chip>
            <span class="text-caption text-medium-emphasis">ID: {{ agent.id }}</span>
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
              <!-- Role -->
              <v-list-item v-if="templateData.role">
                <template #prepend>
                  <v-icon color="primary">mdi-account-badge</v-icon>
                </template>
                <v-list-item-title class="font-weight-bold">Role</v-list-item-title>
                <v-list-item-subtitle>{{ templateData.role }}</v-list-item-subtitle>
              </v-list-item>

              <v-divider v-if="templateData.role"></v-divider>

              <!-- CLI Tool -->
              <v-list-item v-if="templateData.cli_tool">
                <template #prepend>
                  <v-icon color="secondary">mdi-console</v-icon>
                </template>
                <v-list-item-title class="font-weight-bold">CLI Tool</v-list-item-title>
                <v-list-item-subtitle>{{ templateData.cli_tool }}</v-list-item-subtitle>
              </v-list-item>

              <v-divider v-if="templateData.cli_tool"></v-divider>

              <!-- Model -->
              <v-list-item v-if="templateData.model">
                <template #prepend>
                  <v-icon color="tertiary">mdi-robot</v-icon>
                </template>
                <v-list-item-title class="font-weight-bold">Model</v-list-item-title>
                <v-list-item-subtitle>{{ templateData.model }}</v-list-item-subtitle>
              </v-list-item>

              <v-divider v-if="templateData.model"></v-divider>

              <!-- Description -->
              <v-list-item v-if="templateData.description">
                <template #prepend>
                  <v-icon color="info">mdi-text</v-icon>
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
            <v-expansion-panel v-if="templateData.template_content">
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
                    @click="copyToClipboard(templateData.template_content)"
                  >
                    Copy
                  </v-btn>
                </div>
                <v-card variant="outlined" class="template-content-card">
                  <pre class="template-content">{{ templateData.template_content }}</pre>
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
  return props.agent?.agent_type === 'orchestrator'
})

// Methods
const handleClose = () => {
  emit('update:modelValue', false)
}

const getAgentTypeColor = (agentType) => {
  const colors = {
    orchestrator: 'purple',
    implementer: 'blue',
    tester: 'green',
    architect: 'orange',
    reviewer: 'cyan',
    documenter: 'indigo',
  }
  return colors[agentType] || 'grey'
}

const fetchTemplateData = async () => {
  // Handover 0358: Support fetching by template_id OR agent_type
  const hasTemplateId = !!props.agent?.template_id
  const hasAgentType = !!props.agent?.agent_type

  if (!hasTemplateId && !hasAgentType) {
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
    } else if (hasAgentType) {
      // Fetch by agent_type from templates list
      const response = await apiClient.templates.list({ agent_type: props.agent.agent_type })
      const templates = response.data?.templates || response.data || []
      // Find matching template by agent_type or name
      const match = templates.find(t =>
        t.agent_type === props.agent.agent_type ||
        t.name === props.agent.agent_type ||
        t.name === props.agent.agent_name
      )
      if (match) {
        templateData.value = match
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
      } else if (props.agent.template_id) {
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
</style>
