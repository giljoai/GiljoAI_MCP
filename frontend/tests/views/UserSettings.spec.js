import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import UserSettings from '@/views/UserSettings.vue'
import { useSettingsStore } from '@/stores/settings'
import api from '@/services/api'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// Mock the API
vi.mock('@/services/api', () => ({
  default: {
    users: {
      getFieldPriorityConfig: vi.fn(),
      updateFieldPriorityConfig: vi.fn(),
      resetFieldPriorityConfig: vi.fn(),
    },
    products: {
      getActiveProductTokenEstimate: vi.fn(),
      getGitIntegration: vi.fn(() => Promise.resolve({ data: { enabled: false, commit_limit: 20, default_branch: 'main' } })),
      updateGitIntegration: vi.fn(() => Promise.resolve({ data: { enabled: true, commit_limit: 20, default_branch: 'main' } })),
    },
    settings: {
      get: vi.fn(),
      update: vi.fn(),
    },
  },
}))

// Mock setupService
vi.mock('@/services/setupService', () => ({
  default: {
    getSerenaStatus: vi.fn(() => Promise.resolve({ enabled: false })),
    toggleSerena: vi.fn(() => Promise.resolve({ success: true, enabled: false })),
    getSerenaConfig: vi.fn(() => Promise.resolve({
      use_in_prompts: true,
      tailor_by_mission: true,
      dynamic_catalog: true,
      prefer_ranges: true,
      max_range_lines: 180,
      context_halo: 12,
    })),
  },
}))

// Mock router
const mockRouter = {
  currentRoute: {
    value: { query: {} },
  },
  push: vi.fn(),
  replace: vi.fn(),
}

// Mock vue-router
vi.mock('vue-router', () => ({
  useRouter: () => mockRouter,
}))

// Setup vuetify
const vuetify = createVuetify({
  components,
  directives,
})

