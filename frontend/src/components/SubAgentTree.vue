<template>
  <v-card class="sub-agent-tree" elevation="2">
    <!-- Header -->
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2" color="primary">
        <img src="/icons/chart.svg" width="24" height="24" alt="Tree" />
      </v-icon>
      <span>Agent Hierarchy</span>
      <v-spacer />
      <v-btn size="small" @click="expandAll" class="mr-1">
        <v-icon left>mdi-unfold-more-horizontal</v-icon>
        Expand All
      </v-btn>
      <v-btn size="small" @click="collapseAll" class="mr-1">
        <v-icon left>mdi-unfold-less-horizontal</v-icon>
        Collapse
      </v-btn>
      <v-btn size="small" @click="resetView">
        <v-icon left>mdi-restore</v-icon>
        Reset
      </v-btn>
    </v-card-title>

    <!-- Tree Container -->
    <v-card-text class="tree-container">
      <div
        class="tree-wrapper"
        ref="treeWrapper"
        @wheel="handleZoom"
        @mousedown="startPan"
        @mousemove="pan"
        @mouseup="endPan"
        @mouseleave="endPan"
      >
        <svg
          :width="treeWidth"
          :height="treeHeight"
          class="tree-svg"
          :style="{
            transform: `scale(${zoomLevel}) translate(${panOffset.x}px, ${panOffset.y}px)`
          }"
        >
          <!-- Definitions -->
          <defs>
            <!-- Drop shadow filter -->
            <filter id="nodeShadow" x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow dx="2" dy="2" stdDeviation="3" flood-opacity="0.3"/>
            </filter>

            <!-- Gradient definitions for status colors -->
            <linearGradient id="activeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" :style="`stop-color:${colors.active};stop-opacity:1`" />
              <stop offset="100%" :style="`stop-color:${colors.active};stop-opacity:0.7`" />
            </linearGradient>

            <linearGradient id="pendingGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" :style="`stop-color:${colors.pending};stop-opacity:1`" />
              <stop offset="100%" :style="`stop-color:${colors.pending};stop-opacity:0.7`" />
            </linearGradient>
          </defs>

          <!-- Connection Lines -->
          <g class="connections">
            <path
              v-for="link in treeLinks"
              :key="`link-${link.source.id}-${link.target.id}`"
              :d="getLinkPath(link)"
              :stroke="link.active ? colors.active : colors.connectionLine"
              :stroke-width="link.active ? 2 : 1"
              :stroke-dasharray="link.active ? 'none' : '2,2'"
              fill="none"
              class="tree-link"
            />
          </g>

          <!-- Tree Nodes -->
          <g class="nodes">
            <g
              v-for="node in treeNodes"
              :key="node.id"
              :transform="`translate(${node.x}, ${node.y})`"
              class="tree-node"
              @click="selectNode(node)"
              @dblclick="toggleNode(node)"
              @mouseenter="showNodeTooltip(node, $event)"
              @mouseleave="hideNodeTooltip"
              @contextmenu.prevent="showContextMenu(node, $event)"
            >
              <!-- Node Background -->
              <rect
                :x="-nodeWidth / 2"
                :y="-nodeHeight / 2"
                :width="nodeWidth"
                :height="nodeHeight"
                :fill="getNodeBackground(node)"
                :stroke="getNodeBorderColor(node)"
                :stroke-width="2"
                rx="8"
                filter="url(#nodeShadow)"
                class="node-rect"
              />

              <!-- Node Icon -->
              <image
                :href="getNodeIcon(node)"
                :x="-nodeWidth / 2 + 8"
                :y="-nodeHeight / 2 + 8"
                width="20"
                height="20"
              />

              <!-- Node Name -->
              <text
                x="0"
                :y="-nodeHeight / 2 + 20"
                :fill="colors.text"
                text-anchor="middle"
                font-size="14"
                font-weight="500"
                class="node-name"
              >
                {{ node.name }}
              </text>

              <!-- Context Usage Bar -->
              <rect
                v-if="node.context_used !== undefined"
                :x="-nodeWidth / 2 + 10"
                :y="0"
                :width="nodeWidth - 20"
                height="4"
                :fill="colors.trackBackground"
                rx="2"
              />
              <rect
                v-if="node.context_used !== undefined"
                :x="-nodeWidth / 2 + 10"
                :y="0"
                :width="(nodeWidth - 20) * (node.context_used / 150000)"
                height="4"
                :fill="getContextColor(node.context_used)"
                rx="2"
              >
                <animate
                  v-if="node.status === 'active'"
                  attributeName="width"
                  :values="`${(nodeWidth - 20) * (node.context_used / 150000)};${(nodeWidth - 20) * ((node.context_used + 1000) / 150000)};${(nodeWidth - 20) * (node.context_used / 150000)}`"
                  dur="2s"
                  repeatCount="indefinite"
                />
              </rect>

              <!-- Status Text -->
              <text
                x="0"
                :y="nodeHeight / 2 - 8"
                :fill="colors.textSecondary"
                text-anchor="middle"
                font-size="12"
                class="node-status"
              >
                {{ node.status }}
              </text>

              <!-- Expand/Collapse Indicator -->
              <g
                v-if="node.children && node.children.length > 0"
                :transform="`translate(${nodeWidth / 2 - 10}, 0)`"
                class="expand-indicator"
                @click.stop="toggleNode(node)"
              >
                <circle
                  r="8"
                  :fill="colors.primary"
                  opacity="0.8"
                />
                <text
                  x="0"
                  y="3"
                  fill="#0e1c2d"
                  text-anchor="middle"
                  font-size="12"
                  font-weight="bold"
                >
                  {{ node.expanded ? '−' : '+' }}
                </text>
              </g>
            </g>
          </g>
        </svg>
      </div>

      <!-- Zoom Controls -->
      <div class="zoom-controls">
        <v-btn icon="mdi-minus" size="x-small" @click="zoomOut" />
        <v-slider
          v-model="zoomLevel"
          :min="0.5"
          :max="2"
          :step="0.1"
          density="compact"
          hide-details
          class="zoom-slider"
        />
        <v-btn icon="mdi-plus" size="x-small" @click="zoomIn" />
      </div>
    </v-card-text>

    <!-- Node Tooltip -->
    <v-tooltip
      v-model="showTooltip"
      :location="tooltipLocation"
      :open-on-hover="false"
      contained
    >
      <div class="node-tooltip" v-if="hoveredNode">
        <div class="tooltip-header">
          <v-icon :color="getNodeBorderColor(hoveredNode)" size="small">
            mdi-robot
          </v-icon>
          <strong>{{ hoveredNode.name }}</strong>
        </div>
        <v-divider class="my-1" />
        <div class="tooltip-content">
          <div><strong>Type:</strong> {{ hoveredNode.role || 'agent' }}</div>
          <div><strong>Status:</strong> {{ hoveredNode.status }}</div>
          <div><strong>Children:</strong> {{ hoveredNode.children?.length || 0 }}</div>
          <div><strong>Context:</strong> {{ formatContextUsage(hoveredNode.context_used) }}</div>
          <div><strong>Jobs:</strong> {{ hoveredNode.jobs_count || 0 }}</div>
          <div><strong>Messages:</strong> {{ hoveredNode.messages_sent || 0 }}</div>
        </div>
      </div>
    </v-tooltip>

    <!-- Context Menu -->
    <v-menu
      v-model="contextMenu.show"
      :location="contextMenu.location"
      absolute
    >
      <v-list density="compact">
        <v-list-item @click="viewAgentLogs">
          <v-list-item-title>
            <v-icon size="small" class="mr-2">mdi-text-box-outline</v-icon>
            View Logs
          </v-list-item-title>
        </v-list-item>
        <v-list-item @click="viewAgentDetails">
          <v-list-item-title>
            <v-icon size="small" class="mr-2">mdi-information-outline</v-icon>
            View Details
          </v-list-item-title>
        </v-list-item>
        <v-divider v-if="contextMenu.node?.status === 'active'" />
        <v-list-item
          v-if="contextMenu.node?.status === 'active'"
          @click="restartAgent"
        >
          <v-list-item-title>
            <v-icon size="small" class="mr-2" color="warning">mdi-restart</v-icon>
            Restart Agent
          </v-list-item-title>
        </v-list-item>
        <v-list-item
          v-if="contextMenu.node?.status === 'active'"
          @click="terminateAgent"
        >
          <v-list-item-title>
            <v-icon size="small" class="mr-2" color="error">mdi-stop</v-icon>
            Terminate Agent
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>

    <!-- Legend -->
    <v-card-actions class="legend-section">
      <v-chip
        v-for="status in statusTypes"
        :key="status.value"
        :color="status.color"
        size="small"
        variant="flat"
        class="mr-2"
      >
        <v-icon left size="x-small">{{ status.icon }}</v-icon>
        {{ status.label }}
      </v-chip>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useAgentStore } from '@/stores/agents'
