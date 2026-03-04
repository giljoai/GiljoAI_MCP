<template>
  <v-card v-draggable class="template-archive">
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2" color="primary">
        <img src="/icons/archive.svg" width="24" height="24" alt="Archive" />
      </v-icon>
      <span>Version History: {{ template.name }}</span>
      <v-spacer />
      <v-btn icon="mdi-close" variant="text" @click="$emit('close')" />
    </v-card-title>

    <v-card-text>
      <!-- Timeline View -->
      <v-timeline align="start" density="compact" side="end" class="version-timeline">
        <v-timeline-item
          v-for="(version, index) in versions"
          :key="version.id"
          :dot-color="getVersionColor(version, index)"
          :size="index === 0 ? 'default' : 'small'"
          :icon="getVersionIcon(version, index)"
        >
          <template v-slot:opposite>
            <div class="text-caption text-grey">
              {{ formatDate(version.created_at) }}
            </div>
          </template>

          <v-card
            :color="index === 0 ? 'surface-variant' : 'surface'"
            variant="outlined"
            density="compact"
            class="version-card"
          >
            <v-card-title class="text-subtitle-2 d-flex align-center">
              <span>Version {{ versions.length - index }}</span>
              <v-chip v-if="index === 0" size="x-small" color="success" class="ml-2">
                Current
              </v-chip>
              <v-chip v-if="version.archived" size="x-small" color="warning" class="ml-2">
                Archived
              </v-chip>
              <v-spacer />
              <v-btn
                v-if="index !== 0"
                size="small"
                variant="text"
                @click="compareWithCurrent(version)"
              >
                Compare
              </v-btn>
              <v-btn
                v-if="index !== 0"
                size="small"
                variant="text"
                color="primary"
                @click="restoreVersion(version)"
              >
                Restore
              </v-btn>
            </v-card-title>

            <v-card-text class="pt-1">
              <div class="version-metadata">
                <div class="text-caption">
                  <strong>Modified by:</strong> {{ version.modified_by || 'System' }}
                </div>
                <div v-if="version.change_reason" class="text-caption">
                  <strong>Reason:</strong> {{ version.change_reason }}
                </div>
                <div class="text-caption">
                  <strong>Changes:</strong>
                  <v-chip
                    v-for="change in getChangeSummary(version, index)"
                    :key="change"
                    size="x-small"
                    variant="outlined"
                    class="mr-1"
                  >
                    {{ change }}
                  </v-chip>
                </div>
              </div>

              <v-expand-transition>
                <div v-if="expandedVersions.has(version.id)">
                  <v-divider class="my-2" />
                  <div class="version-content">
                    <pre class="template-content">{{ version.template }}</pre>
                  </div>
                </div>
              </v-expand-transition>

              <v-btn size="x-small" variant="text" class="mt-2" @click="toggleVersion(version.id)">
                {{ expandedVersions.has(version.id) ? 'Hide' : 'Show' }} Template
                <v-icon right>
                  {{ expandedVersions.has(version.id) ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
                </v-icon>
              </v-btn>
            </v-card-text>
          </v-card>
        </v-timeline-item>
      </v-timeline>

      <!-- Loading State -->
      <div v-if="loading" class="text-center py-4">
        <v-progress-circular indeterminate color="primary" />
      </div>

      <!-- Empty State -->
      <div v-if="!loading && versions.length === 0" class="text-center py-8">
        <v-icon size="64" color="grey">mdi-history</v-icon>
        <div class="text-h6 mt-4">No Version History</div>
        <div class="text-caption">This template has no previous versions</div>
      </div>
    </v-card-text>

    <!-- Diff Dialog -->
    <v-dialog v-model="diffDialog" max-width="1200px" scrollable>
      <v-card v-draggable>
        <v-card-title class="d-flex align-center">
          <span class="text-h5">Compare Versions</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" aria-label="Close" @click="diffDialog = false" />
        </v-card-title>

        <v-card-text>
          <v-row>
            <v-col cols="12" md="6">
              <div class="text-subtitle-2 mb-2">
                Current Version
                <v-chip size="x-small" color="success" class="ml-2">Active</v-chip>
              </div>
              <v-card variant="outlined" class="diff-panel">
                <pre class="diff-content">{{ currentVersion?.template }}</pre>
              </v-card>
            </v-col>
            <v-col cols="12" md="6">
              <div class="text-subtitle-2 mb-2">
                Version {{ getVersionNumber(comparingVersion) }}
                <v-chip size="x-small" color="grey" class="ml-2">
                  {{ formatDate(comparingVersion?.created_at) }}
                </v-chip>
              </div>
              <v-card variant="outlined" class="diff-panel">
                <pre class="diff-content">{{ comparingVersion?.template }}</pre>
              </v-card>
            </v-col>
          </v-row>

          <!-- Differences Summary -->
          <v-row class="mt-4">
            <v-col cols="12">
              <v-card variant="outlined">
                <v-card-title class="text-subtitle-1">Differences</v-card-title>
                <v-card-text>
                  <div class="diff-summary">
                    <div v-for="diff in differences" :key="diff.line" class="diff-line">
                      <span :class="getDiffClass(diff.type)">
                        {{ diff.type === 'add' ? '+' : diff.type === 'remove' ? '-' : ' ' }}
                        {{ diff.content }}
                      </span>
                    </div>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="diffDialog = false">Close</v-btn>
          <v-btn color="primary" variant="flat" @click="restoreVersion(comparingVersion)">
            Restore This Version
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Restore Confirmation Dialog -->
    <v-dialog v-model="restoreDialog" max-width="500px">
      <v-card v-draggable>
        <v-card-title class="d-flex align-center">
          <span class="text-h5">Confirm Restore</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" aria-label="Close" @click="cancelRestore" />
        </v-card-title>
        <v-card-text>
          <div class="mb-4">
            Are you sure you want to restore Version {{ getVersionNumber(restoringVersion) }}? This
            will replace the current template with this version.
          </div>
          <v-text-field
            v-model="restoreReason"
            label="Reason for restore (optional)"
            hint="Explain why you're restoring this version"
            persistent-hint
            density="compact"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="cancelRestore">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :loading="restoring" @click="confirmRestore">
            Restore
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'
import { format, formatDistanceToNow } from 'date-fns'

const props = defineProps({
  template: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['close', 'restore'])

// Reactive data
const versions = ref([])
const loading = ref(false)
const restoring = ref(false)
const expandedVersions = ref(new Set())

// Diff dialog
const diffDialog = ref(false)
const currentVersion = ref(null)
const comparingVersion = ref(null)
const differences = ref([])

// Restore dialog
const restoreDialog = ref(false)
const restoringVersion = ref(null)
const restoreReason = ref('')

// Methods
const loadVersionHistory = async () => {
  loading.value = true
  try {
    // Handover 0396: Use structured api.templates.history() method
    const response = await api.templates.history(props.template.id)
    versions.value = response.data.versions || []

    // Set current version as the first one
    if (versions.value.length > 0) {
      currentVersion.value = versions.value[0]
    }
  } catch (error) {
    console.error('Failed to load version history:', error)
  } finally {
    loading.value = false
  }
}

const toggleVersion = (versionId) => {
  if (expandedVersions.value.has(versionId)) {
    expandedVersions.value.delete(versionId)
  } else {
    expandedVersions.value.add(versionId)
  }
}

const compareWithCurrent = (version) => {
  comparingVersion.value = version
  calculateDifferences()
  diffDialog.value = true
}

const calculateDifferences = () => {
  if (!currentVersion.value || !comparingVersion.value) return

  const currentLines = currentVersion.value.template.split('\n')
  const compareLines = comparingVersion.value.template.split('\n')
  const diffs = []

  const maxLines = Math.max(currentLines.length, compareLines.length)

  for (let i = 0; i < maxLines; i++) {
    const currentLine = currentLines[i] || ''
    const compareLine = compareLines[i] || ''

    if (currentLine !== compareLine) {
      if (i >= compareLines.length) {
        diffs.push({ line: i, type: 'add', content: currentLine })
      } else if (i >= currentLines.length) {
        diffs.push({ line: i, type: 'remove', content: compareLine })
      } else {
        diffs.push({ line: i, type: 'modify', content: `${compareLine} → ${currentLine}` })
      }
    }
  }

  differences.value = diffs
}

const restoreVersion = (version) => {
  restoringVersion.value = version
  restoreReason.value = ''
  restoreDialog.value = true
}

const confirmRestore = async () => {
  restoring.value = true
  try {
    // Handover 0396: Use structured api.templates.restore() method
    await api.templates.restore(
      props.template.id,
      restoringVersion.value.id,
      restoreReason.value || null
    )

    emit('restore', restoringVersion.value)
    restoreDialog.value = false
    diffDialog.value = false

    // Reload history
    await loadVersionHistory()
  } catch (error) {
    console.error('Failed to restore version:', error)
  } finally {
    restoring.value = false
  }
}

const cancelRestore = () => {
  restoreDialog.value = false
  restoringVersion.value = null
  restoreReason.value = ''
}

const getVersionColor = (version, index) => {
  if (index === 0) return 'success'
  if (version.archived) return 'warning'
  return 'grey'
}

const getVersionIcon = (version, index) => {
  if (index === 0) return 'mdi-check-circle'
  if (version.archived) return 'mdi-archive'
  return 'mdi-history'
}

const getVersionNumber = (version) => {
  const index = versions.value.findIndex((v) => v.id === version?.id)
  return index >= 0 ? versions.value.length - index : 0
}

const getChangeSummary = (version, index) => {
  const changes = []

  if (index > 0) {
    const prevVersion = versions.value[index - 1]

    // Compare template lengths
    const currentLength = version.template?.length || 0
    const prevLength = prevVersion.template?.length || 0

    if (currentLength > prevLength) {
      changes.push(`+${currentLength - prevLength} chars`)
    } else if (currentLength < prevLength) {
      changes.push(`-${prevLength - currentLength} chars`)
    }

    // Compare variables
    const currentVars = version.variables || []
    const prevVars = prevVersion.variables || []

    const addedVars = currentVars.filter((v) => !prevVars.includes(v))
    const removedVars = prevVars.filter((v) => !currentVars.includes(v))

    if (addedVars.length > 0) {
      changes.push(`+${addedVars.length} vars`)
    }
    if (removedVars.length > 0) {
      changes.push(`-${removedVars.length} vars`)
    }
  } else {
    changes.push('Initial version')
  }

  return changes
}

const getDiffClass = (type) => {
  return {
    'diff-add': type === 'add',
    'diff-remove': type === 'remove',
    'diff-modify': type === 'modify',
  }
}

const formatDate = (date) => {
  if (!date) return 'N/A'

  const d = new Date(date)
  const now = new Date()
  const diffHours = (now - d) / (1000 * 60 * 60)

  if (diffHours < 24) {
    return formatDistanceToNow(d, { addSuffix: true })
  }

  return format(d, 'MMM dd, yyyy HH:mm')
}

// Lifecycle
onMounted(() => {
  loadVersionHistory()
})
</script>

<style scoped lang="scss">
.template-archive {
  background: var(--v-theme-surface-variant);

  .version-timeline {
    max-height: 600px;
    overflow-y: auto;
    padding: 16px 0;

    &::-webkit-scrollbar {
      width: 8px;
    }

    &::-webkit-scrollbar-track {
      background: var(--v-theme-surface);
      border-radius: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: var(--v-theme-on-surface-variant);
      border-radius: 4px;

      &:hover {
        background: var(--v-theme-primary);
      }
    }
  }

  .version-card {
    transition: all 0.2s ease;

    &:hover {
      transform: translateX(4px);
    }
  }

  .version-metadata {
    color: var(--v-theme-on-surface);

    strong {
      color: var(--v-theme-info);
    }
  }

  .template-content {
    font-family: 'Roboto Mono', monospace;
    font-size: 0.75rem;
    background: var(--v-theme-background);
    padding: 12px;
    border-radius: 4px;
    color: var(--v-theme-on-surface);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 300px;
    overflow-y: auto;
  }

  .diff-panel {
    background: var(--v-theme-surface);
    height: 400px;
    overflow: auto;
  }

  .diff-content {
    font-family: 'Roboto Mono', monospace;
    font-size: 0.75rem;
    padding: 12px;
    color: var(--v-theme-on-surface);
    white-space: pre-wrap;
    word-break: break-word;
    margin: 0;
  }

  .diff-summary {
    font-family: 'Roboto Mono', monospace;
    font-size: 0.875rem;
    background: var(--v-theme-background);
    padding: 12px;
    border-radius: 4px;
    max-height: 300px;
    overflow-y: auto;

    .diff-line {
      margin: 2px 0;
    }

    .diff-add {
      color: var(--v-theme-success);
      background: rgba(var(--v-theme-success), 0.1);
      padding: 2px 4px;
      border-radius: 2px;
    }

    .diff-remove {
      color: var(--v-theme-error);
      background: rgba(var(--v-theme-error), 0.1);
      padding: 2px 4px;
      border-radius: 2px;
    }

    .diff-modify {
      color: var(--v-theme-warning);
      background: rgba(var(--v-theme-warning), 0.1);
      padding: 2px 4px;
      border-radius: 2px;
    }
  }

  :deep(.v-timeline-item__body) {
    padding-bottom: 16px;
  }

  :deep(.v-timeline-item__opposite) {
    flex: 0 0 auto;
    min-width: 120px;
  }
}
</style>
