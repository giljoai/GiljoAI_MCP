<template>
  <div class="product-tuning-review">
    <!-- Overall Summary Banner -->
    <v-alert
      v-if="proposals?.overall_summary"
      type="info"
      variant="tonal"
      density="compact"
      class="mb-4"
    >
      <template v-slot:prepend>
        <v-icon>mdi-information-outline</v-icon>
      </template>
      <div class="text-subtitle-2 mb-1">Tuning Analysis Summary</div>
      <div class="text-body-2">{{ proposals.overall_summary }}</div>
    </v-alert>

    <!-- No proposals state -->
    <v-alert
      v-if="!sectionKeys.length"
      type="info"
      variant="tonal"
      density="compact"
    >
      No pending proposals to review.
    </v-alert>

    <!-- Per-section expansion panels -->
    <v-expansion-panels
      v-if="sectionKeys.length"
      v-model="expandedPanels"
      variant="accordion"
      multiple
    >
      <v-expansion-panel
        v-for="sectionKey in sectionKeys"
        :key="sectionKey"
      >
        <v-expansion-panel-title>
          <div class="d-flex align-center flex-wrap ga-2" style="width: 100%">
            <v-icon start size="20">{{ getSectionIcon(sectionKey) }}</v-icon>
            <span class="text-subtitle-2">{{ getSectionLabel(sectionKey) }}</span>
            <v-spacer />
            <!-- Drift badge -->
            <span
              class="tuning-chip"
              :style="getSectionData(sectionKey).drift_detected
                ? 'background: rgba(224,120,114,0.15); color: #E07872'
                : 'background: rgba(103,189,109,0.15); color: #67bd6d'"
              :aria-label="getSectionData(sectionKey).drift_detected ? 'Drift detected' : 'No drift'"
            >
              <v-icon start size="14">
                {{ getSectionData(sectionKey).drift_detected ? 'mdi-alert-circle' : 'mdi-check-circle' }}
              </v-icon>
              {{ getSectionData(sectionKey).drift_detected ? 'Drift' : 'Current' }}
            </span>
            <!-- Confidence chip -->
            <span
              class="tuning-chip"
              :style="getConfidenceStyle(getSectionData(sectionKey).confidence)"
              :aria-label="'Confidence: ' + (getSectionData(sectionKey).confidence || 'unknown')"
            >
              {{ formatConfidence(getSectionData(sectionKey).confidence) }}
            </span>
          </div>
        </v-expansion-panel-title>

        <v-expansion-panel-text>
          <div class="py-2">
            <!-- Current Value -->
            <div class="mb-4">
              <div class="text-caption font-weight-bold mb-1" style="color: #8895a8">Current Value</div>
              <v-card variant="flat" class="pa-3 smooth-border" style="border-radius: 8px">
                <div class="text-body-2" style="white-space: pre-wrap;">
                  {{ getSectionData(sectionKey).current_summary || 'No current value' }}
                </div>
              </v-card>
            </div>

            <!-- Evidence -->
            <div v-if="getSectionData(sectionKey).evidence" class="mb-4">
              <div class="text-caption font-weight-bold mb-1" style="color: #8895a8">Evidence</div>
              <div class="text-body-2" style="white-space: pre-wrap; color: #8895a8">
                {{ getSectionData(sectionKey).evidence }}
              </div>
            </div>

            <!-- Proposed Value -->
            <div class="mb-4">
              <div class="text-caption font-weight-bold mb-1" style="color: #8895a8">Proposed Value</div>

              <!-- Edit mode -->
              <div v-if="editingSection === sectionKey">
                <v-textarea
                  v-model="editValue"
                  variant="outlined"
                  density="compact"
                  auto-grow
                  rows="4"
                  max-rows="12"
                  aria-label="Edit proposed value"
                />
                <div class="d-flex ga-2 mt-2">
                  <v-btn
                    variant="flat"
                    color="primary"
                    size="small"
                    :loading="actionLoading === sectionKey"
                    @click="applyAction(sectionKey, 'accept', editValue)"
                  >
                    Save
                  </v-btn>
                  <v-btn
                    variant="text"
                    size="small"
                    @click="cancelEdit"
                  >
                    Cancel
                  </v-btn>
                </div>
              </div>

              <!-- Display mode -->
              <v-card
                v-else
                variant="flat"
                :class="[
                  'pa-3 smooth-border',
                ]"
                :style="hasValueChanged(sectionKey) ? 'border-radius: 8px; --smooth-border-color: #EDBA4A' : 'border-radius: 8px'"
              >
                <div class="text-body-2" style="white-space: pre-wrap;">
                  {{ getSectionData(sectionKey).proposed_value || 'No change proposed' }}
                </div>
              </v-card>
            </div>

            <!-- Reasoning -->
            <div v-if="getSectionData(sectionKey).reasoning" class="mb-4">
              <div class="text-caption font-weight-bold mb-1" style="color: #8895a8">Reasoning</div>
              <div class="text-body-2" style="white-space: pre-wrap; color: #8895a8">
                {{ getSectionData(sectionKey).reasoning }}
              </div>
            </div>

            <!-- Action buttons (only shown when not editing) -->
            <div v-if="editingSection !== sectionKey" class="d-flex ga-2 flex-wrap">
              <v-btn
                variant="flat"
                color="success"
                size="small"
                :loading="actionLoading === sectionKey && actionType === 'accept'"
                :disabled="!!actionLoading"
                @click="applyAction(sectionKey, 'accept')"
              >
                <v-icon start size="16">mdi-check</v-icon>
                Accept
              </v-btn>
              <v-btn
                variant="flat"
                color="warning"
                size="small"
                :disabled="!!actionLoading"
                @click="startEdit(sectionKey)"
              >
                <v-icon start size="16">mdi-pencil</v-icon>
                Edit
              </v-btn>
              <v-btn
                variant="outlined"
                size="small"
                :loading="actionLoading === sectionKey && actionType === 'dismiss'"
                :disabled="!!actionLoading"
                @click="applyAction(sectionKey, 'dismiss')"
              >
                <v-icon start size="16">mdi-close</v-icon>
                Dismiss
              </v-btn>
            </div>
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- Dismiss All button -->
    <div v-if="sectionKeys.length > 1" class="d-flex justify-end mt-4">
      <v-btn
        variant="outlined"
        :loading="dismissingAll"
        :disabled="dismissingAll || !!actionLoading"
        @click="confirmDismissAll"
      >
        <v-icon start>mdi-close-circle-outline</v-icon>
        Dismiss All
      </v-btn>
    </div>

    <!-- Confirm Dismiss All Dialog -->
    <v-dialog v-model="dismissAllDialog" max-width="400">
      <v-card>
        <v-card-title class="text-subtitle-1">Dismiss All Proposals</v-card-title>
        <v-card-text>
          Are you sure you want to dismiss all {{ sectionKeys.length }} pending proposals?
          This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dismissAllDialog = false">Cancel</v-btn>
          <v-btn
            variant="flat"
            color="error"
            :loading="dismissingAll"
            @click="dismissAll"
          >
            Dismiss All
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { apiClient } from '@/services/api'
import { useToast } from '@/composables/useToast'

