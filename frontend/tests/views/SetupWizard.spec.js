import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import SetupWizard from '@/views/SetupWizard.vue'

// Mock setup service
vi.mock('@/services/setupService', () => ({
  default: {
    baseURL: 'http://localhost:7272',
    completeSetup: vi.fn().mockResolvedValue({ requires_restart: false }),
    createAdminUser: vi.fn().mockResolvedValue({ api_key: 'test-api-key-12345' }),
    checkMcpConfigured: vi.fn().mockResolvedValue({ configured: false }),
    generateMcpConfig: vi.fn().mockResolvedValue({ command: 'uvx', args: ['giljo-mcp'] }),
    registerMcp: vi.fn().mockResolvedValue({ success: true }),
    getSerenaStatus: vi.fn().mockResolvedValue({ enabled: false }),
  },
}))

// Create Vuetify instance for testing
const vuetify = createVuetify({
  components,
  directives,
})

/**
 * SetupWizard.spec.js - Tests for SetupWizard component
 *
 * Tests the new step flow with conditional rendering:
 * 1. DatabaseTestStep (always shown)
 * 2. DeploymentModeStep (always shown)
 * 3. AdminSetupStep (conditional: only if mode is 'lan' or 'wan')
 * 4. AttachToolsStep (always shown, mode-aware behavior)
 * 5. SerenaAttachStep (always shown)
 * 6. SetupCompleteStep (always shown, mode-aware content)
 */

