<template>
  <v-card class="sub-agent-timeline" elevation="2">
    <!-- Header -->
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2" color="primary">
        <img src="/icons/users.svg" width="24" height="24" alt="Timeline" />
      </v-icon>
      <span>Agent Timeline</span>
      <v-spacer />
      <v-btn-toggle v-model="viewMode" density="compact" mandatory>
        <v-btn value="live" size="small">Live</v-btn>
        <v-btn value="history" size="small">History</v-btn>
      </v-btn-toggle>
      <v-btn
        :icon="showFilters ? 'mdi-filter-off' : 'mdi-filter'"
        size="small"
        @click="showFilters = !showFilters"
        class="ml-2"
      />
      <v-btn icon="mdi-download" size="small" @click="exportTimeline" class="ml-1" />
      <v-btn icon="mdi-refresh" size="small" @click="refreshTimeline" class="ml-1" />
    </v-card-title>

    <!-- Filters (collapsible) -->
    <v-expand-transition>
      <v-card-text v-show="showFilters" class="filters-section">
        <v-row dense>
          <v-col cols="12" md="3">
            <v-select
              v-model="selectedProject"
              :items="projects"
              label="Project"
              density="compact"
              hide-details
              clearable
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="selectedAgentTypes"
              :items="agentTypes"
              label="Agent Types"
              multiple
              chips
              density="compact"
              hide-details
              clearable
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              v-model="timeRange.start"
              label="Start Time"
              type="datetime-local"
              density="compact"
              hide-details
              clearable
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              v-model="timeRange.end"
              label="End Time"
              type="datetime-local"
              density="compact"
              hide-details
              clearable
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-expand-transition>

    <!-- Timeline Container -->
    <v-card-text class="timeline-container">
      <div class="timeline-wrapper" ref="timelineWrapper">
        <svg :width="timelineWidth" :height="timelineHeight" class="timeline-svg">
          <!-- Background -->
          <rect :width="timelineWidth" :height="timelineHeight" :fill="colors.trackBackground" />

          <!-- Time Axis -->
          <g class="time-axis">
            <line
              :x1="padding.left"
              :y1="timelineHeight - padding.bottom"
              :x2="timelineWidth - padding.right"
              :y2="timelineHeight - padding.bottom"
              :stroke="colors.gridLines"
              stroke-width="1"
            />
            <g v-for="tick in timeTicks" :key="tick.value">
              <line
                :x1="tick.x"
                :y1="timelineHeight - padding.bottom"
                :x2="tick.x"
                :y2="timelineHeight - padding.bottom + 5"
                :stroke="colors.gridLines"
                stroke-width="1"
              />
              <text
                :x="tick.x"
                :y="timelineHeight - padding.bottom + 20"
                :fill="colors.text"
                text-anchor="middle"
                font-size="12"
              >
                {{ tick.label }}
              </text>
            </g>
          </g>

          <!-- Agent Tracks -->
          <g v-for="(track, index) in agentTracks" :key="track.id" class="agent-track">
            <!-- Track Label -->
            <text
              :x="10"
              :y="getTrackY(index) + trackHeight / 2 + 5"
              :fill="colors.text"
              font-size="14"
              font-weight="500"
            >
              {{ track.name }}
            </text>

            <!-- Track Background -->
            <rect
              :x="padding.left"
              :y="getTrackY(index)"
              :width="timelineWidth - padding.left - padding.right"
              :height="trackHeight"
              :fill="colors.trackBackground"
              fill-opacity="0.3"
              rx="4"
            />

            <!-- Agent Bar -->
            <rect
              v-if="track.startTime"
              :x="timeToX(track.startTime)"
              :y="getTrackY(index) + 5"
              :width="timeToX(track.endTime || currentTime) - timeToX(track.startTime)"
              :height="trackHeight - 10"
              :fill="getStatusColor(track.status)"
              rx="4"
              class="agent-bar"
              @click="selectAgent(track)"
              @mouseenter="showTooltip(track, $event)"
              @mouseleave="hideTooltip"
            >
              <animate
                v-if="track.status === 'active'"
                attributeName="opacity"
                values="1;0.7;1"
                dur="2s"
                repeatCount="indefinite"
              />
            </rect>

            <!-- Status Icon -->
            <g v-if="track.startTime">
              <image
                :href="getStatusIcon(track.status)"
                :x="timeToX(track.startTime) + 5"
                :y="getTrackY(index) + trackHeight / 2 - 8"
                width="16"
                height="16"
              />
            </g>

            <!-- Context Usage Indicator -->
            <rect
              v-if="track.contextUsage !== undefined && track.startTime"
              :x="timeToX(track.startTime)"
              :y="getTrackY(index) + trackHeight - 8"
              :width="
                (timeToX(track.endTime || currentTime) - timeToX(track.startTime)) *
                (track.contextUsage / 100)
              "
              height="3"
              :fill="getContextColor(track.contextUsage)"
              rx="1.5"
            />
          </g>

          <!-- Connection Lines (Parent-Child) -->
          <g v-for="connection in connections" :key="connection.id" class="connection">
            <path
              :d="connection.path"
              :stroke="colors.connectionLine"
              stroke-width="1"
              stroke-dasharray="2,2"
              fill="none"
              marker-end="url(#arrowhead)"
            />
          </g>

          <!-- Arrow Marker Definition -->
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" :fill="colors.primary" />
            </marker>
          </defs>
        </svg>
      </div>
    </v-card-text>

    <!-- Agent Details Panel -->
    <v-expand-transition>
      <v-card-text v-if="selectedAgent" class="agent-details">
        <v-row>
          <v-col cols="12" md="6">
            <div class="detail-item"><strong>Agent:</strong> {{ selectedAgent.name }}</div>
            <div class="detail-item">
              <strong>Status:</strong>
              <v-chip :color="getStatusColor(selectedAgent.status)" size="small" variant="flat">
                {{ selectedAgent.status }}
              </v-chip>
            </div>
            <div class="detail-item">
              <strong>Duration:</strong> {{ formatDuration(selectedAgent.duration) }}
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <div class="detail-item">
              <strong>Context Usage:</strong>
              <v-progress-linear
                :model-value="selectedAgent.contextUsage"
                :color="getContextColor(selectedAgent.contextUsage)"
                height="20"
                rounded
              >
                <template v-slot:default> {{ selectedAgent.contextUsage }}% </template>
              </v-progress-linear>
            </div>
            <div class="detail-item">
              <strong>Mission:</strong>
              <v-tooltip :text="selectedAgent.mission">
                <template v-slot:activator="{ props }">
                  <span v-bind="props" class="mission-text">
                    {{ truncate(selectedAgent.mission, 100) }}
                  </span>
                </template>
              </v-tooltip>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-expand-transition>

    <!-- Tooltip -->
    <div
      v-if="tooltip.show"
      class="timeline-tooltip"
      :style="{
        left: tooltip.x + 'px',
        top: tooltip.y + 'px',
      }"
    >
      <div class="tooltip-header">
        <strong>{{ tooltip.agent.name }}</strong>
      </div>
      <div class="tooltip-content">
        <div>Status: {{ tooltip.agent.status }}</div>
        <div>Duration: {{ formatDuration(tooltip.agent.duration) }}</div>
        <div>Context: {{ tooltip.agent.contextUsage }}%</div>
      </div>
    </div>
  </v-card>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useAgentStore } from '@/stores/agents'
