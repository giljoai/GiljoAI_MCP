<template>
  <v-dialog v-model="isOpen" max-width="950" persistent retain-focus>
    <v-card v-draggable class="product-form-card">
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">{{ isEdit ? 'mdi-pencil' : 'mdi-plus' }}</v-icon>
        <span>{{ isEdit ? 'Edit Product' : 'Create New Product' }}</span>
        <v-spacer />

        <v-btn icon="mdi-close" variant="text" aria-label="Close" @click="closeDialog" />
      </v-card-title>

      <v-divider></v-divider>

      <v-card-text style="min-height: 400px; max-height: 600px; overflow-y: auto">
        <!-- Tabbed interface for product configuration (button-toggle style like Settings) -->
        <v-btn-toggle
          v-model="dialogTab"
          mandatory
          variant="outlined"
          divided
          rounded="t-lg"
          color="primary"
          class="mb-0"
        >
          <v-btn value="setup">
            <v-icon start size="small">mdi-cog-outline</v-icon>
            Product Setup
          </v-btn>
          <v-btn value="info" :disabled="analysisInProgress">
            <v-icon start size="small">mdi-information-outline</v-icon>
            Product Info
          </v-btn>
          <v-btn value="tech" :disabled="analysisInProgress">
            <v-icon start size="small">mdi-code-braces</v-icon>
            Tech Stack
          </v-btn>
          <v-btn value="arch" :disabled="analysisInProgress">
            <v-icon start size="small">mdi-sitemap</v-icon>
            Architecture
          </v-btn>
          <v-btn value="features" :disabled="analysisInProgress">
            <v-icon start size="small">mdi-test-tube</v-icon>
            Testing
          </v-btn>
        </v-btn-toggle>

        <v-alert v-if="analysisInProgress" type="info" variant="tonal" density="compact" class="mb-0 mt-2">
          <div class="d-flex align-center">
            <v-progress-circular indeterminate size="16" width="2" class="mr-2" />
            <span class="text-body-2">Waiting for AI analysis... Paste the prompt in your coding tool.</span>
          </div>
          <div v-if="analysisHintVisible" class="text-caption text-muted-a11y mt-2">
            Taking too long? Switch to "Manually define product" to continue.
          </div>
        </v-alert>

        <div class="bordered-tabs-content smooth-border">
          <v-form ref="formRef" v-model="formValid">
            <v-window v-model="dialogTab" class="global-tabs-window">
            <!-- Product Setup Tab -->
            <v-window-item value="setup">
              <div class="text-subtitle-1 mb-1">Product Setup</div>
              <div class="text-caption text-warning mb-4">Always used as context source by orchestrator.</div>

              <!-- Product Name -->
              <v-text-field
                v-model="productForm.name"
                label="Product Name"
                :rules="[(v) => !!v || 'Name is required']"
                variant="outlined"
                density="comfortable"
                required
                class="mb-4 mt-2"
              ></v-text-field>

              <!-- Vision Documents Section -->
              <div class="text-subtitle-2 mt-2 mb-1">Vision Documents</div>
              <div class="text-caption text-muted-a11y mb-4">
                Optionally included as context source by orchestrator.
                <v-chip size="x-small" color="success" variant="tonal" class="ml-2">Activated in Context Manager</v-chip>
              </div>


              <!-- Upload error alert -->
              <v-alert
                v-if="visionUploadError"
                type="error"
                variant="tonal"
                density="compact"
                dismissible
                class="mb-4"
                @click:close="emit('clear-upload-error')"
              >
                {{ visionUploadError }}
              </v-alert>

              <!-- Upload progress indicator -->
              <v-alert
                v-if="uploadingVision"
                type="info"
                variant="tonal"
                density="compact"
                class="mb-4"
              >
                <div class="d-flex align-center mb-2">
                  <v-progress-circular indeterminate size="20" width="2" class="mr-2" />
                  <span>Uploading and processing documents...</span>
                </div>
                <v-progress-linear
                  :model-value="uploadProgress"
                  color="primary"
                  height="6"
                  class="mt-2"
                />
              </v-alert>

              <!-- Existing Documents (shown after upload) -->
              <div v-if="existingVisionDocuments.length > 0" class="mb-4">
                <div class="text-subtitle-2 mb-2">
                  Existing Documents ({{ existingVisionDocuments.length }})
                </div>

                <v-list density="compact" class="mb-3">
                  <v-list-item
                    v-for="doc in existingVisionDocuments"
                    :key="doc.id"
                    class="border rounded mb-2"
                  >
                    <template v-slot:prepend>
                      <v-icon :color="(doc.is_summarized || doc.chunked) ? 'success' : 'warning'">
                        {{ (doc.is_summarized || doc.chunked) ? 'mdi-check-circle' : 'mdi-clock-outline' }}
                      </v-icon>
                    </template>

                    <v-list-item-title>{{ doc.filename || doc.document_name }}</v-list-item-title>
                    <v-list-item-subtitle>
                      {{ doc.is_summarized ? 'Summarized' : 'Processing' }}
                      <span v-if="doc.chunked"> • {{ doc.chunk_count }} chunks</span>
                      • {{ formatDate(doc.created_at) }}
                    </v-list-item-subtitle>

                    <template v-slot:append>
                      <v-btn
                        icon
                        size="small"
                        variant="text"
                        color="error"
                        @click="deleteVisionDocument(doc)"
                      >
                        <v-icon size="20">mdi-delete</v-icon>
                      </v-btn>
                    </template>
                  </v-list-item>
                </v-list>
              </div>

              <!-- File Upload Component -->
              <v-file-input
                v-model="visionFiles"
                accept=".txt,.md,.markdown"
                label="Choose files"
                variant="outlined"
                density="comfortable"
                multiple
                show-size
                clearable
                prepend-icon="mdi-folder-open"
                hint="Upload product file(s), requirements, proposals, specifications (.md, .txt files)"
                persistent-hint
                :disabled="!productForm.name?.trim()"
                class="mb-3"
                @update:model-value="onFilesAttached"
              ></v-file-input>

              <!-- Mode Selection (appears after vision docs are uploaded) -->
              <template v-if="existingVisionDocuments.length > 0">
                <div class="text-subtitle-2 mt-6 mb-2">How would you like to set up this product?</div>
                <v-radio-group v-model="setupMode" hide-details class="mb-2">
                  <v-radio label="Manually define product" value="manual" />
                  <div class="d-flex align-center">
                    <v-radio label="Use AI coding agent" value="ai" />
                    <v-btn
                      v-if="setupMode === 'ai'"
                      color="primary"
                      variant="flat"
                      size="small"
                      class="ml-2"
                      :prepend-icon="analysisPromptCopied ? 'mdi-check' : 'mdi-content-copy'"
                      @click.stop="stageAnalysis"
                    >
                      {{ analysisPromptCopied ? 'Prompt Copied!' : 'Stage Analysis' }}
                    </v-btn>
                  </div>
                </v-radio-group>

                <!-- Clipboard fallback — shown when browser blocks clipboard API -->
                <v-alert
                  v-if="promptFallbackText"
                  type="warning"
                  variant="tonal"
                  density="compact"
                  class="mt-2"
                >
                  <div class="text-body-2 mb-1">Clipboard unavailable — copy this prompt manually:</div>
                  <v-textarea
                    :model-value="promptFallbackText"
                    variant="outlined"
                    density="compact"
                    rows="3"
                    readonly
                    hide-details
                    @focus="$event.target.select()"
                  />
                </v-alert>
              </template>

              <!-- Vision Analysis Info (below radio) -->
              <v-alert
                v-if="setupMode === 'ai' && existingVisionDocuments.length > 0 && !analysisBannerDismissed"
                type="info"
                variant="tonal"
                density="compact"
                class="mt-2 mb-2"
                :icon="false"
              >
                <div class="d-flex align-center mb-1">
                  <img src="/Giljo_gray_Face.svg" alt="GiljoAI" class="mr-2" style="width: 30px; height: 30px; filter: brightness(0) invert(1); opacity: 0.5;" />
                  <span class="text-subtitle-2">Want AI to analyze this document?</span>
                </div>
                <div class="text-body-2">
                  Your AI coding agent will read the document and populate your product configuration fields
                  (tech stack, architecture, testing, etc.) plus generate improved summaries.
                </div>
                <div class="text-caption text-muted-a11y mt-1 text-center">
                  Uses your AI coding agent (Claude Code, Codex CLI, Gemini CLI, or any MCP-compatible tool).
                </div>
              </v-alert>

              <!-- Custom Extraction Instructions (expandable) -->
              <v-expansion-panels v-if="setupMode === 'ai' && existingVisionDocuments.length > 0" variant="accordion" class="mt-2">
                <v-expansion-panel>
                  <v-expansion-panel-title class="text-body-2 py-2" style="min-height: 40px;">
                    Custom extraction instructions (optional)
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-textarea
                      v-model="productForm.extractionCustomInstructions"
                      placeholder="Add domain-specific instructions for AI document analysis (e.g., 'This is a mobile-first app targeting iOS 17+')"
                      variant="outlined"
                      density="compact"
                      rows="2"
                      auto-grow
                      hide-details
                      persistent-placeholder
                    ></v-textarea>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </v-window-item>

            <!-- Product Info Tab -->
            <v-window-item value="info">
              <div class="text-subtitle-1 mb-1">Product Information</div>
              <div class="text-caption text-warning mb-4">Always used as context source by orchestrator.</div>

              <!-- Codebase Folder -->
              <v-text-field
                v-model="productForm.projectPath"
                label="Codebase Folder (optional)"
                variant="outlined"
                density="comfortable"
                placeholder="e.g., F:\Projects\MyApp or /home/user/myapp"
                prepend-icon="mdi-folder-outline"
                hint="Your local codebase path"
                persistent-hint
                class="mb-4"
              ></v-text-field>

              <!-- Description -->
              <v-textarea
                v-model="productForm.description"
                label="Product Description"
                variant="outlined"
                density="comfortable"
                rows="6"
                auto-grow
                hint="Describe what this product does and its purpose"
                persistent-hint
                class="mb-4"
              ></v-textarea>

              <!-- Core Features -->
              <v-textarea
                v-model="productForm.coreFeatures"
                hint="Main functionality and capabilities of this product"
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="4"
                auto-grow
                class="mb-4"
              >
                <template #label>
                  <span>Core Product Features</span>
                </template>
              </v-textarea>

              <v-textarea
                v-model="productForm.brandGuidelines"
                hint="Describe your visual style, colors, and fonts, or provide a path/URL to your brand guide. Agents use this when creating frontend components."
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="4"
                auto-grow
                class="mb-4"
              >
                <template #label>
                  <span>Brand & Design Guidelines</span>
                </template>
              </v-textarea>
            </v-window-item>

            <!-- Tech Stack Tab -->
            <v-window-item value="tech">
              <div class="text-subtitle-1 mb-1">Technology Stack Configuration</div>
              <div class="text-caption text-warning mb-4">
                Optionally included as context source by orchestrator.
                <v-chip size="x-small" color="success" variant="tonal" class="ml-2">Activated in Context Manager</v-chip>
              </div>

              <v-textarea
                v-model="productForm.techStack.programming_languages"
                placeholder="Python 3.11, JavaScript ES2023, TypeScript 5.2"
                hint="List all programming languages used (comma-separated or line-by-line)"
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="3"
                auto-grow
                class="mb-4"
              >
                <template #label>
                  <span>Programming Languages</span>
                </template>
              </v-textarea>

              <v-textarea
                v-model="productForm.techStack.frontend_frameworks"
                placeholder="Vue 3, Vuetify 3, Pinia, Vue Router"
                hint="List frontend technologies (frameworks, libraries, tools)"
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="3"
                auto-grow
                class="mb-4"
              >
                <template #label>
                  <span>Frontend Frameworks & Libraries</span>
                </template>
              </v-textarea>

              <v-textarea
                v-model="productForm.techStack.backend_frameworks"
                placeholder="FastAPI 0.104, SQLAlchemy 2.0, Alembic, asyncio"
                hint="List backend technologies (frameworks, ORMs, services)"
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="3"
                auto-grow
                class="mb-4"
              >
                <template #label>
                  <span>Backend Frameworks & Services</span>
                </template>
              </v-textarea>

              <v-textarea
                v-model="productForm.techStack.databases_storage"
                placeholder="PostgreSQL 16, Redis 7, Vector embeddings (pgvector)"
                hint="List databases and data storage solutions"
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="3"
                auto-grow
                class="mb-4"
              >
                <template #label>
                  <span>Databases & Data Storage</span>
                </template>
              </v-textarea>

              <v-textarea
                v-model="productForm.techStack.infrastructure"
                placeholder="Docker, Kubernetes, GitHub Actions CI/CD, AWS (EC2, S3, RDS)"
                hint="List infrastructure and deployment tools"
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="3"
                auto-grow
                class="mb-4"
              >
                <template #label>
                  <span>Infrastructure & DevOps</span>
                </template>
              </v-textarea>

              <!-- Target Platform(s) - Handover 0425 Phase 2 -->
              <div class="mb-4">
                <label class="text-subtitle-2 mb-2 d-block">Target Platform(s)</label>
                <div class="text-caption text-muted-a11y mb-3">
                  Select the operating systems this product is designed for
                </div>

                <div class="d-flex flex-wrap ga-3">
                  <v-checkbox
                    v-model="productForm.targetPlatforms"
                    value="windows"
                    label="Windows"
                    hide-details
                    density="comfortable"
                    :disabled="isAllPlatformSelected"
                    @update:model-value="handlePlatformChange"
                  />
                  <v-checkbox
                    v-model="productForm.targetPlatforms"
                    value="linux"
                    label="Linux"
                    hide-details
                    density="comfortable"
                    :disabled="isAllPlatformSelected"
                    @update:model-value="handlePlatformChange"
                  />
                  <v-checkbox
                    v-model="productForm.targetPlatforms"
                    value="macos"
                    label="macOS"
                    hide-details
                    density="comfortable"
                    :disabled="isAllPlatformSelected"
                    @update:model-value="handlePlatformChange"
                  />
                  <v-checkbox
                    v-model="productForm.targetPlatforms"
                    value="android"
                    label="Android"
                    hide-details
                    density="comfortable"
                    :disabled="isAllPlatformSelected"
                    @update:model-value="handlePlatformChange"
                  />
                  <v-checkbox
                    v-model="productForm.targetPlatforms"
                    value="ios"
                    label="iOS"
                    hide-details
                    density="comfortable"
                    :disabled="isAllPlatformSelected"
                    @update:model-value="handlePlatformChange"
                  />
                  <v-checkbox
                    v-model="productForm.targetPlatforms"
                    value="all"
                    label="All (Cross-platform)"
                    hide-details
                    density="comfortable"
                    color="primary"
                    @update:model-value="handleAllPlatformChange"
                  />
                </div>

                <div v-if="platformValidationError" class="text-error text-caption mt-2">
                  {{ platformValidationError }}
                </div>
              </div>
            </v-window-item>

            <!-- Architecture Tab -->
            <v-window-item value="arch">
              <div class="text-subtitle-1 mb-1">Architecture & Design Patterns</div>
              <div class="text-caption text-warning mb-4">
                Optionally included as context source by orchestrator.
                <v-chip size="x-small" color="success" variant="tonal" class="ml-2">Activated in Context Manager</v-chip>
              </div>

              <v-textarea
                v-model="productForm.architecture.primary_pattern"
                placeholder="Modular Monolith with Event-Driven components, CQRS for high-traffic modules"
                hint="Describe the overall system architecture approach"
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="2"
                auto-grow
                class="mb-4"
              >
                <template #label>
                  <span>Primary Architecture Pattern</span>
                </template>
              </v-textarea>

              <v-textarea
                v-model="productForm.architecture.design_patterns"
                placeholder="Repository Pattern, Dependency Injection, Factory Pattern, SOLID principles"
                hint="List design patterns and architectural principles used"
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="3"
                auto-grow
                class="mb-4"
              >
                <template #label>
                  <span>Design Patterns & Principles</span>
                </template>
              </v-textarea>

              <v-textarea
                v-model="productForm.architecture.api_style"
                placeholder="REST API (OpenAPI 3.0), WebSocket for real-time updates, GraphQL for complex queries"
                hint="Describe API communication patterns and protocols"
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="2"
                auto-grow
                class="mb-4"
              >
                <template #label>
                  <span>API Style & Communication</span>
                </template>
              </v-textarea>

              <v-textarea
                v-model="productForm.architecture.architecture_notes"
                hint="Additional architectural decisions, constraints, or context"
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="4"
                auto-grow
                class="mb-4"
              >
                <template #label>
                  <span>Architecture Notes</span>
                </template>
              </v-textarea>

              <v-textarea
                v-model="productForm.architecture.coding_conventions"
                hint="Define naming conventions, error handling patterns, code style rules, and other standards agents should follow when writing code"
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="6"
                auto-grow
                class="mb-4"
              >
                <template #label>
                  <span>Coding Conventions & Standards</span>
                </template>
              </v-textarea>
            </v-window-item>

            <!-- Testing Tab -->
            <v-window-item value="features">
              <div class="text-subtitle-1 mb-1">Quality Standards & Testing Configuration</div>
              <div class="text-caption text-warning mb-4">
                Optionally included as context source by orchestrator.
                <v-chip size="x-small" color="success" variant="tonal" class="ml-2">Activated in Context Manager</v-chip>
              </div>

              <!-- Quality Standards -->
              <v-textarea
                v-model="productForm.testConfig.quality_standards"
                placeholder="e.g., Code review required, 80% coverage, zero critical bugs, all tests passing before merge"
                hint="Define your quality expectations for testing and development"
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="4"
                auto-grow
                class="mb-4"
              >
                <template #label>
                  <span>Quality Standards</span>
                </template>
              </v-textarea>

              <!-- Testing Strategy Dropdown -->
              <v-select
                v-model="productForm.testConfig.test_strategy"
                :items="testingStrategies"
                item-title="title"
                item-value="value"
                hint="Choose the primary testing methodology for this product"
                persistent-hint
                variant="outlined"
                density="comfortable"
                class="mb-4"
              >
                <template #label>
                  <span>Testing Strategy & Approach</span>
                </template>

                <!-- Enhanced dropdown items with icons and subtitles -->
                <template #item="{ props, item }">
                  <v-list-item v-bind="props">
                    <template #prepend>
                      <v-icon :icon="item.raw.icon" class="mr-2"></v-icon>
                    </template>
                    <v-list-item-title>{{ item.raw.title }}</v-list-item-title>
                    <v-list-item-subtitle>{{ item.raw.subtitle }}</v-list-item-subtitle>
                  </v-list-item>
                </template>

                <!-- Enhanced selection display with icon -->
                <template #selection="{ item }">
                  <div class="d-flex align-center">
                    <v-icon :icon="item.raw.icon" size="small" class="mr-2"></v-icon>
                    <span>{{ item.raw.title }}</span>
                  </div>
                </template>
              </v-select>

              <!-- Coverage Target Slider -->
              <div class="mb-4">
                <label class="text-caption text-muted-a11y">
                  Test Coverage Target: {{ productForm.testConfig.coverage_target }}%
                </label>
                <v-slider
                  v-model="productForm.testConfig.coverage_target"
                  min="0"
                  max="100"
                  step="5"
                  thumb-label
                  color="primary"
                ></v-slider>
              </div>

              <!-- Testing Frameworks -->
              <v-textarea
                v-model="productForm.testConfig.testing_frameworks"
                placeholder="pytest, pytest-asyncio, Playwright, coverage.py"
                hint="List testing frameworks and quality assurance tools"
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="3"
                auto-grow
                class="mb-4"
              >
                <template #label>
                  <span>Testing Frameworks & Tools</span>
                </template>
              </v-textarea>
            </v-window-item>
            </v-window>
          </v-form>
        </div>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" :disabled="isFirstTab" @click="goPrevTab">Back</v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :disabled="isEdit ? !formValid || saving : isLastTab ? !formValid || saving : saving || analysisInProgress"
          :loading="isEdit ? saving : isLastTab ? saving : false"
          @click="isEdit ? saveProduct() : isLastTab ? saveProduct() : goNextTab()"
        >
          {{ isEdit ? 'Save Changes' : isLastTab ? 'Create Product' : 'Next' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'
import { useFormatDate } from '@/composables/useFormatDate'
import { useProductStore } from '@/stores/products'

const { formatDate } = useFormatDate()

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  product: {
    type: Object,
    default: () => null,
  },
  isEdit: {
    type: Boolean,
    default: false,
  },
  existingVisionDocuments: {
    type: Array,
    default: () => [],
  },
  uploadingVision: {
    type: Boolean,
    default: false,
  },
  uploadProgress: {
    type: Number,
    default: 0,
  },
  visionUploadError: {
    type: String,
    default: null,
  },
})

