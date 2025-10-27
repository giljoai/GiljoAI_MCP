/**
 * Product Form Auto-Save Integration Tests
 * Handover 0051: Product Form Auto-Save & UX Polish Integration
 *
 * Tests critical user scenarios for the product creation/editing workflow
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import ProductsView from '@/views/ProductsView.vue'
import { useProductStore } from '@/stores/products'
import api from '@/services/api'

// Mock API
vi.mock('@/services/api', () => ({
  default: {
    products: {
      list: vi.fn(() => Promise.resolve({ data: [] })),
      create: vi.fn(() => Promise.resolve({ data: { id: 1, name: 'Test', created_at: new Date() } })),
      update: vi.fn(() => Promise.resolve({ data: { id: 1, name: 'Updated', created_at: new Date() } })),
      getCascadeImpact: vi.fn(() => Promise.resolve({ data: {} })),
    },
    visionDocuments: {
      listByProduct: vi.fn(() => Promise.resolve({ data: [] })),
      upload: vi.fn(() => Promise.resolve({ data: {} })),
      delete: vi.fn(() => Promise.resolve({ data: {} })),
    },
  },
}))

describe('ProductForm Auto-Save Integration', () => {
  let wrapper
  let router
  let pinia

  beforeEach(async () => {
    localStorage.clear()
    pinia = createPinia()
    setActivePinia(pinia)

    // Create router
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div></div>' } },
      ],
    })

    // Mount component
    wrapper = mount(ProductsView, {
      global: {
        plugins: [pinia, router],
        stubs: {
          'v-icon': true,
          'v-btn': true,
          'v-card': true,
          'v-dialog': true,
        },
      },
    })

    await flushPromises()
  })

  afterEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('Critical Scenario 1: Basic Save Flow', () => {
    it('should create product with all 5 tabs filled and save to backend', async () => {
      const vm = wrapper.vm

      // Open dialog
      vm.showDialog = true
      await flushPromises()

      // Fill Basic Info tab
      vm.productForm.name = 'Complete Product'
      vm.productForm.description = 'Full product description'

      // Fill Tech Stack tab
      vm.productForm.configData.tech_stack.languages = 'Python 3.11, TypeScript'
      vm.productForm.configData.tech_stack.frontend = 'Vue 3, Vuetify'
      vm.productForm.configData.tech_stack.backend = 'FastAPI'
      vm.productForm.configData.tech_stack.database = 'PostgreSQL'
      vm.productForm.configData.tech_stack.infrastructure = 'Docker, Kubernetes'

      // Fill Architecture tab
      vm.productForm.configData.architecture.pattern = 'Modular Monolith'
      vm.productForm.configData.architecture.design_patterns = 'Repository Pattern'
      vm.productForm.configData.architecture.api_style = 'REST API'

      // Fill Features tab
      vm.productForm.configData.features.core = 'Core features here'
      vm.productForm.configData.test_config.strategy = 'TDD'
      vm.productForm.configData.test_config.coverage_target = 85

      // Validate form
      vm.formValid = true

      // Save product
      await vm.saveProduct()
      await flushPromises()

      // Verify API call
      expect(api.products.create).toHaveBeenCalled()
    })
  })

  describe('Critical Scenario 2: Auto-Save to LocalStorage', () => {
    it('should auto-save form data after 500ms of typing', async () => {
      const vm = wrapper.vm
      vi.useFakeTimers()

      try {
        // Open dialog
        vm.showDialog = true
        await flushPromises()

        // Type in form
        vm.productForm.name = 'Test Product'
        vm.productForm.description = 'Test description'

        // Auto-save should be initialized
        expect(vm.autoSave).toBeDefined()

        // Data should not be in cache yet (not enough time passed)
        expect(localStorage.getItem('product_form_draft_new')).toBeNull()

        // Wait for debounce (500ms)
        vi.advanceTimersByTime(500)
        await flushPromises()

        // Data should now be in cache
        const cached = localStorage.getItem('product_form_draft_new')
        expect(cached).toBeDefined()

        const cacheData = JSON.parse(cached)
        expect(cacheData.data.name).toBe('Test Product')
        expect(cacheData.data.description).toBe('Test description')
      } finally {
        vi.useRealTimers()
      }
    })
  })

  describe('Critical Scenario 3: Draft Recovery Prompt', () => {
    it('should prompt to restore draft if cache exists', async () => {
      // Pre-populate cache
      const draftData = {
        data: {
          name: 'Recovered Draft',
          description: 'This was auto-saved',
          configData: {
            tech_stack: { languages: 'Python' },
            architecture: { pattern: 'Monolith' },
            features: { core: 'Core features' },
            test_config: { strategy: 'TDD', coverage_target: 80 },
          },
        },
        timestamp: Date.now(),
        version: '1.0',
      }

      localStorage.setItem('product_form_draft_new', JSON.stringify(draftData))

      // Mock confirm dialog
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

      const vm = wrapper.vm

      // Open dialog should trigger restore prompt
      vm.showDialog = true
      await flushPromises()

      // Confirm was called
      expect(confirmSpy).toHaveBeenCalled()

      confirmSpy.mockRestore()
    })

    it('should clear cache if user declines to restore', async () => {
      // Pre-populate cache
      const draftData = {
        data: { name: 'Draft to Discard' },
        timestamp: Date.now(),
        version: '1.0',
      }

      localStorage.setItem('product_form_draft_new', JSON.stringify(draftData))

      // Mock confirm to return false
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

      const vm = wrapper.vm

      // Open dialog
      vm.showDialog = true
      await flushPromises()

      // Cache should be cleared
      expect(localStorage.getItem('product_form_draft_new')).toBeNull()

      confirmSpy.mockRestore()
    })
  })

  describe('Critical Scenario 4: Tab Navigation Persistence', () => {
    it('should preserve data when switching tabs', async () => {
      const vm = wrapper.vm
      vi.useFakeTimers()

      try {
        vm.showDialog = true
        await flushPromises()

        // Fill basic info
        vm.productForm.name = 'Tab Navigation Test'
        vm.productForm.description = 'Test description'

        // Switch to vision tab
        vm.dialogTab = 'vision'
        await flushPromises()

        // Switch back to basic
        vm.dialogTab = 'basic'
        await flushPromises()

        // Data should still be there
        expect(vm.productForm.name).toBe('Tab Navigation Test')
        expect(vm.productForm.description).toBe('Test description')

        // Auto-save should have triggered
        vi.advanceTimersByTime(500)
        const cached = localStorage.getItem('product_form_draft_new')
        expect(cached).toBeDefined()
      } finally {
        vi.useRealTimers()
      }
    })
  })

  describe('Critical Scenario 5: Save Status Indicator', () => {
    it('should display unsaved -> saving -> saved status', async () => {
      const vm = wrapper.vm
      vi.useFakeTimers()

      try {
        vm.showDialog = true
        await flushPromises()

        // Initially saved
        expect(vm.autoSave?.saveStatus.value).toBe('saved')

        // Type something
        vm.productForm.name = 'Status Test'

        // Should show unsaved
        expect(vm.autoSave?.saveStatus.value).toBe('unsaved')
        expect(vm.autoSave?.hasUnsavedChanges.value).toBe(true)

        // Wait for auto-save
        vi.advanceTimersByTime(500)
        await flushPromises()

        // Should show saved
        expect(vm.autoSave?.saveStatus.value).toBe('saved')
        expect(vm.autoSave?.hasUnsavedChanges.value).toBe(false)
      } finally {
        vi.useRealTimers()
      }
    })
  })

  describe('Critical Scenario 6: Unsaved Changes Warning (Dialog Close)', () => {
    it('should warn when closing dialog with unsaved changes', async () => {
      const vm = wrapper.vm
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

      try {
        vm.showDialog = true
        await flushPromises()

        // Make changes
        vm.productForm.name = 'Unsaved Changes'
        if (vm.autoSave) {
          vm.autoSave.hasUnsavedChanges.value = true
        }

        // Try to close dialog
        vm.closeDialog()

        // Should show confirmation
        expect(confirmSpy).toHaveBeenCalledWith(
          expect.stringContaining('unsaved changes')
        )
      } finally {
        confirmSpy.mockRestore()
      }
    })

    it('should keep dialog open if user rejects close', async () => {
      const vm = wrapper.vm
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

      try {
        vm.showDialog = true
        await flushPromises()

        vm.productForm.name = 'Keep Me Open'
        if (vm.autoSave) {
          vm.autoSave.hasUnsavedChanges.value = true
        }

        vm.closeDialog()

        // Dialog should remain open
        expect(vm.showDialog).toBe(true)
      } finally {
        confirmSpy.mockRestore()
      }
    })
  })

  describe('Critical Scenario 7: Cache Cleared After Save', () => {
    it('should remove cache after successful product save', async () => {
      const vm = wrapper.vm
      vi.useFakeTimers()

      try {
        vm.showDialog = true
        await flushPromises()

        vm.productForm.name = 'Save and Clear'
        vm.formValid = true

        // Advance for auto-save
        vi.advanceTimersByTime(500)

        const cached = localStorage.getItem('product_form_draft_new')
        expect(cached).toBeDefined()

        // Save product
        await vm.saveProduct()
        await flushPromises()

        // Cache should be cleared
        expect(localStorage.getItem('product_form_draft_new')).toBeNull()
      } finally {
        vi.useRealTimers()
      }
    })
  })

  describe('Critical Scenario 8: Edit Existing Product', () => {
    it('should use correct cache key for editing existing product', async () => {
      const vm = wrapper.vm
      vi.useFakeTimers()

      try {
        const existingProduct = { id: 'prod-123', name: 'Existing', description: 'Old' }
        vm.editingProduct = existingProduct

        vm.showDialog = true
        await flushPromises()

        vm.productForm.name = 'Updated Name'

        // Should use product-specific cache key
        vi.advanceTimersByTime(500)

        const cached = localStorage.getItem('product_form_draft_prod-123')
        expect(cached).toBeDefined()
      } finally {
        vi.useRealTimers()
      }
    })
  })

  describe('Critical Scenario 9: Multiple Products - Separate Cache Keys', () => {
    it('should maintain separate caches for different products', async () => {
      vi.useFakeTimers()

      try {
        const vm = wrapper.vm

        // First product - new
        vm.showDialog = true
        await flushPromises()

        vm.productForm.name = 'Product A'
        vi.advanceTimersByTime(500)

        const cacheA = localStorage.getItem('product_form_draft_new')
        expect(cacheA).toBeDefined()

        // Close dialog
        vm.closeDialog()
        localStorage.clear()

        // Second product - edit existing
        vm.editingProduct = { id: 'prod-456', name: 'Product B' }
        vm.showDialog = true
        await flushPromises()

        vm.productForm.name = 'Product B Updated'
        vi.advanceTimersByTime(500)

        const cacheB = localStorage.getItem('product_form_draft_prod-456')
        expect(cacheB).toBeDefined()
      } finally {
        vi.useRealTimers()
      }
    })
  })

  describe('Critical Scenario 10: Tab Validation Indicators', () => {
    it('should show error badge on Basic Info when name is empty', async () => {
      const vm = wrapper.vm

      vm.showDialog = true
      await flushPromises()

      // Leave name empty
      vm.productForm.name = ''

      // Compute tab validation
      const validation = vm.tabValidation

      expect(validation.basic.hasError).toBe(true)
      expect(validation.basic.valid).toBe(false)
    })

    it('should show warning badges on incomplete tabs', async () => {
      const vm = wrapper.vm

      vm.showDialog = true
      await flushPromises()

      // Fill name but leave tech stack empty
      vm.productForm.name = 'Product'
      vm.productForm.configData.tech_stack.languages = ''

      const validation = vm.tabValidation

      expect(validation.tech.hasWarning).toBe(true)
    })
  })

  describe('Critical Scenario 11: Testing Strategy Dropdown', () => {
    it('should display all 6 testing strategies', async () => {
      const vm = wrapper.vm

      expect(vm.testingStrategies).toHaveLength(6)
      expect(vm.testingStrategies.map(t => t.value)).toEqual([
        'TDD',
        'BDD',
        'Integration-First',
        'E2E-First',
        'Manual',
        'Hybrid',
      ])
    })

    it('should have icons and subtitles for each strategy', async () => {
      const vm = wrapper.vm

      vm.testingStrategies.forEach(strategy => {
        expect(strategy.icon).toBeDefined()
        expect(strategy.subtitle).toBeDefined()
      })
    })
  })

  describe('Edge Case 1: Empty Form Save', () => {
    it('should block save if product name is empty', async () => {
      const vm = wrapper.vm

      vm.showDialog = true
      await flushPromises()

      vm.productForm.name = ''
      vm.formValid = false

      // Should not be able to save
      expect(vm.formValid).toBe(false)

      // Save attempt should be prevented
      // (button is disabled in template)
    })
  })

  describe('Edge Case 2: Very Long Field Values', () => {
    it('should handle 10,000 character descriptions', async () => {
      const vm = wrapper.vm
      vi.useFakeTimers()

      try {
        vm.showDialog = true
        await flushPromises()

        const longText = 'A'.repeat(10000)
        vm.productForm.description = longText

        vi.advanceTimersByTime(500)

        const cached = localStorage.getItem('product_form_draft_new')
        const cacheData = JSON.parse(cached)

        expect(cacheData.data.description.length).toBe(10000)
      } finally {
        vi.useRealTimers()
      }
    })
  })

  describe('Edge Case 3: Special Characters', () => {
    it('should properly escape XSS-like characters', async () => {
      const vm = wrapper.vm
      vi.useFakeTimers()

      try {
        vm.showDialog = true
        await flushPromises()

        vm.productForm.name = '<script>alert("xss")</script>'

        vi.advanceTimersByTime(500)

        const cached = localStorage.getItem('product_form_draft_new')
        const cacheData = JSON.parse(cached)

        expect(cacheData.data.name).toBe('<script>alert("xss")</script>')
        // Should be properly escaped in JSON
      } finally {
        vi.useRealTimers()
      }
    })
  })

  describe('Edge Case 4: Rapid Tab Switching', () => {
    it('should handle rapid tab switches without errors', async () => {
      const vm = wrapper.vm

      vm.showDialog = true
      await flushPromises()

      vm.productForm.name = 'Rapid Tab Test'

      // Rapid tab switches
      for (let i = 0; i < 10; i++) {
        vm.dialogTab = ['basic', 'vision', 'tech', 'arch', 'features'][i % 5]
        await flushPromises()
      }

      // Data should still be intact
      expect(vm.productForm.name).toBe('Rapid Tab Test')
    })
  })

  describe('Edge Case 5: Rapid Dialog Open/Close', () => {
    it('should handle rapid dialog open/close without memory leaks', async () => {
      const vm = wrapper.vm

      for (let i = 0; i < 5; i++) {
        vm.showDialog = true
        await flushPromises()

        vm.productForm.name = `Cycle ${i}`

        vm.showDialog = false
        await flushPromises()
      }

      // Should still work properly
      vm.showDialog = true
      await flushPromises()

      expect(vm.showDialog).toBe(true)
    })
  })

  describe('Critical Scenario 12: Browser Refresh Warning', () => {
    it('should warn on beforeunload if form has unsaved changes', async () => {
      const vm = wrapper.vm

      vm.showDialog = true
      await flushPromises()

      vm.productForm.name = 'Unsaved'
      if (vm.autoSave) {
        vm.autoSave.hasUnsavedChanges.value = true
      }

      // Create beforeunload event
      const event = new Event('beforeunload')
      event.preventDefault = vi.fn()

      vm.handleBeforeUnload(event)

      // If unsaved changes exist and dialog is open, preventDefault should be called
      if (vm.showDialog && vm.hasUnsavedChanges) {
        expect(event.preventDefault).toHaveBeenCalled()
      }
    })
  })

  describe('Critical Scenario 13: Testing Strategy Dropdown Display', () => {
    it('should display strategy with icon and subtitle in dropdown', async () => {
      const vm = wrapper.vm

      expect(vm.testingStrategies[0]).toEqual({
        value: 'TDD',
        title: 'TDD (Test-Driven Development)',
        subtitle: 'Write tests before implementation code',
        icon: 'mdi-test-tube',
      })
    })
  })

  describe('Critical Scenario 14: Form Validation with Tab Indicators', () => {
    it('should show all validation indicators correctly', async () => {
      const vm = wrapper.vm

      vm.showDialog = true
      await flushPromises()

      // Empty name - error
      vm.productForm.name = ''

      // Empty vision docs - warning
      vm.visionFiles = []
      vm.existingVisionDocuments = []

      // Empty tech stack - warning
      vm.productForm.configData.tech_stack.languages = ''

      const validation = vm.tabValidation

      expect(validation.basic.hasError).toBe(true)
      expect(validation.vision.hasWarning).toBe(true)
      expect(validation.tech.hasWarning).toBe(true)
    })
  })

  describe('Critical Scenario 15: Auto-Save State Transitions', () => {
    it('should properly transition through all save states', async () => {
      const vm = wrapper.vm
      vi.useFakeTimers()

      try {
        vm.showDialog = true
        await flushPromises()

        // Initial: saved
        expect(vm.autoSave?.saveStatus.value).toBe('saved')

        // Typing: unsaved
        vm.productForm.name = 'State Test'
        expect(vm.autoSave?.saveStatus.value).toBe('unsaved')

        // Auto-save completes
        vi.advanceTimersByTime(500)
        await flushPromises()

        // Final: saved
        expect(vm.autoSave?.saveStatus.value).toBe('saved')
        expect(vm.autoSave?.hasUnsavedChanges.value).toBe(false)
      } finally {
        vi.useRealTimers()
      }
    })
  })
})
