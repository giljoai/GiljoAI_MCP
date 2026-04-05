import { ref } from 'vue'
import { useProductStore } from '@/stores/products'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'

export function useVisionAnalysis(patchProductForm) {
  const productStore = useProductStore()
  const { copy: copyToClipboard } = useClipboard()
  const { showToast } = useToast()

  const analysisBannerDismissed = ref(false)
  const analysisPromptCopied = ref(false)
  const promptFallbackText = ref(null)
  const setupMode = ref('manual')
  const analysisInProgress = ref(false)
  const analysisAgentConnected = ref(false)
  const analysisHintVisible = ref(false)
  let analysisHintTimer = null

  function resetAnalysisState() {
    analysisInProgress.value = false
    analysisAgentConnected.value = false
    analysisHintVisible.value = false
    clearTimeout(analysisHintTimer)
    analysisHintTimer = null
  }

  async function stageAnalysis(productForm, productId) {
    if (!productId) {
      console.warn('[useVisionAnalysis] stageAnalysis called but no product ID available.')
      return
    }

    const productName = productForm.name || 'this product'
    const prompt = `Analyze the vision document for product "${productName}" and populate its configuration.\nUse the gil_get_vision_doc tool with product_id "${productId}" to read the document and extraction instructions, then call gil_write_product with the extracted fields.`

    promptFallbackText.value = null
    const didCopy = await copyToClipboard(prompt)

    if (didCopy) {
      analysisPromptCopied.value = true
      showToast({ message: 'Analysis prompt copied — paste into your AI coding agent', type: 'success', timeout: 4000 })
      setTimeout(() => { analysisPromptCopied.value = false }, 3000)
    } else {
      promptFallbackText.value = prompt
      showToast({ message: 'Clipboard unavailable — copy the prompt manually below', type: 'warning', timeout: 5000 })
    }

    analysisInProgress.value = true

    analysisHintVisible.value = false
    clearTimeout(analysisHintTimer)
    analysisHintTimer = setTimeout(() => { analysisHintVisible.value = true }, 60000)
  }

  function onVisionAnalysisStarted(event, currentProductId) {
    const productId = event.detail?.product_id
    if (productId && productId === currentProductId) {
      analysisAgentConnected.value = true
    }
  }

  async function onVisionAnalysisComplete(event, currentProductId) {
    const productId = event.detail?.product_id
    if (!productId || productId !== currentProductId) return

    analysisHintVisible.value = false
    clearTimeout(analysisHintTimer)
    analysisHintTimer = null

    const updated = await productStore.fetchProductById(productId)
    if (updated) {
      const ts = updated.tech_stack || {}
      const arch = updated.architecture || {}
      const tc = updated.test_config || {}

      patchProductForm({
        name: updated.name || '',
        description: updated.description || '',
        projectPath: updated.project_path || '',
        targetPlatforms: updated.target_platforms || ['all'],
        techStack: {
          programming_languages: ts.programming_languages || '',
          frontend_frameworks: ts.frontend_frameworks || '',
          backend_frameworks: ts.backend_frameworks || '',
          databases_storage: ts.databases_storage || '',
          infrastructure: ts.infrastructure || '',
        },
        architecture: {
          primary_pattern: arch.primary_pattern || '',
          design_patterns: arch.design_patterns || '',
          api_style: arch.api_style || '',
          architecture_notes: arch.architecture_notes || '',
          coding_conventions: arch.coding_conventions || '',
        },
        coreFeatures: updated.core_features || '',
        brandGuidelines: updated.brand_guidelines || '',
        testConfig: {
          quality_standards: tc.quality_standards || '',
          test_strategy: tc.test_strategy || 'TDD',
          coverage_target: tc.coverage_target || 80,
          testing_frameworks: tc.testing_frameworks || '',
        },
        extractionCustomInstructions: updated.extraction_custom_instructions || '',
      })
    }

    analysisInProgress.value = false
    analysisAgentConnected.value = false
  }

  return {
    analysisBannerDismissed,
    analysisPromptCopied,
    promptFallbackText,
    setupMode,
    analysisInProgress,
    analysisAgentConnected,
    analysisHintVisible,
    resetAnalysisState,
    stageAnalysis,
    onVisionAnalysisStarted,
    onVisionAnalysisComplete,
  }
}