import { useProjectStore } from '@/stores/projects'
import websocketService from '@/services/websocket'

const props = defineProps({
  projectId: {
    type: String,
    default: null,
  },
  agents: {
    type: Array,
    default: () => [],
  },
  timeRange: {
    type: Object,
    default: () => ({ start: null, end: null }),
  },
  autoRefresh: {
    type: Boolean,
    default: true,
  },
  refreshInterval: {
    type: Number,
    default: 1000,
  },
})

const emit = defineEmits(['agent-selected', 'time-range-changed', 'export-requested'])

// Store references
const agentStore = useAgentStore()
const projectStore = useProjectStore()

// Refs
const timelineWrapper = ref(null)
const viewMode = ref('live')
const showFilters = ref(false)
const selectedProject = ref(props.projectId)
const selectedAgentTypes = ref([])
const timeRange = ref({ ...props.timeRange })
const selectedAgent = ref(null)
const tooltip = ref({ show: false, x: 0, y: 0, agent: null })

// Timeline dimensions
const timelineWidth = ref(1200)
const timelineHeight = ref(400)
const trackHeight = 40
const padding = { top: 20, right: 50, bottom: 50, left: 150 }

// Current time for live mode
const currentTime = ref(Date.now())
let animationFrame = null
let refreshInterval = null

// Color scheme from docs/color_themes.md
const colors = {
  background: '#1e3147',
  trackBackground: '#182739',
  active: '#67bd6d',
  pending: '#ffc300',
  completed: '#8f97b7',
  failed: '#c6298c',
  gridLines: '#315074',
  text: '#e1e1e1',
  primary: '#ffc300',
  connectionLine: '#315074',
}

// Computed
const projects = computed(() =>
  projectStore.projects.map((p) => ({
    title: p.name,
    value: p.id,
  })),
)

