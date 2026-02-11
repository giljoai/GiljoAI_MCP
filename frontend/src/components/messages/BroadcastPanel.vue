<template>
  <v-container fluid>
    <v-row>
      <!-- Broadcast Composer -->
      <v-col cols="12" md="6">
        <v-card variant="outlined">
          <v-card-title class="d-flex align-center">
            <v-icon icon="mdi-bullhorn" size="24" class="mr-2" />
            <span>Send Message</span>
          </v-card-title>

          <v-divider />

          <v-card-text>
            <!-- Project Selector -->
            <v-select
              v-model="selectedProject"
              :items="projectOptions"
              :loading="loadingProjects"
              label="Project"
              variant="outlined"
              density="compact"
              class="mb-4"
              prepend-inner-icon="mdi-folder"
              hint="Select project to send message to"
              persistent-hint
            />

            <!-- Priority Selector -->
            <v-select
              v-model="priority"
              :items="priorityOptions"
              label="Priority"
              variant="outlined"
              density="compact"
              class="mb-4"
              prepend-inner-icon="mdi-flag"
            />

            <!-- Message Composer -->
            <v-tabs v-model="activeTab" class="mb-4">
              <v-tab value="edit">
                <v-icon icon="mdi-pencil" start />
                Edit
              </v-tab>
              <v-tab value="preview">
                <v-icon icon="mdi-eye" start />
                Preview
              </v-tab>
            </v-tabs>

            <v-window v-model="activeTab">
              <v-window-item value="edit">
                <v-textarea
                  v-model="messageContent"
                  label="Message"
                  placeholder="Type your message here... (Markdown supported)"
                  variant="outlined"
                  rows="8"
                  counter
                  :maxlength="2000"
                  :error-messages="contentError"
                  hint="Markdown syntax supported (bold, italic, code, lists)"
                  persistent-hint
                  auto-grow
                />
              </v-window-item>

              <v-window-item value="preview">
                <v-card variant="tonal" class="pa-4" min-height="200">
                  <div v-if="messageContent" v-html="markdownPreview" class="markdown-preview" />
                  <div v-else class="text-center text-medium-emphasis">
                    <v-icon icon="mdi-text-box-outline" size="48" class="mb-2" />
                    <p>No content to preview</p>
                  </div>
                </v-card>
              </v-window-item>
            </v-window>
          </v-card-text>

          <v-divider />

          <v-card-actions class="pa-4">
            <v-btn color="primary" :disabled="!canSend" :loading="sending" @click="sendBroadcast">
              <v-icon icon="mdi-send" start />
              Send Broadcast
            </v-btn>

            <v-spacer />

            <!-- Templates Menu -->
            <v-menu>
              <template v-slot:activator="{ props }">
                <v-btn variant="outlined" v-bind="props">
                  <v-icon icon="mdi-text-box-multiple" start />
                  Templates
                </v-btn>
              </template>
              <v-list>
                <v-list-item
                  v-for="template in templates"
                  :key="template.id"
                  @click="applyTemplate(template)"
                >
                  <v-list-item-title>{{ template.name }}</v-list-item-title>
                  <template v-slot:prepend>
                    <v-icon :icon="getTemplateIcon(template.priority)" />
                  </template>
                </v-list-item>
              </v-list>
            </v-menu>
          </v-card-actions>
        </v-card>
      </v-col>

      <!-- Broadcast History -->
      <v-col cols="12" md="6">
        <v-card variant="outlined">
          <v-card-title class="d-flex align-center justify-space-between">
            <div class="d-flex align-center">
              <v-icon icon="mdi-history" size="24" class="mr-2" />
              <span>Broadcast History</span>
            </div>
            <v-btn
              icon="mdi-refresh"
              size="small"
              variant="text"
              :loading="loadingHistory"
              @click="fetchBroadcastHistory"
            />
          </v-card-title>

          <v-divider />

          <v-card-text>
            <!-- Loading State -->
            <div v-if="loadingHistory && broadcastHistory.length === 0" class="text-center pa-8">
              <v-progress-circular indeterminate color="primary" size="48" />
              <p class="text-body-2 text-medium-emphasis mt-4">Loading history...</p>
            </div>

            <!-- Empty State -->
            <div v-else-if="broadcastHistory.length === 0" class="text-center pa-8">
              <v-icon icon="mdi-broadcast-off" size="64" color="grey" class="mb-4" />
              <p class="text-body-1 text-medium-emphasis">No broadcasts sent yet</p>
              <p class="text-caption text-medium-emphasis">
                Send your first broadcast message to see history here
              </p>
            </div>

            <!-- History List -->
            <v-list v-else class="pa-0">
              <v-list-item v-for="broadcast in broadcastHistory" :key="broadcast.id" class="mb-2">
                <template v-slot:prepend>
                  <v-avatar :color="getStatusColor(broadcast.status)">
                    <v-icon :icon="getStatusIcon(broadcast.status)" />
                  </v-avatar>
                </template>

                <v-list-item-title class="text-wrap">
                  {{ truncateContent(broadcast.content) }}
                </v-list-item-title>

                <v-list-item-subtitle>
                  <div class="d-flex align-center mt-1">
                    <v-chip size="x-small" variant="flat" class="mr-2">
                      {{ broadcast.recipient_count || 0 }} recipients
                    </v-chip>
                    <span class="text-caption">{{ formatTime(broadcast.timestamp) }}</span>
                  </div>
                </v-list-item-subtitle>

                <template v-slot:append>
                  <v-chip size="small" :color="getStatusColor(broadcast.status)" variant="flat">
                    {{ broadcast.status }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'
import type { BroadcastTemplate, MessagePriority } from '@/types/message'

interface BroadcastHistoryItem {
  id: string
  content: string
  recipient_count: number
  status: string
  timestamp: string
}

interface ProjectOption {
  title: string
  value: string
}

// State
const selectedProject = ref<string | null>(null)
const priority = ref<MessagePriority>('normal')
const messageContent = ref('')
const activeTab = ref('edit')
const sending = ref(false)
const loadingProjects = ref(false)
const loadingHistory = ref(false)
const contentError = ref<string | null>(null)

const projectOptions = ref<ProjectOption[]>([])
const broadcastHistory = ref<BroadcastHistoryItem[]>([])

// Toast
const { showToast } = useToast()

// Priority options
const priorityOptions = [
  { title: 'Normal', value: 'normal' },
  { title: 'High', value: 'high' },
  { title: 'Urgent', value: 'urgent' },
]

// Broadcast templates
const templates = ref<BroadcastTemplate[]>([
  {
    id: 'status-check',
    name: 'Status Check',
    content: '**Status Check** - Please provide a brief update on your current progress.',
    priority: 'normal',
  },
  {
    id: 'pause-work',
    name: 'Pause Work',
    content: '**Pause Request** - Please pause your current work and await further instructions.',
    priority: 'high',
  },
  {
    id: 'resume-work',
    name: 'Resume Work',
    content: '**Resume Work** - You may resume your assigned tasks. Thank you for waiting.',
    priority: 'normal',
  },
  {
    id: 'urgent-stop',
    name: 'Urgent Stop',
    content: '**URGENT: STOP WORK** - Immediately cease all activities. Critical issue detected.',
    priority: 'urgent',
  },
])

// Computed
const canSend = computed(() => {
  return !!(selectedProject.value && messageContent.value.trim() && !sending.value)
})

const markdownPreview = computed(() => {
  if (!messageContent.value) return ''
  try {
    return DOMPurify.sanitize(marked(messageContent.value))
  } catch (err) {
    console.error('[BroadcastPanel] Markdown parsing error:', err)
    return DOMPurify.sanitize(messageContent.value)
  }
})

// Methods
const fetchProjects = async () => {
  loadingProjects.value = true
  try {
    const response = await api.projects.list({ status: 'active' })
    projectOptions.value = response.data.map((project: any) => ({
      title: `${project.name} (${project.id})`,
      value: project.id,
    }))

    // Auto-select if only one project
    if (projectOptions.value.length === 1) {
      selectedProject.value = projectOptions.value[0].value
    }
  } catch (err: any) {
    console.error('[BroadcastPanel] Error fetching projects:', err)
    showToast('Failed to load projects', 'error')
  } finally {
    loadingProjects.value = false
  }
}

const fetchBroadcastHistory = async () => {
  loadingHistory.value = true
  try {
    // Fetch broadcasts from message list filtered by type
    const response = await api.messages.list({
      project_id: selectedProject.value || undefined,
    })

    // Filter broadcasts from message list
    broadcastHistory.value = response.data
      .filter((msg: any) => msg.type === 'broadcast' || msg.message_type === 'broadcast')
      .slice(0, 10) // Show last 10 broadcasts
      .map((msg: any) => ({
        id: msg.id,
        content: msg.content,
        recipient_count: msg.to_agents?.length || 0,
        status: msg.status || 'delivered',
        timestamp: msg.created_at,
      }))
  } catch (err: any) {
    console.error('[BroadcastPanel] Error fetching broadcast history:', err)
  } finally {
    loadingHistory.value = false
  }
}

const sendBroadcast = async () => {
  // Validation
  contentError.value = null
  if (!messageContent.value.trim()) {
    contentError.value = 'Message content is required'
    return
  }
  if (!selectedProject.value) {
    showToast('Please select a project', 'warning')
    return
  }

  sending.value = true
  try {
    const response = await api.messages.broadcast(selectedProject.value, messageContent.value)

    showToast(`Broadcast sent to ${response.data.recipient_count} agents`, 'success')

    // Clear form
    messageContent.value = ''
    priority.value = 'normal'
    activeTab.value = 'edit'

    // Refresh history
    fetchBroadcastHistory()
  } catch (err: any) {
    console.error('[BroadcastPanel] Error sending broadcast:', err)
    const errorMsg = err.response?.data?.detail || err.message || 'Failed to send broadcast'
    showToast(errorMsg, 'error')
  } finally {
    sending.value = false
  }
}

const applyTemplate = (template: BroadcastTemplate) => {
  messageContent.value = template.content
  priority.value = template.priority
  activeTab.value = 'edit'
}

const truncateContent = (content: string, maxLength: number = 60): string => {
  if (content.length <= maxLength) return content
  return content.substring(0, maxLength) + '...'
}

const formatTime = (timestamp: string): string => {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

const getStatusColor = (status: string): string => {
  switch (status) {
    case 'delivered':
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    case 'pending':
      return 'warning'
    default:
      return 'grey'
  }
}

const getStatusIcon = (status: string): string => {
  switch (status) {
    case 'delivered':
    case 'completed':
      return 'mdi-check-circle'
    case 'failed':
      return 'mdi-alert-circle'
    case 'pending':
      return 'mdi-clock-outline'
    default:
      return 'mdi-circle-outline'
  }
}

const getTemplateIcon = (priority: MessagePriority): string => {
  switch (priority) {
    case 'urgent':
      return 'mdi-alert'
    case 'high':
      return 'mdi-priority-high'
    default:
      return 'mdi-message-text'
  }
}

// Lifecycle
onMounted(() => {
  fetchProjects()
  fetchBroadcastHistory()
})
</script>

<style scoped>
.markdown-preview {
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.markdown-preview :deep(p) {
  margin-bottom: 0.5rem;
}

.markdown-preview :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-preview :deep(code) {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}

.markdown-preview :deep(pre) {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
  margin: 0.5rem 0;
}

.markdown-preview :deep(pre code) {
  background-color: transparent;
  padding: 0;
}

.markdown-preview :deep(strong) {
  font-weight: 600;
}

.markdown-preview :deep(ul),
.markdown-preview :deep(ol) {
  padding-left: 1.5rem;
  margin-bottom: 0.5rem;
}
</style>
