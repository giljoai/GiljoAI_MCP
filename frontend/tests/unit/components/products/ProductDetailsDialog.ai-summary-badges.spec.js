// FE-vision-card: per-doc AI summary badges and "Summary Previews"
// chevron were removed. The product-level "Vision context summary"
// chevron replaces them. These regression tests guard against the old
// per-doc UI reappearing.
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import ProductDetailsDialog from '@/components/products/ProductDetailsDialog.vue'

describe('ProductDetailsDialog per-doc summary UI (removed)', () => {
  let vuetify

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  const createWrapper = (visionDocuments) => mount(ProductDetailsDialog, {
    props: {
      modelValue: true,
      product: {
        id: 'test-product-123',
        name: 'Test Product',
        description: 'Test description',
      },
      visionDocuments,
    },
    global: {
      plugins: [vuetify],
      stubs: {
        'v-dialog': {
          template: '<div class="v-dialog" v-if="modelValue"><slot /></div>',
          props: ['modelValue'],
        },
      },
    },
  })

  it('does not render the per-doc "Summary Previews" chevron when AI summaries exist', () => {
    const wrapper = createWrapper([
      {
        id: 'doc-1',
        document_name: 'product_vision_v2.md',
        is_summarized: true,
        file_size: 1024,
        summary_light_tokens: 4200,
        summary_medium_tokens: 10800,
      },
    ])

    const toggle = wrapper.findAll('button').find((b) => b.text().includes('Summary Previews'))
    expect(toggle).toBeFalsy()
    expect(wrapper.text()).not.toContain('AI-generated summaries')
    expect(wrapper.text()).not.toContain('33% · 4.2K tokens')
  })

  it('does not render the per-doc summary chevron when AI summaries are missing either', () => {
    const wrapper = createWrapper([
      {
        id: 'doc-1',
        document_name: 'product_vision_v2.md',
        is_summarized: true,
        file_size: 1024,
      },
    ])

    expect(wrapper.text()).not.toContain('Summary Previews')
    expect(wrapper.text()).not.toContain('AI summaries')
  })
})
