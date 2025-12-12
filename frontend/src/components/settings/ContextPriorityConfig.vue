<template>
  <v-card>
    <v-card-title>Context Priority Configuration</v-card-title>
    <v-card-text>
      <!-- Git Integration Alert -->
      <v-alert
        v-if="!props.gitIntegrationEnabled"
        type="info"
        variant="tonal"
        density="compact"
        class="mb-4"
      >
        <div>
          <strong>Git History is disabled</strong>
          <br />
          GitHub integration is currently disabled. Enable it in the
          <a
            @click="navigateToIntegrations"
            class="text-decoration-underline cursor-pointer"
            style="cursor: pointer"
          >
            Integrations tab
          </a>
          to use Git History context.
        </div>
      </v-alert>

      <!-- Locked Project Context -->
      <div class="context-row locked-row d-flex justify-space-between align-center py-3 mb-2">
        <div class="d-flex align-center">
          <v-icon size="small" color="primary" class="mr-2">mdi-lock</v-icon>
          <span class="text-subtitle-2 font-weight-medium">Project Context</span>
        </div>
        <v-chip size="small" color="primary" variant="flat"> Always Critical </v-chip>
      </div>

      <v-divider class="mb-4" />

      <!-- Section: Priority Configuration -->
      <div class="mb-4">
        <div class="text-subtitle-2 font-weight-medium mb-2">Priority Configuration (What to Fetch)</div>
        <v-alert type="info" variant="tonal" density="compact" class="mb-3">
          Set field priorities to control which context is included in agent prompts.
        </v-alert>

        <!-- Priority-only Context Rows -->
        <div
          v-for="context in priorityOnlyContexts"
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

          <!-- Priority Select -->
          <v-select
            :model-value="config[context.key]?.priority"
            @update:model-value="updatePriority(context.key, $event)"
            :items="priorityOptions"
            density="compact"
            variant="outlined"
            hide-details
            :aria-label="`${context.label} priority setting`"
            :data-testid="`priority-${context.key.replace('_', '-')}`"
            class="priority-select"
            :disabled="!config[context.key]?.enabled"
          />
        </div>
      </div>

      <v-divider class="my-4" />

      <!-- Section: Depth Configuration -->
      <div>
        <div class="text-subtitle-2 font-weight-medium mb-2">Depth Configuration (How Much Detail)</div>
        <v-alert type="info" variant="tonal" density="compact" class="mb-3">
          Control the level of detail for context fields with adjustable depth.
        </v-alert>

        <!-- Depth-controlled Context Rows -->
        <div
          v-for="context in depthControlledContexts"
          :key="context.key"
          class="context-row d-flex justify-space-between align-center py-2"
          :class="{ 'disabled-row': isContextDisabled(context.key) }"
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
              :aria-label="
                isContextDisabled(context.key)
                  ? `${context.label} disabled - GitHub integration required`
                  : `Toggle ${context.label}`
              "
              class="ml-2 compact-switch"
              :disabled="isContextDisabled(context.key)"
            />
            <v-tooltip
              v-if="context.helpText"
              :text="context.helpText"
              location="bottom"
            >
              <template #activator="{ props }">
                <v-icon v-bind="props" size="small" color="primary" class="ml-1">mdi-information-outline</v-icon>
              </template>
            </v-tooltip>
          </div>

          <!-- Depth/Count Select -->
          <v-select
            :model-value="getDepthValue(context.key)"
            @update:model-value="updateDepth(context.key, $event)"
            :items="formatOptions(context)"
            density="compact"
            variant="outlined"
            hide-details
            :aria-label="`${context.label} depth setting`"
            :data-testid="`depth-${context.key.replace('_', '-')}`"
            class="depth-select mx-2"
            :disabled="!config[context.key]?.enabled || isContextDisabled(context.key)"
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
            :data-testid="`priority-${context.key.replace('_', '-')}`"
            class="priority-select"
            :disabled="!config[context.key]?.enabled || isContextDisabled(context.key)"
          />
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import setupService from '@/services/setupService'

// Router for navigation
const router = useRouter()

// Accept git integration status as prop from parent (UserSettings.vue)
// Parent handles WebSocket listener to ensure it's always active
const props = defineProps({
  gitIntegrationEnabled: {
    type: Boolean,
    default: false,
  },
})

// Context definitions
// Priority-only fields (no depth controls)
const contexts = [
  { key: 'product_description', label: 'Product Description' },
  { key: 'tech_stack', label: 'Tech Stack' },
  { key: 'architecture', label: 'Architecture' },
  { key: 'testing', label: 'Testing' },
  // Depth-controlled fields
  {
    key: 'vision_documents',
    label: 'Vision Documents',
    helpText: 'Semantic compression using LSA extractive summarization'
  },
  {
    key: 'memory_360',
    label: '360 Memory',
    options: [1, 3, 5, 10],
    helpText: 'Number of previous project summaries to include'
  },
  {
    key: 'git_history',
    label: 'Git History',
    options: [5, 10, 25, 50, 100],
    helpText: 'Number of git commits in CLI examples'
  },
  {
    key: 'agent_templates',
    label: 'Agent Templates',
    options: ['type_only', 'full'],
    helpText: 'Type Only = Name/Version | Full = With descriptions'
  },
]

