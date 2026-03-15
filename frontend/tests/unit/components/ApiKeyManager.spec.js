import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import ApiKeyManager from '@/components/ApiKeyManager.vue'

// Mock the API module
vi.mock('@/services/api', () => ({
  default: {
    apiKeys: {
      list: vi.fn(),
      delete: vi.fn(),
    },
  },
}))

describe('ApiKeyManager', () => {
  let wrapper
  let api
  const mockApiKeys = [
    {
      id: 1,
      name: 'Test Key 1',
      key_prefix: 'gk_abc1',
      created_at: '2025-10-09T10:00:00Z',
      last_used: '2025-10-09T12:00:00Z'
    },
    {
      id: 2,
      name: 'Test Key 2',
      key_prefix: 'gk_def2',
      created_at: '2025-10-09T11:00:00Z',
      last_used: null
    }
  ]

  beforeEach(async () => {
    // Get the mocked API
    api = (await import('@/services/api')).default

    // Setup mock responses
    api.apiKeys.list.mockResolvedValue({ data: mockApiKeys })
    api.apiKeys.delete.mockResolvedValue({ data: { message: 'Key revoked' } })

    wrapper = mount(ApiKeyManager, {
      global: {
        plugins: [
          createTestingPinia({
            initialState: {}
          })
        ],
        stubs: {
          ApiKeyWizard: true
        }
      }
    })
  })

  it('loads API keys on mount', async () => {
    await wrapper.vm.$nextTick()
    expect(api.apiKeys.list).toHaveBeenCalled()
  })

  it('refreshes keys after event', async () => {
    await wrapper.vm.refreshKeys()
    expect(api.apiKeys.list).toHaveBeenCalled()
  })

  it('shows revoke dialog with key details', () => {
    const key = mockApiKeys[0]
    wrapper.vm.confirmRevoke(key)

    expect(wrapper.vm.showRevokeDialog).toBe(true)
    expect(wrapper.vm.keyToRevoke).toEqual(key)
  })

  it('revokeKey skips when no key is set', async () => {
    // revokeKey guards against null keyToRevoke
    wrapper.vm.keyToRevoke = null

    await wrapper.vm.revokeKey()
    expect(api.apiKeys.delete).not.toHaveBeenCalled()
  })

  it('allows revocation with correct DELETE confirmation', async () => {
    const key = mockApiKeys[0]
    wrapper.vm.keyToRevoke = key
    wrapper.vm.deleteConfirmation = 'DELETE'

    await wrapper.vm.revokeKey()
    expect(api.apiKeys.delete).toHaveBeenCalledWith(key.id)
  })

  it('humanizes timestamps correctly', () => {
    // Use a timestamp from a week ago
    const pastDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
    const result = wrapper.vm.humanizeTimestamp(pastDate)
    expect(result).toContain('ago') // Should include "ago" for past timestamps
  })

  it('shows "Never" for null timestamps', () => {
    const result = wrapper.vm.humanizeTimestamp(null)
    expect(result).toBe('Never')
  })
})
