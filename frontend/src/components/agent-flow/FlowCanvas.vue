<template>
  <div class="flow-canvas-container">
    <!-- Top Controls Bar -->
    <div class="flow-controls-bar">
      <div class="controls-left">
        <v-btn
          icon
          size="small"
          variant="text"
          @click="resetView"
          title="Reset view"
          class="control-btn"
        >
          <v-icon icon="mdi-home" />
        </v-btn>

        <v-divider vertical class="mx-2" />

        <v-btn-group divided size="small" variant="text">
          <v-btn icon @click="decreaseZoom" title="Zoom out" class="control-btn">
            <v-icon icon="mdi-minus" />
          </v-btn>
          <v-btn disabled text-color="grey" class="zoom-display">
            {{ Math.round(flowStore.flowZoom * 100) }}%
          </v-btn>
          <v-btn icon @click="increaseZoom" title="Zoom in" class="control-btn">
            <v-icon icon="mdi-plus" />
          </v-btn>
        </v-btn-group>

        <v-divider vertical class="mx-2" />

        <!-- Animation Speed Selector -->
        <v-menu>
          <template v-slot:activator="{ props }">
            <v-btn
              icon
              size="small"
              variant="text"
              v-bind="props"
              title="Animation speed"
              class="control-btn"
            >
              <v-icon icon="mdi-speedometer" />
            </v-btn>
          </template>
          <v-list density="compact">
            <v-list-item
              v-for="speed in ['fast', 'normal', 'slow']"
              :key="speed"
              @click="setAnimationSpeed(speed)"
              :active="flowStore.animationSpeed === speed"
            >
              <v-list-item-title>{{
                speed.charAt(0).toUpperCase() + speed.slice(1)
              }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </div>

      <div class="controls-center">
        <v-chip
          v-if="flowStore.missionData"
          size="small"
          color="primary"
          variant="flat"
          class="mission-chip"
        >
          <v-icon icon="mdi-target" size="small" class="mr-1" />
          {{ flowStore.missionData.title || 'Active Mission' }}
        </v-chip>

        <v-chip
          v-if="flowStore.flowLoading"
          size="small"
          color="warning"
          variant="flat"
          class="loading-chip"
        >
          <v-progress-circular indeterminate size="16" class="mr-1" />
          Loading...
        </v-chip>
      </div>

      <div class="controls-right">
        <v-btn
          icon
          size="small"
          variant="text"
          @click="flowStore.showMinimap = !flowStore.showMinimap"
          :color="flowStore.showMinimap ? 'primary' : ''"
          title="Toggle minimap"
          class="control-btn"
        >
          <v-icon icon="mdi-map" />
        </v-btn>

        <v-btn
          icon
          size="small"
          variant="text"
          @click="flowStore.showControls = !flowStore.showControls"
          :color="flowStore.showControls ? 'primary' : ''"
          title="Toggle controls"
          class="control-btn"
        >
          <v-icon icon="mdi-cog" />
        </v-btn>

        <v-menu>
          <template v-slot:activator="{ props }">
            <v-btn icon size="small" variant="text" v-bind="props" class="control-btn">
              <v-icon icon="mdi-dots-vertical" />
            </v-btn>
          </template>
          <v-list density="compact">
            <v-list-item @click="exportFlow" title="Export flow data">
              <template v-slot:prepend>
                <v-icon icon="mdi-download" />
              </template>
              <v-list-item-title>Export Flow</v-list-item-title>
            </v-list-item>

            <v-list-item @click="autoLayout" title="Auto arrange nodes">
              <template v-slot:prepend>
                <v-icon icon="mdi-vector-arrange-above" />
              </template>
              <v-list-item-title>Auto Layout</v-list-item-title>
            </v-list-item>

            <v-divider />

            <v-list-item @click="flowStore.resetFlow()" title="Clear everything">
              <template v-slot:prepend>
                <v-icon icon="mdi-trash-can" color="error" />
              </template>
              <v-list-item-title class="text-error">Clear Flow</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </div>
    </div>

    <!-- Main Canvas Area -->
    <div class="flow-canvas-main" ref="canvasContainer">
      <VueFlow
        v-if="!flowStore.flowLoading || flowStore.nodes.length > 0"
        :nodes="flowStore.nodes"
        :edges="flowStore.edges"
        :default-zoom="flowStore.flowZoom"
        :default-position="[flowStore.flowPan.x, flowStore.flowPan.y]"
        @nodes-change="onNodesChange"
        @edges-change="onEdgesChange"
        @node-click="onNodeClick"
        @edge-click="onEdgeClick"
        @pane-click="onPaneClick"
        @pane-ready="onPaneReady"
        @move-end="onMoveEnd"
        :fit-view-on-init="true"
        :min-zoom="0.1"
        :max-zoom="4"
        :pan-on-scroll="true"
        :pan-on-drag="true"
        :zoom-on-scroll="true"
        :selectable-nodes-on-drag="false"
        :node-extent-padding="[50, 50]"
        class="vue-flow-container"
      >
        <!-- Define node types -->
        <template #node-agent="agentNodeProps">
          <AgentNode v-bind="agentNodeProps" />
        </template>

        <!-- Background and Controls -->
        <Background pattern-color="#aaa" gap-size="16" />

        <Controls
          v-if="flowStore.showControls"
          position="top-left"
          :show-fit-view="true"
          :show-zoom="true"
          :show-interactive="false"
        />

        <MiniMap
          v-if="flowStore.showMinimap"
          position="bottom-right"
          :node-color="getNodeMinimapColor"
        />
      </VueFlow>

      <!-- Loading State -->
      <div v-else class="flow-canvas-loading">
        <v-progress-circular indeterminate color="primary" size="80" />
        <p class="mt-4">Initializing flow canvas...</p>
      </div>
    </div>

    <!-- Status Bar -->
    <div class="flow-status-bar">
      <div class="status-item">
        <span class="label">Agents:</span>
        <span class="value">{{ flowStore.totalNodes }}</span>
      </div>

      <div class="status-item">
        <span class="label">Active:</span>
        <v-chip size="x-small" color="success" variant="flat" class="status-chip">
          {{ flowStore.activeNodes.length }}
        </v-chip>
      </div>

      <div class="status-item">
        <span class="label">Completed:</span>
        <v-chip size="x-small" color="secondary" variant="flat" class="status-chip">
          {{ flowStore.completedNodes.length }}
        </v-chip>
      </div>

      <div class="status-item">
        <span class="label">Errors:</span>
        <v-chip size="x-small" color="error" variant="flat" class="status-chip">
          {{ flowStore.errorNodes.length }}
        </v-chip>
      </div>

      <v-spacer />

      <div class="status-item">
        <span class="label">Success Rate:</span>
        <span class="value">{{ flowStore.successRate }}%</span>
      </div>

      <div class="status-item">
        <span class="label">Avg Duration:</span>
        <span class="value">{{ formatDuration(flowStore.averageExecutionTime) }}</span>
      </div>

      <div v-if="flowStore.flowError" class="status-item error-item">
        <v-icon icon="mdi-alert-circle" color="error" size="small" />
        <span class="error-text">{{ flowStore.flowError }}</span>
      </div>
    </div>

    <!-- Right Panel - Node/Edge Details -->
    <transition name="slide-in">
      <div v-if="showDetailPanel" class="flow-detail-panel">
        <NodeDetailPanel v-if="flowStore.selectedNode" :node="flowStore.selectedNode" />
        <EdgeDetailPanel v-else-if="flowStore.selectedEdge" :edge="flowStore.selectedEdge" />
        <div v-else class="empty-panel">
          <v-icon icon="mdi-information" size="large" color="grey" />
          <p>Select a node or edge for details</p>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { VueFlow, Background, Controls, MiniMap, useVueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

import { useAgentFlowStore } from '@/stores/agentFlow'
import { useAgentStore } from '@/stores/agents'
import { useWebSocketStore } from '@/stores/websocket'

import AgentNode from './AgentNode.vue'
import NodeDetailPanel from './panels/NodeDetailPanel.vue'
import EdgeDetailPanel from './panels/EdgeDetailPanel.vue'

const flowStore = useAgentFlowStore()
const agentStore = useAgentStore()
const { fitView } = useVueFlow()

const canvasContainer = ref(null)
const showDetailPanel = computed(() => flowStore.selectedNode || flowStore.selectedEdge)

const props = defineProps({
  projectId: {
    type: String,
    default: null,
  },
  autoInitialize: {
    type: Boolean,
    default: true,
  },
  showDetails: {
    type: Boolean,
    default: true,
  },
})

const emit = defineEmits(['node-selected', 'edge-selected', 'flow-ready'])

// Handle node changes
function onNodesChange(changes) {
  changes.forEach((change) => {
    if (change.type === 'position' && change.position) {
      const node = flowStore.nodes.find((n) => n.id === change.id)
      if (node) {
        node.position = change.position
      }
    } else if (change.type === 'select') {
      if (change.selected) {
        flowStore.selectNode(change.id)
      }
    }
  })
}

// Handle edge changes
function onEdgesChange(changes) {
  changes.forEach((change) => {
    if (change.type === 'select' && change.selected) {
      flowStore.selectEdge(change.id)
    }
  })
}

// Handle node click
function onNodeClick(event) {
  const nodeId = event.node.id
  flowStore.selectNode(nodeId)
  emit('node-selected', event.node)
}

// Handle edge click
function onEdgeClick(event) {
  const edgeId = event.edge.id
  flowStore.selectEdge(edgeId)
  emit('edge-selected', event.edge)
}

// Handle pane click
function onPaneClick() {
  flowStore.clearSelection()
}

// Handle pane ready
function onPaneReady() {
  fitView()
}

// Handle pan/zoom move
function onMoveEnd(event) {
  if (event.instance) {
    flowStore.updateZoom(event.instance.getZoom())
    const { x, y } = event.instance.getViewport()
    flowStore.updatePan({ x, y })
  }
}

// Control functions
function increaseZoom() {
  flowStore.updateZoom(flowStore.flowZoom + 0.2)
}

function decreaseZoom() {
  flowStore.updateZoom(flowStore.flowZoom - 0.2)
}

function resetView() {
  fitView()
}

function setAnimationSpeed(speed) {
  flowStore.animationSpeed = speed
}

function getNodeMinimapColor(node) {
  return node.data?.color || '#315074'
}

function formatDuration(ms) {
  if (!ms) return '0s'
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

function exportFlow() {
  const flowData = {
    nodes: flowStore.nodes,
    edges: flowStore.edges,
    zoom: flowStore.flowZoom,
    pan: flowStore.flowPan,
    mission: flowStore.missionData,
    artifacts: flowStore.artifacts,
    timestamp: new Date().toISOString(),
  }

  const dataStr = JSON.stringify(flowData, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `flow-${Date.now()}.json`
  link.click()
  URL.revokeObjectURL(url)
}

function autoLayout() {
  // Simple circle layout for nodes
  const nodeCount = flowStore.nodes.length
  if (nodeCount === 0) return

  const radius = Math.max(300, nodeCount * 50)
  const angle = (Math.PI * 2) / nodeCount

  flowStore.nodes.forEach((node, index) => {
    const x = Math.cos(index * angle) * radius
    const y = Math.sin(index * angle) * radius
    node.position = { x, y }
  })

  nextTick(() => {
    fitView()
  })
}

// Initialize flow
async function initializeFlow() {
  try {
    // Fetch agents from store
    if (props.autoInitialize && agentStore.agents.length === 0) {
      await agentStore.fetchAgents(props.projectId)
    }

    // Initialize flow from agents
    flowStore.initializeFromAgents()

    // Initialize WebSocket store
    const wsStore = useWebSocketStore()
    if (props.projectId) {
      wsStore.subscribe(`project:${props.projectId}`)
    }

    // Subscribe to message flow events
    wsStore.on('message:flow', (data) => {
      console.log('Flow message:', data)
    })

    emit('flow-ready')
  } catch (error) {
    console.error('Failed to initialize flow:', error)
    flowStore.flowError = 'Failed to initialize flow canvas'
  }
}

// Lifecycle hooks
onMounted(async () => {
  await nextTick()
  await initializeFlow()
})

onUnmounted(() => {
  if (props.projectId) {
    const wsStore = useWebSocketStore()
    wsStore.unsubscribe(`project:${props.projectId}`)
  }
})
</script>

<style scoped lang="scss">
.flow-canvas-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #0e1c2d;
  color: #e1e1e1;
  position: relative;

  .flow-controls-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    background: #182739;
    border-bottom: 1px solid #315074;
    gap: 16px;
    flex-wrap: wrap;

    .controls-left,
    .controls-center,
    .controls-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .control-btn {
      transition: all 0.2s ease;

      &:hover {
        transform: scale(1.1);
      }
    }

    .zoom-display {
      min-width: 60px;
      font-family: 'Roboto Mono', monospace;
      font-size: 12px;
    }

    .mission-chip {
      background: linear-gradient(135deg, #315074 0%, #1e3147 100%) !important;
      animation: pulse-glow 2s ease-in-out infinite;
    }

    .loading-chip {
      animation: pulse 2s ease-in-out infinite;
    }
  }

  .flow-canvas-main {
    flex: 1;
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, #0e1c2d 0%, #182739 100%);

    .vue-flow-container {
      width: 100%;
      height: 100%;
      background: transparent;

      :deep(.vue-flow__viewport) {
        background:
          radial-gradient(circle at 20% 50%, rgba(49, 80, 116, 0.1) 0%, transparent 50%),
          radial-gradient(circle at 80% 80%, rgba(103, 189, 109, 0.05) 0%, transparent 50%);
      }

      :deep(.vue-flow__edge-textbg) {
        fill: #182739;
      }

      :deep(.vue-flow__edge-text) {
        fill: #e1e1e1;
        font-size: 12px;
      }
    }

    .flow-canvas-loading {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;

      p {
        margin-top: 16px;
        color: #8f97b7;
      }
    }
  }

  .flow-status-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 8px 16px;
    background: #182739;
    border-top: 1px solid #315074;
    font-size: 12px;
    overflow-x: auto;

    .status-item {
      display: flex;
      align-items: center;
      gap: 4px;
      white-space: nowrap;

      .label {
        color: #8f97b7;
        font-weight: 500;
      }

      .value {
        color: #e1e1e1;
        font-weight: 600;
        font-family: 'Roboto Mono', monospace;
      }

      .status-chip {
        min-width: 30px;
        font-size: 11px;
      }

      &.error-item {
        color: #c6298c;
        gap: 8px;

        .error-text {
          color: #c6298c;
        }
      }
    }
  }

  .flow-detail-panel {
    position: absolute;
    right: 0;
    top: 48px;
    bottom: 40px;
    width: 320px;
    background: #182739;
    border-left: 1px solid #315074;
    border-bottom: 1px solid #315074;
    box-shadow: -2px 0 8px rgba(0, 0, 0, 0.3);
    overflow-y: auto;
    z-index: 10;

    .empty-panel {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #8f97b7;
    }
  }
}

// Animations
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes pulse-glow {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(49, 80, 116, 0.7);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(49, 80, 116, 0);
  }
}

.slide-in-enter-active,
.slide-in-leave-active {
  transition: all 0.3s ease;
}

.slide-in-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.slide-in-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
</style>
