/**
 * Comprehensive tests for useWebSocketV2 composable
 * Tests behavior and lifecycle management via component mounting
 *
 * TDD Focus:
 * - Composable API contract (what components rely on)
 * - Auto-cleanup on unmount (memory leak prevention)
 * - Subscription management
 * - Message handling
 * - Edge cases and error scenarios
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
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
 * Simple component using composable
 */
const BasicComponent = {
  setup() {
    const composable = useWebSocketV2()
    return composable
  },
  template: '<div>Test</div>',
}

/**
 * Component that subscribes and receives updates
 */
const SubscriberComponent = {
  setup() {
    const composable = useWebSocketV2()
    return composable
  },
  template: '<div>Subscriber</div>',
}

/**
 * Component that registers message handlers
 */
const ListenerComponent = {
  setup() {
    const composable = useWebSocketV2()
    const handleCustomEvent = () => {}
    composable.on('custom_event', handleCustomEvent)
    return composable
  },
  template: '<div>Listener</div>',
}

/**
 * Component with connection listener
 */
const ConnectionListenerComponent = {
  setup() {
    const composable = useWebSocketV2()
    composable.onConnectionChange(() => {})
    return composable
  },
  template: '<div>Connection</div>',
}

// ============================================
// CATEGORY 1: BASIC COMPOSABLE API
// ============================================

describe('useWebSocketV2 Composable - Basic API', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('composable returns all required methods and properties', () => {
    const wrapper = mount(BasicComponent)
    const instance = wrapper.vm

    // Methods
    expect(typeof instance.subscribe).toBe('function')
    expect(typeof instance.unsubscribe).toBe('function')
    expect(typeof instance.on).toBe('function')
    expect(typeof instance.off).toBe('function')
    expect(typeof instance.send).toBe('function')
    expect(typeof instance.connect).toBe('function')
    expect(typeof instance.disconnect).toBe('function')
    expect(typeof instance.onConnectionChange).toBe('function')

    // Reactive properties
    expect(instance.isConnected).toBeDefined()
    expect(instance.isConnecting).toBeDefined()
    expect(instance.isReconnecting).toBeDefined()
    expect(instance.isDisconnected).toBeDefined()
    expect(instance.connectionStatus).toBeDefined()
  })

  it('subscribe returns a subscription key string', () => {
    const wrapper = mount(BasicComponent)
    const key = wrapper.vm.subscribe('project', 'proj-1')

    expect(typeof key).toBe('string')
    expect(key).toContain('project')
    expect(key).toContain('proj-1')
  })

  it('multiple components share same store instance', () => {
    const wrapper1 = mount(BasicComponent)
    const wrapper2 = mount(BasicComponent)

    wrapper1.vm.subscribe('project', 'proj-a')
    wrapper2.vm.subscribe('project', 'proj-b')

    const store = useWebSocketStore()
    // Both subscriptions should exist in same store
    expect(store.subscriptions.value.has('project:proj-a')).toBe(true)
    expect(store.subscriptions.value.has('project:proj-b')).toBe(true)
  })
})

// ============================================
// CATEGORY 2: AUTO-CLEANUP ON UNMOUNT
// (CRITICAL - MEMORY LEAK PREVENTION)
// ============================================

describe('useWebSocketV2 Composable - Auto-Cleanup on Unmount', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('auto-cleanup on unmount prevents subscription leaks', () => {
    const store = useWebSocketStore()
    const baseline = store.subscriptions.value.size

    const wrapper = mount(SubscriberComponent)
    wrapper.vm.subscribe('project', 'proj-cleanup-test')

    expect(store.subscriptions.value.has('project:proj-cleanup-test')).toBe(true)

    // Unmount component
    wrapper.unmount()

    // Subscription should be removed
    expect(store.subscriptions.value.has('project:proj-cleanup-test')).toBe(false)
    expect(store.subscriptions.value.size).toBe(baseline)
  })

  it('message handler cleanup on unmount', () => {
    const store = useWebSocketStore()
    const baseline = store.eventHandlers.value.size

    const wrapper = mount(ListenerComponent)

    // Handler should be registered
    expect(store.eventHandlers.value.size).toBeGreaterThan(baseline)

    wrapper.unmount()

    // Handlers cleaned up
    expect(store.eventHandlers.value.size).toBeLessThanOrEqual(baseline)
  })

  it('connection listener cleanup on unmount', () => {
    const store = useWebSocketStore()
    const baseline = store.connectionListeners.value.size

    const wrapper = mount(ConnectionListenerComponent)

    // Listener registered
    expect(store.connectionListeners.value.size).toBeGreaterThan(baseline)

    wrapper.unmount()

    // Listener cleaned up
    expect(store.connectionListeners.value.size).toBe(baseline)
  })

  it('memory leak test: 100 mount/unmount cycles', () => {
    const store = useWebSocketStore()
    const baseline = store.subscriptions.value.size

    for (let i = 0; i < 100; i++) {
      const wrapper = mount(SubscriberComponent)
      wrapper.vm.subscribe('test', `entity-${i}`)
      wrapper.unmount()
    }

    // No memory leak
    expect(store.subscriptions.value.size).toBe(baseline)
  })

  it('memory leak test: 500 mount/unmount cycles with handlers', () => {
    const store = useWebSocketStore()
    const baseline = store.eventHandlers.value.size

    for (let i = 0; i < 500; i++) {
      const wrapper = mount(ListenerComponent)
      wrapper.unmount()
    }

    expect(store.eventHandlers.value.size).toBeLessThanOrEqual(baseline + 1)
  })

  it('memory leak test: 1000 cycles stress test', () => {
    const store = useWebSocketStore()
    const baselineSubs = store.subscriptions.value.size
    const baselineHandlers = store.eventHandlers.value.size

    for (let i = 0; i < 1000; i++) {
      const wrapper = mount(BasicComponent)
      wrapper.vm.subscribe('stress', `item-${i}`)
      wrapper.vm.on('event', () => {})
      wrapper.unmount()
    }

    expect(store.subscriptions.value.size).toBe(baselineSubs)
    expect(store.eventHandlers.value.size).toBeLessThanOrEqual(baselineHandlers + 2)
  })
})