const emit = defineEmits(['update:modelValue', 'save', 'cancel', 'remove-vision', 'clear-upload-error', 'upload-vision-files'])

const { copy: copyToClipboard } = useClipboard()
const { showToast } = useToast()

// State
const saving = ref(false)
const formValid = ref(false)
const formRef = ref(null)
const dialogTab = ref('setup')
const visionFiles = ref([])

// Vision analysis prompt state (Handover 0842d)
const analysisBannerDismissed = ref(false)
const analysisPromptCopied = ref(false)
const promptFallbackText = ref(null) // Shown when clipboard copy fails

// Setup mode and analysis state (Handover 0842i)
const setupMode = ref('manual')
const analysisInProgress = ref(false)
const analysisHintVisible = ref(false)
let analysisHintTimer = null

// Product form data — single source of truth for the default shape
function getDefaultFormState() {
  return {
    name: '',
    description: '',
    projectPath: '',
    targetPlatforms: ['all'],
    techStack: {
      programming_languages: '',
      frontend_frameworks: '',
      backend_frameworks: '',
      databases_storage: '',
      infrastructure: '',
    },
    architecture: {
      primary_pattern: '',
      design_patterns: '',
      api_style: '',
      architecture_notes: '',
      coding_conventions: '- Keep code simple and readable. Prefer fewer files over many small ones.\n- Use consistent naming: snake_case for Python, camelCase for JavaScript.\n- No commented-out code. Delete what you don\'t need.\n- Handle errors explicitly. Don\'t silently swallow exceptions.\n- Write functions that do one thing. Keep them short enough to read without scrolling.\n- If unsure about a design decision, choose the simpler option.',
    },
    coreFeatures: '',
    brandGuidelines: '',
    testConfig: {
      quality_standards: '',
      test_strategy: 'TDD',
      coverage_target: 80,
      testing_frameworks: '',
    },
    extractionCustomInstructions: '',
  }
}

