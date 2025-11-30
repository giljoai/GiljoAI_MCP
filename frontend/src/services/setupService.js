/**
 * Setup Wizard API Service
 *
 * Handles all API communication for the setup wizard including:
 * - Tool detection
 * - MCP configuration generation
 * - Database testing
 * - System setup
 * - Setup completion
 */

import { API_CONFIG } from '@/config/api'

class SetupService {
  constructor() {
    // IMPORTANT: Don't cache baseURL at construction time
    // Read it dynamically from window.API_BASE_URL or API_CONFIG at call time
  }

  /**
   * Get the current API base URL (runtime-aware)
   * @returns {string}
   */
  getBaseURL() {
    return window.API_BASE_URL || API_CONFIG.REST_API.baseURL
  }

  /**
   * Check fresh install status (Handover 0034 - simplified)
   * @returns {Promise<{is_fresh_install: boolean, total_users_count: number, requires_admin_creation: boolean}>}
   */
  async checkEnhancedStatus() {
    try {
      const response = await fetch(`${this.getBaseURL()}/api/setup/status`, {
        method: 'GET',
        cache: 'no-cache',
      })

      if (response.ok) {
        const data = await response.json()
        return {
          is_fresh_install: data.is_fresh_install,
          total_users_count: data.total_users_count,
          requires_admin_creation: data.requires_admin_creation,
        }
      } else {
        console.warn('[SETUP_SERVICE] Setup status endpoint failed:', response.status)
        // Conservative fallback - assume fresh install (allows account creation)
        return {
          is_fresh_install: true,
          total_users_count: 0,
          requires_admin_creation: true,
        }
      }
    } catch (error) {
      console.warn('[SETUP_SERVICE] Status check failed:', error)
      // Conservative fallback - assume fresh install (allows account creation)
      return {
        is_fresh_install: true,
        total_users_count: 0,
        requires_admin_creation: true,
      }
    }
  }

  /**
   * Check setup completion status (Handover 0034 - backward compatibility wrapper)
   * @returns {Promise<{requires_setup: boolean, is_fresh_install: boolean}>}
   */
  async checkStatus() {
    try {
      const status = await this.checkEnhancedStatus()
      return {
        requires_setup: false, // v3.0: Always false, no setup wizard
        is_fresh_install: status.is_fresh_install,
      }
    } catch (error) {
      console.warn('[SETUP_SERVICE] Status check failed:', error)
      // Fallback - no setup required, not fresh install
      return { requires_setup: false, is_fresh_install: false }
    }
  }

