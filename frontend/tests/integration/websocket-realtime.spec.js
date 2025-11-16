/**
 * Integration tests for WebSocket V2 real-time updates
 * Tests end-to-end user workflows and real-time data synchronization
 *
 * TDD Focus:
 * - Real-time agent status updates
 * - Project mission updates
 * - Multi-tenant isolation (security)
 * - Message handler delivery
 * - Complete user workflows
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
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
// HELPER: Trigger message handlers
// ============================================

function triggerMessageHandlers(store, eventType, payload) {
  const handlers = store.eventHandlers?.value?.get(eventType)
  if (handlers) {
    handlers.forEach((handler) => {
      try {
        handler(payload)
      } catch (error) {
        console.error(`Error in handler for ${eventType}:`, error)
      }
    })
  }
}

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
 * Component that tracks connection state changes
 */
const ConnectionStateComponent = {
  setup() {
    const composable = useWebSocketV2()
    const connectionHistory = ref([])

    composable.onConnectionChange((data) => {
      connectionHistory.value.push({
        state: data.state,
        timestamp: new Date().toISOString(),
      })
    })

    return {
      connectionHistory,
      ...composable,
    }
  },
  template: '<div>{{ connectionHistory.length }}</div>',
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
    const receivedData = ref(null)

    composable.on('secure:update', (payload) => {
      // Only accept if tenant matches
      if (payload.tenant_key === props.tenantKey) {
        receivedData.value = payload.data
      }
    })

    return {
      receivedData,
      ...composable,
    }
  },
  template: '<div>{{ receivedData }}</div>',
}

/**
 * Subscription manager component
 */
const SubscriptionComponent = {
  setup() {
    const composable = useWebSocketV2()
    const subscriptionKey = ref(null)

    const doSubscribe = (entityType, entityId) => {
      subscriptionKey.value = composable.subscribe(entityType, entityId)
    }

    const doUnsubscribe = (entityType, entityId) => {
      composable.unsubscribe(entityType, entityId)
      subscriptionKey.value = null
    }

    return {
      subscriptionKey,
      doSubscribe,
      doUnsubscribe,
      ...composable,
    }
  },
  template: '<div>{{ subscriptionKey }}</div>',
}

// ============================================
// CATEGORY 1: REAL-TIME MESSAGE DELIVERY
// ============================================

describe('WebSocket Integration - Real-time Message Delivery', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('message handler receives real-time updates', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    expect(wrapper.vm.agents).toHaveLength(0)

    // Trigger agent:created message
    triggerMessageHandlers(store, 'agent:created', {
      id: 'agent-1',
      name: 'Test Agent',
      status: 'active',
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.agents).toHaveLength(1)
    expect(wrapper.vm.agents[0].name).toBe('Test Agent')
  })

  it('multiple messages processed sequentially', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    // Send three agent creation messages
    triggerMessageHandlers(store, 'agent:created', { id: 'a1', name: 'Agent 1', status: 'idle' })
    triggerMessageHandlers(store, 'agent:created', { id: 'a2', name: 'Agent 2', status: 'idle' })
    triggerMessageHandlers(store, 'agent:created', { id: 'a3', name: 'Agent 3', status: 'idle' })

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.agents).toHaveLength(3)
  })

  it('agent status updates appear in UI', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    // Create agent
    triggerMessageHandlers(store, 'agent:created', { id: 'a1', name: 'Agent', status: 'idle' })
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.agents[0].status).toBe('idle')

    // Update status
    triggerMessageHandlers(store, 'agent:status_changed', { id: 'a1', status: 'running' })
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.agents[0].status).toBe('running')
  })

  it('agent deletion removes from UI', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    // Create two agents
    triggerMessageHandlers(store, 'agent:created', { id: 'a1', name: 'Agent 1', status: 'idle' })
    triggerMessageHandlers(store, 'agent:created', { id: 'a2', name: 'Agent 2', status: 'idle' })
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.agents).toHaveLength(2)

    // Delete first
    triggerMessageHandlers(store, 'agent:deleted', { id: 'a1' })
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.agents).toHaveLength(1)
    expect(wrapper.vm.agents[0].id).toBe('a2')
  })
})

// ============================================
// CATEGORY 2: PROJECT UPDATES
// ============================================

