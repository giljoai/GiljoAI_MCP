import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import ProductTuningMenu from '@/components/products/ProductTuningMenu.vue'

vi.mock('@/services/api', () => ({
  default: {
    products: {
      getTuningSections: vi.fn(async () => ({
        data: { sections: ['description', 'architecture'] },
      })),
      generateTuningPrompt: vi.fn(),
    },
  },
}))

vi.mock('@/composables/useClipboard', () => ({
  useClipboard: () => ({
    copy: vi.fn(async () => true),
    copied: false,
  }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn(),
  }),
}))

describe('ProductTuningMenu', () => {
  let vuetify

  beforeEach(() => {
    vuetify = createVuetify({ components, directives })
  })

  it('does not render a duplicate trigger when embedded with hideTrigger', async () => {
    const wrapper = mount(ProductTuningMenu, {
      props: {
        productId: 'prod-1',
        hideTrigger: true,
        initiallyOpen: true,
      },
      global: {
        plugins: [vuetify],
      },
    })

    await flushPromises()

    expect(wrapper.text()).not.toContain('Tune Context')
    expect(wrapper.text()).toContain('Select Sections to Tune')
  })
})
