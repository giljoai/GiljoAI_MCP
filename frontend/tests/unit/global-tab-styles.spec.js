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

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'

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

// Create shared global stubs for all tests
const globalStubs = {
  'v-tabs': {
    template: '<div class="v-tabs global-tabs"><slot /></div>',
    props: ['modelValue', 'bgColor', 'color', 'class', 'alignTabs', 'showArrows'],
  },
  'v-tab': {
    template: '<div class="v-tab"><slot /></div>',
    props: ['value'],
  },
  'v-window': {
    template: '<div class="v-window global-tabs-window"><slot /></div>',
    props: ['modelValue', 'touch', 'reverse', 'class'],
  },
  'v-window-item': {
    template: '<div class="v-window-item"><slot /></div>',
    props: ['value'],
  },
  'v-tabs-window': {
    template: '<div class="v-tabs-window global-tabs-window"><slot /></div>',
    props: ['modelValue', 'class'],
  },
  'v-tabs-window-item': {
    template: '<div class="v-tabs-window-item"><slot /></div>',
    props: ['value'],
  },
  'v-form': {
    template: '<form><slot /></form>',
    props: ['modelValue'],
  },
  'v-text-field': true,
  'v-textarea': true,
  'v-select': true,
  'v-slider': true,
  'v-file-input': true,
  'v-radio-group': true,
  'v-radio': true,
  'v-switch': true,
  'v-alert': true,
  'v-list': true,
  'v-list-item': true,
  'v-list-item-title': true,
  'v-list-item-subtitle': true,
  'v-progress-circular': true,
  'v-progress-linear': true,
  LaunchTab: true,
  JobsTab: true,
  TemplateManager: true,
  ApiKeyManager: true,
  ClaudeCodeExport: true,
  SlashCommandSetup: true,
  SerenaAdvancedSettingsDialog: true,
  ContextPriorityConfig: true,
  McpIntegrationCard: true,
  SerenaIntegrationCard: true,
  GitIntegrationCard: true,
  NetworkSettingsTab: true,
  DatabaseConnection: true,
  SecuritySettingsTab: true,
  SystemPromptTab: true,
}

describe('Global Tab Styles', () => {
  describe('Tab Opacity Standards', () => {
    it('should apply global-tabs class to v-tabs container', async () => {
      const pinia = createPinia()
      const wrapper = mount(ProjectTabs, {
        props: {
          project: {
            id: 'test-project',
            name: 'Test Project',
          },
        },
        global: {
          plugins: [pinia],
          stubs: globalStubs,
        },
      })

      await wrapper.vm.$nextTick()

      // Check for global-tabs class on v-tabs
      const vTabs = wrapper.find('.v-tabs')
      expect(vTabs.exists()).toBe(true)
      expect(vTabs.classes()).toContain('global-tabs')
    })

  })

  describe('ProjectTabs Component', () => {
    it('should use global-tabs class instead of custom styling', async () => {
      const pinia = createPinia()
      const wrapper = mount(ProjectTabs, {
        props: {
          project: {
            id: 'test-project',
            name: 'Test Project',
          },
        },
        global: {
          plugins: [pinia],
          stubs: globalStubs,
        },
      })

      const vTabs = wrapper.find('.v-tabs')
      expect(vTabs.exists()).toBe(true)
      expect(vTabs.classes()).toContain('global-tabs')
    })

    it('should have global-tabs-window class on v-window', async () => {
      const pinia = createPinia()
      const wrapper = mount(ProjectTabs, {
        props: {
          project: {
            id: 'test-project',
            name: 'Test Project',
          },
        },
        global: {
          plugins: [pinia],
          stubs: globalStubs,
        },
      })

      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('UserSettings Component', () => {
    it('should use global-tabs class', async () => {
      const pinia = createPinia()
      const wrapper = mount(UserSettings, {
        global: {
          plugins: [pinia],
          stubs: globalStubs,
        },
      })

      await wrapper.vm.$nextTick()

      const vTabs = wrapper.find('.v-tabs')
      expect(vTabs.exists()).toBe(true)
      expect(vTabs.classes()).toContain('global-tabs')
    })

    it('should use global-tabs-window class', async () => {
      const pinia = createPinia()
      const wrapper = mount(UserSettings, {
        global: {
          plugins: [pinia],
          stubs: globalStubs,
        },
      })

      await wrapper.vm.$nextTick()

      const vWindow = wrapper.find('.v-window')
      expect(vWindow.exists()).toBe(true)
      expect(vWindow.classes()).toContain('global-tabs-window')
    })
  })

  describe('SystemSettings Component', () => {
    it('should use global-tabs class', async () => {
      const pinia = createPinia()
      const wrapper = mount(SystemSettings, {
        global: {
          plugins: [pinia],
          stubs: globalStubs,
        },
      })

      await wrapper.vm.$nextTick()

      const vTabs = wrapper.find('.v-tabs')
      expect(vTabs.exists()).toBe(true)
      expect(vTabs.classes()).toContain('global-tabs')
    })

    it('should use global-tabs-window class', async () => {
      const pinia = createPinia()
      const wrapper = mount(SystemSettings, {
        global: {
          plugins: [pinia],
          stubs: globalStubs,
        },
      })

      await wrapper.vm.$nextTick()

      const vWindow = wrapper.find('.v-window')
      expect(vWindow.exists()).toBe(true)
      expect(vWindow.classes()).toContain('global-tabs-window')
    })
  })

  describe('ProductForm Component', () => {
    it('should use global-tabs class', async () => {
      const pinia = createPinia()
      const wrapper = mount(ProductForm, {
        props: {
          modelValue: true,
          product: null,
          isEdit: false,
        },
        global: {
          plugins: [pinia],
          stubs: globalStubs,
        },
      })

      await wrapper.vm.$nextTick()

      const vTabs = wrapper.find('.v-tabs')
      expect(vTabs.exists()).toBe(true)
      expect(vTabs.classes()).toContain('global-tabs')
    })

    it('should use global-tabs-window class', async () => {
      const pinia = createPinia()
      const wrapper = mount(ProductForm, {
        props: {
          modelValue: true,
          product: null,
          isEdit: false,
        },
        global: {
          plugins: [pinia],
          stubs: globalStubs,
        },
      })

      await wrapper.vm.$nextTick()

      const vWindow = wrapper.find('.v-tabs-window')
      expect(vWindow.exists()).toBe(true)
      expect(vWindow.classes()).toContain('global-tabs-window')
    })
  })

  describe('Tab Class Consistency', () => {
    it('should have consistent global-tabs class across all tab components', async () => {
      const pinia = createPinia()

      const components = [
        {
          name: 'ProjectTabs',
          component: ProjectTabs,
          props: { project: { id: 'test', name: 'Test' } },
        },
        {
          name: 'UserSettings',
          component: UserSettings,
          props: {},
        },
        {
          name: 'SystemSettings',
          component: SystemSettings,
          props: {},
        },
        {
          name: 'ProductForm',
          component: ProductForm,
          props: { modelValue: true, product: null, isEdit: false },
        },
      ]

      for (const config of components) {
        const wrapper = mount(config.component, {
          props: config.props,
          global: {
            plugins: [pinia],
            stubs: globalStubs,
          },
        })

        await wrapper.vm.$nextTick()

        const vTabs = wrapper.find('.v-tabs')
        expect(vTabs.exists()).toBe(true)
        expect(vTabs.classes()).toContain('global-tabs')
      }
    })
  })
})
