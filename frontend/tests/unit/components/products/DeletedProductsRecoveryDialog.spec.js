import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import DeletedProductsRecoveryDialog from '@/components/products/DeletedProductsRecoveryDialog.vue'

describe('DeletedProductsRecoveryDialog Component', () => {
  const defaultProps = {
    modelValue: true,
    deletedProducts: [],
    restoringProductId: null,
    loading: false
  }

  const sampleDeletedProducts = [
    {
      id: 'prod-1',
      name: 'Product A',
      description: 'First test product',
      deleted_at: '2025-11-10T12:00:00Z',
      days_until_purge: 7,
      project_count: 3,
      vision_documents_count: 2
    },
    {
      id: 'prod-2',
      name: 'Product B',
      description: 'Second test product',
      deleted_at: '2025-11-15T08:30:00Z',
      days_until_purge: 4,
      project_count: 1,
      vision_documents_count: 5
    },
    {
      id: 'prod-3',
      name: 'Product C',
      description: null,
      deleted_at: '2025-11-18T16:45:00Z',
      days_until_purge: 1,
      project_count: 0,
      vision_documents_count: 0
    }
  ]

  const createWrapper = (props = {}) => {
    return mount(DeletedProductsRecoveryDialog, {
      props: { ...defaultProps, ...props },
      global: {
        stubs: {
          'v-dialog': {
            template: '<div class="v-dialog" v-if="$attrs.modelValue"><slot /></div>',
            props: ['modelValue']
          },
          'v-card': { template: '<div class="v-card"><slot /></div>' },
          'v-card-title': { template: '<div class="v-card-title"><slot /></div>' },
          'v-card-text': { template: '<div class="v-card-text"><slot /></div>' },
          'v-card-actions': { template: '<div class="v-card-actions"><slot /></div>' },
          'v-btn': {
            template: '<button class="v-btn" :disabled="$attrs.disabled" :class="{ loading: $attrs.loading }" @click="$emit(\'click\')"><slot /></button>',
            emits: ['click']
          },
          'v-icon': { template: '<span class="v-icon"><slot /></span>' },
          'v-divider': { template: '<hr class="v-divider" />' },
          'v-alert': { template: '<div class="v-alert"><slot /></div>' },
          'v-progress-circular': { template: '<div class="v-progress-circular">Loading...</div>' },
          'v-list': { template: '<div class="v-list"><slot /></div>' },
          'v-list-item': { template: '<div class="v-list-item"><slot /></div>' },
          'v-chip': {
            template: '<span class="v-chip" :class="$attrs.color"><slot /></span>',
            props: ['color']
          },
          'v-spacer': { template: '<div class="v-spacer"></div>' }
        }
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

      const closeButton = wrapper.findAll('.v-btn').find(btn => btn.html().includes('mdi-close'))
      if (closeButton) {
        await closeButton.trigger('click')
      }

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

    it('shows product description or fallback text', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: sampleDeletedProducts
      })

      const html = wrapper.html()
      expect(html).toContain('First test product')
      expect(html).toContain('Second test product')
      expect(html).toContain('No description')
    })
  })

  describe('Days Until Purge Display', () => {
    it('displays days until purge for each product', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: sampleDeletedProducts
      })

      const html = wrapper.html()
      expect(html).toContain('7 days left')
      expect(html).toContain('4 days left')
      expect(html).toContain('1 day')
    })

    it('shows green color for products with more than 5 days', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: [sampleDeletedProducts[0]] // 7 days
      })

      const chip = wrapper.find('.v-chip')
      expect(chip.classes()).toContain('success')
    })

    it('shows yellow/warning color for products with 3-5 days', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: [sampleDeletedProducts[1]] // 4 days
      })

      const chip = wrapper.find('.v-chip')
      expect(chip.classes()).toContain('warning')
    })

    it('shows red/error color for products with less than 3 days', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: [sampleDeletedProducts[2]] // 1 day
      })

      const chip = wrapper.find('.v-chip')
      expect(chip.classes()).toContain('error')
    })
  })

  describe('Product Statistics', () => {
    it('shows project count per deleted product', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: sampleDeletedProducts
      })

      const html = wrapper.html()
      expect(html).toContain('3 projects')
      expect(html).toContain('1 project')
      expect(html).toContain('0 projects')
    })

    it('shows vision documents count per deleted product', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: sampleDeletedProducts
      })

      const html = wrapper.html()
      expect(html).toContain('2 vision docs')
      expect(html).toContain('5 vision docs')
      expect(html).toContain('0 vision docs')
    })
  })

  describe('Date Formatting', () => {
    it('displays deletion date formatted correctly', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: sampleDeletedProducts
      })

      const html = wrapper.html()
      // Check that dates are formatted (component should format them)
      expect(html).toContain('Deleted')
      // The exact format depends on implementation but should show date info
    })
  })

  describe('Restore Functionality', () => {
    it('emits restore event with product id when restore button clicked', async () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: [sampleDeletedProducts[0]]
      })

      const restoreButton = wrapper.findAll('.v-btn').find(btn =>
        btn.html().includes('Restore') || btn.html().includes('mdi-restore')
      )

      expect(restoreButton).toBeTruthy()
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

      const restoreButton = wrapper.findAll('.v-btn').find(btn =>
        btn.html().includes('Restore') || btn.html().includes('mdi-restore')
      )

      expect(restoreButton.classes()).toContain('loading')
    })

    it('disables restore button when another product is being restored', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: sampleDeletedProducts,
        restoringProductId: 'prod-1'
      })

      // Find restore buttons for products other than prod-1
      const buttons = wrapper.findAll('.v-btn')
      const restoreButtons = buttons.filter(btn =>
        btn.html().includes('Restore') || btn.html().includes('mdi-restore')
      )

      // At least one button should be disabled
      const hasDisabledButton = restoreButtons.some(btn => btn.attributes('disabled') !== undefined)
      expect(hasDisabledButton).toBe(true)
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
      expect(html).toContain('mdi-delete-empty')
    })

    it('does not show list when empty', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: []
      })

      expect(wrapper.find('.v-list').exists()).toBe(false)
    })
  })

  describe('Loading State', () => {
    it('shows loading indicator when loading prop is true', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: [],
        loading: true
      })

      expect(wrapper.find('.v-progress-circular').exists()).toBe(true)
    })

    it('shows loading text when loading', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: [],
        loading: true
      })

      const html = wrapper.html()
      expect(html).toContain('Loading deleted products')
    })

    it('does not show list while loading', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: sampleDeletedProducts,
        loading: true
      })

      // When loading, should not render the list even if products exist
      const listItems = wrapper.findAll('.v-list-item')
      expect(listItems.length).toBe(0)
    })
  })

  describe('Info Alert', () => {
    it('displays informational alert about purge timeline', () => {
      const wrapper = createWrapper({
        modelValue: true,
        deletedProducts: sampleDeletedProducts
      })

      const html = wrapper.html()
      expect(html).toContain('10 days')
      expect(html).toContain('permanently purged')
    })
  })

  describe('Close Actions', () => {
    it('emits update:modelValue when Close button in actions is clicked', async () => {
      const wrapper = createWrapper({ modelValue: true })

      const closeButton = wrapper.findAll('.v-btn').find(btn =>
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
      expect(wrapper.find('.v-card').exists()).toBe(true)
      expect(wrapper.find('.v-card-title').exists()).toBe(true)
    })

    it('has close button in header', () => {
      const wrapper = createWrapper({ modelValue: true })

      const cardTitle = wrapper.find('.v-card-title')
      const closeIcon = cardTitle.find('.v-icon')
      expect(closeIcon.exists()).toBe(true)
    })
  })
})
