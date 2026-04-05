<template>
  <v-container fluid>
    <!-- Filters & Search Bar -->
    <v-row class="mb-4">
      <v-col cols="12" md="3">
        <v-select
          v-model="selectedAgent"
          :items="agentOptions"
          label="Filter by Agent"
          clearable
          variant="solo"
          flat
          density="compact"
          prepend-inner-icon="mdi-filter"
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-select
          v-model="selectedType"
          :items="messageTypeOptions"
          label="Message Type"
          clearable
          variant="solo"
          flat
          density="compact"
          prepend-inner-icon="mdi-tag"
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-select
          v-model="selectedStatus"
          :items="statusOptions"
          label="Status"
          clearable
          variant="solo"
          flat
          density="compact"
          prepend-inner-icon="mdi-check-circle"
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="searchQuery"
          label="Search messages..."
          prepend-inner-icon="mdi-magnify"
          clearable
          variant="outlined"
          density="compact"
        />
      </v-col>
    </v-row>

    <!-- Message Timeline -->
    <v-row>
      <v-col cols="12">
        <v-card variant="flat" class="smooth-border panel-card">
          <v-card-title class="d-flex align-center justify-space-between pa-4">
            <div class="d-flex align-center">
              <v-icon icon="mdi-message-text" size="24" class="mr-2" />
              <span>Message History</span>
              <span
                v-if="filteredMessages.length > 0"
                class="count-chip ml-2"
              >
                {{ filteredMessages.length }}
              </span>
            </div>
            <div class="d-flex align-center">
              <span class="connection-chip" :class="wsConnected ? 'connection-live' : 'connection-off'">
                <v-icon :icon="wsConnected ? 'mdi-wifi' : 'mdi-wifi-off'" size="16" class="mr-1" />
                {{ wsConnected ? 'Live' : 'Disconnected' }}
              </span>
              <v-btn
                icon="mdi-refresh"
                size="small"
                variant="text"
                class="ml-2"
                :loading="loading"
                @click="refreshMessages"
              />
            </div>
          </v-card-title>

          <v-divider />

          <v-card-text class="pa-0">
            <!-- Loading State -->
            <div v-if="loading && messages.length === 0" class="text-center pa-8">
              <v-progress-circular indeterminate color="primary" size="48" />
              <p class="text-body-2 text-muted-a11y mt-4">Loading messages...</p>
            </div>

            <!-- Error State -->
            <v-alert v-else-if="error" type="error" variant="tonal" class="ma-4">
              {{ error }}
            </v-alert>

            <!-- Empty State -->
            <v-alert
              v-else-if="filteredMessages.length === 0 && !loading"
              type="info"
              variant="tonal"
              class="ma-4"
            >
              <template v-if="hasFilters">
                No messages match your filters. Try adjusting your search criteria.
              </template>
              <template v-else>
                No messages yet. Launch a project to see agent communications.
              </template>
            </v-alert>

            <!-- Message List -->
            <MessageList v-else :messages="filteredMessages" />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import api from '@/services/api'
import MessageList from './MessageList.vue'
import type { Message, MessageType, MessageStatus } from '@/types/message'

interface Props {
  projectId?: string
}

const props = defineProps<Props>()

