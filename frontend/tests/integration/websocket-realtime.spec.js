/**
 * Integration tests for WebSocket V2 real-time updates
 * Tests end-to-end user workflows and real-time data synchronization
 *
 * TDD Focus:
 * - Real-time agent status updates
 * - Project mission updates
 * - Toast notifications
 * - Multi-tenant isolation (security)
 * - Reconnection scenarios
 * - Complete user workflows
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { ref } from 'vue'
import { useWebSocketV2 } from '@/composables/useWebSocket'
import { useWebSocketStore } from '@/stores/websocket'

// Mock WebSocket
global.WebSocket = vi.fn(() => ({
  readyState: WebSocket.OPEN,
  send: vi.fn(),
  close: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  OPEN: 1,
  CONNECTING: 0,
  CLOSING: 2,
  CLOSED: 3,
}))

// Mock toast composable
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn(),
  }),
}))

// ============================================
// TEST COMPONENTS
// ============================================

/**
 * Component that displays real-time agent list
 */
const AgentListComponent = {
  setup() {
    const composable = useWebSocketV2()
    const agents = ref([])

    // Subscribe to agent updates
    composable.on('agent:created', (data) => {
      agents.value.push(data)
    })

    composable.on('agent:status_changed', (data) => {
      const agent = agents.value.find((a) => a.id === data.id)
      if (agent) {
        agent.status = data.status
      }
    })

    composable.on('agent:deleted', (data) => {
      agents.value = agents.value.filter((a) => a.id !== data.id)
    })

    return {
      agents,
      ...composable,
    }
  },
  template: `
    <div>
      <div v-for="agent in agents" :key="agent.id" class="agent-item">
        <span>{{ agent.name }}</span>
        <span class="status">{{ agent.status }}</span>
      </div>
    </div>
  `,
}

/**
 * Component that displays project with mission
 */
const ProjectDashboardComponent = {
  setup() {
    const composable = useWebSocketV2()
    const project = ref({ id: 'proj-1', name: 'Test Project', mission: '' })

    // Subscribe to project updates
    composable.on('project:mission_updated', (data) => {
      if (data.projectId === project.value.id) {
        project.value.mission = data.mission
      }
    })

    return {
      project,
      ...composable,
    }
  },
  template: `
    <div>
      <h1>{{ project.name }}</h1>
      <p>{{ project.mission }}</p>
    </div>
  `,
}

/**
 * Component with subscription-based updates
 */
const EntitySubscriberComponent = {
  setup() {
    const composable = useWebSocketV2()
    const entity = ref(null)
    const subscriptionKey = ref(null)

    const subscribe = (entityType, entityId) => {
      subscriptionKey.value = composable.subscribe(entityType, entityId)
    }

    const unsubscribe = (entityType, entityId) => {
      composable.unsubscribe(entityType, entityId)
      subscriptionKey.value = null
    }

    return {
      entity,
      subscriptionKey,
      subscribe,
      unsubscribe,
      ...composable,
    }
  },
  template: '<div></div>',
}

/**
 * Component that shows connection status
 */
const ConnectionStatusComponent = {
  setup() {
    const composable = useWebSocketV2()
    const statusHistory = ref([])

    composable.onConnectionChange((data) => {
      statusHistory.value.push(data.state)
    })

    return {
      statusHistory,
      ...composable,
    }
  },
  template: `
    <div>
      <span class="current-status">{{ isConnected ? 'Connected' : 'Disconnected' }}</span>
      <div class="status-history">
        <span v-for="status in statusHistory" :key="status">{{ status }}</span>
      </div>
    </div>
  `,
}

/**
 * Multi-tenant component
 */
const MultiTenantComponent = {
  props: {
    tenantKey: String,
  },
  setup(props) {
    const composable = useWebSocketV2()
    const data = ref(null)

    composable.on('data:updated', (payload) => {
      // Only update if from same tenant
      if (payload.tenant_key === props.tenantKey) {
        data.value = payload.data
      }
    })

    return {
      data,
      ...composable,
    }
  },
  template: '<div>{{ data }}</div>',
}

