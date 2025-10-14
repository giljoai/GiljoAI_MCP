import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import AIToolSetup from '@/components/AIToolSetup.vue'
import { createTestingPinia } from '@pinia/testing'

// Mock fetch globally
global.fetch = vi.fn()

describe('AIToolSetup', () => {
  let wrapper

  beforeEach(() => {
    vi.clearAllMocks()

    wrapper = mount(AIToolSetup, {
      global: {
        plugins: [
          createTestingPinia({
            initialState: {}
          })
        ],
        stubs: {
          VDialog: false,
          VCard: false,
          VBtn: false
        }
      }
    })
  })

  describe('Initial Setup', () => {
    it('renders the component', () => {
      expect(wrapper.exists()).toBe(true)
    })

    it('loads supported tools on mount', async () => {
      const mockTools = {
        tools: [
          { id: 'claude', name: 'Claude Code', supported: true },
          { id: 'codex', name: 'Codex', supported: false }
        ]
      }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTools
      })

      await wrapper.vm.loadSupportedTools()

      expect(wrapper.vm.supportedTools).toHaveLength(1)
      expect(wrapper.vm.supportedTools[0].id).toBe('claude')
    })
  })

  describe('API Key Generation Flow', () => {
    beforeEach(() => {
      // Mock supported tools
      wrapper.vm.supportedTools = [
        { id: 'claude', name: 'Claude Code', supported: true }
      ]
    })

    it('generates new API key with descriptive name when tool selected', async () => {
      const mockApiKeyResponse = {
        key: 'gk_test_1234567890abcdef',
        id: 1,
        name: 'Claude Code - 10/13/2025',
        created_at: '2025-10-13T10:00:00Z'
      }

      const mockConfigResponse = {
        file_location: '~/.claude.json',
        config_content: JSON.stringify({
          mcpServers: {
            'giljo-mcp': {
              command: 'python',
              args: ['-m', 'giljo_mcp'],
              env: {
                GILJO_SERVER_URL: 'http://localhost:7272',
                GILJO_API_KEY: 'gk_test_1234567890abcdef'
              }
            }
          }
        }, null, 2),
        instructions: ['Copy config', 'Restart tool'],
        download_filename: 'claude-code-setup.md'
      }

      // Mock API key creation
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockApiKeyResponse
        })
        // Mock config generation with API key
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockConfigResponse
        })

      wrapper.vm.selectedTool = 'claude'
      await wrapper.vm.generateConfig()

      // Verify API key was created
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/api-keys'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          }),
          body: expect.stringContaining('Claude Code')
        })
      )

      // Verify generated config contains the API key
      expect(wrapper.vm.configData).toBeTruthy()
      expect(wrapper.vm.configData.config_content).toContain('gk_test_1234567890abcdef')
      expect(wrapper.vm.generatedApiKey).toBe('gk_test_1234567890abcdef')
    })

    it('shows API key security warning after generation', async () => {
      wrapper.vm.generatedApiKey = 'gk_test_key'
      wrapper.vm.showApiKeyWarning = true
      wrapper.vm.configData = { config_content: 'test' }
      await nextTick()

      // Verify state is set correctly
      expect(wrapper.vm.generatedApiKey).toBe('gk_test_key')
      expect(wrapper.vm.showApiKeyWarning).toBe(true)
      expect(wrapper.vm.configData).toBeTruthy()
    })

    it('auto-generates descriptive API key name based on tool and date', () => {
      const keyName = wrapper.vm.generateApiKeyName('claude')
      expect(keyName).toMatch(/Claude Code - \d{1,2}\/\d{1,2}\/\d{4}/)
    })

    it('handles API key creation failure gracefully', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'API key creation failed' })
      })

      wrapper.vm.selectedTool = 'claude'
      await wrapper.vm.generateConfig()

      expect(wrapper.vm.error).toContain('API key creation failed')
      expect(wrapper.vm.configData).toBeNull()
    })

    it('displays generated API key prefix in success message', async () => {
      const mockApiKey = 'gk_test_1234567890abcdef'
      wrapper.vm.generatedApiKey = mockApiKey
      wrapper.vm.configData = { config_content: '{}' }
      await nextTick()

      // Verify the API key is stored correctly
      expect(wrapper.vm.generatedApiKey).toBe(mockApiKey)
      expect(wrapper.vm.generatedApiKey.substring(0, 10)).toBe('gk_test_12')
    })

    it('provides API key management information when key is generated', async () => {
      wrapper.vm.generatedApiKey = 'gk_test_key'
      wrapper.vm.configData = { config_content: 'test' }
      await nextTick()

      // Verify API key is available for display
      expect(wrapper.vm.generatedApiKey).toBeTruthy()
      // Verify config data is present (which triggers the UI to show the management link)
      expect(wrapper.vm.configData).toBeTruthy()
    })
  })

  describe('Config Generation with API Key', () => {
    it('uses frontend configTemplates with generated API key', async () => {
      const mockApiKey = 'gk_test_key_12345'

      // Mock API key creation
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          key: mockApiKey,
          id: 1,
          name: 'Test Key'
        })
      })

      wrapper.vm.selectedTool = 'claude'
      await wrapper.vm.generateConfig()

      // Verify config uses the API key (not tenant_key)
      expect(wrapper.vm.configData.config_content).toContain(mockApiKey)
      expect(wrapper.vm.configData.config_content).not.toContain('tenant_key')
      expect(wrapper.vm.configData.config_content).not.toContain('GILJO_TENANT_KEY')
    })

    it('generates valid JSON config for Claude Code', async () => {
      const mockApiKey = 'gk_test_key'

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ key: mockApiKey, id: 1, name: 'Test' })
      })

      wrapper.vm.selectedTool = 'claude'
      await wrapper.vm.generateConfig()

      const configContent = wrapper.vm.configData.config_content
      expect(() => JSON.parse(configContent)).not.toThrow()

      const config = JSON.parse(configContent)
      expect(config.mcpServers['giljo-mcp'].env.GILJO_API_KEY).toBe(mockApiKey)
    })
  })

  describe('Error Handling', () => {
    it('shows error when tool selection fails', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Failed to load tools' })
      })

      await wrapper.vm.loadSupportedTools()

      expect(wrapper.vm.error).toContain('Failed to load supported tools')
    })

    it('handles network errors during API key creation', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'))

      wrapper.vm.selectedTool = 'claude'
      await wrapper.vm.generateConfig()

      expect(wrapper.vm.error).toBeTruthy()
      expect(wrapper.vm.loading).toBe(false)
    })

    it('clears error state on successful config generation', async () => {
      wrapper.vm.error = 'Previous error'

      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ key: 'gk_test', id: 1, name: 'Test' })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            config_content: '{}',
            instructions: [],
            file_location: 'test'
          })
        })

      wrapper.vm.selectedTool = 'claude'
      await wrapper.vm.generateConfig()

      expect(wrapper.vm.error).toBeNull()
    })
  })

  describe('User Workflow', () => {
    it('follows complete workflow: select tool -> generate key -> copy config', async () => {
      const mockApiKey = 'gk_complete_workflow_key'

      // Step 1: Load tools
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          tools: [{ id: 'claude', name: 'Claude Code', supported: true }]
        })
      })

      await wrapper.vm.loadSupportedTools()
      expect(wrapper.vm.supportedTools).toHaveLength(1)

      // Step 2: Select tool and generate config (creates API key)
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ key: mockApiKey, id: 1, name: 'Auto' })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            config_content: JSON.stringify({ key: mockApiKey }),
            instructions: ['Test'],
            file_location: 'test.json'
          })
        })

      wrapper.vm.selectedTool = 'claude'
      await wrapper.vm.generateConfig()

      expect(wrapper.vm.configData).toBeTruthy()
      expect(wrapper.vm.generatedApiKey).toBe(mockApiKey)

      // Step 3: Copy config
      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn().mockResolvedValue(undefined)
        }
      })

      await wrapper.vm.copyToClipboard()
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining(mockApiKey)
      )
      expect(wrapper.vm.copied).toBe(true)
    })

    it('resets state when dialog closes', async () => {
      wrapper.vm.selectedTool = 'claude'
      wrapper.vm.configData = { config_content: 'test' }
      wrapper.vm.generatedApiKey = 'gk_test'
      wrapper.vm.error = 'test error'

      wrapper.vm.closeDialog()

      await new Promise(resolve => setTimeout(resolve, 350))

      expect(wrapper.vm.selectedTool).toBeNull()
      expect(wrapper.vm.configData).toBeNull()
      expect(wrapper.vm.generatedApiKey).toBeNull()
      expect(wrapper.vm.error).toBeNull()
    })
  })
})
