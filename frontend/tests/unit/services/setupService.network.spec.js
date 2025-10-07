/**
 * Tests for setupService network-related methods
 * Testing IP detection and setup completion with API key generation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import setupService from '@/services/setupService'

describe('setupService - Network Methods', () => {
  let fetchMock

  beforeEach(() => {
    // Mock global fetch
    fetchMock = vi.fn()
    global.fetch = fetchMock
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('detectIp', () => {
    it('should call /api/network/detect-ip endpoint', async () => {
      const mockResponse = {
        primary_ip: '192.168.1.100',
        hostname: 'DESKTOP-TEST',
        local_ips: ['192.168.1.100', '10.0.0.50'],
      }

      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await setupService.detectIp()

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/network/detect-ip')
      )
      expect(result).toEqual(mockResponse)
    })

    it('should handle single IP address', async () => {
      const mockResponse = {
        primary_ip: '192.168.1.100',
        hostname: 'LAPTOP-TEST',
        local_ips: ['192.168.1.100'],
      }

      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await setupService.detectIp()

      expect(result.primary_ip).toBe('192.168.1.100')
      expect(result.local_ips).toHaveLength(1)
    })

    it('should handle multiple IP addresses', async () => {
      const mockResponse = {
        primary_ip: '192.168.1.100',
        hostname: 'SERVER-TEST',
        local_ips: ['192.168.1.100', '10.0.0.50', '172.16.0.10'],
      }

      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await setupService.detectIp()

      expect(result.local_ips).toHaveLength(3)
      expect(result.local_ips).toContain('192.168.1.100')
      expect(result.local_ips).toContain('10.0.0.50')
    })

    it('should throw error on network failure', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      })

      await expect(setupService.detectIp()).rejects.toThrow('IP detection failed')
    })

    it('should handle no IPs found', async () => {
      const mockResponse = {
        primary_ip: null,
        hostname: 'OFFLINE-TEST',
        local_ips: [],
      }

      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await setupService.detectIp()

      expect(result.local_ips).toHaveLength(0)
      expect(result.primary_ip).toBeNull()
    })

    it('should handle fetch rejection', async () => {
      fetchMock.mockRejectedValue(new Error('Network error'))

      await expect(setupService.detectIp()).rejects.toThrow('Network error')
    })
  })

  describe('completeSetup - API Key Generation', () => {
    it('should return api_key for LAN mode setup', async () => {
      const setupConfig = {
        deploymentMode: 'lan',
        aiTools: ['claude-code'],
        serenaEnabled: false,
        lanSettings: {
          serverIp: '192.168.1.100',
          adminUsername: 'admin',
          adminPassword: 'securepassword123',
          firewallConfigured: true,
          hostname: 'giljo-server',
        },
      }

      const mockResponse = {
        success: true,
        message: 'Setup completed successfully',
        api_key: 'gai_1234567890abcdef',
        requires_restart: true,
      }

      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await setupService.completeSetup(setupConfig)

      expect(result.success).toBe(true)
      expect(result.api_key).toBe('gai_1234567890abcdef')
      expect(result.requires_restart).toBe(true)
    })

    it('should not return api_key for localhost mode', async () => {
      const setupConfig = {
        deploymentMode: 'localhost',
        aiTools: ['claude-code'],
        serenaEnabled: false,
        lanSettings: null,
      }

      const mockResponse = {
        success: true,
        message: 'Setup completed successfully',
        requires_restart: false,
      }

      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await setupService.completeSetup(setupConfig)

      expect(result.success).toBe(true)
      expect(result.api_key).toBeUndefined()
      expect(result.requires_restart).toBe(false)
    })

    it('should include admin_password in payload for LAN mode', async () => {
      const setupConfig = {
        deploymentMode: 'lan',
        aiTools: ['claude-code'],
        serenaEnabled: false,
        lanSettings: {
          serverIp: '192.168.1.100',
          adminUsername: 'admin',
          adminPassword: 'securepassword123',
          firewallConfigured: true,
          hostname: 'giljo-server',
        },
      }

      const mockResponse = {
        success: true,
        message: 'Setup completed',
        api_key: 'gai_test123',
        requires_restart: true,
      }

      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      })

      await setupService.completeSetup(setupConfig)

      // Check that fetch was called with admin_password in lan_config
      const callArgs = fetchMock.mock.calls[0]
      const requestBody = JSON.parse(callArgs[1].body)

      expect(requestBody.lan_config).toBeDefined()
      expect(requestBody.lan_config.admin_password).toBe('securepassword123')
      expect(requestBody.lan_config.admin_username).toBe('admin')
    })

    it('should handle missing admin credentials gracefully', async () => {
      const setupConfig = {
        deploymentMode: 'lan',
        aiTools: ['claude-code'],
        serenaEnabled: false,
        lanSettings: {
          serverIp: '192.168.1.100',
          firewallConfigured: true,
          // Missing adminUsername and adminPassword
        },
      }

      const mockResponse = {
        success: true,
        message: 'Setup completed',
        api_key: 'gai_test123',
        requires_restart: true,
      }

      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      })

      await setupService.completeSetup(setupConfig)

      const callArgs = fetchMock.mock.calls[0]
      const requestBody = JSON.parse(callArgs[1].body)

      // Should use defaults
      expect(requestBody.lan_config.admin_username).toBe('admin')
    })

    it('should handle setup failure with error details', async () => {
      const setupConfig = {
        deploymentMode: 'lan',
        aiTools: [],
        serenaEnabled: false,
        lanSettings: null,
      }

      const errorResponse = {
        detail: 'Invalid configuration: admin password required',
      }

      fetchMock.mockResolvedValue({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => errorResponse,
      })

      await expect(setupService.completeSetup(setupConfig)).rejects.toThrow(
        'Invalid configuration'
      )
    })

    it('should transform tools array correctly', async () => {
      const setupConfig = {
        deploymentMode: 'localhost',
        aiTools: [
          { id: 'claude-code', name: 'Claude Code', configured: true },
          { id: 'cursor', name: 'Cursor', configured: false },
        ],
        serenaEnabled: true,
        lanSettings: null,
      }

      const mockResponse = {
        success: true,
        message: 'Setup completed',
      }

      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      })

      await setupService.completeSetup(setupConfig)

      const callArgs = fetchMock.mock.calls[0]
      const requestBody = JSON.parse(callArgs[1].body)

      expect(requestBody.tools_attached).toEqual(['claude-code', 'cursor'])
    })
  })

  describe('Error Handling', () => {
    it('should provide clear error messages for network failures', async () => {
      fetchMock.mockRejectedValue(new Error('Failed to fetch'))

      await expect(setupService.detectIp()).rejects.toThrow('Failed to fetch')
    })

    it('should handle JSON parsing errors', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => {
          throw new Error('Invalid JSON')
        },
      })

      await expect(setupService.detectIp()).rejects.toThrow('Invalid JSON')
    })
  })
})
