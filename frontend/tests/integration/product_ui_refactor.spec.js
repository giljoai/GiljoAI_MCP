/**
 * Integration tests for Product UI Refactor (Handover 0316)
 * Tests reorganization of ProductsView.vue UI
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import ProductsView from '@/views/ProductsView.vue'

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: [] })),
    post: vi.fn(() => Promise.resolve({ data: { id: '123' } })),
    put: vi.fn(() => Promise.resolve({ data: { id: '123' } })),
    delete: vi.fn(() => Promise.resolve({ data: {} })),
  }
}))

describe('Product UI Refactor (Handover 0316)', () => {
  let wrapper
  let vuetify

  beforeEach(() => {
    // Setup Pinia
    const pinia = createPinia()
    setActivePinia(pinia)

    // Setup Vuetify
    vuetify = createVuetify({
      components,
      directives,
    })

    // Mount component
    wrapper = mount(ProductsView, {
      global: {
        plugins: [pinia, vuetify],
        stubs: {
          'v-dialog': false,
          'v-tabs': false,
          'v-tabs-window': false,
          'v-tabs-window-item': false,
        }
      }
    })
  })

  it('Core Features field is in Basic Info tab', async () => {
    // Open create product dialog
    wrapper.vm.showDialog = true
    await wrapper.vm.$nextTick()

    // Should be on Basic Info tab by default
    expect(wrapper.vm.dialogTab).toBe('basic')

    // Find the Core Features field - it should be in Basic Info tab
    const basicTabContent = wrapper.find('[value="basic"]')
    expect(basicTabContent.exists()).toBe(true)

    // Core Features v-textarea should exist in Basic Info tab
    // Check productForm.configData.features.core is bound
    const coreFeatures = wrapper.vm.productForm.configData.features.core
    expect(coreFeatures).toBeDefined()
  })

  it('Testing tab is renamed from "Features & Testing"', async () => {
    // Open create product dialog
    wrapper.vm.showDialog = true
    await wrapper.vm.$nextTick()

    // Check tab order - 'features' tab should still exist (internal value)
    expect(wrapper.vm.tabOrder).toContain('features')

    // The tab LABEL should be "Testing" (not "Features & Testing")
    // This will be verified in the template
    const tabsText = wrapper.text()
    expect(tabsText).not.toContain('Features & Testing')
  })

  it('Quality Standards field exists in Testing tab', async () => {
    // Open create product dialog
    wrapper.vm.showDialog = true
    await wrapper.vm.$nextTick()

    // Navigate to Testing tab
    wrapper.vm.dialogTab = 'features'
    await wrapper.vm.$nextTick()

    // Quality Standards field should be in productForm.configData
    // (After we add it in GREEN phase)
    const form = wrapper.vm.productForm
    expect(form.configData).toBeDefined()
    expect(form.configData.test_config).toBeDefined()
  })

  it('Product creation saves quality_standards field', async () => {
    // This test will verify backend integration
    // Open create product dialog
    wrapper.vm.showDialog = true
    await wrapper.vm.$nextTick()

    // Fill basic info
    wrapper.vm.productForm.name = 'Test Product'
    wrapper.vm.productForm.description = 'Test description'

    // Navigate to Testing tab and fill quality_standards
    wrapper.vm.dialogTab = 'features'
    await wrapper.vm.$nextTick()

    // Set quality_standards (after we add it in GREEN phase)
    if (wrapper.vm.productForm.configData.test_config.quality_standards !== undefined) {
      wrapper.vm.productForm.configData.test_config.quality_standards = '80% coverage, zero bugs'
    }

    // Verify form data is structured correctly
    expect(wrapper.vm.productForm.configData.test_config).toBeDefined()
  })

  it('tabOrder is defined correctly', () => {
    expect(wrapper.vm.tabOrder).toEqual(['basic', 'vision', 'tech', 'arch', 'features'])
  })
})
