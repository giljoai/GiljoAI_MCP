import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import DeletedProductsRecoveryDialog from '@/components/products/DeletedProductsRecoveryDialog.vue'

describe('DeletedProductsRecoveryDialog Component', () => {
  const defaultProps = {
    modelValue: true,
    deletedProducts: [],
    restoringProductId: null,
    purgingProductId: null,
    purgingAll: false
  }

  const sampleDeletedProducts = [
    {
      id: 'prod-1',
      name: 'Product A',
      description: 'First test product',
      deleted_at: '2025-11-10T12:00:00Z',
    },
    {
      id: 'prod-2',
      name: 'Product B',
      description: 'Second test product',
      deleted_at: '2025-11-15T08:30:00Z',
    },
    {
      id: 'prod-3',
      name: 'Product C',
      description: null,
      deleted_at: '2025-11-18T16:45:00Z',
    }
  ]

  const createWrapper = (props = {}) => {
    return mount(DeletedProductsRecoveryDialog, {
      props: { ...defaultProps, ...props },
      global: {
        stubs: {
          'v-dialog': {
            template: '<div class="v-dialog" v-if="modelValue"><slot /></div>',
            props: ['modelValue']
          },
          'v-list-item': {
            template: '<div class="v-list-item"><slot name="prepend" /><slot /><slot name="append" /></div>',
          },
        },
      }
    })
  }

  describe('Dialog Visibility', () => {
    it('renders dialog when modelValue is true', () => {
      const wrapper = createWrapper({ modelValue: true })

      expect(wrapper.find('.v-dialog').exists()).toBe(true)
    })

    it('does not render dialog when modelValue is false', () => {
      const wrapper = createWrapper({ modelValue: false })

      expect(wrapper.find('.v-dialog').exists()).toBe(false)
    })

    it('emits update:modelValue when close button is clicked', async () => {
      const wrapper = createWrapper({ modelValue: true })

      // The close button has aria-label="Close dialog"
      const closeButton = wrapper.find('button[aria-label="Close dialog"]')
      expect(closeButton.exists()).toBe(true)
      await closeButton.trigger('click')

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')[0]).toEqual([false])
    })
  })

  describe('Product List Display', () => {
    it('displays list of deleted products', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: sampleDeletedProducts
      })

      const listItems = wrapper.findAll('.v-list-item')
      expect(listItems.length).toBe(3)
    })

    it('shows product name in each list item', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: sampleDeletedProducts
      })

      const html = wrapper.html()
      expect(html).toContain('Product A')
      expect(html).toContain('Product B')
      expect(html).toContain('Product C')
    })

    it('shows product description or fallback to id', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: sampleDeletedProducts
      })

      const html = wrapper.html()
      expect(html).toContain('First test product')
      expect(html).toContain('Second test product')
      // Product C has null description, falls back to product.id
      expect(html).toContain('prod-3')
    })
  })

  describe('Product Count Display', () => {
    it('displays count of deleted products in title', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: sampleDeletedProducts
      })

      const html = wrapper.html()
      expect(html).toContain('Deleted Products (3)')
    })

    it('shows zero count when no products', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: []
      })

      const html = wrapper.html()
      expect(html).toContain('Deleted Products (0)')
    })
  })

  describe('Restore Functionality', () => {
    it('emits restore event with product id when restore button clicked', async () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: [sampleDeletedProducts[0]]
      })

      const restoreButton = wrapper.find('button[aria-label="Restore deleted product"]')
      expect(restoreButton.exists()).toBe(true)
      await restoreButton.trigger('click')

      expect(wrapper.emitted('restore')).toBeTruthy()
      expect(wrapper.emitted('restore')[0]).toEqual(['prod-1'])
    })

    it('shows loading state on restore button when restoring that product', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: [sampleDeletedProducts[0]],
        restoringProductId: 'prod-1'
      })

      const restoreButton = wrapper.find('button[aria-label="Restore deleted product"]')
      expect(restoreButton.exists()).toBe(true)
      // The button should have loading attribute passed through
      expect(restoreButton.attributes('loading')).toBe('true')
    })

    it('disables purge button when product is being restored', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: [sampleDeletedProducts[0]],
        restoringProductId: 'prod-1'
      })

      const purgeButton = wrapper.find('button[aria-label="Permanently delete product"]')
      expect(purgeButton.exists()).toBe(true)
      expect(purgeButton.attributes('disabled')).toBeDefined()
    })
  })

  describe('Purge Functionality', () => {
    it('emits purge event with product id when purge button clicked', async () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: [sampleDeletedProducts[0]]
      })

      const purgeButton = wrapper.find('button[aria-label="Permanently delete product"]')
      expect(purgeButton.exists()).toBe(true)
      await purgeButton.trigger('click')

      expect(wrapper.emitted('purge')).toBeTruthy()
      expect(wrapper.emitted('purge')[0]).toEqual(['prod-1'])
    })

    it('emits purge-all event when Delete All button clicked', async () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: sampleDeletedProducts
      })

      const buttons = wrapper.findAll('button')
      const deleteAllBtn = buttons.find(btn => btn.text().includes('Delete All'))
      expect(deleteAllBtn).toBeTruthy()
      await deleteAllBtn.trigger('click')

      expect(wrapper.emitted('purge-all')).toBeTruthy()
    })

    it('disables Delete All button when no products', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: []
      })

      const buttons = wrapper.findAll('button')
      const deleteAllBtn = buttons.find(btn => btn.text().includes('Delete All'))
      expect(deleteAllBtn).toBeTruthy()
      expect(deleteAllBtn.attributes('disabled')).toBeDefined()
    })
  })

  describe('Empty State', () => {
    it('displays empty state when no deleted products', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: []
      })

      const html = wrapper.html()
      expect(html).toContain('No deleted products')
    })

    it('shows empty state icon', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: []
      })

      const html = wrapper.html()
      expect(html).toContain('mdi-package-variant')
    })

    it('does not show list when empty', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: []
      })

      expect(wrapper.find('.v-list').exists()).toBe(false)
    })
  })

  describe('Warning Alert', () => {
    it('displays warning alert when products exist', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: sampleDeletedProducts
      })

      const html = wrapper.html()
      expect(html).toContain('Permanently deleting')
      expect(html).toContain('cannot be undone')
    })
  })

  describe('Close Actions', () => {
    it('emits update:modelValue when Close button in actions is clicked', async () => {
      const wrapper = createWrapper({ modelValue: true })

      const buttons = wrapper.findAll('button')
      const closeButton = buttons.find(btn =>
        btn.text().includes('Close')
      )

      expect(closeButton).toBeTruthy()
      await closeButton.trigger('click')

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    })
  })

  describe('Accessibility', () => {
    it('has proper dialog structure', () => {
      const wrapper = createWrapper({ modelValue: true })

      expect(wrapper.find('.v-dialog').exists()).toBe(true)
    })

    it('has close button with aria-label in header', () => {
      const wrapper = createWrapper({ modelValue: true })

      const closeButton = wrapper.find('button[aria-label="Close dialog"]')
      expect(closeButton.exists()).toBe(true)
    })
  })
})
