/**
 * Configuration Service
 *
 * Fetches API host configuration from the backend to ensure WebSocket
 * connections use the correct host in LAN mode.
 *
 * This service solves the problem where the frontend might be accessed via
 * localhost but needs to connect to the API via the actual LAN IP.
 */

import { getApiBaseUrl, getWsBaseUrl } from '@/composables/useApiUrl'

class ConfigService {
  constructor() {
    this.config = null
    this.fetchPromise = null
    this.debug = import.meta.env.VITE_CONFIG_DEBUG === 'true' || false
  }

  /**
   * Fetch configuration from backend
   * @returns {Promise<Object>} Configuration object
   */
  async fetchConfig() {
    // Return cached config if available
    if (this.config) {
      this.log('Using cached config', this.config)
      return this.config
    }

    // Return existing fetch promise if already fetching
    if (this.fetchPromise) {
      this.log('Fetch already in progress, waiting...')
      return this.fetchPromise
    }

    // Start new fetch
    this.fetchPromise = this._doFetch()

    try {
      this.config = await this.fetchPromise
      return this.config
    } finally {
      this.fetchPromise = null
    }
  }

  /**
   * Internal fetch implementation
   * @private
   */
  async _doFetch() {
    try {
      // Determine backend URL for config endpoint.
      // Dev: resolver returns '' so we use a relative URL and let Vite proxy.
      // Prod/demo: resolver gives us the correct absolute base (VITE_API_URL,
      // window.API_BASE_URL, or same-origin). Never compose hostname + port.
      const base = getApiBaseUrl()
      const configUrl = base ? `${base}/api/v1/config/frontend` : '/api/v1/config/frontend'

      this.log(`Fetching config from ${configUrl}`)

      // Fetch with timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000)

      try {
        const response = await fetch(configUrl, {
          signal: controller.signal,
          headers: {
            Accept: 'application/json',
          },
        })

        clearTimeout(timeoutId)

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const config = await response.json()
        this.log('Config fetched successfully', config)

        // Validate response structure. Neither host nor port is strictly
        // required: on Cloudflare/nginx-fronted deployments the backend returns
        // port=null (the public URL has no explicit port), and host may be
        // absent when the deployment relies on same-origin. Gate only on the
        // presence of the `api` object — the URL resolver in
        // @/composables/useApiUrl handles missing host/port by falling back to
        // window.location.
        if (!config.api) {
          throw new Error('Invalid config response structure')
        }

        return config
      } catch (fetchError) {
        clearTimeout(timeoutId)
        throw fetchError
      }
    } catch (error) {
      this.log('Failed to fetch config from backend', error)

      // Fallback: derive everything from the central URL resolver so we
      // never produce `hostname:VITE_API_PORT` for deployments that sit
      // behind a reverse proxy (Cloudflare Tunnel, SaaS).
      const fallbackBase = getApiBaseUrl() || window.location.origin
      const fallbackWs = getWsBaseUrl() || fallbackBase.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:')
      const fallbackUrl = new URL(fallbackBase)
      const fallbackConfig = {
        api: {
          host: fallbackUrl.hostname,
          port: fallbackUrl.port
            ? parseInt(fallbackUrl.port, 10)
            : fallbackUrl.protocol === 'https:'
              ? 443
              : 80,
          protocol: fallbackUrl.protocol.replace(':', ''),
        },
        websocket: {
          url: fallbackWs,
        },
        mode: 'unknown',
        security: {
          api_keys_required: false,
        },
        _fallback: true,
      }

      this.log('Using fallback config', fallbackConfig)
      return fallbackConfig
    }
  }

  /**
   * Get API base URL
   * @returns {string} API base URL
   */
  getApiBaseUrl() {
    if (!this.config) {
      throw new Error('Config not loaded. Call fetchConfig() first.')
    }

    const { host, port } = this.config.api
    const protocol = this.config.api?.protocol || (window.location.protocol === 'https:' ? 'https' : 'http')
    return `${protocol}://${host}:${port}`
  }

  /**
   * Get WebSocket URL
   * @returns {string} WebSocket URL
   */
  getWebSocketUrl() {
    if (!this.config) {
      throw new Error('Config not loaded. Call fetchConfig() first.')
    }

    return this.config.websocket.url
  }

  /**
   * Get deployment mode
   * @returns {string} Deployment mode (localhost, lan, server, wan)
   */
  getMode() {
    if (!this.config) {
      throw new Error('Config not loaded. Call fetchConfig() first.')
    }

    return this.config.mode
  }

  /**
   * Check if API keys are required
   * @returns {boolean} True if API keys are required
   */
  areApiKeysRequired() {
    if (!this.config) {
      throw new Error('Config not loaded. Call fetchConfig() first.')
    }

    return this.config.security?.api_keys_required || false
  }

  /**
   * Get product edition (e.g., "community")
   * @returns {string} Edition identifier
   */
  getEdition() {
    return this.config?.edition || 'community'
  }

  /**
   * Get GILJO_MODE (ce, demo, saas)
   * @returns {string} Mode identifier
   */
  getGiljoMode() {
    return this.config?.giljo_mode || 'ce'
  }

  /**
   * Check if config was fetched successfully or is using fallback
   * @returns {boolean} True if using fallback config
   */
  isFallback() {
    return this.config?._fallback || false
  }

  /**
   * Get raw config object
   * @returns {Object} Configuration object
   */
  getRawConfig() {
    return this.config
  }

  /**
   * Clear cached config (forces refetch on next access)
   */
  clearCache() {
    this.log('Clearing config cache')
    this.config = null
    this.fetchPromise = null
  }

  /**
   * Debug logging
   * @param {string} message Log message
   * @param {*} data Optional data to log
   */
  log(message, data = null) {
    if (this.debug) {
      console.warn(`[ConfigService] ${message}`, data || '')
    }
  }
}

// Create singleton instance
const configService = new ConfigService()

export default configService
export { ConfigService }
