<template>
  <v-dialog
    :model-value="show"
    :fullscreen="isMobile"
    :max-width="isMobile ? undefined : '900'"
    persistent
    class="closeout-modal"
    role="dialog"
    :aria-labelledby="'closeout-modal-title'"
    data-testid="closeout-modal"
    @keydown.esc="handleClose"
  >
    <v-card v-draggable data-testid="closeout-modal">
      <!-- Modal header -->
      <v-card-title id="closeout-modal-title" class="modal-title bg-primary text-white pa-4">
        <div class="d-flex align-center justify-space-between">
          <div class="d-flex align-center">
            <v-icon icon="mdi-memory" size="large" class="mr-2" />
            <span class="text-h6">Project 360 Memory: {{ projectName }}</span>
          </div>
          <v-btn icon variant="text" color="white" :aria-label="'Close modal'" @click="handleClose">
            <v-icon icon="mdi-close" />
          </v-btn>
        </div>
      </v-card-title>

      <v-divider />

      <!-- Modal content -->
      <v-card-text class="pa-4">
        <!-- 360 Memory Info Banner -->
        <v-alert
          type="info"
          variant="tonal"
          density="compact"
          class="mb-4"
          icon="mdi-information"
        >
          <template #title>
            <span class="text-body-2 font-weight-medium">360 Memory Entries</span>
          </template>
          <span class="text-body-2">
            Review the cumulative knowledge and project history stored in this product's 360 Memory.
            These entries provide context for future projects and orchestrator decision-making.
          </span>
        </v-alert>

        <!-- Loading state -->
        <div v-if="loading" class="text-center py-8">
          <v-progress-circular indeterminate color="primary" size="64" />
          <div class="text-body-1 mt-4">Loading 360 memory entries...</div>
        </div>

        <!-- Error state -->
        <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
          {{ error }}
        </v-alert>

        <!-- No entries state -->
        <v-alert
          v-if="!loading && !error && memoryEntries.length === 0"
          type="info"
          variant="outlined"
          class="mb-4"
        >
          No 360 memory entries found for this project yet. Memory entries are created when
          projects are completed or when orchestrators trigger handovers.
        </v-alert>

        <!-- Memory Entries -->
        <div v-if="!loading && !error && memoryEntries.length > 0">
          <div class="text-subtitle-1 font-weight-medium mb-3">
            {{ memoryEntries.length }} Memory
            {{ memoryEntries.length === 1 ? 'Entry' : 'Entries' }} Found
          </div>

          <v-expansion-panels v-model="expandedPanels" multiple variant="accordion">
            <v-expansion-panel
              v-for="(entry, index) in memoryEntries"
              :key="index"
              :value="index"
            >
              <v-expansion-panel-title>
                <div class="d-flex align-center w-100">
                  <v-icon icon="mdi-book-open-page-variant" class="mr-2" size="small" />
                  <span class="font-weight-medium">
                    Entry #{{ entry.sequence }} - {{ formatEntryType(entry.type) }}
                  </span>
                  <v-spacer />
                  <span class="text-caption text-grey">
                    {{ formatDate(entry.timestamp) }}
                  </span>
                </div>
              </v-expansion-panel-title>

              <v-expansion-panel-text>
                <!-- Summary section -->
                <div v-if="entry.summary" class="mb-4">
                  <h4 class="text-subtitle-2 font-weight-bold mb-2">Summary</h4>
                  <div class="text-body-2 summary-text">{{ entry.summary }}</div>
                </div>

                <!-- Key Outcomes -->
                <div v-if="entry.key_outcomes && entry.key_outcomes.length > 0" class="mb-4">
                  <h4 class="text-subtitle-2 font-weight-bold mb-2">Key Outcomes</h4>
                  <v-list density="compact" class="outcomes-list">
                    <v-list-item
                      v-for="(outcome, outcomeIndex) in entry.key_outcomes"
                      :key="outcomeIndex"
                      class="px-0"
                    >
                      <template #prepend>
                        <v-icon icon="mdi-check-circle" color="success" size="small" class="mr-2" />
                      </template>
                      <v-list-item-title class="text-body-2">{{ outcome }}</v-list-item-title>
                    </v-list-item>
                  </v-list>
                </div>

                <!-- Decisions Made -->
                <div v-if="entry.decisions_made && entry.decisions_made.length > 0" class="mb-4">
                  <h4 class="text-subtitle-2 font-weight-bold mb-2">Decisions Made</h4>
                  <v-list density="compact" class="decisions-list">
                    <v-list-item
                      v-for="(decision, decisionIndex) in entry.decisions_made"
                      :key="decisionIndex"
                      class="px-0"
                    >
                      <template #prepend>
                        <v-icon icon="mdi-lightbulb" color="warning" size="small" class="mr-2" />
                      </template>
                      <v-list-item-title class="text-body-2">{{ decision }}</v-list-item-title>
                    </v-list-item>
                  </v-list>
                </div>

                <!-- Git Commits (if available) -->
                <div v-if="entry.git_commits && entry.git_commits.length > 0" class="mb-4">
                  <h4 class="text-subtitle-2 font-weight-bold mb-2">
                    Git Commits ({{ entry.git_commits.length }})
                  </h4>
                  <v-list density="compact" class="git-commits-list" max-height="300" style="overflow-y: auto">
                    <v-list-item
                      v-for="(commit, commitIndex) in entry.git_commits"
                      :key="commitIndex"
                      class="px-2 py-1"
                    >
                      <template #prepend>
                        <v-icon icon="mdi-source-commit" color="info" size="small" class="mr-2" />
                      </template>
                      <v-list-item-title class="text-body-2">
                        {{ commit.message }}
                      </v-list-item-title>
                      <v-list-item-subtitle class="text-caption">
                        {{ commit.author }} - {{ formatCommitDate(commit.timestamp) }}
                      </v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </div>

                <!-- Metadata -->
                <div class="metadata-section mt-4 pt-3" style="border-top: 1px solid rgba(0,0,0,0.12)">
                  <div class="d-flex text-caption text-grey">
                    <div class="mr-4">
                      <strong>Type:</strong> {{ entry.type }}
                    </div>
                    <div v-if="entry.sequence">
                      <strong>Sequence:</strong> #{{ entry.sequence }}
                    </div>
                  </div>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </div>

        <!-- Action Guidance -->
        <v-alert
          v-if="!loading && !error"
          type="success"
          variant="tonal"
          density="compact"
          class="mt-4"
          icon="mdi-check-circle"
        >
          <template #title>
            <span class="text-body-2 font-weight-medium">Next Steps</span>
          </template>
          <div class="text-body-2">
            <strong>Continue Working:</strong> Keep this project active and continue development.
            <br />
            <strong>Close Out Project:</strong> Archive this project and mark it as completed in 360 Memory.
          </div>
        </v-alert>
      </v-card-text>

      <v-divider />

      <!-- Modal actions -->
      <v-card-actions class="pa-4">
        <v-btn
          color="primary"
          variant="elevated"
          :loading="continueLoading"
          :disabled="closeoutLoading"
          prepend-icon="mdi-play-circle"
          :aria-label="'Continue working on project'"
          data-testid="continue-working-btn"
          @click="handleContinueWorking"
        >
          Continue Working
        </v-btn>
        <v-btn
          color="success"
          variant="elevated"
          :loading="closeoutLoading"
          :disabled="continueLoading"
          prepend-icon="mdi-check-circle"
          :aria-label="'Close out project'"
          data-testid="close-out-btn"
          @click="handleCloseOutProject"
        >
          Close Out Project
        </v-btn>
        <v-spacer />
        <v-btn
          variant="text"
          :disabled="continueLoading || closeoutLoading"
          :aria-label="'Cancel'"
          @click="handleClose"
        >
          Cancel
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useDisplay } from 'vuetify'
import api from '@/services/api'

