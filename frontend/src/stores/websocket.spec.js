import { beforeEach, afterEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useWebSocketStore } from '@/stores/websocket'

class MockWebSocket {
  static instances = []

  constructor(url) {
    this.url = url
    this.sent = []
    this.onopen = null
    this.onmessage = null
    this.onclose = null
    this.onerror = null

    MockWebSocket.instances.push(this)
  }

  send(data) {
    this.sent.push(data)
  }

  close() {
    // Intentionally no-op for unit tests to avoid triggering reconnect logic.
  }

  open() {
    this.onopen?.()
  }
}

function getSentTypes(socket) {
  return socket.sent.map((raw) => JSON.parse(raw).type)
}

describe('websocket store - subscription refcounting', () => {
  let originalWebSocket

  beforeEach(() => {
    setActivePinia(createPinia())
    MockWebSocket.instances = []

    originalWebSocket = globalThis.WebSocket
    globalThis.WebSocket = MockWebSocket
  })

  afterEach(() => {
    globalThis.WebSocket = originalWebSocket
  })

  it('keeps server subscription active until last unsubscribe', async () => {
    const wsStore = useWebSocketStore()

    const connectPromise = wsStore.connect()
    const socket = MockWebSocket.instances[0]
    socket.open()
    await connectPromise

    wsStore.subscribe('project', 'proj-1')
    wsStore.subscribe('project', 'proj-1')

    expect(getSentTypes(socket).filter((t) => t === 'subscribe')).toHaveLength(1)

    wsStore.unsubscribe('project', 'proj-1')
    expect(getSentTypes(socket)).not.toContain('unsubscribe')

    wsStore.unsubscribe('project', 'proj-1')
    expect(getSentTypes(socket).filter((t) => t === 'unsubscribe')).toHaveLength(1)

    wsStore.disconnect()
  })

  it('resubscribes only active subscriptions after reconnect', async () => {
    const wsStore = useWebSocketStore()

    // First connection
    const connectPromise1 = wsStore.connect()
    const socket1 = MockWebSocket.instances[0]
    socket1.open()
    await connectPromise1

    wsStore.subscribe('project', 'proj-1')
    wsStore.subscribe('project', 'proj-1')
    wsStore.unsubscribe('project', 'proj-1') // one subscriber remains

    wsStore.disconnect()

    // Second connection (simulated reconnect)
    const connectPromise2 = wsStore.connect()
    const socket2 = MockWebSocket.instances[1]
    socket2.open()
    await connectPromise2

    expect(getSentTypes(socket2)).toContain('subscribe')
    expect(getSentTypes(socket2).filter((t) => t === 'subscribe')).toHaveLength(1)

    wsStore.disconnect()
  })
})