  /**
   * Test database connection
   * @returns {Promise<{success: boolean, database: string, host: string}>}
   */
  async testDatabaseConnection() {
    const response = await fetch(`${this.getBaseURL()}/api/v1/config/health/database`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Test PostgreSQL connection with setup credentials
   * @param {Object} dbConfig - Database configuration
   * @param {string} dbConfig.host - PostgreSQL host
   * @param {number} dbConfig.port - PostgreSQL port
   * @param {string} dbConfig.admin_user - PostgreSQL admin username
   * @param {string} dbConfig.admin_password - PostgreSQL admin password
   * @param {string} dbConfig.database_name - Database name
   * @returns {Promise<{success: boolean, status: string, message: string, postgresql_version?: number, database_exists?: boolean}>}
   */
  async testPostgresConnection(dbConfig) {
    const response = await fetch(`${this.getBaseURL()}/api/setup/database/test-connection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dbConfig),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Setup PostgreSQL database
   * @param {Object} dbConfig - Database configuration
   * @param {string} dbConfig.host - PostgreSQL host
   * @param {number} dbConfig.port - PostgreSQL port
   * @param {string} dbConfig.admin_user - PostgreSQL admin username
   * @param {string} dbConfig.admin_password - PostgreSQL admin password
   * @param {string} dbConfig.database_name - Database name
   * @returns {Promise<{success: boolean, status: string, message: string, credentials_file?: string, warnings?: Array}>}
   */
  async setupPostgresDatabase(dbConfig) {
    const response = await fetch(`${this.getBaseURL()}/api/setup/database/setup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dbConfig),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Detect installed AI coding tools
   * @returns {Promise<{tools: Array}>}
   */
  async detectTools() {
    const response = await fetch(`${this.getBaseURL()}/api/setup/detect-tools`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return response.json()
  }

  // AUTO-INJECTION METHODS REMOVED (v3.0 unified architecture)
  // registerMcp() and checkMcpConfigured() removed
  // Use downloadable setup scripts instead for all users (localhost and remote)

  /**
   * Test MCP connection for a tool
   * @param {string} tool - Tool name to test
   * @returns {Promise<{success: boolean, status: string, message: string}>}
   */
  async testMcpConnection(tool) {
    const response = await fetch(`${this.getBaseURL()}/api/setup/test-mcp-connection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  // LAN/network configuration removed for v3.0 unified architecture

  /**
   * Mark setup as complete
   * @param {Object} config - Complete wizard configuration
   * @param {Array<string>} config.aiTools - List of attached AI tools
   * @returns {Promise<{success: boolean, message: string}>}
   */
  async completeSetup(config) {
    console.log('[SETUP_SERVICE] completeSetup called with:', config)

    // Transform wizard config to API format
    // aiTools is array of objects [{id, name, configured}], need to extract IDs
    const toolIds = (config.aiTools || []).map((tool) => {
      // Handle both object format {id: 'claude-code'} and string format
      return typeof tool === 'string' ? tool : tool.id
    })

    const payload = {
      tools_attached: toolIds,
      serena_enabled: config.serenaEnabled || false,
    }

    console.log('[SETUP_SERVICE] Sending payload:', payload)

    const response = await fetch(`${this.getBaseURL()}/api/setup/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      // Try to get detailed error message from response body
      let errorDetail = response.statusText
      try {
        const errorBody = await response.json()
        console.error('[SETUP_SERVICE] Error response body:', errorBody)
        errorDetail = errorBody.detail || JSON.stringify(errorBody)
      } catch (e) {
        // Response body not JSON, use statusText
      }
      throw new Error(`HTTP ${response.status}: ${errorDetail}`)
    }

    return response.json()
  }

  /**
   * Restart services after setup completion
   * @returns {Promise<{success: boolean, status: string, message: string}>}
   */
  async restartServices() {
    const response = await fetch(`${this.getBaseURL()}/api/setup/restart-services`, {
      method: 'POST',
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Wait for backend to come back online after restart
   * Polls /health endpoint until it returns 200 OK
   * @param {number} maxAttempts - Maximum number of polling attempts
   * @param {number} intervalMs - Interval between polls in milliseconds
   * @returns {Promise<boolean>} True if backend is online, false if timeout
   */
  async waitForBackend(maxAttempts = 30, intervalMs = 1000) {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const response = await fetch(`${this.getBaseURL()}/health`, {
          method: 'GET',
          cache: 'no-cache',
        })

        if (response.ok) {
          console.log(`Backend online after ${attempt} attempts`)
          return true
        }
      } catch (error) {
        // Backend not ready yet, continue polling
        console.log(`Attempt ${attempt}/${maxAttempts}: Backend not ready`)
      }

      // Wait before next attempt
      await new Promise((resolve) => setTimeout(resolve, intervalMs))
    }

    console.error('Backend did not come back online within timeout')
    return false
  }

  /**
   * Verify database setup from CLI installation
   *
   * Reads credentials from server-side .env (never sent to client).
   * Tests connection to verify database exists and is accessible.
   * Checks schema migration status.
   *
   * Security: Credentials are read server-side from .env and NEVER sent to frontend.
   * Only non-sensitive metadata is returned (database name, host, port, version, table count).
   *
   * @returns {Promise<{success: boolean, status: string, message: string, database?: string, host?: string, port?: number, postgresql_version?: number, schema_migrated?: boolean, tables_count?: number, errors?: Array, error?: string}>}
   */
  async verifyDatabaseSetup() {
    const response = await fetch(`${this.getBaseURL()}/api/setup/database/verify`)

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Detect server IP addresses using backend endpoint
   * @returns {Promise<{primary_ip: string, hostname: string, local_ips: Array<string>}>}
   */
  async detectIp() {
    const response = await fetch(`${this.getBaseURL()}/api/network/detect-ip`)

    if (!response.ok) {
      throw new Error('IP detection failed')
    }

    return response.json()
  }

  // Network adapters detection removed for v3.0 unified architecture

  /**
   * Toggle Serena MCP prompt injection on/off
   * @param {boolean} enabled - Whether to enable Serena prompts
   * @returns {Promise<{success: boolean, enabled: boolean, message?: string}>}
   */
  async toggleSerena(enabled) {
    // Import API here to avoid circular dependency
    const { default: api } = await import('@/services/api')

    try {
      const response = await api.serena.toggle(enabled)
      return response.data
    } catch (error) {
      console.error('[SETUP_SERVICE] Serena toggle failed:', error)
      throw error
    }
  }

  /**
   * Get current Serena MCP prompt injection status
   * @returns {Promise<{enabled: boolean}>}
   */
  async getSerenaStatus() {
    // Import API here to avoid circular dependency
    const { default: api } = await import('@/services/api')

    try {
      const response = await api.serena.getStatus()
      return response.data
    } catch (error) {
      console.error('[SETUP_SERVICE] Serena status check failed:', error)
      throw error
    }
  }

  /**
   * Get full Serena MCP configuration
   * @returns {Promise<{use_in_prompts:boolean, tailor_by_mission:boolean, dynamic_catalog:boolean, prefer_ranges:boolean, max_range_lines:number, context_halo:number}>}
   */
  async getSerenaConfig() {
    const { default: api } = await import('@/services/api')
    try {
      const response = await api.serena.getConfig()
      return response.data
    } catch (error) {
      console.error('[SETUP_SERVICE] Serena config fetch failed:', error)
      throw error
    }
  }

  /**
   * Update Serena MCP configuration
   * @param {object} data - Partial config update
   * @returns {Promise<object>} - Updated config
   */
  async updateSerenaConfig(data) {
    const { default: api } = await import('@/services/api')
    try {
      const response = await api.serena.updateConfig(data)
      return response.data
    } catch (error) {
      console.error('[SETUP_SERVICE] Serena config update failed:', error)
      throw error
    }
  }

  // Admin user creation removed for v3.0 unified architecture

  /**
   * Toggle Git integration on/off (system-level)
   * @param {boolean} enabled - Whether to enable Git integration
   * @returns {Promise<{success: boolean, enabled: boolean, message?: string, settings?: object}>}
   */
  async toggleGit(enabled) {
    // Import API here to avoid circular dependency
    const { default: api } = await import('@/services/api')

    try {
      const response = await api.git.toggle(enabled)
      return response.data
    } catch (error) {
      console.error('[SETUP_SERVICE] Git toggle failed:', error)
      throw error
    }
  }

  /**
   * Get current Git integration settings
   * @returns {Promise<{enabled: boolean, use_in_prompts: boolean, include_commit_history: boolean, max_commits: number, branch_strategy: string}>}
   */
  async getGitSettings() {
    // Import API here to avoid circular dependency
    const { default: api } = await import('@/services/api')

    try {
      const response = await api.git.getSettings()
      return response.data
    } catch (error) {
      console.error('[SETUP_SERVICE] Git settings fetch failed:', error)
      throw error
    }
  }

  /**
   * Update Git integration advanced settings
   * @param {object} settings - Git advanced settings
   * @returns {Promise<{success: boolean, enabled: boolean, message?: string, settings?: object}>}
   */
  async updateGitSettings(settings) {
    // Import API here to avoid circular dependency
    const { default: api } = await import('@/services/api')

    try {
      const response = await api.git.updateSettings(settings)
      return response.data
    } catch (error) {
      console.error('[SETUP_SERVICE] Git settings update failed:', error)
      throw error
    }
  }
}

export default new SetupService()
