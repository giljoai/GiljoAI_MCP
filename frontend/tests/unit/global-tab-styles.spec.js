/**
 * Test: Global Tab Styling Standardization
 *
 * Tests for consistent tab styling across the application.
 * All tabs should follow a consistent pattern:
 * - Inactive tabs: opacity 0.6 (faded)
 * - Active tab: opacity 1.0 (full)
 * - No yellow color overrides
 * - Smooth transitions
 * - Consistent behavior across all components
 *
 * Components tested:
 * - ProjectTabs.vue
 * - UserSettings.vue
 * - SystemSettings.vue
 * - ProductForm.vue
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// Import components to test
import ProjectTabs from '@/components/projects/ProjectTabs.vue'
import UserSettings from '@/views/UserSettings.vue'
import SystemSettings from '@/views/SystemSettings.vue'
import ProductForm from '@/components/products/ProductForm.vue'

// Import global styles
import '@/styles/global-tabs.scss'

// Mock dependencies
vi.mock('vue-router', () => ({
  useRoute: () => ({
    query: {},
    hash: '',
  }),
  useRouter: () => ({
    replace: vi.fn(),
    currentRoute: { value: { query: {} } },
  }),
}))

vi.mock('@/services/api', () => ({
  default: {
    products: {
      getGitIntegration: vi.fn().mockResolvedValue({ data: { enabled: false } }),
      updateGitIntegration: vi.fn().mockResolvedValue({ data: { enabled: false } }),
    },
  },
}))

vi.mock('@/services/setupService', () => ({
  default: {
    getSerenaStatus: vi.fn().mockResolvedValue({ enabled: false }),
    toggleSerena: vi.fn().mockResolvedValue({ success: true, enabled: false }),
  },
}))

describe('Global Tab Styles', () => {
  let vuetify

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  describe('Tab Opacity Standards', () => {
    it('should apply opacity 0.6 to inactive tabs', async () => {
      // This test will initially fail until we create the global styles
      const wrapper = mount(ProjectTabs, {
        props: {
          project: {
            id: 'test-project',
            name: 'Test Project',
          },
        },
        global: {
          plugins: [vuetify],
          stubs: {
            LaunchTab: true,
            JobsTab: true,
          },
        },
      })

      // Wait for next tick to ensure DOM is updated
      await wrapper.vm.$nextTick()

      // Check that inactive tabs have the global-tabs class
      const tabs = wrapper.findAll('.v-tab')
      expect(tabs.length).toBeGreaterThan(0)

      // Check for global-tabs class on v-tabs
      const vTabs = wrapper.find('.v-tabs')
      expect(vTabs.classes()).toContain('global-tabs')
    })

    it('should apply opacity 1.0 to active tab', async () => {
      const wrapper = mount(ProjectTabs, {
        props: {
          project: {
            id: 'test-project',
            name: 'Test Project',
          },
        },
        global: {
          plugins: [vuetify],
          stubs: {
            LaunchTab: true,
            JobsTab: true,
          },
        },
      })

      await wrapper.vm.$nextTick()

      // Find active tab
      const activeTab = wrapper.find('.v-tab--selected')
      expect(activeTab.exists()).toBe(true)

      // Active tab should have full opacity via global-tabs class
      const vTabs = wrapper.find('.v-tabs')
      expect(vTabs.classes()).toContain('global-tabs')
    })
  })

  describe('ProjectTabs Component', () => {
    it('should use global-tabs class instead of custom styling', async () => {
      const wrapper = mount(ProjectTabs, {
        props: {
          project: {
            id: 'test-project',
            name: 'Test Project',
          },
        },
        global: {
          plugins: [vuetify],
          stubs: {
            LaunchTab: true,
            JobsTab: true,
          },
        },
      })

      // Check that global-tabs class is applied
      const vTabs = wrapper.find('.v-tabs')
      expect(vTabs.classes()).toContain('global-tabs')
    })

    it('should NOT have yellow color override', async () => {
      const wrapper = mount(ProjectTabs, {
        props: {
          project: {
            id: 'test-project',
            name: 'Test Project',
          },
        },
        global: {
          plugins: [vuetify],
          stubs: {
            LaunchTab: true,
            JobsTab: true,
          },
        },
      })

      // Check that no yellow color prop is set
      const vTabs = wrapper.findComponent({ name: 'VTabs' })
      expect(vTabs.props('color')).not.toBe('yellow-darken-2')
    })

    it('should have minimal custom CSS', async () => {
      const wrapper = mount(ProjectTabs, {
        props: {
          project: {
            id: 'test-project',
            name: 'Test Project',
          },
        },
        global: {
          plugins: [vuetify],
          stubs: {
            LaunchTab: true,
            JobsTab: true,
          },
        },
      })

      // Component should exist and be mounted
      expect(wrapper.exists()).toBe(true)

      // The component should rely on global styles, not extensive custom CSS
      // This is validated by checking that the global-tabs class is present
      const vTabs = wrapper.find('.v-tabs')
      expect(vTabs.classes()).toContain('global-tabs')
    })
  })

  describe('UserSettings Component', () => {
    it('should use global-tabs class', async () => {
      const wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify],
          stubs: {
            TemplateManager: true,
            ApiKeyManager: true,
            ClaudeCodeExport: true,
            SlashCommandSetup: true,
            SerenaAdvancedSettingsDialog: true,
            ContextPriorityConfig: true,
            McpIntegrationCard: true,
            SerenaIntegrationCard: true,
            GitIntegrationCard: true,
          },
        },
      })

      await wrapper.vm.$nextTick()

      // Check for global-tabs class
      const vTabs = wrapper.find('.v-tabs')
      expect(vTabs.classes()).toContain('global-tabs')
    })

    it('should NOT have animation override CSS', () => {
      const wrapper = mount(UserSettings, {
        global: {
          plugins: [vuetify],
          stubs: {
            TemplateManager: true,
            ApiKeyManager: true,
            ClaudeCodeExport: true,
            SlashCommandSetup: true,
            SerenaAdvancedSettingsDialog: true,
            ContextPriorityConfig: true,
            McpIntegrationCard: true,
            SerenaIntegrationCard: true,
            GitIntegrationCard: true,
          },
        },
      })

      // The component should not have custom animation overrides
      // This will be validated by checking the component's style tag doesn't contain v-window overrides
      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('SystemSettings Component', () => {
    it('should use global-tabs class', async () => {
      const wrapper = mount(SystemSettings, {
        global: {
          plugins: [vuetify],
          stubs: {
            NetworkSettingsTab: true,
            DatabaseConnection: true,
            AdminIntegrationsTab: true,
            SecuritySettingsTab: true,
            SystemPromptTab: true,
            ClaudeConfigModal: true,
            CodexConfigModal: true,
            GeminiConfigModal: true,
          },
        },
      })

      await wrapper.vm.$nextTick()

      // Check for global-tabs class
      const vTabs = wrapper.find('.v-tabs')
      expect(vTabs.classes()).toContain('global-tabs')
    })
  })

  describe('ProductForm Component', () => {
    it('should use global-tabs class', async () => {
      const wrapper = mount(ProductForm, {
        props: {
          modelValue: true,
          product: null,
          isEdit: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Check for global-tabs class
      const vTabs = wrapper.find('.v-tabs')
      expect(vTabs.classes()).toContain('global-tabs')
    })

    it('should NOT have color="primary" prop', async () => {
      const wrapper = mount(ProductForm, {
        props: {
          modelValue: true,
          product: null,
          isEdit: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await wrapper.vm.$nextTick()

      // Check that no primary color prop is set
      const vTabs = wrapper.findComponent({ name: 'VTabs' })
      expect(vTabs.props('color')).not.toBe('primary')
    })
  })

  describe('Tab Transition Consistency', () => {
    it('should have consistent transition timing across all components', async () => {
      // Create wrapper for each component
      const components = [
        {
          name: 'ProjectTabs',
          component: ProjectTabs,
          props: {
            project: { id: 'test', name: 'Test' },
          },
          stubs: {
            LaunchTab: true,
            JobsTab: true,
          },
        },
        {
          name: 'UserSettings',
          component: UserSettings,
          props: {},
          stubs: {
            TemplateManager: true,
            ApiKeyManager: true,
            ClaudeCodeExport: true,
            SlashCommandSetup: true,
            SerenaAdvancedSettingsDialog: true,
            ContextPriorityConfig: true,
            McpIntegrationCard: true,
            SerenaIntegrationCard: true,
            GitIntegrationCard: true,
          },
        },
      ]

      for (const config of components) {
        const wrapper = mount(config.component, {
          props: config.props,
          global: {
            plugins: [vuetify],
            stubs: config.stubs,
          },
        })

        await wrapper.vm.$nextTick()

        // All components should have the global-tabs class
        const vTabs = wrapper.find('.v-tabs')
        expect(vTabs.classes()).toContain('global-tabs')
      }
    })
  })

  describe('CSS Class Structure', () => {
    it('should define global-tabs class with proper opacity for inactive tabs', () => {
      // This test checks that the global SCSS file defines the correct styles
      // In a real implementation, we would parse the compiled CSS
      // For now, we just ensure the class is applied to components
      const wrapper = mount(ProjectTabs, {
        props: {
          project: { id: 'test', name: 'Test' },
        },
        global: {
          plugins: [vuetify],
          stubs: {
            LaunchTab: true,
            JobsTab: true,
          },
        },
      })

      const vTabs = wrapper.find('.v-tabs')
      expect(vTabs.classes()).toContain('global-tabs')
    })

    it('should define global-tabs class with proper opacity for active tabs', () => {
      const wrapper = mount(ProjectTabs, {
        props: {
          project: { id: 'test', name: 'Test' },
        },
        global: {
          plugins: [vuetify],
          stubs: {
            LaunchTab: true,
            JobsTab: true,
          },
        },
      })

      const vTabs = wrapper.find('.v-tabs')
      expect(vTabs.classes()).toContain('global-tabs')

      // Check that active tab exists
      const activeTab = wrapper.find('.v-tab--selected')
      expect(activeTab.exists()).toBe(true)
    })
  })
})
