import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import setupService from '@/services/setupService'

// Mock axios
vi.mock('axios')

describe('setupService - Serena MCP Methods', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  describe('detectSerena', () => {
    it('should make POST request to /api/setup/detect-serena', async () => {
      const mockResponse = { installed: false, version: null }
      axios.post.mockResolvedValue({ data: mockResponse })

      const result = await setupService.detectSerena()

      expect(axios.post).toHaveBeenCalledWith('/api/setup/detect-serena')
      expect(result).toEqual(mockResponse)
    })

    it('should handle detection failures', async () => {
      axios.post.mockRejectedValue(new Error('Network error'))

      await expect(setupService.detectSerena()).rejects.toThrow('Network error')
    })

    it('should handle partial response', async () => {
      const partialResponse = { installed: true }
      axios.post.mockResolvedValue({ data: partialResponse })

      const result = await setupService.detectSerena()

      expect(result).toEqual(partialResponse)
    })
  })

  describe('attachSerena', () => {
    it('should make POST request to /api/setup/attach-serena', async () => {
      const mockResponse = { success: true }
      axios.post.mockResolvedValue({ data: mockResponse })

      const result = await setupService.attachSerena()

      expect(axios.post).toHaveBeenCalledWith('/api/setup/attach-serena')
      expect(result).toEqual(mockResponse)
    })

    it('should handle attachment failures', async () => {
      axios.post.mockRejectedValue(new Error('Attachment failed'))

      await expect(setupService.attachSerena()).rejects.toThrow('Attachment failed')
    })
  })

  describe('detachSerena', () => {
    it('should make POST request to /api/setup/detach-serena', async () => {
      const mockResponse = { success: true }
      axios.post.mockResolvedValue({ data: mockResponse })

      const result = await setupService.detachSerena()

      expect(axios.post).toHaveBeenCalledWith('/api/setup/detach-serena')
      expect(result).toEqual(mockResponse)
    })

    it('should handle detachment failures', async () => {
      axios.post.mockRejectedValue(new Error('Detachment failed'))

      await expect(setupService.detachSerena()).rejects.toThrow('Detachment failed')
    })
  })

  describe('getSerenaStatus', () => {
    it('should make GET request to /api/setup/serena-status', async () => {
      const mockResponse = {
        enabled: false,
        version: null,
        config: {}
      }
      axios.get.mockResolvedValue({ data: mockResponse })

      const result = await setupService.getSerenaStatus()

      expect(axios.get).toHaveBeenCalledWith('/api/setup/serena-status')
      expect(result).toEqual(mockResponse)
    })

    it('should handle status retrieval failures', async () => {
      axios.get.mockRejectedValue(new Error('Status retrieval failed'))

      await expect(setupService.getSerenaStatus()).rejects.toThrow('Status retrieval failed')
    })
  })

  describe('Error Handling', () => {
    it('should transform network errors consistently', async () => {
      axios.post.mockRejectedValue(new Error('Connection refused'))

      try {
        await setupService.detectSerena()
      } catch (error) {
        expect(error.message).toContain('Connection refused')
        expect(error.name).toBe('SerenaDetectionError')
      }
    })
  })
})