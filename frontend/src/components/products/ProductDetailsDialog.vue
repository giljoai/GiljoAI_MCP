<template>
  <v-dialog v-model="isOpen" max-width="600">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-information-outline</v-icon>
        Product Details
        <v-spacer></v-spacer>
        <v-btn icon variant="text" @click="handleClose">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider></v-divider>

      <v-card-text v-if="product">
        <!-- Product Name -->
        <div class="text-h6 mb-2">{{ product.name }}</div>
        <div class="text-caption text-medium-emphasis mb-4">ID: {{ product.id }}</div>

        <!-- Description -->
        <div class="mb-4">
          <div class="text-subtitle-2 mb-1">Description</div>
          <div class="text-body-2">
            {{ product.description || 'No description provided' }}
          </div>
        </div>

        <!-- Statistics -->
        <div class="mb-4">
          <div class="text-subtitle-2 mb-2">Statistics</div>
          <v-row dense>
            <v-col cols="6">
              <div class="text-caption">Unresolved Tasks</div>
              <div class="text-h6">{{ product.unresolved_tasks || 0 }}</div>
            </v-col>
            <v-col cols="6">
              <div class="text-caption">Unfinished Projects</div>
              <div class="text-h6">{{ product.unfinished_projects || 0 }}</div>
            </v-col>
          </v-row>
        </div>

        <!-- Vision Documents -->
        <div>
          <div class="text-subtitle-2 mb-2">Vision Documents ({{ visionDocuments.length }})</div>

          <v-list v-if="visionDocuments.length > 0" density="compact">
            <v-card v-for="doc in visionDocuments" :key="doc.id" variant="outlined" class="mb-2">
              <v-list-item class="px-3">
                <template v-slot:prepend>
                  <v-icon color="primary">mdi-file-document</v-icon>
                </template>

                <v-list-item-title>{{ doc.filename || doc.document_name }}</v-list-item-title>
                <v-list-item-subtitle>
                  {{ doc.is_summarized ? 'Summarized' : 'Processing' }} •
                  {{ formatFileSize(doc.file_size || 0) }}
                </v-list-item-subtitle>
              </v-list-item>

              <!-- Summary Levels Preview -->
              <v-card-text v-if="doc.has_summaries" class="pt-0 pb-2">
                <div class="text-caption text-medium-emphasis mb-1">Summary Previews</div>
                <div class="d-flex justify-space-around">
                  <v-chip
                    size="small"
                    variant="tonal"
                    color="success"
                    :disabled="!doc.summary_light"
                    @click="showSummary(doc, 'low')"
                    class="cursor-pointer"
                  >
                    Low
                    <v-icon end size="14">mdi-eye</v-icon>
                    <v-tooltip activator="parent" location="bottom">
                      {{ doc.summary_light_tokens ? `~${formatTokens(doc.summary_light_tokens)} tokens` : 'Not available' }}
                    </v-tooltip>
                  </v-chip>
                  <v-chip
                    size="small"
                    variant="tonal"
                    color="warning"
                    :disabled="!doc.summary_moderate"
                    @click="showSummary(doc, 'medium')"
                    class="cursor-pointer"
                  >
                    Medium
                    <v-icon end size="14">mdi-eye</v-icon>
                    <v-tooltip activator="parent" location="bottom">
                      {{ doc.summary_moderate_tokens ? `~${formatTokens(doc.summary_moderate_tokens)} tokens` : 'Not available' }}
                    </v-tooltip>
                  </v-chip>
                  <v-chip
                    size="small"
                    variant="tonal"
                    color="error"
                    :disabled="!doc.summary_heavy"
                    @click="showSummary(doc, 'high')"
                    class="cursor-pointer"
                  >
                    High
                    <v-icon end size="14">mdi-eye</v-icon>
                    <v-tooltip activator="parent" location="bottom">
                      {{ doc.summary_heavy_tokens ? `~${formatTokens(doc.summary_heavy_tokens)} tokens` : 'Not available' }}
                    </v-tooltip>
                  </v-chip>
                </div>
              </v-card-text>
              <v-card-text v-else class="pt-0 pb-2">
                <div class="text-caption text-medium-emphasis">
                  <v-icon size="12" class="mr-1">mdi-information-outline</v-icon>
                  No summaries generated yet
                </div>
              </v-card-text>
            </v-card>
          </v-list>

          <v-alert v-else type="info" variant="tonal" density="compact">
            No vision documents attached
          </v-alert>

          <!-- Aggregate Stats (only show if documents exist) -->
          <v-card v-if="visionDocuments.length > 0" variant="tonal" color="primary" class="mt-3">
            <v-card-text class="py-2">
              <div class="text-caption">
                <v-icon size="16" class="mr-1">mdi-file-document-multiple</v-icon>
                <strong>Documents:</strong> {{ visionDocuments.length }} ({{ summarizedCount }} summarized)<br />
                <v-icon size="16" class="mr-1">mdi-folder-outline</v-icon>
                <strong>Total size:</strong> {{ totalFileSize }}
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- Configuration Data Display -->
        <div v-if="product.has_config_data" class="mt-4">
          <v-divider class="mb-3"></v-divider>
          <div class="text-subtitle-2 mb-2">Configuration Data</div>

          <v-expansion-panels variant="accordion">
            <!-- Tech Stack -->
            <v-expansion-panel v-if="product.config_data?.tech_stack">
              <v-expansion-panel-title>
                <v-icon start>mdi-code-tags</v-icon>
                Tech Stack
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-if="product.config_data.tech_stack.languages" class="mb-2">
                  <div class="text-caption font-weight-bold">Languages:</div>
                  <div class="text-body-2">{{ product.config_data.tech_stack.languages }}</div>
                </div>
                <div v-if="product.config_data.tech_stack.frontend" class="mb-2">
                  <div class="text-caption font-weight-bold">Frontend:</div>
                  <div class="text-body-2">{{ product.config_data.tech_stack.frontend }}</div>
                </div>
                <div v-if="product.config_data.tech_stack.backend" class="mb-2">
                  <div class="text-caption font-weight-bold">Backend:</div>
                  <div class="text-body-2">{{ product.config_data.tech_stack.backend }}</div>
                </div>
                <div v-if="product.config_data.tech_stack.database">
                  <div class="text-caption font-weight-bold">Databases:</div>
                  <div class="text-body-2">{{ product.config_data.tech_stack.database }}</div>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Architecture -->
            <v-expansion-panel v-if="product.config_data?.architecture">
              <v-expansion-panel-title>
                <v-icon start>mdi-sitemap</v-icon>
                Architecture
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-if="product.config_data.architecture.pattern" class="mb-2">
                  <div class="text-caption font-weight-bold">Pattern:</div>
                  <div class="text-body-2">{{ product.config_data.architecture.pattern }}</div>
                </div>
                <div v-if="product.config_data.architecture.api_style" class="mb-2">
                  <div class="text-caption font-weight-bold">API Style:</div>
                  <div class="text-body-2">{{ product.config_data.architecture.api_style }}</div>
                </div>
                <div v-if="product.config_data.architecture.design_patterns">
                  <div class="text-caption font-weight-bold">Design Patterns:</div>
                  <div class="text-body-2">
                    {{ product.config_data.architecture.design_patterns }}
                  </div>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Features & Testing -->
            <v-expansion-panel
              v-if="product.config_data?.features || product.config_data?.test_config"
            >
              <v-expansion-panel-title>
                <v-icon start>mdi-star-outline</v-icon>
                Features & Testing
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-if="product.config_data.features?.core" class="mb-2">
                  <div class="text-caption font-weight-bold">Core Features:</div>
                  <div class="text-body-2">{{ product.config_data.features.core }}</div>
                </div>
                <div v-if="product.config_data.test_config?.strategy" class="mb-2">
                  <div class="text-caption font-weight-bold">Testing Strategy:</div>
                  <div class="text-body-2">{{ product.config_data.test_config.strategy }}</div>
                </div>
                <div v-if="product.config_data.test_config?.coverage_target">
                  <div class="text-caption font-weight-bold">Coverage Target:</div>
                  <div class="text-body-2">
                    {{ product.config_data.test_config.coverage_target }}%
                  </div>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </div>

        <!-- Created/Updated -->
        <div class="text-caption text-medium-emphasis mt-4">
          Created: {{ formatDate(product.created_at) }}<br />
          Updated: {{ formatDate(product.updated_at) }}
        </div>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="handleClose">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Summary Preview Dialog -->
  <v-dialog v-model="summaryDialog" max-width="800" scrollable>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start :color="summaryLevelColor">mdi-text-box-outline</v-icon>
        {{ summaryTitle }}
        <v-spacer></v-spacer>
        <v-chip size="small" :color="summaryLevelColor" variant="tonal" class="mr-2">
          {{ summaryLevel }}
        </v-chip>
        <v-btn icon variant="text" @click="summaryDialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider></v-divider>

      <v-card-text class="summary-content" style="max-height: 60vh; overflow-y: auto;">
        <div class="text-caption text-medium-emphasis mb-2">
          <v-icon size="14" class="mr-1">mdi-counter</v-icon>
          ~{{ formatTokens(summaryTokens) }} tokens
        </div>
        <div class="text-body-2" style="white-space: pre-wrap;">{{ summaryContent }}</div>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="summaryDialog = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  product: {
    type: Object,
    default: () => ({}),
  },
  visionDocuments: {
    type: Array,
    default: () => [],
  },
  stats: {
    type: Object,
    default: () => ({ unresolved_tasks: 0, unfinished_projects: 0 }),
  },
})

