/**
 * Setup Wizard API Service
 *
 * Handles all API communication for the setup wizard including:
 * - Tool detection
 * - MCP configuration generation
 * - Database testing
 * - Deployment mode configuration
 * - Setup completion
 */

import { API_CONFIG } from '@/config/api'

class SetupService {
  constructor() {
    this.baseURL = API_CONFIG.REST_API.baseURL
  }

  /**
   * Check setup completion status
   * @returns {Promise<{completed: boolean}>}
   */
  async checkStatus() {
    const response = await fetch(`${this.baseURL}/api/setup/status`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Test database connection
   * @returns {Promise<{success: boolean, database: string, host: string}>}
   */
  async testDatabaseConnection() {
    const response = await fetch(`${this.baseURL}/api/v1/config/health/database`)
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
    const response = await fetch(`${this.baseURL}/api/setup/database/test-connection`, {
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
    const response = await fetch(`${this.baseURL}/api/setup/database/setup`, {
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
    const response = await fetch(`${this.baseURL}/api/setup/detect-tools`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Generate MCP configuration for a tool
   * @param {string} tool - Tool name (e.g., 'Claude Code')
   * @param {string} mode - Deployment mode: 'localhost', 'lan', or 'wan'
   * @returns {Promise<Object>} Generated MCP configuration
   */
  async generateMcpConfig(tool, mode) {
    const response = await fetch(`${this.baseURL}/api/setup/generate-mcp-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool, mode }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Register MCP server with AI tool (writes config file)
   * @param {string} tool - Tool name
   * @param {Object} config - MCP configuration to write
   * @returns {Promise<{success: boolean, config_path: string, backup_path: string}>}
   */
  async registerMcp(tool, config) {
    const response = await fetch(`${this.baseURL}/api/setup/register-mcp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool, config }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Test MCP connection for a tool
   * @param {string} tool - Tool name to test
   * @returns {Promise<{success: boolean, status: string, message: string}>}
   */
  async testMcpConnection(tool) {
    const response = await fetch(`${this.baseURL}/api/setup/test-mcp-connection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Configure deployment mode
   * @param {string} mode - Deployment mode: 'localhost', 'lan', or 'wan'
   * @param {string} [lanIp] - LAN IP address (required for LAN mode)
   * @param {string} [wanUrl] - WAN URL (required for WAN mode)
   * @returns {Promise<{success: boolean, mode: string, api_url: string}>}
   */
  async configureDeploymentMode(mode, lanIp = null, wanUrl = null) {
    const response = await fetch(`${this.baseURL}/api/setup/configure-deployment-mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, lan_ip: lanIp, wan_url: wanUrl }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Mark setup as complete
   * @param {Object} config - Complete wizard configuration
   * @returns {Promise<{success: boolean, setup_completed: boolean}>}
   */
  async completeSetup(config) {
    const response = await fetch(`${this.baseURL}/api/setup/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Restart services after setup completion
   * @returns {Promise<{success: boolean, status: string, message: string}>}
   */
  async restartServices() {
    const response = await fetch(`${this.baseURL}/api/setup/restart-services`, {
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
        const response = await fetch(`${this.baseURL}/health`, {
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
    const response = await fetch(`${this.baseURL}/api/setup/database/verify`)

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Detect if Serena MCP is installed
   * @returns {Promise<{installed: boolean, version?: string, path?: string}>}
   */
  async detectSerena() {
    try {
      const response = await fetch(`${this.baseURL}/api/setup/detect-serena`, {
        method: 'POST',
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.error('[SETUP_SERVICE] Serena detection failed:', error)
      throw error
    }
  }

  /**
   * Attach Serena MCP to Claude Code configuration
   * @returns {Promise<{success: boolean, config_path?: string, error?: string}>}
   */
  async attachSerena() {
    try {
      const response = await fetch(`${this.baseURL}/api/setup/attach-serena`, {
        method: 'POST',
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.error('[SETUP_SERVICE] Serena attachment failed:', error)
      throw error
    }
  }

  /**
   * Detach Serena MCP from Claude Code configuration
   * @returns {Promise<{success: boolean, config_path?: string, error?: string}>}
   */
  async detachSerena() {
    try {
      const response = await fetch(`${this.baseURL}/api/setup/detach-serena`, {
        method: 'POST',
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.error('[SETUP_SERVICE] Serena detachment failed:', error)
      throw error
    }
  }

  /**
   * Get current Serena MCP status
   * @returns {Promise<{installed: boolean, configured: boolean, version?: string}>}
   */
  async getSerenaStatus() {
    try {
      const response = await fetch(`${this.baseURL}/api/setup/serena-status`)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.error('[SETUP_SERVICE] Serena status check failed:', error)
      throw error
    }
  }
}

export default new SetupService()
