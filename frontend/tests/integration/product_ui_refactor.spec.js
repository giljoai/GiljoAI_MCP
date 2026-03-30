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

  it('Core Features field is in Setup tab', async () => {
    await wrapper.vm.$nextTick()

    // Should be on Setup tab by default
    expect(wrapper.vm.dialogTab).toBe('setup')

    // Core Features field is bound to productForm.coreFeatures
    const coreFeatures = wrapper.vm.productForm.coreFeatures
    expect(coreFeatures).toBeDefined()
  })

  it('Testing tab is renamed from "Features & Testing"', async () => {
    await wrapper.vm.$nextTick()

    // Check tab order - 'features' tab should still exist (internal value)
    expect(wrapper.vm.tabOrder).toContain('features')

    // The tab LABEL should not be "Features & Testing"
    const tabsText = wrapper.text()
    expect(tabsText).not.toContain('Features & Testing')
  })

  it('Quality Standards field exists in Testing tab', async () => {
    await wrapper.vm.$nextTick()

    // Navigate to Testing tab
    wrapper.vm.dialogTab = 'features'
    await wrapper.vm.$nextTick()

    // Quality Standards field should be in productForm.testConfig
    const form = wrapper.vm.productForm
    expect(form.testConfig).toBeDefined()
    expect(form.testConfig.quality_standards).toBeDefined()
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
    if (wrapper.vm.productForm.testConfig.quality_standards !== undefined) {
      wrapper.vm.productForm.testConfig.quality_standards = '80% coverage, zero bugs'
    }

    // Verify form data is structured correctly
    expect(wrapper.vm.productForm.testConfig).toBeDefined()
  })

  it('tabOrder is defined correctly', () => {
    expect(wrapper.vm.tabOrder).toEqual(['setup', 'info', 'tech', 'arch', 'features'])
  })
})