const productForm = ref(getDefaultFormState())

// Testing strategies
const testingStrategies = [
  {
    value: 'TDD',
    title: 'TDD (Test-Driven Development)',
    subtitle: 'Write tests before implementation code',
    icon: 'mdi-test-tube',
  },
  {
    value: 'BDD',
    title: 'BDD (Behavior-Driven Development)',
    subtitle: 'Tests based on user stories and behavior specs',
    icon: 'mdi-comment-text-multiple',
  },
  {
    value: 'Integration-First',
    title: 'Integration-First',
    subtitle: 'Focus on testing component interactions',
    icon: 'mdi-connection',
  },
  {
    value: 'E2E-First',
    title: 'E2E-First',
    subtitle: 'Prioritize end-to-end user workflow tests',
    icon: 'mdi-path',
  },
  {
    value: 'Manual',
    title: 'Manual Testing',
    subtitle: 'User-driven QA and exploratory testing',
    icon: 'mdi-human-male',
  },
  {
    value: 'Hybrid',
    title: 'Hybrid Approach',
    subtitle: 'Combination of multiple testing strategies',
    icon: 'mdi-view-grid-plus',
  },
]

// Tab navigation
const tabOrder = ['setup', 'info', 'tech', 'arch', 'features']
const isFirstTab = computed(() => tabOrder.indexOf(dialogTab.value) === 0)
const isLastTab = computed(() => tabOrder.indexOf(dialogTab.value) === tabOrder.length - 1)

