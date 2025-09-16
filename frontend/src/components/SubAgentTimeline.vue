<template>
  <v-card class="sub-agent-timeline" elevation="2">
    <v-card-title class="d-flex align-center">
      <v-icon :icon="'mdi-timeline-text'" class="mr-2" color="primary" />
      <span>Agent Timeline</span>
      <v-spacer />
      <v-chip
        size="small"
        :color="isLive ? 'success' : 'grey'"
        variant="flat"
      >
        <v-icon
          size="x-small"
          :icon="isLive ? 'mdi-circle' : 'mdi-circle-outline'"
          class="mr-1"
        />
        {{ isLive ? 'Live' : 'Paused' }}
      </v-chip>
      <v-btn
        icon
        size="small"
        variant="text"
        @click="toggleAutoScroll"
        class="ml-2"
      >
        <v-icon :icon="autoScroll ? 'mdi-arrow-collapse-down' : 'mdi-arrow-expand-down'" />
      </v-btn>
    </v-card-title>

    <v-card-text>
      <v-timeline
        align="start"
        density="compact"
        side="end"
        class="timeline-container"
        ref="timelineContainer"
      >
        <v-timeline-item
          v-for="event in timelineEvents"
          :key="event.id"
          :dot-color="getEventColor(event)"
          :size="event.type === 'spawn' ? 'default' : 'small'"
          :icon="getEventIcon(event)"
        >
          <template v-slot:opposite>
            <div class="text-caption text-grey">
              {{ formatTime(event.timestamp) }}
            </div>
          </template>

          <v-card
            :color="getEventCardColor(event)"
            variant="outlined"
            density="compact"
            class="timeline-card"
            @click="expandEvent(event)"
          >
            <v-card-title class="text-subtitle-2 d-flex align-center">
              <v-icon
                :icon="getAgentIcon(event.agent_name)"
                size="small"
                class="mr-2"
              />
              {{ event.agent_name }}
              <v-spacer />
              <v-chip
                size="x-small"
                :color="getStatusColor(event.status)"
                variant="flat"
              >
                {{ event.status }}
              </v-chip>
            </v-card-title>

            <v-card-text v-if="event.type === 'spawn'" class="pt-1">
              <div class="text-caption">
                <strong>Parent:</strong> {{ event.parent_agent }}
              </div>
              <div class="text-caption mission-preview" v-if="event.mission">
                <strong>Mission:</strong> {{ truncateMission(event.mission) }}
              </div>
            </v-card-text>

            <v-card-text v-else-if="event.type === 'complete'" class="pt-1">
              <v-row dense>
                <v-col cols="6">
                  <div class="text-caption">
                    <strong>Duration:</strong> {{ formatDuration(event.duration) }}
                  </div>
                </v-col>
                <v-col cols="6">
                  <div class="text-caption">
                    <strong>Tokens:</strong> {{ formatNumber(event.tokens_used) }}
                  </div>
                </v-col>
              </v-row>
            </v-card-text>

            <v-expand-transition>
              <div v-if="expandedEvents.has(event.id)">
                <v-divider />
                <v-card-text>
                  <div v-if="event.mission" class="text-caption mb-2">
                    <strong>Full Mission:</strong>
                    <pre class="mission-full">{{ event.mission }}</pre>
                  </div>
                  <div v-if="event.context_usage" class="text-caption">
                    <strong>Context Usage:</strong>
                    <v-progress-linear
                      :model-value="event.context_usage"
                      :color="getContextColor(event.context_usage)"
                      height="20"
                      rounded
                    >
                      <template v-slot:default>
                        {{ event.context_usage }}%
                      </template>
                    </v-progress-linear>
                  </div>
                </v-card-text>
              </div>
            </v-expand-transition>
          </v-card>
        </v-timeline-item>

        <v-timeline-item
          v-if="timelineEvents.length === 0"
          dot-color="grey"
          size="small"
        >
          <v-card variant="text">
            <v-card-text class="text-center text-grey">
              <v-icon icon="mdi-timeline-text-outline" size="large" />
              <div class="mt-2">No agent events yet</div>
            </v-card-text>
          </v-card>
        </v-timeline-item>
      </v-timeline>

      <div v-if="loading" class="text-center py-4">
        <v-progress-circular indeterminate color="primary" />
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useAgentStore } from '@/stores/agents'
import { formatDistanceToNow, format } from 'date-fns'