// State
const messages = ref<Message[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// Filters
const selectedAgent = ref<string | null>(null)
const selectedType = ref<MessageType | null>(null)
const selectedStatus = ref<MessageStatus | null>(null)
const searchQuery = ref('')

// WebSocket
const { isConnected: wsConnected, on: onWebSocket, connect } = useWebSocket()

// Filter options
const agentOptions = computed(() => {
  const agents = new Set<string>()
  messages.value.forEach((msg) => {
    const sender = msg.from || msg.from_agent
    if (sender) agents.add(sender)
    msg.to_agents?.forEach((agent) => agents.add(agent))
  })
  return Array.from(agents)
    .sort()
    .map((agent) => ({
      title: agent,
      value: agent,
    }))
})

const messageTypeOptions = [
  { title: 'Direct', value: 'direct' },
  { title: 'Broadcast', value: 'broadcast' },
  { title: 'System', value: 'system' },
  { title: 'Info', value: 'info' },
  { title: 'Error', value: 'error' },
  { title: 'Success', value: 'success' },
]

const statusOptions = [
  { title: 'Pending', value: 'pending' },
  { title: 'Delivered', value: 'delivered' },
  { title: 'Acknowledged', value: 'acknowledged' },
  { title: 'Completed', value: 'completed' },
  { title: 'Failed', value: 'failed' },
]

// Computed
const hasFilters = computed(() => {
  return !!(selectedAgent.value || selectedType.value || selectedStatus.value || searchQuery.value)
})

const filteredMessages = computed(() => {
  let result = messages.value

  // Filter by agent
  if (selectedAgent.value) {
    result = result.filter((msg) => {
      const sender = msg.from || msg.from_agent
      return (
        sender === selectedAgent.value ||
        msg.to_agents?.includes(selectedAgent.value) ||
        msg.to_agent === selectedAgent.value
      )
    })
  }

  // Filter by type
  if (selectedType.value) {
    result = result.filter((msg) => {
      const msgType = msg.type || msg.message_type
      return msgType === selectedType.value
    })
  }

  // Filter by status
  if (selectedStatus.value) {
    result = result.filter((msg) => msg.status === selectedStatus.value)
  }

  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter((msg) => msg.content.toLowerCase().includes(query))
  }

  return result
})

// Methods
const fetchMessages = async () => {
  loading.value = true
  error.value = null

  try {
    const params: any = {}
    if (props.projectId) {
      params.project_id = props.projectId
    }

    const response = await api.messages.list(params)
    messages.value = response.data
  } catch (err: any) {
    console.error('[MessagePanel] Error fetching messages:', err)
    error.value = err.response?.data?.detail || err.message || 'Failed to load messages'
  } finally {
    loading.value = false
  }
}

const refreshMessages = () => {
  fetchMessages()
}

// WebSocket handlers
const handleNewMessage = (data: any) => {
  // Add new message to beginning of list
  const newMessage: Message = {
    id: data.message_id || data.id,
    from: data.from_agent || data.from || 'unknown',
    from_agent: data.from_agent || data.from,
    to_agents: data.to_agents || [],
    to_agent: data.to_agent,
    content: data.message || data.content || '',
    type: data.type || data.message_type || 'direct',
    message_type: data.type || data.message_type,
    priority: data.priority || 'normal',
    status: data.status || 'pending',
    created_at: data.timestamp || new Date().toISOString(),
    recipient_count: data.recipient_count,
  }

  // Avoid duplicates
  const exists = messages.value.some((msg) => msg.id === newMessage.id)
  if (!exists) {
    messages.value.unshift(newMessage)
  }
}

const handleMessageUpdate = (data: any) => {
  const messageId = data.message_id || data.id
  const index = messages.value.findIndex((msg) => msg.id === messageId)

  if (index !== -1) {
    // Update existing message - handle both flat payload and nested message_data
    const updateData = data.message_data || data
    messages.value[index] = {
      ...messages.value[index],
      ...updateData,
      status: updateData.status || messages.value[index].status,
    }
  } else {
    // New message not in list yet
    handleNewMessage(data.message_data || data)
  }
}

// Lifecycle
onMounted(() => {
  fetchMessages()

  // Connect WebSocket if not already connected
  if (!wsConnected.value) {
    connect()
  }

  // Subscribe to message events
  onWebSocket('message:new', handleNewMessage)
  onWebSocket('message:broadcast', handleNewMessage)
  onWebSocket('message:update', handleMessageUpdate)
  onWebSocket('message:acknowledged', handleMessageUpdate)
  onWebSocket('message:completed', handleMessageUpdate)
})

onUnmounted(() => {
  // Cleanup handled by useWebSocket composable
})
</script>

<style lang="scss" scoped>
@use '../../styles/design-tokens' as *;
.panel-card {
  background: $elevation-raised;
  border-radius: $border-radius-rounded;
}

.count-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 1px 8px;
  border-radius: $border-radius-default;
  font-size: 0.72rem;
  font-weight: 600;
  background: var(--agent-implementor-tinted);
  color: $color-agent-implementor;
  min-width: 24px;
}

.connection-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: $border-radius-md;
  font-size: 0.72rem;
  font-weight: 600;
}

.connection-live {
  background: rgba($color-accent-success, 0.15);
  color: $color-accent-success;
}

.connection-off {
  background: var(--agent-analyzer-tinted);
  color: $color-agent-analyzer;
}
</style>