function goNextTab() {
  const idx = tabOrder.indexOf(dialogTab.value)
  if (idx >= 0 && idx < tabOrder.length - 1) {
    dialogTab.value = tabOrder[idx + 1]
  }
}

function goPrevTab() {
  const idx = tabOrder.indexOf(dialogTab.value)
  if (idx > 0) {
    dialogTab.value = tabOrder[idx - 1]
  }
}

// Computed v-model for dialog
const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

// Handover 0425: Platform selection state
const platformValidationError = ref('')
const isAllPlatformSelected = computed(() => productForm.value.targetPlatforms.includes('all'))

// Methods
function closeDialog() {
  emit('cancel')
  emit('update:modelValue', false)
}

function saveProduct() {
  if (!formValid.value) return

  // Handover 0425: Validate platforms before saving
  if (!validatePlatforms()) {
    return
  }

  saving.value = true

  const productData = {
    name: productForm.value.name,
    description: productForm.value.description,
    project_path: productForm.value.projectPath,
    target_platforms: productForm.value.targetPlatforms,
    tech_stack: productForm.value.techStack,
    architecture: productForm.value.architecture,
    test_config: productForm.value.testConfig,
    core_features: productForm.value.coreFeatures,
    brand_guidelines: productForm.value.brandGuidelines,
    extraction_custom_instructions: productForm.value.extractionCustomInstructions,
  }

  // Vision files are uploaded on attach, not on save
  emit('save', { productData })

  // Note: Parent component should set saving = false after async operation completes
}

