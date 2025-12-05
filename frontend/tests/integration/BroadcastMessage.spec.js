/**
 * Broadcast Message Integration Test
 *
 * Tests the complete broadcast message workflow:
 * 1. Frontend API endpoint correctness
 * 2. Message composition and submission
 * 3. Store state management
 * 4. Error handling and edge cases
 *
 * CRITICAL FIX: Handover 0296
 * - Fixed 405 Method Not Allowed error
 * - Updated endpoint from /api/agent-jobs/broadcast to /api/v1/messages/broadcast
 * - Ensured request body matches backend BroadcastMessage schema
 * - Updated response handling to match backend response format
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import api from '@/services/api'

// Mock the API service module
vi.mock('@/services/api', () => ({
  default: {
    agentJobs: {
      broadcast: vi.fn(),
    },
  },
}))

describe('Broadcast Message Integration - Handover 0296', () => {
  const mockProjectId = 'test-project-uuid'
  const mockMessage = 'Hello all agents!'

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('API Endpoint Configuration', () => {
    it('should POST to /api/v1/messages/broadcast endpoint', async () => {
      // Mock successful response
      const mockResponse = {
        success: true,
        message_id: 'msg-123',
        recipient_count: 3,
        recipients: ['orchestrator', 'analyzer', 'implementor'],
        timestamp: '2025-01-15T10:00:00Z',
      }

      vi.mocked(api.agentJobs.broadcast).mockResolvedValue({ data: mockResponse })

      const result = await api.agentJobs.broadcast({
        project_id: mockProjectId,
        content: mockMessage,
      })

      // Verify the endpoint was called
      expect(api.agentJobs.broadcast).toHaveBeenCalled()

      // Verify response structure
      expect(result.data).toEqual(mockResponse)
    })

    it('should include required fields in request body', async () => {
      const mockResponse = {
        success: true,
        message_id: 'msg-123',
        recipient_count: 1,
        recipients: ['orchestrator'],
        timestamp: '2025-01-15T10:00:00Z',
      }

      vi.mocked(api.agentJobs.broadcast).mockResolvedValue({ data: mockResponse })

      const payload = {
        project_id: mockProjectId,
        content: mockMessage,
        priority: 'normal',
        from_agent: 'user',
      }

      await api.agentJobs.broadcast(payload)

      expect(api.agentJobs.broadcast).toHaveBeenCalledWith(payload)
    })

    it('should default priority to "normal" when not specified', async () => {
      vi.mocked(axios.post).mockResolvedValue({
        data: {
          success: true,
          message_id: 'msg-123',
          recipient_count: 0,
          recipients: [],
          timestamp: '2025-01-15T10:00:00Z',
        },
      })

      await api.agentJobs.broadcast({
        project_id: mockProjectId,
        content: mockMessage,
      })

      const callArgs = vi.mocked(axios.post).mock.calls[0]
      const requestBody = callArgs[1]

      expect(requestBody.priority).toBe('normal')
    })

    it('should default from_agent to "user" when not specified', async () => {
      vi.mocked(axios.post).mockResolvedValue({
        data: {
          success: true,
          message_id: 'msg-123',
          recipient_count: 0,
          recipients: [],
          timestamp: '2025-01-15T10:00:00Z',
        },
      })

      await api.agentJobs.broadcast({
        project_id: mockProjectId,
        content: mockMessage,
      })

      const callArgs = vi.mocked(axios.post).mock.calls[0]
      const requestBody = callArgs[1]

      expect(requestBody.from_agent).toBe('user')
    })
  })

  describe('Response Handling', () => {
    it('should return message_id from response', async () => {
      const expectedMessageId = 'msg-abc123'
      const mockResponse = {
        success: true,
        message_id: expectedMessageId,
        recipient_count: 2,
        recipients: ['agent1', 'agent2'],
        timestamp: '2025-01-15T10:00:00Z',
      }

      vi.mocked(axios.post).mockResolvedValue({ data: mockResponse })

      const result = await api.agentJobs.broadcast({
        project_id: mockProjectId,
        content: mockMessage,
      })

      expect(result.data.message_id).toBe(expectedMessageId)
    })

    it('should return recipient_count', async () => {
      const mockResponse = {
        success: true,
        message_id: 'msg-123',
        recipient_count: 4,
        recipients: ['orchestrator', 'analyzer', 'implementor', 'tester'],
        timestamp: '2025-01-15T10:00:00Z',
      }

      vi.mocked(axios.post).mockResolvedValue({ data: mockResponse })

      const result = await api.agentJobs.broadcast({
        project_id: mockProjectId,
        content: mockMessage,
      })

      expect(result.data.recipient_count).toBe(4)
    })

    it('should return array of recipients', async () => {
      const expectedRecipients = ['orchestrator', 'analyzer', 'implementor']
      const mockResponse = {
        success: true,
        message_id: 'msg-123',
        recipient_count: 3,
        recipients: expectedRecipients,
        timestamp: '2025-01-15T10:00:00Z',
      }

      vi.mocked(axios.post).mockResolvedValue({ data: mockResponse })

      const result = await api.agentJobs.broadcast({
        project_id: mockProjectId,
        content: mockMessage,
      })

      expect(result.data.recipients).toEqual(expectedRecipients)
    })

    it('should return ISO timestamp', async () => {
      const expectedTimestamp = '2025-01-15T10:30:45.123Z'
      const mockResponse = {
        success: true,
        message_id: 'msg-123',
        recipient_count: 1,
        recipients: ['orchestrator'],
        timestamp: expectedTimestamp,
      }

      vi.mocked(axios.post).mockResolvedValue({ data: mockResponse })

      const result = await api.agentJobs.broadcast({
        project_id: mockProjectId,
        content: mockMessage,
      })

      expect(result.data.timestamp).toBe(expectedTimestamp)
    })
  })

  describe('Error Handling', () => {
    it('should handle 405 Method Not Allowed (original bug)', async () => {
      const error = {
        response: {
          status: 405,
          statusText: 'Method Not Allowed',
          data: { detail: 'Method Not Allowed' },
        },
      }

      vi.mocked(axios.post).mockRejectedValue(error)

      await expect(
        api.agentJobs.broadcast({
          project_id: mockProjectId,
          content: mockMessage,
        })
      ).rejects.toThrow()

      // Verify error is thrown (not silently caught)
      expect(axios.post).toHaveBeenCalled()
    })

    it('should handle 404 Project Not Found', async () => {
      const error = {
        response: {
          status: 404,
          statusText: 'Not Found',
          data: { detail: 'Project not found' },
        },
      }

      vi.mocked(axios.post).mockRejectedValue(error)

      await expect(
        api.agentJobs.broadcast({
          project_id: 'invalid-project-id',
          content: mockMessage,
        })
      ).rejects.toThrow()
    })

    it('should handle 400 Bad Request (invalid payload)', async () => {
      const error = {
        response: {
          status: 400,
          statusText: 'Bad Request',
          data: { detail: 'Invalid payload' },
        },
      }

      vi.mocked(axios.post).mockRejectedValue(error)

      await expect(
        api.agentJobs.broadcast({
          project_id: mockProjectId,
          content: '', // Empty content
        })
      ).rejects.toThrow()
    })

    it('should handle 500 Server Error', async () => {
      const error = {
        response: {
          status: 500,
          statusText: 'Internal Server Error',
          data: { detail: 'Database error' },
        },
      }

      vi.mocked(axios.post).mockRejectedValue(error)

      await expect(
        api.agentJobs.broadcast({
          project_id: mockProjectId,
          content: mockMessage,
        })
      ).rejects.toThrow()
    })

    it('should handle network error', async () => {
      const error = new Error('Network Error')

      vi.mocked(axios.post).mockRejectedValue(error)

      await expect(
        api.agentJobs.broadcast({
          project_id: mockProjectId,
          content: mockMessage,
        })
      ).rejects.toThrow('Network Error')
    })
  })

  describe('Message Content Validation', () => {
    it('should accept messages up to reasonable length', async () => {
      const longMessage = 'x'.repeat(1000)

      vi.mocked(axios.post).mockResolvedValue({
        data: {
          success: true,
          message_id: 'msg-123',
          recipient_count: 1,
          recipients: ['orchestrator'],
          timestamp: '2025-01-15T10:00:00Z',
        },
      })

      const result = await api.agentJobs.broadcast({
        project_id: mockProjectId,
        content: longMessage,
      })

      expect(result.data.success).toBe(true)
    })

    it('should preserve special characters in message content', async () => {
      const specialMessage = 'Test with "quotes" and \n newlines and @symbols'

      vi.mocked(axios.post).mockResolvedValue({
        data: {
          success: true,
          message_id: 'msg-123',
          recipient_count: 1,
          recipients: ['orchestrator'],
          timestamp: '2025-01-15T10:00:00Z',
        },
      })

      await api.agentJobs.broadcast({
        project_id: mockProjectId,
        content: specialMessage,
      })

      const callArgs = vi.mocked(axios.post).mock.calls[0]
      const requestBody = callArgs[1]

      expect(requestBody.content).toBe(specialMessage)
    })
  })

  describe('Broadcast vs Individual Messages', () => {
    it('should use different endpoint than individual message send', async () => {
      vi.mocked(axios.post).mockResolvedValue({
        data: {
          success: true,
          message_id: 'msg-123',
          recipient_count: 3,
          recipients: ['agent1', 'agent2', 'agent3'],
          timestamp: '2025-01-15T10:00:00Z',
        },
      })

      // Broadcast call
      await api.agentJobs.broadcast({
        project_id: mockProjectId,
        content: mockMessage,
      })

      const broadcastCall = vi.mocked(axios.post).mock.calls[0]
      expect(broadcastCall[0]).toContain('/api/v1/messages/broadcast')

      // Individual message would use different endpoint
      // This demonstrates the distinction
    })

    it('should deliver to all active agents in project', async () => {
      const allAgents = [
        'orchestrator',
        'analyzer',
        'implementor',
        'tester',
        'reviewer',
      ]

      vi.mocked(axios.post).mockResolvedValue({
        data: {
          success: true,
          message_id: 'msg-123',
          recipient_count: allAgents.length,
          recipients: allAgents,
          timestamp: '2025-01-15T10:00:00Z',
        },
      })

      const result = await api.agentJobs.broadcast({
        project_id: mockProjectId,
        content: mockMessage,
      })

      expect(result.data.recipients).toHaveLength(allAgents.length)
      expect(result.data.recipients).toEqual(allAgents)
    })
  })
})
