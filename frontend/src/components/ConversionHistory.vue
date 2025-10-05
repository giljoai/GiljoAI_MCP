<template>
  <v-card class="conversion-history">
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2" color="primary">mdi-history</v-icon>
      Conversion History
      <v-spacer />
      <v-btn
        icon="mdi-refresh"
        size="small"
        variant="text"
        @click="refreshHistory"
        :loading="loading"
        aria-label="Refresh history"
      />
    </v-card-title>

    <v-divider />

    <!-- History Filters -->
    <v-card-text class="pb-0">
      <v-row>
        <v-col cols="12" md="4">
          <v-select
            v-model="timeFilter"
            :items="timeFilterOptions"
            label="Time Period"
            variant="outlined"
            density="compact"
            hide-details
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-select
            v-model="statusFilter"
            :items="statusFilterOptions"
            label="Status"
            variant="outlined"
            density="compact"
            hide-details
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-text-field
            v-model="searchFilter"
            label="Search conversions"
            variant="outlined"
            density="compact"
            prepend-inner-icon="mdi-magnify"
            clearable
            hide-details
          />
        </v-col>
      </v-row>
    </v-card-text>

    <!-- History Timeline -->
    <v-card-text>
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate color="primary" />
        <div class="mt-2">Loading conversion history...</div>
      </div>

      <div v-else-if="filteredHistory.length === 0" class="text-center py-8">
        <v-icon size="large" color="grey" class="mb-2">mdi-timeline-clock-outline</v-icon>
        <div class="text-h6">No Conversion History</div>
        <div class="text-body-2 text-medium-emphasis">
          {{
            hasFilters
              ? 'No conversions match your filters'
              : 'Conversion history will be available when real API is implemented'
          }}
        </div>
      </div>

      <v-timeline v-else side="end" density="compact">
        <v-timeline-item
          v-for="conversion in filteredHistory"
          :key="conversion.id"
          :dot-color="getStatusColor(conversion.status)"
          size="small"
        >
          <template v-slot:icon>
            <v-icon size="small" color="white">
              {{ getStatusIcon(conversion.status) }}
            </v-icon>
          </template>

          <template v-slot:opposite>
            <div class="text-caption text-medium-emphasis">
              {{ formatTimestamp(conversion.created_at) }}
            </div>
          </template>

          <v-card variant="outlined" class="conversion-card">
            <v-card-text class="pb-2">
              <!-- Conversion Header -->
              <div class="d-flex align-center mb-2">
                <v-icon class="mr-2" color="primary">mdi-arrow-right-bold-circle</v-icon>
                <div class="flex-grow-1">
                  <div class="font-weight-medium">
                    {{ conversion.task_count }} task{{ conversion.task_count > 1 ? 's' : '' }} →
                    {{ conversion.project_count }} project{{
                      conversion.project_count > 1 ? 's' : ''
                    }}
                  </div>
                  <div class="text-caption text-medium-emphasis">
                    Strategy: {{ conversion.strategy || 'single' }}
                  </div>
                </div>
                <v-chip :color="getStatusColor(conversion.status)" size="small" variant="flat">
                  {{ conversion.status }}
                </v-chip>
              </div>

              <!-- Task Details -->
              <div class="mb-3">
                <div class="text-subtitle-2 mb-1">Converted Tasks:</div>
                <v-chip-group>
                  <v-chip
                    v-for="task in conversion.tasks"
                    :key="task.id"
                    size="small"
                    variant="outlined"
                    :color="getPriorityColor(task.priority)"
                  >
                    {{ task.title }}
                  </v-chip>
                </v-chip-group>
              </div>

              <!-- Created Projects -->
              <div class="mb-3">
                <div class="text-subtitle-2 mb-1">Created Projects:</div>
                <div v-for="project in conversion.projects" :key="project.id" class="mb-1">
                  <v-chip
                    size="small"
                    color="primary"
                    variant="outlined"
                    prepend-icon="mdi-folder"
                    @click="openProject(project.id)"
                    class="mr-2 mb-1"
                  >
                    {{ project.name }}
                  </v-chip>
                </div>
              </div>

              <!-- Conversion Options -->
              <div v-if="conversion.options" class="mb-3">
                <v-expansion-panels variant="accordion" density="compact">
                  <v-expansion-panel>
                    <v-expansion-panel-title class="text-caption">
                      <v-icon class="mr-2" size="small">mdi-cog</v-icon>
                      Conversion Options
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <v-row density="compact">
                        <v-col cols="6">
                          <div class="d-flex align-center mb-1">
                            <v-icon
                              :color="conversion.options.preserveTaskLinks ? 'success' : 'grey'"
                              size="small"
                              class="mr-2"
                            >
                              {{ conversion.options.preserveTaskLinks ? 'mdi-check' : 'mdi-close' }}
                            </v-icon>
                            <span class="text-caption">Preserve task links</span>
                          </div>
                          <div class="d-flex align-center mb-1">
                            <v-icon
                              :color="conversion.options.markTasksConverted ? 'success' : 'grey'"
                              size="small"
                              class="mr-2"
                            >
                              {{
                                conversion.options.markTasksConverted ? 'mdi-check' : 'mdi-close'
                              }}
                            </v-icon>
                            <span class="text-caption">Mark tasks converted</span>
                          </div>
                        </v-col>
                        <v-col cols="6">
                          <div class="d-flex align-center mb-1">
                            <v-icon
                              :color="conversion.options.assignToCurrentAgent ? 'success' : 'grey'"
                              size="small"
                              class="mr-2"
                            >
                              {{
                                conversion.options.assignToCurrentAgent ? 'mdi-check' : 'mdi-close'
                              }}
                            </v-icon>
                            <span class="text-caption">Assign to agent</span>
                          </div>
                          <div class="d-flex align-center mb-1">
                            <v-icon
                              :color="conversion.options.inheritTaskPriority ? 'success' : 'grey'"
                              size="small"
                              class="mr-2"
                            >
                              {{
                                conversion.options.inheritTaskPriority ? 'mdi-check' : 'mdi-close'
                              }}
                            </v-icon>
                            <span class="text-caption">Inherit priority</span>
                          </div>
                        </v-col>
                      </v-row>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </div>

              <!-- Error Details -->
              <div v-if="conversion.status === 'failed' && conversion.error" class="mb-3">
                <v-alert type="error" variant="outlined" density="compact" class="text-caption">
                  <strong>Error:</strong> {{ conversion.error }}
                </v-alert>
              </div>

              <!-- Actions -->
              <div class="d-flex justify-end gap-2">
                <v-btn
                  v-if="conversion.status === 'completed' && canRollback(conversion)"
                  size="small"
                  variant="outlined"
                  color="warning"
                  prepend-icon="mdi-undo"
                  @click="rollbackConversion(conversion)"
                  :loading="rollbackLoading === conversion.id"
                >
                  Rollback
                </v-btn>
                <v-btn
                  size="small"
                  variant="text"
                  prepend-icon="mdi-information"
                  @click="showConversionDetails(conversion)"
                >
                  Details
                </v-btn>
              </div>
            </v-card-text>
          </v-card>
        </v-timeline-item>
      </v-timeline>
    </v-card-text>

    <!-- Conversion Details Dialog -->
    <v-dialog v-model="showDetailsDialog" max-width="600">
      <v-card v-if="selectedConversion">
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-information</v-icon>
          <span>Conversion Details</span>
          <v-spacer />
          <v-btn
            icon="mdi-close"
            variant="text"
            @click="showDetailsDialog = false"
            aria-label="Close"
          />
        </v-card-title>
        <v-divider />
        <v-card-text>
          <v-row>
            <v-col cols="6">
              <div class="text-subtitle-2 mb-1">Conversion ID</div>
              <div class="text-body-2 mb-3">{{ selectedConversion.id }}</div>

              <div class="text-subtitle-2 mb-1">Created At</div>
              <div class="text-body-2 mb-3">
                {{ formatFullTimestamp(selectedConversion.created_at) }}
              </div>

              <div class="text-subtitle-2 mb-1">Status</div>
              <v-chip
                :color="getStatusColor(selectedConversion.status)"
                size="small"
                variant="flat"
                class="mb-3"
              >
                {{ selectedConversion.status }}
              </v-chip>
            </v-col>
            <v-col cols="6">
              <div class="text-subtitle-2 mb-1">Strategy</div>
              <div class="text-body-2 mb-3">{{ selectedConversion.strategy || 'single' }}</div>

              <div class="text-subtitle-2 mb-1">Task Count</div>
              <div class="text-body-2 mb-3">{{ selectedConversion.task_count }}</div>

              <div class="text-subtitle-2 mb-1">Project Count</div>
              <div class="text-body-2 mb-3">{{ selectedConversion.project_count }}</div>
            </v-col>
          </v-row>

          <div v-if="selectedConversion.metadata" class="mt-4">
            <div class="text-subtitle-2 mb-2">Metadata</div>
            <pre class="metadata-display">{{
              JSON.stringify(selectedConversion.metadata, null, 2)
            }}</pre>
          </div>
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDetailsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { format, formatDistanceToNow } from 'date-fns'

