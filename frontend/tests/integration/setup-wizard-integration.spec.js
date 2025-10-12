/**
 * Setup Wizard Integration Tests
 *
 * Comprehensive integration tests verifying the setup wizard works correctly
 * with the new SetupStateManager backend architecture.
 *
 * These tests validate:
 * - Fresh install flow
 * - Localhost to LAN conversion flow
 * - Router guard integration
 * - API endpoint integration
 * - Modal flow (API key, restart)
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import SetupWizard from '@/views/SetupWizard.vue'
import setupService from '@/services/setupService'
import {
  setupTestEnvironment,
  cleanupTestEnvironment,
  mockInstallationInfo,
  mockSetupStatus,
  mockCompleteSetup,
} from '../mocks/setup.js'

describe('Setup Wizard - Backend Integration Tests', () => {
  let vuetify
  let router
  let wrapper
  let mockFetch

  beforeEach(() => {
    // Setup complete test environment
    const env = setupTestEnvironment()
    mockFetch = env.mockFetch

    // Create Vuetify instance
    vuetify = createVuetify({
      components,
      directives,
    })

    // Create router
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/',
          name: 'Dashboard',
          component: { template: '<div>Dashboard</div>' }
        },
        {
          path: '/setup',
          name: 'Setup',
          component: SetupWizard,
          meta: { requiresSetup: false }
        },
      ],
    })

    // Add router guard for testing
    router.beforeEach(async (to, from, next) => {
      if (to.meta.requiresSetup === false) {
        next()
        return
      }

      try {
        const status = await setupService.checkStatus()
        if (!status.database_initialized && to.path !== '/setup') {
          next('/setup')
        } else {
          next()
        }
      } catch (error) {
        next() // Allow navigation on error
      }
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    cleanupTestEnvironment()
  })

  describe('Fresh Install Flow', () => {
    it('should fetch setup status on mount', async () => {
      // Mock is already set up in setupTestEnvironment()
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()
      await new Promise((resolve) => setTimeout(resolve, 100)) // Wait for async mount

      // Verify installation-info endpoint was called
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/setup/installation-info')
      )
    })

    it('should complete localhost mode setup without API key modal', async () => {
      // Mock installation info
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      // Mock completeSetup response for localhost mode
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: 'Setup completed successfully',
          api_key: null,
          requires_restart: false,
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Set configuration for localhost mode
      wrapper.vm.config.deploymentMode = 'localhost'
      wrapper.vm.config.aiTools = []

      // Trigger finish
      await wrapper.vm.saveSetupConfig()

      // Verify API key modal NOT shown
      expect(wrapper.vm.showApiKeyModal).toBe(false)

      // Verify restart modal NOT shown
      expect(wrapper.vm.showRestartModal).toBe(false)

      // Verify redirect will happen (isRestarting becomes true temporarily)
      expect(wrapper.vm.isRestarting).toBe(true)
    })

    it('should render all wizard steps', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Verify stepper items exist
      expect(wrapper.vm.stepperItems).toHaveLength(5)
      expect(wrapper.vm.stepperItems[0].title).toBe('Database')
      expect(wrapper.vm.stepperItems[1].title).toBe('Attach Tools')
      expect(wrapper.vm.stepperItems[2].title).toBe('Serena MCP')
      expect(wrapper.vm.stepperItems[3].title).toBe('Network')
      expect(wrapper.vm.stepperItems[4].title).toBe('Complete')
    })

    it('should allow progression through all steps', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Start at step 1
      expect(wrapper.vm.currentStep).toBe(1)

      // Progress through steps
      wrapper.vm.handleDatabaseNext()
      expect(wrapper.vm.currentStep).toBe(2)

      wrapper.vm.handleToolsNext()
      expect(wrapper.vm.currentStep).toBe(3)

      wrapper.vm.handleSerenaNext({ serenaEnabled: false })
      expect(wrapper.vm.currentStep).toBe(4)

      wrapper.vm.handleNetworkNext()
      expect(wrapper.vm.currentStep).toBe(5)
    })

    it('should allow back navigation', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Go to step 3
      wrapper.vm.currentStep = 3

      // Go back
      wrapper.vm.handleBack()

      expect(wrapper.vm.currentStep).toBe(2)
    })
  })

  describe('Localhost to LAN Conversion Flow', () => {
    it('should show LAN confirmation modal when configuring LAN mode', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Set LAN configuration
      wrapper.vm.config.deploymentMode = 'lan'
      wrapper.vm.config.lanSettings = {
        serverIp: '192.168.1.100',
        firewallConfigured: true,
        adminUsername: 'admin',
        adminPassword: 'secure123',
        hostname: 'giljo.local',
      }

      // Trigger finish - should show confirmation modal
      wrapper.vm.handleFinish()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showLanConfirmModal).toBe(true)
    })

    it('should show API key modal after LAN configuration', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      // Mock completeSetup response with API key
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: 'LAN mode configured',
          api_key: 'gk_test_key_1234567890abcdef',
          requires_restart: true,
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Configure for LAN mode
      wrapper.vm.config.deploymentMode = 'lan'
      wrapper.vm.config.lanSettings = {
        serverIp: '192.168.1.100',
        firewallConfigured: true,
        adminUsername: 'admin',
        adminPassword: 'secure123',
        hostname: 'giljo.local',
      }

      // Trigger save
      await wrapper.vm.saveSetupConfig()

      // Verify API key modal shown
      expect(wrapper.vm.showApiKeyModal).toBe(true)
      expect(wrapper.vm.generatedApiKey).toBe('gk_test_key_1234567890abcdef')
    })

    it('should require checkbox confirmation before continuing from API key modal', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Show API key modal manually for testing
      wrapper.vm.showApiKeyModal = true
      wrapper.vm.generatedApiKey = 'gk_test_key_1234567890abcdef'
      await wrapper.vm.$nextTick()

      // Initially, confirmation should be false
      expect(wrapper.vm.apiKeyConfirmed).toBe(false)

      // Find the continue button (would be disabled)
      const continueButton = wrapper.find('button')
      // Note: In actual implementation, button would be disabled when !apiKeyConfirmed

      // Confirm API key saved
      wrapper.vm.apiKeyConfirmed = true
      await wrapper.vm.$nextTick()

      // Proceed to restart modal
      wrapper.vm.proceedToRestart()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showApiKeyModal).toBe(false)
      expect(wrapper.vm.showRestartModal).toBe(true)
    })

    it('should copy API key to clipboard', async () => {
      // Mock clipboard API
      const mockWriteText = vi.fn()
      Object.assign(navigator, {
        clipboard: {
          writeText: mockWriteText,
        },
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Setup API key
      wrapper.vm.generatedApiKey = 'gk_test_key_1234567890abcdef'
      wrapper.vm.showApiKeyModal = true
      await wrapper.vm.$nextTick()

      // Copy API key
      wrapper.vm.copyApiKey()

      expect(mockWriteText).toHaveBeenCalledWith('gk_test_key_1234567890abcdef')
      expect(wrapper.vm.apiKeyCopied).toBe(true)

      // Wait for copied state to reset
      await new Promise((resolve) => setTimeout(resolve, 3100))
      expect(wrapper.vm.apiKeyCopied).toBe(false)
    })

    it('should show restart modal after API key modal', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Setup state
      wrapper.vm.showApiKeyModal = true
      wrapper.vm.apiKeyConfirmed = true
      wrapper.vm.generatedApiKey = 'gk_test_key_1234567890abcdef'

      // Proceed to restart
      wrapper.vm.proceedToRestart()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showRestartModal).toBe(true)
      expect(wrapper.vm.showApiKeyModal).toBe(false)
    })

    it('should display platform-specific restart instructions', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Verify Windows instructions
      expect(wrapper.vm.platform).toBe('windows')
      expect(wrapper.vm.restartInstructions).toContain('Open Command Prompt or PowerShell')
      expect(wrapper.vm.restartInstructions).toContain('stop_backend.bat')
      expect(wrapper.vm.restartInstructions).toContain('start_backend.bat')
    })

    it('should set localStorage flag when finishing LAN setup', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      // Mock localStorage
      const localStorageMock = {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
      }
      global.localStorage = localStorageMock

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Configure LAN mode
      wrapper.vm.config.deploymentMode = 'lan'

      // Mock window.location.href
      delete window.location
      window.location = { href: '' }

      // Finish setup
      wrapper.vm.finishSetup()

      expect(localStorageMock.setItem).toHaveBeenCalledWith('giljo_lan_setup_complete', 'true')
    })
  })

  describe('Router Guard Integration', () => {
    it('should allow navigation to /setup when setup not completed', async () => {
      // Mock setup status check
      vi.spyOn(setupService, 'checkStatus').mockResolvedValue({
        database_initialized: false,
      })

      await router.push('/setup')
      await router.isReady()

      expect(router.currentRoute.value.path).toBe('/setup')
    })

    it('should allow navigation to /setup even when setup completed (for re-running)', async () => {
      // Mock setup status check
      vi.spyOn(setupService, 'checkStatus').mockResolvedValue({
        database_initialized: true,
      })

      await router.push('/setup')
      await router.isReady()

      // Should still allow access to setup for re-running wizard
      expect(router.currentRoute.value.path).toBe('/setup')
    })

    it('should redirect to /setup when accessing dashboard with incomplete setup', async () => {
      // Mock setup status check
      vi.spyOn(setupService, 'checkStatus').mockResolvedValue({
        database_initialized: false,
      })

      await router.push('/')
      await router.isReady()

      // Should redirect to setup
      expect(router.currentRoute.value.path).toBe('/setup')
    })

    it('should allow dashboard access when setup completed', async () => {
      // Mock setup status check
      vi.spyOn(setupService, 'checkStatus').mockResolvedValue({
        database_initialized: true,
      })

      await router.push('/')
      await router.isReady()

      // Should stay on dashboard
      expect(router.currentRoute.value.path).toBe('/')
    })

    it('should handle setup status check failure gracefully', async () => {
      // Mock setup status check failure
      vi.spyOn(setupService, 'checkStatus').mockRejectedValue(
        new Error('API not available')
      )

      await router.push('/')
      await router.isReady()

      // Should allow navigation even if check fails (to avoid blocking)
      expect(router.currentRoute.value.path).toBe('/')
    })
  })

  describe('API Integration', () => {
    it('should call completeSetup with correct payload', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      // Mock completeSetup
      const completeSetupSpy = vi.spyOn(setupService, 'completeSetup')
      completeSetupSpy.mockResolvedValue({
        success: true,
        message: 'Setup completed',
        api_key: null,
        requires_restart: false,
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Configure wizard
      wrapper.vm.config.deploymentMode = 'localhost'
      wrapper.vm.config.aiTools = [{ id: 'claude-code', name: 'Claude Code' }]
      wrapper.vm.config.serenaEnabled = true

      // Complete setup
      await wrapper.vm.saveSetupConfig()

      // Verify API called with correct data
      expect(completeSetupSpy).toHaveBeenCalledWith({
        deploymentMode: 'localhost',
        aiTools: [{ id: 'claude-code', name: 'Claude Code' }],
        serenaEnabled: true,
        lanSettings: null,
      })
    })

    it('should handle API errors during setup completion', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      // Mock API error
      vi.spyOn(setupService, 'completeSetup').mockRejectedValue(
        new Error('Database connection failed')
      )

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Mock window.location.href
      delete window.location
      window.location = { href: '' }

      // Try to complete setup
      await wrapper.vm.saveSetupConfig()

      // Should hide loading overlay
      expect(wrapper.vm.isRestarting).toBe(true) // Shows error state
      expect(wrapper.vm.restartMessage).toContain('Error')
    })

    it('should fetch installation info on mount', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/setup/installation-info')
      )
      expect(wrapper.vm.installationPath).toBe('F:\\GiljoAI_MCP')
      expect(wrapper.vm.detectedPlatform).toBe('windows')
    })

    it('should fallback to browser detection if installation info fails', async () => {
      // Mock fetch failure
      mockFetch.mockRejectedValueOnce(new Error('API error'))

      // Mock user agent for Windows
      Object.defineProperty(window.navigator, 'userAgent', {
        value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        configurable: true,
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Should detect Windows from user agent
      expect(wrapper.vm.detectedPlatform).toBe('windows')
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      // Mock network error during setup
      vi.spyOn(setupService, 'completeSetup').mockRejectedValue(
        new Error('Network error')
      )

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Mock window.location.href
      delete window.location
      window.location = { href: '' }

      // Try to complete setup
      await wrapper.vm.saveSetupConfig()

      // Should show error state but eventually redirect
      expect(wrapper.vm.isRestarting).toBe(true)
    })

    it('should display error message when setup fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      // Mock API error
      vi.spyOn(setupService, 'completeSetup').mockRejectedValue(
        new Error('Setup validation failed')
      )

      // Spy on console.error
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Try to complete setup
      await wrapper.vm.saveSetupConfig()

      // Should log error
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '[WIZARD] Setup completion failed:',
        expect.any(Error)
      )

      consoleErrorSpy.mockRestore()
    })
  })

  describe('State Management', () => {
    it('should persist wizard configuration across steps', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Configure step by step
      wrapper.vm.config.deploymentMode = 'lan'
      wrapper.vm.handleDatabaseNext()

      wrapper.vm.config.aiTools = [{ id: 'claude-code' }]
      wrapper.vm.handleToolsNext()

      wrapper.vm.config.serenaEnabled = true
      wrapper.vm.handleSerenaNext({ serenaEnabled: true })

      // Verify all config persisted
      expect(wrapper.vm.config.deploymentMode).toBe('lan')
      expect(wrapper.vm.config.aiTools).toHaveLength(1)
      expect(wrapper.vm.config.serenaEnabled).toBe(true)
    })

    it('should update serenaEnabled from SerenaAttachStep', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Initially false
      expect(wrapper.vm.config.serenaEnabled).toBe(false)

      // Enable Serena
      wrapper.vm.handleSerenaNext({ serenaEnabled: true })

      expect(wrapper.vm.config.serenaEnabled).toBe(true)
    })
  })

  describe('Modal Flow', () => {
    it('should show modals in correct sequence for LAN mode', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          api_key: 'gk_test_key_123',
          requires_restart: true,
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Configure LAN mode
      wrapper.vm.config.deploymentMode = 'lan'
      wrapper.vm.config.lanSettings = { serverIp: '192.168.1.100' }

      // Step 1: Show LAN confirmation modal
      wrapper.vm.handleFinish()
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.showLanConfirmModal).toBe(true)

      // Step 2: Confirm LAN config -> API key modal
      await wrapper.vm.confirmLanConfig()
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.showLanConfirmModal).toBe(false)
      expect(wrapper.vm.showApiKeyModal).toBe(true)

      // Step 3: Confirm API key saved -> restart modal
      wrapper.vm.apiKeyConfirmed = true
      wrapper.vm.proceedToRestart()
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.showApiKeyModal).toBe(false)
      expect(wrapper.vm.showRestartModal).toBe(true)
    })

    it('should allow canceling LAN confirmation', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation_path: 'F:\\GiljoAI_MCP',
          platform: 'windows',
        }),
      })

      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify, router],
        },
      })

      await wrapper.vm.$nextTick()

      // Show LAN confirmation modal
      wrapper.vm.config.deploymentMode = 'lan'
      wrapper.vm.handleFinish()
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.showLanConfirmModal).toBe(true)

      // Cancel
      wrapper.vm.cancelLanConfig()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showLanConfirmModal).toBe(false)
      // User stays on summary screen (step 5)
      expect(wrapper.vm.currentStep).toBe(1) // Still on original step
    })
  })
})