function deleteVisionDocument(doc) {
  emit('remove-vision', doc)
}


// Vision analysis prompt — product must already be saved (UUID exists via upload-on-attach)
async function stageAnalysis() {
  const productId = props.product?.id
  if (!productId) {
    console.warn('[ProductForm] stageAnalysis called but no product ID available. product:', props.product)
    return
  }

  const productName = productForm.value.name || 'this product'
  const prompt = `Analyze the vision document for product "${productName}" and populate its configuration.\nUse the gil_get_vision_doc tool with product_id "${productId}" to read the document and extraction instructions, then call gil_write_product with the extracted fields.`

  promptFallbackText.value = null
  const didCopy = await copyToClipboard(prompt)

  if (didCopy) {
    analysisPromptCopied.value = true
    showToast({ message: 'Analysis prompt copied — paste into your AI coding agent', type: 'success', duration: 4000 })
    setTimeout(() => { analysisPromptCopied.value = false }, 3000)
  } else {
    promptFallbackText.value = prompt
    showToast({ message: 'Clipboard unavailable — copy the prompt manually below', type: 'warning', duration: 5000 })
  }

  analysisInProgress.value = true

  // Start the "taking too long?" hint timer (60 seconds)
  analysisHintVisible.value = false
  clearTimeout(analysisHintTimer)
  analysisHintTimer = setTimeout(() => { analysisHintVisible.value = true }, 60000)
}