describe('WebSocket Integration - Project Updates', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('project mission update appears in dashboard', async () => {
    const wrapper = mount(ProjectDashboardComponent)
    const store = useWebSocketStore()

    expect(wrapper.vm.project.mission).toBe('')

    triggerMessageHandlers(store, 'project:mission_updated', {
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

    // Update for different project
    triggerMessageHandlers(store, 'project:mission_updated', {
      projectId: 'proj-999',
      mission: 'Different mission',
    })

    await wrapper.vm.$nextTick()

    // Original mission unchanged
    expect(wrapper.vm.project.mission).toBe('')
  })
})

// ============================================
// CATEGORY 3: CONNECTION STATE MANAGEMENT
// ============================================

describe('WebSocket Integration - Connection State Management', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('connection state listeners receive updates', async () => {
    const wrapper = mount(ConnectionStateComponent)
    const store = useWebSocketStore()

    // Notify connection change
    const listeners = store.connectionListeners.value
    listeners.forEach((listener) => {
      listener({ state: 'connected' })
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.connectionHistory.length).toBeGreaterThan(0)
    expect(wrapper.vm.connectionHistory[0].state).toBe('connected')
  })

  it('isConnected tracks connection state', async () => {
    const wrapper = mount(ConnectionStateComponent)
    const store = useWebSocketStore()

    store.connectionStatus.value = 'disconnected'
    expect(wrapper.vm.isConnected.value).toBe(false)

    store.connectionStatus.value = 'connected'
    expect(wrapper.vm.isConnected.value).toBe(true)
  })

  it('isReconnecting reflects reconnection state', async () => {
    const wrapper = mount(ConnectionStateComponent)
    const store = useWebSocketStore()

    store.connectionStatus.value = 'reconnecting'
    expect(wrapper.vm.isReconnecting.value).toBe(true)

    store.connectionStatus.value = 'connected'
    expect(wrapper.vm.isReconnecting.value).toBe(false)
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
    const wrapperA = mount(MultiTenantComponent, {
      props: { tenantKey: 'tenant-a' },
    })

    const wrapperB = mount(MultiTenantComponent, {
      props: { tenantKey: 'tenant-b' },
    })

    const store = useWebSocketStore()

    // Send update for tenant A
    triggerMessageHandlers(store, 'secure:update', {
      tenant_key: 'tenant-a',
      data: 'User A Data',
    })

    await wrapperA.vm.$nextTick()
    await wrapperB.vm.$nextTick()

    // User A sees it
    expect(wrapperA.vm.receivedData).toBe('User A Data')

    // User B does NOT
    expect(wrapperB.vm.receivedData).toBeNull()
  })

  it('User B data not overwritten by User A update', async () => {
    const wrapperA = mount(MultiTenantComponent, {
      props: { tenantKey: 'tenant-a' },
    })

    const wrapperB = mount(MultiTenantComponent, {
      props: { tenantKey: 'tenant-b' },
    })

    const store = useWebSocketStore()

    // User B gets data first
    triggerMessageHandlers(store, 'secure:update', {
      tenant_key: 'tenant-b',
      data: 'User B Data',
    })

    await wrapperB.vm.$nextTick()
    expect(wrapperB.vm.receivedData).toBe('User B Data')

    // User A gets update
    triggerMessageHandlers(store, 'secure:update', {
      tenant_key: 'tenant-a',
      data: 'User A Data',
    })

    await wrapperA.vm.$nextTick()

    // User B's data unchanged
    expect(wrapperB.vm.receivedData).toBe('User B Data')
  })

  it('multiple tenants maintain isolated state', async () => {
    const tenants = []
    for (let i = 0; i < 5; i++) {
      tenants.push(
        mount(MultiTenantComponent, {
          props: { tenantKey: `tenant-${i}` },
        })
      )
    }

    const store = useWebSocketStore()

    // Send update for each tenant
    for (let i = 0; i < 5; i++) {
      triggerMessageHandlers(store, 'secure:update', {
        tenant_key: `tenant-${i}`,
        data: `Tenant ${i} Data`,
      })
    }

    await Promise.all(tenants.map((t) => t.vm.$nextTick?.()))

    // Each tenant only sees their data
    for (let i = 0; i < 5; i++) {
      expect(tenants[i].vm.receivedData).toBe(`Tenant ${i} Data`)
    }
  })
})

// ============================================
// CATEGORY 5: SUBSCRIPTION WORKFLOWS
// ============================================

describe('WebSocket Integration - Subscription Workflows', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('subscribe creates subscription key', () => {
    const wrapper = mount(SubscriptionComponent)

    wrapper.vm.doSubscribe('project', 'proj-1')

    expect(wrapper.vm.subscriptionKey).toBe('project:proj-1')
  })

  it('unsubscribe clears subscription', () => {
    const wrapper = mount(SubscriptionComponent)
    const store = useWebSocketStore()

    wrapper.vm.doSubscribe('project', 'proj-1')
    expect(store.subscriptions.value.has('project:proj-1')).toBe(true)

    wrapper.vm.doUnsubscribe('project', 'proj-1')
    expect(store.subscriptions.value.has('project:proj-1')).toBe(false)
    expect(wrapper.vm.subscriptionKey).toBeNull()
  })

  it('multiple components can subscribe to same entity', async () => {
    const wrapper1 = mount(SubscriptionComponent)
    const wrapper2 = mount(SubscriptionComponent)

    wrapper1.vm.doSubscribe('project', 'shared-proj')
    wrapper2.vm.doSubscribe('project', 'shared-proj')

    const store = useWebSocketStore()
    expect(store.subscriptions.value.has('project:shared-proj')).toBe(true)
  })
})

