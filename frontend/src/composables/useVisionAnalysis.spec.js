import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useVisionAnalysis } from './useVisionAnalysis'

describe('useVisionAnalysis', () => {
  let patchProductForm

  beforeEach(() => {
    setActivePinia(createPinia())
    patchProductForm = vi.fn()
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('initializes with default state', () => {
    const {
      analysisBannerDismissed,
      analysisPromptCopied,
      promptFallbackText,
      setupMode,
      analysisInProgress,
      analysisAgentConnected,
      analysisHintVisible,
    } = useVisionAnalysis(patchProductForm)

    expect(analysisBannerDismissed.value).toBe(false)
    expect(analysisPromptCopied.value).toBe(false)
    expect(promptFallbackText.value).toBeNull()
    expect(setupMode.value).toBe('manual')
    expect(analysisInProgress.value).toBe(false)
    expect(analysisAgentConnected.value).toBe(false)
    expect(analysisHintVisible.value).toBe(false)
  })

  it('resetAnalysisState resets all analysis flags', () => {
    const { resetAnalysisState, analysisInProgress, analysisAgentConnected, analysisHintVisible, setupMode } =
      useVisionAnalysis(patchProductForm)

    analysisInProgress.value = true
    analysisAgentConnected.value = true
    analysisHintVisible.value = true

    resetAnalysisState()

    expect(analysisInProgress.value).toBe(false)
    expect(analysisAgentConnected.value).toBe(false)
    expect(analysisHintVisible.value).toBe(false)
  })

  it('onVisionAnalysisStarted sets analysisAgentConnected when product IDs match', () => {
    const { onVisionAnalysisStarted, analysisAgentConnected } = useVisionAnalysis(patchProductForm)

    const event = new CustomEvent('vision-analysis-started', {
      detail: { product_id: 'prod-123' },
    })

    onVisionAnalysisStarted(event, 'prod-123')

    expect(analysisAgentConnected.value).toBe(true)
  })

  it('onVisionAnalysisStarted ignores events for different product IDs', () => {
    const { onVisionAnalysisStarted, analysisAgentConnected } = useVisionAnalysis(patchProductForm)

    const event = new CustomEvent('vision-analysis-started', {
      detail: { product_id: 'prod-other' },
    })

    onVisionAnalysisStarted(event, 'prod-123')

    expect(analysisAgentConnected.value).toBe(false)
  })

  it('onVisionAnalysisComplete calls patchProductForm with updated product data', async () => {
    const { onVisionAnalysisComplete, analysisInProgress, analysisAgentConnected } =
      useVisionAnalysis(patchProductForm)

    analysisInProgress.value = true
    analysisAgentConnected.value = true

    const { useProductStore } = await import('@/stores/products')
    const productStore = useProductStore()
    const mockUpdated = {
      id: 'prod-123',
      name: 'Updated Product',
      description: 'AI populated',
      project_path: '/path',
      target_platforms: ['linux'],
      tech_stack: { programming_languages: 'Python' },
      architecture: { primary_pattern: 'MVC' },
      test_config: { test_strategy: 'TDD', coverage_target: 80 },
      core_features: 'Feature set',
      brand_guidelines: 'Brand info',
      extraction_custom_instructions: '',
    }
    productStore.fetchProductById = vi.fn(() => Promise.resolve(mockUpdated))

    const event = new CustomEvent('vision-analysis-complete', {
      detail: { product_id: 'prod-123' },
    })

    await onVisionAnalysisComplete(event, 'prod-123')

    expect(patchProductForm).toHaveBeenCalledWith(expect.objectContaining({ name: 'Updated Product' }))
    expect(analysisInProgress.value).toBe(false)
    expect(analysisAgentConnected.value).toBe(false)
  })

  it('onVisionAnalysisComplete ignores events for different product IDs', async () => {
    const { onVisionAnalysisComplete } = useVisionAnalysis(patchProductForm)

    const event = new CustomEvent('vision-analysis-complete', {
      detail: { product_id: 'prod-other' },
    })

    await onVisionAnalysisComplete(event, 'prod-123')

    expect(patchProductForm).not.toHaveBeenCalled()
  })

  it('onVisionAnalysisComplete clears analysis hint timer', async () => {
    const { onVisionAnalysisComplete, analysisHintVisible } = useVisionAnalysis(patchProductForm)

    analysisHintVisible.value = true

    const { useProductStore } = await import('@/stores/products')
    const productStore = useProductStore()
    productStore.fetchProductById = vi.fn(() => Promise.resolve(null))

    const event = new CustomEvent('vision-analysis-complete', {
      detail: { product_id: 'prod-123' },
    })

    await onVisionAnalysisComplete(event, 'prod-123')

    expect(analysisHintVisible.value).toBe(false)
  })
})