import * as d3 from 'd3'
import api from '@/services/api'
import websocketService from '@/services/websocket'

const props = defineProps({
  projectId: {
    type: String,
    default: null
  },
  rootAgent: {
    type: Object,
    default: null
  },
  expandLevel: {
    type: Number,
    default: 2
  },
  interactive: {
    type: Boolean,
    default: true
  },
  showLegend: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['node-selected', 'node-expanded', 'node-collapsed', 'context-menu'])

// Store
const agentStore = useAgentStore()

// Refs
const treeWrapper = ref(null)
const treeWidth = ref(1200)
const treeHeight = ref(600)
const zoomLevel = ref(1)
const panOffset = ref({ x: 0, y: 0 })
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0 })

// Node dimensions
const nodeWidth = 140
const nodeHeight = 60
const nodeSpacingX = 180
const nodeSpacingY = 100

// Tree data
const treeData = ref(null)
const treeNodes = ref([])
const treeLinks = ref([])
const expandedNodes = ref(new Set())

// Tooltip
const showTooltip = ref(false)
const hoveredNode = ref(null)
const tooltipLocation = ref('top')

// Context menu
const contextMenu = ref({
  show: false,
  location: { x: 0, y: 0 },
  node: null
})

// Color scheme from docs/color_themes.md
const colors = {
  background: '#1e3147',
  nodeBackground: '#182739',
  orchestratorBackground: '#1e3147',
  trackBackground: '#182739',
  active: '#67bd6d',
  pending: '#ffc300',
  completed: '#8f97b7',
  failed: '#c6298c',
  connectionLine: '#315074',
  text: '#e1e1e1',
  textSecondary: '#8f97b7',
  primary: '#ffc300'
}

