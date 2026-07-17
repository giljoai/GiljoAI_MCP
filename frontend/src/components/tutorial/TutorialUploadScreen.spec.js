/**
 * TutorialUploadScreen.spec.js — TSK-9206
 *
 * Regression: if the tutorial's run-owned draft product is deleted externally
 * mid-flow, the upload screen used to keep the id-only stub ({id, name:''}) and a
 * later upload targeted the dead product id (500 server-side). fetchProductById
 * swallows the 404 and returns null, so the fix treats a null lookup as "the
 * draft is gone": it drops the stub and emits `product-invalidated` (the overlay
 * clears s.productId), so the next upload takes the fresh-create branch.
 *
 * Edition scope: CE frontend (shared frontend/src; both editions render it).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const h = vi.hoisted(() => ({
  fetchResult: null, // what productStore.fetchProductById resolves to
  editingRef: null, // the editingProduct ref the component hands the upload composable
  uploadImpl: null, // side effect of uploadVisionFilesOnAttach (simulates create/edit)
  stageAnalysis: vi.fn(),
}))

vi.mock('@/stores/products', () => ({
  useProductStore: () => ({
    fetchProductById: vi.fn(async () => h.fetchResult),
  }),
}))

vi.mock('@/composables/useProductVisionUpload', () => ({
  useProductVisionUpload: ({ editingProduct }) => {
    h.editingRef = editingProduct
    return {
      uploadingVision: ref(false),
      uploadVisionFilesOnAttach: vi.fn(async (args) => h.uploadImpl?.(args)),
    }
  },
}))

vi.mock('@/composables/useVisionAnalysis', () => ({
  useVisionAnalysis: () => ({
    promptFallbackText: ref(''),
    analysisHintVisible: ref(false),
    stageAnalysis: (...a) => h.stageAnalysis(...a),
    onVisionAnalysisComplete: vi.fn(),
    resetAnalysisState: vi.fn(),
  }),
}))

import TutorialUploadScreen from './TutorialUploadScreen.vue'

function mountScreen(productId) {
  return mount(TutorialUploadScreen, {
    props: { productId },
    global: { stubs: { 'v-icon': true, 'v-btn': true } },
  })
}

async function dropFile(wrapper) {
  const file = new File(['vision body'], 'vision.md', { type: 'text/markdown' })
  await wrapper
    .find('[data-testid="tutorial-drop-zone"]')
    .trigger('drop', { dataTransfer: { files: [file] } })
  await flushPromises()
}

describe('TutorialUploadScreen — stale run-owned draft (TSK-9206)', () => {
  beforeEach(() => {
    h.fetchResult = null
    h.editingRef = null
    h.uploadImpl = null
    h.stageAnalysis = vi.fn()
  })

  it('drops the stale stub and invalidates the run product when the draft is gone', async () => {
    h.fetchResult = null // deleted externally -> fetchProductById swallows the 404 -> null
    const wrapper = mountScreen('dead-id')
    await flushPromises()

    expect(wrapper.emitted('product-invalidated')).toBeTruthy()
  })

  it('after invalidation, the next upload creates a FRESH product (never targets the dead id)', async () => {
    h.fetchResult = null
    // Simulate the create branch: the upload composable mints a brand-new product.
    h.uploadImpl = () => {
      h.editingRef.value = { id: 'fresh-id', name: 'vision' }
    }
    const wrapper = mountScreen('dead-id')
    await flushPromises()

    await dropFile(wrapper)

    // The upload registered the FRESH product, not the deleted stub id.
    const created = wrapper.emitted('product-created')
    expect(created).toBeTruthy()
    expect(created.at(-1)).toEqual(['fresh-id'])
    expect(h.stageAnalysis).toHaveBeenCalledWith(expect.anything(), 'fresh-id')
    expect(h.stageAnalysis).not.toHaveBeenCalledWith(expect.anything(), 'dead-id')
  })

  it('happy path: an existing run-owned product is adopted and reused (no invalidation, edit branch)', async () => {
    h.fetchResult = { id: 'live-id', name: 'Live Product' }
    // Edit branch: uploading against an existing product does not mint a new one.
    h.uploadImpl = () => {}
    const wrapper = mountScreen('live-id')
    await flushPromises()

    expect(wrapper.emitted('product-invalidated')).toBeFalsy()

    await dropFile(wrapper)

    // Re-used the adopted product: no new product-created, staged against live-id.
    expect(wrapper.emitted('product-created')).toBeFalsy()
    expect(h.stageAnalysis).toHaveBeenCalledWith(expect.anything(), 'live-id')
  })
})
