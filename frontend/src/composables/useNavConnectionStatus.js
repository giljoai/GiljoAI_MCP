/**
 * useNavConnectionStatus Composable
 *
 * Derives the navigation-drawer connection orb's icon / color / tooltip text
 * from the WebSocket store's `connectionStatus`. Extracted from
 * NavigationDrawer (INF-6055) to keep that component under the 800-line
 * guardrail — a cohesive group of three pure computeds with no state or side
 * effects, mirroring the existing useNavDrawerAccount split.
 *
 * Reads the Pinia WebSocket store directly (singleton), so the returned
 * computeds track live connection changes exactly as the prior in-component
 * implementation did.
 */
import { computed } from 'vue'
import { useWebSocketStore } from '@/stores/websocket'

export function useNavConnectionStatus() {
  const wsStore = useWebSocketStore()

  const connectionIcon = computed(() => {
    switch (wsStore.connectionStatus) {
      case 'connected':
        return 'mdi-wifi'
      case 'connecting':
      case 'reconnecting':
        return 'mdi-wifi-sync'
      case 'disconnected':
        return 'mdi-wifi-off'
      default:
        return 'mdi-help-circle'
    }
  })

  const connectionColor = computed(() => {
    switch (wsStore.connectionStatus) {
      case 'connected':
        return 'success'
      case 'connecting':
      case 'reconnecting':
        return 'warning'
      case 'disconnected':
        return 'error'
      default:
        return 'grey'
    }
  })

  const connectionText = computed(() => {
    switch (wsStore.connectionStatus) {
      case 'connected':
        return 'Connected'
      case 'connecting':
        return 'Connecting...'
      case 'reconnecting':
        return `Reconnecting (${wsStore.reconnectAttempts}/${wsStore.maxReconnectAttempts})`
      case 'disconnected':
        return 'Disconnected'
      default:
        return 'Unknown'
    }
  })

  return {
    connectionIcon,
    connectionColor,
    connectionText,
  }
}