// Props
const props = defineProps({
  productId: {
    type: String,
    default: null,
  },
})

// Emits
const emit = defineEmits(['project-selected'])

// State
const loading = ref(false)
const conversions = ref([])
const timeFilter = ref('all')
const statusFilter = ref('all')
const searchFilter = ref('')
const rollbackLoading = ref(null)
const showDetailsDialog = ref(false)
const selectedConversion = ref(null)

// Filter options
const timeFilterOptions = [
  { title: 'All Time', value: 'all' },
  { title: 'Last 24 Hours', value: '24h' },
  { title: 'Last Week', value: '7d' },
  { title: 'Last Month', value: '30d' },
]

const statusFilterOptions = [
  { title: 'All Status', value: 'all' },
  { title: 'Completed', value: 'completed' },
  { title: 'Failed', value: 'failed' },
  { title: 'In Progress', value: 'in_progress' },
]

// Computed
const hasFilters = computed(() => {
  return timeFilter.value !== 'all' || statusFilter.value !== 'all' || searchFilter.value
})

const filteredHistory = computed(() => {
  let filtered = [...conversions.value]

  // Time filter
  if (timeFilter.value !== 'all') {
    const now = new Date()
    const cutoff = new Date()

    switch (timeFilter.value) {
      case '24h':
        cutoff.setHours(now.getHours() - 24)
        break
      case '7d':
        cutoff.setDate(now.getDate() - 7)
        break
      case '30d':
        cutoff.setDate(now.getDate() - 30)
        break
    }

    filtered = filtered.filter((c) => new Date(c.created_at) >= cutoff)
  }

  // Status filter
  if (statusFilter.value !== 'all') {
    filtered = filtered.filter((c) => c.status === statusFilter.value)
  }

  // Search filter
  if (searchFilter.value) {
    const search = searchFilter.value.toLowerCase()
    filtered = filtered.filter(
      (c) =>
        c.tasks?.some((t) => t.title.toLowerCase().includes(search)) ||
        c.projects?.some((p) => p.name.toLowerCase().includes(search)),
    )
  }

  return filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
})

