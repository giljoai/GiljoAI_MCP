<template>
  <v-container>
    <!-- Header with Actions -->
    <v-row align="center" class="mb-4">
      <v-col>
        <h1 class="text-h4">Messages</h1>
      </v-col>
      <v-col cols="auto">
        <v-btn
          color="primary"
          prepend-icon="mdi-message-plus"
          @click="showComposeDialog = true"
        >
          New Message
        </v-btn>
      </v-col>
    </v-row>

    <!-- Filters Row -->
    <v-row class="mb-4">
      <v-col cols="12" md="4">
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="Search messages"
          variant="outlined"
          density="compact"
          clearable
          hide-details
          data-search-input
        />
      </v-col>
      <v-col cols="12" md="2">
        <v-select
          v-model="statusFilter"
          :items="statusOptions"
          label="Status"
          variant="outlined"
          density="compact"
          clearable
          hide-details
        />
      </v-col>
      <v-col cols="12" md="2">
        <v-select
          v-model="priorityFilter"
          :items="priorityOptions"
          label="Priority"
          variant="outlined"
          density="compact"
          clearable
          hide-details
        />
      </v-col>
      <v-col cols="12" md="2">
        <v-select
          v-model="agentFilter"
          :items="agentOptions"
          label="Agent"
          variant="outlined"
          density="compact"
          clearable
          hide-details
        />
      </v-col>
      <v-col cols="12" md="2">
        <v-btn
          variant="outlined"
          @click="clearFilters"
          block
        >
          Clear Filters
        </v-btn>
      </v-col>
    </v-row>

    <!-- Messages Table -->
    <v-card>
      <v-data-table
        :headers="headers"
        :items="filteredMessages"
        :search="search"
        :loading="loading"
        :items-per-page="10"
        class="elevation-0"
        data-table
      >
        <!-- Loading State -->
        <template v-slot:loading>
          <MascotLoader 
            variant="loader"
            :size="60"
            text="Loading messages..."
          />
        </template>

        <!-- Priority Column -->
        <template v-slot:item.priority="{ item }">
          <v-chip
            :color="getPriorityColor(item.priority)"
            size="small"
            label
          >
            {{ item.priority }}
          </v-chip>
        </template>

        <!-- Status Column -->
        <template v-slot:item.status="{ item }">
          <v-chip
            :color="getStatusColor(item.status)"
            size="small"
            variant="outlined"
          >
            <v-icon start size="x-small">{{ getStatusIcon(item.status) }}</v-icon>
            {{ item.status }}
          </v-chip>
        </template>

        <!-- From Column -->
        <template v-slot:item.from="{ item }">
          <div class="d-flex align-center">
            <v-avatar size="24" class="mr-2">
              <v-icon size="small">mdi-robot</v-icon>
            </v-avatar>
            {{ item.from || 'System' }}
          </div>
        </template>

        <!-- To Column -->
        <template v-slot:item.to_agents="{ item }">
          <v-tooltip v-if="item.to_agents?.length > 2" location="top">
            <template v-slot:activator="{ props }">
              <span v-bind="props">
                {{ item.to_agents.slice(0, 2).join(', ') }} +{{ item.to_agents.length - 2 }}
              </span>
            </template>
            <span>{{ item.to_agents.join(', ') }}</span>
          </v-tooltip>
          <span v-else>
            {{ item.to_agents?.join(', ') || 'All' }}
          </span>
        </template>

        <!-- Content Column -->
        <template v-slot:item.content="{ item }">
          <div class="text-truncate" style="max-width: 300px;">
            {{ item.content }}
          </div>
        </template>

        <!-- Actions Column -->
        <template v-slot:item.actions="{ item }">
          <v-btn
            icon="mdi-eye"
            size="small"
            variant="text"
            @click="viewMessage(item)"
            aria-label="View message"
          />
          <v-btn
            v-if="item.status === 'pending'"
            icon="mdi-check"
            size="small"
            variant="text"
            color="success"
            @click="acknowledgeMessage(item)"
            aria-label="Acknowledge message"
          />
          <v-btn
            icon="mdi-reply"
            size="small"
            variant="text"
            @click="replyToMessage(item)"
            aria-label="Reply to message"
          />
        </template>

        <!-- No Data -->
        <template v-slot:no-data>
          <div class="text-center py-8">
            <MascotLoader
              type="image"
              variant="thinker"
              :size="80"
              :show-text="false"
            />
            <p class="text-h6 mt-4">No messages found</p>
            <p class="text-body-2 text-medium-emphasis">
              {{ search || statusFilter || priorityFilter || agentFilter ? 'Try adjusting your filters' : 'Messages will appear here when sent' }}
            </p>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Message Detail Dialog -->
    <v-dialog v-model="showDetailDialog" max-width="800">
      <v-card v-if="selectedMessage">
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-message</v-icon>
          Message Details
          <v-spacer />
          <v-btn
            icon="mdi-close"
            variant="text"
            @click="showDetailDialog = false"
            aria-label="Close dialog"
          />
        </v-card-title>
        
        <v-card-text>
          <v-row class="mb-4">
            <v-col cols="6">
              <div class="text-caption text-medium-emphasis">From</div>
              <div class="text-body-1">{{ selectedMessage.from || 'System' }}</div>
            </v-col>
            <v-col cols="6">
              <div class="text-caption text-medium-emphasis">To</div>
              <div class="text-body-1">{{ selectedMessage.to_agents?.join(', ') || 'All' }}</div>
            </v-col>
          </v-row>
          
          <v-row class="mb-4">
            <v-col cols="4">
              <div class="text-caption text-medium-emphasis">Priority</div>
              <v-chip
                :color="getPriorityColor(selectedMessage.priority)"
                size="small"
                label
              >
                {{ selectedMessage.priority }}
              </v-chip>
            </v-col>
            <v-col cols="4">
              <div class="text-caption text-medium-emphasis">Status</div>
              <v-chip
                :color="getStatusColor(selectedMessage.status)"
                size="small"
                variant="outlined"
              >
                {{ selectedMessage.status }}
              </v-chip>
            </v-col>
            <v-col cols="4">
              <div class="text-caption text-medium-emphasis">Created</div>
              <div class="text-body-2">{{ formatDate(selectedMessage.created_at) }}</div>
            </v-col>
          </v-row>
          
          <v-divider class="my-4" />
          
          <div class="text-caption text-medium-emphasis mb-2">Content</div>
          <div class="text-body-1" style="white-space: pre-wrap;">{{ selectedMessage.content }}</div>
          
          <div v-if="selectedMessage.acknowledged_by?.length" class="mt-4">
            <div class="text-caption text-medium-emphasis mb-2">Acknowledged By</div>
            <v-chip
              v-for="agent in selectedMessage.acknowledged_by"
              :key="agent"
              size="small"
              class="mr-2"
            >
              {{ agent }}
            </v-chip>
          </div>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showDetailDialog = false"
          >
            Close
          </v-btn>
          <v-btn
            v-if="selectedMessage.status === 'pending'"
            color="success"
            variant="flat"
            @click="acknowledgeMessage(selectedMessage)"
          >
            Acknowledge
          </v-btn>
          <v-btn
            color="primary"
            variant="flat"
            @click="replyToMessage(selectedMessage)"
          >
            Reply
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Compose Message Dialog -->
    <v-dialog v-model="showComposeDialog" max-width="600">
      <v-card>
        <v-card-title>
          <v-icon class="mr-2">mdi-message-plus</v-icon>
          Compose Message
        </v-card-title>
        
        <v-card-text>
          <v-form ref="composeForm">
            <v-select
              v-model="newMessage.to_agents"
              :items="agentOptions"
              label="To Agents"
              multiple
              chips
              variant="outlined"
              :rules="[v => v?.length > 0 || 'Select at least one recipient']"
            />
            
            <v-select
              v-model="newMessage.priority"
              :items="priorityOptions"
              label="Priority"
              variant="outlined"
            />
            
            <v-textarea
              v-model="newMessage.content"
              label="Message Content"
              variant="outlined"
              rows="5"
              :rules="[v => !!v || 'Message content is required']"
            />
          </v-form>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="cancelCompose"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            variant="flat"
            @click="sendMessage"
            :loading="sending"
          >
            Send Message
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMessageStore } from '@/stores/messages'
import { useAgentStore } from '@/stores/agents'
import { formatRelative } from 'date-fns'
import MascotLoader from '@/components/MascotLoader.vue'

