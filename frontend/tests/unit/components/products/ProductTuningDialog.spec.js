import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import ProductTuningDialog from '@/components/products/ProductTuningDialog.vue'

describe('ProductTuningDialog', () => {
  let vuetify

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
    })
  })

  function createWrapper(props = {}) {
    return mount(ProductTuningDialog, {
      props: {
        modelValue: true,
        product: {
          id: 'prod-1',
          name: 'Test Product',
          tuning_state: {
            pending_proposals: {
              overall_summary: 'Context drift detected',
              architecture: {
                current_summary: 'Old architecture',
                proposed_value: 'Updated architecture',
              },
            },
          },
        },
        ...props,
      },
      global: {
        plugins: [vuetify],
        stubs: {
          'v-dialog': {
            template: '<div class="v-dialog" v-if="modelValue"><slot /></div>',
            props: ['modelValue'],
          },
          ProductTuningMenu: {
            template: '<div class="tuning-menu-stub">Tuning Menu Stub</div>',
          },
          ProductTuningReview: {
            template: '<div class="tuning-review-stub">Tuning Review Stub</div>',
          },
        },
      },
    })
  }

  it('renders an independent tune context dialog for a product', () => {
    const wrapper = createWrapper()

    expect(wrapper.text()).toContain('Tune Context')
    expect(wrapper.text()).toContain('Test Product')
    expect(wrapper.text()).toContain('Tuning Review Stub')
    expect(wrapper.text()).toContain('Tuning Menu Stub')
  })

  it('hides the proposals section when no pending proposals exist', () => {
    const wrapper = createWrapper({
      product: {
        id: 'prod-1',
        name: 'Test Product',
        tuning_state: {},
      },
    })

    expect(wrapper.text()).not.toContain('Tuning Review Stub')
    expect(wrapper.text()).toContain('Tuning Menu Stub')
  })
})