const props = defineProps({
  productId: {
    type: String,
    required: true,
  },
  proposals: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['proposals-updated'])

const { showToast } = useToast()

// UI state
const expandedPanels = ref([])
const editingSection = ref(null)
const editValue = ref('')
const actionLoading = ref(null)
const actionType = ref('')
const dismissingAll = ref(false)
const dismissAllDialog = ref(false)

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

// Section icons
const SECTION_ICONS = {
  description: 'mdi-text',
  tech_stack: 'mdi-code-tags',
  architecture: 'mdi-sitemap',
  core_features: 'mdi-star-outline',
  codebase_structure: 'mdi-folder-outline',
  database_type: 'mdi-database',
  backend_framework: 'mdi-server',
  frontend_framework: 'mdi-monitor',
  quality_standards: 'mdi-check-decagram',
  target_platforms: 'mdi-devices',
  vision_documents: 'mdi-file-document-outline',
}

/**
 * Computed list of section keys from proposals,
 * excluding non-section properties like overall_summary
 */
const sectionKeys = computed(() => {
  if (!props.proposals) return []
  return Object.keys(props.proposals).filter(
    (key) => key !== 'overall_summary' && typeof props.proposals[key] === 'object'
  )
})

/**
 * Get section data from proposals, with safe defaults
 */
function getSectionData(sectionKey) {
  return props.proposals?.[sectionKey] || {}
}

/**
 * Get human-readable label for a section key
 */
function getSectionLabel(sectionKey) {
  return SECTION_LABELS[sectionKey] || sectionKey.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

/**
 * Get icon for a section key
 */
function getSectionIcon(sectionKey) {
  return SECTION_ICONS[sectionKey] || 'mdi-file-document-outline'
}

/**
 * Map confidence level to tinted chip inline style
 */
function getConfidenceStyle(confidence) {
  switch (confidence?.toLowerCase()) {
    case 'high':
      return 'background: rgba(103,189,109,0.15); color: #67bd6d'
    case 'medium':
      return 'background: rgba(237,186,74,0.15); color: #EDBA4A'
    case 'low':
      return 'background: rgba(224,120,114,0.15); color: #E07872'
    default:
      return 'background: rgba(255,255,255,0.05); color: #8895a8'
  }
}

/**
 * Format confidence label for display
 */
function formatConfidence(confidence) {
  if (!confidence) return 'Unknown'
  return confidence.charAt(0).toUpperCase() + confidence.slice(1).toLowerCase()
}

/**
 * Check if proposed value differs from current value
 */
function hasValueChanged(sectionKey) {
  const data = getSectionData(sectionKey)
  return data.proposed_value && data.current_summary && data.proposed_value !== data.current_summary
}

/**
 * Enter edit mode for a section
 */
function startEdit(sectionKey) {
  editingSection.value = sectionKey
  editValue.value = getSectionData(sectionKey).proposed_value || ''
}

/**
 * Cancel editing
 */
function cancelEdit() {
  editingSection.value = null
  editValue.value = ''
}

/**
 * Apply an action (accept, dismiss) on a specific section proposal.
 * When editing, the edited value is sent as the proposed value.
 */
async function applyAction(sectionKey, action, editedValue) {
  actionLoading.value = sectionKey
  actionType.value = action

  try {
    const body = { action }
    if (editedValue !== undefined) {
      body.edited_value = editedValue
    }

    await apiClient.post(
      `/api/v1/products/${props.productId}/tuning/proposals/${sectionKey}/apply`,
      body
    )

    const label = getSectionLabel(sectionKey)
    const actionLabel = action === 'accept' ? 'accepted' : 'dismissed'
    showToast({ message: `${label} proposal ${actionLabel}`, type: 'success' })

    // Exit edit mode if we were editing
    if (editingSection.value === sectionKey) {
      cancelEdit()
    }

    emit('proposals-updated')
  } catch (error) {
    const message = error.response?.data?.detail || `Failed to ${action} proposal`
    showToast({ message, type: 'error' })
    console.error(`[ProductTuningReview] Failed to ${action} proposal for ${sectionKey}:`, error)
  } finally {
    actionLoading.value = null
    actionType.value = ''
  }
}

/**
 * Show confirmation dialog for dismissing all proposals
 */
function confirmDismissAll() {
  dismissAllDialog.value = true
}

/**
 * Dismiss all pending proposals
 */
async function dismissAll() {
  dismissingAll.value = true

  try {
    await apiClient.post(
      `/api/v1/products/${props.productId}/tuning/dismiss-all`
    )

    showToast({ message: 'All proposals dismissed', type: 'success' })
    dismissAllDialog.value = false
    emit('proposals-updated')
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to dismiss all proposals'
    showToast({ message, type: 'error' })
    console.error('[ProductTuningReview] Failed to dismiss all proposals:', error)
  } finally {
    dismissingAll.value = false
  }
}
</script>

<style scoped>
.tuning-chip {
  display: inline-flex;
  align-items: center;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 8px;
  line-height: 1.4;
  letter-spacing: 0.02em;
}
</style>