// Status types for legend
const statusTypes = [
  { value: 'active', label: 'Active', color: 'success', icon: 'mdi-rocket-launch' },
  { value: 'pending', label: 'Pending', color: 'warning', icon: 'mdi-clock-outline' },
  { value: 'completed', label: 'Complete', color: 'grey', icon: 'mdi-check-circle' },
  { value: 'failed', label: 'Failed', color: 'error', icon: 'mdi-alert-circle' }
]

// Methods
const fetchTreeData = async () => {
  try {
    const response = await api.get(`/api/agents/tree${props.projectId ? `?project_id=${props.projectId}` : ''}`)
    treeData.value = response.data
    processTreeData()
  } catch (error) {
    console.error('Failed to fetch agent tree:', error)
  }
}

const processTreeData = () => {
  if (!treeData.value) return

  // Initialize expanded nodes based on expandLevel
  expandedNodes.value.clear()
  const initExpanded = (node, level = 0) => {
    if (level < props.expandLevel) {
      expandedNodes.value.add(node.id)
      if (node.children) {
        node.children.forEach(child => initExpanded(child, level + 1))
      }
    }
  }
  initExpanded(treeData.value)

  // Create D3 hierarchy
  const root = d3.hierarchy(treeData.value)
  const treeLayout = d3.tree()
    .nodeSize([nodeSpacingX, nodeSpacingY])
    .separation((a, b) => a.parent === b.parent ? 1 : 1.5)

  // Calculate layout
  treeLayout(root)

  // Center the tree
  const centerX = treeWidth.value / 2
  const centerY = 100

  // Extract nodes and links
  treeNodes.value = root.descendants().map(d => ({
    ...d.data,
    x: d.x + centerX,
    y: d.y + centerY,
    expanded: expandedNodes.value.has(d.data.id),
    children: d.children ? d.children.map(c => c.data) : []
  }))

  treeLinks.value = root.links().map(d => ({
    source: {
      ...d.source.data,
      x: d.source.x + centerX,
      y: d.source.y + centerY
    },
    target: {
      ...d.target.data,
      x: d.target.x + centerX,
      y: d.target.y + centerY
    },
    active: d.source.data.status === 'active' && d.target.data.status === 'active'
  }))
}

