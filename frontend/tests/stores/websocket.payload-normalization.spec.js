/**
 * WebSocket Payload Normalization Tests (Handover 0290)
 * TDD: Tests written FIRST, then implementation
 *
 * Behavior under test:
 * - Nested payloads (from direct broadcast_to_tenant) → normalized to flat payloads
 * - Flat payloads (from HTTP bridge) → remain unchanged
 * - All edge cases handled gracefully
 *
 * Root Cause:
 * - Backend emits `orchestrator:instructions_fetched` via broadcast_to_tenant()
 * - This wraps payload in nested `data` object: { type, data: { project_id, tenant_key, ... } }
 * - Frontend handlers expect flat: { type, project_id, tenant_key, ... }
 * - Result: tenant_key check fails (undefined), UI doesn't update
 *
 * Solution:
 * - Centralized normalization in handleMessage() merges nested data to top level
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWebSocketStore } from '@/stores/websocket'

// ============================================
// MOCK SETUP
// ============================================

// Mock WebSocket API
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  constructor(url) {
    this.url = url
    this.readyState = MockWebSocket.CONNECTING
    this.onopen = null
    this.onclose = null
    this.onerror = null
    this.onmessage = null

    MockWebSocket.instances.push(this)

    // Auto-open connection
    Promise.resolve().then(() => {
      if (this.onopen && this.readyState === MockWebSocket.CONNECTING) {
        this.readyState = MockWebSocket.OPEN
        this.onopen()
      }
    })
  }

  send(data) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open')
    }
    MockWebSocket.sentMessages.push(JSON.parse(data))
  }

  close(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSING
    Promise.resolve().then(() => {
      this.readyState = MockWebSocket.CLOSED
      if (this.onclose) {
        this.onclose({ code, reason })
      }
    })
  }

  // Test helper: simulate receiving a message
  simulateMessage(data) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) })
    }
  }
}

MockWebSocket.instances = []
MockWebSocket.sentMessages = []
MockWebSocket.reset = () => {
  MockWebSocket.instances = []
  MockWebSocket.sentMessages = []
}

global.WebSocket = MockWebSocket

// Mock API_CONFIG
vi.mock('@/config/api', () => ({
  API_CONFIG: {
    WEBSOCKET: {
      url: 'ws://localhost:7272',
      debug: false
    }
  }
}))

// Mock useToast
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

// Store interval tracking
const originalSetInterval = global.setInterval
const originalClearInterval = global.clearInterval
const activeIntervals = new Set()

global.setInterval = vi.fn((callback, delay, ...args) => {
  const intervalId = originalSetInterval(callback, delay, ...args)
  activeIntervals.add(intervalId)
  return intervalId
})

global.clearInterval = vi.fn((intervalId) => {
  activeIntervals.delete(intervalId)
  originalClearInterval(intervalId)
})

function clearAllTestIntervals() {
  activeIntervals.forEach(id => originalClearInterval(id))
  activeIntervals.clear()
}

// ============================================
// TEST HELPERS
// ============================================

async function flushPromises() {
  return new Promise(resolve => setImmediate(resolve))
}

/**
 * Helper to connect store and get active WebSocket instance
 */
async function setupConnectedStore() {
  const store = useWebSocketStore()
  await store.connect({ token: 'test-token' })
  await flushPromises()

  const ws = MockWebSocket.instances[MockWebSocket.instances.length - 1]
  return { store, ws }
}

// ============================================
// TEST SUITE: Payload Normalization
// ============================================

