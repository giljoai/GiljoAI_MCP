import { describe, it, expect } from 'vitest'
import { useProductFormTabs } from './useProductFormTabs'

describe('useProductFormTabs', () => {
  const TAB_ORDER = ['setup', 'info', 'tech', 'arch', 'features']

  it('initializes to the setup tab', () => {
    const { dialogTab } = useProductFormTabs()
    expect(dialogTab.value).toBe('setup')
  })

  it('isFirstTab is true on the first tab', () => {
    const { isFirstTab } = useProductFormTabs()
    expect(isFirstTab.value).toBe(true)
  })

  it('isLastTab is false on the first tab', () => {
    const { isLastTab } = useProductFormTabs()
    expect(isLastTab.value).toBe(false)
  })

  it('goNextTab advances to the next tab', () => {
    const { dialogTab, goNextTab } = useProductFormTabs()
    goNextTab()
    expect(dialogTab.value).toBe('info')
  })

  it('goNextTab does not advance past the last tab', () => {
    const { dialogTab, goNextTab } = useProductFormTabs()
    for (let i = 0; i < TAB_ORDER.length + 2; i++) {
      goNextTab()
    }
    expect(dialogTab.value).toBe('features')
  })

  it('goPrevTab goes back to the previous tab', () => {
    const { dialogTab, goNextTab, goPrevTab } = useProductFormTabs()
    goNextTab()
    goNextTab()
    expect(dialogTab.value).toBe('tech')
    goPrevTab()
    expect(dialogTab.value).toBe('info')
  })

  it('goPrevTab does not go before the first tab', () => {
    const { dialogTab, goPrevTab } = useProductFormTabs()
    goPrevTab()
    expect(dialogTab.value).toBe('setup')
  })

  it('isLastTab is true on the features tab', () => {
    const { dialogTab, isLastTab } = useProductFormTabs()
    dialogTab.value = 'features'
    expect(isLastTab.value).toBe(true)
  })

  it('isFirstTab is false when not on the first tab', () => {
    const { dialogTab, isFirstTab } = useProductFormTabs()
    dialogTab.value = 'info'
    expect(isFirstTab.value).toBe(false)
  })

  it('resetTab returns to setup tab', () => {
    const { dialogTab, goNextTab, resetTab } = useProductFormTabs()
    goNextTab()
    goNextTab()
    resetTab()
    expect(dialogTab.value).toBe('setup')
  })
})
