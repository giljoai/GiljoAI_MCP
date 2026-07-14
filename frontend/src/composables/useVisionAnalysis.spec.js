import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useVisionAnalysis } from './useVisionAnalysis'

// Spy-able clipboard mock — replaces useClipboard for the entire spec file.
const copyMock = vi.fn(() => Promise.resolve(true))
vi.mock('@/composables/useClipboard', () => ({
  useClipboard: () => ({
    copy: copyMock,
    copied: { value: false },
  }),
}))

describe('useVisionAnalysis', () => {
  let patchProductForm

  beforeEach(() => {
    setActivePinia(createPinia())
    patchProductForm = vi.fn()
    vi.clearAllMocks()
    copyMock.mockImplementation(() => Promise.resolve(true))
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('initializes with default state', () => {
    const {
      analysisPromptCopied,
      promptFallbackText,
      analysisInProgress,
      analysisAgentConnected,
      analysisHintVisible,
    } = useVisionAnalysis(patchProductForm)

    expect(analysisPromptCopied.value).toBe(false)
    expect(promptFallbackText.value).toBeNull()
    expect(analysisInProgress.value).toBe(false)
    expect(analysisAgentConnected.value).toBe(false)
    expect(analysisHintVisible.value).toBe(false)
  })

  it('resetAnalysisState resets all analysis flags', () => {
    const { resetAnalysisState, analysisInProgress, analysisAgentConnected, analysisHintVisible } =
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

  describe('stageAnalysis', () => {
    const PRODUCT_ID = 'prod-123'

    function expectsBasePrompt(prompt) {
      // BE-9164: the expanded two-role prompt template (BE-5118) now lives
      // server-side in VISION_EXTRACTION_PROMPT (get_vision_doc's
      // extraction_instructions) as the single source of truth. This wizard
      // prompt only needs to point the agent at that flow and require a
      // single atomic update_product_context call.
      expect(prompt).toContain('Analyze the vision documents for product "My Product"')
      expect(prompt).toContain(`get_vision_doc(product_id="${PRODUCT_ID}")`)
      expect(prompt).toMatch(/extraction_instructions/)
      expect(prompt).toMatch(/update_product_context/)
      expect(prompt).toMatch(/ONE single|single call/i)
      expect(prompt).toMatch(/vision_analysis_complete/)
    }

    it('appends custom instructions to prompt when extractionCustomInstructions is non-empty', async () => {
      const { stageAnalysis } = useVisionAnalysis(patchProductForm)
      const productForm = {
        name: 'My Product',
        extractionCustomInstructions: 'Focus on iOS 17+ APIs.',
      }
      const { useProductStore } = await import('@/stores/products')
      useProductStore().updateProduct = vi.fn(() => Promise.resolve({}))

      await stageAnalysis(productForm, PRODUCT_ID)

      expect(copyMock).toHaveBeenCalledTimes(1)
      const copied = copyMock.mock.calls[0][0]
      expectsBasePrompt(copied)
      expect(copied).toContain(
        'Additional extraction guidance from the product owner:\nFocus on iOS 17+ APIs.',
      )
    })

    it('does not append when extractionCustomInstructions is empty or whitespace-only', async () => {
      const { stageAnalysis } = useVisionAnalysis(patchProductForm)
      const productForm = {
        name: 'My Product',
        extractionCustomInstructions: '   \n   ',
      }
      const { useProductStore } = await import('@/stores/products')
      useProductStore().updateProduct = vi.fn(() => Promise.resolve({}))

      await stageAnalysis(productForm, PRODUCT_ID)

      expect(copyMock).toHaveBeenCalledTimes(1)
      const copied = copyMock.mock.calls[0][0]
      expectsBasePrompt(copied)
      expect(copied).not.toContain('Additional extraction guidance')
    })

    it('persists extraction_custom_instructions to product before copying when non-empty', async () => {
      const { stageAnalysis } = useVisionAnalysis(patchProductForm)
      const productForm = {
        name: 'My Product',
        extractionCustomInstructions: '  Focus on iOS 17+ APIs.  ',
      }
      const { useProductStore } = await import('@/stores/products')
      const productStore = useProductStore()

      const callOrder = []
      productStore.updateProduct = vi.fn(() => {
        callOrder.push('update')
        return Promise.resolve({})
      })
      copyMock.mockImplementation(() => {
        callOrder.push('copy')
        return Promise.resolve(true)
      })

      await stageAnalysis(productForm, PRODUCT_ID)

      expect(productStore.updateProduct).toHaveBeenCalledWith(PRODUCT_ID, {
        extraction_custom_instructions: 'Focus on iOS 17+ APIs.',
      })
      expect(callOrder).toEqual(['update', 'copy'])
    })

    it('skips persistence when customInstructions is empty', async () => {
      const { stageAnalysis } = useVisionAnalysis(patchProductForm)
      const productForm = {
        name: 'My Product',
        extractionCustomInstructions: '',
      }
      const { useProductStore } = await import('@/stores/products')
      const productStore = useProductStore()
      productStore.updateProduct = vi.fn(() => Promise.resolve({}))

      await stageAnalysis(productForm, PRODUCT_ID)

      expect(productStore.updateProduct).not.toHaveBeenCalled()
      expect(copyMock).toHaveBeenCalledTimes(1)
    })

    it('does not block the copy when persistence fails', async () => {
      const { stageAnalysis } = useVisionAnalysis(patchProductForm)
      const productForm = {
        name: 'My Product',
        extractionCustomInstructions: 'Focus on iOS 17+ APIs.',
      }
      const { useProductStore } = await import('@/stores/products')
      const productStore = useProductStore()
      productStore.updateProduct = vi.fn(() => Promise.reject(new Error('boom')))
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      await stageAnalysis(productForm, PRODUCT_ID)

      expect(productStore.updateProduct).toHaveBeenCalled()
      expect(copyMock).toHaveBeenCalledTimes(1)
      warnSpy.mockRestore()
    })
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