// Stores
const messageStore = useMessageStore()
const agentStore = useAgentStore()

// State
const search = ref('')
const statusFilter = ref(null)
const priorityFilter = ref(null)
const agentFilter = ref(null)
const showDetailDialog = ref(false)
const showComposeDialog = ref(false)
const selectedMessage = ref(null)
const composeForm = ref(null)
const sending = ref(false)

// New message form
const newMessage = ref({
  to_agents: [],
  priority: 'normal',
  content: ''
})

// Table headers
const headers = [
  { title: 'Priority', key: 'priority', width: '100' },
  { title: 'Status', key: 'status', width: '120' },
  { title: 'From', key: 'from', width: '150' },
  { title: 'To', key: 'to_agents', width: '150' },
  { title: 'Content', key: 'content' },
  { title: 'Created', key: 'created_at', width: '150' },
  { title: 'Actions', key: 'actions', sortable: false, width: '120' }
]

// Filter options
const statusOptions = ['pending', 'acknowledged', 'completed']
const priorityOptions = ['low', 'normal', 'high', 'urgent', 'critical']

// Computed
const loading = computed(() => messageStore.loading)
const messages = computed(() => messageStore.messages)

const agentOptions = computed(() => {
  return agentStore.agents.map(agent => agent.name)
})

const filteredMessages = computed(() => {
  let filtered = [...messages.value]
  
  if (statusFilter.value) {
    filtered = filtered.filter(m => m.status === statusFilter.value)
  }
  
  if (priorityFilter.value) {
    filtered = filtered.filter(m => m.priority === priorityFilter.value)
  }
  
  if (agentFilter.value) {
    filtered = filtered.filter(m => 
      m.from === agentFilter.value || 
      m.to_agents?.includes(agentFilter.value)
    )
  }
  
  return filtered
})