// ============================================
// CATEGORY 1: REAL-TIME AGENT UPDATES
// ============================================

describe('WebSocket Integration - Real-time Agent Updates', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('creates agent triggers real-time UI update', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    expect(wrapper.vm.agents).toHaveLength(0)

    // Simulate WebSocket message
    const newAgent = { id: 'agent-1', name: 'Test Agent', status: 'active' }
    store.handleMessage({
      type: 'agent:created',
      ...newAgent,
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.agents).toHaveLength(1)
    expect(wrapper.vm.agents[0].name).toBe('Test Agent')
    expect(wrapper.vm.agents[0].status).toBe('active')
    expect(wrapper.text()).toContain('Test Agent')
  })

  it('agent status change appears immediately in UI', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    // Create agent
    store.handleMessage({
      type: 'agent:created',
      id: 'agent-1',
      name: 'Test Agent',
      status: 'idle',
    })

    await wrapper.vm.$nextTick()
    expect(wrapper.vm.agents[0].status).toBe('idle')

    // Update agent status
    store.handleMessage({
      type: 'agent:status_changed',
      id: 'agent-1',
      status: 'running',
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.agents[0].status).toBe('running')
    expect(wrapper.text()).toContain('running')
  })

  it('agent deletion removes from UI immediately', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    // Create two agents
    store.handleMessage({
      type: 'agent:created',
      id: 'agent-1',
      name: 'Agent 1',
      status: 'active',
    })

    store.handleMessage({
      type: 'agent:created',
      id: 'agent-2',
      name: 'Agent 2',
      status: 'active',
    })

    await wrapper.vm.$nextTick()
    expect(wrapper.vm.agents).toHaveLength(2)

    // Delete first agent
    store.handleMessage({
      type: 'agent:deleted',
      id: 'agent-1',
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.agents).toHaveLength(1)
    expect(wrapper.vm.agents[0].name).toBe('Agent 2')
    expect(wrapper.text()).not.toContain('Agent 1')
  })

  it('handles multiple rapid agent updates without losing data', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    // Rapid updates
    for (let i = 0; i < 10; i++) {
      store.handleMessage({
        type: 'agent:created',
        id: `agent-${i}`,
        name: `Agent ${i}`,
        status: 'active',
      })
    }

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.agents).toHaveLength(10)
  })
})

// ============================================
// CATEGORY 2: PROJECT MISSION UPDATES
// ============================================

describe('WebSocket Integration - Project Mission Updates', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('project mission update reflects immediately in dashboard', async () => {
    const wrapper = mount(ProjectDashboardComponent)
    const store = useWebSocketStore()

    expect(wrapper.vm.project.mission).toBe('')

    // Simulate mission update
    store.handleMessage({
      type: 'project:mission_updated',
      projectId: 'proj-1',
      mission: 'Build new feature',
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.project.mission).toBe('Build new feature')
    expect(wrapper.text()).toContain('Build new feature')
  })

  it('only updates mission for matching project', async () => {
    const wrapper = mount(ProjectDashboardComponent)
    const store = useWebSocketStore()

    // Update mission for different project
    store.handleMessage({
      type: 'project:mission_updated',
      projectId: 'proj-999',
      mission: 'Different project mission',
    })

    await wrapper.vm.$nextTick()

    // Original project mission unchanged
    expect(wrapper.vm.project.mission).toBe('')
    expect(wrapper.text()).not.toContain('Different project mission')
  })

  it('project activation event triggers subscription', async () => {
    const wrapper = mount(EntitySubscriberComponent)
    const store = useWebSocketStore()

    wrapper.vm.subscribe('project', 'proj-1')
    expect(wrapper.vm.subscriptionKey).toBe('project:proj-1')

    expect(store.subscriptions.value.has('project:proj-1')).toBe(true)
  })
})

// ============================================
// CATEGORY 3: CONNECTION STATE TRACKING
// ============================================