// Upload files immediately on attachment
function onFilesAttached(files) {
  if (!files || files.length === 0) return
  if (!productForm.value.name?.trim()) return

  emit('upload-vision-files', { productName: productForm.value.name, files: [...files] })
  visionFiles.value = [] // Clear local files — parent handles upload
}

// Handover 0425: Platform selection handlers
function handleAllPlatformChange(value) {
  platformValidationError.value = ''
  if (value && productForm.value.targetPlatforms.includes('all')) {
    // When "All" is selected, clear other selections
    productForm.value.targetPlatforms = ['all']
  } else if (!value) {
    // When "All" is deselected, remove it from array
    productForm.value.targetPlatforms = productForm.value.targetPlatforms.filter(p => p !== 'all')
  }
  validatePlatforms()
}

function handlePlatformChange() {
  platformValidationError.value = ''
  // If "All" is selected and user selects another platform, deselect "All"
  if (productForm.value.targetPlatforms.includes('all') && productForm.value.targetPlatforms.length > 1) {
    productForm.value.targetPlatforms = productForm.value.targetPlatforms.filter(p => p !== 'all')
  }
  validatePlatforms()
}

function validatePlatforms() {
  if (productForm.value.targetPlatforms.length === 0) {
    platformValidationError.value = 'At least one platform must be selected'
    formValid.value = false
    return false
  }
  platformValidationError.value = ''
  return true
}

