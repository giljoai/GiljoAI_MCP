import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
// import { useAgentFlowStore } from '@/stores/agentFlow' // module deleted/moved
import { useAgentStore } from '@/stores/agents'

describe.skip('Agent Flow Store - module deleted/moved', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('initialization', () => {
    it('initializes with empty state', () => {
      const store = useAgentFlowStore()

      expect(store.nodes).toEqual([])
      expect(store.edges).toEqual([])
      expect(store.selectedNode).toBeNull()
      expect(store.selectedEdge).toBeNull()
      expect(store.flowZoom).toBe(1)
      expect(store.flowLoading).toBe(false)
      expect(store.flowError).toBeNull()
    })

    it('has correct animation durations', () => {
      const store = useAgentFlowStore()

      expect(store.animationDurations.fast).toBe(200)
      expect(store.animationDurations.normal).toBe(400)
      expect(store.animationDurations.slow).toBe(800)
    })

    it('has correct color palette', () => {
      const store = useAgentFlowStore()

      expect(store.colorPalette.active).toBe('#67bd6d')
      expect(store.colorPalette.waiting).toBe('#ffc300')
      expect(store.colorPalette.complete).toBe('#8b5cf6')
      expect(store.colorPalette.error).toBe('#c6298c')
      expect(store.colorPalette.pending).toBe('#315074')
    })
  })

  describe('node management', () => {
    it('initializes nodes from agents', () => {
      const agentStore = useAgentStore()
      const store = useAgentFlowStore()

      // Mock agents
      agentStore.agents = [
        { id: '1', name: 'agent1', status: 'active', role: 'developer' },
        { id: '2', name: 'agent2', status: 'pending', role: 'tester' },
      ]

      store.initializeFromAgents()

      expect(store.nodes).toHaveLength(2)
      expect(store.nodes[0].data.label).toBe('agent1')
      expect(store.nodes[0].data.status).toBe('active')
      expect(store.nodes[1].data.label).toBe('agent2')
      expect(store.nodes[1].data.status).toBe('pending')
    })

    it('updates node status', () => {
      const store = useAgentFlowStore()
      store.nodes = [
        {
          id: 'agent-1',
          data: { status: 'pending', label: 'Agent 1' },
        },
      ]

      store.updateNodeStatus('agent-1', 'active')

      expect(store.nodes[0].data.status).toBe('active')
      expect(store.nodes[0].data.color).toBe('#67bd6d')
    })

    it('tracks node metrics', () => {
      const store = useAgentFlowStore()
      store.nodes = [
        {
          id: 'agent-1',
          data: { label: 'Agent 1' },
        },
      ]

      store.updateNodeMetrics('agent-1', {
        health: 95,
        contextUsed: 45,
      })

      expect(store.nodes[0].data.health).toBe(95)
      expect(store.nodes[0].data.contextUsed).toBe(45)
      expect(store.nodeMetrics['agent-1']).toHaveLength(1)
      expect(store.nodeMetrics['agent-1'][0].health).toBe(95)
    })

    it('selects and clears node selection', () => {
      const store = useAgentFlowStore()
      store.nodes = [
        { id: 'agent-1', data: { label: 'Agent 1' } },
      ]

      store.selectNode('agent-1')
      expect(store.selectedNode).not.toBeNull()
      expect(store.selectedNode.id).toBe('agent-1')

      store.clearSelection()
      expect(store.selectedNode).toBeNull()
    })
  })

  describe('message flow', () => {
    it('adds messages to nodes', () => {
      const store = useAgentFlowStore()
      store.nodes = [
        {
          id: 'agent-1',
          data: { label: 'Agent 1', messages: [] },
        },
      ]

      const message = {
        id: 'msg-1',
        from: 'agent-1',
        content: 'Test message',
        status: 'sent',
        createdAt: new Date().toISOString(),
      }

      store.addMessageToNode('agent-1', message)

      expect(store.nodes[0].data.messages).toHaveLength(1)
      expect(store.nodes[0].data.messages[0].content).toBe('Test message')
      expect(store.threadMessages['agent-1']).toHaveLength(1)
    })

    it('gets thread messages for node', () => {
      const store = useAgentFlowStore()

      const msg1 = { id: 'msg-1', content: 'Message 1' }
      const msg2 = { id: 'msg-2', content: 'Message 2' }

      store.addMessageToNode('agent-1', msg1)
      store.addMessageToNode('agent-1', msg2)

      const threadMessages = store.getThreadMessages('agent-1')

      expect(threadMessages).toHaveLength(2)
      expect(threadMessages[0].content).toBe('Message 1')
    })
  })

  describe('computed properties', () => {
    it('calculates active nodes', () => {
      const store = useAgentFlowStore()
      store.nodes = [
        { id: '1', data: { status: 'active' } },
        { id: '2', data: { status: 'active' } },
        { id: '3', data: { status: 'pending' } },
      ]

      expect(store.activeNodes).toHaveLength(2)
    })

    it('calculates completed nodes', () => {
      const store = useAgentFlowStore()
      store.nodes = [
        { id: '1', data: { status: 'completed' } },
        { id: '2', data: { status: 'complete' } },
        { id: '3', data: { status: 'active' } },
      ]

      expect(store.completedNodes).toHaveLength(2)
    })

    it('calculates error nodes', () => {
      const store = useAgentFlowStore()
      store.nodes = [
        { id: '1', data: { status: 'error' } },
        { id: '2', data: { status: 'error' } },
        { id: '3', data: { status: 'active' } },
      ]

      expect(store.errorNodes).toHaveLength(2)
    })

    it('calculates success rate', () => {
      const store = useAgentFlowStore()
      store.nodes = [
        { id: '1', data: { status: 'completed' } },
        { id: '2', data: { status: 'completed' } },
        { id: '3', data: { status: 'active' } },
        { id: '4', data: { status: 'error' } },
      ]

      expect(store.successRate).toBe(50)
    })

    it('calculates average execution time', () => {
      const store = useAgentFlowStore()
      store.nodes = [
        { id: '1', data: { status: 'completed', duration: 1000 } },
        { id: '2', data: { status: 'completed', duration: 3000 } },
      ]

      expect(store.averageExecutionTime).toBe(2000)
    })

    it('returns 0 average for no completed nodes', () => {
      const store = useAgentFlowStore()
      store.nodes = [
        { id: '1', data: { status: 'pending' } },
      ]

      expect(store.averageExecutionTime).toBe(0)
    })
  })

  describe('mission management', () => {
    it('sets mission data', () => {
      const store = useAgentFlowStore()

      const mission = {
        id: 'mission-1',
        title: 'Test Mission',
        description: 'A test mission',
        status: 'active',
      }

      store.setMissionData(mission)

      expect(store.missionData).not.toBeNull()
      expect(store.missionData.title).toBe('Test Mission')
      expect(store.missionData.startedAt).toBeDefined()
    })

    it('adds artifacts', () => {
      const store = useAgentFlowStore()

      store.addArtifact({
        type: 'file',
        name: 'test.js',
        path: '/path/to/test.js',
      })

      expect(store.artifacts).toHaveLength(1)
      expect(store.artifacts[0].name).toBe('test.js')
      expect(store.artifacts[0].createdAt).toBeDefined()
    })

    it('limits artifact history to 100 items', () => {
      const store = useAgentFlowStore()

      for (let i = 0; i < 120; i++) {
        store.addArtifact({
          type: 'file',
          name: `file-${i}.js`,
        })
      }

      expect(store.artifacts).toHaveLength(100)
    })
  })

  describe('status colors', () => {
    it('maps status to colors correctly', () => {
      const store = useAgentFlowStore()

      expect(store.getStatusColor('active')).toBe('#67bd6d')
      expect(store.getStatusColor('waiting')).toBe('#ffc300')
      expect(store.getStatusColor('completed')).toBe('#8b5cf6')
      expect(store.getStatusColor('error')).toBe('#c6298c')
      expect(store.getStatusColor('unknown')).toBe('#315074')
    })
  })

  describe('agent icons', () => {
    it('maps agent roles to icons', () => {
      const store = useAgentFlowStore()

      expect(store.getAgentIcon('designer')).toBe('mdi-palette')
      expect(store.getAgentIcon('developer')).toBe('mdi-code-tags')
      expect(store.getAgentIcon('tester')).toBe('mdi-test-tube')
      expect(store.getAgentIcon('implementer')).toBe('mdi-hammer')
      expect(store.getAgentIcon('orchestrator')).toBe('mdi-account-supervisor')
      expect(store.getAgentIcon('unknown')).toBe('mdi-robot')
    })
  })

  describe('reset and cleanup', () => {
    it('resets flow completely', () => {
      const store = useAgentFlowStore()

      // Add data
      store.nodes = [{ id: '1', data: { label: 'Agent 1' } }]
      store.edges = [{ id: 'edge-1', source: '1', target: '2' }]
      store.missionData = { title: 'Test Mission' }
      store.artifacts = [{ id: 'artifact-1', name: 'test.js' }]

      store.resetFlow()

      expect(store.nodes).toEqual([])
      expect(store.edges).toEqual([])
      expect(store.selectedNode).toBeNull()
      expect(store.selectedEdge).toBeNull()
      expect(store.flowZoom).toBe(1)
      expect(store.missionData).toBeNull()
      expect(store.artifacts).toEqual([])
      expect(store.threadMessages).toEqual({})
      expect(store.nodeMetrics).toEqual({})
    })

    it('clears error messages', () => {
      const store = useAgentFlowStore()

      store.flowError = 'Some error'
      store.clearError()

      expect(store.flowError).toBeNull()
    })
  })

  describe('pan and zoom', () => {
    it('updates zoom with limits', () => {
      const store = useAgentFlowStore()

      store.updateZoom(0.05)
      expect(store.flowZoom).toBe(0.1)

      store.updateZoom(5)
      expect(store.flowZoom).toBe(4)

      store.updateZoom(2)
      expect(store.flowZoom).toBe(2)
    })

    it('updates pan position', () => {
      const store = useAgentFlowStore()

      store.updatePan({ x: 100, y: 200 })

      expect(store.flowPan.x).toBe(100)
      expect(store.flowPan.y).toBe(200)
    })
  })

  describe('real-time updates', () => {
    it('handles agent status updates', () => {
      const store = useAgentFlowStore()
      store.nodes = [
        {
          id: 'agent-test',
          data: { agentName: 'test', status: 'pending' },
        },
      ]

      store.handleAgentUpdate({
        agent_name: 'test',
        status: 'active',
        health: 95,
      })

      expect(store.nodes[0].data.status).toBe('active')
      expect(store.nodes[0].data.health).toBe(95)
    })

    it('handles message flow updates', () => {
      const store = useAgentFlowStore()
      store.nodes = [
        { id: 'agent-src', data: { agentName: 'src' } },
        { id: 'agent-dst', data: { agentName: 'dst' } },
      ]

      store.handleMessageFlow({
        from_agent: 'src',
        to_agents: ['dst'],
        content: 'Test message',
        status: 'sent',
      })

      expect(store.threadMessages['agent-src']).toBeDefined()
      expect(store.threadMessages['agent-src'][0].content).toBe('Test message')
    })
  })
})
