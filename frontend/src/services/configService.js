/**
 * Configuration Service
 *
 * Fetches API host configuration from the backend to ensure WebSocket
 * connections use the correct host in LAN mode.
 *
 * This service solves the problem where the frontend might be accessed via
 * localhost but needs to connect to the API via the actual LAN IP.
 */

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
      // Determine backend URL for config endpoint
      // Dev: use relative URL so Vite proxy handles CORS
      // Prod: direct to configured API host:port
      let configUrl
      if (import.meta.env.DEV) {
        configUrl = '/api/v1/config/frontend'
      } else {
        const currentHost = window.location.hostname
        const apiPort = import.meta.env.VITE_API_PORT || window.API_PORT || '7272'
        const protocol = window.location.protocol === 'https:' ? 'https' : 'http'
        configUrl = `${protocol}://${currentHost}:${apiPort}/api/v1/config/frontend`
      }

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

        // Validate response structure
        if (!config.api || !config.api.host || !config.api.port) {
          throw new Error('Invalid config response structure')
        }

        return config
      } catch (fetchError) {
        clearTimeout(timeoutId)
        throw fetchError
      }
    } catch (error) {
      this.log('Failed to fetch config from backend', error)

      // Fallback to window.location.hostname
      const fallbackHost = window.location.hostname
      const fallbackPort = parseInt(import.meta.env.VITE_API_PORT || window.API_PORT || '7272', 10)

      const fallbackConfig = {
        api: {
          host: fallbackHost,
          port: fallbackPort,
        },
        websocket: {
          url: `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${fallbackHost}:${fallbackPort}`,
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
      console.log(`[ConfigService] ${message}`, data || '')
    }
  }
}

// Create singleton instance
const configService = new ConfigService()

export default configService
export { ConfigService }