// Methods
function getPriorityColor(priority) {
  const colors = {
    low: 'grey',
    normal: 'info',
    high: 'warning',
    urgent: 'orange',
    critical: 'error'
  }
  return colors[priority] || 'grey'
}

function getStatusColor(status) {
  const colors = {
    pending: 'warning',
    acknowledged: 'info',
    completed: 'success'
  }
  return colors[status] || 'grey'
}

function getStatusIcon(status) {
  const icons = {
    pending: 'mdi-clock-outline',
    acknowledged: 'mdi-check',
    completed: 'mdi-check-all'
  }
  return icons[status] || 'mdi-help'
}

function formatDate(date) {
  if (!date) return ''
  return formatRelative(new Date(date), new Date())
}

function clearFilters() {
  search.value = ''
  statusFilter.value = null
  priorityFilter.value = null
  agentFilter.value = null
}

function viewMessage(message) {
  selectedMessage.value = message
  showDetailDialog.value = true
}

async function acknowledgeMessage(message) {
  try {
    await messageStore.acknowledgeMessage(message.id, 'user')
    showDetailDialog.value = false
  } catch (error) {
    console.error('Failed to acknowledge message:', error)
  }
}

function replyToMessage(message) {
  showDetailDialog.value = false
  newMessage.value = {
    to_agents: message.from ? [message.from] : [],
    priority: 'normal',
    content: `Re: ${message.content.substring(0, 50)}...

`
  }
  showComposeDialog.value = true
}

function cancelCompose() {
  showComposeDialog.value = false
  newMessage.value = {
    to_agents: [],
    priority: 'normal',
    content: ''
  }
}

async function sendMessage() {
  const { valid } = await composeForm.value.validate()
  if (!valid) return
  
  sending.value = true
  try {
    await messageStore.sendMessage({
      to_agents: newMessage.value.to_agents,
      priority: newMessage.value.priority,
      content: newMessage.value.content,
      from_agent: 'user'
    })
    cancelCompose()
  } catch (error) {
    console.error('Failed to send message:', error)
  } finally {
    sending.value = false
  }
}

// Lifecycle
onMounted(async () => {
  await Promise.all([
    messageStore.fetchMessages(),
    agentStore.fetchAgents()
  ])
})
</script>
