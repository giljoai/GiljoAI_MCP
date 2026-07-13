/**
 * Normalize a WebSocket event payload to handle both:
 * - flat structures: { type, tenant_key, ... }
 * - nested structures: { type, data: { tenant_key, ... } }
 *
 * When a nested `data` object is found, its fields are merged to the top level.
 * The original `data` key is preserved for handlers that need nested access.
 *
 * @param {Object} rawEvent - Raw WebSocket event object
 * @returns {{ type: string|undefined, payload: Object }}
 *
 * @see Handover 0290 - WebSocket Payload Normalization
 */
export function normalizeWebsocketPayload(rawEvent) {
  if (!rawEvent || typeof rawEvent !== 'object') {
    return { type: undefined, payload: {} }
  }

  const { type, ...rest } = rawEvent

  // If `data` is a plain object, merge its fields to top level for flat access
  if (rest.data && typeof rest.data === 'object' && !Array.isArray(rest.data)) {
    return { type, payload: { ...rest, ...rest.data } }
  }

  return { type, payload: rest }
}
