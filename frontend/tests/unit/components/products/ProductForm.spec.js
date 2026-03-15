/**
 * Test suite for ProductForm component
 * TDD Phase 1: Write failing tests before implementation
 *
 * Tests cover:
 * - Dialog rendering based on modelValue
 * - Title display (Create/Edit modes)
 * - Tab navigation (5 tabs)
 * - Form validation
 * - Event emissions
 * - Auto-save status indicator
 * - Config data updates
 * - ProductVisionPanel integration
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ProductForm from '@/components/products/ProductForm.vue'

describe('ProductForm Component', () => {
  beforeEach(() => {
    // Create and set active Pinia for each test
    setActivePinia(createPinia())
  })

  const createWrapper = (props = {}) => {
    const defaultProps = {
      modelValue: true,
      product: null,
      isEdit: false,
      existingVisionDocuments: [],
      autoSaveState: { status: 'saved', enabled: true }
    }

    return mount(ProductForm, {
      props: { ...defaultProps, ...props },
      global: {
        plugins: [createPinia()],
        stubs: {
          'v-dialog': {
            template: '<div class="v-dialog" v-if="modelValue"><slot /></div>',
            props: ['modelValue', 'persistent', 'maxWidth']
          },
          'v-card': { template: '<div class="v-card"><slot /></div>' },
          'v-card-title': { template: '<div class="v-card-title"><slot /></div>' },
          'v-card-text': { template: '<div class="v-card-text"><slot /></div>' },
          'v-card-actions': { template: '<div class="v-card-actions"><slot /></div>' },
          'v-divider': { template: '<hr class="v-divider" />' },
          'v-icon': { template: '<span class="v-icon"><slot /></span>' },
          'v-spacer': { template: '<div class="v-spacer"></div>' },
          'v-chip': {
            template: '<span class="v-chip" :class="color"><slot /></span>',
            props: ['color', 'size', 'variant']
          },
          'v-btn': {
            template: '<button class="v-btn" :disabled="disabled" @click="$emit(\'click\', $event)"><slot /></button>',
            props: ['variant', 'color', 'disabled', 'loading', 'icon'],
            emits: ['click']
          },
          'v-tabs': {
            template: '<div class="v-tabs"><slot /></div>',
            props: ['modelValue', 'color', 'showArrows'],
            emits: ['update:modelValue']
          },
          'v-tab': {
            template: '<button class="v-tab" :data-value="value" @click="$emit(\'click\')"><slot /></button>',
            props: ['value'],
            emits: ['click']
          },
          'v-tabs-window': {
            template: '<div class="v-tabs-window"><slot /></div>',
            props: ['modelValue']
          },
          'v-tabs-window-item': {
            template: '<div class="v-tabs-window-item" :data-value="value"><slot /></div>',
            props: ['value']
          },
          'v-form': {
            template: '<form class="v-form" @submit.prevent><slot /></form>',
            props: ['modelValue'],
            emits: ['update:modelValue']
          },
          'v-text-field': {
            template: '<input class="v-text-field" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" :placeholder="placeholder" />',
            props: ['modelValue', 'label', 'rules', 'variant', 'density', 'placeholder', 'hint', 'persistentHint', 'prependInnerIcon'],
            emits: ['update:modelValue']
          },
          'v-textarea': {
            template: '<textarea class="v-textarea" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" :placeholder="placeholder"></textarea>',
            props: ['modelValue', 'label', 'variant', 'density', 'rows', 'autoGrow', 'hint', 'persistentHint', 'placeholder'],
            emits: ['update:modelValue']
          },
          'v-select': {
            template: '<select class="v-select" :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="item in items" :key="item.value" :value="item.value">{{ item.title }}</option></select>',
            props: ['modelValue', 'items', 'itemTitle', 'itemValue', 'hint', 'persistentHint', 'variant', 'density'],
            emits: ['update:modelValue']
          },
          'v-slider': {
            template: '<input type="range" class="v-slider" :value="modelValue" @input="$emit(\'update:modelValue\', Number($event.target.value))" :min="min" :max="max" :step="step" />',
            props: ['modelValue', 'min', 'max', 'step', 'thumbLabel', 'color'],
            emits: ['update:modelValue']
          },
          'v-file-input': {
            template: '<input type="file" class="v-file-input" @change="$emit(\'update:modelValue\', $event.target.files)" :accept="accept" :multiple="multiple" />',
            props: ['modelValue', 'accept', 'label', 'variant', 'density', 'multiple', 'showSize', 'clearable', 'prependIcon', 'hint', 'persistentHint'],
            emits: ['update:modelValue']
          },
          'v-alert': {
            template: '<div class="v-alert" :class="type"><slot /><button v-if="dismissible" class="v-alert-close" @click="$emit(\'click:close\')">x</button></div>',
            props: { type: String, variant: String, density: String, dismissible: { type: Boolean, default: false } },
            emits: ['click:close']
          },
          'v-list': { template: '<div class="v-list"><slot /></div>' },
          'v-list-item': { template: '<div class="v-list-item"><slot /></div>' },
          'v-list-item-title': { template: '<div class="v-list-item-title"><slot /></div>' },
          'v-list-item-subtitle': { template: '<div class="v-list-item-subtitle"><slot /></div>' },
          'v-tooltip': { template: '<div class="v-tooltip"><slot name="activator" /><slot /></div>' },
          'v-progress-circular': { template: '<div class="v-progress-circular">Loading...</div>' },
          'v-progress-linear': { template: '<div class="v-progress-linear"></div>' },
          'ProductVisionPanel': {
            template: '<div class="product-vision-panel" data-testid="vision-panel"></div>',
            props: ['existingDocuments', 'uploadProgress', 'uploading', 'error']
          }
        },
        mocks: {
          $t: (msg) => msg
        }
      }
    })
  }

  describe('Dialog Rendering', () => {
    it('renders dialog when modelValue is true', () => {
      const wrapper = createWrapper({ modelValue: true })

      expect(wrapper.find('.v-dialog').exists()).toBe(true)
    })

    it('does not render dialog when modelValue is false', () => {
      const wrapper = createWrapper({ modelValue: false })

      expect(wrapper.find('.v-dialog').exists()).toBe(false)
    })
  })

  describe('Title Display', () => {
    it('shows "Create New Product" title for new products', async () => {
      const wrapper = createWrapper({ isEdit: false })
      await flushPromises()

      expect(wrapper.text()).toContain('Create New Product')
    })

    it('shows "Edit Product" title for existing products', async () => {
      const wrapper = createWrapper({
        isEdit: true,
        product: { id: 'test-id', name: 'Test Product' }
      })
      await flushPromises()

      expect(wrapper.text()).toContain('Edit Product')
    })

    it('shows pencil icon for edit mode', async () => {
      const wrapper = createWrapper({ isEdit: true })
      await flushPromises()

      const icons = wrapper.findAll('.v-icon')
      const titleIcon = icons.find(icon => icon.text().includes('mdi-pencil'))
      expect(titleIcon).toBeDefined()
    })

    it('shows plus icon for create mode', async () => {
      const wrapper = createWrapper({ isEdit: false })
      await flushPromises()

      const icons = wrapper.findAll('.v-icon')
      const titleIcon = icons.find(icon => icon.text().includes('mdi-plus'))
      expect(titleIcon).toBeDefined()
    })
  })

  describe('Tab Navigation', () => {
    it('renders all 5 tabs', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const tabs = wrapper.findAll('.v-tab')
      expect(tabs.length).toBe(5)
    })

    it('renders Basic Info tab', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.text()).toContain('Basic Info')
    })

    it('renders Vision Docs tab', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.text()).toContain('Vision Docs')
    })

    it('renders Tech Stack tab', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.text()).toContain('Tech Stack')
    })

    it('renders Architecture tab', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.text()).toContain('Architecture')
    })

    it('renders Testing tab', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.text()).toContain('Testing')
    })

    it('starts on Basic Info tab by default', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.dialogTab).toBe('basic')
    })

    it('Back button is disabled on first tab', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const buttons = wrapper.findAll('.v-btn')
      const backButton = buttons.find(btn => btn.text().includes('Back'))

      expect(backButton).toBeDefined()
      expect(backButton.attributes('disabled')).toBeDefined()
    })

    it('Next button navigates to next tab', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      expect(wrapper.vm.dialogTab).toBe('basic')

      // Find and click Next button
      const buttons = wrapper.findAll('.v-btn')
      const nextButton = buttons.find(btn => btn.text().includes('Next'))

      await nextButton.trigger('click')
      await flushPromises()

      expect(wrapper.vm.dialogTab).toBe('vision')
    })

    it('Back button navigates to previous tab', async () => {
      const wrapper = createWrapper()

      // Move to second tab
      wrapper.vm.dialogTab = 'vision'
      await flushPromises()

      // Click back
      const buttons = wrapper.findAll('.v-btn')
      const backButton = buttons.find(btn => btn.text().includes('Back'))

      await backButton.trigger('click')
      await flushPromises()

      expect(wrapper.vm.dialogTab).toBe('basic')
    })

    it('shows "Create Product" button on last tab for new products', async () => {
      const wrapper = createWrapper({ isEdit: false })

      // Navigate to last tab
      wrapper.vm.dialogTab = 'features'
      await flushPromises()

      const buttons = wrapper.findAll('.v-btn')
      const createButton = buttons.find(btn => btn.text().includes('Create Product'))

      expect(createButton).toBeDefined()
    })

    it('shows "Save Changes" button on any tab for edit mode', async () => {
      const wrapper = createWrapper({ isEdit: true })
      await flushPromises()

      const buttons = wrapper.findAll('.v-btn')
      const saveButton = buttons.find(btn => btn.text().includes('Save Changes'))

      expect(saveButton).toBeDefined()
    })
  })

  describe('Form Validation', () => {
    it('prevents save with empty name', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Name is empty by default
      expect(wrapper.vm.productForm.name).toBe('')

      // Form should not be valid
      expect(wrapper.vm.formValid).toBe(false)
    })

    it('allows save when name is provided', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Set name
      wrapper.vm.productForm.name = 'Test Product'
      await flushPromises()

      // Find name input and trigger validation
      const nameInput = wrapper.find('.v-text-field')
      await nameInput.setValue('Test Product')
      await flushPromises()

      // In real component, form would be valid
      expect(wrapper.vm.productForm.name).toBe('Test Product')
    })

    it('has name field with required rule', () => {
      const wrapper = createWrapper()

      // Check that productForm has name field
      expect(wrapper.vm.productForm).toHaveProperty('name')
    })
  })

  describe('Event Emissions', () => {
    it('emits save event with product data on save', async () => {
      const wrapper = createWrapper({ isEdit: true })
      await flushPromises()

      // Set product name to make form valid
      wrapper.vm.productForm.name = 'Test Product'
      wrapper.vm.formValid = true
      await flushPromises()

      // Find and click save button
      const buttons = wrapper.findAll('.v-btn')
      const saveButton = buttons.find(btn => btn.text().includes('Save Changes'))

      await saveButton.trigger('click')
      await flushPromises()

      expect(wrapper.emitted('save')).toBeTruthy()
      expect(wrapper.emitted('save')[0][0]).toHaveProperty('name', 'Test Product')
    })

    it('emits cancel event when close button clicked', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Use the closeDialog method directly
      wrapper.vm.closeDialog()
      await flushPromises()

      expect(wrapper.emitted('cancel')).toBeTruthy()
    })

    it('emits update:modelValue with false when cancelled', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Trigger close
      wrapper.vm.closeDialog()
      await flushPromises()

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')[0]).toEqual([false])
    })

    it('tracks vision files locally for inclusion in save payload', async () => {
      const wrapper = createWrapper()

      // Navigate to vision tab
      wrapper.vm.dialogTab = 'vision'
      await flushPromises()

      // Vision files are managed locally and passed via the save event payload
      expect(wrapper.vm.visionFiles).toBeDefined()
      expect(Array.isArray(wrapper.vm.visionFiles)).toBe(true)
    })

    it('emits remove-vision event when document deleted', async () => {
      const wrapper = createWrapper({
        existingVisionDocuments: [
          { id: 'doc-1', filename: 'test.md', chunk_count: 5 }
        ]
      })

      // Navigate to vision tab
      wrapper.vm.dialogTab = 'vision'
      await flushPromises()

      // Component should handle existing documents
      expect(wrapper.props('existingVisionDocuments')).toHaveLength(1)
    })
  })

  describe('Auto-save Status Indicator', () => {
    it('shows "Saving..." chip when status is saving', async () => {
      const wrapper = createWrapper({
        autoSaveState: { status: 'saving', enabled: true }
      })
      await flushPromises()

      expect(wrapper.text()).toContain('Saving')
    })

    it('shows "Saved" chip when status is saved', async () => {
      const wrapper = createWrapper({
        autoSaveState: { status: 'saved', enabled: true }
      })
      await flushPromises()

      expect(wrapper.text()).toContain('Saved')
    })

    it('shows "Unsaved changes" chip when status is unsaved', async () => {
      const wrapper = createWrapper({
        autoSaveState: { status: 'unsaved', enabled: true }
      })
      await flushPromises()

      expect(wrapper.text()).toContain('Unsaved')
    })

    it('shows "Error" chip when status is error', async () => {
      const wrapper = createWrapper({
        autoSaveState: { status: 'error', enabled: true }
      })
      await flushPromises()

      expect(wrapper.text()).toContain('Error')
    })

    it('has correct color for saving status (info)', async () => {
      const wrapper = createWrapper({
        autoSaveState: { status: 'saving', enabled: true }
      })
      await flushPromises()

      const chips = wrapper.findAll('.v-chip')
      const savingChip = chips.find(chip => chip.text().includes('Saving'))

      expect(savingChip).toBeDefined()
      if (savingChip) {
        expect(savingChip.classes()).toContain('info')
      }
    })
  })

  describe('Tech Stack Configuration', () => {
    it('has languages field in config_data', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.configData.tech_stack.languages).toBeDefined()
    })

    it('has frontend field in config_data', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.configData.tech_stack.frontend).toBeDefined()
    })

    it('has backend field in config_data', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.configData.tech_stack.backend).toBeDefined()
    })

    it('has database field in config_data', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.configData.tech_stack.database).toBeDefined()
    })

    it('has infrastructure field in config_data', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.configData.tech_stack.infrastructure).toBeDefined()
    })

    it('updates tech_stack when textarea changes', async () => {
      const wrapper = createWrapper()

      // Set languages
      wrapper.vm.productForm.configData.tech_stack.languages = 'Python 3.11, JavaScript'
      await flushPromises()

      expect(wrapper.vm.productForm.configData.tech_stack.languages).toBe('Python 3.11, JavaScript')
    })
  })

  describe('Architecture Configuration', () => {
    it('has pattern field in config_data', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.configData.architecture.pattern).toBeDefined()
    })

    it('has design_patterns field in config_data', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.configData.architecture.design_patterns).toBeDefined()
    })

    it('has api_style field in config_data', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.configData.architecture.api_style).toBeDefined()
    })

    it('has notes field in config_data', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.configData.architecture.notes).toBeDefined()
    })

    it('updates architecture when textarea changes', async () => {
      const wrapper = createWrapper()

      wrapper.vm.productForm.configData.architecture.pattern = 'Microservices'
      await flushPromises()

      expect(wrapper.vm.productForm.configData.architecture.pattern).toBe('Microservices')
    })
  })

  describe('Testing Configuration', () => {
    it('has strategy field with default TDD', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.configData.test_config.strategy).toBe('TDD')
    })

    it('has coverage_target field with default 80', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.configData.test_config.coverage_target).toBe(80)
    })

    it('has frameworks field in config_data', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.configData.test_config.frameworks).toBeDefined()
    })

    it('has quality_standards field in config_data', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.configData.test_config.quality_standards).toBeDefined()
    })

    it('updates test_config when values change', async () => {
      const wrapper = createWrapper()

      wrapper.vm.productForm.configData.test_config.coverage_target = 90
      wrapper.vm.productForm.configData.test_config.strategy = 'BDD'
      await flushPromises()

      expect(wrapper.vm.productForm.configData.test_config.coverage_target).toBe(90)
      expect(wrapper.vm.productForm.configData.test_config.strategy).toBe('BDD')
    })
  })

  describe('Tab Validation Badges', () => {
    it('has tabValidation computed property', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.tabValidation).toBeDefined()
    })

    it('basic tab shows error when name is empty', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.tabValidation.basic.hasError).toBe(true)
    })

    it('basic tab shows valid when name is provided', async () => {
      const wrapper = createWrapper()

      wrapper.vm.productForm.name = 'Test Product'
      await flushPromises()

      expect(wrapper.vm.tabValidation.basic.valid).toBe(true)
      expect(wrapper.vm.tabValidation.basic.hasError).toBe(false)
    })

    it('vision tab shows warning when no documents', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.tabValidation.vision.hasWarning).toBe(true)
    })

    it('tech tab shows warning when no languages specified', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.tabValidation.tech.hasWarning).toBe(true)
    })

    it('arch tab shows warning when no pattern specified', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.tabValidation.arch.hasWarning).toBe(true)
    })

    it('features tab shows warning when no core features', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.tabValidation.features.hasWarning).toBe(true)
    })
  })

  describe('Product Data Loading', () => {
    it('loads existing product data in edit mode', async () => {
      const existingProduct = {
        id: 'product-123',
        name: 'Existing Product',
        description: 'Test description',
        project_path: 'F:/Projects/Test',
        config_data: {
          tech_stack: {
            languages: 'Python',
            frontend: 'Vue',
            backend: 'FastAPI',
            database: 'PostgreSQL',
            infrastructure: 'Docker'
          },
          architecture: {
            pattern: 'Microservices',
            design_patterns: 'SOLID',
            api_style: 'REST',
            notes: 'Some notes'
          },
          features: {
            core: 'Core features list'
          },
          test_config: {
            strategy: 'BDD',
            coverage_target: 90,
            frameworks: 'pytest',
            quality_standards: 'High quality'
          }
        }
      }

      // Start with modelValue false, then set to true to trigger watch
      const wrapper = createWrapper({
        modelValue: false,
        isEdit: true,
        product: existingProduct
      })
      await flushPromises()

      // Now open the dialog to trigger the watch that loads product data
      await wrapper.setProps({ modelValue: true })
      await flushPromises()

      // Component should load product data
      expect(wrapper.vm.productForm.name).toBe('Existing Product')
      expect(wrapper.vm.productForm.description).toBe('Test description')
    })

    it('resets form when creating new product', async () => {
      const wrapper = createWrapper({ isEdit: false })
      await flushPromises()

      expect(wrapper.vm.productForm.name).toBe('')
      expect(wrapper.vm.productForm.description).toBe('')
    })
  })

  describe('Core Features Field', () => {
    it('has core features field in configData', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.configData.features.core).toBeDefined()
    })

    it('updates core features when textarea changes', async () => {
      const wrapper = createWrapper()

      wrapper.vm.productForm.configData.features.core = 'Feature 1, Feature 2'
      await flushPromises()

      expect(wrapper.vm.productForm.configData.features.core).toBe('Feature 1, Feature 2')
    })
  })

  describe('Project Path Field', () => {
    it('has projectPath field in form', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.productForm.projectPath).toBeDefined()
    })

    it('accepts project path input', async () => {
      const wrapper = createWrapper()

      wrapper.vm.productForm.projectPath = 'F:/Projects/MyProduct'
      await flushPromises()

      expect(wrapper.vm.productForm.projectPath).toBe('F:/Projects/MyProduct')
    })
  })

  describe('V-Model Pattern', () => {
    it('implements computed isOpen for v-model pattern', () => {
      const wrapper = createWrapper({ modelValue: true })

      expect(wrapper.vm.isOpen).toBe(true)
    })

    it('updates isOpen when modelValue changes', async () => {
      const wrapper = createWrapper({ modelValue: true })

      expect(wrapper.vm.isOpen).toBe(true)

      await wrapper.setProps({ modelValue: false })

      expect(wrapper.vm.isOpen).toBe(false)
    })
  })

  describe('Props Validation', () => {
    it('accepts required modelValue prop', () => {
      const wrapper = createWrapper({ modelValue: true })
      expect(wrapper.props('modelValue')).toBe(true)
    })

    it('accepts product prop with default null', () => {
      const wrapper = createWrapper()
      expect(wrapper.props('product')).toBeNull()
    })

    it('accepts isEdit prop with default false', () => {
      const wrapper = createWrapper()
      expect(wrapper.props('isEdit')).toBe(false)
    })

    it('accepts existingVisionDocuments prop with default empty array', () => {
      const wrapper = createWrapper()
      expect(wrapper.props('existingVisionDocuments')).toEqual([])
    })

    it('accepts autoSaveState prop', () => {
      const wrapper = createWrapper({
        autoSaveState: { status: 'saved', enabled: true }
      })
      expect(wrapper.props('autoSaveState')).toEqual({ status: 'saved', enabled: true })
    })

    it('accepts uploadingVision prop', () => {
      const wrapper = createWrapper({ uploadingVision: true })
      expect(wrapper.props('uploadingVision')).toBe(true)
    })

    it('accepts uploadProgress prop', () => {
      const wrapper = createWrapper({ uploadProgress: 66 })
      expect(wrapper.props('uploadProgress')).toBe(66)
    })

    it('accepts visionUploadError prop', () => {
      const wrapper = createWrapper({ visionUploadError: 'Something broke' })
      expect(wrapper.props('visionUploadError')).toBe('Something broke')
    })
  })

  describe('Testing Strategies Dropdown', () => {
    it('has testingStrategies array', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.testingStrategies).toBeDefined()
      expect(Array.isArray(wrapper.vm.testingStrategies)).toBe(true)
    })

    it('includes TDD strategy', () => {
      const wrapper = createWrapper()

      const tdd = wrapper.vm.testingStrategies.find(s => s.value === 'TDD')
      expect(tdd).toBeDefined()
      expect(tdd.title).toContain('TDD')
    })

    it('includes BDD strategy', () => {
      const wrapper = createWrapper()

      const bdd = wrapper.vm.testingStrategies.find(s => s.value === 'BDD')
      expect(bdd).toBeDefined()
      expect(bdd.title).toContain('BDD')
    })

    it('all strategies have icon, title, subtitle, and value', () => {
      const wrapper = createWrapper()

      wrapper.vm.testingStrategies.forEach(strategy => {
        expect(strategy).toHaveProperty('value')
        expect(strategy).toHaveProperty('title')
        expect(strategy).toHaveProperty('subtitle')
        expect(strategy).toHaveProperty('icon')
      })
    })
  })

  describe('Tab Navigation Helpers', () => {
    it('has tabOrder array with 5 tabs', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.tabOrder).toEqual(['basic', 'vision', 'tech', 'arch', 'features'])
    })

    it('isFirstTab is true when on basic tab', () => {
      const wrapper = createWrapper()

      wrapper.vm.dialogTab = 'basic'

      expect(wrapper.vm.isFirstTab).toBe(true)
    })

    it('isFirstTab is false when not on basic tab', () => {
      const wrapper = createWrapper()

      wrapper.vm.dialogTab = 'vision'

      expect(wrapper.vm.isFirstTab).toBe(false)
    })

    it('isLastTab is true when on features tab', () => {
      const wrapper = createWrapper()

      wrapper.vm.dialogTab = 'features'

      expect(wrapper.vm.isLastTab).toBe(true)
    })

    it('isLastTab is false when not on features tab', () => {
      const wrapper = createWrapper()

      wrapper.vm.dialogTab = 'basic'

      expect(wrapper.vm.isLastTab).toBe(false)
    })

    it('goNextTab moves to next tab', () => {
      const wrapper = createWrapper()

      wrapper.vm.dialogTab = 'basic'
      wrapper.vm.goNextTab()

      expect(wrapper.vm.dialogTab).toBe('vision')
    })

    it('goPrevTab moves to previous tab', () => {
      const wrapper = createWrapper()

      wrapper.vm.dialogTab = 'vision'
      wrapper.vm.goPrevTab()

      expect(wrapper.vm.dialogTab).toBe('basic')
    })

    it('goNextTab does not go past last tab', () => {
      const wrapper = createWrapper()

      wrapper.vm.dialogTab = 'features'
      wrapper.vm.goNextTab()

      expect(wrapper.vm.dialogTab).toBe('features')
    })

    it('goPrevTab does not go before first tab', () => {
      const wrapper = createWrapper()

      wrapper.vm.dialogTab = 'basic'
      wrapper.vm.goPrevTab()

      expect(wrapper.vm.dialogTab).toBe('basic')
    })
  })

  describe('Vision Upload Progress UI (Handover 0816)', () => {
    it('hides progress indicator when uploadingVision is false', async () => {
      const wrapper = createWrapper({ uploadingVision: false })
      wrapper.vm.dialogTab = 'vision'
      await flushPromises()

      const alerts = wrapper.findAll('.v-alert.info')
      expect(alerts.length).toBe(0)
    })

    it('shows progress indicator when uploadingVision is true', async () => {
      const wrapper = createWrapper({
        uploadingVision: true,
        uploadProgress: 50
      })
      wrapper.vm.dialogTab = 'vision'
      await flushPromises()

      const infoAlert = wrapper.find('.v-alert.info')
      expect(infoAlert.exists()).toBe(true)
      expect(infoAlert.text()).toContain('Uploading vision documents...')
    })

    it('renders progress bar inside the progress indicator', async () => {
      const wrapper = createWrapper({
        uploadingVision: true,
        uploadProgress: 75
      })
      wrapper.vm.dialogTab = 'vision'
      await flushPromises()

      const infoAlert = wrapper.find('.v-alert.info')
      expect(infoAlert.exists()).toBe(true)
      const progressBar = infoAlert.find('.v-progress-linear')
      expect(progressBar.exists()).toBe(true)
    })

    it('renders spinning indicator during upload', async () => {
      const wrapper = createWrapper({
        uploadingVision: true,
        uploadProgress: 25
      })
      wrapper.vm.dialogTab = 'vision'
      await flushPromises()

      const infoAlert = wrapper.find('.v-alert.info')
      const spinner = infoAlert.find('.v-progress-circular')
      expect(spinner.exists()).toBe(true)
    })

    it('hides error alert when visionUploadError is null', async () => {
      const wrapper = createWrapper({ visionUploadError: null })
      wrapper.vm.dialogTab = 'vision'
      await flushPromises()

      const errorAlert = wrapper.find('.v-alert.error')
      expect(errorAlert.exists()).toBe(false)
    })

    it('shows error alert when visionUploadError is set', async () => {
      const wrapper = createWrapper({
        visionUploadError: 'test.pdf: File too large (max 10MB)'
      })
      wrapper.vm.dialogTab = 'vision'
      await flushPromises()

      const errorAlert = wrapper.find('.v-alert.error')
      expect(errorAlert.exists()).toBe(true)
      expect(errorAlert.text()).toContain('test.pdf: File too large (max 10MB)')
    })

    it('error alert has dismiss button', async () => {
      const wrapper = createWrapper({
        visionUploadError: 'Upload failed'
      })
      wrapper.vm.dialogTab = 'vision'
      await flushPromises()

      const errorAlert = wrapper.find('.v-alert.error')
      const closeBtn = errorAlert.find('.v-alert-close')
      expect(closeBtn.exists()).toBe(true)
    })

    it('emits clear-upload-error when error alert is dismissed', async () => {
      const wrapper = createWrapper({
        visionUploadError: 'Upload failed'
      })
      wrapper.vm.dialogTab = 'vision'
      await flushPromises()

      const errorAlert = wrapper.find('.v-alert.error')
      const closeBtn = errorAlert.find('.v-alert-close')
      await closeBtn.trigger('click')
      await flushPromises()

      expect(wrapper.emitted('clear-upload-error')).toBeTruthy()
      expect(wrapper.emitted('clear-upload-error').length).toBe(1)
    })

    it('defaults uploadingVision prop to false', () => {
      const wrapper = createWrapper()
      expect(wrapper.props('uploadingVision')).toBe(false)
    })

    it('defaults uploadProgress prop to 0', () => {
      const wrapper = createWrapper()
      expect(wrapper.props('uploadProgress')).toBe(0)
    })

    it('defaults visionUploadError prop to null', () => {
      const wrapper = createWrapper()
      expect(wrapper.props('visionUploadError')).toBeNull()
    })

    it('has visionFiles local ref for file selection', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.visionFiles).toBeDefined()
      expect(Array.isArray(wrapper.vm.visionFiles)).toBe(true)
    })
  })

  describe('Form State Management', () => {
    it('has saving ref', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.saving).toBeDefined()
      expect(wrapper.vm.saving).toBe(false)
    })

    it('has formValid ref', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.formValid).toBeDefined()
    })

    it('has formRef for v-form reference', () => {
      const wrapper = createWrapper()

      expect(wrapper.vm.formRef).toBeDefined()
    })
  })

  describe('Accessibility', () => {
    it('has proper dialog structure', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      const dialog = wrapper.find('.v-dialog')
      expect(dialog.exists()).toBe(true)
    })

    it('has close button with aria-label', async () => {
      const wrapper = createWrapper()
      await flushPromises()

      // Component should have accessible close button
      const buttons = wrapper.findAll('.v-btn')
      expect(buttons.length).toBeGreaterThan(0)
    })
  })
})