// ============================================
// CATEGORY 3: SUBSCRIPTION MANAGEMENT
// ============================================

describe('useWebSocketV2 Composable - Subscription Management', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('subscribe creates subscription in store', () => {
    const wrapper = mount(SubscriberComponent)
    const store = useWebSocketStore()

    wrapper.vm.subscribe('agent', 'agent-1')

    expect(store.subscriptions.value.has('agent:agent-1')).toBe(true)
  })

  it('unsubscribe removes subscription from store', () => {
    const wrapper = mount(SubscriberComponent)
    const store = useWebSocketStore()

    wrapper.vm.subscribe('agent', 'agent-2')
    expect(store.subscriptions.value.has('agent:agent-2')).toBe(true)

    wrapper.vm.unsubscribe('agent', 'agent-2')
    expect(store.subscriptions.value.has('agent:agent-2')).toBe(false)
  })

  it('subscribeToProject convenience method works', () => {
    const wrapper = mount(SubscriberComponent)
    const store = useWebSocketStore()

    const key = wrapper.vm.subscribeToProject('proj-1')

    expect(key).toBe('project:proj-1')
    expect(store.subscriptions.value.has('project:proj-1')).toBe(true)
  })

  it('subscribeToAgent convenience method works', () => {
    const wrapper = mount(SubscriberComponent)
    const store = useWebSocketStore()

    const key = wrapper.vm.subscribeToAgent('agent-1')

    expect(key).toBe('agent:agent-1')
    expect(store.subscriptions.value.has('agent:agent-1')).toBe(true)
  })

  it('can manage multiple subscriptions', () => {
    const wrapper = mount(SubscriberComponent)
    const store = useWebSocketStore()

    wrapper.vm.subscribe('project', 'p-1')
    wrapper.vm.subscribe('agent', 'a-1')
    wrapper.vm.subscribe('project', 'p-2')

    const count = Array.from(store.subscriptions.value.keys()).length
    expect(count).toBeGreaterThanOrEqual(3)
  })

  it('subscription cleanup on unmount affects only component subscriptions', () => {
    const store = useWebSocketStore()

    const wrapper1 = mount(SubscriberComponent)
    const wrapper2 = mount(SubscriberComponent)

    wrapper1.vm.subscribe('project', 'p-shared')
    wrapper2.vm.subscribe('project', 'p-shared')

    // Both subscribed
    expect(store.subscriptions.value.has('project:p-shared')).toBe(true)

    // Unmount first - shared subscription remains
    wrapper1.unmount()
    expect(store.subscriptions.value.has('project:p-shared')).toBe(true)

    wrapper2.unmount()
  })
})

// ============================================
// CATEGORY 4: MESSAGE HANDLING
// ============================================

describe('useWebSocketV2 Composable - Message Handling', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('on() registers message handler', () => {
    const wrapper = mount(BasicComponent)
    const store = useWebSocketStore()
    const baseline = store.eventHandlers.value.size

    wrapper.vm.on('test_message', () => {})

    expect(store.eventHandlers.value.size).toBeGreaterThan(baseline)
  })

  it('on() returns cleanup function', () => {
    const wrapper = mount(BasicComponent)

    const cleanup = wrapper.vm.on('test', () => {})

    expect(typeof cleanup).toBe('function')
  })

  it('off() removes message handler', () => {
    const wrapper = mount(BasicComponent)
    const store = useWebSocketStore()

    const handler = vi.fn()
    wrapper.vm.on('test', handler)
    expect(store.eventHandlers.value.has('test')).toBe(true)

    wrapper.vm.off('test', handler)
    expect(store.eventHandlers.value.has('test')).toBe(false)
  })

  it('send() queues message when disconnected', () => {
    const wrapper = mount(BasicComponent)
    const store = useWebSocketStore()

    store.connectionStatus.value = 'disconnected'
    const result = wrapper.vm.send({ type: 'test', data: {} })

    expect(result).toBe(false)
    expect(store.messageQueue.value.length).toBeGreaterThan(0)
  })

  it('wildcard handler receives all messages', () => {
    const wrapper = mount(BasicComponent)
    const store = useWebSocketStore()

    wrapper.vm.on('*', () => {})

    expect(store.eventHandlers.value.has('*')).toBe(true)
  })
})

