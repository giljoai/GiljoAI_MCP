import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ProductIntroTour from '@/components/settings/ProductIntroTour.vue'

const pushMock = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}))

describe('ProductIntroTour', () => {
  let storage

  beforeEach(() => {
    pushMock.mockReset()
    storage = {}
    global.localStorage = {
      getItem: (key) => (Object.prototype.hasOwnProperty.call(storage, key) ? storage[key] : null),
      setItem: (key, value) => {
        storage[key] = String(value)
      },
      removeItem: (key) => {
        delete storage[key]
      },
    }
    global.localStorage.removeItem('giljo_intro_tour_hidden')
  })

  it('initializes slides and toggles hidden preference via localStorage', async () => {
    const wrapper = mount(ProductIntroTour, {
      props: { modelValue: true },
      global: {
        stubs: {
          'v-dialog': true,
          'v-card': true,
          'v-card-title': true,
          'v-card-text': true,
          'v-card-actions': true,
          'v-btn': true,
          'v-icon': true,
          'v-chip': true,
          'v-window': true,
          'v-window-item': true,
          'v-avatar': true,
          'v-list': true,
          'v-list-item': true,
          'v-list-item-title': true,
          'v-alert': true,
          'v-divider': true,
          'v-checkbox': true,
        },
      },
    })

    expect(wrapper.vm.slides.length).toBeGreaterThan(0)
    expect(wrapper.vm.activeIndex).toBe(0)

    // Hide preference
    wrapper.vm.dontShowAgain = true
    wrapper.vm.close()

    expect(global.localStorage.getItem('giljo_intro_tour_hidden')).toBe('1')

    // Unhide preference
    wrapper.vm.dontShowAgain = false
    wrapper.vm.close()
    expect(global.localStorage.getItem('giljo_intro_tour_hidden')).toBe(null)
  })

  it('navigates via slide action helpers', () => {
    const wrapper = mount(ProductIntroTour, {
      props: { modelValue: true },
      global: {
        stubs: {
          'v-dialog': true,
          'v-card': true,
          'v-card-title': true,
          'v-card-text': true,
          'v-card-actions': true,
          'v-btn': true,
          'v-icon': true,
          'v-chip': true,
          'v-window': true,
          'v-window-item': true,
          'v-avatar': true,
          'v-list': true,
          'v-list-item': true,
          'v-list-item-title': true,
          'v-alert': true,
          'v-divider': true,
          'v-checkbox': true,
        },
      },
    })

    wrapper.vm.runAction({ type: 'userSettingsTab', tab: 'integrations' })
    expect(pushMock).toHaveBeenCalledWith({ name: 'UserSettings', query: { tab: 'integrations' } })
  })
})