const agentTypes = [
  { title: 'Orchestrator', value: 'orchestrator' },
  { title: 'Designer', value: 'designer' },
  { title: 'Frontend', value: 'frontend' },
  { title: 'Implementer', value: 'implementer' },
  { title: 'Tester', value: 'tester' },
]

const agentTracks = computed(() => {
  let agents = props.agents.length > 0 ? props.agents : agentStore.agents

  // Apply filters
  if (selectedProject.value) {
    agents = agents.filter((a) => a.project_id === selectedProject.value)
  }

  if (selectedAgentTypes.value.length > 0) {
    agents = agents.filter((a) => selectedAgentTypes.value.includes(a.type))
  }

  // Build hierarchy
  const tracks = []
  const orchestrator = agents.find((a) => a.type === 'orchestrator')

  if (orchestrator) {
    tracks.push({
      ...orchestrator,
      level: 0,
      indent: 0,
    })

    // Add children
    const children = agents.filter((a) => a.parent === orchestrator.id)
    children.forEach((child, index) => {
      tracks.push({
        ...child,
        level: 1,
        indent: 1,
      })

      // Add grandchildren
      const grandchildren = agents.filter((a) => a.parent === child.id)
      grandchildren.forEach((gc) => {
        tracks.push({
          ...gc,
          level: 2,
          indent: 2,
        })
      })
    })
  }

  return tracks
})

const connections = computed(() => {
  const conns = []
  agentTracks.value.forEach((track, index) => {
    if (track.parent) {
      const parentIndex = agentTracks.value.findIndex((t) => t.id === track.parent)
      if (parentIndex >= 0) {
        const parent = agentTracks.value[parentIndex]
        conns.push({
          id: `${parent.id}-${track.id}`,
          path: calculateConnectionPath(parentIndex, index, parent, track),
        })
      }
    }
  })
  return conns
})

const timeTicks = computed(() => {
  const ticks = []
  const range = getTimeRange()
  const tickCount = 10
  const tickInterval = (range.end - range.start) / tickCount

  for (let i = 0; i <= tickCount; i++) {
    const time = range.start + tickInterval * i
    ticks.push({
      value: time,
      x: timeToX(time),
      label: formatTimeLabel(time),
    })
  }

  return ticks
})

// Methods
const getTrackY = (index) => {
  return padding.top + index * (trackHeight + 10)
}

const getTimeRange = () => {
  if (timeRange.value.start && timeRange.value.end) {
    return {
      start: new Date(timeRange.value.start).getTime(),
      end: new Date(timeRange.value.end).getTime(),
    }
  }

  // Auto-calculate from agents
  const times = agentTracks.value
    .filter((a) => a.startTime)
    .map((a) => [a.startTime, a.endTime || currentTime.value])
    .flat()

  if (times.length === 0) {
    const now = Date.now()
    return { start: now - 300000, end: now } // Last 5 minutes
  }

  return {
    start: Math.min(...times) - 10000,
    end: Math.max(...times) + 10000,
  }
}

const timeToX = (time) => {
  const range = getTimeRange()
  const ratio = (time - range.start) / (range.end - range.start)
  return padding.left + ratio * (timelineWidth.value - padding.left - padding.right)
}

const getStatusColor = (status) => {
  const statusColors = {
    active: colors.active,
    pending: colors.pending,
    completed: colors.completed,
    failed: colors.failed,
  }
  return statusColors[status] || colors.gridLines
}

const getStatusIcon = (status) => {
  const icons = {
    active: '/icons/rocket.svg',
    pending: '/icons/adjust.svg',
    completed: '/icons/checkmark.svg',
    failed: '/icons/close.svg',
  }
  return icons[status] || '/icons/bubble.svg'
}

const getContextColor = (usage) => {
  if (usage < 50) return colors.active
  if (usage < 70) return colors.pending
  if (usage < 80) return '#ff9800' // Orange blend
  return colors.failed
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
  }
  return `${seconds}s`
}

