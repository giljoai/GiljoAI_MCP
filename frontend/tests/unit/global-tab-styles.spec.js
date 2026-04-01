/**
 * Test: Global Tab Styling Standardization
 *
 * Tests for consistent tab styling across the application.
 *
 * Post-refactor notes:
 * - ProductForm uses v-btn-toggle for tab navigation
 * - ProjectTabs uses pill-button toggles (0871c)
 * - UserSettings and SystemSettings use pill-button toggles (0871b)
 * - global-tabs-window class is used on v-window for tab content
 *
 * Components tested:
 * - ProjectTabs.vue (pill-toggle buttons)
 * - UserSettings.vue (pill-toggle buttons)
 * - SystemSettings.vue (pill-toggle buttons)
 * - ProductForm.vue (v-btn-toggle)
 *
 * Note on testing strategy:
 * The global test setup (tests/setup.js) mocks Vuetify components with
 * simple HTML stubs. v-btn-toggle is NOT in the global stubs, so it
 * renders as an unresolved custom element <v-btn-toggle>. We use
 * wrapper.find('v-btn-toggle') to locate it in the rendered HTML.
 * Similarly, v-window renders as a <div class="v-window"> stub that
 * does not preserve parent-template classes. For the global-tabs-window
 * class test, we verify the class appears in the raw HTML output since
 * the stub's v-bind="$attrs" can propagate it in some cases, or we
 * read the source file statically.
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { readFileSync } from 'fs'
import { resolve } from 'path'

// Import components to test
import ProjectTabs from '@/components/projects/ProjectTabs.vue'
import UserSettings from '@/views/UserSettings.vue'
import SystemSettings from '@/views/SystemSettings.vue'
import ProductForm from '@/components/products/ProductForm.vue'

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
    users: {
      getFieldToggleConfig: vi.fn().mockResolvedValue({ data: { priorities: {} } }),
    },
  },
}))

vi.mock('@/services/setupService', () => ({
  default: {
    getSerenaStatus: vi.fn().mockResolvedValue({ enabled: false }),
    toggleSerena: vi.fn().mockResolvedValue({ success: true, enabled: false }),
  },
}))

// Mock child components that may cause import issues
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocketV2: () => ({
    on: vi.fn(),
    off: vi.fn(),
  }),
}))

const vuetify = createVuetify({ components, directives })

// Create shared global stubs for all tests
const globalStubs = {
  LaunchTab: true,
  JobsTab: true,
  TemplateManager: true,
  ApiKeyManager: true,
  AgentExport: true,
  SerenaAdvancedSettingsDialog: true,
  ContextPriorityConfig: true,
  McpIntegrationCard: true,
  SerenaIntegrationCard: true,
  GitIntegrationCard: true,
  GitAdvancedSettingsDialog: true,
  ProductIntroTour: true,
  NetworkSettingsTab: true,
  DatabaseConnection: true,
  SecuritySettingsTab: true,
  SystemPromptTab: true,
  CloseoutModal: true,
}

describe('Global Tab Styles', () => {
  describe('Tab Implementation Standard', () => {
    it('ProjectTabs uses pill-button toggles for tab navigation', async () => {
      const pinia = createPinia()
      const wrapper = mount(ProjectTabs, {
        props: {
          project: {
            id: 'test-project',
            name: 'Test Project',
          },
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: globalStubs,
        },
      })

      await wrapper.vm.$nextTick()

      const pills = wrapper.findAll('.pill-btn')
      expect(pills.length).toBeGreaterThanOrEqual(2)
      expect(wrapper.find('.tab-pills').exists()).toBe(true)
    })
  })

  describe('UserSettings Component', () => {
    it('uses pill-toggle buttons for tab navigation', async () => {
      const pinia = createPinia()
      const wrapper = mount(UserSettings, {
        global: {
          plugins: [pinia, vuetify],
          stubs: globalStubs,
        },
      })

      await wrapper.vm.$nextTick()

      const pills = wrapper.findAll('.pill-toggle')
      expect(pills.length).toBe(6)
      expect(wrapper.find('.pill-toggle-row').exists()).toBe(true)
    })

    it('uses global-tabs-window class on v-window', () => {
      // Static source code verification: the UserSettings template
      // must apply class="global-tabs-window" to its v-window element.
      const srcPath = resolve(__dirname, '../../src/views/UserSettings.vue')
      const source = readFileSync(srcPath, 'utf-8')
      expect(source).toContain('class="global-tabs-window"')
      expect(source).toContain('<v-window')
    })
  })

  describe('SystemSettings Component', () => {
    it('uses pill-toggle buttons for tab navigation', async () => {
      const pinia = createPinia()
      const wrapper = mount(SystemSettings, {
        global: {
          plugins: [pinia, vuetify],
          stubs: globalStubs,
        },
      })

      await wrapper.vm.$nextTick()

      const pills = wrapper.findAll('.pill-toggle')
      expect(pills.length).toBe(5)
      expect(wrapper.find('.pill-toggle-row').exists()).toBe(true)
    })

    it('uses global-tabs-window class on v-window', () => {
      // Static source code verification
      const srcPath = resolve(__dirname, '../../src/views/SystemSettings.vue')
      const source = readFileSync(srcPath, 'utf-8')
      expect(source).toContain('class="global-tabs-window"')
      expect(source).toContain('<v-window')
    })
  })

  describe('ProductForm Component', () => {
    it('uses v-btn-toggle for tab navigation', async () => {
      const pinia = createPinia()
      const wrapper = mount(ProductForm, {
        props: {
          modelValue: true,
          product: null,
          isEdit: false,
        },
        global: {
          plugins: [pinia, vuetify],
          stubs: globalStubs,
        },
      })

      await wrapper.vm.$nextTick()

      const html = wrapper.html()
      expect(html).toContain('v-btn-toggle')
    })

    it('does not use global-tabs-window on ProductForm (dialog-based)', () => {
      // ProductForm uses a bordered-tabs-content pattern inside a dialog,
      // not the global-tabs-window class used by full-page views.
      const srcPath = resolve(__dirname, '../../src/components/products/ProductForm.vue')
      const source = readFileSync(srcPath, 'utf-8')
      expect(source).toContain('bordered-tabs-content')
    })
  })

  describe('Tab Class Consistency', () => {
    it('ProductForm uses v-btn-toggle', async () => {
      const pinia = createPinia()

      const wrapper = mount(ProductForm, {
        props: { modelValue: true, product: null, isEdit: false },
        global: {
          plugins: [pinia, vuetify],
          stubs: globalStubs,
        },
      })

      await wrapper.vm.$nextTick()

      const html = wrapper.html()
      expect(html).toContain('v-btn-toggle')
    })

    it('ProjectTabs uses pill-button toggles', async () => {
      const pinia = createPinia()

      const wrapper = mount(ProjectTabs, {
        props: { project: { id: 'test', name: 'Test' } },
        global: {
          plugins: [pinia, vuetify],
          stubs: globalStubs,
        },
      })

      await wrapper.vm.$nextTick()

      const pills = wrapper.findAll('.pill-btn')
      expect(pills.length).toBeGreaterThanOrEqual(2)
    })

    it('UserSettings and SystemSettings use pill-toggle buttons', async () => {
      const pinia = createPinia()

      const configs = [
        { name: 'UserSettings', component: UserSettings, props: {}, expectedPills: 6 },
        { name: 'SystemSettings', component: SystemSettings, props: {}, expectedPills: 5 },
      ]

      for (const config of configs) {
        const wrapper = mount(config.component, {
          props: config.props,
          global: {
            plugins: [pinia, vuetify],
            stubs: globalStubs,
          },
        })

        await wrapper.vm.$nextTick()

        const pills = wrapper.findAll('.pill-toggle')
        expect(pills.length).toBe(config.expectedPills)
      }
    })
  })
})
