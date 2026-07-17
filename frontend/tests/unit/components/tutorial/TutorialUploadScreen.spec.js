/**
 * Unit tests for TutorialUploadScreen (FE-9200, audit F3) — the re-entry
 * guard: an upload screen re-entered with a run-owned productId must take the
 * composable's EDIT branch (no duplicate silent-create); a fresh entry that
 * creates must register the product with the state machine.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const mockProductStore = {
  createProduct: vi.fn(async ({ name }) => ({ id: 'created-1', name })),
  fetchProductById: vi.fn(async (id) => ({ id, name: 'Run Owned', description: '' })),
  updateProduct: vi.fn(async () => ({})),
}

vi.mock('@/stores/products', () => ({
  useProductStore: () => mockProductStore,
}))

vi.mock('@/composables/useClipboard', () => ({
  useClipboard: () => ({ copy: vi.fn(async () => true) }),
}))

import TutorialUploadScreen from '@/components/tutorial/TutorialUploadScreen.vue'

const vuetify = createVuetify({ components, directives })

function mountScreen(props = {}) {
  return mount(TutorialUploadScreen, {
    props,
    global: { plugins: [vuetify] },
  })
}

function makeVisionFile() {
  return new File(['# Vision\nA product vision.'], 'vision.md', { type: 'text/markdown' })
}

async function dropFile(wrapper) {
  await wrapper.find('[data-testid="tutorial-drop-zone"]').trigger('drop', {
    dataTransfer: { files: [makeVisionFile()] },
  })
  await flushPromises()
}

describe('TutorialUploadScreen', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('creates a product on a fresh entry and registers it with the state machine', async () => {
    const wrapper = mountScreen()
    await dropFile(wrapper)

    expect(mockProductStore.createProduct).toHaveBeenCalledTimes(1)
    expect(wrapper.emitted('product-created')?.at(-1)).toEqual(['created-1'])
  })

  it('re-entry with a run-owned productId does NOT create a second product (audit F3)', async () => {
    const wrapper = mountScreen({ productId: 'run-owned-1' })
    await flushPromises()
    await dropFile(wrapper)

    expect(mockProductStore.createProduct).not.toHaveBeenCalled()
    // No fresh create → nothing new to register.
    expect(wrapper.emitted('product-created')).toBeFalsy()
  })
})
