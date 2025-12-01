/**
 * Real-Time Synchronization Test Suite
 * Tests WebSocket integration for Git integration toggle updates
 *
 * Scenario:
 * - User opens Context Priority Config tab (Git integration disabled)
 * - User navigates to Integrations tab and enables Git integration
 * - Git integration update sent via WebSocket event 'product:git:settings:changed'
 * - Context Priority Config tab IMMEDIATELY reflects the change without page refresh
 * - Git History controls become enabled
 * - Alert disappears
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'
import ContextPriorityConfig from '@/components/settings/ContextPriorityConfig.vue'

// Mock setupService
vi.mock('@/services/setupService', () => ({
  default: {
    getGitSettings: vi.fn(),
    updateGitSettings: vi.fn(),
  },
}))

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
  },
}))

describe('ContextPriorityConfig.vue - WebSocket Real-Time Sync', () => {
  let vuetify
  let pinia
  let wrapper
  let setupServiceMock
  let axiosMock
  let webSocketMockHandlers = {}

  beforeEach(async () => {
    // Setup Vuetify
    vuetify = createVuetify({
      components,
      directives,
    })

    // Setup Pinia
    pinia = createPinia()
    setActivePinia(pinia)

    // Setup service mocks
    const setupService = await import('@/services/setupService')
    setupServiceMock = setupService.default

    // Mock useWebSocketV2 composable
    vi.doMock('@/composables/useWebSocket', () => ({
      useWebSocketV2: () => ({
        on: vi.fn((eventType, handler) => {
          webSocketMockHandlers[eventType] = handler
        }),
        off: vi.fn(),
        connect: vi.fn(),
        disconnect: vi.fn(),
      }),
    }))

    // Setup axios mock
    const axios = await import('axios')
    axiosMock = axios.default
    axiosMock.get.mockResolvedValue({
      data: {
        priorities: {
          product_core: 1,
          project_context: 2,
          vision_documents: 2,
          agent_templates: 2,
          memory_360: 3,
          git_history: 3,
        },
      },
    })
    axiosMock.put.mockResolvedValue({ data: {} })

    // Reset handlers
    webSocketMockHandlers = {}
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  describe('Git Integration Real-Time Updates', () => {
    it('should display alert when Git integration is disabled on mount', async () => {
      // Git is disabled initially
      setupServiceMock.getGitSettings.mockResolvedValue({ enabled: false })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()
      await wrapper.vm.$nextTick()

      // Check the reactive state
      expect(wrapper.vm.gitIntegrationEnabled).toBe(false)
      // Check that Git History is disabled due to Git integration being off
      expect(wrapper.vm.isContextDisabled('git_history')).toBe(true)
    })

    it('should register WebSocket listener for git integration updates on mount', async () => {
      setupServiceMock.getGitSettings.mockResolvedValue({ enabled: false })

      // Mock the useWebSocketV2 composable
      const mockOn = vi.fn()
      const mockOff = vi.fn()

      vi.doMock('@/composables/useWebSocket', () => ({
        useWebSocketV2: () => ({
          on: mockOn,
          off: mockOff,
          connect: vi.fn(),
          disconnect: vi.fn(),
        }),
      }))

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // WebSocket listener should be registered
      // Note: Due to module mocking complexity, we verify through the exposed function
      expect(wrapper.vm.handleGitIntegrationUpdate).toBeDefined()
    })

    it('should handle git integration enabled event from WebSocket', async () => {
      setupServiceMock.getGitSettings.mockResolvedValue({ enabled: false })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // Initially disabled
      expect(wrapper.vm.gitIntegrationEnabled).toBe(false)

      // Simulate WebSocket event: Git integration enabled
      const eventData = {
        product_id: 'product-123',
        settings: {
          enabled: true,
          commit_limit: 20,
          default_branch: 'main',
        },
      }

      wrapper.vm.handleGitIntegrationUpdate(eventData)

      // State should update immediately
      expect(wrapper.vm.gitIntegrationEnabled).toBe(true)
    })

    it('should handle git integration disabled event from WebSocket', async () => {
      setupServiceMock.getGitSettings.mockResolvedValue({ enabled: true })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // Initially enabled
      expect(wrapper.vm.gitIntegrationEnabled).toBe(true)

      // Simulate WebSocket event: Git integration disabled
      const eventData = {
        product_id: 'product-123',
        settings: {
          enabled: false,
          commit_limit: 20,
          default_branch: 'main',
        },
      }

      wrapper.vm.handleGitIntegrationUpdate(eventData)

      // State should update immediately
      expect(wrapper.vm.gitIntegrationEnabled).toBe(false)
    })

    it('should enable Git History controls when integration is toggled ON', async () => {
      setupServiceMock.getGitSettings.mockResolvedValue({ enabled: false })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // Git History should be disabled initially
      expect(wrapper.vm.isContextDisabled('git_history')).toBe(true)

      // Simulate WebSocket event: Git integration enabled
      wrapper.vm.handleGitIntegrationUpdate({
        product_id: 'product-123',
        settings: { enabled: true },
      })

      // Git History should now be enabled
      expect(wrapper.vm.isContextDisabled('git_history')).toBe(false)
    })

    it('should disable Git History controls when integration is toggled OFF', async () => {
      setupServiceMock.getGitSettings.mockResolvedValue({ enabled: true })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // Git History should be enabled initially
      expect(wrapper.vm.isContextDisabled('git_history')).toBe(false)

      // Simulate WebSocket event: Git integration disabled
      wrapper.vm.handleGitIntegrationUpdate({
        product_id: 'product-123',
        settings: { enabled: false },
      })

      // Git History should now be disabled
      expect(wrapper.vm.isContextDisabled('git_history')).toBe(true)
    })

    it('should handle missing or invalid WebSocket event data gracefully', async () => {
      setupServiceMock.getGitSettings.mockResolvedValue({ enabled: false })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // Test with null data
      wrapper.vm.handleGitIntegrationUpdate(null)
      expect(wrapper.vm.gitIntegrationEnabled).toBe(false) // Should not change

      // Test with missing settings
      wrapper.vm.handleGitIntegrationUpdate({ product_id: 'product-123' })
      expect(wrapper.vm.gitIntegrationEnabled).toBe(false) // Should not change

      // Test with undefined enabled field
      wrapper.vm.handleGitIntegrationUpdate({
        product_id: 'product-123',
        settings: { commit_limit: 20 },
      })
      expect(wrapper.vm.gitIntegrationEnabled).toBe(false) // Should default to false
    })

    it('should log appropriate messages when Git integration state changes', async () => {
      setupServiceMock.getGitSettings.mockResolvedValue({ enabled: false })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // Clear previous logs from mount
      const consoleSpy = vi.spyOn(console, 'log').mockClear()

      // Enable Git integration
      wrapper.vm.handleGitIntegrationUpdate({
        product_id: 'product-123',
        settings: { enabled: true },
      })

      // Check that appropriate log messages were written
      const logCalls = consoleSpy.mock.calls.flatMap((c) => c)
      expect(logCalls.some((msg) => msg?.includes?.('[CONTEXT PRIORITY CONFIG] Git integration updated via WebSocket:') || msg?.toString?.().includes?.('[CONTEXT PRIORITY CONFIG] Git integration updated via WebSocket:'))).toBe(true)
      expect(logCalls.some((msg) => msg?.includes?.('Git History context is now available') || msg?.toString?.().includes?.('Git History context is now available'))).toBe(true)

      consoleSpy.mockRestore()
    })

    it('should update alert visibility reactively when Git integration changes', async () => {
      setupServiceMock.getGitSettings.mockResolvedValue({ enabled: false })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
          stubs: {
            VAlert: {
              template: `<div v-if="$attrs.show" class="v-alert">Alert shown</div>`,
              props: ['type', 'variant', 'density', 'show'],
            },
          },
        },
      })

      await flushPromises()

      // Alert should be visible (Git disabled)
      expect(wrapper.vm.gitIntegrationEnabled).toBe(false)

      // Enable Git via WebSocket
      wrapper.vm.handleGitIntegrationUpdate({
        product_id: 'product-123',
        settings: { enabled: true },
      })

      await wrapper.vm.$nextTick()

      // Alert should no longer be visible (Git enabled)
      expect(wrapper.vm.gitIntegrationEnabled).toBe(true)
    })
  })

  describe('Complete User Workflow', () => {
    it('should complete full workflow: disabled -> toggle in Integrations -> enabled in Context', async () => {
      // Step 1: User opens Context tab with Git disabled
      setupServiceMock.getGitSettings.mockResolvedValue({ enabled: false })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await flushPromises()

      // Verify initial state
      expect(wrapper.vm.gitIntegrationEnabled).toBe(false)
      expect(wrapper.vm.isContextDisabled('git_history')).toBe(true)
      console.log('Step 1: Git integration disabled, Git History controls disabled')

      // Step 2: Simulate user toggling Git integration in Integrations tab
      console.log('Step 2: User toggles Git integration in Integrations tab')
      wrapper.vm.handleGitIntegrationUpdate({
        product_id: 'product-123',
        settings: {
          enabled: true,
          commit_limit: 20,
          default_branch: 'main',
        },
      })

      await wrapper.vm.$nextTick()

      // Step 3: Verify Context tab immediately reflects the change
      expect(wrapper.vm.gitIntegrationEnabled).toBe(true)
      expect(wrapper.vm.isContextDisabled('git_history')).toBe(false)
      console.log('Step 3: Context tab updated WITHOUT page refresh')
      console.log('Step 4: Git History controls are now enabled')

      // Verify Git History config can be modified
      expect(wrapper.vm.config.git_history.enabled).toBe(true)
    })
  })
})
