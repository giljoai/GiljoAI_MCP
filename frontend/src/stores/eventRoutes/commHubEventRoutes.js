/**
 * commHubEventRoutes.js — FE-6054e/f Agent Message Hub WebSocket event routes.
 *
 * Routes `thread_message` and `thread_update` WS events to commHubStore actions,
 * then mirrors each event as a CustomEvent on `window` so the
 * useHubNotifications composable can observe without coupling to the router.
 */
import { useCommHubStore } from '../commHubStore'

function dispatchWindowEvent(name, detail) {
  window.dispatchEvent(new CustomEvent(name, { detail }))
}

export const COMM_HUB_EVENT_ROUTES = {
  thread_message: {
    handler: async (payload) => {
      const commHub = useCommHubStore()
      commHub.handleThreadMessage(payload)
      dispatchWindowEvent('hub:thread_message', payload)
    },
  },
  thread_update: {
    handler: async (payload) => {
      const commHub = useCommHubStore()
      commHub.handleThreadUpdate(payload)
      dispatchWindowEvent('hub:thread_update', payload)
    },
  },
}