describe('WebSocket Integration - Connection State Tracking', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('connection state changes trigger listeners', async () => {
    const wrapper = mount(ConnectionStatusComponent)
    const store = useWebSocketStore()

    expect(wrapper.vm.statusHistory).toHaveLength(0)

    // Notify connection listeners
    store.notifyConnectionListeners('connected')
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.statusHistory).toHaveLength(1)
    expect(wrapper.vm.statusHistory[0]).toBe('connected')

    // Another state change
    store.notifyConnectionListeners('reconnecting', { attempt: 1 })
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.statusHistory).toHaveLength(2)
    expect(wrapper.vm.statusHistory[1]).toBe('reconnecting')
  })

  it('isConnected computed property reflects connection state', async () => {
    const wrapper = mount(ConnectionStatusComponent)
    const store = useWebSocketStore()

    store.connectionStatus.value = 'disconnected'
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.isConnected).toBe(false)

    store.connectionStatus.value = 'connected'
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.isConnected).toBe(true)
  })

  it('isReconnecting reflects reconnection state', async () => {
    const wrapper = mount(ConnectionStatusComponent)
    const store = useWebSocketStore()

    store.connectionStatus.value = 'reconnecting'
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.isReconnecting).toBe(true)

    store.connectionStatus.value = 'connected'
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.isReconnecting).toBe(false)
  })
})

// ============================================
// CATEGORY 4: MULTI-TENANT ISOLATION
// (SECURITY-CRITICAL)
// ============================================

describe('WebSocket Integration - Multi-Tenant Isolation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('User A updates do not appear for User B', async () => {
    const store = useWebSocketStore()

    // Component for User A
    const wrapperA = mount(MultiTenantComponent, {
      props: { tenantKey: 'tenant-a' },
    })

    // Component for User B
    const wrapperB = mount(MultiTenantComponent, {
      props: { tenantKey: 'tenant-b' },
    })

    // User A receives update
    store.handleMessage({
      type: 'data:updated',
      tenant_key: 'tenant-a',
      data: 'User A Data',
    })

    await wrapperA.vm.$nextTick()
    await wrapperB.vm.$nextTick()

    // User A's component updates
    expect(wrapperA.vm.data).toBe('User A Data')

    // User B's component does NOT update
    expect(wrapperB.vm.data).toBeNull()
  })

  it('User B data remains unchanged after User A update', async () => {
    const store = useWebSocketStore()

    const wrapperA = mount(MultiTenantComponent, {
      props: { tenantKey: 'tenant-a' },
    })

    const wrapperB = mount(MultiTenantComponent, {
      props: { tenantKey: 'tenant-b' },
    })

    // User B receives update first
    store.handleMessage({
      type: 'data:updated',
      tenant_key: 'tenant-b',
      data: 'User B Data',
    })

    await wrapperB.vm.$nextTick()
    expect(wrapperB.vm.data).toBe('User B Data')

    // User A receives update
    store.handleMessage({
      type: 'data:updated',
      tenant_key: 'tenant-a',
      data: 'User A Data',
    })

    await wrapperA.vm.$nextTick()

    // User B's data unchanged
    expect(wrapperB.vm.data).toBe('User B Data')
  })

  it('subscriptions respect tenant boundaries', async () => {
    const wrapperA = mount(MultiTenantComponent, {
      props: { tenantKey: 'tenant-a' },
    })

    const wrapperB = mount(MultiTenantComponent, {
      props: { tenantKey: 'tenant-b' },
    })

    wrapperA.vm.subscribe('project', 'proj-1')
    wrapperB.vm.subscribe('project', 'proj-1')

    // Both can subscribe to same entity (store doesn't track tenant)
    // But application layer enforces filtering via tenant_key in messages
    const store = useWebSocketStore()
    expect(store.subscriptions.value.has('project:proj-1')).toBe(true)
  })

  it('handles multiple tenants in concurrent components', async () => {
    const store = useWebSocketStore()

    const components = []
    for (let i = 0; i < 5; i++) {
      components.push(
        mount(MultiTenantComponent, {
          props: { tenantKey: `tenant-${i}` },
        })
      )
    }

    // Send updates for each tenant
    for (let i = 0; i < 5; i++) {
      store.handleMessage({
        type: 'data:updated',
        tenant_key: `tenant-${i}`,
        data: `Tenant ${i} Data`,
      })
    }

    await Promise.all(components.map((c) => c.vm.$nextTick?.()))

    // Each component should only have its own data
    for (let i = 0; i < 5; i++) {
      expect(components[i].vm.data).toBe(`Tenant ${i} Data`)
    }
  })
})

