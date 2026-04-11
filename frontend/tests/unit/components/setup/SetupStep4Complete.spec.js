/**
 * Unit tests for SetupStep4Complete component (Handover 0855f)
 * Covers header rendering.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import SetupStep4Complete from '@/components/setup/SetupStep4Complete.vue'

const vuetify = createVuetify({ components, directives })

function mountStep4(props = {}) {
  return mount(SetupStep4Complete, {
    props,
    global: {
      plugins: [vuetify],
    },
  })
}

describe('SetupStep4Complete', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // -------------------------------------------------------------------
  // Rendering
  // -------------------------------------------------------------------
  describe('Rendering', () => {
    it('renders success header with "You\'re all set!" text', () => {
      const wrapper = mountStep4()
      const title = wrapper.find('.complete-title')

      expect(title.exists()).toBe(true)
      expect(title.text()).toBe("You're all set!")
    })

    it('renders subtitle text about AI coding tools', () => {
      const wrapper = mountStep4()
      const subtitle = wrapper.find('.complete-subtitle')

      expect(subtitle.exists()).toBe(true)
      expect(subtitle.text()).toContain('AI coding tools')
      expect(subtitle.text()).toContain('connected and ready')
    })

    it('does not render a Continue button (completion handled by parent Finish button)', () => {
      const wrapper = mountStep4()
      const btn = wrapper.find('.card-btn')

      expect(btn.exists()).toBe(false)
    })
  })
})
