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

    // BE-5118: prompt now drives the AI agent through a multi-document
    // analysis. The agent must (1) read every chunk via get_vision_doc,
    // (2) write a 33% + 66% summary per vision doc, (3) write a 33% + 66%
    // CONSOLIDATED summary across all docs, and (4) commit everything plus
    // the product card fields in a SINGLE update_product_context call so the
    // backend can flip vision_analysis_complete atomically.
    let prompt =
      `Analyze the vision documents for product "${productName}" and populate its configuration.\n` +
      '\n' +
      'Your analysis has two roles:\n' +
      '1. Product Manager — for `consolidated_vision_light` and `consolidated_vision_medium`, write a synthesized cross-document narrative explaining what the product is and why it exists: the developer\'s purpose, what they\'re trying to achieve, important callouts, and proposal context worth retaining. Do NOT add per-document section headers (e.g. `## filename.md`) inside these summaries — they are a unified product story, not a per-source breakdown. Per-doc traceability lives elsewhere in the UI.\n' +
      '2. Engineering Manager — for `tech_stack`, `architecture`, `test_config`, and other structured fields, write absolutes. Extract them if the user defined them in the documents; propose them if the user did not. Write tech specs as committed decisions, even though the user may modify them later.\n' +
      '\n' +
      'Follow these steps in order:\n' +
      `1. Call get_vision_doc(product_id="${productId}") to read every chunk across all vision documents attached to this product.\n` +
      '2. For EACH vision document, generate two summaries:\n' +
      '   - a Light summary (~33% of the original length)\n' +
      '   - a Medium summary (~66% of the original length)\n' +
      '3. For the product as a whole (across ALL documents), generate a CONSOLIDATED Light (~33%) and Medium (~66%) summary as the Product Manager role above — a unified product narrative, not a stitched concatenation, no per-doc section headers.\n' +
      '4. Extract the product card fields (tech stack, architecture, test config, core features, brand guidelines, target platforms, etc.) as the Engineering Manager role above.\n' +
      `5. Call update_product_context ONCE with product_id="${productId}", passing:\n` +
      '   - vision_summaries=[{doc_id, light, medium}, ...] covering every active document\n' +
      '   - consolidated_vision={light, medium}\n' +
      '   - the extracted product card fields grouped into the tech_stack, architecture, quality, and testing dicts (see the tool schema for each group\'s fields), plus the top-level product_name, product_description, and core_features\n' +
      '\n' +
      'A single update_product_context call lets the backend re-evaluate vision_analysis_complete atomically and emit the WebSocket event that unlocks the rest of the product setup wizard. Do not split the write into multiple calls.'

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