const getLinkPath = (link) => {
  const source = link.source
  const target = link.target

  // Bezier curve path
  const midY = (source.y + target.y) / 2
  return `M ${source.x},${source.y + nodeHeight / 2}
          C ${source.x},${midY}
            ${target.x},${midY}
            ${target.x},${target.y - nodeHeight / 2}`
}

const getNodeBackground = (node) => {
  if (node.role === 'orchestrator') {
    return colors.orchestratorBackground
  }
  return colors.nodeBackground
}

const getNodeBorderColor = (node) => {
  const statusColors = {
    active: colors.active,
    pending: colors.pending,
    completed: colors.completed,
    failed: colors.failed
  }
  return statusColors[node.status] || colors.connectionLine
}

const getNodeIcon = (node) => {
  if (node.role === 'orchestrator') return '/icons/users.svg'
  if (node.name?.includes('designer')) return '/icons/adjust.svg'
  if (node.name?.includes('developer')) return '/icons/code.svg'
  if (node.name?.includes('implementer')) return '/icons/settings.svg'
  if (node.name?.includes('tester')) return '/icons/checkmark.svg'
  return '/icons/bubble.svg'
}

const getContextColor = (usage) => {
  const percentage = (usage / 150000) * 100
  if (percentage < 50) return colors.active
  if (percentage < 70) return colors.pending
  if (percentage < 80) return '#ff9800'
  return colors.failed
}

const formatContextUsage = (usage) => {
  if (!usage) return '0 / 150K'
  const percentage = Math.round((usage / 150000) * 100)
  return `${(usage / 1000).toFixed(1)}K / 150K (${percentage}%)`
}

const selectNode = (node) => {
  emit('node-selected', node)
}

const toggleNode = (node) => {
  if (expandedNodes.value.has(node.id)) {
    expandedNodes.value.delete(node.id)
    emit('node-collapsed', node)
  } else {
    expandedNodes.value.add(node.id)
    emit('node-expanded', node)
  }
  processTreeData()
}

const expandAll = () => {
  const addAll = (node) => {
    expandedNodes.value.add(node.id)
    if (node.children) {
      node.children.forEach(addAll)
    }
  }
  if (treeData.value) {
    addAll(treeData.value)
    processTreeData()
  }
}

const collapseAll = () => {
  expandedNodes.value.clear()
  processTreeData()
}

const resetView = () => {
  zoomLevel.value = 1
  panOffset.value = { x: 0, y: 0 }
  processTreeData()
}

const zoomIn = () => {
  zoomLevel.value = Math.min(zoomLevel.value + 0.1, 2)
}

const zoomOut = () => {
  zoomLevel.value = Math.max(zoomLevel.value - 0.1, 0.5)
}

const handleZoom = (event) => {
  event.preventDefault()
  const delta = event.deltaY > 0 ? -0.1 : 0.1
  zoomLevel.value = Math.max(0.5, Math.min(2, zoomLevel.value + delta))
}

const startPan = (event) => {
  if (!props.interactive) return
  isPanning.value = true
  panStart.value = { x: event.clientX - panOffset.value.x, y: event.clientY - panOffset.value.y }
}

