import { ref, computed } from 'vue'

const TAB_ORDER = ['setup', 'info', 'tech', 'arch', 'features']

export function useProductFormTabs() {
  const dialogTab = ref('setup')

  const isFirstTab = computed(() => TAB_ORDER.indexOf(dialogTab.value) === 0)
  const isLastTab = computed(() => TAB_ORDER.indexOf(dialogTab.value) === TAB_ORDER.length - 1)

  function goNextTab() {
    const idx = TAB_ORDER.indexOf(dialogTab.value)
    if (idx >= 0 && idx < TAB_ORDER.length - 1) {
      dialogTab.value = TAB_ORDER[idx + 1]
    }
  }

  function goPrevTab() {
    const idx = TAB_ORDER.indexOf(dialogTab.value)
    if (idx > 0) {
      dialogTab.value = TAB_ORDER[idx - 1]
    }
  }

  function resetTab() {
    dialogTab.value = 'setup'
  }

  return {
    dialogTab,
    tabOrder: TAB_ORDER,
    isFirstTab,
    isLastTab,
    goNextTab,
    goPrevTab,
    resetTab,
  }
}
