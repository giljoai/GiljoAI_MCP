<template>
  <v-dialog v-model="isOpen" max-width="600">
    <v-card v-draggable>
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
        <div class="text-caption text-medium-emphasis mb-2">ID: {{ product.id }}</div>

        <!-- Context Tuning (Handover 0831) -->
        <div class="d-flex align-center mb-4">
          <v-btn
            variant="outlined"
            color="primary"
            size="small"
            prepend-icon="mdi-tune"
            @click="showTuningMenu = !showTuningMenu"
          >
            Tune Context
          </v-btn>
        </div>

        <ProductTuningMenu
          v-if="showTuningMenu"
          :product-id="product.id"
          class="mb-4"
        />

        <ProductTuningReview
          v-if="product.tuning_state?.pending_proposals"
          :product-id="product.id"
          :pending-proposals="product.tuning_state.pending_proposals"
          class="mb-4"
        />

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
                  {{ doc.is_summarized ? 'Summarized' : 'Processing' }}
                  <span v-if="doc.chunked"> • Chunked ({{ doc.chunk_count }} chunks)</span>
                  • {{ formatFileSize(doc.file_size || 0) }}
                </v-list-item-subtitle>
              </v-list-item>

              <!-- Summary Levels Preview (Handover 0246b: light/medium/full) -->
              <v-card-text v-if="doc.is_summarized || doc.vision_document" class="pt-0 pb-2">
                <div class="text-caption text-medium-emphasis mb-1">Summary Previews</div>
                <div class="d-flex justify-space-around">
                  <v-chip
                    size="small"
                    variant="tonal"
                    color="success"
                    :loading="loadingSummary.docId === doc.id && loadingSummary.level === 'light'"
                    class="cursor-pointer"
                    @click="showSummary(doc, 'light')"
                  >
                    Light
                    <v-icon end size="14">mdi-eye</v-icon>
                    <v-tooltip activator="parent" location="bottom">
                      {{ doc.summary_light_tokens ? `~${formatTokens(doc.summary_light_tokens)} tokens (33%)` : 'Click to load' }}
                    </v-tooltip>
                  </v-chip>
                  <v-chip
                    size="small"
                    variant="tonal"
                    color="warning"
                    :loading="loadingSummary.docId === doc.id && loadingSummary.level === 'medium'"
                    class="cursor-pointer"
                    @click="showSummary(doc, 'medium')"
                  >
                    Medium
                    <v-icon end size="14">mdi-eye</v-icon>
                    <v-tooltip activator="parent" location="bottom">
                      {{ doc.summary_medium_tokens ? `~${formatTokens(doc.summary_medium_tokens)} tokens (66%)` : 'Click to load' }}
                    </v-tooltip>
                  </v-chip>
                  <v-chip
                    size="small"
                    variant="tonal"
                    color="primary-lighten-1"
                    :loading="loadingSummary.docId === doc.id && loadingSummary.level === 'full'"
                    class="cursor-pointer"
                    @click="showSummary(doc, 'full')"
                  >
                    Full
                    <v-icon end size="14">mdi-eye</v-icon>
                    <v-tooltip activator="parent" location="bottom">
                      {{ doc.original_token_count ? `~${formatTokens(doc.original_token_count)} tokens (100%)` : 'Click to load' }}
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

          <!-- AI Analysis Result (Handover 0842d) -->
          <v-alert
            v-if="visionAnalysisResult"
            type="success"
            variant="tonal"
            density="compact"
            class="mt-3 mb-3"
            closable
            @click:close="visionAnalysisResult = null"
          >
            <div class="text-body-2">
              AI populated {{ visionAnalysisResult.fields_written }} product fields —
              <span
                class="text-primary"
                style="cursor: pointer"
                role="button"
                tabindex="0"
                @click="$emit('refresh-product')"
                @keydown.enter="$emit('refresh-product')"
              >review in Product Info</span>
            </div>
          </v-alert>

          <!-- Aggregate Stats (only show if documents exist) -->
          <v-card v-if="visionDocuments.length > 0" variant="tonal" color="primary" class="mt-3">
            <v-card-text class="py-2">
              <div class="text-caption">
                <v-icon size="16" class="mr-1">mdi-file-document-multiple</v-icon>
                <strong>Documents:</strong> {{ visionDocuments.length }} ({{ summarizedCount }} summarized, {{ chunkedCount }} chunked)
                <br />
                <v-icon size="16" class="mr-1">mdi-database</v-icon>
                <strong>Total chunks:</strong> {{ totalChunks }}
                <br />
                <v-icon size="16" class="mr-1">mdi-folder-outline</v-icon>
                <strong>Total size:</strong> {{ totalFileSize }}
              </div>
            </v-card-text>
          </v-card>

        <!-- Consolidated Vision Summaries (Handover 0377) -->
        <div v-if="product?.consolidated_vision_light" class="mt-4">
          <div class="text-subtitle-2 mb-2">
            <v-icon start size="20">mdi-database-merge</v-icon>
            Consolidated Vision Summaries
          </div>
          <div class="d-flex flex-wrap ga-2 mb-3">
            <v-chip
              size="small"
              variant="tonal"
              color="success"
              class="cursor-pointer"
              @click="showConsolidatedSummary('light')"
            >
              Light (33%)
              <v-tooltip activator="parent" location="bottom">
                ~{{ formatTokens(product.consolidated_vision_light_tokens) }} tokens
              </v-tooltip>
            </v-chip>

            <v-chip
              v-if="product?.consolidated_vision_medium"
              size="small"
              variant="tonal"
              color="info"
              class="cursor-pointer"
              @click="showConsolidatedSummary('medium')"
            >
              Medium (66%)
              <v-tooltip activator="parent" location="bottom">
                ~{{ formatTokens(product.consolidated_vision_medium_tokens) }} tokens
              </v-tooltip>
            </v-chip>
          </div>

          <div v-if="product?.consolidated_at" class="text-caption text-medium-emphasis mb-3">
            <v-icon size="14" class="mr-1">mdi-clock-outline</v-icon>
            Last consolidated: {{ formatDate(product.consolidated_at) }}
            <span v-if="product?.consolidated_vision_hash" class="ml-2">
              Hash: {{ product.consolidated_vision_hash.substring(0, 8) }}...
            </span>
          </div>

          <v-btn
            size="small"
            variant="outlined"
            color="info"
            :loading="regeneratingConsolidation"
            :disabled="!visionDocuments?.length"
            class="mb-2"
            @click="regenerateConsolidation"
          >
            <v-icon start>mdi-refresh</v-icon>
            Regenerate
          </v-btn>
        </div>
        </div>

        <!-- Configuration Data Display -->
        <div v-if="product.tech_stack || product.architecture || product.test_config || product.core_features || product.brand_guidelines" class="mt-4">
          <v-divider class="mb-3"></v-divider>
          <div class="text-subtitle-2 mb-2">Configuration Data</div>

          <v-expansion-panels variant="accordion">
            <!-- Tech Stack -->
            <v-expansion-panel v-if="product.tech_stack">
              <v-expansion-panel-title>
                <v-icon start>mdi-code-tags</v-icon>
                Tech Stack
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-if="product.tech_stack.programming_languages" class="mb-2">
                  <div class="text-caption font-weight-bold">Programming Languages:</div>
                  <div class="text-body-2">{{ product.tech_stack.programming_languages }}</div>
                </div>
                <div v-if="product.tech_stack.frontend_frameworks" class="mb-2">
                  <div class="text-caption font-weight-bold">Frontend Frameworks:</div>
                  <div class="text-body-2">{{ product.tech_stack.frontend_frameworks }}</div>
                </div>
                <div v-if="product.tech_stack.backend_frameworks" class="mb-2">
                  <div class="text-caption font-weight-bold">Backend Frameworks:</div>
                  <div class="text-body-2">{{ product.tech_stack.backend_frameworks }}</div>
                </div>
                <div v-if="product.tech_stack.databases_storage" class="mb-2">
                  <div class="text-caption font-weight-bold">Databases & Storage:</div>
                  <div class="text-body-2">{{ product.tech_stack.databases_storage }}</div>
                </div>
                <div v-if="product.target_platforms && product.target_platforms.length">
                  <div class="text-caption font-weight-bold">Target Platforms:</div>
                  <div class="text-body-2">{{ product.target_platforms.map(p => formatPlatform(p)).join(', ') }}</div>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Architecture -->
            <v-expansion-panel v-if="product.architecture">
              <v-expansion-panel-title>
                <v-icon start>mdi-sitemap</v-icon>
                Architecture
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-if="product.architecture.primary_pattern" class="mb-2">
                  <div class="text-caption font-weight-bold">Primary Pattern:</div>
                  <div class="text-body-2">{{ product.architecture.primary_pattern }}</div>
                </div>
                <div v-if="product.architecture.api_style" class="mb-2">
                  <div class="text-caption font-weight-bold">API Style:</div>
                  <div class="text-body-2">{{ product.architecture.api_style }}</div>
                </div>
                <div v-if="product.architecture.design_patterns" class="mb-2">
                  <div class="text-caption font-weight-bold">Design Patterns:</div>
                  <div class="text-body-2">
                    {{ product.architecture.design_patterns }}
                  </div>
                </div>
                <div v-if="product.architecture.coding_conventions">
                  <div class="text-caption font-weight-bold">Coding Conventions:</div>
                  <div class="text-body-2" style="white-space: pre-line">{{ product.architecture.coding_conventions }}</div>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Features & Testing -->
            <!-- Brand Guidelines -->
            <v-expansion-panel v-if="product.brand_guidelines">
              <v-expansion-panel-title>
                <v-icon start>mdi-palette-outline</v-icon>
                Brand & Design Guidelines
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div class="text-body-2" style="white-space: pre-line">{{ product.brand_guidelines }}</div>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Features & Testing -->
            <v-expansion-panel
              v-if="product.core_features || product.test_config"
            >
              <v-expansion-panel-title>
                <v-icon start>mdi-star-outline</v-icon>
                Features & Testing
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-if="product.core_features" class="mb-2">
                  <div class="text-caption font-weight-bold">Core Features:</div>
                  <div class="text-body-2">{{ product.core_features }}</div>
                </div>
                <div v-if="product.test_config?.test_strategy" class="mb-2">
                  <div class="text-caption font-weight-bold">Test Strategy:</div>
                  <div class="text-body-2">{{ product.test_config.test_strategy }}</div>
                </div>
                <div v-if="product.test_config?.coverage_target">
                  <div class="text-caption font-weight-bold">Coverage Target:</div>
                  <div class="text-body-2">
                    {{ product.test_config.coverage_target }}%
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
    <v-card v-draggable>
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

  <!-- Consolidated Summary Viewer Dialog (Handover 0377) -->
  <v-dialog v-model="consolidatedSummaryDialog" max-width="800" scrollable>
    <v-card v-draggable>
      <v-card-title class="d-flex align-center">
        <v-icon start color="teal">mdi-database-merge</v-icon>
        {{ consolidatedSummaryTitle }}
        <v-spacer></v-spacer>
        <v-chip size="small" :color="consolidatedSummaryColor" variant="tonal" class="mr-2">
          {{ consolidatedSummaryLevel }}
        </v-chip>
        <v-btn icon variant="text" @click="consolidatedSummaryDialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider></v-divider>

      <v-card-text class="summary-content" style="max-height: 60vh; overflow-y: auto;">
        <div class="text-caption text-medium-emphasis mb-2">
          <v-icon size="14" class="mr-1">mdi-counter</v-icon>
          ~{{ formatTokens(consolidatedSummaryTokens) }} tokens
          <span v-if="consolidatedSummaryHash" class="ml-2">
            Hash: {{ consolidatedSummaryHash.substring(0, 12) }}...
          </span>
        </div>
        <div class="text-body-2" style="white-space: pre-wrap;">{{ consolidatedSummaryContent }}</div>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="consolidatedSummaryDialog = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import api from '@/services/api'
