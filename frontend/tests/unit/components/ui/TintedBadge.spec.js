import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TintedBadge from '@/components/ui/TintedBadge.vue'

describe('TintedBadge.vue', () => {
  const createWrapper = (props = {}) => {
    return mount(TintedBadge, {
      props: {
        color: '#D4B08A',
        label: 'OR',
        ...props,
      },
    })
  }

  it('renders the 2-char label', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toBe('OR')
  })

  it('applies tinted background from hex color', () => {
    const wrapper = createWrapper({ color: '#AC80CC' })
    const style = wrapper.attributes('style')
    expect(style).toContain('rgba(172, 128, 204, 0.15)')
    expect(style).toContain('color: rgb(172, 128, 204)')
  })

  it('defaults to 36px size', () => {
    const wrapper = createWrapper()
    const style = wrapper.attributes('style')
    expect(style).toContain('width: 36px')
    expect(style).toContain('height: 36px')
  })

  it('respects custom size prop', () => {
    const wrapper = createWrapper({ size: 48 })
    const style = wrapper.attributes('style')
    expect(style).toContain('width: 48px')
    expect(style).toContain('height: 48px')
  })

  it('scales font size proportionally', () => {
    const wrapper = createWrapper({ size: 48 })
    const style = wrapper.attributes('style')
    // 48 * 0.33 = 15.84
    expect(style).toContain('font-size: 15.84px')
  })

  it('enforces minimum font size of 10px', () => {
    const wrapper = createWrapper({ size: 20 })
    const style = wrapper.attributes('style')
    // 20 * 0.33 = 6.6, clamped to 10
    expect(style).toContain('font-size: 10px')
  })

  it('renders as a div element', () => {
    const wrapper = createWrapper()
    expect(wrapper.element.tagName).toBe('DIV')
  })

  it('has border-radius 8px via CSS class', () => {
    const wrapper = createWrapper()
    expect(wrapper.classes()).toContain('tinted-badge')
  })
})
