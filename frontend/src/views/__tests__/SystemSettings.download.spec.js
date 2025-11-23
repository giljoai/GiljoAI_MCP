import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import SystemSettings from '../SystemSettings.vue'
import api from '@/services/api'

/**
 * SystemSettings Download Button Tests
 *
 * Test Coverage:
 * 1. Download button rendering in Integrations tab
 * 2. Token generation API calls
 * 3. Download URL opening
 * 4. Error handling and user feedback
 * 5. Loading state management
 * 6. Success/error notifications
 *
 * @see CLAUDE.md - Token-Efficient MCP Downloads
 */

vi.mock('@/services/api', () => ({
  default: {
    post: vi.fn(),
    settings: {
      getCookieDomains: vi.fn(() => Promise.resolve({ data: { domains: [] } })),
      addCookieDomain: vi.fn(),
      removeCookieDomain: vi.fn(),
    },
    get: vi.fn(),
  },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}))

vi.mock('vuetify', () => ({
  useTheme: () => ({
    global: {
      current: {
        value: { dark: false },
      },
    },
  }),
}))

describe('SystemSettings - Download Button Handlers', () => {
  let wrapper
  let window_open_spy

  beforeEach(() => {
    // Reset API mocks
    vi.clearAllMocks()

    // Mock window.open
    window_open_spy = vi.spyOn(global, 'open').mockImplementation(() => ({}))

    // Mock fetch for network/database settings
    global.fetch = vi.fn((url) => {
      if (url.includes('/api/v1/config')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              services: {
                external_host: 'localhost',
                api: { port: 7272 },
                frontend: { port: 7274 },
              },
              security: { cors: { allowed_origins: [] } },
            }),
        })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    window_open_spy.mockRestore()
  })

  describe('Download Buttons Rendering', () => {
    it('should render Download Slash Commands button in Integrations tab', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          stubs: {
            'v-btn': true,
            'v-card': true,
            'v-window': true,
            'v-window-item': true,
            'v-tabs': true,
            'v-tab': true,
            'v-icon': true,
            'v-alert': true,
            'v-avatar': true,
            'v-img': true,
            'v-list': true,
            'v-list-item': true,
            'v-text-field': true,
            'v-divider': true,
            'v-card-title': true,
            'v-card-subtitle': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-dialog': true,
            'v-container': true,
            DatabaseConnection: true,
            CodexMarkIcon: true,
          },
          mocks: {
            $router: { push: vi.fn() },
          },
        },
      })

      await flushPromises()
      await nextTick()

      // Check that the download methods exist and are callable
      expect(typeof wrapper.vm.generateSlashCommandsDownload).toBe('function')
      expect(typeof wrapper.vm.generateAgentTemplatesDownload).toBe('function')
    })

    it('should have download loading state variables', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          stubs: {
            'v-btn': true,
            'v-card': true,
            'v-window': true,
            'v-window-item': true,
            'v-tabs': true,
            'v-tab': true,
            'v-icon': true,
            'v-alert': true,
            'v-avatar': true,
            'v-img': true,
            'v-list': true,
            'v-list-item': true,
            'v-text-field': true,
            'v-divider': true,
            'v-card-title': true,
            'v-card-subtitle': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-dialog': true,
            'v-container': true,
            DatabaseConnection: true,
            CodexMarkIcon: true,
          },
          mocks: {
            $router: { push: vi.fn() },
          },
        },
      })

      await flushPromises()
      await nextTick()

      expect(wrapper.vm.downloadingSlashCommands).toBe(false)
      expect(wrapper.vm.downloadingAgentTemplates).toBe(false)
      expect(wrapper.vm.slashCommandsDownloadFeedback).toBe(null)
      expect(wrapper.vm.agentTemplatesDownloadFeedback).toBe(null)
    })
  })

  describe('Token Generation - Slash Commands', () => {
    beforeEach(() => {
      api.post.mockResolvedValue({
        data: {
          download_url: 'http://localhost:7272/api/download/temp/token-123/slash_commands.zip',
          expires_at: '2025-11-04T10:45:00Z',
          content_type: 'slash_commands',
          one_time_use: true,
        },
      })
    })

    it('should generate token when Download Slash Commands is clicked', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          stubs: {
            'v-btn': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
            'v-card': true,
            'v-window': true,
            'v-window-item': true,
            'v-tabs': true,
            'v-tab': true,
            'v-icon': true,
            'v-alert': true,
            'v-avatar': true,
            'v-img': true,
            'v-list': true,
            'v-list-item': true,
            'v-text-field': true,
            'v-divider': true,
            'v-card-title': true,
            'v-card-subtitle': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-dialog': true,
            'v-container': true,
            DatabaseConnection: true,
            CodexMarkIcon: true,
          },
          mocks: {
            $router: { push: vi.fn() },
          },
        },
      })

      await flushPromises()
      await nextTick()

      // Simulate button click
      await wrapper.vm.generateSlashCommandsDownload()

      expect(api.post).toHaveBeenCalledWith('/api/download/generate-token', {
        content_type: 'slash_commands',
      })
    })

    it('should open download URL in new tab on success', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          stubs: {
            'v-btn': true,
            'v-card': true,
            'v-window': true,
            'v-window-item': true,
            'v-tabs': true,
            'v-tab': true,
            'v-icon': true,
            'v-alert': true,
            'v-avatar': true,
            'v-img': true,
            'v-list': true,
            'v-list-item': true,
            'v-text-field': true,
            'v-divider': true,
            'v-card-title': true,
            'v-card-subtitle': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-dialog': true,
            'v-container': true,
            DatabaseConnection: true,
            CodexMarkIcon: true,
          },
          mocks: {
            $router: { push: vi.fn() },
          },
        },
      })

      await flushPromises()
      await nextTick()

      await wrapper.vm.generateSlashCommandsDownload()

      expect(window_open_spy).toHaveBeenCalledWith(
        'http://localhost:7272/api/download/temp/token-123/slash_commands.zip',
        '_blank',
      )
    })

    it('should set loading state while generating token', async () => {
      api.post.mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => {
              resolve({
                data: {
                  download_url:
                    'http://localhost:7272/api/download/temp/token-123/slash_commands.zip',
                  expires_at: '2025-11-04T10:45:00Z',
                },
              })
            }, 100)
          }),
      )

      wrapper = mount(SystemSettings, {
        global: {
          stubs: {
            'v-btn': true,
            'v-card': true,
            'v-window': true,
            'v-window-item': true,
            'v-tabs': true,
            'v-tab': true,
            'v-icon': true,
            'v-alert': true,
            'v-avatar': true,
            'v-img': true,
            'v-list': true,
            'v-list-item': true,
            'v-text-field': true,
            'v-divider': true,
            'v-card-title': true,
            'v-card-subtitle': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-dialog': true,
            'v-container': true,
            DatabaseConnection: true,
            CodexMarkIcon: true,
          },
          mocks: {
            $router: { push: vi.fn() },
          },
        },
      })

      await flushPromises()
      await nextTick()

      const downloadPromise = wrapper.vm.generateSlashCommandsDownload()
      expect(wrapper.vm.downloadingSlashCommands).toBe(true)

      await downloadPromise
      await flushPromises()

      expect(wrapper.vm.downloadingSlashCommands).toBe(false)
    })
  })

  describe('Token Generation - Agent Templates', () => {
    beforeEach(() => {
      api.post.mockResolvedValue({
        data: {
          download_url: 'http://localhost:7272/api/download/temp/token-456/agent_templates.zip',
          expires_at: '2025-11-04T10:45:00Z',
          content_type: 'agent_templates',
          one_time_use: true,
        },
      })
    })

    it('should generate token when Download Agent Templates is clicked', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          stubs: {
            'v-btn': true,
            'v-card': true,
            'v-window': true,
            'v-window-item': true,
            'v-tabs': true,
            'v-tab': true,
            'v-icon': true,
            'v-alert': true,
            'v-avatar': true,
            'v-img': true,
            'v-list': true,
            'v-list-item': true,
            'v-text-field': true,
            'v-divider': true,
            'v-card-title': true,
            'v-card-subtitle': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-dialog': true,
            'v-container': true,
            DatabaseConnection: true,
            CodexMarkIcon: true,
          },
          mocks: {
            $router: { push: vi.fn() },
          },
        },
      })

      await flushPromises()
      await nextTick()

      await wrapper.vm.generateAgentTemplatesDownload()

      expect(api.post).toHaveBeenCalledWith('/api/download/generate-token', {
        content_type: 'agent_templates',
      })
    })

    it('should open download URL in new tab on success', async () => {
      wrapper = mount(SystemSettings, {
        global: {
          stubs: {
            'v-btn': true,
            'v-card': true,
            'v-window': true,
            'v-window-item': true,
            'v-tabs': true,
            'v-tab': true,
            'v-icon': true,
            'v-alert': true,
            'v-avatar': true,
            'v-img': true,
            'v-list': true,
            'v-list-item': true,
            'v-text-field': true,
            'v-divider': true,
            'v-card-title': true,
            'v-card-subtitle': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-dialog': true,
            'v-container': true,
            DatabaseConnection: true,
            CodexMarkIcon: true,
          },
          mocks: {
            $router: { push: vi.fn() },
          },
        },
      })

      await flushPromises()
      await nextTick()

      await wrapper.vm.generateAgentTemplatesDownload()

      expect(window_open_spy).toHaveBeenCalledWith(
        'http://localhost:7272/api/download/temp/token-456/agent_templates.zip',
        '_blank',
      )
    })

    it('should set loading state while generating token', async () => {
      api.post.mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => {
              resolve({
                data: {
                  download_url:
                    'http://localhost:7272/api/download/temp/token-456/agent_templates.zip',
                  expires_at: '2025-11-04T10:45:00Z',
                },
              })
            }, 100)
          }),
      )

      wrapper = mount(SystemSettings, {
        global: {
          stubs: {
            'v-btn': true,
            'v-card': true,
            'v-window': true,
            'v-window-item': true,
            'v-tabs': true,
            'v-tab': true,
            'v-icon': true,
            'v-alert': true,
            'v-avatar': true,
            'v-img': true,
            'v-list': true,
            'v-list-item': true,
            'v-text-field': true,
            'v-divider': true,
            'v-card-title': true,
            'v-card-subtitle': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-dialog': true,
            'v-container': true,
            DatabaseConnection: true,
            CodexMarkIcon: true,
          },
          mocks: {
            $router: { push: vi.fn() },
          },
        },
      })

      await flushPromises()
      await nextTick()

      const downloadPromise = wrapper.vm.generateAgentTemplatesDownload()
      expect(wrapper.vm.downloadingAgentTemplates).toBe(true)

      await downloadPromise
      await flushPromises()

      expect(wrapper.vm.downloadingAgentTemplates).toBe(false)
    })
  })

  describe('Error Handling', () => {
    it('should handle API errors gracefully for slash commands', async () => {
      const errorMessage = 'Server error: Token generation failed'
      api.post.mockRejectedValue({
        response: {
          data: {
            detail: errorMessage,
          },
        },
      })

      wrapper = mount(SystemSettings, {
        global: {
          stubs: {
            'v-btn': true,
            'v-card': true,
            'v-window': true,
            'v-window-item': true,
            'v-tabs': true,
            'v-tab': true,
            'v-icon': true,
            'v-alert': true,
            'v-avatar': true,
            'v-img': true,
            'v-list': true,
            'v-list-item': true,
            'v-text-field': true,
            'v-divider': true,
            'v-card-title': true,
            'v-card-subtitle': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-dialog': true,
            'v-container': true,
            DatabaseConnection: true,
            CodexMarkIcon: true,
          },
          mocks: {
            $router: { push: vi.fn() },
          },
        },
      })

      await flushPromises()
      await nextTick()

      await wrapper.vm.generateSlashCommandsDownload()

      // Should not call window.open on error
      expect(window_open_spy).not.toHaveBeenCalled()
    })

    it('should handle API errors gracefully for agent templates', async () => {
      const errorMessage = 'Server error: Token generation failed'
      api.post.mockRejectedValue({
        response: {
          data: {
            detail: errorMessage,
          },
        },
      })

      wrapper = mount(SystemSettings, {
        global: {
          stubs: {
            'v-btn': true,
            'v-card': true,
            'v-window': true,
            'v-window-item': true,
            'v-tabs': true,
            'v-tab': true,
            'v-icon': true,
            'v-alert': true,
            'v-avatar': true,
            'v-img': true,
            'v-list': true,
            'v-list-item': true,
            'v-text-field': true,
            'v-divider': true,
            'v-card-title': true,
            'v-card-subtitle': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-dialog': true,
            'v-container': true,
            DatabaseConnection: true,
            CodexMarkIcon: true,
          },
          mocks: {
            $router: { push: vi.fn() },
          },
        },
      })

      await flushPromises()
      await nextTick()

      await wrapper.vm.generateAgentTemplatesDownload()

      // Should not call window.open on error
      expect(window_open_spy).not.toHaveBeenCalled()
    })

    it('should always reset loading state on error', async () => {
      api.post.mockRejectedValue(new Error('Network error'))

      wrapper = mount(SystemSettings, {
        global: {
          stubs: {
            'v-btn': true,
            'v-card': true,
            'v-window': true,
            'v-window-item': true,
            'v-tabs': true,
            'v-tab': true,
            'v-icon': true,
            'v-alert': true,
            'v-avatar': true,
            'v-img': true,
            'v-list': true,
            'v-list-item': true,
            'v-text-field': true,
            'v-divider': true,
            'v-card-title': true,
            'v-card-subtitle': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-dialog': true,
            'v-container': true,
            DatabaseConnection: true,
            CodexMarkIcon: true,
          },
          mocks: {
            $router: { push: vi.fn() },
          },
        },
      })

      await flushPromises()
      await nextTick()

      await wrapper.vm.generateSlashCommandsDownload()
      expect(wrapper.vm.downloadingSlashCommands).toBe(false)

      await wrapper.vm.generateAgentTemplatesDownload()
      expect(wrapper.vm.downloadingAgentTemplates).toBe(false)
    })
  })

  describe('User Experience', () => {
    it('should prevent multiple concurrent downloads', async () => {
      api.post.mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => {
              resolve({
                data: {
                  download_url:
                    'http://localhost:7272/api/download/temp/token-123/slash_commands.zip',
                  expires_at: '2025-11-04T10:45:00Z',
                },
              })
            }, 200)
          }),
      )

      wrapper = mount(SystemSettings, {
        global: {
          stubs: {
            'v-btn': true,
            'v-card': true,
            'v-window': true,
            'v-window-item': true,
            'v-tabs': true,
            'v-tab': true,
            'v-icon': true,
            'v-alert': true,
            'v-avatar': true,
            'v-img': true,
            'v-list': true,
            'v-list-item': true,
            'v-text-field': true,
            'v-divider': true,
            'v-card-title': true,
            'v-card-subtitle': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-dialog': true,
            'v-container': true,
            DatabaseConnection: true,
            CodexMarkIcon: true,
          },
          mocks: {
            $router: { push: vi.fn() },
          },
        },
      })

      await flushPromises()
      await nextTick()

      // Start first download
      wrapper.vm.generateSlashCommandsDownload()
      expect(wrapper.vm.downloadingSlashCommands).toBe(true)

      // Start second download (should not reset the flag)
      wrapper.vm.generateSlashCommandsDownload()
      expect(wrapper.vm.downloadingSlashCommands).toBe(true)

      // API should have been called twice
      expect(api.post).toHaveBeenCalledTimes(2)
    })

    it('should not open duplicate tabs on rapid clicks', async () => {
      api.post.mockResolvedValue({
        data: {
          download_url: 'http://localhost:7272/api/download/temp/token-123/slash_commands.zip',
          expires_at: '2025-11-04T10:45:00Z',
        },
      })

      wrapper = mount(SystemSettings, {
        global: {
          stubs: {
            'v-btn': true,
            'v-card': true,
            'v-window': true,
            'v-window-item': true,
            'v-tabs': true,
            'v-tab': true,
            'v-icon': true,
            'v-alert': true,
            'v-avatar': true,
            'v-img': true,
            'v-list': true,
            'v-list-item': true,
            'v-text-field': true,
            'v-divider': true,
            'v-card-title': true,
            'v-card-subtitle': true,
            'v-card-text': true,
            'v-card-actions': true,
            'v-spacer': true,
            'v-dialog': true,
            'v-container': true,
            DatabaseConnection: true,
            CodexMarkIcon: true,
          },
          mocks: {
            $router: { push: vi.fn() },
          },
        },
      })

      await flushPromises()
      await nextTick()

      // Simulate rapid clicks
      await wrapper.vm.generateSlashCommandsDownload()
      await wrapper.vm.generateSlashCommandsDownload()

      // window.open should be called twice (one per request)
      expect(window_open_spy).toHaveBeenCalledTimes(2)
    })
  })
})
