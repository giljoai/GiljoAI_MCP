<template>
  <v-card>
    <v-card-title>Context Priority Configuration</v-card-title>
    <v-card-text>
      <!-- Locked Project Context -->
      <div class="context-row locked-row d-flex justify-space-between align-center py-3 mb-2">
        <div class="d-flex align-center">
          <v-icon size="small" color="primary" class="mr-2">mdi-lock</v-icon>
          <span class="text-subtitle-2 font-weight-medium">Project Context</span>
        </div>
        <v-chip size="small" color="primary" variant="flat"> Always High </v-chip>
      </div>

      <v-divider class="mb-3" />

      <!-- Context Rows -->
      <div
        v-for="context in contexts"
        :key="context.key"
        class="context-row d-flex justify-space-between align-center py-2"
      >
        <!-- Context Name and Toggle -->
        <div class="d-flex align-center flex-grow-1">
          <span class="text-body-2 context-label">{{ context.label }}</span>
          <v-switch
            :model-value="config[context.key]?.enabled"
            @update:model-value="toggleContext(context.key)"
            density="compact"
            hide-details
            color="primary"
            :aria-label="`Toggle ${context.label}`"
            class="ml-2 compact-switch"
          />
        </div>

        <!-- Depth/Count Select (if applicable) -->
        <v-select
          v-if="context.options"
          :model-value="getDepthValue(context.key)"
          @update:model-value="updateDepth(context.key, $event)"
          :items="formatOptions(context)"
          density="compact"
          variant="outlined"
          hide-details
          :aria-label="`${context.label} depth setting`"
          class="depth-select mx-2"
          :disabled="!config[context.key]?.enabled"
        />

        <!-- Priority Select -->
        <v-select
          :model-value="config[context.key]?.priority"
          @update:model-value="updatePriority(context.key, $event)"
          :items="priorityOptions"
          density="compact"
          variant="outlined"
          hide-details
          :aria-label="`${context.label} priority setting`"
          class="priority-select"
          :disabled="!config[context.key]?.enabled"
        />
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

// Context definitions
const contexts = [
  { key: 'product_description', label: 'Product Description' },
  {
    key: 'vision_documents',
    label: 'Vision Documents',
    options: ['none', 'light', 'moderate', 'heavy'],
  },
  { key: 'tech_stack', label: 'Tech Stack' },
  { key: 'architecture', label: 'Architecture' },
  { key: 'testing', label: 'Testing' },
  { key: 'agent_templates', label: 'Agent Templates', options: ['type_only', 'full'] },
  { key: 'memory_360', label: '360 Memory', options: [1, 3, 5, 10] },
  { key: 'git_history', label: 'Git History', options: [0, 5, 15, 25] },
]

const priorityOptions = [
  { title: 'Critical', value: 1 },
  { title: 'Important', value: 2 },
  { title: 'Reference', value: 3 },
  { title: 'Exclude', value: 4 },
]

// State
interface ContextConfig {
  enabled: boolean
  priority: number
  depth?: string
  count?: number
}

const config = ref<Record<string, ContextConfig>>({
  product_description: { enabled: true, priority: 1 },
  vision_documents: { enabled: true, priority: 2, depth: 'moderate' },
  tech_stack: { enabled: true, priority: 2 },
  architecture: { enabled: true, priority: 2 },
  testing: { enabled: true, priority: 3 },
  agent_templates: { enabled: true, priority: 2, depth: 'type_only' },
  memory_360: { enabled: true, priority: 3, count: 3 },
  git_history: { enabled: true, priority: 3, count: 15 },
})

const loading = ref(false)
const saving = ref(false)

// Methods
function toggleContext(key: string) {
  config.value[key].enabled = !config.value[key].enabled
  saveConfig() // Auto-save
}

function updatePriority(key: string, value: number) {
  config.value[key].priority = value
  saveConfig() // Auto-save
}

function updateDepth(key: string, value: string | number) {
  const contextDef = contexts.find((c) => c.key === key)
  if (!contextDef) return

  // Determine if this is a count-based or depth-based context
  if (key === 'memory_360' || key === 'git_history') {
    config.value[key].count = value as number
  } else {
    config.value[key].depth = value as string
  }
  saveConfig() // Auto-save
}