// Map UI categories to backend categories for API requests
// FIX: 1:1 mapping for all fields (was incorrectly grouping fields)
const UI_TO_BACKEND_CATEGORY_MAP: Record<string, string> = {
  product_description: 'product_core',
  tech_stack: 'tech_stack',
  architecture: 'architecture',
  testing: 'testing',
  vision_documents: 'vision_documents',
  agent_templates: 'agent_templates',
  memory_360: 'memory_360',
  git_history: 'git_history',
}

// Reverse mapping: backend keys to frontend keys
// FIX: 1:1 mapping for all fields (was incorrectly grouping fields)
const BACKEND_TO_UI_CATEGORY_MAP: Record<string, string[]> = {
  product_core: ['product_description'],
  tech_stack: ['tech_stack'],
  architecture: ['architecture'],
  testing: ['testing'],
  vision_documents: ['vision_documents'],
  agent_templates: ['agent_templates'],
  memory_360: ['memory_360'],
  git_history: ['git_history'],
}

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
  tech_stack: { enabled: true, priority: 2 },
  architecture: { enabled: true, priority: 2 },
  testing: { enabled: true, priority: 2 },
  vision_documents: { enabled: true, priority: 2, depth: 'moderate' },
  memory_360: { enabled: true, priority: 2, count: 3 },
  git_history: { enabled: false, priority: 4, count: 25 },
  agent_templates: { enabled: true, priority: 2, depth: 'type_only' },
})

const loading = ref(false)
const saving = ref(false)
const fetchingVisionStats = ref(false)
const visionStats = ref(null)

// Computed properties to split contexts into two groups
const priorityOnlyContexts = computed(() => {
  return contexts.filter(c => !c.options)
})

const depthControlledContexts = computed(() => {
  return contexts.filter(c => c.options || c.key === 'vision_documents')
})

// Methods
function toggleContext(key: string) {
  const newEnabled = !config.value[key].enabled
  config.value[key].enabled = newEnabled

  // If enabling from EXCLUDED, set to Reference (priority 3)
  if (newEnabled && config.value[key].priority === 4) {
    config.value[key].priority = 3  // Reference (NICE_TO_HAVE)
  }
  // If disabling, set to EXCLUDED (priority 4)
  else if (!newEnabled) {
    config.value[key].priority = 4
  }

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
  } else if (key === 'vision_documents' || key === 'agent_templates') {
    config.value[key].depth = value as string
  }
  saveConfig() // Auto-save
}

function getDepthValue(key: string): string | number | undefined {
  const contextConfig = config.value[key]
  if (!contextConfig) return undefined

  if (key === 'memory_360' || key === 'git_history') {
    return contextConfig.count
  } else if (key === 'vision_documents' || key === 'agent_templates') {
    return contextConfig.depth
  }
  return undefined
}

function formatOptions(context: { key: string; options?: (string | number)[] }) {
  // Handover 0345e: Semantic compression levels (Light/Moderate/Heavy/Full)
  // Sumy LSA summarization is always enabled, no toggle needed
  if (context.key === 'vision_documents') {
    return [
      { title: 'None', value: 'none', subtitle: '0 tokens' },
      { title: 'Light (5K tokens)', value: 'light', subtitle: '~250 sentences, 87% compression' },
      { title: 'Moderate (12.5K tokens)', value: 'moderate', subtitle: '~625 sentences, 69% compression' },
      { title: 'Heavy (25K tokens)', value: 'heavy', subtitle: '~1,250 sentences, 37% compression' },
      { title: 'Full (All)', value: 'full', subtitle: 'Complete document, no compression' }
    ]
  }
  
  if (!context.options) return []

  return context.options.map((opt) => {
    if (typeof opt === 'number') {
      if (context.key === 'memory_360') {
        return { title: `${opt} project${opt === 1 ? '' : 's'}`, value: opt }
      } else if (context.key === 'git_history') {
        return { title: `${opt} commits`, value: opt }
      }
      return { title: String(opt), value: opt }
    }
    // String options (other than vision_documents)
    // Default: capitalize first letter
    return { title: opt.charAt(0).toUpperCase() + opt.slice(1).replace('_', ' '), value: opt }
  })
}

function isContextDisabled(contextKey: string): boolean {
  // Only git_history is disabled when Git integration is OFF
  return contextKey === 'git_history' && !props.gitIntegrationEnabled
}

function navigateToIntegrations() {
  // Navigate to UserSettings with integrations tab query parameter
  router.push({ name: 'UserSettings', query: { tab: 'integrations' } })
}


async function fetchVisionStats() {
  fetchingVisionStats.value = true
  try {
    const response = await axios.get('/api/v1/products/active/vision-stats')
    visionStats.value = response.data
    console.log('[CONTEXT PRIORITY CONFIG] Vision stats loaded:', visionStats.value)
  } catch (error) {
    console.warn('[CONTEXT PRIORITY CONFIG] Failed to fetch vision stats:', error)
    // Gracefully handle error - use null and formatOptions will show defaults
    visionStats.value = null
  } finally {
    fetchingVisionStats.value = false
  }
}