import { useFormatDate } from '@/composables/useFormatDate'
import ProductTuningMenu from './ProductTuningMenu.vue'
import ProductTuningReview from './ProductTuningReview.vue'

const { formatDate } = useFormatDate()

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
  autoExpandTuning: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'refresh-product'])

// Context Tuning toggle (Handover 0831)
const showTuningMenu = ref(false)

// Vision analysis result (Handover 0842d)
const visionAnalysisResult = ref(null)

function handleVisionAnalysisComplete(event) {
  if (event.detail?.product_id === props.product?.id) {
    visionAnalysisResult.value = event.detail
  }
}

onMounted(() => {
  window.addEventListener('vision-analysis-complete', handleVisionAnalysisComplete)
})

onUnmounted(() => {
  window.removeEventListener('vision-analysis-complete', handleVisionAnalysisComplete)
})

// Handover 0842d: Auto-expand tuning when opened via tune button
watch(
  () => props.modelValue,
  (open) => {
    if (open && props.autoExpandTuning) {
      showTuningMenu.value = true
    }
  },
)

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

// Consolidated summary dialog state (Handover 0377)
const consolidatedSummaryDialog = ref(false)
const consolidatedSummaryContent = ref('')
const consolidatedSummaryTitle = ref('')
const consolidatedSummaryLevel = ref('')
const consolidatedSummaryTokens = ref(0)
const consolidatedSummaryHash = ref('')
const regeneratingConsolidation = ref(false)

