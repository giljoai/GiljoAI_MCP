<template>
  <v-card class="git-commit-history" elevation="2">
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2" color="primary">
        <img src="/icons/document.svg" width="24" height="24" alt="History" />
      </v-icon>
      <span>Commit History</span>
      <v-spacer />
      <v-btn
        color="primary"
        prepend-icon="mdi-refresh"
        variant="text"
        size="small"
        :loading="loading"
        @click="loadCommitHistory"
      >
        Refresh
      </v-btn>
    </v-card-title>

    <v-card-text>
      <!-- Filters -->
      <v-row class="mb-4">
        <v-col cols="12" md="4">
          <v-select
            v-model="selectedBranch"
            :items="branches"
            label="Branch"
            prepend-icon="mdi-source-branch"
            density="compact"
            hide-details
            @update:model-value="loadCommitHistory"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-select
            v-model="commitLimit"
            :items="limitOptions"
            label="Show commits"
            density="compact"
            hide-details
            @update:model-value="loadCommitHistory"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-select
            v-model="filterType"
            :items="typeOptions"
            label="Filter by type"
            clearable
            density="compact"
            hide-details
            @update:model-value="applyFilters"
          />
        </v-col>
      </v-row>

      <!-- Empty State -->
      <v-alert
        v-if="!loading && (!commits || commits.length === 0)"
        type="info"
        variant="tonal"
        class="mb-4"
      >
        <v-alert-title>No Commits Found</v-alert-title>
        <div>No commit history available. Make some commits to see them here.</div>
      </v-alert>

      <!-- Loading State -->
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate color="primary" />
        <div class="mt-2">Loading commit history...</div>
      </div>

      <!-- Commit List -->
      <v-timeline
        v-else-if="filteredCommits && filteredCommits.length > 0"
        side="end"
        density="compact"
      >
        <v-timeline-item
          v-for="commit in filteredCommits"
          :key="commit.hash"
          :dot-color="getCommitTypeColor(commit.triggered_by)"
          size="small"
        >
          <template #icon>
            <v-icon :color="getCommitTypeColor(commit.triggered_by)" size="small">
              {{ getCommitTypeIcon(commit.triggered_by) }}
            </v-icon>
          </template>

          <v-card variant="outlined" class="mb-2">
            <v-card-text class="py-3">
              <!-- Commit Header -->
              <div class="d-flex align-start mb-2">
                <div class="flex-grow-1">
                  <div class="text-body-2 font-weight-medium mb-1">
                    {{ commit.message.split('\n')[0] }}
                  </div>
                  <div class="text-caption text-medium-emphasis">
                    by {{ commit.author_name }}
                    <span class="mx-1">•</span>
                    {{ formatDate(commit.date) }}
                  </div>
                </div>
                <div class="d-flex align-center gap-1">
                  <v-chip
                    :color="getCommitTypeColor(commit.triggered_by)"
                    size="x-small"
                    variant="tonal"
                  >
                    {{ commit.triggered_by || 'manual' }}
                  </v-chip>
                  <v-chip
                    v-if="commit.push_status"
                    :color="getPushStatusColor(commit.push_status)"
                    size="x-small"
                    variant="tonal"
                  >
                    {{ commit.push_status }}
                  </v-chip>
                </div>
              </div>

              <!-- Commit Hash -->
              <div class="d-flex align-center mb-2">
                <v-code class="text-caption mr-2">{{ commit.hash.substring(0, 8) }}</v-code>
                <v-btn
                  icon="mdi-content-copy"
                  size="x-small"
                  variant="text"
                  @click="copyToClipboard(commit.hash)"
                />
                <v-spacer />
                <v-btn
                  icon="mdi-eye"
                  size="x-small"
                  variant="text"
                  @click="viewCommitDetails(commit)"
                />
              </div>

              <!-- File Changes -->
              <div v-if="commit.files_changed && commit.files_changed.length > 0" class="mb-2">
                <div class="text-caption text-medium-emphasis mb-1">
                  {{ commit.files_changed.length }} file(s) changed
                  <span v-if="commit.insertions || commit.deletions">
                    <span class="text-success">+{{ commit.insertions || 0 }}</span>
                    <span class="text-error">-{{ commit.deletions || 0 }}</span>
                  </span>
                </div>
                <div class="d-flex flex-wrap gap-1">
                  <v-chip
                    v-for="file in commit.files_changed.slice(0, 3)"
                    :key="file"
                    size="x-small"
                    variant="outlined"
                    class="text-caption"
                  >
                    {{ getFileName(file) }}
                  </v-chip>
                  <v-chip
                    v-if="commit.files_changed.length > 3"
                    size="x-small"
                    variant="text"
                    class="text-caption"
                  >
                    +{{ commit.files_changed.length - 3 }} more
                  </v-chip>
                </div>
              </div>

              <!-- Project Link -->
              <div v-if="commit.project_id" class="text-caption">
                <v-icon size="x-small" class="mr-1">mdi-folder</v-icon>
                <router-link
                  :to="{ name: 'ProjectDetail', params: { id: commit.project_id } }"
                  class="text-decoration-none"
                >
                  View Project
                </router-link>
              </div>
            </v-card-text>
          </v-card>
        </v-timeline-item>
      </v-timeline>

      <!-- Load More -->
      <div v-if="hasMore" class="text-center mt-4">
        <v-btn color="primary" variant="outlined" :loading="loadingMore" @click="loadMoreCommits">
          Load More Commits
        </v-btn>
      </div>
    </v-card-text>

    <!-- Commit Details Dialog -->
    <v-dialog v-model="showDetailsDialog" max-width="800">
      <v-card v-if="selectedCommit">
        <v-card-title class="d-flex align-center">
          <span>Commit Details</span>
          <v-spacer />
          <v-btn
            icon="mdi-close"
            variant="text"
            @click="showDetailsDialog = false"
            aria-label="Close"
          />
        </v-card-title>

        <v-card-text>
          <v-row>
            <v-col cols="12">
              <h3 class="text-h6 mb-2">{{ selectedCommit.message.split('\n')[0] }}</h3>
              <pre
                v-if="selectedCommit.message.includes('\n')"
                class="text-body-2 whitespace-pre-wrap"
                >{{ selectedCommit.message.split('\n').slice(1).join('\n').trim() }}</pre
              >
            </v-col>

            <v-col cols="12" md="6">
              <v-list density="compact">
                <v-list-item>
                  <v-list-item-title>Commit Hash</v-list-item-title>
                  <v-list-item-subtitle>
                    <v-code>{{ selectedCommit.hash }}</v-code>
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Author</v-list-item-title>
                  <v-list-item-subtitle
                    >{{ selectedCommit.author_name }} &lt;{{
                      selectedCommit.author_email
                    }}&gt;</v-list-item-subtitle
                  >
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Date</v-list-item-title>
                  <v-list-item-subtitle>{{ formatDate(selectedCommit.date) }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>

            <v-col cols="12" md="6">
              <v-list density="compact">
                <v-list-item>
                  <v-list-item-title>Triggered By</v-list-item-title>
                  <v-list-item-subtitle>
                    <v-chip
                      :color="getCommitTypeColor(selectedCommit.triggered_by)"
                      size="small"
                      variant="tonal"
                    >
                      {{ selectedCommit.triggered_by || 'manual' }}
                    </v-chip>
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Push Status</v-list-item-title>
                  <v-list-item-subtitle>
                    <v-chip
                      :color="getPushStatusColor(selectedCommit.push_status)"
                      size="small"
                      variant="tonal"
                    >
                      {{ selectedCommit.push_status || 'unknown' }}
                    </v-chip>
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Changes</v-list-item-title>
                  <v-list-item-subtitle>
                    <span class="text-success">+{{ selectedCommit.insertions || 0 }}</span>
                    <span class="text-error">-{{ selectedCommit.deletions || 0 }}</span>
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>

            <v-col
              v-if="selectedCommit.files_changed && selectedCommit.files_changed.length > 0"
              cols="12"
            >
              <h4 class="text-subtitle-1 mb-2">Changed Files</h4>
              <v-chip-group>
                <v-chip
                  v-for="file in selectedCommit.files_changed"
                  :key="file"
                  size="small"
                  variant="outlined"
                >
                  {{ file }}
                </v-chip>
              </v-chip-group>
            </v-col>
          </v-row>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" @click="showDetailsDialog = false"> Close </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from '@/composables/useToast'
import { api } from '@/services/api'

export default {
  name: 'GitCommitHistory',
  props: {
    productId: {
      type: String,
      required: true,
    },
    repoPath: {
      type: String,
      default: '/app',
    },
  },
  setup(props) {
    const { showToast } = useToast()

    // Reactive data
    const loading = ref(false)
    const loadingMore = ref(false)
    const commits = ref([])
    const selectedBranch = ref('main')
    const commitLimit = ref(20)
    const filterType = ref(null)
    const showDetailsDialog = ref(false)
    const selectedCommit = ref(null)
    const hasMore = ref(false)

    // Static data
    const branches = ref(['main', 'master', 'develop'])
    const limitOptions = [
      { title: '10 commits', value: 10 },
      { title: '20 commits', value: 20 },
      { title: '50 commits', value: 50 },
      { title: '100 commits', value: 100 },
    ]
    const typeOptions = [
      { title: 'Auto commits', value: 'auto' },
      { title: 'Project completions', value: 'project_completion' },
      { title: 'Manual commits', value: 'manual' },
    ]

    // Computed
    const filteredCommits = computed(() => {
      if (!commits.value || !filterType.value) return commits.value
      return commits.value.filter((commit) => commit.triggered_by === filterType.value)
    })

    // Methods
    const loadCommitHistory = async () => {
      loading.value = true
      try {
        const response = await api.get(`/git/history/${props.productId}`, {
          params: {
            repo_path: props.repoPath,
            limit: commitLimit.value,
            branch: selectedBranch.value,
          },
        })

        if (response.data.success) {
          commits.value = response.data.commits || []
          hasMore.value = response.data.commits?.length === commitLimit.value
        } else {
          throw new Error(response.data.error || 'Failed to load commit history')
        }
      } catch (error) {
        console.error('Failed to load commit history:', error)
        showToast(`Failed to load commit history: ${error.message}`, 'error')
        commits.value = []
      } finally {
        loading.value = false
      }
    }

    const loadMoreCommits = async () => {
      loadingMore.value = true
      try {
        const response = await api.get(`/git/history/${props.productId}`, {
          params: {
            repo_path: props.repoPath,
            limit: commitLimit.value,
            branch: selectedBranch.value,
            offset: commits.value.length,
          },
        })

        if (response.data.success) {
          const newCommits = response.data.commits || []
          commits.value.push(...newCommits)
          hasMore.value = newCommits.length === commitLimit.value
        }
      } catch (error) {
        console.error('Failed to load more commits:', error)
        showToast('Failed to load more commits', 'error')
      } finally {
        loadingMore.value = false
      }
    }

    const applyFilters = () => {
      // Filters are applied via computed property
    }

    const viewCommitDetails = (commit) => {
      selectedCommit.value = commit
      showDetailsDialog.value = true
    }

    const copyToClipboard = async (text) => {
      try {
        await navigator.clipboard.writeText(text)
        showToast('Copied to clipboard', 'success')
      } catch (error) {
        console.error('Failed to copy to clipboard:', error)
        showToast('Failed to copy to clipboard', 'error')
      }
    }

    const getCommitTypeColor = (type) => {
      switch (type) {
        case 'auto':
          return 'blue'
        case 'project_completion':
          return 'green'
        case 'manual':
          return 'purple'
        default:
          return 'grey'
      }
    }

    const getCommitTypeIcon = (type) => {
      switch (type) {
        case 'auto':
          return 'mdi-robot'
        case 'project_completion':
          return 'mdi-check-circle'
        case 'manual':
          return 'mdi-account'
        default:
          return 'mdi-source-commit'
      }
    }

    const getPushStatusColor = (status) => {
      switch (status) {
        case 'pushed':
          return 'success'
        case 'pending':
          return 'warning'
        case 'failed':
          return 'error'
        default:
          return 'grey'
      }
    }

    const getFileName = (filePath) => {
      return filePath.split('/').pop() || filePath
    }

    const formatDate = (dateString) => {
      const date = new Date(dateString)
      const now = new Date()
      const diffMs = now - date
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

      if (diffDays === 0) {
        return date.toLocaleTimeString()
      } else if (diffDays === 1) {
        return 'Yesterday'
      } else if (diffDays < 7) {
        return `${diffDays} days ago`
      } else {
        return date.toLocaleDateString()
      }
    }

    // Watchers
    watch(() => props.productId, loadCommitHistory, { immediate: true })

    // Lifecycle
    onMounted(() => {
      loadCommitHistory()
    })

    return {
      // Reactive data
      loading,
      loadingMore,
      commits,
      selectedBranch,
      commitLimit,
      filterType,
      showDetailsDialog,
      selectedCommit,
      hasMore,

      // Static data
      branches,
      limitOptions,
      typeOptions,

      // Computed
      filteredCommits,

      // Methods
      loadCommitHistory,
      loadMoreCommits,
      applyFilters,
      viewCommitDetails,
      copyToClipboard,
      getCommitTypeColor,
      getCommitTypeIcon,
      getPushStatusColor,
      getFileName,
      formatDate,
    }
  },
}
</script>

<style scoped>
.git-commit-history {
  max-width: 100%;
}

.v-timeline {
  padding-left: 0;
}

.v-code {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Roboto Mono', monospace;
}

.whitespace-pre-wrap {
  white-space: pre-wrap;
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  padding: 12px;
  border-radius: 4px;
  font-family: 'Roboto Mono', monospace;
}

.d-flex.gap-1 > * + * {
  margin-left: 4px;
}

.flex-wrap {
  flex-wrap: wrap;
  gap: 4px;
}
</style>
