import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import ProductDetailsDialog from '@/components/products/ProductDetailsDialog.vue'

describe('ProductDetailsDialog AI summary badges', () => {
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

  it('renders per-document AI summary badges when AI summaries exist', async () => {
    const wrapper = createWrapper([
      {
        id: 'doc-1',
        document_name: 'product_vision_v2.md',
        is_summarized: true,
        file_size: 1024,
        has_ai_summaries: true,
        ai_summary_light_tokens: 4200,
        ai_summary_medium_tokens: 10800,
      },
    ])

    const toggles = wrapper.findAll('button')
    const summaryToggle = toggles.find((button) => button.text().includes('Summary Previews'))
    await summaryToggle.trigger('click')

    expect(wrapper.text()).toContain('AI summaries')
    expect(wrapper.text()).toContain('33% · 4.2K tokens')
    expect(wrapper.text()).toContain('66% · 10.8K tokens')
  })

  it('hides per-document AI summary badges when AI summaries do not exist', () => {
    const wrapper = createWrapper([
      {
        id: 'doc-1',
        document_name: 'product_vision_v2.md',
        is_summarized: true,
        file_size: 1024,
        has_ai_summaries: false,
      },
    ])

    expect(wrapper.text()).not.toContain('AI summaries')
  })
})