const formatTimeLabel = (time) => {
  const date = new Date(time)
  const now = new Date()

  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const truncate = (text, length) => {
  if (!text) return ''
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}

const calculateConnectionPath = (parentIndex, childIndex, parent, child) => {
  const parentY = getTrackY(parentIndex) + trackHeight / 2
  const childY = getTrackY(childIndex) + trackHeight / 2
  const parentX = timeToX(parent.endTime || currentTime.value)
  const childX = timeToX(child.startTime)

  // Bezier curve path
  const midX = (parentX + childX) / 2
  return `M ${parentX} ${parentY} C ${midX} ${parentY}, ${midX} ${childY}, ${childX} ${childY}`
}

const selectAgent = (agent) => {
  selectedAgent.value = agent
  emit('agent-selected', agent)
}

const showTooltip = (agent, event) => {
  const rect = timelineWrapper.value.getBoundingClientRect()
  tooltip.value = {
    show: true,
    x: event.clientX - rect.left,
    y: event.clientY - rect.top - 60,
    agent,
  }
}

const hideTooltip = () => {
  tooltip.value.show = false
}

const refreshTimeline = async () => {
  await agentStore.fetchAgents(selectedProject.value)
  if (selectedProject.value) {
    await agentStore.fetchAgentTree(selectedProject.value)
  }
}

const exportTimeline = () => {
  const format = 'json' // Could add dialog to choose format
  emit('export-requested', format)

  // Export logic
  const data = {
    timeline: agentTracks.value,
    timeRange: getTimeRange(),
    exported: new Date().toISOString(),
  }

  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `agent-timeline-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

// WebSocket handlers
const handleAgentSpawn = (data) => {
  agentStore.handleAgentSpawn(data)
  if (viewMode.value === 'live') {
    refreshTimeline()
  }
}

const handleAgentComplete = (data) => {
  agentStore.handleAgentComplete(data)
  if (viewMode.value === 'live') {
    refreshTimeline()
  }
}

const handleAgentUpdate = (data) => {
  agentStore.handleRealtimeUpdate(data)
}

// Animation loop for live mode
const animate = () => {
  if (viewMode.value === 'live') {
    currentTime.value = Date.now()
    animationFrame = requestAnimationFrame(animate)
  }
}

// Lifecycle
onMounted(() => {
  // Set up WebSocket listeners
  const unsubscribeSpawn = websocketService.onMessage('agent:spawn', handleAgentSpawn)
  const unsubscribeComplete = websocketService.onMessage('agent:complete', handleAgentComplete)
  const unsubscribeUpdate = websocketService.onMessage('agent:update', handleAgentUpdate)

  // Start animation if in live mode
  if (viewMode.value === 'live' && props.autoRefresh) {
    animate()
    refreshInterval = setInterval(refreshTimeline, props.refreshInterval)
  }

  // Initial load
  refreshTimeline()

  // Cleanup
  onUnmounted(() => {
    unsubscribeSpawn()
    unsubscribeComplete()
    unsubscribeUpdate()

    if (animationFrame) {
      cancelAnimationFrame(animationFrame)
    }

    if (refreshInterval) {
      clearInterval(refreshInterval)
    }
  })
})

// Watch for view mode changes
watch(viewMode, (newMode) => {
  if (newMode === 'live' && props.autoRefresh) {
    animate()
    refreshInterval = setInterval(refreshTimeline, props.refreshInterval)
  } else {
    if (animationFrame) {
      cancelAnimationFrame(animationFrame)
    }
    if (refreshInterval) {
      clearInterval(refreshInterval)
    }
  }
})
</script>

<style scoped lang="scss">
.sub-agent-timeline {
  background: #1e3147;

  .filters-section {
    background: #182739;
    border-top: 1px solid #315074;
  }

  .timeline-container {
    position: relative;
    overflow-x: auto;
    overflow-y: hidden;

    &::-webkit-scrollbar {
      height: 8px;
    }

    &::-webkit-scrollbar-track {
      background: #182739;
      border-radius: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: #315074;
      border-radius: 4px;

      &:hover {
        background: #ffc300;
      }
    }
  }

  .timeline-svg {
    min-width: 1200px;

    .agent-bar {
      cursor: pointer;
      transition: opacity 0.2s ease;

      &:hover {
        opacity: 0.8;
      }
    }
  }

  .agent-details {
    background: #182739;
    border-top: 1px solid #315074;

    .detail-item {
      margin-bottom: 12px;
      color: #e1e1e1;

      strong {
        color: #ffc300;
        margin-right: 8px;
      }
    }

    .mission-text {
      color: #8f97b7;
      cursor: help;
    }
  }

  .timeline-tooltip {
    position: absolute;
    background: #0e1c2d;
    border: 1px solid #315074;
    border-radius: 4px;
    padding: 8px;
    pointer-events: none;
    z-index: 1000;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);

    .tooltip-header {
      color: #ffc300;
      margin-bottom: 4px;
      font-weight: 500;
    }

    .tooltip-content {
      color: #e1e1e1;
      font-size: 0.875rem;

      div {
        margin: 2px 0;
      }
    }
  }
}

@media (max-width: 600px) {
  .sub-agent-timeline {
    .timeline-container {
      .timeline-svg {
        min-width: 800px;
      }
    }
  }
}
</style>