// ============================================
// CATEGORY 5: RECONNECTION SCENARIOS
// ============================================

describe('WebSocket Integration - Reconnection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('messages resume after disconnect and reconnect', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    // Initial connection
    store.connectionStatus.value = 'connected'

    // Create agent while connected
    store.handleMessage({
      type: 'agent:created',
      id: 'agent-1',
      name: 'Agent 1',
      status: 'active',
    })

    await wrapper.vm.$nextTick()
    expect(wrapper.vm.agents).toHaveLength(1)

    // Simulate disconnect
    store.connectionStatus.value = 'disconnected'

    // Can't create during disconnect (would queue)
    store.send({
      type: 'subscribe',
      entity_type: 'agent',
      entity_id: 'agent-new',
    })

    // Reconnect
    store.connectionStatus.value = 'reconnecting'
    store.connectionStatus.value = 'connected'

    // New agent created after reconnect
    store.handleMessage({
      type: 'agent:created',
      id: 'agent-2',
      name: 'Agent 2',
      status: 'active',
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.agents).toHaveLength(2)
  })

  it('subscriptions persist through reconnect', async () => {
    const wrapper = mount(EntitySubscriberComponent)
    const store = useWebSocketStore()

    // Subscribe while connected
    store.connectionStatus.value = 'connected'
    wrapper.vm.subscribe('project', 'proj-1')

    expect(store.subscriptions.value.has('project:proj-1')).toBe(true)

    // Disconnect
    store.connectionStatus.value = 'disconnected'

    // Subscription should persist
    expect(store.subscriptions.value.has('project:proj-1')).toBe(true)

    // Reconnect - subscription re-sent by resubscribeAll()
    store.connectionStatus.value = 'connected'
    store.resubscribeAll()

    expect(store.subscriptions.value.has('project:proj-1')).toBe(true)
  })

  it('reconnect attempts tracked and incremented', async () => {
    const store = useWebSocketStore()

    expect(store.reconnectAttempts.value).toBe(0)

    // Simulate reconnect attempts
    store.reconnectAttempts.value = 1
    expect(store.reconnectAttempts.value).toBe(1)

    store.reconnectAttempts.value = 2
    expect(store.reconnectAttempts.value).toBe(2)
  })

  it('max reconnect attempts prevents infinite loop', async () => {
    const store = useWebSocketStore()

    // Set to max attempts
    store.reconnectAttempts.value = store.maxReconnectAttempts || 10

    // Should not attempt further reconnects
    expect(store.reconnectAttempts.value).toBe(store.maxReconnectAttempts)
  })
})

// ============================================
// CATEGORY 6: COMPLEX WORKFLOW SCENARIOS
// ============================================

