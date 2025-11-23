<template>
  <v-card class="artifact-timeline" elevation="2">
    <!-- Header -->
    <v-card-title class="d-flex align-center justify-space-between">
      <div class="d-flex align-center">
        <v-icon icon="mdi-file-multiple" class="mr-2" color="primary" />
        <span>Artifact Timeline</span>
        <v-chip size="small" variant="flat" color="primary" class="ml-3">
          {{ artifacts.length }}
        </v-chip>
      </div>
      <div class="header-controls">
        <v-btn
          icon
          size="small"
          variant="text"
          @click="sortOrder = sortOrder === 'asc' ? 'desc' : 'asc'"
          :title="`Sort ${sortOrder === 'asc' ? 'newest first' : 'oldest first'}`"
        >
          <v-icon :icon="sortOrder === 'asc' ? 'mdi-sort-descending' : 'mdi-sort-ascending'" />
        </v-btn>
        <v-btn
          icon
          size="small"
          variant="text"
          @click="viewMode = viewMode === 'list' ? 'grid' : 'list'"
          :title="`Switch to ${viewMode === 'list' ? 'grid' : 'list'} view`"
        >
          <v-icon :icon="viewMode === 'list' ? 'mdi-view-grid' : 'mdi-view-list'" />
        </v-btn>
      </div>
    </v-card-title>

    <v-divider />

    <!-- Filter Bar -->
    <div class="artifact-filters">
      <v-text-field
        v-model="searchQuery"
        placeholder="Search artifacts..."
        prepend-inner-icon="mdi-magnify"
        hide-details
        size="small"
        variant="outlined"
        density="compact"
        class="search-field"
      />

      <v-menu>
        <template v-slot:activator="{ props }">
          <v-btn
            size="small"
            variant="outlined"
            v-bind="props"
            :color="hasActiveFilters ? 'primary' : ''"
          >
            <v-icon icon="mdi-filter" size="small" />
          </v-btn>
        </template>
        <v-list density="compact">
          <v-list-item
            v-for="type in artifactTypes"
            :key="type"
            @click="toggleTypeFilter(type)"
            :active="typeFilters.has(type)"
          >
            <template v-slot:prepend>
              <v-checkbox :model-value="typeFilters.has(type)" hide-details size="small" />
            </template>
            <v-list-item-title>{{ formatType(type) }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </div>

    <!-- Empty State -->
    <v-card-text v-if="filteredArtifacts.length === 0" class="empty-state">
      <v-icon icon="mdi-folder-open-outline" size="64" color="grey" />
      <p>{{ searchQuery ? 'No artifacts match your search' : 'No artifacts yet' }}</p>
    </v-card-text>

    <!-- List View -->
    <v-card-text v-else-if="viewMode === 'list'" class="artifacts-list">
      <transition-group name="list" tag="div">
        <div
          v-for="artifact in filteredArtifacts"
          :key="artifact.id"
          class="artifact-item"
          :class="`type-${artifact.type}`"
        >
          <!-- Icon and Name -->
          <div class="artifact-header">
            <v-icon :icon="getArtifactIcon(artifact.type)" size="small" class="artifact-icon" />

            <div class="artifact-info">
              <div class="artifact-name">{{ artifact.name }}</div>
              <div class="artifact-meta">
                <span class="agent-name">{{ artifact.agentName }}</span>
                <span class="artifact-size" v-if="artifact.size">{{
                  formatFileSize(artifact.size)
                }}</span>
                <span class="artifact-time">{{ formatTime(artifact.createdAt) }}</span>
              </div>
            </div>

            <v-chip
              size="x-small"
              :color="getTypeColor(artifact.type)"
              variant="flat"
              class="type-chip"
            >
              {{ formatType(artifact.type) }}
            </v-chip>
          </div>

          <!-- Description -->
          <div v-if="artifact.description" class="artifact-description">
            {{ artifact.description }}
          </div>

          <!-- Path -->
          <div v-if="artifact.path" class="artifact-path mono">
            {{ artifact.path }}
          </div>

          <!-- Tags -->
          <div v-if="artifact.tags && artifact.tags.length > 0" class="artifact-tags">
            <v-chip
              v-for="tag in artifact.tags"
              :key="tag"
              size="x-small"
              variant="outlined"
              class="tag-chip"
            >
              {{ tag }}
            </v-chip>
          </div>

          <!-- Actions -->
          <div class="artifact-actions">
            <v-btn
              v-if="artifact.type === 'code' || artifact.type === 'file'"
              size="x-small"
              variant="text"
              @click="viewArtifact(artifact)"
            >
              <v-icon icon="mdi-eye" size="x-small" class="mr-1" />
              View
            </v-btn>

            <v-btn size="x-small" variant="text" @click="downloadArtifact(artifact)">
              <v-icon icon="mdi-download" size="x-small" class="mr-1" />
              Download
            </v-btn>

            <v-btn size="x-small" variant="text" @click="copyPath(artifact.path)">
              <v-icon icon="mdi-content-copy" size="x-small" class="mr-1" />
              Copy Path
            </v-btn>

            <v-menu size="small">
              <template v-slot:activator="{ props }">
                <v-btn size="x-small" variant="text" v-bind="props">
                  <v-icon icon="mdi-dots-vertical" size="x-small" />
                </v-btn>
              </template>
              <v-list density="compact">
                <v-list-item @click="shareArtifact(artifact)">
                  <template v-slot:prepend>
                    <v-icon icon="mdi-share-variant" />
                  </template>
                  <v-list-item-title>Share</v-list-item-title>
                </v-list-item>

                <v-list-item @click="deleteArtifact(artifact.id)">
                  <template v-slot:prepend>
                    <v-icon icon="mdi-trash-can" color="error" />
                  </template>
                  <v-list-item-title class="text-error">Delete</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </div>
        </div>
      </transition-group>
    </v-card-text>

    <!-- Grid View -->
    <v-card-text v-else class="artifacts-grid">
      <transition-group name="list" tag="div" class="grid-container">
        <div
          v-for="artifact in filteredArtifacts"
          :key="artifact.id"
          class="artifact-card"
          :class="`type-${artifact.type}`"
        >
          <div class="card-header">
            <v-icon :icon="getArtifactIcon(artifact.type)" size="large" class="card-icon" />
            <v-chip size="x-small" :color="getTypeColor(artifact.type)" variant="flat">
              {{ formatType(artifact.type) }}
            </v-chip>
          </div>

          <div class="card-content">
            <h4 class="card-title">{{ truncate(artifact.name, 30) }}</h4>
            <p v-if="artifact.description" class="card-description">
              {{ truncate(artifact.description, 50) }}
            </p>
            <div class="card-meta">
              <span class="meta-label">Agent:</span>
              <span class="meta-value">{{ truncate(artifact.agentName, 15) }}</span>
            </div>
            <div class="card-meta">
              <span class="meta-label">Size:</span>
              <span class="meta-value">{{
                artifact.size ? formatFileSize(artifact.size) : 'N/A'
              }}</span>
            </div>
            <div class="card-time">{{ formatTime(artifact.createdAt) }}</div>
          </div>

          <div class="card-actions">
            <v-btn size="x-small" variant="text" @click="viewArtifact(artifact)" color="primary">
              <v-icon icon="mdi-eye" size="x-small" />
            </v-btn>
            <v-btn size="x-small" variant="text" @click="downloadArtifact(artifact)">
              <v-icon icon="mdi-download" size="x-small" />
            </v-btn>
            <v-btn size="x-small" variant="text" @click="deleteArtifact(artifact.id)" color="error">
              <v-icon icon="mdi-trash-can" size="x-small" />
            </v-btn>
          </div>
        </div>
      </transition-group>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAgentFlowStore } from '@/stores/agentFlow'
