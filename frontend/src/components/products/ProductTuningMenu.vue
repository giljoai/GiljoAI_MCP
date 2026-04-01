<template>
  <div class="product-tuning-menu">
    <!-- Tune Context Button -->
    <v-btn
      variant="outlined"
      color="primary"
      :loading="loadingSections"
      :disabled="loadingSections"
      @click="togglePanel"
    >
      <v-icon start>mdi-tune</v-icon>
      Tune Context
    </v-btn>

    <!-- Section Selection Panel -->
    <v-expand-transition>
      <v-card v-if="panelOpen" variant="flat" class="mt-3 smooth-border tuning-card">
        <v-card-title class="text-subtitle-1 d-flex align-center">
          <v-icon start size="20">mdi-format-list-checks</v-icon>
          Select Sections to Tune
        </v-card-title>

        <v-divider />

        <v-card-text>
          <!-- Loading state -->
          <div v-if="loadingSections" class="d-flex align-center justify-center py-4">
            <v-progress-circular indeterminate color="primary" size="24" class="mr-3" />
            <span class="text-body-2">Loading available sections...</span>
          </div>

          <!-- Error state -->
          <v-alert
            v-else-if="sectionsError"
            type="error"
            variant="tonal"
            density="compact"
            class="mb-0"
          >
            {{ sectionsError }}
          </v-alert>

          <!-- Sections list -->
          <div v-else-if="sections.length > 0">
            <!-- Select All -->
            <v-checkbox
              :model-value="allSelected"
              :indeterminate="someSelected && !allSelected"
              label="Select All"
              density="compact"
              hide-details
              color="primary"
              class="mb-1"
              @update:model-value="toggleSelectAll"
            />

            <v-divider class="my-2" />

            <!-- Individual section checkboxes -->
            <v-checkbox
              v-for="section in sections"
              :key="section"
              v-model="selectedSections"
              :value="section"
              :label="getSectionLabel(section)"
              density="compact"
              hide-details
              color="primary"
              class="mb-1"
            />
          </div>

          <!-- No sections available -->
          <v-alert
            v-else
            type="info"
            variant="tonal"
            density="compact"
            class="mb-0"
          >
            No tunable sections available for this product.
          </v-alert>
        </v-card-text>

        <v-divider v-if="sections.length > 0" />

        <v-card-actions v-if="sections.length > 0">
          <v-spacer />
          <v-btn
            variant="text"
            @click="panelOpen = false"
          >
            Cancel
          </v-btn>
          <v-btn
            variant="flat"
            color="primary"
            :loading="generatingPrompt"
            :disabled="selectedSections.length === 0 || generatingPrompt"
            @click="generatePrompt"
          >
            <v-icon start>mdi-creation</v-icon>
            Generate Tuning Prompt
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-expand-transition>

    <!-- Generated Prompt Display -->
    <v-expand-transition>
      <v-card v-if="generatedPrompt" variant="flat" class="mt-3 smooth-border tuning-card">
        <v-card-title class="text-subtitle-1 d-flex align-center">
          <v-icon start size="20">mdi-text-box-outline</v-icon>
          Generated Tuning Prompt
          <v-spacer />
          <v-btn
            variant="text"
            size="small"
            :color="copied ? 'success' : 'primary'"
            @click="copyPrompt"
          >
            <v-icon start size="16">{{ copied ? 'mdi-check' : 'mdi-content-copy' }}</v-icon>
            {{ copied ? 'Copied' : 'Copy' }}
          </v-btn>
        </v-card-title>

        <v-divider />

        <v-card-text>
          <v-textarea
            :model-value="generatedPrompt"
            readonly
            auto-grow
            rows="8"
            max-rows="20"
            variant="outlined"
            density="compact"
            hide-details
            aria-label="Generated tuning prompt"
          />
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="generatedPrompt = ''"
          >
            Dismiss
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-expand-transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '@/services/api'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'

const props = defineProps({
  productId: {
    type: String,
    required: true,
  },
})

const { copy: clipboardCopy, copied } = useClipboard()
const { showToast } = useToast()

// Panel state
const panelOpen = ref(false)
const sections = ref([])
const selectedSections = ref([])
const loadingSections = ref(false)
const sectionsError = ref('')

// Prompt generation state
const generatingPrompt = ref(false)
const generatedPrompt = ref('')

// Section display labels
const SECTION_LABELS = {
  description: 'Product Description',
  tech_stack: 'Tech Stack',
  architecture: 'Architecture',
  core_features: 'Core Features',
  codebase_structure: 'Codebase Structure',
  database_type: 'Database',
  backend_framework: 'Backend Framework',
  frontend_framework: 'Frontend Framework',
  quality_standards: 'Quality Standards',
  target_platforms: 'Target Platforms',
  vision_documents: 'Vision Documents',
}

// Computed: selection state
const allSelected = computed(() => {
  return sections.value.length > 0 && selectedSections.value.length === sections.value.length
})

const someSelected = computed(() => {
  return selectedSections.value.length > 0
})

/**
 * Get human-readable label for a section key
 */
function getSectionLabel(section) {
  return SECTION_LABELS[section] || section.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

/**
 * Toggle the section selection panel.
 * Fetches available sections on first open.
 */
async function togglePanel() {
  if (panelOpen.value) {
    panelOpen.value = false
    return
  }

  panelOpen.value = true
  await fetchSections()
}

/**
 * Fetch eligible tuning sections from the API
 */
async function fetchSections() {
  loadingSections.value = true
  sectionsError.value = ''

  try {
    const response = await api.products.getTuningSections(props.productId)
    const data = response.data
    sections.value = data.sections || []
    // Pre-select all sections by default
    selectedSections.value = [...sections.value]
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to load tuning sections'
    sectionsError.value = message
    console.error('[ProductTuningMenu] Failed to fetch sections:', error)
  } finally {
    loadingSections.value = false
  }
}

/**
 * Toggle select-all / deselect-all
 */
function toggleSelectAll(value) {
  if (value) {
    selectedSections.value = [...sections.value]
  } else {
    selectedSections.value = []
  }
}

/**
 * Generate the tuning prompt for selected sections
 */
async function generatePrompt() {
  generatingPrompt.value = true

  try {
    const response = await api.products.generateTuningPrompt(
      props.productId,
      selectedSections.value,
    )

    const data = response.data
    generatedPrompt.value = data.prompt || data.generated_prompt || ''

    if (!generatedPrompt.value) {
      showToast({ message: 'No prompt was generated. Check that selected sections have data.', type: 'warning' })
    }
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to generate tuning prompt'
    showToast({ message, type: 'error' })
    console.error('[ProductTuningMenu] Failed to generate prompt:', error)
  } finally {
    generatingPrompt.value = false
  }
}

/**
 * Copy the generated prompt to clipboard
 */
async function copyPrompt() {
  const success = await clipboardCopy(generatedPrompt.value)
  if (success) {
    showToast({ message: 'Tuning prompt copied to clipboard', type: 'success' })
  } else {
    showToast({ message: 'Failed to copy to clipboard', type: 'error' })
  }
}
</script>

<style lang="scss" scoped>
@use '../../styles/design-tokens' as *;

.tuning-card {
  border-radius: $border-radius-md;
}
</style>
