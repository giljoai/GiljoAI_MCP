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
          <!-- Template Description -->
          <div v-if="templateData.description" class="mb-4">
            <div class="text-subtitle-2 mb-1">Description</div>
            <div class="text-body-2">{{ templateData.description }}</div>
          </div>

          <!-- Template Metadata -->
          <v-row v-if="hasMetadata" dense class="mb-4">
            <v-col v-if="templateData.model" cols="12" sm="6">
              <div class="text-caption font-weight-bold">Model:</div>
              <v-chip size="small" color="primary" variant="tonal" label>
                {{ templateData.model }}
              </v-chip>
            </v-col>
            <v-col v-if="templateData.variables?.length > 0" cols="12" sm="6">
              <div class="text-caption font-weight-bold mb-1">Variables:</div>
              <div class="d-flex flex-wrap gap-1">
                <v-chip
                  v-for="variable in templateData.variables"
                  :key="variable"
                  size="x-small"
                  variant="outlined"
                  label
                >
                  {{ variable }}
                </v-chip>
              </div>
            </v-col>
            <v-col v-if="templateData.tools?.length > 0" cols="12">
              <div class="text-caption font-weight-bold mb-1">Tools:</div>
              <div class="d-flex flex-wrap gap-1">
                <v-chip
                  v-for="tool in templateData.tools"
                  :key="tool"
                  size="x-small"
                  color="secondary"
                  variant="tonal"
                  label
                >
                  {{ tool }}
                </v-chip>
              </div>
            </v-col>
          </v-row>

          <!-- Template Content -->
          <div class="mb-3">
            <div class="d-flex align-center justify-space-between mb-2">
              <div class="text-subtitle-2">Template Content</div>
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
              <pre class="template-content">{{ templateData.template_content || 'No content available' }}</pre>
            </v-card>
          </div>
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

        <!-- No Template ID -->
        <div v-else-if="!isOrchestrator && !agent.template_id && !loading">
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

const hasMetadata = computed(() => {
  return (
    templateData.value?.model ||
    templateData.value?.variables?.length > 0 ||
    templateData.value?.tools?.length > 0
  )
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
  if (!props.agent?.template_id) {
    error.value = null
    return
  }

  loading.value = true
  error.value = null
  templateData.value = null

  try {
    const response = await apiClient.templates.get(props.agent.template_id)
    templateData.value = response.data
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