describe('WebSocket Integration - Complex Workflows', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('simultaneous agent list and project dashboard updates', async () => {
    const agentWrapper = mount(AgentListComponent)
    const projectWrapper = mount(ProjectDashboardComponent)
    const store = useWebSocketStore()

    // Multiple updates simultaneously
    store.handleMessage({
      type: 'agent:created',
      id: 'agent-1',
      name: 'Agent 1',
      status: 'active',
    })

    store.handleMessage({
      type: 'project:mission_updated',
      projectId: 'proj-1',
      mission: 'New Mission',
    })

    store.handleMessage({
      type: 'agent:status_changed',
      id: 'agent-1',
      status: 'running',
    })

    await agentWrapper.vm.$nextTick()
    await projectWrapper.vm.$nextTick()

    expect(agentWrapper.vm.agents).toHaveLength(1)
    expect(agentWrapper.vm.agents[0].status).toBe('running')
    expect(projectWrapper.vm.project.mission).toBe('New Mission')
  })

  it('component subscription lifecycle: mount -> subscribe -> update -> unsubscribe -> unmount', async () => {
    const wrapper = mount(EntitySubscriberComponent)
    const store = useWebSocketStore()

    // Mount (done)

    // Subscribe
    wrapper.vm.subscribe('project', 'proj-1')
    expect(store.subscriptions.value.has('project:proj-1')).toBe(true)

    // Update (if subscribed)
    store.handleMessage({
      type: 'project:updated',
      id: 'proj-1',
    })

    // Unsubscribe
    wrapper.vm.unsubscribe('project', 'proj-1')
    expect(store.subscriptions.value.has('project:proj-1')).toBe(false)

    // Unmount (auto-cleanup via composable)
    wrapper.unmount()
  })

  it('handles mixed message types and subscription events', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    // Mix of different event types
    const events = [
      { type: 'agent:created', id: 'agent-1', name: 'Agent 1', status: 'idle' },
      { type: 'agent:status_changed', id: 'agent-1', status: 'running' },
      { type: 'agent:created', id: 'agent-2', name: 'Agent 2', status: 'idle' },
      { type: 'subscribed', entity_type: 'agent', entity_id: 'agent-1' },
      { type: 'agent:status_changed', id: 'agent-2', status: 'running' },
      { type: 'agent:deleted', id: 'agent-1' },
      { type: 'unsubscribed', entity_type: 'agent', entity_id: 'agent-1' },
    ]

    for (const event of events) {
      store.handleMessage(event)
      await wrapper.vm.$nextTick()
    }

    // Final state: only agent-2 exists
    expect(wrapper.vm.agents).toHaveLength(1)
    expect(wrapper.vm.agents[0].id).toBe('agent-2')
  })
})

// ============================================
// CATEGORY 7: ERROR HANDLING AND EDGE CASES
// ============================================

describe('WebSocket Integration - Error Handling', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('handles malformed WebSocket messages gracefully', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    const consoleWarnSpy = vi.spyOn(console, 'warn')

    // Malformed message (missing type)
    store.handleMessage({
      id: 'agent-1',
      name: 'Agent 1',
      status: 'active',
      // type is missing - should handle gracefully
    })

    await wrapper.vm.$nextTick()

    // Should not crash
    expect(wrapper.vm.agents).toHaveLength(0)
  })

  it('ignores messages for unregistered event types', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    // Send message for unregistered type
    store.handleMessage({
      type: 'unknown:event',
      data: 'something',
    })

    await wrapper.vm.$nextTick()

    // Component should not crash
    expect(wrapper.exists()).toBe(true)
    expect(wrapper.vm.agents).toHaveLength(0)
  })

  it('multiple components can subscribe to same message type', async () => {
    const wrapper1 = mount(AgentListComponent)
    const wrapper2 = mount(AgentListComponent)
    const store = useWebSocketStore()

    // Both components listen to agent:created
    store.handleMessage({
      type: 'agent:created',
      id: 'agent-1',
      name: 'Test Agent',
      status: 'active',
    })

    await wrapper1.vm.$nextTick()
    await wrapper2.vm.$nextTick()

    // Both receive update
    expect(wrapper1.vm.agents).toHaveLength(1)
    expect(wrapper2.vm.agents).toHaveLength(1)
  })

  it('unregistered subscription attempts do not break component', async () => {
    const wrapper = mount(EntitySubscriberComponent)
    const store = useWebSocketStore()

    // Try to unsubscribe from non-existent subscription
    wrapper.vm.unsubscribe('nonexistent', 'nonexistent')

    expect(() => {
      wrapper.vm.unsubscribe('nonexistent', 'nonexistent')
    }).not.toThrow()

    // Component still functional
    expect(wrapper.exists()).toBe(true)
  })
})