// Load product data when editing, or reset to defaults
function loadProductData() {
  if (props.isEdit && props.product) {
    const p = props.product
    const ts = p.tech_stack || {}
    const arch = p.architecture || {}
    const tc = p.test_config || {}

    productForm.value = {
      name: p.name || '',
      description: p.description || '',
      projectPath: p.project_path || '',
      targetPlatforms: p.target_platforms || ['all'],
      techStack: {
        programming_languages: ts.programming_languages || '',
        frontend_frameworks: ts.frontend_frameworks || '',
        backend_frameworks: ts.backend_frameworks || '',
        databases_storage: ts.databases_storage || '',
        infrastructure: ts.infrastructure || '',
      },
      architecture: {
        primary_pattern: arch.primary_pattern || '',
        design_patterns: arch.design_patterns || '',
        api_style: arch.api_style || '',
        architecture_notes: arch.architecture_notes || '',
        coding_conventions: arch.coding_conventions || '',
      },
      coreFeatures: p.core_features || '',
      brandGuidelines: p.brand_guidelines || '',
      testConfig: {
        quality_standards: tc.quality_standards || '',
        test_strategy: tc.test_strategy || 'TDD',
        coverage_target: tc.coverage_target || 80,
        testing_frameworks: tc.testing_frameworks || '',
      },
      extractionCustomInstructions: p.extraction_custom_instructions || '',
    }
  } else {
    productForm.value = getDefaultFormState()
  }
}

