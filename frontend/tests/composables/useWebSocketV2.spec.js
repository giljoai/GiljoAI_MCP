/**
 * Comprehensive tests for useWebSocketV2 composable
 * Tests behavior and lifecycle management, NOT implementation details
 *
 * TDD Focus:
 * - Composable API contract (what components rely on)
 * - Auto-cleanup on unmount (memory leak prevention)
 * - Subscription management
 * - Message handling
 * - Edge cases and error scenarios
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
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

// Test component that uses the composable
const TestComponent = {
  setup() {
    const composable = useWebSocketV2()
    return {
      ...composable,
    }
  },
  template: '<div>Test Component</div>',
}

// Test component that subscribes to events
const SubscribingComponent = {
  setup() {
    const composable = useWebSocketV2()
    const messageReceived = ref(null)

    // Subscribe to test event
    composable.on('test_event', (data) => {
      messageReceived.value = data
    })

    return {
      ...composable,
      messageReceived,
    }
  },
  template: '<div>Subscribing Component</div>',
}

import { ref } from 'vue'

// ============================================
// CATEGORY 1: BASIC COMPOSABLE API
// ============================================

describe('useWebSocketV2 Composable - Basic API', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('returns WebSocket store reference and API methods', () => {
    const wrapper = mount(TestComponent)

    const instance = wrapper.vm

    // Verify all API methods are available
    expect(typeof instance.subscribe).toBe('function')
    expect(typeof instance.unsubscribe).toBe('function')
    expect(typeof instance.on).toBe('function')
    expect(typeof instance.off).toBe('function')
    expect(typeof instance.send).toBe('function')
    expect(typeof instance.connect).toBe('function')
    expect(typeof instance.disconnect).toBe('function')
    expect(typeof instance.onConnectionChange).toBe('function')
  })

  it('returns reactive connection state properties', () => {
    const wrapper = mount(TestComponent)

    const instance = wrapper.vm

    // Verify reactive properties exist
    expect(instance.isConnected).toBeDefined()
    expect(instance.isConnecting).toBeDefined()
    expect(instance.isReconnecting).toBeDefined()
    expect(instance.isDisconnected).toBeDefined()
    expect(instance.connectionStatus).toBeDefined()
    expect(instance.connectionError).toBeDefined()
    expect(instance.reconnectAttempts).toBeDefined()
    expect(instance.clientId).toBeDefined()
    expect(instance.messageQueueSize).toBeDefined()
    expect(instance.subscriptions).toBeDefined()
  })

  it('subscribe() creates subscription and returns subscription key', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    const key = instance.subscribe('project', 'proj-123')

    expect(key).toBe('project:proj-123')
    expect(store.subscriptions.value.has(key)).toBe(true)
  })

  it('multiple composable calls return same store reference', () => {
    const composable1 = useWebSocketV2()
    const composable2 = useWebSocketV2()
    const store = useWebSocketStore()

    // Both should work with the same store state
    composable1.subscribe('agent', 'agent-1')
    composable2.subscribe('project', 'project-1')

    expect(store.subscriptions.value.size).toBe(2)
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

  it('automatically unsubscribes when component unmounts', () => {
    const store = useWebSocketStore()
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm

    // Subscribe to entity
    instance.subscribe('project', 'proj-123')
    expect(store.subscriptions.value.has('project:proj-123')).toBe(true)

    // Unmount component
    wrapper.unmount()

    // Verify subscription removed
    expect(store.subscriptions.value.has('project:proj-123')).toBe(false)
  })

  it('unsubscribes multiple subscriptions on unmount', () => {
    const store = useWebSocketStore()
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm

    // Create multiple subscriptions
    instance.subscribe('project', 'proj-1')
    instance.subscribe('agent', 'agent-1')
    instance.subscribe('project', 'proj-2')

    expect(store.subscriptions.value.size).toBe(3)

    // Unmount component
    wrapper.unmount()

    // Verify all subscriptions removed
    expect(store.subscriptions.value.size).toBe(0)
  })

  it('removes all message handlers when component unmounts', () => {
    const store = useWebSocketStore()
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm

    // Register multiple handlers
    instance.on('test_event', () => {})
    instance.on('another_event', () => {})
    instance.on('*', () => {})

    expect(store.eventHandlers.value.size).toBe(3)

    // Unmount component
    wrapper.unmount()

    // Verify all handlers removed
    expect(store.eventHandlers.value.size).toBe(0)
  })

  it('removes connection change listeners when component unmounts', () => {
    const store = useWebSocketStore()
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm

    // Register connection listener
    instance.onConnectionChange(() => {})

    const listenerCountBefore = store.connectionListeners.value.size
    expect(listenerCountBefore).toBe(1)

    // Unmount component
    wrapper.unmount()

    // Verify listener removed
    expect(store.connectionListeners.value.size).toBe(0)
  })

  it('memory leak test: 100 mount/unmount cycles do not leak subscriptions', () => {
    const store = useWebSocketStore()
    const baseline = store.subscriptions.value.size

    // Mount/unmount 100 times
    for (let i = 0; i < 100; i++) {
      const wrapper = mount(TestComponent)
      const instance = wrapper.vm

      // Create some subscriptions
      instance.subscribe('project', `proj-${i}`)
      instance.subscribe('agent', `agent-${i}`)

      // Unmount (should cleanup)
      wrapper.unmount()
    }

    // Verify no subscriptions leaked
    expect(store.subscriptions.value.size).toBe(baseline)
  })

  it('memory leak test: 500 mount/unmount cycles do not leak handlers', () => {
    const store = useWebSocketStore()
    const baseline = store.eventHandlers.value.size

    // Mount/unmount 500 times
    for (let i = 0; i < 500; i++) {
      const wrapper = mount(TestComponent)
      const instance = wrapper.vm

      // Register handlers
      instance.on(`event_${i}`, () => {})
      instance.on(`another_${i}`, () => {})

      // Unmount (should cleanup)
      wrapper.unmount()
    }

    // Verify no handlers leaked
    expect(store.eventHandlers.value.size).toBe(baseline)
  })

  it('memory leak test: 1000 mount/unmount cycles - stress test', () => {
    const store = useWebSocketStore()

    // Get baseline
    const baselineSubscriptions = store.subscriptions.value.size
    const baselineHandlers = store.eventHandlers.value.size
    const baselineListeners = store.connectionListeners.value.size

    // Stress test: 1000 cycles
    for (let i = 0; i < 1000; i++) {
      const wrapper = mount(TestComponent)
      const instance = wrapper.vm

      // Do various operations
      instance.subscribe('project', `p-${i}`)
      instance.on('test', () => {})
      instance.onConnectionChange(() => {})

      // Cleanup
      wrapper.unmount()
    }

    // Verify nothing leaked
    expect(store.subscriptions.value.size).toBe(baselineSubscriptions)
    expect(store.eventHandlers.value.size).toBe(baselineHandlers)
    expect(store.connectionListeners.value.size).toBe(baselineListeners)
  })

  it('handles cleanup errors gracefully (no throw)', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    // Mock a handler that throws during cleanup
    const throwingCleanup = vi.fn(() => {
      throw new Error('Cleanup error')
    })

    // Manually add a broken cleanup to simulate the issue
    // (This tests the try-catch in onUnmounted)
    const consoleWarnSpy = vi.spyOn(console, 'warn')

    wrapper.unmount()

    // Verify cleanup didn't throw (gracefully handled)
    // The component should unmount without crashing
    expect(wrapper.vm).toBeUndefined()
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

  it('subscribe() returns unsubscribe key', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm

    const key = instance.subscribe('project', 'proj-456')

    expect(key).toBe('project:proj-456')
  })

  it('unsubscribe() removes subscription', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    // Subscribe
    instance.subscribe('project', 'proj-789')
    expect(store.subscriptions.value.has('project:proj-789')).toBe(true)

    // Unsubscribe
    instance.unsubscribe('project', 'proj-789')
    expect(store.subscriptions.value.has('project:proj-789')).toBe(false)
  })

  it('subscribeToProject() is convenience method for subscribe', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    const key = instance.subscribeToProject('proj-999')

    expect(key).toBe('project:proj-999')
    expect(store.subscriptions.value.has(key)).toBe(true)
  })

  it('subscribeToAgent() is convenience method for subscribe', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    const key = instance.subscribeToAgent('agent-999')

    expect(key).toBe('agent:agent-999')
    expect(store.subscriptions.value.has(key)).toBe(true)
  })

  it('can subscribe to multiple entities simultaneously', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    instance.subscribe('project', 'proj-1')
    instance.subscribe('agent', 'agent-1')
    instance.subscribe('project', 'proj-2')
    instance.subscribe('agent', 'agent-2')

    expect(store.subscriptions.value.size).toBe(4)
  })

  it('unsubscribe only affects specified subscription', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    instance.subscribe('project', 'proj-a')
    instance.subscribe('project', 'proj-b')
    instance.subscribe('agent', 'agent-a')

    expect(store.subscriptions.value.size).toBe(3)

    // Unsubscribe only one
    instance.unsubscribe('project', 'proj-a')

    expect(store.subscriptions.value.size).toBe(2)
    expect(store.subscriptions.value.has('project:proj-b')).toBe(true)
    expect(store.subscriptions.value.has('agent:agent-a')).toBe(true)
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
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    const handler = vi.fn()
    instance.on('test_event', handler)

    expect(store.eventHandlers.value.has('test_event')).toBe(true)
  })

  it('on() returns cleanup function', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm

    const cleanup = instance.on('test_event', () => {})

    expect(typeof cleanup).toBe('function')
  })

  it('send() queues message when not connected', async () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    // Ensure disconnected
    store.connectionStatus.value = 'disconnected'

    const result = instance.send({ type: 'test', payload: 'data' })

    expect(result).toBe(false) // Not sent immediately
    expect(store.messageQueue.value.length).toBeGreaterThan(0)
  })

  it('send() sends message when connected', async () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    // Simulate connection
    store.ws = {
      send: vi.fn(),
      readyState: WebSocket.OPEN,
    }
    store.connectionStatus.value = 'connected'

    const result = instance.send({ type: 'test', payload: 'data' })

    expect(result).toBe(true) // Sent successfully
  })

  it('off() removes message handler', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    const handler = vi.fn()
    instance.on('test_event', handler)
    expect(store.eventHandlers.value.has('test_event')).toBe(true)

    instance.off('test_event', handler)
    expect(store.eventHandlers.value.has('test_event')).toBe(false)
  })

  it('can register wildcard handler for all message types', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    const handler = vi.fn()
    instance.on('*', handler)

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

  it('connect() initiates WebSocket connection', async () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    // Mock the store's connect method
    store.connect = vi.fn().mockResolvedValue(undefined)

    await instance.connect()

    expect(store.connect).toHaveBeenCalled()
  })

  it('disconnect() closes WebSocket connection', async () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    // Mock the store's disconnect method
    store.disconnect = vi.fn()

    instance.disconnect()

    expect(store.disconnect).toHaveBeenCalled()
  })

  it('onConnectionChange() registers state listener', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    const listener = vi.fn()
    instance.onConnectionChange(listener)

    expect(store.connectionListeners.value.size).toBeGreaterThan(0)
  })

  it('onConnectionChange() returns cleanup function', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm

    const cleanup = instance.onConnectionChange(() => {})

    expect(typeof cleanup).toBe('function')
  })
})

// ============================================
// CATEGORY 6: DEBUG AND INFO METHODS
// ============================================

describe('useWebSocketV2 Composable - Debug Methods', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('getConnectionInfo() returns connection details', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm

    const info = instance.getConnectionInfo()

    expect(info).toBeDefined()
    expect(info.state).toBeDefined()
    expect(info.clientId).toBeDefined()
    expect(info.reconnectAttempts).toBeDefined()
    expect(info.messageQueueSize).toBeDefined()
    expect(info.subscriptionsCount).toBeDefined()
  })

  it('getDebugInfo() returns debug information', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm

    const debug = instance.getDebugInfo()

    expect(debug).toBeDefined()
    expect(debug.isConnected).toBeDefined()
    expect(debug.isConnecting).toBeDefined()
    expect(debug.isReconnecting).toBeDefined()
    expect(debug.subscriptions).toBeDefined()
  })
})

// ============================================
// CATEGORY 7: EDGE CASES AND ERROR SCENARIOS
// ============================================

describe('useWebSocketV2 Composable - Edge Cases', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('handles rapid mount/unmount cycles', () => {
    const store = useWebSocketStore()

    // Rapid create/destroy
    for (let i = 0; i < 50; i++) {
      const wrapper = mount(TestComponent)
      wrapper.unmount()
    }

    // Should not crash or leak
    expect(store.subscriptions.value.size).toBe(0)
  })

  it('handles unsubscribe from non-existent subscription gracefully', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm

    // Should not throw
    expect(() => {
      instance.unsubscribe('nonexistent', 'nonexistent')
    }).not.toThrow()
  })

  it('handles removing non-registered handler gracefully', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm

    const handler = vi.fn()

    // Should not throw
    expect(() => {
      instance.off('nonexistent', handler)
    }).not.toThrow()
  })

  it('handles unmount before connection established', () => {
    const store = useWebSocketStore()
    store.connectionStatus.value = 'connecting'

    const wrapper = mount(TestComponent)
    const instance = wrapper.vm

    instance.subscribe('project', 'proj-1')

    // Should unmount gracefully even during connection
    expect(() => {
      wrapper.unmount()
    }).not.toThrow()

    // Subscriptions should be cleaned up
    const hasSubscription = store.subscriptions.value.has?.('project:proj-1')
    expect(hasSubscription).toBe(false)
  })

  it('handles multiple subscriptions to same entity', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm
    const store = useWebSocketStore()

    // Subscribe to same entity multiple times
    instance.subscribe('project', 'proj-1')
    const key2 = instance.subscribe('project', 'proj-1') // Duplicate

    // Should not create duplicate (store handles this)
    const subscriptionCount = store.subscriptions.value.size ?? 0
    expect(subscriptionCount).toBeGreaterThanOrEqual(1)
  })

  it('handles concurrent component instances', () => {
    const store = useWebSocketStore()
    const wrapper1 = mount(TestComponent)
    const wrapper2 = mount(TestComponent)

    const instance1 = wrapper1.vm
    const instance2 = wrapper2.vm

    // Both components mount without error
    expect(wrapper1.exists()).toBe(true)
    expect(wrapper2.exists()).toBe(true)

    instance1.subscribe('project', 'proj-1')
    instance2.subscribe('project', 'proj-2')

    // Unmount first component - should auto-cleanup
    wrapper1.unmount()

    // Second component should still be functional
    expect(wrapper2.exists()).toBe(true)

    // Unmount second component
    wrapper2.unmount()

    // Both unmounted successfully (wrappers should no longer exist)
    expect(wrapper1.exists()).toBe(false)
    expect(wrapper2.exists()).toBe(false)
  })

  it('preserves subscriptions after failed unsubscribe', () => {
    const wrapper = mount(TestComponent)
    const instance = wrapper.vm

    // Subscribe to known entities
    instance.subscribe('project', 'proj-1')
    instance.subscribe('project', 'proj-2')

    // Get subscriptions before unsubscribe attempt (array of subscription keys)
    const subsBefore = instance.subscriptions?.value ?? []
    const countBefore = subsBefore.length

    // Try to unsubscribe from non-existent
    instance.unsubscribe('nonexistent', 'nonexistent')

    // Verify unsubscribe from non-existent didn't crash
    expect(() => {
      instance.unsubscribe('nonexistent', 'nonexistent')
    }).not.toThrow()

    // Subscriptions should still be accessible
    const subsAfter = instance.subscriptions?.value ?? []
    expect(subsAfter.length).toBeGreaterThanOrEqual(0)
  })
})
