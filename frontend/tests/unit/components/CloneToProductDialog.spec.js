import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref, nextTick, defineComponent, h } from 'vue'
import CloneToProductDialog from '@/components/CloneToProductDialog.vue'
import api from '@/services/api'

// Custom dialog stub that renders slot content
const DialogStub = defineComponent({
  props: ['modelValue'],
  emits: ['update:modelValue'],
  setup(props, { slots }) {
    return () => {
      if (!props.modelValue) return null
      return h('div', { class: 'v-dialog-stub' }, slots.default?.())
    }
  },
})

const mockShowToast = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: mockShowToast }),
}))

describe('CloneToProductDialog', () => {
  const mockTemplate = {
    id: 42,
    name: 'test-implementer',
    role: 'implementer',
  }

  const mockProducts = [
    { id: 1, name: 'Product A' },
    { id: 2, name: 'Product B' },
    { id: 3, name: 'Product C' },
  ]

  const currentProductId = 1

  function mountDialog(propsOverrides = {}) {
    return mount(CloneToProductDialog, {
      props: {
        modelValue: true,
        template: mockTemplate,
        products: mockProducts,
        currentProductId,
        ...propsOverrides,
      },
      global: {
        stubs: {
          'v-dialog': DialogStub,
        },
      },
    })
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders dialog when modelValue is true', () => {
    const wrapper = mountDialog()
    expect(wrapper.find('.clone-dialog').exists()).toBe(true)
  })

  it('does not render when modelValue is false', () => {
    const wrapper = mountDialog({ modelValue: false })
    expect(wrapper.find('.clone-dialog').exists()).toBe(false)
  })

  it('shows template name in header', () => {
    const wrapper = mountDialog()
    expect(wrapper.text()).toContain('test-implementer')
  })

  it('filters out current product from product list', () => {
    const wrapper = mountDialog()
    const text = wrapper.text()
    // Should not show Product A (current product)
    expect(text).not.toContain('Product A')
    // Should show other products
    expect(text).toContain('Product B')
    expect(text).toContain('Product C')
  })

  it('has a close button with dlg-close class', () => {
    const wrapper = mountDialog()
    const closeBtn = wrapper.find('.dlg-close')
    expect(closeBtn.exists()).toBe(true)
  })

  it('calls cloneToProduct API on product selection', async () => {
    api.templates.cloneToProduct.mockResolvedValue({
      data: { success: true, template_id: 99 },
    })

    const wrapper = mountDialog()
    await nextTick()

    // Find and click a product item
    const productItems = wrapper.findAll('[data-testid^="clone-target-"]')
    expect(productItems.length).toBe(2) // Products B and C

    await productItems[0].trigger('click')
    await nextTick()

    expect(api.templates.cloneToProduct).toHaveBeenCalledWith(42, 2)
  })

  it('shows success toast after clone', async () => {
    api.templates.cloneToProduct.mockResolvedValue({
      data: { success: true, template_id: 99 },
    })

    const wrapper = mountDialog()
    await nextTick()

    const productItems = wrapper.findAll('[data-testid^="clone-target-"]')
    await productItems[0].trigger('click')
    await nextTick()

    expect(mockShowToast).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('Product B'),
        type: 'success',
      })
    )
  })

  it('emits update:modelValue false after successful clone', async () => {
    api.templates.cloneToProduct.mockResolvedValue({
      data: { success: true, template_id: 99 },
    })

    const wrapper = mountDialog()
    await nextTick()

    const productItems = wrapper.findAll('[data-testid^="clone-target-"]')
    await productItems[0].trigger('click')
    await nextTick()

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual([false])
  })

  it('emits cloned event with template and product info', async () => {
    api.templates.cloneToProduct.mockResolvedValue({
      data: { success: true, template_id: 99 },
    })

    const wrapper = mountDialog()
    await nextTick()

    const productItems = wrapper.findAll('[data-testid^="clone-target-"]')
    await productItems[0].trigger('click')
    await nextTick()

    expect(wrapper.emitted('cloned')).toBeTruthy()
    expect(wrapper.emitted('cloned')[0][0]).toEqual(
      expect.objectContaining({
        templateId: 42,
        targetProductId: 2,
        targetProductName: 'Product B',
      })
    )
  })

  it('handles API error gracefully', async () => {
    api.templates.cloneToProduct.mockRejectedValue(
      new Error('Clone failed')
    )

    const wrapper = mountDialog()
    await nextTick()

    const productItems = wrapper.findAll('[data-testid^="clone-target-"]')
    await productItems[0].trigger('click')
    await nextTick()

    expect(mockShowToast).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'error',
      })
    )
  })

  it('shows empty state when no other products available', () => {
    const wrapper = mountDialog({
      products: [{ id: 1, name: 'Product A' }],
      currentProductId: 1,
    })

    expect(wrapper.text()).toContain('No other products')
  })
})