const props = defineProps({
  show: {
    type: Boolean,
    required: true,
  },
  projectId: {
    type: String,
    required: true,
  },
  projectName: {
    type: String,
    required: true,
  },
  productId: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['close', 'continue', 'closeout'])

// Vuetify display breakpoints
const { mobile } = useDisplay()
const isMobile = computed(() => mobile.value)

// Reactive state
const loading = ref(false)
const error = ref(null)
const memoryEntries = ref([])
const expandedPanels = ref([]) // Multiple panels can be expanded
const continueLoading = ref(false)
const closeoutLoading = ref(false)

// Watch for modal open to load data
watch(
  () => props.show,
  (newValue) => {
    if (newValue) {
      loadMemoryEntries()
      // Expand first entry by default
      expandedPanels.value = [0]
    } else {
      resetState()
    }
  },
)

// Methods
const loadMemoryEntries = async () => {
  loading.value = true
  error.value = null
  memoryEntries.value = []

  try {
    // Handover 0490: Fetch memory entries from normalized table via new API endpoint
    const response = await api.products.getMemoryEntries(
      props.productId,
      {
        project_id: props.projectId,
        limit: 10
      }
    )

    // API returns structured response: { success, entries, total_count, filtered_count }
    memoryEntries.value = response.data.entries || []
  } catch (err) {
    console.error('[CloseoutModal] Failed to load 360 memory:', err)
    error.value =
      err.response?.data?.message || err.message || 'Failed to load 360 memory entries'
  } finally {
    loading.value = false
  }
}

const handleContinueWorking = async () => {
  continueLoading.value = true
  error.value = null

  try {
    // Call the continue-working endpoint to restore/reactivate project
    await api.projects.restoreCompleted(props.projectId)

    emit('continue')
    emit('close')
  } catch (err) {
    console.error('[CloseoutModal] Failed to continue working:', err)
    error.value =
      err.response?.data?.message || err.message || 'Failed to continue working on project'
  } finally {
    continueLoading.value = false
  }
}

const handleCloseOutProject = async () => {
  closeoutLoading.value = true
  error.value = null

  try {
    // Call the archive endpoint to close out project (Handover 0412)
    const response = await api.projects.archive(props.projectId)

    emit('closeout', response.data)
    emit('close')
  } catch (err) {
    console.error('[CloseoutModal] Failed to close out project:', err)
    error.value = err.response?.data?.message || err.message || 'Failed to close out project'
  } finally {
    closeoutLoading.value = false
  }
}

const handleClose = () => {
  if (!continueLoading.value && !closeoutLoading.value) {
    emit('close')
  }
}

const formatDate = (timestamp) => {
  if (!timestamp) return 'Unknown'
  try {
    const date = new Date(timestamp)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return timestamp
  }
}

const formatCommitDate = (timestamp) => {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return timestamp
  }
}

