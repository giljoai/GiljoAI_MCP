import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TintedChip from '@/components/ui/TintedChip.vue'

describe('TintedChip.vue', () => {
  const createWrapper = (props = {}) => {
    return mount(TintedChip, {
      props: {
        color: '#E07872',
        label: 'Analyzer',
        ...props,
      },
    })
  }

  it('renders the label text', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toBe('Analyzer')
  })

  it('applies tinted background from hex color', () => {
    const wrapper = createWrapper({ color: '#6DB3E4' })
    const style = wrapper.attributes('style')
    expect(style).toContain('rgba(109, 179, 228, 0.15)')
    expect(style).toContain('color: rgb(109, 179, 228)')
  })

  it('defaults to pill shape (border-radius 9999px)', () => {
    const wrapper = createWrapper()
    expect(wrapper.classes()).toContain('tinted-chip--pill')
  })

  it('uses square shape when pill is false', () => {
    const wrapper = createWrapper({ pill: false })
    expect(wrapper.classes()).not.toContain('tinted-chip--pill')
  })

  it('applies sm size class', () => {
    const wrapper = createWrapper({ size: 'sm' })
    expect(wrapper.classes()).toContain('tinted-chip--sm')
  })

  it('does not apply sm class for default size', () => {
    const wrapper = createWrapper({ size: 'default' })
    expect(wrapper.classes()).not.toContain('tinted-chip--sm')
  })

  it('renders as a span element', () => {
    const wrapper = createWrapper()
    expect(wrapper.element.tagName).toBe('SPAN')
  })
})
