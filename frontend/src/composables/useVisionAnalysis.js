import { ref } from 'vue'
import { useProductStore } from '@/stores/products'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'

export function useVisionAnalysis(patchProductForm) {
  const productStore = useProductStore()
  const { copy: copyToClipboard } = useClipboard()
  const { showToast } = useToast()

  const analysisPromptCopied = ref(false)
  const promptFallbackText = ref(null)
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
    const customInstructions = (productForm.extractionCustomInstructions || '').trim()

    // Persist custom instructions BEFORE copying so the agent (which fetches the
    // product via get_vision_doc) sees the latest text. Non-blocking on failure —
    // the user's primary action is copying the prompt, not waiting for an API.
    if (customInstructions) {
      try {
        await productStore.updateProduct(productId, {
          extraction_custom_instructions: customInstructions,
        })
      } catch (err) {
        console.warn('[useVisionAnalysis] Failed to persist extraction_custom_instructions:', err)
      }
    }

    // BE-9164: the detailed two-role analysis brief now lives server-side in
    // VISION_EXTRACTION_PROMPT and is returned by get_vision_doc as
    // extraction_instructions (single source of truth). This wizard prompt only
    // points the agent at that flow.
    let prompt =
      `Analyze the vision documents for product "${productName}".\n` +
      `1. Call get_vision_doc(product_id="${productId}") and FOLLOW the extraction_instructions embedded in the response.\n` +
      `2. Make ONE single update_product_context call with product_id="${productId}" covering all per-document and consolidated summaries plus the product card fields. A single call lets the backend flip vision_analysis_complete atomically and emit the WebSocket event that unlocks the rest of the setup wizard.`

    if (customInstructions) {
      prompt += `\n\nAdditional extraction guidance from the product owner:\n${customInstructions}`
    }

    promptFallbackText.value = null
    const didCopy = await copyToClipboard(prompt)

    if (didCopy) {
      analysisPromptCopied.value = true
      showToast({ message: 'Discovery prompt copied. Paste into your AI agent to analyze your vision doc.', type: 'success', timeout: 4000 })
      setTimeout(() => { analysisPromptCopied.value = false }, 3000)
    } else {
      promptFallbackText.value = prompt
      showToast({ message: 'Clipboard blocked. Select the prompt below and press Ctrl+C.', type: 'warning', timeout: 5000 })
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
    analysisPromptCopied,
    promptFallbackText,
    analysisInProgress,
    analysisAgentConnected,
    analysisHintVisible,
    resetAnalysisState,
    stageAnalysis,
    onVisionAnalysisStarted,
    onVisionAnalysisComplete,
  }
}
