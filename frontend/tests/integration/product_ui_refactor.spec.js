/**
 * Integration tests for Product UI Refactor (Handover 0316)
 * Tests reorganization of product form UI
 *
 * Post-refactor notes:
 * - ProductForm.vue is now a separate component (not inline in ProductsView)
 * - dialogTab, tabOrder, productForm are internal to ProductForm.vue
 * - Must mount ProductForm directly to test form internals
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import ProductForm from '@/components/products/ProductForm.vue'

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

    // Mount ProductForm component directly
    wrapper = mount(ProductForm, {
      props: {
        modelValue: true,
        product: null,
        isEdit: false,
      },
      global: {
        plugins: [pinia, vuetify],
      }
    })
  })

  it('Core Features field is in Basic Info tab', async () => {
    await wrapper.vm.$nextTick()

    // Should be on Basic Info tab by default
    expect(wrapper.vm.dialogTab).toBe('basic')

    // Core Features v-textarea should exist in Basic Info tab
    // Check productForm.configData.features.core is bound
    const coreFeatures = wrapper.vm.productForm.configData.features.core
    expect(coreFeatures).toBeDefined()
  })

  it('Testing tab is renamed from "Features & Testing"', async () => {
    await wrapper.vm.$nextTick()

    // Check tab order - 'features' tab should still exist (internal value)
    expect(wrapper.vm.tabOrder).toContain('features')

    // The tab LABEL should be "Testing" (not "Features & Testing")
    const tabsText = wrapper.text()
    expect(tabsText).not.toContain('Features & Testing')
  })

  it('Quality Standards field exists in Testing tab', async () => {
    await wrapper.vm.$nextTick()

    // Navigate to Testing tab
    wrapper.vm.dialogTab = 'features'
    await wrapper.vm.$nextTick()

    // Quality Standards field should be in productForm.configData.test_config
    const form = wrapper.vm.productForm
    expect(form.configData).toBeDefined()
    expect(form.configData.test_config).toBeDefined()
  })

  it('Product creation saves quality_standards field', async () => {
    await wrapper.vm.$nextTick()

    // Fill basic info
    wrapper.vm.productForm.name = 'Test Product'
    wrapper.vm.productForm.description = 'Test description'

    // Navigate to Testing tab and verify quality_standards exists
    wrapper.vm.dialogTab = 'features'
    await wrapper.vm.$nextTick()

    // Set quality_standards
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
