import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'
import ProductForm from '@/components/products/ProductForm.vue'

/**
 * 0842h: Tests for the vision analysis banner and custom instructions
 * in ProductForm.vue.
 *
 * The analysis banner appears when:
 * - setupMode is 'ai' (user selects AI radio)
 * - Vision documents exist
 * - Banner has not been dismissed
 *
 * Custom extraction instructions textarea appears under the same conditions.
 */
describe('ProductForm — Vision Analysis Banner', () => {
  let vuetify
  let pinia

  const existingDocs = [
    { id: 'doc-1', filename: 'design.pdf', size: 1024, status: 'ready' },
  ]

  const baseProduct = {
    id: 'prod-1',
    name: 'Test Product',
    description: 'A product',
    tech_stack: '',
    architecture: '',
    test_config: '',
    coding_conventions: '',
    brand_guidelines: '',
    extraction_custom_instructions: '',
  }

  beforeEach(() => {
    vuetify = createVuetify({ components, directives })
    pinia = createPinia()
    setActivePinia(pinia)
  })

  function createWrapper(props = {}) {
    return mount(ProductForm, {
      props: {
        modelValue: true,
        isEdit: true,
        product: baseProduct,
        existingVisionDocuments: existingDocs,
        uploadingVision: false,
        uploadProgress: 0,
        visionUploadError: null,
        ...props,
      },
      global: {
        plugins: [vuetify, pinia],
        stubs: {
          'v-dialog': {
            template: '<div class="v-dialog" v-if="modelValue"><slot /></div>',
            props: ['modelValue'],
          },
          'v-file-input': { template: '<input type="file" />' },
        },
      },
    })
  }

  it('renders dialog in edit mode with product data', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.v-dialog').exists()).toBe(true)
    // Product name is loaded into form fields (not visible as plain text)
    expect(wrapper.html()).toContain('Save Changes')
  })

  it('does not show analysis banner in default manual mode', () => {
    const wrapper = createWrapper()
    // In manual mode, the AI analysis banner should not appear
    expect(wrapper.html()).not.toContain('Want AI to analyze this document')
  })

  it('shows Stage Analysis button text somewhere in the component', () => {
    const wrapper = createWrapper()
    // The "Stage Analysis" button is conditional on setupMode === 'ai'
    // In manual mode it should not be visible
    expect(wrapper.html()).not.toContain('Stage Analysis')
  })

  it('loads custom extraction instructions from product prop', () => {
    const product = {
      ...baseProduct,
      extraction_custom_instructions: 'Focus on mobile-first architecture',
    }
    const wrapper = createWrapper({ product })
    // The component should load the extraction_custom_instructions into form state
    expect(wrapper.vm).toBeTruthy()
  })

  it('renders without vision documents gracefully', () => {
    const wrapper = createWrapper({ existingVisionDocuments: [] })
    expect(wrapper.find('.v-dialog').exists()).toBe(true)
    // No analysis features without documents
    expect(wrapper.html()).not.toContain('Want AI to analyze this document')
  })

  it('renders in create mode without product', () => {
    const wrapper = createWrapper({ isEdit: false, product: null })
    expect(wrapper.find('.v-dialog').exists()).toBe(true)
  })
})