const props = defineProps({
  projectId: {
    type: String,
    required: true
  },
  maxEvents: {
    type: Number,
    default: 50
  },
  autoRefresh: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['event-selected'])

const agentStore = useAgentStore()
const timelineContainer = ref(null)
const expandedEvents = ref(new Set())
const isLive = ref(true)
const autoScroll = ref(true)
const loading = ref(false)

const timelineEvents = computed(() => {
  return agentStore.agentTimeline
    .filter(event => !props.projectId || event.project_id === props.projectId)
    .slice(0, props.maxEvents)
})

const getEventColor = (event) => {
  const colorMap = {
    spawn: '#67bd6d',
    complete: '#8f97b7',
    error: '#c6298c',
    warning: '#ffc300',
    info: '#8b5cf6'
  }
  return colorMap[event.type] || '#315074'
}

const getEventCardColor = (event) => {
  if (event.status === 'active') return 'surface-variant'
  if (event.status === 'completed') return 'surface'
  if (event.status === 'error') return 'error'
  return 'surface'
}

const getEventIcon = (event) => {
  const iconMap = {
    spawn: 'mdi-rocket-launch',
    complete: 'mdi-check-circle',
    error: 'mdi-alert-circle',
    warning: 'mdi-alert',
    info: 'mdi-information'
  }
  return iconMap[event.type] || 'mdi-circle'
}

const getAgentIcon = (agentName) => {
  if (agentName === 'orchestrator') return 'mdi-account-supervisor'
  if (agentName.includes('designer')) return 'mdi-palette'
  if (agentName.includes('developer')) return 'mdi-code-tags'
  if (agentName.includes('tester')) return 'mdi-test-tube'
  if (agentName.includes('implementer')) return 'mdi-hammer'
  return 'mdi-robot'
}

const getStatusColor = (status) => {
  const statusMap = {
    active: 'success',
    pending: 'warning',
    completed: 'grey',
    error: 'error'
  }
  return statusMap[status] || 'info'
}

const getContextColor = (usage) => {
  if (usage < 50) return 'success'
  if (usage < 70) return 'warning'
  if (usage < 80) return 'orange'
  return 'error'
}

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date

  if (diffMs < 60000) {
    return 'Just now'
  } else if (diffMs < 3600000) {
    return formatDistanceToNow(date, { addSuffix: true })
  } else {
    return format(date, 'HH:mm:ss')
  }
}

const formatDuration = (ms) => {
  if (!ms) return 'N/A'
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`
  } else {
    return `${seconds}s`
  }
}

const formatNumber = (num) => {
  if (!num) return '0'
  return num.toLocaleString()
}

const truncateMission = (mission) => {
  if (!mission) return ''
  const maxLength = 100
  if (mission.length <= maxLength) return mission
  return mission.substring(0, maxLength) + '...'
}

const expandEvent = (event) => {
  if (expandedEvents.value.has(event.id)) {
    expandedEvents.value.delete(event.id)
  } else {
    expandedEvents.value.add(event.id)
  }
  emit('event-selected', event)
}

const toggleAutoScroll = () => {
  autoScroll.value = !autoScroll.value
}

const scrollToTop = async () => {
  if (!autoScroll.value || !timelineContainer.value) return

  await nextTick()
  const container = timelineContainer.value.$el
  if (container) {
    container.scrollTop = 0
  }
}

watch(timelineEvents, () => {
  scrollToTop()
})

onMounted(() => {
  if (props.autoRefresh) {
    isLive.value = true
  }
})

onUnmounted(() => {
  isLive.value = false
})
</script>

<style scoped lang="scss">
.sub-agent-timeline {
  background: var(--color-bg-elevated, #1e3147);

  .timeline-container {
    max-height: 600px;
    overflow-y: auto;
    padding: 16px 0;

    &::-webkit-scrollbar {
      width: 8px;
    }

    &::-webkit-scrollbar-track {
      background: var(--color-bg-secondary, #182739);
      border-radius: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: var(--color-border, #315074);
      border-radius: 4px;

      &:hover {
        background: var(--color-accent-primary, #ffc300);
      }
    }
  }

  .timeline-card {
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      transform: translateX(4px);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }
  }

  .mission-preview {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }

  .mission-full {
    white-space: pre-wrap;
    word-break: break-word;
    font-family: 'Roboto Mono', monospace;
    font-size: 0.75rem;
    background: var(--color-bg-secondary, #182739);
    padding: 8px;
    border-radius: 4px;
    margin-top: 4px;
  }

  :deep(.v-timeline-item__body) {
    padding-bottom: 16px;
  }

  :deep(.v-timeline-item__opposite) {
    flex: 0 0 auto;
    min-width: 80px;
  }
}
</style>