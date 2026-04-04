<template>
  <v-dialog v-model="isOpen" max-width="600" scrollable>
    <v-card v-draggable class="smooth-border product-details-card">
      <div class="dlg-header">
        <v-icon class="dlg-icon" icon="mdi-information-outline" />
        <span class="dlg-title">Product Details</span>
        <v-btn icon variant="text" size="small" class="dlg-close" @click="handleClose">
          <v-icon icon="mdi-close" size="18" />
        </v-btn>
      </div>

      <v-divider />

      <v-card-text v-if="product" class="pa-4 dialog-body-scroll product-details-body">
        <!-- Product Name -->
        <div class="text-h6 mb-2">{{ product.name }}</div>
        <div class="text-caption mb-4 text-muted-a11y font-mono product-id-text">ID: {{ product.id }}</div>

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
              <div class="text-caption text-muted-a11y">Unresolved Tasks</div>
              <div class="text-h6 text-secondary-a11y">{{ product.unresolved_tasks || 0 }}</div>
            </v-col>
            <v-col cols="6">
              <div class="text-caption text-muted-a11y">Unfinished Projects</div>
              <div class="text-h6 text-secondary-a11y">{{ product.unfinished_projects || 0 }}</div>
            </v-col>
          </v-row>
        </div>

        <!-- Vision Documents -->
        <div>
          <div class="text-subtitle-2 mb-2">Vision Documents ({{ visionDocuments.length }})</div>

          <v-list v-if="visionDocuments.length > 0" density="compact">
            <v-card
              v-for="doc in visionDocuments"
              :key="doc.id"
              variant="flat"
              class="smooth-border mb-2 doc-entry-card"
            >
              <div class="doc-card-header px-3 py-3">
                <div class="doc-card-heading">
                  <v-icon color="primary" class="mr-2">mdi-file-document</v-icon>
                  <div class="doc-card-heading-text">
                    <div class="doc-card-title">{{ doc.filename || doc.document_name }}</div>
                    <div class="doc-card-meta">
                      <span class="doc-meta-pill">{{ doc.is_summarized ? 'Summarized' : 'Processing' }}</span>
                      <span class="doc-meta-pill">{{ formatFileSize(doc.file_size || 0) }}</span>
                      <span v-if="doc.chunked" class="doc-meta-pill">Chunked · {{ doc.chunk_count }} chunks</span>
                      <span v-if="doc.original_token_count" class="doc-meta-pill">{{ formatTokens(doc.original_token_count) }} tokens</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="doc-dropdown">
                <button
                  v-if="doc.is_summarized || doc.vision_document"
                  type="button"
                  class="detail-section-toggle detail-section-toggle--compact"
                  @click="toggleSummarySection(doc.id)"
                >
                  <span class="detail-section-title-wrap">
                    <span class="detail-section-title">Summary Previews</span>
                  </span>
                  <v-icon size="18">{{ isSummaryOpen(doc.id) ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
                </button>

                <div v-if="isSummaryOpen(doc.id) && (doc.is_summarized || doc.vision_document)" class="detail-section-body">
                  <div class="detail-section-subtitle text-caption text-muted-a11y">
                    Extractive summaries — original sentences selected by LSA, no AI generation.
                  </div>
                  <div class="summary-action-grid">
                    <button
                      type="button"
                      class="summary-action-btn"
                      :style="docSummaryStyle('light')"
                      @click="showSummary(doc, 'light')"
                    >
                      <v-progress-circular
                        v-if="loadingSummary.docId === doc.id && loadingSummary.level === 'light'"
                        indeterminate size="12" width="2" class="mr-1"
                      />
                      <span>Light</span>
                    </button>
                    <button
                      type="button"
                      class="summary-action-btn"
                      :style="docSummaryStyle('medium')"
                      @click="showSummary(doc, 'medium')"
                    >
                      <v-progress-circular
                        v-if="loadingSummary.docId === doc.id && loadingSummary.level === 'medium'"
                        indeterminate size="12" width="2" class="mr-1"
                      />
                      <span>Medium</span>
                    </button>
                    <button
                      type="button"
                      class="summary-action-btn"
                      :style="docSummaryStyle('full')"
                      @click="showSummary(doc, 'full')"
                    >
                      <v-progress-circular
                        v-if="loadingSummary.docId === doc.id && loadingSummary.level === 'full'"
                        indeterminate size="12" width="2" class="mr-1"
                      />
                      <span>Full</span>
                    </button>
                  </div>
                  <div v-if="doc.has_ai_summaries" class="mt-3">
                    <div class="detail-section-subtitle text-caption text-muted-a11y">
                      AI-generated summaries — rewritten by your LLM.
                    </div>
                    <div class="summary-action-grid summary-action-grid--ai">
                      <button
                        v-if="doc.ai_summary_light_tokens"
                        type="button"
                        class="summary-action-btn"
                        :style="aiSummaryStyle('light')"
                        @click="showAiSummary(doc, 'light')"
                      >
                        <v-progress-circular
                          v-if="loadingAiSummary.docId === doc.id && loadingAiSummary.level === 'light'"
                          indeterminate size="12" width="2" class="mr-1"
                        />
                        <span>Light · {{ formatTokens(doc.ai_summary_light_tokens) }} tokens</span>
                      </button>
                      <button
                        v-if="doc.ai_summary_medium_tokens"
                        type="button"
                        class="summary-action-btn"
                        :style="aiSummaryStyle('medium')"
                        @click="showAiSummary(doc, 'medium')"
                      >
                        <v-progress-circular
                          v-if="loadingAiSummary.docId === doc.id && loadingAiSummary.level === 'medium'"
                          indeterminate size="12" width="2" class="mr-1"
                        />
                        <span>Medium · {{ formatTokens(doc.ai_summary_medium_tokens) }} tokens</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
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
                class="text-primary cursor-pointer"
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
            <span
              class="summary-level-chip cursor-pointer"
              :style="consolidatedSummaryStyle('light')"
              role="button"
              tabindex="0"
              @click="showConsolidatedSummary('light')"
              @keydown.enter="showConsolidatedSummary('light')"
            >
              Light (33%)
              <v-tooltip activator="parent" location="bottom">
                ~{{ formatTokens(product.consolidated_vision_light_tokens) }} tokens
              </v-tooltip>
            </span>

            <span
              v-if="product?.consolidated_vision_medium"
              class="summary-level-chip cursor-pointer"
              :style="consolidatedSummaryStyle('medium')"
              role="button"
              tabindex="0"
              @click="showConsolidatedSummary('medium')"
              @keydown.enter="showConsolidatedSummary('medium')"
            >
              Medium (66%)
              <v-tooltip activator="parent" location="bottom">
                ~{{ formatTokens(product.consolidated_vision_medium_tokens) }} tokens
              </v-tooltip>
            </span>
          </div>

          <div v-if="product?.consolidated_at" class="text-caption mb-3 text-muted-a11y">
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
                  <div class="text-body-2 text-pre-line">{{ product.architecture.coding_conventions }}</div>
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
                <div class="text-body-2 text-pre-line">{{ product.brand_guidelines }}</div>
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
        <div class="text-caption text-muted-a11y mt-4">
          Created: {{ formatDate(product.created_at) }}<br />
          Updated: {{ formatDate(product.updated_at) }}
        </div>
      </v-card-text>

      <v-divider />

      <div class="dlg-footer">
        <v-spacer />
        <v-btn variant="text" @click="handleClose">Close</v-btn>
      </div>
    </v-card>
  </v-dialog>

  <!-- Summary Preview Dialog -->
  <v-dialog v-model="summaryDialog" max-width="800" scrollable>
    <v-card v-draggable class="smooth-border">
      <div class="dlg-header">
        <v-icon class="dlg-icon" :color="summaryLevelColor" icon="mdi-text-box-outline" />
        <span class="dlg-title">{{ summaryTitle }}</span>
        <v-chip size="small" :color="summaryLevelColor" variant="tonal" class="mr-2">
          {{ summaryLevel }}
        </v-chip>
        <v-btn icon variant="text" size="small" class="dlg-close" @click="summaryDialog = false">
          <v-icon icon="mdi-close" size="18" />
        </v-btn>
      </div>

      <v-divider />

      <v-card-text class="summary-content pa-4 dialog-body-scroll">
        <div class="text-caption text-muted-a11y mb-2">
          <v-icon size="14" class="mr-1">mdi-counter</v-icon>
          ~{{ formatTokens(summaryTokens) }} tokens
        </div>
        <div class="text-body-2 text-pre-wrap">{{ summaryContent }}</div>
      </v-card-text>

      <v-divider />

      <div class="dlg-footer">
        <v-spacer />
        <v-btn variant="text" @click="summaryDialog = false">Close</v-btn>
      </div>
    </v-card>
  </v-dialog>

  <!-- Consolidated Summary Viewer Dialog (Handover 0377) -->
  <v-dialog v-model="consolidatedSummaryDialog" max-width="800" scrollable>
    <v-card v-draggable class="smooth-border">
      <div class="dlg-header">
        <v-icon class="dlg-icon" color="teal" icon="mdi-database-merge" />
        <span class="dlg-title">{{ consolidatedSummaryTitle }}</span>
        <v-chip size="small" :color="consolidatedSummaryColor" variant="tonal" class="mr-2">
          {{ consolidatedSummaryLevel }}
        </v-chip>
        <v-btn icon variant="text" size="small" class="dlg-close" @click="consolidatedSummaryDialog = false">
          <v-icon icon="mdi-close" size="18" />
        </v-btn>
      </div>

      <v-divider />

      <v-card-text class="summary-content pa-4 dialog-body-scroll">
        <div class="text-caption text-muted-a11y mb-2">
          <v-icon size="14" class="mr-1">mdi-counter</v-icon>
          ~{{ formatTokens(consolidatedSummaryTokens) }} tokens
          <span v-if="consolidatedSummaryHash" class="ml-2">
            Hash: {{ consolidatedSummaryHash.substring(0, 12) }}...
          </span>
        </div>
        <div class="text-body-2 text-pre-wrap">{{ consolidatedSummaryContent }}</div>
      </v-card-text>

      <v-divider />

      <div class="dlg-footer">
        <v-spacer />
        <v-btn variant="text" @click="consolidatedSummaryDialog = false">Close</v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import api from '@/services/api'
import { useFormatDate } from '@/composables/useFormatDate'
import { useToast } from '@/composables/useToast'
import { hexToRgba } from '@/utils/colorUtils'
import { getAgentColor } from '@/config/agentColors'
import { getStatusColor } from '@/utils/statusConfig'

const { formatDate } = useFormatDate()
const { showToast } = useToast()

// Summary level color tokens (status-complete green, tester yellow, implementer blue)
const DOC_SUMMARY_COLORS = {
  light: getStatusColor('complete'),
  medium: getAgentColor('tester').hex,
  full: getAgentColor('implementer').hex,
}

const CONSOLIDATED_SUMMARY_COLORS = {
  light: getStatusColor('complete'),
  medium: getAgentColor('implementer').hex,
}

const AI_SUMMARY_COLORS = {
  light: getStatusColor('complete'),
  medium: getAgentColor('tester').hex,
}

function docSummaryStyle(level) {
  const hex = DOC_SUMMARY_COLORS[level] || '#8895a8'
  return { background: hexToRgba(hex, 0.15), color: hex }
}

function consolidatedSummaryStyle(level) {
  const hex = CONSOLIDATED_SUMMARY_COLORS[level] || '#8895a8'
  return { background: hexToRgba(hex, 0.15), color: hex }
}

function aiSummaryStyle(level) {
  const hex = AI_SUMMARY_COLORS[level] || '#8895a8'
  return { background: hexToRgba(hex, 0.15), color: hex }
}

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

const emit = defineEmits(['update:modelValue', 'refresh-product'])

const openSummarySections = ref({})

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

watch(
  () => props.modelValue,
  (open) => {
    if (!open) {
      openSummarySections.value = {}
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

function toggleSummarySection(documentId) {
  openSummarySections.value = {
    ...openSummarySections.value,
    [documentId]: !openSummarySections.value[documentId],
  }
}

function isSummaryOpen(documentId) {
  return Boolean(openSummarySections.value[documentId])
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
const loadingAiSummary = ref({ docId: null, level: null })

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

/**
 * Show AI-generated summary (light or medium)
 * Fetches from dedicated AI summary endpoint
 */
async function showAiSummary(doc, level) {
  try {
    loadingAiSummary.value = { docId: doc.id, level }
    const response = await api.visionDocuments.getAiSummary(doc.id, level)
    const data = response.data

    summaryContent.value = data.summary
    summaryTitle.value = `${doc.document_name || doc.filename} - AI Summary`
    summaryLevel.value = data.level
    summaryTokens.value = data.tokens || 0
    summaryDialog.value = true
  } catch (error) {
    console.error('Failed to fetch AI summary:', error)
    summaryContent.value = 'Error: Could not load AI summary content'
    summaryTitle.value = `${doc.document_name || doc.filename} - Error`
    summaryLevel.value = level.charAt(0).toUpperCase() + level.slice(1)
    summaryTokens.value = 0
    summaryDialog.value = true
  } finally {
    loadingAiSummary.value = { docId: null, level: null }
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
    android: 'Android',
    ios: 'iOS',
    web: 'Web',
    all: 'All (Cross-platform)',
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
    const message = error.response?.data?.detail || 'Failed to regenerate summaries. Please try again.'
    showToast({ message, type: 'error' })
  } finally {
    regeneratingConsolidation.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '../../styles/design-tokens' as *;
.product-id-text {
  font-size: 0.65rem;
}

:deep(.product-details-card) {
  display: flex;
  flex-direction: column;
  max-height: min(80vh, 900px);
  overflow: hidden;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.10) !important;
}

:deep(.product-details-body) {
  flex: 1 1 auto;
  min-height: 0;
}

:deep(.doc-entry-card) {
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.10) !important;
}

.detail-section {
  overflow: hidden;
  background: rgba(255, 255, 255, 0.03);
}

.detail-section-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  background: transparent;
  border: none;
  color: var(--color-text-primary);
  text-align: left;
  cursor: pointer;
}

.detail-section-toggle:hover {
  background: rgba(255, 255, 255, 0.03);
}

.detail-section-toggle--compact {
  padding: 10px 14px;
}

.detail-section-title-wrap {
  display: inline-flex;
  align-items: center;
  min-width: 0;
}

.detail-section-title {
  font-size: 0.82rem;
  font-weight: 600;
}

.detail-section-body {
  padding: 0 14px 14px;
}

.detail-section-subtitle {
  margin-bottom: 10px;
}

.doc-card-header {
  display: flex;
  align-items: flex-start;
}

.doc-card-heading {
  display: flex;
  align-items: flex-start;
  width: 100%;
}

.doc-card-heading-text {
  min-width: 0;
  flex: 1;
}

.doc-card-title {
  font-size: 0.85rem;
  font-weight: 600;
  line-height: 1.4;
  word-break: break-word;
}

.doc-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.doc-meta-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: $border-radius-pill;
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-muted);
  font-size: 0.66rem;
  line-height: 1.4;
}

.doc-dropdown {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.summary-action-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.summary-action-btn {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  border: none;
  border-radius: $border-radius-default;
  font-size: 0.74rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform $transition-fast ease, opacity $transition-fast ease;
}

.summary-action-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.summary-action-btn:focus-visible,
.detail-section-toggle:focus-visible {
  outline: 2px solid rgba(255, 195, 0, 0.45);
  outline-offset: 2px;
}

.summary-level-chip {
  display: inline-flex;
  align-items: center;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: $border-radius-default;
  line-height: 1.4;
  letter-spacing: 0.02em;
  transition: opacity $transition-fast ease;
}

.summary-level-chip:hover {
  opacity: 0.85;
}

.summary-action-grid--ai {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (max-width: 640px) {
  .summary-action-grid {
    grid-template-columns: 1fr;
  }
}
</style>