import { formatDistanceToNow } from 'date-fns'

const flowStore = useAgentFlowStore()

const searchQuery = ref('')
const typeFilters = ref(new Set(['file', 'directory', 'code']))
const sortOrder = ref('desc')
const viewMode = ref('list')

const artifactTypes = ['file', 'directory', 'code']

const artifacts = computed(() => flowStore.artifacts)

const filteredArtifacts = computed(() => {
  let filtered = artifacts.value.slice()

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(
      (a) =>
        (a.name || '').toLowerCase().includes(query) ||
        (a.path || '').toLowerCase().includes(query) ||
        (a.description || '').toLowerCase().includes(query) ||
        (a.agentName || '').toLowerCase().includes(query),
    )
  }

  // Filter by type
  if (typeFilters.value.size > 0) {
    filtered = filtered.filter((a) => typeFilters.value.has(a.type))
  }

  // Sort by creation time
  filtered.sort((a, b) => {
    const timeA = new Date(a.createdAt).getTime()
    const timeB = new Date(b.createdAt).getTime()
    return sortOrder.value === 'desc' ? timeB - timeA : timeA - timeB
  })

  return filtered
})

const hasActiveFilters = computed(
  () => typeFilters.value.size < artifactTypes.length || searchQuery.value.length > 0,
)