describe('SetupWizard.vue', () => {
  let wrapper

  beforeEach(() => {
    // Mock fetch for installation info
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            installation_path: 'F:\\GiljoAI_MCP',
            platform: 'windows',
          }),
      })
    )
  })

  describe('Step Flow - Localhost Mode', () => {
    it('should show correct steps in localhost mode', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // In localhost mode, AdminSetupStep should NOT be visible
      // Expected steps: Database, DeploymentMode, AttachTools, Serena, Complete
      const visibleSteps = wrapper.vm.visibleSteps

      expect(visibleSteps).toHaveLength(5)
      expect(visibleSteps[0].title).toBe('Database Test')
      expect(visibleSteps[1].title).toBe('Deployment Mode')
      expect(visibleSteps[2].title).toBe('MCP Configuration')
      expect(visibleSteps[3].title).toBe('Serena Enhancement')
      expect(visibleSteps[4].title).toBe('Complete')
    })

    it('should skip AdminSetupStep when navigating in localhost mode', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Set deployment mode to localhost
      wrapper.vm.config.deploymentMode = 'localhost'
      await wrapper.vm.$nextTick()

      // Navigate from DeploymentMode (step 2) to next step
      wrapper.vm.currentStepIndex = 1 // DeploymentModeStep
      wrapper.vm.handleNext()
      await wrapper.vm.$nextTick()

      // Should go directly to AttachToolsStep, skipping AdminSetupStep
      expect(wrapper.vm.currentStepIndex).toBe(2)
      expect(wrapper.vm.currentVisibleStep.title).toBe('MCP Configuration')
    })
  })

  describe('Step Flow - LAN Mode', () => {
    it('should show AdminSetupStep in LAN mode', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Set deployment mode to LAN
      wrapper.vm.config.deploymentMode = 'lan'
      await wrapper.vm.$nextTick()

      // Get visible steps with LAN mode
      const visibleSteps = wrapper.vm.visibleSteps

      expect(visibleSteps).toHaveLength(6)
      expect(visibleSteps[0].title).toBe('Database Test')
      expect(visibleSteps[1].title).toBe('Deployment Mode')
      expect(visibleSteps[2].title).toBe('Admin Setup')
      expect(visibleSteps[3].title).toBe('MCP Configuration')
      expect(visibleSteps[4].title).toBe('Serena Enhancement')
      expect(visibleSteps[5].title).toBe('Complete')
    })

    it('should show AdminSetupStep when navigating in LAN mode', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Set deployment mode to LAN
      wrapper.vm.config.deploymentMode = 'lan'
      await wrapper.vm.$nextTick()

      // Navigate from DeploymentMode (step 2) to next step
      wrapper.vm.currentStepIndex = 1 // DeploymentModeStep
      wrapper.vm.handleNext()
      await wrapper.vm.$nextTick()

      // Should go to AdminSetupStep
      expect(wrapper.vm.currentStepIndex).toBe(2)
      expect(wrapper.vm.currentVisibleStep.title).toBe('Admin Setup')
    })
  })

  describe('State Management', () => {
    it('should persist configuration across step navigation', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Set configuration values
      wrapper.vm.config.deploymentMode = 'lan'
      wrapper.vm.config.dbTestPassed = true
      wrapper.vm.config.adminUsername = 'testuser'
      wrapper.vm.config.adminPassword = 'Test123!'

      // Navigate forward
      wrapper.vm.handleNext()
      await wrapper.vm.$nextTick()

      // Navigate backward
      wrapper.vm.handlePrevious()
      await wrapper.vm.$nextTick()

      // Configuration should persist
      expect(wrapper.vm.config.deploymentMode).toBe('lan')
      expect(wrapper.vm.config.dbTestPassed).toBe(true)
      expect(wrapper.vm.config.adminUsername).toBe('testuser')
      expect(wrapper.vm.config.adminPassword).toBe('Test123!')
    })

    it('should update config when deployment mode changes', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Initially localhost
      expect(wrapper.vm.config.deploymentMode).toBe('localhost')

      // Change to LAN
      wrapper.vm.config.deploymentMode = 'lan'
      await wrapper.vm.$nextTick()

      // Visible steps should update
      const visibleSteps = wrapper.vm.visibleSteps
      expect(visibleSteps.some(step => step.title === 'Admin Setup')).toBe(true)
    })
  })

  describe('API Key Flow', () => {
    it('should store API key from AdminSetup completion', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Set LAN mode
      wrapper.vm.config.deploymentMode = 'lan'
      await wrapper.vm.$nextTick()

      // Simulate AdminSetup completion with API key
      const mockApiKey = 'test-api-key-12345'
      wrapper.vm.handleAdminSetupComplete({ apiKey: mockApiKey })
      await wrapper.vm.$nextTick()

      // API key should be stored in config
      expect(wrapper.vm.config.apiKey).toBe(mockApiKey)
    })

    it('should pass API key to AttachToolsStep in LAN mode', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Set LAN mode and API key
      wrapper.vm.config.deploymentMode = 'lan'
      wrapper.vm.config.apiKey = 'test-api-key-12345'
      await wrapper.vm.$nextTick()

      // Navigate to AttachToolsStep
      wrapper.vm.currentStepIndex = 3 // AttachToolsStep in LAN mode
      await wrapper.vm.$nextTick()

      // AttachToolsStep should receive API key prop
      const attachToolsProps = wrapper.vm.currentStepProps
      expect(attachToolsProps.apiKey).toBe('test-api-key-12345')
    })
  })

  describe('Progress Calculation', () => {
    it('should calculate progress based on visible steps in localhost mode', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Localhost mode: 5 visible steps
      wrapper.vm.config.deploymentMode = 'localhost'
      await wrapper.vm.$nextTick()

      // Step 1 of 5
      wrapper.vm.currentStepIndex = 0
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.progressPercent).toBe(20)

      // Step 3 of 5
      wrapper.vm.currentStepIndex = 2
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.progressPercent).toBe(60)

      // Step 5 of 5
      wrapper.vm.currentStepIndex = 4
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.progressPercent).toBe(100)
    })

    it('should calculate progress based on visible steps in LAN mode', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // LAN mode: 6 visible steps
      wrapper.vm.config.deploymentMode = 'lan'
      await wrapper.vm.$nextTick()

      // Step 1 of 6
      wrapper.vm.currentStepIndex = 0
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.progressPercent).toBe(17) // Math.round((1/6) * 100) = 17

      // Step 3 of 6 (AdminSetup)
      wrapper.vm.currentStepIndex = 2
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.progressPercent).toBe(50)

      // Step 6 of 6
      wrapper.vm.currentStepIndex = 5
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.progressPercent).toBe(100)
    })

    it('should show correct step counter in localhost mode', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      wrapper.vm.config.deploymentMode = 'localhost'
      await wrapper.vm.$nextTick()

      // Step 1 of 5
      wrapper.vm.currentStepIndex = 0
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.stepCounter).toBe('Step 1 of 5')

      // Step 3 of 5
      wrapper.vm.currentStepIndex = 2
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.stepCounter).toBe('Step 3 of 5')
    })

    it('should show correct step counter in LAN mode', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      wrapper.vm.config.deploymentMode = 'lan'
      await wrapper.vm.$nextTick()

      // Step 1 of 6
      wrapper.vm.currentStepIndex = 0
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.stepCounter).toBe('Step 1 of 6')

      // Step 4 of 6
      wrapper.vm.currentStepIndex = 3
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.stepCounter).toBe('Step 4 of 6')
    })
  })

  describe('Step Navigation', () => {
    it('should navigate forward correctly', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      expect(wrapper.vm.currentStepIndex).toBe(0)

      wrapper.vm.handleNext()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.currentStepIndex).toBe(1)
    })

    it('should navigate backward correctly', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      wrapper.vm.currentStepIndex = 2
      await wrapper.vm.$nextTick()

      wrapper.vm.handlePrevious()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.currentStepIndex).toBe(1)
    })

    it('should not navigate backward from first step', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      expect(wrapper.vm.currentStepIndex).toBe(0)

      wrapper.vm.handlePrevious()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.currentStepIndex).toBe(0)
    })

    it('should not navigate forward from last step', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Go to last step
      wrapper.vm.config.deploymentMode = 'localhost'
      wrapper.vm.currentStepIndex = 4 // Last step in localhost mode
      await wrapper.vm.$nextTick()

      wrapper.vm.handleNext()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.currentStepIndex).toBe(4)
    })
  })

  describe('Conditional Rendering', () => {
    it('should render current step component', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Current step component should be rendered
      const currentStep = wrapper.vm.currentVisibleStep
      expect(currentStep).toBeDefined()
      expect(currentStep.title).toBe('Database Test')
    })

    it('should pass correct props to step components', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Navigate to DeploymentModeStep
      wrapper.vm.currentStepIndex = 1
      await wrapper.vm.$nextTick()

      const props = wrapper.vm.currentStepProps
      // DeploymentModeStep receives modelValue, not deploymentMode prop
      expect(props.modelValue).toBe(wrapper.vm.config.deploymentMode)
      expect(props['onUpdate:modelValue']).toBeDefined()
    })

    it('should pass server URL to AttachToolsStep in LAN mode', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      wrapper.vm.config.deploymentMode = 'lan'
      wrapper.vm.config.serverIp = '192.168.1.100'
      await wrapper.vm.$nextTick()

      // Navigate to AttachToolsStep
      wrapper.vm.currentStepIndex = 3
      await wrapper.vm.$nextTick()

      const props = wrapper.vm.currentStepProps
      expect(props.serverUrl).toContain('192.168.1.100')
    })
  })

  describe('Mode-Aware Behavior', () => {
    it('should set server URL to localhost in localhost mode', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      wrapper.vm.config.deploymentMode = 'localhost'
      await wrapper.vm.$nextTick()

      const serverUrl = wrapper.vm.serverUrl
      expect(serverUrl).toContain('127.0.0.1')
    })

    it('should set server URL to LAN IP in LAN mode', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      wrapper.vm.config.deploymentMode = 'lan'
      wrapper.vm.config.serverIp = '192.168.1.100'
      await wrapper.vm.$nextTick()

      const serverUrl = wrapper.vm.serverUrl
      expect(serverUrl).toBe('http://192.168.1.100:7272')
    })

    it('should pass complete configuration to SetupCompleteStep', async () => {
      wrapper = mount(SetupWizard, {
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Set configuration
      wrapper.vm.config.deploymentMode = 'lan'
      wrapper.vm.config.apiKey = 'test-key'
      wrapper.vm.config.adminUsername = 'admin'
      wrapper.vm.config.serenaEnabled = true
      await wrapper.vm.$nextTick()

      // Navigate to SetupCompleteStep
      wrapper.vm.currentStepIndex = 5
      await wrapper.vm.$nextTick()

      const props = wrapper.vm.currentStepProps
      expect(props.config).toEqual(wrapper.vm.config)
    })
  })
})