// ============================================
// CATEGORY 5: CONNECTION MANAGEMENT
// ============================================

describe('useWebSocketV2 Composable - Connection Management', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('isConnected reflects connection state', () => {
    const wrapper = mount(BasicComponent)
    const store = useWebSocketStore()

    store.connectionStatus.value = 'disconnected'
    expect(wrapper.vm.isConnected.value).toBe(false)

    store.connectionStatus.value = 'connected'
    expect(wrapper.vm.isConnected.value).toBe(true)
  })

  it('isReconnecting reflects reconnecting state', () => {
    const wrapper = mount(BasicComponent)
    const store = useWebSocketStore()

    store.connectionStatus.value = 'reconnecting'
    expect(wrapper.vm.isReconnecting.value).toBe(true)

    store.connectionStatus.value = 'connected'
    expect(wrapper.vm.isReconnecting.value).toBe(false)
  })

  it('connectionStatus exposes current connection state', () => {
    const wrapper = mount(BasicComponent)
    const store = useWebSocketStore()

    store.connectionStatus.value = 'connecting'
    expect(wrapper.vm.connectionStatus.value).toBe('connecting')
  })

  it('onConnectionChange registers listener', () => {
    const wrapper = mount(BasicComponent)
    const store = useWebSocketStore()
    const baseline = store.connectionListeners.value.size

    wrapper.vm.onConnectionChange(() => {})

    expect(store.connectionListeners.value.size).toBeGreaterThan(baseline)
  })
})

// ============================================
// CATEGORY 6: DEBUG AND INFO
// ============================================

describe('useWebSocketV2 Composable - Debug Methods', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('getConnectionInfo returns connection details', () => {
    const wrapper = mount(BasicComponent)

    const info = wrapper.vm.getConnectionInfo()

    expect(info).toBeDefined()
    expect(info.state).toBeDefined()
    expect(info.clientId).toBeDefined()
    expect(info.messageQueueSize).toBeDefined()
    expect(info.subscriptionsCount).toBeDefined()
  })

  it('getDebugInfo returns debug information', () => {
    const wrapper = mount(BasicComponent)

    const debug = wrapper.vm.getDebugInfo()

    expect(debug).toBeDefined()
    expect(debug.isConnected).toBeDefined()
    expect(debug.subscriptions).toBeDefined()
    expect(Array.isArray(debug.subscriptions)).toBe(true)
  })
})

// ============================================
// CATEGORY 7: EDGE CASES
// ============================================

describe('useWebSocketV2 Composable - Edge Cases', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('rapid mount/unmount cycles do not crash', () => {
    const store = useWebSocketStore()

    expect(() => {
      for (let i = 0; i < 50; i++) {
        const wrapper = mount(BasicComponent)
        wrapper.unmount()
      }
    }).not.toThrow()
  })

  it('unsubscribe from non-existent entity does not throw', () => {
    const wrapper = mount(BasicComponent)

    expect(() => {
      wrapper.vm.unsubscribe('nonexistent', 'nonexistent')
    }).not.toThrow()
  })

  it('off() with non-registered handler does not throw', () => {
    const wrapper = mount(BasicComponent)

    expect(() => {
      wrapper.vm.off('nonexistent', () => {})
    }).not.toThrow()
  })

  it('composable works during disconnected state', () => {
    const wrapper = mount(BasicComponent)
    const store = useWebSocketStore()

    store.connectionStatus.value = 'disconnected'

    expect(() => {
      wrapper.vm.subscribe('test', 'entity')
      wrapper.vm.on('message', () => {})
      wrapper.vm.send({ type: 'test' })
    }).not.toThrow()
  })

  it('handles multiple unsubscribe calls gracefully', () => {
    const wrapper = mount(BasicComponent)

    wrapper.vm.subscribe('test', 'entity')
    wrapper.vm.unsubscribe('test', 'entity')

    expect(() => {
      wrapper.vm.unsubscribe('test', 'entity')
    }).not.toThrow()
  })

  it('cleanup is idempotent', () => {
    const wrapper = mount(BasicComponent)
    const store = useWebSocketStore()

    const baseline = store.subscriptions.value?.size ?? 0

    wrapper.vm.subscribe('test', 'entity')
    wrapper.unmount()

    const afterCleanup = store.subscriptions.value?.size ?? 0
    expect(afterCleanup).toBe(baseline)

    // Multiple unmounts should not cause issues
    expect(() => {
      wrapper.unmount()
    }).not.toThrow()
  })
})
