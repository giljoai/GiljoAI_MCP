<template>
  <v-dialog v-model="isOpen" max-width="800" persistent>
    <v-card v-draggable class="smooth-border">
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
            <span
              class="agent-tinted-badge"
              :style="{
                backgroundColor: hexToRgba(getAgentDisplayNameColor(agent.agent_display_name), 0.15),
                color: getAgentDisplayNameColor(agent.agent_display_name),
              }"
            >
              {{ agent.agent_display_name }}
            </span>
            <span class="text-caption details-text-muted">Agent ID: {{ agent.agent_id || agent.id || '—' }}</span>
          </div>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="text-center py-8">
          <v-progress-circular indeterminate color="primary"></v-progress-circular>
          <div class="text-body-2 details-text-muted mt-3">Loading...</div>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="py-4">
          <v-alert type="error" variant="tonal" density="compact">
            <strong>Failed to load:</strong> {{ error }}
          </v-alert>
        </div>

        <!-- Template Preview (Regular Agents) — Handover 0814: simplified to match TemplateManager preview -->
        <div v-else-if="!isOrchestrator && previewContent">
          <v-card variant="flat" class="template-content-card smooth-border">
            <pre class="template-content">{{ previewContent }}</pre>
          </v-card>
        </div>

        <!-- Orchestrator Prompt Content -->
        <div v-else-if="isOrchestrator && orchestratorPrompt">
          <v-card variant="flat" class="template-content-card smooth-border">
            <pre class="template-content">{{ orchestratorPrompt }}</pre>
          </v-card>
        </div>

        <!-- No Template Data (after attempting fetch) -->
        <div v-else-if="!isOrchestrator && !previewContent && !loading">
          <v-alert type="info" variant="tonal" density="compact">
            No template information available for this agent.
          </v-alert>
        </div>
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
import { getAgentColor as getAgentColorConfig } from '@/config/agentColors'
import { hexToRgba } from '@/utils/colorUtils'

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
const previewContent = ref(null)
const orchestratorPrompt = ref(null)

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

const getAgentDisplayNameColor = (displayName) => {
  return getAgentColorConfig(displayName).hex
}

/**
 * Fetch template and generate preview content (Handover 0814)
 * Resolves template by template_id or name matching, then calls preview API
 */
const fetchTemplateData = async () => {
  const hasTemplateId = !!props.agent?.template_id
  const displayName = props.agent?.agent_display_name
  const agentName = props.agent?.agent_name

  if (!hasTemplateId && !displayName && !agentName) {
    error.value = null
    return
  }

  loading.value = true
  error.value = null
  previewContent.value = null

  try {
    let templateId = null

    if (hasTemplateId) {
      templateId = props.agent.template_id
    } else {
      // Fetch all active templates and find matching one by name
      const response = await apiClient.templates.list({ is_active: true })
      const templates = Array.isArray(response.data) ? response.data : (response.data?.templates || [])

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
        templateId = match.id
      }
    }

    if (templateId) {
      const previewResponse = await apiClient.templates.preview(templateId, {})
      previewContent.value = previewResponse.data.preview
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

// Watchers
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue && props.agent) {
      // Reset state
      previewContent.value = null
      orchestratorPrompt.value = null
      error.value = null

      // Fetch appropriate data
      if (isOrchestrator.value) {
        fetchOrchestratorPrompt()
      } else {
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

.details-text-muted {
  color: #8895a8;
}

.agent-tinted-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 8px;
  font-size: 0.75rem;
  font-weight: 600;
}
</style>
