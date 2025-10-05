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
      body: JSON.stringify({ tool, mode })
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
      body: JSON.stringify({ tool, config })
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
      body: JSON.stringify({ tool })
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
      body: JSON.stringify({ mode, lan_ip: lanIp, wan_url: wanUrl })
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
      body: JSON.stringify(config)
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }
}

export default new SetupService()
