import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAgentStore } from './agents'
import { useMessageStore } from './messages'

export const useAgentFlowStore = defineStore('agentFlow', () => {
  const agentStore = useAgentStore()
  const messageStore = useMessageStore()

  // State
  const nodes = ref([])
  const edges = ref([])
  const selectedNode = ref(null)
  const selectedEdge = ref(null)
  const flowZoom = ref(1)
  const flowPan = ref({ x: 0, y: 0 })
  const flowLoading = ref(false)
  const flowError = ref(null)
  const animationSpeed = ref('normal') // fast, normal, slow
  const showMinimap = ref(true)
  const showControls = ref(true)
  const missionData = ref(null)
  const artifacts = ref([])
  const threadMessages = ref({}) // Map of node ID to messages
  const nodeMetrics = ref({}) // Map of node ID to metrics

  // Color palette for flow visualization
  const colorPalette = {
    active: '#67bd6d', // Green
    waiting: '#ffc300', // Amber
    complete: '#8b5cf6', // Purple
    error: '#c6298c', // Red/Pink
    pending: '#315074', // Blue
  }

  // Animation durations (milliseconds)
  const animationDurations = {
    fast: 200,
    normal: 400,
    slow: 800,
  }

  // Computed properties
  const activeNodes = computed(() => nodes.value.filter((n) => n.data?.status === 'active'))

  const completedNodes = computed(() =>
    nodes.value.filter((n) => n.data?.status === 'completed' || n.data?.status === 'complete'),
  )

  const errorNodes = computed(() => nodes.value.filter((n) => n.data?.status === 'error'))

  const nodesByStatus = computed(() => ({
    active: activeNodes.value,
    completed: completedNodes.value,
    error: errorNodes.value,
    waiting: nodes.value.filter((n) => n.data?.status === 'waiting'),
    pending: nodes.value.filter((n) => n.data?.status === 'pending'),
  }))

  const totalNodes = computed(() => nodes.value.length)

  const successRate = computed(() => {
    if (totalNodes.value === 0) return 0
    const successful = completedNodes.value.length
    return Math.round((successful / totalNodes.value) * 100)
  })

  const averageExecutionTime = computed(() => {
    if (completedNodes.value.length === 0) return 0
    const totalTime = completedNodes.value.reduce(
      (sum, node) => sum + (node.data?.duration || 0),
      0,
    )
    return Math.round(totalTime / completedNodes.value.length)
  })

  const getAnimationDuration = computed(
    () => () => animationDurations[animationSpeed.value] || animationDurations.normal,
  )

  // Actions
  function initializeFromAgents() {
    flowLoading.value = true
    flowError.value = null

    try {
      const agents = agentStore.agents
      const newNodes = agents.map((agent, index) => {
        // Calculate position in a circle or grid
        const angle = (index / agents.length) * Math.PI * 2
        const radius = Math.max(300, agents.length * 50)
        const x = Math.cos(angle) * radius
        const y = Math.sin(angle) * radius

        return {
          id: `agent-${agent.id || agent.name}`,
          data: {
            label: agent.name,
            agentId: agent.id,
            agentName: agent.name,
            status: agent.status || 'pending',
            role: agent.role || 'helper',
            health: agent.health || 100,
            activeJobs: agent.active_jobs || 0,
            contextUsed: agent.context_used || 0,
            tokens: agent.tokens_used || 0,
            duration: agent.duration || 0,
            color: getStatusColor(agent.status || 'pending'),
            icon: getAgentIcon(agent.role || agent.name),
            messages: [],
            createdAt: agent.created_at || new Date().toISOString(),
            updatedAt: agent.updated_at || new Date().toISOString(),
          },
          position: { x, y },
          selectable: true,
          draggable: true,
        }
      })

      nodes.value = newNodes
      generateEdgesFromMessages()
    } catch (error) {
      flowError.value = error.message
      console.error('Failed to initialize flow from agents:', error)
    } finally {
      flowLoading.value = false
    }
  }

  function generateEdgesFromMessages() {
    const newEdges = []
    const messageMap = new Map()

    // Build message map from messages store
    messageStore.messages.forEach((msg) => {
      const fromNode = `agent-${msg.from}`
      if (msg.to_agents && Array.isArray(msg.to_agents)) {
        msg.to_agents.forEach((toAgent) => {
          const toNode = `agent-${toAgent}`
          const edgeKey = `${fromNode}-${toNode}`

          if (!messageMap.has(edgeKey)) {
            messageMap.set(edgeKey, {
              source: fromNode,
              target: toNode,
              messages: [],
              totalMessages: 0,
            })
          }

          const edgeData = messageMap.get(edgeKey)
          edgeData.messages.push(msg)
          edgeData.totalMessages++
        })
      }
    })

    // Create edges from message map
    messageMap.forEach((data, key) => {
      newEdges.push({
        id: key,
        source: data.source,
        target: data.target,
        data: {
          messageCount: data.totalMessages,
          messages: data.messages,
          animated: data.messages.some((m) => m.status === 'pending'),
        },
        animated: data.messages.some((m) => m.status === 'pending'),
        style: {
          strokeWidth: Math.min(3 + data.totalMessages * 0.5, 8),
        },
      })
    })

    edges.value = newEdges
  }

  function updateNodeStatus(nodeId, status) {
    const node = nodes.value.find((n) => n.id === nodeId)
    if (node) {
      node.data.status = status
      node.data.color = getStatusColor(status)
      node.data.updatedAt = new Date().toISOString()
    }
  }

  function updateNodeMetrics(nodeId, metrics) {
    const node = nodes.value.find((n) => n.id === nodeId)
    if (node) {
      node.data = {
        ...node.data,
        ...metrics,
        updatedAt: new Date().toISOString(),
      }
    }

    // Also store in nodeMetrics for tracking
    if (!nodeMetrics.value[nodeId]) {
      nodeMetrics.value[nodeId] = []
    }

    nodeMetrics.value[nodeId].push({
      ...metrics,
      timestamp: new Date().toISOString(),
    })

    // Keep only last 100 metric entries per node
    if (nodeMetrics.value[nodeId].length > 100) {
      nodeMetrics.value[nodeId] = nodeMetrics.value[nodeId].slice(-100)
    }
  }

  function addMessageToNode(nodeId, message) {
    const node = nodes.value.find((n) => n.id === nodeId)
    if (node) {
      if (!node.data.messages) {
        node.data.messages = []
      }

      node.data.messages.push(message)

      // Keep only last 50 messages
      if (node.data.messages.length > 50) {
        node.data.messages = node.data.messages.slice(-50)
      }
    }

    // Store in thread messages
    if (!threadMessages.value[nodeId]) {
      threadMessages.value[nodeId] = []
    }

    threadMessages.value[nodeId].push(message)

    // Keep only last 100 messages
    if (threadMessages.value[nodeId].length > 100) {
      threadMessages.value[nodeId] = threadMessages.value[nodeId].slice(-100)
    }
  }

  function getThreadMessages(nodeId) {
    return threadMessages.value[nodeId] || []
  }

  function getNodeMetrics(nodeId) {
    return nodeMetrics.value[nodeId] || []
  }

  function selectNode(nodeId) {
    selectedNode.value = nodes.value.find((n) => n.id === nodeId) || null
  }

  function selectEdge(edgeId) {
    selectedEdge.value = edges.value.find((e) => e.id === edgeId) || null
  }

  function clearSelection() {
    selectedNode.value = null
    selectedEdge.value = null
  }

  function updateZoom(zoom) {
    flowZoom.value = Math.max(0.1, Math.min(zoom, 4))
  }

  function updatePan(pan) {
    flowPan.value = pan
  }

  function setMissionData(mission) {
    missionData.value = {
      ...mission,
      startedAt: new Date().toISOString(),
    }
  }

  function addArtifact(artifact) {
    artifacts.value.push({
      id: `artifact-${Date.now()}`,
      ...artifact,
      createdAt: new Date().toISOString(),
    })

    // Keep only last 100 artifacts
    if (artifacts.value.length > 100) {
      artifacts.value = artifacts.value.slice(-100)
    }
  }

  function getStatusColor(status) {
    const statusColorMap = {
      active: colorPalette.active,
      running: colorPalette.active,
      waiting: colorPalette.waiting,
      pending: colorPalette.pending,
      completed: colorPalette.complete,
      complete: colorPalette.complete,
      error: colorPalette.error,
      failed: colorPalette.error,
    }
    return statusColorMap[status] || colorPalette.pending
  }

  function getAgentIcon(roleOrName) {
    const iconMap = {
      orchestrator: 'mdi-account-supervisor',
      designer: 'mdi-palette',
      developer: 'mdi-code-tags',
      tester: 'mdi-test-tube',
      implementer: 'mdi-hammer',
      analyst: 'mdi-chart-line',
      reviewer: 'mdi-eye',
      helper: 'mdi-robot',
    }

    const lowerName = (roleOrName || '').toLowerCase()

    // Check if name contains any of the roles
    for (const [role, icon] of Object.entries(iconMap)) {
      if (lowerName.includes(role)) {
        return icon
      }
    }

    return iconMap.helper
  }

  function resetFlow() {
    nodes.value = []
    edges.value = []
    selectedNode.value = null
    selectedEdge.value = null
    flowZoom.value = 1
    flowPan.value = { x: 0, y: 0 }
    missionData.value = null
    artifacts.value = []
    threadMessages.value = {}
    nodeMetrics.value = {}
    flowError.value = null
  }

  function clearError() {
    flowError.value = null
  }

  // Handle real-time updates from WebSocket
  function handleAgentUpdate(data) {
    const nodeId = `agent-${data.agent_name || data.agentId}`
    const node = nodes.value.find((n) => n.id === nodeId)

    if (node) {
      if (data.status) {
        updateNodeStatus(nodeId, data.status)
      }

      if (data.health !== undefined || data.context_used !== undefined) {
        const metrics = {}
        if (data.health !== undefined) metrics.health = data.health
        if (data.context_used !== undefined) metrics.contextUsed = data.context_used
        if (data.active_jobs !== undefined) metrics.activeJobs = data.active_jobs
        updateNodeMetrics(nodeId, metrics)
      }
    } else if (data.agent_name) {
      // New agent - reinitialize flow
      initializeFromAgents()
    }
  }

  function handleMessageFlow(data) {
    const fromNodeId = `agent-${data.from_agent}`
    const message = {
      id: data.message_id || `msg-${Date.now()}`,
      from: data.from_agent,
      to: data.to_agents || [],
      content: data.content,
      status: data.status || 'sent',
      createdAt: data.created_at || new Date().toISOString(),
    }

    // Add to source node's messages
    addMessageToNode(fromNodeId, message)

    // Add to each target node's messages
    if (message.to && Array.isArray(message.to)) {
      message.to.forEach((toAgent) => {
        const toNodeId = `agent-${toAgent}`
        addMessageToNode(toNodeId, {
          ...message,
          type: 'received',
        })
      })
    }

    // Update edges
    generateEdgesFromMessages()
  }

  return {
    // State
    nodes,
    edges,
    selectedNode,
    selectedEdge,
    flowZoom,
    flowPan,
    flowLoading,
    flowError,
    animationSpeed,
    showMinimap,
    showControls,
    missionData,
    artifacts,
    threadMessages,
    nodeMetrics,
    colorPalette,
    animationDurations,

    // Getters
    activeNodes,
    completedNodes,
    errorNodes,
    nodesByStatus,
    totalNodes,
    successRate,
    averageExecutionTime,
    getAnimationDuration,

    // Actions
    initializeFromAgents,
    generateEdgesFromMessages,
    updateNodeStatus,
    updateNodeMetrics,
    addMessageToNode,
    getThreadMessages,
    getNodeMetrics,
    selectNode,
    selectEdge,
    clearSelection,
    updateZoom,
    updatePan,
    setMissionData,
    addArtifact,
    getStatusColor,
    getAgentIcon,
    resetFlow,
    clearError,
    handleAgentUpdate,
    handleMessageFlow,
  }
})