function getDepthValue(key: string): string | number | undefined {
  const contextConfig = config.value[key]
  if (!contextConfig) return undefined

  if (key === 'memory_360' || key === 'git_history') {
    return contextConfig.count
  }
  return contextConfig.depth
}

function formatOptions(context: { key: string; options?: (string | number)[] }) {
  if (!context.options) return []

  return context.options.map((opt) => {
    if (typeof opt === 'number') {
      if (context.key === 'memory_360') {
        return { title: `${opt} project${opt === 1 ? '' : 's'}`, value: opt }
      } else if (context.key === 'git_history') {
        if (opt === 0) return { title: 'None', value: opt }
        return { title: `${opt} commits`, value: opt }
      }
      return { title: String(opt), value: opt }
    }
    // String options - capitalize first letter
    return { title: opt.charAt(0).toUpperCase() + opt.slice(1).replace('_', ' '), value: opt }
  })
}

async function fetchConfig() {
  loading.value = true
  try {
    const response = await axios.get('/api/v1/users/me/field-priority')
    const priorities = response.data?.priorities || {}

    Object.entries(priorities).forEach(([key, value]) => {
      const numericPriority = typeof value === 'number' ? value : Number(value)
      if (config.value[key]) {
        config.value[key] = {
          ...config.value[key],
          enabled: numericPriority !== 4,
          priority: numericPriority || 3,
        }
      }
    })

    console.log('[CONTEXT PRIORITY CONFIG] Field priorities loaded from server')
  } catch (error) {
    console.error('[CONTEXT PRIORITY CONFIG] Failed to fetch config:', error)
    // Keep default values on error
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    await axios.put('/api/v1/users/me/field-priority', {
      version: '2.0',
      priorities: convertToBackendFormat(config.value),
    })
    console.log('[CONTEXT PRIORITY CONFIG] Field priorities saved successfully')
  } catch (error) {
    console.error('[CONTEXT PRIORITY CONFIG] Failed to save config:', error)
  } finally {
    saving.value = false
  }
}

function convertToBackendFormat(localConfig: Record<string, ContextConfig>): Record<string, number> {
  const priorities: Record<string, number> = {}
  Object.entries(localConfig).forEach(([key, value]) => {
    const priority = value.enabled ? value.priority : 4
    priorities[key] = priority
  })
  return priorities
}

// Lifecycle
onMounted(() => {
  fetchConfig()
})

// Expose for testing
defineExpose({
  contexts,
  priorityOptions,
  config,
  loading,
  saving,
  toggleContext,
  updatePriority,
  updateDepth,
  saveConfig,
})
</script>

<style scoped>
.context-row {
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

.context-row:last-of-type {
  border-bottom: none;
}

.locked-row {
  background-color: rgba(var(--v-theme-primary), 0.05);
  border-radius: 4px;
  padding-left: 12px;
  padding-right: 12px;
}

.context-label {
  min-width: 140px;
}

.compact-switch {
  margin: 0;
  padding: 0;
}

.compact-switch :deep(.v-switch__track) {
  height: 14px;
  width: 28px;
}

.compact-switch :deep(.v-switch__thumb) {
  height: 10px;
  width: 10px;
}

.compact-switch :deep(.v-selection-control) {
  min-height: auto;
}

.depth-select {
  max-width: 140px;
  min-width: 120px;
}

.depth-select :deep(.v-field__input) {
  font-size: 0.75rem;
  padding-top: 4px;
  padding-bottom: 4px;
}

.depth-select :deep(.v-field) {
  min-height: 32px;
}

.priority-select {
  max-width: 100px;
  min-width: 90px;
}

.priority-select :deep(.v-field__input) {
  font-size: 0.75rem;
  padding-top: 4px;
  padding-bottom: 4px;
}

.priority-select :deep(.v-field) {
  min-height: 32px;
}

/* Mobile responsive */
@media (max-width: 600px) {
  .context-row {
    flex-wrap: wrap;
  }

  .context-label {
    min-width: 100%;
    margin-bottom: 8px;
  }

  .depth-select,
  .priority-select {
    flex-grow: 1;
  }
}
</style>