function getArtifactIcon(type) {
  const iconMap = {
    file: 'mdi-file',
    directory: 'mdi-folder',
    code: 'mdi-code-tags',
  }
  return iconMap[type] || 'mdi-file'
}

function getTypeColor(type) {
  const colorMap = {
    file: 'primary',
    directory: 'info',
    code: 'success',
  }
  return colorMap[type] || 'grey'
}

function formatType(type) {
  const typeMap = {
    file: 'File',
    directory: 'Directory',
    code: 'Code',
  }
  return typeMap[type] || type
}

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

function formatTime(timestamp) {
  if (!timestamp) return 'Unknown'
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date

  if (diffMs < 60000) {
    return 'Just now'
  }
  return formatDistanceToNow(date, { addSuffix: true })
}

function truncate(str, length) {
  if (!str) return ''
  return str.length > length ? str.substring(0, length) + '...' : str
}

function toggleTypeFilter(type) {
  if (typeFilters.value.has(type)) {
    typeFilters.value.delete(type)
  } else {
    typeFilters.value.add(type)
  }
}

function viewArtifact(artifact) {
  console.log('View artifact:', artifact)
  // Implement artifact viewer
}

function downloadArtifact(artifact) {
  console.log('Download artifact:', artifact)
  // Implement artifact download
}

function copyPath(path) {
  if (path) {
    navigator.clipboard.writeText(path)
  }
}

function shareArtifact(artifact) {
  console.log('Share artifact:', artifact)
  // Implement artifact sharing
}

function deleteArtifact(artifactId) {
  const index = flowStore.artifacts.findIndex((a) => a.id === artifactId)
  if (index !== -1) {
    flowStore.artifacts.splice(index, 1)
  }
}
</script>

