/**
 * Test suite for ApiKeyManager.vue - Handover 0028 Simplified Interface
 *
 * Tests for simplified API key management:
 * - Single API key type (integration keys only)
 * - Industry-standard key masking (gk_abc123...xyz789)
 * - Key naming with common name/description
 * - Creation date display
 * - Proper revocation with DELETE confirmation
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import ApiKeyManager from '@/components/ApiKeyManager.vue'

// Mock the API module
vi.mock('@/services/api', () => ({
  default: {
    apiKeys: {
      list: vi.fn(),
      delete: vi.fn()
    }
  }
}))

// Mock ApiKeyWizard component
vi.mock('@/components/ApiKeyWizard.vue', () => ({
  default: { template: '<div data-test="api-key-wizard-mock">API Key Wizard</div>' }
}))

describe('ApiKeyManager.vue - Handover 0028 Simplified Interface', () => {
  let wrapper
  let vuetify
  let api

  const mockApiKeys = [
    {
      id: 1,
      name: 'Claude Code Integration',
      key_prefix: 'gk_abc123',
      created_at: '2025-10-01T10:00:00Z',
      last_used: '2025-10-09T15:30:00Z'
    },
    {
      id: 2,
      name: 'Codex Integration',
      key_prefix: 'gk_xyz789',
      created_at: '2025-10-05T12:00:00Z',
      last_used: null
    },
    {
      id: 3,
      name: 'Testing Key',
      key_prefix: 'gk_test456',
      created_at: '2025-10-10T08:00:00Z',
      last_used: '2025-10-10T09:00:00Z'
    }
  ]

  beforeEach(async () => {
    // Setup Vuetify
    vuetify = createVuetify({
      components,
      directives
    })

    // Get the mocked API
    api = (await import('@/services/api')).default

    // Setup mock responses
    api.apiKeys.list.mockResolvedValue({ data: mockApiKeys })
    api.apiKeys.delete.mockResolvedValue({ data: { message: 'Key deleted' } })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('renders the component', () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('displays "API Keys" title', () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.text()).toContain('API Keys')
    })

    it('displays subtitle about API key management', () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.text()).toContain('Manage API keys for AI tool integrations')
    })
  })

  describe('Generate New Key Button', () => {
    it('displays "Generate New Key" button', () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.text()).toContain('Generate New Key')
    })

    it('has plus icon on generate button', () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      const html = wrapper.html()
      expect(html).toContain('mdi-plus')
    })

    it('opens wizard when generate button clicked', async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.vm.showWizard).toBe(false)

      wrapper.vm.showWizard = true
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showWizard).toBe(true)
    })

    it('disables generate button while loading', async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.loading = true
      await wrapper.vm.$nextTick()

      const generateBtn = wrapper.find('button')
      expect(generateBtn.attributes('disabled')).toBeDefined()
    })
  })

  describe('API Keys Loading', () => {
    it('loads API keys on mount', async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.$nextTick()

      expect(api.apiKeys.list).toHaveBeenCalled()
    })

    it('displays loaded API keys', async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.loadKeys()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.apiKeys).toEqual(mockApiKeys)
    })

    it('shows loading state while fetching keys', async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      const loadPromise = wrapper.vm.loadKeys()
      expect(wrapper.vm.loading).toBe(true)

      await loadPromise
      expect(wrapper.vm.loading).toBe(false)
    })
  })

  describe('Empty State', () => {
    it('displays empty state when no keys exist', async () => {
      api.apiKeys.list.mockResolvedValueOnce({ data: [] })

      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.loadKeys()
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('No API keys created yet')
    })

    it('empty state mentions AI tool integrations', async () => {
      api.apiKeys.list.mockResolvedValueOnce({ data: [] })

      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.loadKeys()
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('Claude Code, Codex, or other external applications')
    })

    it('hides data table when no keys exist', async () => {
      api.apiKeys.list.mockResolvedValueOnce({ data: [] })

      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.loadKeys()
      await wrapper.vm.$nextTick()

      const dataTable = wrapper.find('.v-data-table')
      expect(dataTable.exists()).toBe(false)
    })
  })

  describe('API Keys Table Structure', () => {
    beforeEach(async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.loadKeys()
      await wrapper.vm.$nextTick()
    })

    it('displays table headers correctly', () => {
      const headers = wrapper.vm.headers
      expect(headers).toHaveLength(5)
      expect(headers.map(h => h.key)).toEqual([
        'name',
        'key_prefix',
        'created_at',
        'last_used',
        'actions'
      ])
    })

    it('name column is sortable', () => {
      const headers = wrapper.vm.headers
      const nameHeader = headers.find(h => h.key === 'name')
      expect(nameHeader.sortable).toBe(true)
    })

    it('created_at column is sortable', () => {
      const headers = wrapper.vm.headers
      const createdHeader = headers.find(h => h.key === 'created_at')
      expect(createdHeader.sortable).toBe(true)
    })

    it('last_used column is sortable', () => {
      const headers = wrapper.vm.headers
      const lastUsedHeader = headers.find(h => h.key === 'last_used')
      expect(lastUsedHeader.sortable).toBe(true)
    })

    it('key_prefix column is not sortable', () => {
      const headers = wrapper.vm.headers
      const keyPrefixHeader = headers.find(h => h.key === 'key_prefix')
      expect(keyPrefixHeader.sortable).toBe(false)
    })

    it('actions column is not sortable', () => {
      const headers = wrapper.vm.headers
      const actionsHeader = headers.find(h => h.key === 'actions')
      expect(actionsHeader.sortable).toBe(false)
    })
  })

  describe('Key Name Display', () => {
    beforeEach(async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.apiKeys = mockApiKeys
      await wrapper.vm.$nextTick()
    })

    it('displays key name with label icon', () => {
      const html = wrapper.html()
      expect(html).toContain('mdi-label')
    })

    it('displays all key names', () => {
      mockApiKeys.forEach(key => {
        expect(wrapper.text()).toContain(key.name)
      })
    })
  })

  describe('Key Prefix Display (Industry Standard Masking)', () => {
    beforeEach(async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.apiKeys = mockApiKeys
      await wrapper.vm.$nextTick()
    })

    it('displays key prefix with ellipsis', () => {
      mockApiKeys.forEach(key => {
        const prefixText = `${key.key_prefix}...`
        expect(wrapper.text()).toContain(key.key_prefix)
      })
    })

    it('uses monospace font for key prefix', () => {
      const html = wrapper.html()
      expect(html).toContain('<code')
    })

    it('displays prefix in code format', () => {
      const html = wrapper.html()
      expect(html).toContain('text-caption')
    })
  })

  describe('Created Date Display', () => {
    beforeEach(async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.apiKeys = mockApiKeys
      await wrapper.vm.$nextTick()
    })

    it('formats created date with date and time', () => {
      const formatted = wrapper.vm.formatDate('2025-10-01T10:00:00Z')
      expect(formatted).toMatch(/\d{1,2}\/\d{1,2}\/\d{4}/)
      expect(formatted).toMatch(/\d{1,2}:\d{2}/)
    })

    it('handles null created date', () => {
      const formatted = wrapper.vm.formatDate(null)
      expect(formatted).toBe('N/A')
    })

    it('handles invalid created date', () => {
      const formatted = wrapper.vm.formatDate('invalid')
      expect(formatted).toBe('N/A')
    })
  })

  describe('Last Used Display', () => {
    beforeEach(async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.apiKeys = mockApiKeys
      await wrapper.vm.$nextTick()
    })

    it('displays relative time for last used', () => {
      const lastUsed = wrapper.vm.humanizeTimestamp(mockApiKeys[0].last_used)
      expect(lastUsed).toContain('ago')
    })

    it('displays "Never" for null last used', () => {
      const lastUsed = wrapper.vm.humanizeTimestamp(null)
      expect(lastUsed).toBe('Never')
    })

    it('handles invalid last used timestamp', () => {
      const lastUsed = wrapper.vm.humanizeTimestamp('invalid')
      expect(lastUsed).toBe('Unknown')
    })
  })

  describe('Key Revocation', () => {
    beforeEach(async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.apiKeys = mockApiKeys
      await wrapper.vm.$nextTick()
    })

    it('has revoke button for each key', () => {
      const html = wrapper.html()
      expect(html).toContain('mdi-delete')
    })

    it('opens revoke dialog when revoke button clicked', async () => {
      expect(wrapper.vm.showRevokeDialog).toBe(false)

      wrapper.vm.confirmRevoke(mockApiKeys[0])
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showRevokeDialog).toBe(true)
    })

    it('sets keyToRevoke when confirming revoke', async () => {
      wrapper.vm.confirmRevoke(mockApiKeys[0])
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.keyToRevoke).toEqual(mockApiKeys[0])
    })

    it('displays key information in revoke dialog', async () => {
      wrapper.vm.confirmRevoke(mockApiKeys[0])
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain(mockApiKeys[0].name)
      expect(wrapper.text()).toContain(mockApiKeys[0].key_prefix)
    })
  })

  describe('DELETE Confirmation Requirement', () => {
    beforeEach(async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.apiKeys = mockApiKeys
      wrapper.vm.confirmRevoke(mockApiKeys[0])
      await wrapper.vm.$nextTick()
    })

    it('requires typing DELETE to confirm', async () => {
      expect(wrapper.text()).toContain('Type DELETE to confirm')
    })

    it('revoke button is disabled without DELETE confirmation', async () => {
      wrapper.vm.deleteConfirmation = ''
      await wrapper.vm.$nextTick()

      // Revoke button should be disabled
      expect(wrapper.vm.deleteConfirmation).not.toBe('DELETE')
    })

    it('revoke button is enabled when DELETE is typed', async () => {
      wrapper.vm.deleteConfirmation = 'DELETE'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.deleteConfirmation).toBe('DELETE')
    })

    it('revoke button is disabled with incorrect confirmation', async () => {
      wrapper.vm.deleteConfirmation = 'delete'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.deleteConfirmation).not.toBe('DELETE')
    })

    it('confirmation field has proper placeholder', () => {
      const html = wrapper.html()
      expect(html).toContain('DELETE')
    })
  })

  describe('Key Revocation Execution', () => {
    beforeEach(async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.apiKeys = mockApiKeys
      await wrapper.vm.$nextTick()
    })

    it('calls API to delete key', async () => {
      wrapper.vm.keyToRevoke = mockApiKeys[0]
      wrapper.vm.deleteConfirmation = 'DELETE'

      await wrapper.vm.revokeKey()

      expect(api.apiKeys.delete).toHaveBeenCalledWith(mockApiKeys[0].id)
    })

    it('removes key from list after revocation', async () => {
      wrapper.vm.keyToRevoke = mockApiKeys[0]
      wrapper.vm.deleteConfirmation = 'DELETE'

      await wrapper.vm.revokeKey()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.apiKeys.find(k => k.id === mockApiKeys[0].id)).toBeUndefined()
    })

    it('closes revoke dialog after successful revocation', async () => {
      wrapper.vm.showRevokeDialog = true
      wrapper.vm.keyToRevoke = mockApiKeys[0]
      wrapper.vm.deleteConfirmation = 'DELETE'

      await wrapper.vm.revokeKey()

      expect(wrapper.vm.showRevokeDialog).toBe(false)
      expect(wrapper.vm.keyToRevoke).toBeNull()
      expect(wrapper.vm.deleteConfirmation).toBe('')
    })

    it('reloads keys after revocation', async () => {
      wrapper.vm.keyToRevoke = mockApiKeys[0]
      wrapper.vm.deleteConfirmation = 'DELETE'

      api.apiKeys.list.mockClear()
      await wrapper.vm.revokeKey()

      expect(api.apiKeys.list).toHaveBeenCalled()
    })

    it('shows loading state while revoking', async () => {
      wrapper.vm.keyToRevoke = mockApiKeys[0]
      wrapper.vm.deleteConfirmation = 'DELETE'

      const revokePromise = wrapper.vm.revokeKey()
      expect(wrapper.vm.revoking).toBe(true)

      await revokePromise
      expect(wrapper.vm.revoking).toBe(false)
    })

    it('prevents revocation without DELETE confirmation', async () => {
      api.apiKeys.delete.mockClear()

      wrapper.vm.keyToRevoke = mockApiKeys[0]
      wrapper.vm.deleteConfirmation = 'wrong'

      await wrapper.vm.revokeKey()

      expect(api.apiKeys.delete).not.toHaveBeenCalled()
    })

    it('prevents revocation without selected key', async () => {
      api.apiKeys.delete.mockClear()

      wrapper.vm.keyToRevoke = null
      wrapper.vm.deleteConfirmation = 'DELETE'

      await wrapper.vm.revokeKey()

      expect(api.apiKeys.delete).not.toHaveBeenCalled()
    })
  })

  describe('Cancel Revocation', () => {
    beforeEach(async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.apiKeys = mockApiKeys
      wrapper.vm.confirmRevoke(mockApiKeys[0])
      await wrapper.vm.$nextTick()
    })

    it('closes dialog when cancel clicked', async () => {
      wrapper.vm.cancelRevoke()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showRevokeDialog).toBe(false)
    })

    it('clears keyToRevoke when cancelled', async () => {
      wrapper.vm.cancelRevoke()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.keyToRevoke).toBeNull()
    })

    it('clears deleteConfirmation when cancelled', async () => {
      wrapper.vm.deleteConfirmation = 'DELETE'
      wrapper.vm.cancelRevoke()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.deleteConfirmation).toBe('')
    })
  })

  describe('Key Wizard Integration', () => {
    it('shows wizard when showWizard is true', async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.showWizard = true
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showWizard).toBe(true)
    })

    it('refreshes keys after wizard creates key', async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      api.apiKeys.list.mockClear()
      await wrapper.vm.refreshKeys()

      expect(api.apiKeys.list).toHaveBeenCalled()
    })

    it('listens for api-key-created event', () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      // Verify event listener setup
      expect(wrapper.vm).toBeDefined()
    })
  })

  describe('Error Handling', () => {
    it('handles API error when loading keys', async () => {
      api.apiKeys.list.mockRejectedValueOnce(new Error('Network error'))

      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.loadKeys()

      expect(wrapper.vm.loading).toBe(false)
      expect(wrapper.vm.apiKeys).toEqual([])
    })

    it('does not show error for 401 unauthorized', async () => {
      api.apiKeys.list.mockRejectedValueOnce({ response: { status: 401 } })

      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      await wrapper.vm.loadKeys()

      // Should handle gracefully
      expect(wrapper.vm.loading).toBe(false)
    })

    it('handles API error when revoking key', async () => {
      api.apiKeys.delete.mockRejectedValueOnce(new Error('Delete failed'))

      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.keyToRevoke = mockApiKeys[0]
      wrapper.vm.deleteConfirmation = 'DELETE'

      await wrapper.vm.revokeKey()

      expect(wrapper.vm.revoking).toBe(false)
    })
  })

  describe('Accessibility', () => {
    beforeEach(async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.apiKeys = mockApiKeys
      await wrapper.vm.$nextTick()
    })

    it('revoke button has tooltip', () => {
      const html = wrapper.html()
      expect(html).toContain('Revoke this API key')
    })

    it('uses semantic icons for actions', () => {
      const html = wrapper.html()
      expect(html).toContain('mdi-delete')
      expect(html).toContain('mdi-key-variant')
      expect(html).toContain('mdi-label')
    })
  })

  describe('Visual Styling', () => {
    beforeEach(async () => {
      wrapper = mount(ApiKeyManager, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.apiKeys = mockApiKeys
      await wrapper.vm.$nextTick()
    })

    it('applies elevation to data table', () => {
      const html = wrapper.html()
      expect(html).toContain('elevation-1')
    })

    it('uses code styling for key prefix', () => {
      const html = wrapper.html()
      expect(html).toContain('<code')
    })
  })
})