const summaryLevelColor = computed(() => {
  // Handover 0246b: Updated to Light/Medium/Full
  switch (summaryLevel.value) {
    case 'Light': return 'success'
    case 'Medium': return 'warning'
    case 'Full': return 'primary-lighten-1'  // Project's lightest blue
    default: return 'primary-lighten-1'
  }
})

const consolidatedSummaryColor = computed(() => {
  // Handover 0377: Consolidated vision summaries
  switch (consolidatedSummaryLevel.value) {
    case 'Light': return 'success'
    case 'Medium': return 'info'
    default: return 'teal'
  }
})

// Track which doc/level is loading
const loadingSummary = ref({ docId: null, level: null })

/**
 * Show document summary (light, medium, or full)
 * Fetches from API if not cached in doc object
 */
async function showSummary(doc, level) {
  // Handover 0246b: Updated to light/medium/full
  const levelMap = {
    light: { field: 'summary_light', tokens: 'summary_light_tokens', label: 'Light' },
    medium: { field: 'summary_medium', tokens: 'summary_medium_tokens', label: 'Medium' },
    full: { field: 'vision_document', tokens: 'original_token_count', label: 'Full' },
  }

  const config = levelMap[level]
  if (!config) return

  // If data is already cached, show it immediately
  if (doc[config.field]) {
    summaryContent.value = doc[config.field]
    summaryTitle.value = `${doc.document_name || doc.filename} - ${level === 'full' ? 'Full Document' : 'Summary'}`
    summaryLevel.value = config.label
    summaryTokens.value = doc[config.tokens] || 0
    summaryDialog.value = true
    return
  }

  // Fetch from API (like showFullDocument does)
  try {
    loadingSummary.value = { docId: doc.id, level }
    const response = await api.visionDocuments.get(doc.id)
    const fullDoc = response.data

    // Cache all fields on the doc object for future use
    doc.vision_document = fullDoc.vision_document
    doc.summary_light = fullDoc.summary_light
    doc.summary_medium = fullDoc.summary_medium
    doc.summary_light_tokens = fullDoc.summary_light_tokens
    doc.summary_medium_tokens = fullDoc.summary_medium_tokens
    doc.original_token_count = fullDoc.original_token_count

    const content = fullDoc[config.field]
    if (!content) {
      summaryContent.value = `No ${config.label.toLowerCase()} summary available for this document.`
      summaryTitle.value = `${doc.document_name || doc.filename} - Not Available`
      summaryLevel.value = config.label
      summaryTokens.value = 0
      summaryDialog.value = true
      return
    }

    summaryContent.value = content
    summaryTitle.value = `${doc.document_name || doc.filename} - ${level === 'full' ? 'Full Document' : 'Summary'}`
    summaryLevel.value = config.label
    summaryTokens.value = fullDoc[config.tokens] || 0
    summaryDialog.value = true
  } catch (error) {
    console.error('Failed to fetch document:', error)
    summaryContent.value = 'Error: Could not load document content'
    summaryTitle.value = `${doc.document_name || doc.filename} - Error`
    summaryLevel.value = config.label
    summaryTokens.value = 0
    summaryDialog.value = true
  } finally {
    loadingSummary.value = { docId: null, level: null }
  }
}


