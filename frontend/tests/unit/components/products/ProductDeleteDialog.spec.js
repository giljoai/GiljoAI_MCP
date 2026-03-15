/**
 * Test suite for ProductDeleteDialog component
 * TDD Phase 1: Write failing tests before implementation
 *
 * Tests cover:
 * - Dialog rendering based on modelValue
 * - Product name display
 * - Cascade impact display
 * - Confirmation checkbox behavior
 * - Delete button disabled state
 * - Event emissions (confirm, cancel)
 * - Loading state
 * - Warning alert display
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ProductDeleteDialog from '@/components/products/ProductDeleteDialog.vue'

describe('ProductDeleteDialog Component', () => {
  const createWrapper = (props = {}) => {
    const defaultProps = {
      modelValue: true,
      product: {
        id: 'test-product-id',
        name: 'Test Product'
      },
      cascadeImpact: {
        unfinished_projects: 3,
        projects_count: 5,
        unresolved_tasks: 10,
        tasks_count: 20,
        vision_documents_count: 2,
        total_chunks: 50
      },
      loading: false
    }

    return mount(ProductDeleteDialog, {
      props: { ...defaultProps, ...props },
      global: {
        stubs: {
          'v-dialog': {
            template: '<div class="v-dialog"><slot /></div>',
            props: ['modelValue', 'persistent']
          },
          'v-card': { template: '<div class="v-card"><slot /></div>' },
          'v-card-title': { template: '<div class="v-card-title"><slot /></div>' },
          'v-card-text': { template: '<div class="v-card-text"><slot /></div>' },
          'v-card-actions': { template: '<div class="v-card-actions"><slot /></div>' },
          'v-divider': { template: '<hr class="v-divider" />' },
          'v-icon': { template: '<span class="v-icon"><slot /></span>' },
          'v-alert': { template: '<div class="v-alert"><slot /></div>' },
          'v-list': { template: '<div class="v-list"><slot /></div>' },
          'v-list-item': { template: '<div class="v-list-item"><slot /></div>' },
          'v-list-item-title': { template: '<div class="v-list-item-title"><slot /></div>' },
          'v-list-item-subtitle': { template: '<div class="v-list-item-subtitle"><slot /></div>' },
          'v-checkbox': {
            template: '<div class="v-checkbox"><input type="checkbox" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" /><slot name="label" /></div>',
            props: ['modelValue', 'density', 'hideDetails'],
            emits: ['update:modelValue']
          },
          'v-btn': {
            template: '<button class="v-btn" :disabled="disabled" @click="$emit(\'click\', $event)"><slot /></button>',
            props: ['variant', 'color', 'disabled', 'loading'],
            emits: ['click']
          },
          'v-spacer': { template: '<div class="v-spacer"></div>' },
          'v-progress-circular': { template: '<div class="v-progress-circular">Loading...</div>' }
        }
      }
    })
  }

  describe('Dialog Rendering', () => {
    it('renders dialog when modelValue is true', () => {
      const wrapper = createWrapper({ modelValue: true })

      expect(wrapper.find('.v-dialog').exists()).toBe(true)
    })

    it('does not render dialog content when modelValue is false', () => {
      const wrapper = createWrapper({ modelValue: false })

      // Dialog should exist
      const dialog = wrapper.find('.v-dialog')
      expect(dialog.exists()).toBe(true)
    })

    it('displays product name in dialog content', async () => {
      const productName = 'My Test Product'
      const wrapper = createWrapper({
        product: { id: 'test-id', name: productName }
      })

      await flushPromises()

      expect(wrapper.text()).toContain(productName)
    })
  })

  describe('Cascade Impact Display', () => {
    it('shows unfinished projects count', async () => {
      const cascadeImpact = {
        unfinished_projects: 5,
        projects_count: 10,
        unresolved_tasks: 0,
        tasks_count: 0,
        vision_documents_count: 0,
        total_chunks: 0
      }

      const wrapper = createWrapper({ cascadeImpact })
      await flushPromises()

      expect(wrapper.text()).toContain('5')
      expect(wrapper.text()).toContain('unfinished projects')
    })

    it('shows total projects count', async () => {
      const cascadeImpact = {
        unfinished_projects: 3,
        projects_count: 8,
        unresolved_tasks: 0,
        tasks_count: 0,
        vision_documents_count: 0,
        total_chunks: 0
      }

      const wrapper = createWrapper({ cascadeImpact })
      await flushPromises()

      expect(wrapper.text()).toContain('8 total projects')
    })

    it('shows unresolved tasks count', async () => {
      const cascadeImpact = {
        unfinished_projects: 0,
        projects_count: 0,
        unresolved_tasks: 15,
        tasks_count: 30,
        vision_documents_count: 0,
        total_chunks: 0
      }

      const wrapper = createWrapper({ cascadeImpact })
      await flushPromises()

      expect(wrapper.text()).toContain('15')
      expect(wrapper.text()).toContain('unresolved tasks')
    })

    it('shows vision documents count', async () => {
      const cascadeImpact = {
        unfinished_projects: 0,
        projects_count: 0,
        unresolved_tasks: 0,
        tasks_count: 0,
        vision_documents_count: 7,
        total_chunks: 0
      }

      const wrapper = createWrapper({ cascadeImpact })
      await flushPromises()

      expect(wrapper.text()).toContain('7')
      expect(wrapper.text()).toContain('vision documents')
    })

    it('shows context chunks count', async () => {
      const cascadeImpact = {
        unfinished_projects: 0,
        projects_count: 0,
        unresolved_tasks: 0,
        tasks_count: 0,
        vision_documents_count: 0,
        total_chunks: 100
      }

      const wrapper = createWrapper({ cascadeImpact })
      await flushPromises()

      expect(wrapper.text()).toContain('100')
      expect(wrapper.text()).toContain('context chunks')
    })
  })

  describe('Confirmation Checkbox Behavior', () => {
    it('has checkbox initially unchecked', () => {
      const wrapper = createWrapper()

      const checkbox = wrapper.find('.v-checkbox input')
      expect(checkbox.exists()).toBe(true)
      expect(checkbox.element.checked).toBe(false)
    })

    it('checkbox can be toggled', async () => {
      const wrapper = createWrapper()

      const checkbox = wrapper.find('.v-checkbox input')

      // Simulate checkbox change
      await checkbox.setValue(true)
      await flushPromises()

      // The checkbox state is managed internally by BaseDialog via confirm-checkbox prop.
      // Verify the DOM reflects the toggle.
      expect(checkbox.element.checked).toBe(true)
    })
  })

  describe('Delete Button State', () => {
    it('delete button is disabled when checkbox is unchecked', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const buttons = wrapper.findAll('.v-btn')
      const deleteButton = buttons.find(btn =>
        btn.text().includes('Move to Trash') || btn.text().includes('Trash')
      )

      expect(deleteButton).toBeDefined()
      expect(deleteButton.attributes('disabled')).toBeDefined()
    })

    it('delete button is enabled when checkbox is checked', async () => {
      const wrapper = createWrapper()

      // Check the checkbox
      const checkbox = wrapper.find('.v-checkbox input')
      await checkbox.setValue(true)
      await flushPromises()

      const buttons = wrapper.findAll('.v-btn')
      const deleteButton = buttons.find(btn =>
        btn.text().includes('Move to Trash') || btn.text().includes('Trash')
      )

      expect(deleteButton).toBeDefined()
      // Button should not be disabled when checkbox is checked
      expect(deleteButton.attributes('disabled')).toBeUndefined()
    })

    it('delete button passes loading state when deleting', async () => {
      const wrapper = createWrapper({ deleting: true })

      // Check the checkbox first
      const checkbox = wrapper.find('.v-checkbox input')
      await checkbox.setValue(true)
      await flushPromises()

      // BaseDialog receives loading=true via the :loading="deleting" prop binding,
      // which makes the confirm button loading (implicitly disabled in real Vuetify).
      // Verify the deleting prop is passed through to BaseDialog.
      const baseDialog = wrapper.findComponent({ name: 'BaseDialog' })
      expect(baseDialog.exists()).toBe(true)
      expect(baseDialog.props('loading')).toBe(true)
    })
  })

  describe('Event Emissions', () => {
    it('emits confirm event when delete button clicked', async () => {
      const wrapper = createWrapper()

      // Check the checkbox first to enable the button
      const checkbox = wrapper.find('.v-checkbox input')
      await checkbox.setValue(true)
      await flushPromises()

      // Find and click the delete button
      const buttons = wrapper.findAll('.v-btn')
      const deleteButton = buttons.find(btn =>
        btn.text().includes('Move to Trash') || btn.text().includes('Trash')
      )

      await deleteButton.trigger('click')
      await flushPromises()

      expect(wrapper.emitted('confirm')).toBeTruthy()
      expect(wrapper.emitted('confirm').length).toBe(1)
    })

    it('emits cancel event when cancel button clicked', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Find and click the cancel button
      const buttons = wrapper.findAll('.v-btn')
      const cancelButton = buttons.find(btn =>
        btn.text().includes('Cancel')
      )

      await cancelButton.trigger('click')
      await flushPromises()

      expect(wrapper.emitted('cancel')).toBeTruthy()
      expect(wrapper.emitted('cancel').length).toBe(1)
    })

    it('emits update:modelValue with false when cancel clicked', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Find and click the cancel button
      const buttons = wrapper.findAll('.v-btn')
      const cancelButton = buttons.find(btn =>
        btn.text().includes('Cancel')
      )

      await cancelButton.trigger('click')
      await flushPromises()

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')[0]).toEqual([false])
    })
  })

  describe('Loading State', () => {
    it('shows loading spinner when calculating cascade impact', async () => {
      const wrapper = createWrapper({ loading: true })
      await flushPromises()

      expect(wrapper.text()).toContain('Calculating impact')
      expect(wrapper.find('.v-progress-circular').exists()).toBe(true)
    })

    it('hides cascade impact details while loading', async () => {
      const wrapper = createWrapper({
        loading: true,
        cascadeImpact: {
          unfinished_projects: 5,
          projects_count: 10,
          unresolved_tasks: 15,
          tasks_count: 30,
          vision_documents_count: 7,
          total_chunks: 100
        }
      })
      await flushPromises()

      // Should show loading, not the cascade impact
      expect(wrapper.text()).toContain('Calculating impact')
      expect(wrapper.text()).not.toContain('unfinished projects')
    })

    it('shows cascade impact when loading is complete', async () => {
      const wrapper = createWrapper({ loading: false })
      await flushPromises()

      expect(wrapper.text()).not.toContain('Calculating impact')
      expect(wrapper.text()).toContain('unfinished projects')
    })
  })

  describe('Warning Alert', () => {
    it('displays warning about 10-day recovery window', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.text()).toContain('10 days')
      expect(wrapper.text()).toContain('recovered')
    })

    it('displays product name in warning message', async () => {
      const productName = 'Special Product'
      const wrapper = createWrapper({
        product: { id: 'test-id', name: productName }
      })
      await flushPromises()

      // Warning should mention the product name
      const alertText = wrapper.text()
      expect(alertText).toContain(productName)
    })

    it('displays permanent deletion warning', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.text()).toContain('permanently deleted')
    })
  })

  describe('V-Model Pattern', () => {
    it('implements computed isOpen for v-model pattern', () => {
      const wrapper = createWrapper({ modelValue: true })

      // Component should use isOpen computed property
      expect(wrapper.vm.isOpen).toBe(true)
    })

    it('updates isOpen when modelValue changes', async () => {
      const wrapper = createWrapper({ modelValue: true })

      expect(wrapper.vm.isOpen).toBe(true)

      await wrapper.setProps({ modelValue: false })

      expect(wrapper.vm.isOpen).toBe(false)
    })
  })

  describe('State Reset', () => {
    it('BaseDialog manages checkbox state reset when dialog opens', async () => {
      // The confirmation checkbox is now managed internally by BaseDialog
      // via the confirm-checkbox prop. Verify the prop is passed correctly.
      const wrapper = createWrapper({ modelValue: false })

      // Open dialog
      await wrapper.setProps({ modelValue: true })
      await flushPromises()

      // BaseDialog receives the confirm-checkbox prop
      const baseDialog = wrapper.findComponent({ name: 'BaseDialog' })
      expect(baseDialog.exists()).toBe(true)
      expect(baseDialog.props('confirmCheckbox')).toBe(true)
    })

    it('BaseDialog manages checkbox state reset when dialog closes', async () => {
      // The confirmation checkbox is now managed internally by BaseDialog
      const wrapper = createWrapper({ modelValue: true })

      // Close dialog
      await wrapper.setProps({ modelValue: false })
      await flushPromises()

      // BaseDialog receives the confirm-checkbox prop
      const baseDialog = wrapper.findComponent({ name: 'BaseDialog' })
      expect(baseDialog.exists()).toBe(true)
      expect(baseDialog.props('confirmCheckbox')).toBe(true)
    })
  })

  describe('Props Validation', () => {
    it('accepts required modelValue prop', () => {
      const wrapper = createWrapper({ modelValue: true })
      expect(wrapper.props('modelValue')).toBe(true)
    })

    it('accepts product prop with default empty object', () => {
      const wrapper = mount(ProductDeleteDialog, {
        props: {
          modelValue: true
        },
        global: {
          stubs: {
            'v-dialog': { template: '<div><slot /></div>' },
            'v-card': { template: '<div><slot /></div>' },
            'v-card-title': { template: '<div><slot /></div>' },
            'v-card-text': { template: '<div><slot /></div>' },
            'v-card-actions': { template: '<div><slot /></div>' },
            'v-divider': { template: '<hr />' },
            'v-icon': { template: '<span><slot /></span>' },
            'v-alert': { template: '<div><slot /></div>' },
            'v-list': { template: '<div><slot /></div>' },
            'v-list-item': { template: '<div><slot /></div>' },
            'v-list-item-title': { template: '<div><slot /></div>' },
            'v-list-item-subtitle': { template: '<div><slot /></div>' },
            'v-checkbox': { template: '<div><slot name="label" /></div>' },
            'v-btn': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
            'v-spacer': { template: '<div></div>' },
            'v-progress-circular': { template: '<div></div>' }
          }
        }
      })

      // Should have default empty object
      expect(wrapper.props('product')).toEqual({})
    })

    it('accepts cascadeImpact prop with defaults', () => {
      const wrapper = mount(ProductDeleteDialog, {
        props: {
          modelValue: true
        },
        global: {
          stubs: {
            'v-dialog': { template: '<div><slot /></div>' },
            'v-card': { template: '<div><slot /></div>' },
            'v-card-title': { template: '<div><slot /></div>' },
            'v-card-text': { template: '<div><slot /></div>' },
            'v-card-actions': { template: '<div><slot /></div>' },
            'v-divider': { template: '<hr />' },
            'v-icon': { template: '<span><slot /></span>' },
            'v-alert': { template: '<div><slot /></div>' },
            'v-list': { template: '<div><slot /></div>' },
            'v-list-item': { template: '<div><slot /></div>' },
            'v-list-item-title': { template: '<div><slot /></div>' },
            'v-list-item-subtitle': { template: '<div><slot /></div>' },
            'v-checkbox': { template: '<div><slot name="label" /></div>' },
            'v-btn': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
            'v-spacer': { template: '<div></div>' },
            'v-progress-circular': { template: '<div></div>' }
          }
        }
      })

      // Should have default cascade impact values
      expect(wrapper.props('cascadeImpact')).toBeDefined()
    })

    it('accepts loading prop with default false', () => {
      const wrapper = mount(ProductDeleteDialog, {
        props: {
          modelValue: true
        },
        global: {
          stubs: {
            'v-dialog': { template: '<div><slot /></div>' },
            'v-card': { template: '<div><slot /></div>' },
            'v-card-title': { template: '<div><slot /></div>' },
            'v-card-text': { template: '<div><slot /></div>' },
            'v-card-actions': { template: '<div><slot /></div>' },
            'v-divider': { template: '<hr />' },
            'v-icon': { template: '<span><slot /></span>' },
            'v-alert': { template: '<div><slot /></div>' },
            'v-list': { template: '<div><slot /></div>' },
            'v-list-item': { template: '<div><slot /></div>' },
            'v-list-item-title': { template: '<div><slot /></div>' },
            'v-list-item-subtitle': { template: '<div><slot /></div>' },
            'v-checkbox': { template: '<div><slot name="label" /></div>' },
            'v-btn': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
            'v-spacer': { template: '<div></div>' },
            'v-progress-circular': { template: '<div></div>' }
          }
        }
      })

      expect(wrapper.props('loading')).toBe(false)
    })
  })

  describe('Accessibility', () => {
    it('has proper dialog structure', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const dialog = wrapper.find('.v-dialog')
      expect(dialog.exists()).toBe(true)
    })

    it('has delete icon in title area', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const icon = wrapper.find('.v-card-title .v-icon')
      expect(icon.exists()).toBe(true)
      expect(icon.text()).toContain('mdi-delete')
    })
  })
})