<style scoped lang="scss">
.artifact-timeline {
  background: #182739;

  :deep(.v-card-title) {
    padding: 12px 16px;
    background: linear-gradient(135deg, #1e3147 0%, #182739 100%);
    border-bottom: 1px solid #315074;

    .header-controls {
      display: flex;
      gap: 4px;
    }
  }

  .artifact-filters {
    display: flex;
    gap: 8px;
    padding: 12px;
    background: rgba(30, 49, 71, 0.5);
    border-bottom: 1px solid rgba(49, 80, 116, 0.3);

    .search-field {
      flex: 1;
    }
  }

  :deep(.v-card-text) {
    padding: 16px;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 300px;
    color: #8f97b7;

    p {
      margin-top: 12px;
    }
  }

  .artifacts-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 600px;
    overflow-y: auto;

    .artifact-item {
      background: linear-gradient(135deg, rgba(30, 49, 71, 0.8) 0%, rgba(24, 39, 57, 0.8) 100%);
      border: 1px solid rgba(49, 80, 116, 0.4);
      border-left: 4px solid #315074;
      border-radius: 6px;
      padding: 12px;
      transition: all 0.2s ease;

      &:hover {
        background: linear-gradient(135deg, rgba(30, 49, 71, 0.95) 0%, rgba(24, 39, 57, 0.95) 100%);
        border-color: rgba(49, 80, 116, 0.6);
      }

      &.type-code {
        border-left-color: #67bd6d;
      }

      &.type-directory {
        border-left-color: #8b5cf6;
      }

      .artifact-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;

        .artifact-icon {
          color: var(--artifact-color, #315074);
          flex-shrink: 0;
        }

        .artifact-info {
          flex: 1;

          .artifact-name {
            font-size: 13px;
            font-weight: 600;
            color: #e1e1e1;
            margin-bottom: 4px;
          }

          .artifact-meta {
            display: flex;
            gap: 8px;
            font-size: 11px;
            color: #8f97b7;

            .agent-name {
              font-weight: 500;
            }
          }
        }

        .type-chip {
          flex-shrink: 0;
        }
      }

      .artifact-description {
        font-size: 12px;
        color: #8f97b7;
        margin-bottom: 8px;
        line-height: 1.3;
      }

      .artifact-path {
        font-size: 10px;
        color: #8f97b7;
        background: rgba(49, 80, 116, 0.2);
        padding: 6px;
        border-radius: 3px;
        margin-bottom: 8px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .artifact-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 8px;

        .tag-chip {
          font-size: 10px !important;
        }
      }

      .artifact-actions {
        display: flex;
        gap: 4px;
        justify-content: flex-end;
      }
    }
  }

  .artifacts-grid {
    display: flex;
    flex-direction: column;

    .grid-container {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 12px;
    }

    .artifact-card {
      background: linear-gradient(135deg, rgba(30, 49, 71, 0.8) 0%, rgba(24, 39, 57, 0.8) 100%);
      border: 1px solid rgba(49, 80, 116, 0.4);
      border-radius: 8px;
      padding: 12px;
      transition: all 0.2s ease;
      display: flex;
      flex-direction: column;

      &:hover {
        background: linear-gradient(135deg, rgba(30, 49, 71, 0.95) 0%, rgba(24, 39, 57, 0.95) 100%);
        border-color: rgba(49, 80, 116, 0.6);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
      }

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 8px;
        margin-bottom: 12px;

        .card-icon {
          color: #315074;
        }
      }

      .card-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-bottom: 12px;

        .card-title {
          font-size: 13px;
          font-weight: 600;
          color: #e1e1e1;
          margin: 0;
        }

        .card-description {
          font-size: 11px;
          color: #8f97b7;
          margin: 0;
          line-height: 1.3;
        }

        .card-meta {
          display: flex;
          gap: 4px;
          font-size: 11px;

          .meta-label {
            color: #8f97b7;
            font-weight: 500;
          }

          .meta-value {
            color: #e1e1e1;
          }
        }

        .card-time {
          font-size: 10px;
          color: #8f97b7;
          margin-top: auto;
        }
      }

      .card-actions {
        display: flex;
        gap: 4px;
        justify-content: flex-end;
      }
    }
  }

  // Scrollbar styling
  ::-webkit-scrollbar {
    width: 8px;
  }

  ::-webkit-scrollbar-track {
    background: rgba(30, 49, 71, 0.3);
  }

  ::-webkit-scrollbar-thumb {
    background: rgba(49, 80, 116, 0.5);
    border-radius: 4px;

    &:hover {
      background: rgba(49, 80, 116, 0.7);
    }
  }

  > :deep(.v-divider) {
    border-color: rgba(49, 80, 116, 0.3);
  }
}

.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}

.list-enter-from {
  opacity: 0;
  transform: translateX(-8px);
}

.list-leave-to {
  opacity: 0;
  transform: translateX(8px);
}
</style>