// Reset state when dialog opens/closes
watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal) {
      // Dialog opening — reset local state only (upload progress is owned by parent)
      dialogTab.value = 'setup'
      visionFiles.value = []
      saving.value = false
      analysisBannerDismissed.value = false
      setupMode.value = 'manual'
      analysisInProgress.value = false
      analysisHintVisible.value = false
      clearTimeout(analysisHintTimer)
      loadProductData()
    }
  },
)

// Also watch for product changes (only reload in edit mode — during create, the
// product prop is set by silent-save and we must not overwrite the user's form)
watch(
  () => props.product,
  () => {
    if (props.modelValue && props.isEdit) {
      loadProductData()
    }
  },
  { deep: true },
)

// Reset analysis lock when switching back to manual mode (Handover 0842i)
watch(setupMode, (newMode) => {
  if (newMode === 'manual') {
    analysisInProgress.value = false
    analysisHintVisible.value = false
    clearTimeout(analysisHintTimer)
  }
})

// Listen for vision:analysis_complete WebSocket event to unlock the UI
const productStore = useProductStore()

async function onVisionAnalysisComplete(event) {
  const productId = event.detail?.product_id
  if (productId && productId === props.product?.id) {
    analysisHintVisible.value = false
    clearTimeout(analysisHintTimer)

    // Fetch updated product with AI-populated fields from the API
    const updated = await productStore.fetchProductById(productId)
    if (updated) {
      const ts = updated.tech_stack || {}
      const arch = updated.architecture || {}
      const tc = updated.test_config || {}

      productForm.value = {
        name: updated.name || productForm.value.name,
        description: updated.description || '',
        projectPath: updated.project_path || '',
        targetPlatforms: updated.target_platforms || ['all'],
        techStack: {
          programming_languages: ts.programming_languages || '',
          frontend_frameworks: ts.frontend_frameworks || '',
          backend_frameworks: ts.backend_frameworks || '',
          databases_storage: ts.databases_storage || '',
          infrastructure: ts.infrastructure || '',
        },
        architecture: {
          primary_pattern: arch.primary_pattern || '',
          design_patterns: arch.design_patterns || '',
          api_style: arch.api_style || '',
          architecture_notes: arch.architecture_notes || '',
          coding_conventions: arch.coding_conventions || '',
        },
        coreFeatures: updated.core_features || '',
        brandGuidelines: updated.brand_guidelines || '',
        testConfig: {
          quality_standards: tc.quality_standards || '',
          test_strategy: tc.test_strategy || 'TDD',
          coverage_target: tc.coverage_target || 80,
          testing_frameworks: tc.testing_frameworks || '',
        },
        extractionCustomInstructions: updated.extraction_custom_instructions || '',
      }
    }

    // Unlock the UI
    analysisInProgress.value = false
  }
}

onMounted(() => {
  window.addEventListener('vision-analysis-complete', onVisionAnalysisComplete)
})

onUnmounted(() => {
  window.removeEventListener('vision-analysis-complete', onVisionAnalysisComplete)
})
</script>

<style lang="scss" scoped>
@use '../../styles/design-tokens' as *;

/* Card uses darker background color for layered effect */
/* Header and footer inherit this dark background, content area is lighter */
.product-form-card {
  background: rgb(var(--v-theme-background)) !important;
}

/* Button toggle tabs styling - matches Settings page pattern */
.bordered-tabs-content {
  border: none;
  border-top: none;
  border-radius: 0 $border-radius-default $border-radius-default $border-radius-default;
  padding: 16px;
  background: rgb(var(--v-theme-surface));
}

/* All tabs - transparent background by default, remove bottom border */
:deep(.v-btn-toggle > .v-btn) {
  background: transparent !important;
  border-bottom-color: transparent !important;
}

/* Inactive tabs - faded text, transparent background (shows darker card bg) */
:deep(.v-btn-toggle > .v-btn:not(.v-btn--active)) {
  color: rgba(255, 255, 255, 0.5) !important;
  background: transparent !important;
}

/* Active tab - lighter surface background that matches content area */
:deep(.v-btn-toggle > .v-btn.v-btn--active) {
  background: rgb(var(--v-theme-surface)) !important;
  color: white !important;
}

/* Override Vuetify overlay on active button */
:deep(.v-btn-toggle > .v-btn.v-btn--active > .v-btn__overlay) {
  opacity: 0 !important;
}
</style>