const formatEntryType = (type) => {
  if (!type) return 'Unknown'
  // Convert snake_case to Title Case
  return type
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

const resetState = () => {
  expandedPanels.value = []
  error.value = null
  memoryEntries.value = []
  continueLoading.value = false
  closeoutLoading.value = false
}
</script>

<style scoped>
.modal-title {
  position: sticky;
  top: 0;
  z-index: 1;
}

.summary-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.6;
}

.outcomes-list,
.decisions-list {
  background-color: transparent;
}

.git-commits-list {
  background-color: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
  padding: 8px 0;
}

.metadata-section {
  background-color: rgba(0, 0, 0, 0.02);
  padding: 12px;
  border-radius: 4px;
}

/* Focus trap for accessibility */
.v-dialog {
  outline: none;
}

/* Ensure proper spacing */
.v-list-item {
  min-height: 40px;
}

/* Mobile optimizations */
@media (max-width: 600px) {
  .modal-title {
    font-size: 1.125rem;
  }

  .git-commits-list {
    max-height: 200px;
  }
}

/* Expansion panel styling */
:deep(.v-expansion-panel-title) {
  font-size: 0.95rem;
  padding: 12px 16px;
}

:deep(.v-expansion-panel-text__wrapper) {
  padding: 16px 20px;
}
</style>