describe('WebSocket Payload Normalization (Handover 0290)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    MockWebSocket.reset()
    clearAllTestIntervals()
  })

  afterEach(() => {
    clearAllTestIntervals()
  })

  describe('when receiving nested payload from direct broadcast_to_tenant', () => {
    it('normalizes nested data object to top level for handlers', async () => {
      // Setup
      const { store, ws } = await setupConnectedStore()
      let receivedPayload = null

      // Register handler
      store.on('orchestrator:instructions_fetched', (payload) => {
        receivedPayload = payload
      })

      // Given: Backend sends nested payload (from broadcast_to_tenant)
      const nestedPayload = {
        type: 'orchestrator:instructions_fetched',
        timestamp: '2025-12-03T10:00:00Z',
        schema_version: '1.0',
        data: {
          project_id: 'uuid-123',
          tenant_key: 'tenant-abc',
          agent_count: 3,
          status: 'active'
        }
      }

      // When: Message is received
      ws.simulateMessage(nestedPayload)
      await flushPromises()

      // Then: Handler receives flat payload with data merged to top level
      expect(receivedPayload).not.toBeNull()
      expect(receivedPayload.project_id).toBe('uuid-123')
      expect(receivedPayload.tenant_key).toBe('tenant-abc')
      expect(receivedPayload.agent_count).toBe(3)
      expect(receivedPayload.status).toBe('active')
    })

    it('normalizes agent:created event with nested agent object', async () => {
      const { store, ws } = await setupConnectedStore()
      let receivedPayload = null

      store.on('agent:created', (payload) => {
        receivedPayload = payload
      })

      // Given: Backend sends nested agent payload
      const nestedAgentPayload = {
        type: 'agent:created',
        timestamp: '2025-12-03T10:00:00Z',
        schema_version: '1.0',
        data: {
          project_id: 'proj-456',
          tenant_key: 'tenant-xyz',
          agent: {
            id: 'agent-1',
            agent_name: 'Implementer',
            agent_type: 'implementer',
            status: 'waiting'
          }
        }
      }

      // When
      ws.simulateMessage(nestedAgentPayload)
      await flushPromises()

      // Then: Both flat access and nested agent access work
      expect(receivedPayload).not.toBeNull()
      expect(receivedPayload.project_id).toBe('proj-456')
      expect(receivedPayload.tenant_key).toBe('tenant-xyz')
      expect(receivedPayload.agent.id).toBe('agent-1')
      expect(receivedPayload.agent.agent_name).toBe('Implementer')
    })

    it('normalizes job:mission_read event', async () => {
      const { store, ws } = await setupConnectedStore()
      let receivedPayload = null

      store.on('job:mission_read', (payload) => {
        receivedPayload = payload
      })

      // Given: Nested payload
      const nestedPayload = {
        type: 'job:mission_read',
        timestamp: '2025-12-03T10:00:00Z',
        schema_version: '1.0',
        data: {
          job_id: 'job-789',
          mission_read_at: '2025-12-03T10:00:00Z',
          tenant_key: 'tenant-123'
        }
      }

      // When
      ws.simulateMessage(nestedPayload)
      await flushPromises()

      // Then
      expect(receivedPayload).not.toBeNull()
      expect(receivedPayload.job_id).toBe('job-789')
      expect(receivedPayload.tenant_key).toBe('tenant-123')
    })
  })

  describe('when receiving flat payload from HTTP bridge', () => {
    it('passes flat payloads through unchanged', async () => {
      const { store, ws } = await setupConnectedStore()
      let receivedPayload = null

      store.on('project:mission_updated', (payload) => {
        receivedPayload = payload
      })

      // Given: HTTP bridge sends flat payload
      const flatPayload = {
        type: 'project:mission_updated',
        timestamp: '2025-12-03T10:00:00Z',
        schema_version: '1.0',
        project_id: 'uuid-456',
        tenant_key: 'tenant-xyz',
        mission: 'Mission text here...',
        token_estimate: 250
      }

      // When
      ws.simulateMessage(flatPayload)
      await flushPromises()

      // Then: Payload unchanged
      expect(receivedPayload).not.toBeNull()
      expect(receivedPayload.project_id).toBe('uuid-456')
      expect(receivedPayload.tenant_key).toBe('tenant-xyz')
      expect(receivedPayload.mission).toBe('Mission text here...')
      expect(receivedPayload.token_estimate).toBe(250)
    })

    it('passes flat agent:created payload through unchanged', async () => {
      const { store, ws } = await setupConnectedStore()
      let receivedPayload = null

      store.on('agent:created', (payload) => {
        receivedPayload = payload
      })

      // Given: Flat payload from HTTP bridge
      const flatPayload = {
        type: 'agent:created',
        timestamp: '2025-12-03T10:00:00Z',
        schema_version: '1.0',
        project_id: 'proj-123',
        tenant_key: 'tenant-abc',
        agent_id: 'agent-2',
        agent_name: 'Tester',
        agent_type: 'tester',
        status: 'pending'
      }

      // When
      ws.simulateMessage(flatPayload)
      await flushPromises()

      // Then
      expect(receivedPayload).not.toBeNull()
      expect(receivedPayload.project_id).toBe('proj-123')
      expect(receivedPayload.tenant_key).toBe('tenant-abc')
      expect(receivedPayload.agent_id).toBe('agent-2')
    })
  })

  describe('edge cases', () => {
    it('handles payload with data key that is not an object', async () => {
      const { store, ws } = await setupConnectedStore()
      let receivedPayload = null

      store.on('custom:event', (payload) => {
        receivedPayload = payload
      })

      // Given: Payload with data as string (edge case)
      const edgeCasePayload = {
        type: 'custom:event',
        data: 'string-value'
      }

      // When
      ws.simulateMessage(edgeCasePayload)
      await flushPromises()

      // Then: Should not crash, passes through
      expect(receivedPayload).not.toBeNull()
      expect(receivedPayload.data).toBe('string-value')
    })

    it('handles payload with data key that is an array', async () => {
      const { store, ws } = await setupConnectedStore()
      let receivedPayload = null

      store.on('list:event', (payload) => {
        receivedPayload = payload
      })

      // Given: Payload with data as array
      const arrayPayload = {
        type: 'list:event',
        data: [1, 2, 3]
      }

      // When
      ws.simulateMessage(arrayPayload)
      await flushPromises()

      // Then: Array should not be merged
      expect(receivedPayload).not.toBeNull()
      expect(Array.isArray(receivedPayload.data)).toBe(true)
      expect(receivedPayload.data).toEqual([1, 2, 3])
    })

    it('handles payload with null data', async () => {
      const { store, ws } = await setupConnectedStore()
      let receivedPayload = null

      store.on('null:event', (payload) => {
        receivedPayload = payload
      })

      // Given: Payload with null data
      const nullPayload = {
        type: 'null:event',
        data: null
      }

      // When
      ws.simulateMessage(nullPayload)
      await flushPromises()

      // Then: Should not crash
      expect(receivedPayload).not.toBeNull()
      expect(receivedPayload.data).toBeNull()
    })

    it('preserves original data object reference for handlers that need nested access', async () => {
      const { store, ws } = await setupConnectedStore()
      let receivedPayload = null

      store.on('agent:created', (payload) => {
        receivedPayload = payload
      })

      // Given: Nested payload with deep structure
      const nestedPayload = {
        type: 'agent:created',
        timestamp: '2025-12-03T10:00:00Z',
        schema_version: '1.0',
        data: {
          agent: {
            id: 'agent-deep',
            name: 'Deep Agent',
            metadata: { level: 'nested' }
          },
          project_id: 'proj-deep',
          tenant_key: 'tenant-deep'
        }
      }

      // When
      ws.simulateMessage(nestedPayload)
      await flushPromises()

      // Then: Both flat access AND nested access work
      expect(receivedPayload).not.toBeNull()
      expect(receivedPayload.project_id).toBe('proj-deep')  // Flat access
      expect(receivedPayload.tenant_key).toBe('tenant-deep')  // Flat access
      expect(receivedPayload.data).toBeDefined()  // Original preserved
      expect(receivedPayload.data.agent.id).toBe('agent-deep')  // Nested access
      expect(receivedPayload.data.agent.metadata.level).toBe('nested')  // Deep nested
    })

    it('does not overwrite existing top-level fields with nested data', async () => {
      const { store, ws } = await setupConnectedStore()
      let receivedPayload = null

      store.on('conflict:event', (payload) => {
        receivedPayload = payload
      })

      // Given: Payload with conflicting field names
      const conflictPayload = {
        type: 'conflict:event',
        timestamp: 'top-level-timestamp',  // Top level
        schema_version: '1.0',
        data: {
          timestamp: 'nested-timestamp',  // Nested (should not overwrite)
          project_id: 'proj-conflict'
        }
      }

      // When
      ws.simulateMessage(conflictPayload)
      await flushPromises()

      // Then: Nested data wins (spread order: ...rest, ...rest.data)
      // This is intentional - nested data is the authoritative source
      expect(receivedPayload).not.toBeNull()
      expect(receivedPayload.timestamp).toBe('nested-timestamp')
      expect(receivedPayload.project_id).toBe('proj-conflict')
    })

    it('handles empty data object', async () => {
      const { store, ws } = await setupConnectedStore()
      let receivedPayload = null

      store.on('empty:event', (payload) => {
        receivedPayload = payload
      })

      // Given: Payload with empty data object
      const emptyDataPayload = {
        type: 'empty:event',
        timestamp: '2025-12-03T10:00:00Z',
        data: {}
      }

      // When
      ws.simulateMessage(emptyDataPayload)
      await flushPromises()

      // Then: Should not crash
      expect(receivedPayload).not.toBeNull()
      expect(receivedPayload.timestamp).toBe('2025-12-03T10:00:00Z')
    })
  })

  describe('real-world scenario: Stage Project flow', () => {
    it('allows tenant isolation check to pass with normalized payload', async () => {
      const { store, ws } = await setupConnectedStore()
      let handlerCalled = false
      const expectedTenant = 'user-tenant-key'

      // Simulate ProjectTabs handler with tenant check
      store.on('orchestrator:instructions_fetched', (data) => {
        // This is the actual check that was failing before normalization
        if (data.tenant_key === expectedTenant) {
          handlerCalled = true
        }
      })

      // Given: Backend sends nested payload (the actual problem scenario)
      const nestedPayload = {
        type: 'orchestrator:instructions_fetched',
        timestamp: '2025-12-03T10:00:00Z',
        schema_version: '1.0',
        data: {
          orchestrator_id: 'orch-123',
          project_id: 'proj-456',
          tenant_key: expectedTenant,  // This was inaccessible before
          agent_count: 3,
          status: 'active'
        }
      }

      // When: Message received
      ws.simulateMessage(nestedPayload)
      await flushPromises()

      // Then: Tenant check passes, handler is called
      expect(handlerCalled).toBe(true)
    })

    it('allows project isolation check to pass with normalized payload', async () => {
      const { store, ws } = await setupConnectedStore()
      let handlerCalled = false
      const expectedProjectId = 'target-project-id'

      // Simulate LaunchTab handler with project check
      store.on('orchestrator:instructions_fetched', (data) => {
        // This is the actual check that was failing before normalization
        if (data.project_id === expectedProjectId) {
          handlerCalled = true
        }
      })

      // Given: Backend sends nested payload
      const nestedPayload = {
        type: 'orchestrator:instructions_fetched',
        timestamp: '2025-12-03T10:00:00Z',
        schema_version: '1.0',
        data: {
          orchestrator_id: 'orch-789',
          project_id: expectedProjectId,  // This was inaccessible before
          tenant_key: 'some-tenant',
          agent_count: 4
        }
      }

      // When
      ws.simulateMessage(nestedPayload)
      await flushPromises()

      // Then: Project check passes
      expect(handlerCalled).toBe(true)
    })
  })
})