// Methods
function getStatusColor(status) {
  const colors = {
    completed: 'success',
    failed: 'error',
    in_progress: 'warning',
    pending: 'info',
  }
  return colors[status] || 'grey'
}

function getStatusIcon(status) {
  const icons = {
    completed: 'mdi-check',
    failed: 'mdi-alert',
    in_progress: 'mdi-clock',
    pending: 'mdi-dots-horizontal',
  }
  return icons[status] || 'mdi-help'
}

function getPriorityColor(priority) {
  const colors = {
    low: 'grey',
    medium: 'info',
    high: 'warning',
    critical: 'error',
  }
  return colors[priority] || 'grey'
}

function formatTimestamp(timestamp) {
  return formatDistanceToNow(new Date(timestamp), { addSuffix: true })
}

function formatFullTimestamp(timestamp) {
  return format(new Date(timestamp), 'PPpp')
}

function canRollback(conversion) {
  // Can rollback if completed within last 24 hours and no dependencies
  const dayAgo = new Date()
  dayAgo.setHours(dayAgo.getHours() - 24)

  return (
    conversion.status === 'completed' &&
    new Date(conversion.created_at) > dayAgo &&
    !conversion.has_dependencies
  )
}

async function refreshHistory() {
  loading.value = true
  try {
    // TODO: Fetch from API when conversion history endpoint is implemented
    conversions.value = []
  } catch (error) {
    console.error('Failed to fetch conversion history:', error)
  } finally {
    loading.value = false
  }
}

async function rollbackConversion(conversion) {
  if (
    !confirm(`Are you sure you want to rollback the conversion of ${conversion.task_count} tasks?`)
  ) {
    return
  }

  rollbackLoading.value = conversion.id
  try {
    // Mock rollback - would call API
    console.log('Rolling back conversion:', conversion.id)

    // Update status
    conversion.status = 'rolled_back'

    // Emit event to refresh tasks
    emit('conversion-rolled-back', conversion)
  } catch (error) {
    console.error('Failed to rollback conversion:', error)
  } finally {
    rollbackLoading.value = null
  }
}

function openProject(projectId) {
  emit('project-selected', projectId)
}

function showConversionDetails(conversion) {
  selectedConversion.value = conversion
  showDetailsDialog.value = true
}

// Lifecycle
onMounted(() => {
  refreshHistory()
})
</script>

<style scoped>
.conversion-history {
  max-height: 600px;
  overflow-y: auto;
}

.conversion-card {
  transition: transform 0.2s ease;
}

.conversion-card:hover {
  transform: translateY(-1px);
}

.metadata-display {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
}
</style>