const pan = (event) => {
  if (!isPanning.value) return
  panOffset.value = {
    x: event.clientX - panStart.value.x,
    y: event.clientY - panStart.value.y
  }
}

const endPan = () => {
  isPanning.value = false
}

const showNodeTooltip = (node, event) => {
  hoveredNode.value = node
  showTooltip.value = true
}

const hideNodeTooltip = () => {
  showTooltip.value = false
}

const showContextMenu = (node, event) => {
  contextMenu.value = {
    show: true,
    location: { x: event.clientX, y: event.clientY },
    node
  }
  emit('context-menu', { node, event })
}

const viewAgentLogs = () => {
  console.log('View logs for', contextMenu.value.node)
  contextMenu.value.show = false
}

const viewAgentDetails = () => {
  console.log('View details for', contextMenu.value.node)
  contextMenu.value.show = false
}

const restartAgent = () => {
  console.log('Restart agent', contextMenu.value.node)
  contextMenu.value.show = false
}

const terminateAgent = () => {
  console.log('Terminate agent', contextMenu.value.node)
  contextMenu.value.show = false
}

// WebSocket handlers
const handleAgentSpawn = (data) => {
  fetchTreeData()
}

const handleAgentComplete = (data) => {
  fetchTreeData()
}

const handleAgentHandoff = (data) => {
  // Animate handoff between agents
  fetchTreeData()
}

// Lifecycle
onMounted(async () => {
  await fetchTreeData()

  // Set up WebSocket listeners
  const unsubscribeSpawn = websocketService.onMessage('agent:spawn', handleAgentSpawn)
  const unsubscribeComplete = websocketService.onMessage('agent:complete', handleAgentComplete)
  const unsubscribeHandoff = websocketService.onMessage('agent:handoff', handleAgentHandoff)

  // Cleanup
  onUnmounted(() => {
    unsubscribeSpawn()
    unsubscribeComplete()
    unsubscribeHandoff()
  })
})
</script>

<style scoped lang="scss">
.sub-agent-tree {
  background: #1e3147;

  .tree-container {
    position: relative;
    height: 600px;
    overflow: hidden;
    background: #182739;
    border-radius: 8px;
  }

  .tree-wrapper {
    width: 100%;
    height: 100%;
    cursor: grab;

    &:active {
      cursor: grabbing;
    }
  }

  .tree-svg {
    transform-origin: center center;
    transition: transform 0.2s ease;

    .tree-node {
      cursor: pointer;

      .node-rect {
        transition: all 0.3s ease;

        &:hover {
          filter: url(#nodeShadow) brightness(1.1);
        }
      }

      .node-name {
        pointer-events: none;
      }

      .node-status {
        pointer-events: none;
      }

      .expand-indicator {
        cursor: pointer;

        circle {
          transition: opacity 0.2s ease;
        }

        &:hover circle {
          opacity: 1;
        }
      }
    }

    .tree-link {
      pointer-events: none;
    }
  }

  .zoom-controls {
    position: absolute;
    bottom: 16px;
    right: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
    background: #0e1c2d;
    border: 1px solid #315074;
    border-radius: 8px;
    padding: 8px;

    .zoom-slider {
      width: 100px;
    }
  }

  .node-tooltip {
    .tooltip-header {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #ffc300;
      margin-bottom: 8px;
    }

    .tooltip-content {
      color: #e1e1e1;
      font-size: 0.875rem;

      div {
        margin: 4px 0;

        strong {
          color: #8f97b7;
          margin-right: 4px;
        }
      }
    }
  }

  .legend-section {
    background: #182739;
    border-top: 1px solid #315074;
    padding: 12px 16px;
  }
}

@media (max-width: 600px) {
  .sub-agent-tree {
    .tree-container {
      height: 400px;
    }

    .zoom-controls {
      bottom: 8px;
      right: 8px;

      .zoom-slider {
        width: 80px;
      }
    }
  }
}
</style>