function formatTokenCount(tokens) {
  if (tokens >= 1000) {
    const k = (tokens / 1000).toFixed(1)
    return k + 'K'
  }
  return tokens.toString()
}

async function fetchConfig() {
  loading.value = true
  try {
    // Fetch priorities from field-priority endpoint
    const prioritiesResponse = await axios.get('/api/v1/users/me/field-priority')
    const priorities = prioritiesResponse.data?.priorities || {}

    // Apply backend priorities to frontend keys using reverse mapping
    Object.entries(priorities).forEach(([backendKey, value]) => {
      const numericPriority = typeof value === 'number' ? value : Number(value)

      // Get frontend keys for this backend key
      const frontendKeys = BACKEND_TO_UI_CATEGORY_MAP[backendKey] || [backendKey]

      // Apply to all matching frontend keys
      frontendKeys.forEach((frontendKey) => {
        if (config.value[frontendKey]) {
          config.value[frontendKey] = {
            ...config.value[frontendKey],
            enabled: numericPriority !== 4,
            priority: numericPriority || 3,
          }
        }
      })
    })

    // Fetch depth config from context/depth endpoint (only 4 fields with depth controls)
    try {
      const depthResponse = await axios.get('/api/v1/users/me/context/depth')
      const depthData = depthResponse.data?.depth_config || {}

      // Map backend field names back to frontend structure
      if (depthData.memory_last_n_projects && config.value.memory_360) {
        config.value.memory_360.count = depthData.memory_last_n_projects
      }
      if (depthData.git_commits && config.value.git_history) {
        config.value.git_history.count = depthData.git_commits
      }
      if (depthData.vision_document_depth && config.value.vision_documents) {
        config.value.vision_documents.depth = depthData.vision_document_depth
      }
      if (depthData.agent_template_detail && config.value.agent_templates) {
        config.value.agent_templates.depth = depthData.agent_template_detail
      }

      console.log('[CONTEXT PRIORITY CONFIG] Field priorities and depth config loaded from server')
    } catch (depthError) {
      // Depth endpoint is optional - continue with defaults if it fails
      console.warn('[CONTEXT PRIORITY CONFIG] Depth config not available, using defaults:', depthError)
    }
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
    // Save priorities to field-priority endpoint
    await axios.put('/api/v1/users/me/field-priority', {
      version: '2.0',
      priorities: convertToBackendFormat(config.value),
    })
    console.log('[CONTEXT PRIORITY CONFIG] Field priorities saved successfully')

    // Save depth config to context/depth endpoint (only 4 fields with depth controls)
    try {
      await axios.put('/api/v1/users/me/context/depth', {
        depth_config: {
          memory_last_n_projects: config.value.memory_360?.count || 3,
          git_commits: config.value.git_history?.count || 25,
          vision_document_depth: config.value.vision_documents?.depth || 'moderate',
          agent_template_detail: config.value.agent_templates?.depth || 'type_only',
        }
      })
      console.log('[CONTEXT PRIORITY CONFIG] Depth config saved successfully')
    } catch (depthError) {
      // Log depth save error but don't fail the overall save
      console.warn('[CONTEXT PRIORITY CONFIG] Warning: Depth config save failed:', depthError)
    }
  } catch (error) {
    console.error('[CONTEXT PRIORITY CONFIG] Failed to save config:', error)
  } finally {
    saving.value = false
  }
}

function convertToBackendFormat(localConfig: Record<string, ContextConfig>): Record<string, number> {
  const backendPriorities: Record<string, number> = {}

  // Map UI categories to backend categories and aggregate priorities
  Object.entries(localConfig).forEach(([uiKey, value]) => {
    const backendKey = UI_TO_BACKEND_CATEGORY_MAP[uiKey] || uiKey
    const priority = value.enabled ? value.priority : 4

    // If multiple UI fields map to same backend category, take highest priority (lowest number)
    if (!backendPriorities[backendKey] || priority < backendPriorities[backendKey]) {
      backendPriorities[backendKey] = priority
    }
  })

  // CRITICAL: Always include project_context with priority 1 (locked field, always CRITICAL)
  backendPriorities.project_context = 1

  return backendPriorities
}

// Lifecycle
onMounted(async () => {
  // Fetch context config on mount
  // Git integration status is passed from parent via props (UserSettings.vue)
  fetchConfig()
  // Fetch vision stats for dynamic token counts
  await fetchVisionStats()
})

// Expose for testing
defineExpose({
  contexts,
  priorityOnlyContexts,
  depthControlledContexts,
  priorityOptions,
  config,
  loading,
  saving,
  fetchingVisionStats,
  visionStats,
  toggleContext,
  updatePriority,
  updateDepth,
  saveConfig,
  isContextDisabled,
  navigateToIntegrations,
  fetchVisionStats,
  formatTokenCount,
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

.disabled-row {
  opacity: 0.5;
  pointer-events: none;
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