const emit = defineEmits(['update:modelValue'])

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const handleClose = () => {
  emit('update:modelValue', false)
}

// Summary preview dialog state
const summaryDialog = ref(false)
const summaryContent = ref('')
const summaryTitle = ref('')
const summaryLevel = ref('')
const summaryTokens = ref(0)

const summaryLevelColor = computed(() => {
  switch (summaryLevel.value) {
    case 'Low': return 'success'
    case 'Medium': return 'warning'
    case 'High': return 'error'
    default: return 'primary'
  }
})

function showSummary(doc, level) {
  const levelMap = {
    low: { field: 'summary_light', tokens: 'summary_light_tokens', label: 'Low' },
    medium: { field: 'summary_moderate', tokens: 'summary_moderate_tokens', label: 'Medium' },
    high: { field: 'summary_heavy', tokens: 'summary_heavy_tokens', label: 'High' },
  }

  const config = levelMap[level]
  if (!config || !doc[config.field]) return

  summaryContent.value = doc[config.field]
  summaryTitle.value = `${doc.document_name || doc.filename} - Summary`
  summaryLevel.value = config.label
  summaryTokens.value = doc[config.tokens] || 0
  summaryDialog.value = true
}

function formatTokens(tokens) {
  if (!tokens) return '0'
  if (tokens >= 1000) {
    return (tokens / 1000).toFixed(1) + 'K'
  }
  return tokens.toString()
}

// Computed properties for aggregate stats (Handover 0246b: removed chunk count)
const summarizedCount = computed(() => {
  return props.visionDocuments.filter(doc => doc.is_summarized).length
})

const totalFileSize = computed(() => {
  const bytes = props.visionDocuments.reduce((sum, doc) => sum + (doc.file_size || 0), 0)
  return formatFileSize(bytes)
})

// Helper functions
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
</script>