function formatTokens(tokens) {
  if (!tokens) return '0'
  if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(1)  }K`
  }
  return tokens.toString()
}

// Computed properties for aggregate stats (Handover 0347: restored chunk count)
const summarizedCount = computed(() => {
  return props.visionDocuments.filter(doc => doc.is_summarized).length
})

const chunkedCount = computed(() => {
  return props.visionDocuments.filter(doc => doc.chunked).length
})

const totalChunks = computed(() => {
  return props.visionDocuments.reduce((sum, doc) => sum + (doc.chunk_count || 0), 0)
})

const totalFileSize = computed(() => {
  const bytes = props.visionDocuments.reduce((sum, doc) => sum + (doc.file_size || 0), 0)
  return formatFileSize(bytes)
})

// Helper functions
function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes  } B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)  } KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)  } MB`
}


function formatPlatform(platform) {
  const labels = {
    windows: 'Windows',
    linux: 'Linux',
    macos: 'macOS',
    all: 'All (Cross-platform)'
  }
  return labels[platform] || platform
}

/**
 * Show consolidated vision summary (Handover 0377)
 * Displays light or medium consolidated vision summaries
 */
function showConsolidatedSummary(depth) {
  const depthMap = {
    light: {
      field: 'consolidated_vision_light',
      tokens: 'consolidated_vision_light_tokens',
      label: 'Light (33%)',
    },
    medium: {
      field: 'consolidated_vision_medium',
      tokens: 'consolidated_vision_medium_tokens',
      label: 'Medium (66%)',
    },
  }

  const config = depthMap[depth]
  if (!config || !props.product[config.field]) return

  consolidatedSummaryContent.value = props.product[config.field]
  consolidatedSummaryTitle.value = 'Consolidated Vision Summary'
  consolidatedSummaryLevel.value = config.label
  consolidatedSummaryTokens.value = props.product[config.tokens] || 0
  consolidatedSummaryHash.value = props.product.consolidated_vision_hash || ''
  consolidatedSummaryDialog.value = true
}

/**
 * Regenerate consolidated vision summaries (Handover 0377)
 * Calls API to trigger manual consolidation
 */
async function regenerateConsolidation() {
  if (!props.product?.id) return

  regeneratingConsolidation.value = true
  try {
    await api.products.regenerateConsolidated(props.product.id, true)

    // Refresh product data to get updated consolidated fields
    // Parent component should handle the refresh via event or refetch
    emit('refresh-product')

    // Success — parent refreshes via the refresh-product event above
  } catch (error) {
    console.error('Failed to regenerate summaries:', error)
    const message = error.response?.data?.detail || 'Failed to regenerate summaries'
    console.error(message)
  } finally {
    regeneratingConsolidation.value = false
  }
}
</script>