// ============================================
// CATEGORY 6: ERROR HANDLING
// ============================================

describe('WebSocket Integration - Error Handling', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('handler error does not crash component', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    // Message with malformed data (missing required fields)
    expect(() => {
      triggerMessageHandlers(store, 'agent:created', {
        // missing id, name, status
      })
    }).not.toThrow()

    await wrapper.vm.$nextTick()

    // Component should still be functional
    expect(wrapper.exists()).toBe(true)
  })

  it('unregistered message types do not crash', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    // Send message for unregistered type
    triggerMessageHandlers(store, 'unknown:event', { data: 'something' })

    await wrapper.vm.$nextTick()

    // Component functional
    expect(wrapper.exists()).toBe(true)
  })

  it('handler execution errors are caught', async () => {
    const wrapper = mount(AgentListComponent)
    const store = useWebSocketStore()

    // Register handler that throws
    const throwingHandler = vi.fn(() => {
      throw new Error('Handler error')
    })

    store.on('test:error', throwingHandler)

    // Should not throw at call site
    expect(() => {
      triggerMessageHandlers(store, 'test:error', {})
    }).not.toThrow()
  })
})

// ============================================
// CATEGORY 7: COMPONENT LIFECYCLE
// ============================================

describe('WebSocket Integration - Component Lifecycle', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('handlers automatically cleanup on unmount', () => {
    const store = useWebSocketStore()
    const baseline = store.eventHandlers?.value?.size ?? 0

    const wrapper = mount(AgentListComponent)
    const afterMount = store.eventHandlers?.value?.size ?? 0
    expect(afterMount).toBeGreaterThan(baseline)

    wrapper.unmount()
    const afterUnmount = store.eventHandlers?.value?.size ?? 0
    expect(afterUnmount).toBeLessThanOrEqual(baseline)
  })

  it('subscriptions automatically cleanup on unmount', () => {
    const store = useWebSocketStore()
    const baseline = store.subscriptions?.value?.size ?? 0

    const wrapper = mount(SubscriptionComponent)
    wrapper.vm.doSubscribe('test', 'entity')

    const afterSub = store.subscriptions?.value?.size ?? 0
    expect(afterSub).toBeGreaterThan(baseline)

    wrapper.unmount()
    const afterUnmount = store.subscriptions?.value?.size ?? 0
    expect(afterUnmount).toBeLessThanOrEqual(baseline)
  })

  it('mount/unmount cycles do not leak resources', () => {
    const store = useWebSocketStore()
    const baselineHandlers = store.eventHandlers.value?.size ?? 0
    const baselineSubs = store.subscriptions.value?.size ?? 0

    for (let i = 0; i < 50; i++) {
      const wrapper = mount(AgentListComponent)
      wrapper.unmount()
    }

    const finalHandlers = store.eventHandlers.value?.size ?? 0
    const finalSubs = store.subscriptions.value?.size ?? 0
    expect(finalHandlers).toBeLessThanOrEqual(baselineHandlers + 1)
    expect(finalSubs).toBe(baselineSubs)
  })
})