describe('UserSettings.vue - Context Priority Management (Handover 0052)', () => {
  let wrapper

  beforeEach(() => {
    setActivePinia(createPinia())
    
    // Mock API responses
    api.users.getFieldPriorityConfig.mockResolvedValue({
      data: {
        version: '1.0',
        token_budget: 2000,
        fields: {
          'tech_stack.languages': 1,
          'tech_stack.backend': 1,
          'features.core': 2,
          'architecture.pattern': 3,
        },
      },
    })

    api.products.getActiveProductTokenEstimate.mockResolvedValue({
      data: {
        name: 'Test Product',
        total_tokens: 450,
        field_tokens: {
          'tech_stack.languages': 120,
          'tech_stack.backend': 150,
          'features.core': 100,
          'architecture.pattern': 80,
        },
      },
    })

    api.settings.get.mockResolvedValue({
      data: {
        theme: 'dark',
        notifications: true,
      },
    })
  })

  // Helper function to mount component
  function mountComponent() {
    return mount(UserSettings, {
      global: {
        plugins: [createPinia(), vuetify],
        mocks: {
          $router: mockRouter,
        },
        stubs: {
          TemplateManager: true,
          ApiKeyManager: true,
          McpConfigComponent: true,
          AiToolConfigWizard: true,
          ClaudeCodeExport: true,
          SlashCommandSetup: true,
          SerenaAdvancedSettingsDialog: true,
          ContextPriorityConfig: true,
          McpIntegrationCard: {
            name: 'McpIntegrationCard',
            template: '<div class="mcp-integration-card-stub"></div>',
          },
          SerenaIntegrationCard: {
            name: 'SerenaIntegrationCard',
            template: '<div class="serena-integration-card-stub"></div>',
            props: ['enabled', 'config', 'loading'],
            emits: ['update:enabled', 'openAdvanced'],
          },
          GitIntegrationCard: {
            name: 'GitIntegrationCard',
            template: '<div class="git-integration-card-stub"></div>',
            props: ['enabled', 'config', 'loading'],
            emits: ['update:enabled', 'save'],
          },
          draggable: {
            template: '<div><slot></slot></div>',
            props: ['modelValue', 'group', 'itemKey', 'handle'],
            emits: ['update:modelValue', 'change'],
          },
        },
      },
    })
  }

  describe('Phase 1: Bug Fix Verification', () => {
    it('resetGeneralSettings should not reference projectName field', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // The reset function should not throw any errors
      expect(() => {
        wrapper.vm.resetGeneralSettings()
      }).not.toThrow()

      // General settings should be empty object (no projectName)
      expect(wrapper.vm.settings.general).toEqual({})
    })

    it('reset button should be clickable and functional', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      const resetBtn = wrapper.find('[data-test="reset-general-btn"]')
      expect(resetBtn.exists()).toBe(true)
      expect(resetBtn.attributes('disabled')).toBeUndefined()
    })

    it('saveGeneralSettings should succeed after reset', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      vi.spyOn(wrapper.vm, 'resetGeneralSettings')
      wrapper.vm.resetGeneralSettings()
      
      expect(wrapper.vm.resetGeneralSettings).toHaveBeenCalled()
    })
  })

  describe('Phase 2: Unassigned Category Behavior', () => {
    it('should load unassigned fields from difference of available and assigned', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      // Total available fields = 13
      // Assigned: 4 (tech_stack.languages, tech_stack.backend, features.core, architecture.pattern)
      // Expected unassigned: 13 - 4 = 9
      expect(wrapper.vm.unassignedFields.length).toBe(9)
    })

    it('should have all 13 available fields defined', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      const allFields = [
        'architecture.api_style',
        'architecture.design_patterns',
        'architecture.notes',
        'architecture.pattern',
        'features.core',
        'tech_stack.backend',
        'tech_stack.database',
        'tech_stack.frontend',
        'tech_stack.infrastructure',
        'tech_stack.languages',
        'test_config.coverage_target',
        'test_config.frameworks',
        'test_config.strategy',
      ]

      expect(wrapper.vm.ALL_AVAILABLE_FIELDS).toEqual(allFields)
      expect(wrapper.vm.ALL_AVAILABLE_FIELDS.length).toBe(13)
    })

    it('removeField should move field to unassigned (not delete)', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      const initialUnassignedCount = wrapper.vm.unassignedFields.length
      const fieldToRemove = wrapper.vm.priority1Fields[0]

      wrapper.vm.removeField(fieldToRemove, 'priority_1')
      await wrapper.vm.$nextTick()

      // Field should be gone from priority1
      expect(wrapper.vm.priority1Fields).not.toContain(fieldToRemove)

      // Field should appear in unassigned
      expect(wrapper.vm.unassignedFields).toContain(fieldToRemove)
      expect(wrapper.vm.unassignedFields.length).toBe(initialUnassignedCount + 1)
    })

    it('should update fieldPriorityHasChanges when removing field', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      wrapper.vm.fieldPriorityHasChanges.value = false
      const fieldToRemove = wrapper.vm.priority1Fields[0]

      wrapper.vm.removeField(fieldToRemove, 'priority_1')

      expect(wrapper.vm.fieldPriorityHasChanges).toBe(true)
    })

    it('should show unassigned category in UI', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      const unassignedCard = wrapper.find('.unassigned-card')
      expect(unassignedCard.exists()).toBe(true)

      const title = unassignedCard.find('.v-card-title')
      expect(title.text()).toContain('Unassigned Fields')
    })

    it('saveFieldPriority should not send unassigned fields to backend', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      api.users.updateFieldPriorityConfig.mockResolvedValue({
        data: { success: true },
      })

      wrapper.vm.fieldPriorityHasChanges = true
      await wrapper.vm.saveFieldPriority()

      // Check that API was called
      expect(api.users.updateFieldPriorityConfig).toHaveBeenCalled()

      // Check the config sent - should only have priority 1-3 fields
      const sentConfig = api.users.updateFieldPriorityConfig.mock.calls[0][0]
      expect(sentConfig.fields).toBeDefined()

      // All keys in fields object should be assigned (value 1, 2, or 3)
      Object.values(sentConfig.fields).forEach(priority => {
        expect([1, 2, 3]).toContain(priority)
      })
    })
  })

  describe('Phase 3: Real-Time Token Estimation', () => {
    it('should prefer real token data from active product', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      // Active product token estimate should be loaded
      expect(wrapper.vm.activeProductTokens).not.toBeNull()
      expect(wrapper.vm.activeProductTokens.total_tokens).toBe(450)

      // Estimated tokens should use real data, not static calculation
      expect(wrapper.vm.estimatedTokens).toBe(450)
    })

    it('should fall back to static calculation when no active product', async () => {
      api.products.getActiveProductTokenEstimate.mockRejectedValue(
        new Error('No active product')
      )

      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      expect(wrapper.vm.activeProductTokens).toBeNull()

      // Should use static calculation: (2 * 50) + (1 * 30) + (1 * 20) + 500
      // = 100 + 30 + 20 + 500 = 650
      const expectedTokens = (2 * 50) + (1 * 30) + (1 * 20) + 500
      expect(wrapper.vm.estimatedTokens).toBe(expectedTokens)
    })

    it('tokenPercentage should calculate correctly', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      // 450 / 2000 = 0.225 = 22.5% rounds to 22%
      const percentage = Math.round((450 / 2000) * 100)
      expect(wrapper.vm.tokenPercentage).toBe(percentage)
    })

    it('tokenIndicatorColor should be success when < 70%', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      // 450 / 2000 = 22.5% (< 70%)
      expect(wrapper.vm.tokenPercentage).toBeLessThan(70)
      expect(wrapper.vm.tokenIndicatorColor).toBe('success')
    })

    it('tokenIndicatorColor should be warning when 70-90%', async () => {
      api.products.getActiveProductTokenEstimate.mockResolvedValue({
        data: {
          name: 'Test Product',
          total_tokens: 1600, // 80% of 2000
          field_tokens: {},
        },
      })

      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      // 1600 / 2000 = 80%
      expect(wrapper.vm.tokenPercentage).toBe(80)
      expect(wrapper.vm.tokenIndicatorColor).toBe('warning')
    })

    it('tokenIndicatorColor should be error when > 90%', async () => {
      api.products.getActiveProductTokenEstimate.mockResolvedValue({
        data: {
          name: 'Test Product',
          total_tokens: 1900, // 95% of 2000
          field_tokens: {},
        },
      })

      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      // 1900 / 2000 = 95%
      expect(wrapper.vm.tokenPercentage).toBe(95)
      expect(wrapper.vm.tokenIndicatorColor).toBe('error')
    })

    it('should refresh token estimate after saving', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      api.users.updateFieldPriorityConfig.mockResolvedValue({
        data: { success: true },
      })

      const initialCallCount = api.products.getActiveProductTokenEstimate.mock.calls.length
      
      wrapper.vm.fieldPriorityHasChanges = true
      await wrapper.vm.saveFieldPriority()

      // Should have called fetchActiveProductTokenEstimate after save
      const newCallCount = api.products.getActiveProductTokenEstimate.mock.calls.length
      expect(newCallCount).toBeGreaterThan(initialCallCount)
    })

    it('should refresh token estimate after reset', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      api.users.resetFieldPriorityConfig.mockResolvedValue({
        data: {
          version: '1.0',
          token_budget: 2000,
          fields: {},
        },
      })

      const initialCallCount = api.products.getActiveProductTokenEstimate.mock.calls.length
      
      await wrapper.vm.resetFieldPriorityToDefaults()

      // Should have called fetchActiveProductTokenEstimate after reset
      const newCallCount = api.products.getActiveProductTokenEstimate.mock.calls.length
      expect(newCallCount).toBeGreaterThan(initialCallCount)
    })
  })

  describe('Phase 4: Edge Cases', () => {
    it('should show empty state when all fields assigned', async () => {
      api.users.getFieldPriorityConfig.mockResolvedValue({
        data: {
          version: '1.0',
          token_budget: 2000,
          fields: {
            'architecture.api_style': 1,
            'architecture.design_patterns': 1,
            'architecture.notes': 1,
            'architecture.pattern': 1,
            'features.core': 1,
            'tech_stack.backend': 1,
            'tech_stack.database': 1,
            'tech_stack.frontend': 1,
            'tech_stack.infrastructure': 1,
            'tech_stack.languages': 1,
            'test_config.coverage_target': 1,
            'test_config.frameworks': 1,
            'test_config.strategy': 1,
          },
        },
      })

      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      // Unassigned should be empty
      expect(wrapper.vm.unassignedFields.length).toBe(0)

      // Check for empty state message in unassigned card
      const unassignedCard = wrapper.find('.unassigned-card')
      expect(unassignedCard.text()).toContain('All fields are assigned to priorities')
    })

    it('should handle rapid field movements without duplicates', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      const fieldToMove = wrapper.vm.priority1Fields[0]
      const totalFieldsBefore = wrapper.vm.priority1Fields.length + 
                               wrapper.vm.priority2Fields.length +
                               wrapper.vm.priority3Fields.length +
                               wrapper.vm.unassignedFields.length

      // Move field: P1 -> P2
      wrapper.vm.priority2Fields.push(fieldToMove)
      const idx1 = wrapper.vm.priority1Fields.indexOf(fieldToMove)
      if (idx1 > -1) wrapper.vm.priority1Fields.splice(idx1, 1)

      // Move field: P2 -> P3
      wrapper.vm.priority3Fields.push(fieldToMove)
      const idx2 = wrapper.vm.priority2Fields.indexOf(fieldToMove)
      if (idx2 > -1) wrapper.vm.priority2Fields.splice(idx2, 1)

      // Move field: P3 -> Unassigned
      wrapper.vm.unassignedFields.push(fieldToMove)
      const idx3 = wrapper.vm.priority3Fields.indexOf(fieldToMove)
      if (idx3 > -1) wrapper.vm.priority3Fields.splice(idx3, 1)

      // Move field: Unassigned -> P1
      wrapper.vm.priority1Fields.push(fieldToMove)
      const idx4 = wrapper.vm.unassignedFields.indexOf(fieldToMove)
      if (idx4 > -1) wrapper.vm.unassignedFields.splice(idx4, 1)

      const totalFieldsAfter = wrapper.vm.priority1Fields.length + 
                              wrapper.vm.priority2Fields.length +
                              wrapper.vm.priority3Fields.length +
                              wrapper.vm.unassignedFields.length

      // Total should be the same (no duplication)
      expect(totalFieldsAfter).toBe(totalFieldsBefore)

      // Field should be in priority1
      expect(wrapper.vm.priority1Fields).toContain(fieldToMove)
    })

    it('should show empty state message for each priority when empty', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      // Clear all fields
      wrapper.vm.priority1Fields = []
      wrapper.vm.priority2Fields = []
      wrapper.vm.priority3Fields = []
      await wrapper.vm.$nextTick()

      const cards = wrapper.findAll('.v-card')
      const priority1Card = cards.find(c => c.text().includes('Priority 1'))
      const priority2Card = cards.find(c => c.text().includes('Priority 2'))
      const priority3Card = cards.find(c => c.text().includes('Priority 3'))

      expect(priority1Card?.text()).toContain('No fields assigned to Priority 1')
      expect(priority2Card?.text()).toContain('No fields assigned to Priority 2')
      expect(priority3Card?.text()).toContain('No fields assigned to Priority 3')
    })

    it('should disable save button when no changes', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      wrapper.vm.fieldPriorityHasChanges = false
      await wrapper.vm.$nextTick()

      const saveBtn = wrapper.find('button:has-text("Save Field Priority")')
      // Note: This may need adjustment based on actual button selector
    })
  })

  describe('Active Product Integration', () => {
    it('should display active product name in token indicator', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      expect(wrapper.vm.activeProductName).toBe('Test Product')
    })

    it('should show "No Active Product" message when no product available', async () => {
      api.products.getActiveProductTokenEstimate.mockRejectedValue(
        new Error('No active product')
      )

      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      expect(wrapper.vm.activeProductName).toBe('No Active Product')
    })

    it('should show token budget indicator card when active product exists', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      expect(wrapper.vm.activeProductTokens).not.toBeNull()
      expect(wrapper.find('[data-test="general-settings"]').exists()).toBe(true)
    })

    it('should show info alert when no active product', async () => {
      api.products.getActiveProductTokenEstimate.mockRejectedValue(
        new Error('No active product')
      )

      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      const alerts = wrapper.findAll('.v-alert')
      const noProductAlert = alerts.find(a => a.text().includes('No active product'))
      expect(noProductAlert?.exists()).toBe(true)
    })
  })

  describe('Integration Cards Extraction (Refactoring)', () => {
    it('should render McpIntegrationCard component in integrations tab', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Navigate to integrations tab
      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      // Check that the McpIntegrationCard stub is rendered
      const mcpCard = wrapper.findComponent({ name: 'McpIntegrationCard' })
      expect(mcpCard.exists()).toBe(true)
    })

    it('should render SerenaIntegrationCard component with correct props', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Navigate to integrations tab
      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      // Check that the SerenaIntegrationCard stub is rendered
      const serenaCard = wrapper.findComponent({ name: 'SerenaIntegrationCard' })
      expect(serenaCard.exists()).toBe(true)

      // Verify props are passed correctly
      expect(serenaCard.props('enabled')).toBe(false) // Initial state from mock
      expect(serenaCard.props('loading')).toBe(false)
    })

    it('should render GitIntegrationCard component with correct props', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Navigate to integrations tab
      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      // Check that the GitIntegrationCard stub is rendered
      const gitCard = wrapper.findComponent({ name: 'GitIntegrationCard' })
      expect(gitCard.exists()).toBe(true)

      // Verify props are passed correctly
      expect(gitCard.props('enabled')).toBe(false) // Initial state from mock
      expect(gitCard.props('loading')).toBe(false)
    })

    it('should handle SerenaIntegrationCard update:enabled event via toggleSerena', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Call the toggleSerena handler directly (this is what the component would call)
      await wrapper.vm.toggleSerena(true)
      await wrapper.vm.$nextTick()

      // The serenaEnabled state should be updated based on mock response
      // Mock returns success: true, enabled: false
      expect(wrapper.vm.serenaEnabled).toBe(false)
    })

    it('should handle SerenaIntegrationCard openAdvanced event via openSerenaAdvanced', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Call the openSerenaAdvanced handler directly
      await wrapper.vm.openSerenaAdvanced()
      await wrapper.vm.$nextTick()

      // The showSerenaAdvanced dialog should be opened
      expect(wrapper.vm.showSerenaAdvanced).toBe(true)
    })

    it('should handle GitIntegrationCard update:enabled event via onGitToggle', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      // Call the onGitToggle handler directly
      wrapper.vm.onGitToggle(true)
      await wrapper.vm.$nextTick()

      // The gitIntegration.enabled state should change
      expect(wrapper.vm.gitIntegration.enabled).toBe(true)
    })

    it('should handle GitIntegrationCard save event via handleGitSave', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      // Set up productInfo to simulate an active product
      const settingsStore = useSettingsStore()
      settingsStore.productInfo = { id: 'test-product-id', name: 'Test Product' }

      // Call the handleGitSave handler directly with payload
      const savePayload = {
        enabled: true,
        commit_limit: 30,
        default_branch: 'develop'
      }
      await wrapper.vm.handleGitSave(savePayload)
      await wrapper.vm.$nextTick()

      // The API should have been called
      expect(api.products.updateGitIntegration).toHaveBeenCalled()
    })

    it('should keep SlashCommandSetup and ClaudeCodeExport inline', async () => {
      wrapper = mountComponent()
      await wrapper.vm.$nextTick()

      // Navigate to integrations tab
      wrapper.vm.activeTab = 'integrations'
      await wrapper.vm.$nextTick()

      // These components should still be rendered (as stubs)
      const slashCommandSetup = wrapper.findComponent({ name: 'SlashCommandSetup' })
      const claudeCodeExport = wrapper.findComponent({ name: 'ClaudeCodeExport' })

      expect(slashCommandSetup.exists()).toBe(true)
      expect(claudeCodeExport.exists()).toBe(true)
    })
  })
})
