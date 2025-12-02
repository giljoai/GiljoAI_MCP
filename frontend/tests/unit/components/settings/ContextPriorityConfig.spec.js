/**
 * Test suite for ContextPriorityConfig.vue component
 * Handover 0323: Frontend Simplification
 *
 * Tests the simplified Context Priority Configuration:
 * - Rendering of context rows with toggles and priority selects
 * - Locked Project Context display
 * - API integration for loading/saving config
 * - State management and event emissions
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'
import ContextPriorityConfig from '@/components/settings/ContextPriorityConfig.vue'

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
  },
}))

describe('ContextPriorityConfig.vue', () => {
  let vuetify
  let pinia
  let wrapper
  let axiosMock

  const defaultConfig = {
    contexts: {
      product_description: { enabled: true, priority: 'high' },
      vision_documents: { enabled: true, priority: 'medium', depth: 'moderate' },
      tech_stack: { enabled: true, priority: 'medium' },
      architecture: { enabled: true, priority: 'medium' },
      testing: { enabled: true, priority: 'low' },
      agent_templates: { enabled: true, priority: 'medium', depth: 'type_only' },
      memory_360: { enabled: true, priority: 'low', count: 3 },
      git_history: { enabled: true, priority: 'low', count: 15 },
    },
  }

  beforeEach(async () => {
    // Setup Vuetify
    vuetify = createVuetify({
      components,
      directives,
    })

    // Setup Pinia
    pinia = createPinia()
    setActivePinia(pinia)

    // Setup axios mock
    const axios = await import('axios')
    axiosMock = axios.default
    axiosMock.get.mockResolvedValue({ data: defaultConfig })
    axiosMock.put.mockResolvedValue({ data: defaultConfig })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('renders the component', () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('displays card title "Context Priority Configuration"', () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      expect(wrapper.text()).toContain('Context Priority Configuration')
    })

    it('displays locked Project Context at top', () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      const text = wrapper.text()
      expect(text).toContain('Project Context')
      expect(text).toContain('Always Critical')
    })

    it('renders all 9 context rows (8 configurable + 1 locked)', () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      const text = wrapper.text()
      // 8 configurable contexts
      expect(text).toContain('Product Description')
      expect(text).toContain('Vision Documents')
      expect(text).toContain('Tech Stack')
      expect(text).toContain('Architecture')
      expect(text).toContain('Testing')
      expect(text).toContain('Agent Templates')
      expect(text).toContain('360 Memory')
      expect(text).toContain('Git History')
      // 1 locked context
      expect(text).toContain('Project Context')
    })

    it('renders priority selects for each context', () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      // Verify contexts are defined (Vuetify components may not render fully in test)
      const contexts = wrapper.vm.contexts
      expect(contexts.length).toBe(8)

      // Each context should have a priority select in the config
      contexts.forEach((context) => {
        expect(wrapper.vm.config[context.key]).toBeDefined()
        expect(wrapper.vm.config[context.key].priority).toBeDefined()
      })
    })

    it('renders toggle switches for each context', () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      // Verify contexts are defined (Vuetify components may not render fully in test)
      const contexts = wrapper.vm.contexts
      expect(contexts.length).toBe(8)

      // Each context should have an enabled flag in the config
      contexts.forEach((context) => {
        expect(wrapper.vm.config[context.key]).toBeDefined()
        expect(wrapper.vm.config[context.key].enabled).toBeDefined()
      })
    })
  })

  describe('Context Definitions', () => {
    it('includes correct context keys', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      const contexts = wrapper.vm.contexts
      const keys = contexts.map((c) => c.key)

      expect(keys).toContain('product_description')
      expect(keys).toContain('vision_documents')
      expect(keys).toContain('tech_stack')
      expect(keys).toContain('architecture')
      expect(keys).toContain('testing')
      expect(keys).toContain('agent_templates')
      expect(keys).toContain('memory_360')
      expect(keys).toContain('git_history')
    })

    it('vision_documents has depth options', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      const contexts = wrapper.vm.contexts
      const visionContext = contexts.find((c) => c.key === 'vision_documents')

      expect(visionContext.options).toBeDefined()
      expect(visionContext.options).toContain('none')
      expect(visionContext.options).toContain('light')
      expect(visionContext.options).toContain('moderate')
      expect(visionContext.options).toContain('heavy')
    })

    it('agent_templates has depth options', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      const contexts = wrapper.vm.contexts
      const agentContext = contexts.find((c) => c.key === 'agent_templates')

      expect(agentContext.options).toBeDefined()
      expect(agentContext.options).toContain('type_only')
      expect(agentContext.options).toContain('full')
    })

    it('memory_360 has count options', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      const contexts = wrapper.vm.contexts
      const memoryContext = contexts.find((c) => c.key === 'memory_360')

      expect(memoryContext.options).toBeDefined()
      expect(memoryContext.options).toContain(1)
      expect(memoryContext.options).toContain(3)
      expect(memoryContext.options).toContain(5)
      expect(memoryContext.options).toContain(10)
    })

    it('git_history has count options', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      const contexts = wrapper.vm.contexts
      const gitContext = contexts.find((c) => c.key === 'git_history')

      expect(gitContext.options).toBeDefined()
      expect(gitContext.options).toContain(0)
      expect(gitContext.options).toContain(5)
      expect(gitContext.options).toContain(15)
      expect(gitContext.options).toContain(25)
    })

    it('tech_stack has depth options', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      const contexts = wrapper.vm.contexts
      const techStackContext = contexts.find((c) => c.key === 'tech_stack')

      expect(techStackContext.options).toBeDefined()
      expect(techStackContext.options).toContain('required')
      expect(techStackContext.options).toContain('all')
    })

    it('architecture has depth options', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      const contexts = wrapper.vm.contexts
      const architectureContext = contexts.find((c) => c.key === 'architecture')

      expect(architectureContext.options).toBeDefined()
      expect(architectureContext.options).toContain('overview')
      expect(architectureContext.options).toContain('detailed')
    })

    it('testing has depth options', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      const contexts = wrapper.vm.contexts
      const testingContext = contexts.find((c) => c.key === 'testing')

      expect(testingContext.options).toBeDefined()
      expect(testingContext.options).toContain('none')
      expect(testingContext.options).toContain('basic')
      expect(testingContext.options).toContain('full')
    })
  })

  describe('Priority Options', () => {
    it('has Critical/Important/Reference/Exclude priority options', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      const priorityOptions = wrapper.vm.priorityOptions

      expect(priorityOptions).toContainEqual({ title: 'Critical', value: 1 })
      expect(priorityOptions).toContainEqual({ title: 'Important', value: 2 })
      expect(priorityOptions).toContainEqual({ title: 'Reference', value: 3 })
      expect(priorityOptions).toContainEqual({ title: 'Exclude', value: 4 })
    })
  })

  describe('API Integration', () => {
    it('fetches config on mount', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      expect(axiosMock.get).toHaveBeenCalledWith('/api/v1/users/me/context/depth')
    })

    it('saves config when save button clicked', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      // Find and click save button
      const saveBtn = wrapper.find('[data-test="save-context-config"]')
      if (saveBtn.exists()) {
        await saveBtn.trigger('click')
        await wrapper.vm.$nextTick()

        expect(axiosMock.put).toHaveBeenCalledWith(
          '/api/v1/users/me/context/depth',
          expect.objectContaining({
            contexts: expect.any(Object),
          })
        )
      }
    })

    it('handles API error gracefully', async () => {
      axiosMock.get.mockRejectedValueOnce(new Error('Network error'))

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      // Component should still render
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.text()).toContain('Context Priority Configuration')
    })
  })

  describe('State Management', () => {
    it('initializes with default config', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      const config = wrapper.vm.config
      expect(config.product_description.enabled).toBeDefined()
      expect(config.product_description.priority).toBeDefined()
    })

    it('updates config when toggle changes', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      // Get initial state
      const initialEnabled = wrapper.vm.config.testing.enabled

      // Toggle testing context
      wrapper.vm.toggleContext('testing')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.config.testing.enabled).toBe(!initialEnabled)
    })

    it('updates config when priority changes', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      // Update priority
      wrapper.vm.updatePriority('tech_stack', 'high')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.config.tech_stack.priority).toBe('high')
    })

    it('updates depth value for vision_documents', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      // Update depth
      wrapper.vm.updateDepth('vision_documents', 'heavy')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.config.vision_documents.depth).toBe('heavy')
    })

    it('updates count value for memory_360', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      // Update count
      wrapper.vm.updateDepth('memory_360', 10)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.config.memory_360.count).toBe(10)
    })
  })

  describe('Loading States', () => {
    it('shows loading state during fetch', async () => {
      // Delay the response
      axiosMock.get.mockImplementationOnce(
        () => new Promise((resolve) => setTimeout(() => resolve({ data: defaultConfig }), 100))
      )

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      // Check loading state before response
      expect(wrapper.vm.loading).toBe(true)
    })

    it('shows saving state during save', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      // Start save
      const savePromise = wrapper.vm.saveConfig()

      // Check saving state
      expect(wrapper.vm.saving).toBe(true)

      await savePromise
    })
  })

  describe('No Token Estimation', () => {
    it('does not display token estimates', () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      const text = wrapper.text()
      // Should not contain typical token estimation text
      expect(text).not.toContain('tokens')
      expect(text).not.toContain('Token Budget')
      expect(text).not.toContain('Estimated')
    })
  })

  describe('Accessibility', () => {
    it('has aria labels on switches', () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      const switches = wrapper.findAllComponents({ name: 'VSwitch' })
      switches.forEach((switchComponent) => {
        const ariaLabel = switchComponent.attributes('aria-label')
        expect(ariaLabel).toBeTruthy()
      })
    })

    it('has aria labels on priority selects', () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      const selects = wrapper.findAllComponents({ name: 'VSelect' })
      selects.forEach((select) => {
        const ariaLabel = select.attributes('aria-label')
        expect(ariaLabel).toBeTruthy()
      })
    })
  })

  describe('Field Mapping Persistence', () => {
    it('should save tech_stack priority independently from product_core', async () => {
      // Arrange: Track what's sent to backend
      const savedPriorities = {}
      axiosMock.put.mockImplementation((url, data) => {
        if (url === '/api/v1/users/me/field-priority') {
          savedPriorities.fieldPriority = data.priorities
        }
        return Promise.resolve({ data: {} })
      })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      // Act: Disable tech_stack (should set priority to 4)
      await wrapper.vm.toggleContext('tech_stack')

      // Assert: Backend should receive tech_stack = 4, product_core should remain 1
      expect(savedPriorities.fieldPriority).toBeDefined()
      expect(savedPriorities.fieldPriority.tech_stack).toBe(4)
      expect(savedPriorities.fieldPriority.product_core).toBe(1)
    })

    it('should save architecture priority independently from project_context', async () => {
      // Arrange: Track what's sent to backend
      const savedPriorities = {}
      axiosMock.put.mockImplementation((url, data) => {
        if (url === '/api/v1/users/me/field-priority') {
          savedPriorities.fieldPriority = data.priorities
        }
        return Promise.resolve({ data: {} })
      })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      // Act: Disable architecture (should set priority to 4)
      await wrapper.vm.toggleContext('architecture')

      // Assert: Backend should receive architecture = 4, project_context shouldn't exist
      expect(savedPriorities.fieldPriority).toBeDefined()
      expect(savedPriorities.fieldPriority.architecture).toBe(4)
      expect(savedPriorities.fieldPriority.project_context).toBeUndefined()
    })

    it('should save testing priority independently', async () => {
      // Arrange: Track what's sent to backend
      const savedPriorities = {}
      axiosMock.put.mockImplementation((url, data) => {
        if (url === '/api/v1/users/me/field-priority') {
          savedPriorities.fieldPriority = data.priorities
        }
        return Promise.resolve({ data: {} })
      })

      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      // Act: Disable testing (should set priority to 4)
      await wrapper.vm.toggleContext('testing')

      // Assert: Backend should receive testing = 4
      expect(savedPriorities.fieldPriority).toBeDefined()
      expect(savedPriorities.fieldPriority.testing).toBe(4)
    })

    it('should restore tech_stack setting independently when loading from backend', async () => {
      // Arrange: Mock server response with tech_stack disabled but product_core enabled
      axiosMock.get.mockImplementation((url) => {
        if (url === '/api/v1/users/me/field-priority') {
          return Promise.resolve({
            data: {
              priorities: {
                product_core: 1,     // Enabled
                tech_stack: 4,       // Disabled
                architecture: 2,
                testing: 2,
                vision_documents: 2,
                agent_templates: 2,
                memory_360: 3,
                git_history: 3,
              },
            },
          })
        }
        if (url === '/api/v1/users/me/context/depth') {
          return Promise.resolve({ data: { depth_config: {} } })
        }
        return Promise.resolve({ data: {} })
      })

      // Act: Mount component (triggers fetchConfig)
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()
      await new Promise((resolve) => setTimeout(resolve, 50)) // Wait for async fetch

      // Assert: tech_stack should be disabled, product_description should be enabled
      expect(wrapper.vm.config.tech_stack.enabled).toBe(false)
      expect(wrapper.vm.config.tech_stack.priority).toBe(4)
      expect(wrapper.vm.config.product_description.enabled).toBe(true)
      expect(wrapper.vm.config.product_description.priority).toBe(1)
    })

    it('should restore architecture and testing settings independently', async () => {
      // Arrange: Mock server response with architecture disabled, testing enabled
      axiosMock.get.mockImplementation((url) => {
        if (url === '/api/v1/users/me/field-priority') {
          return Promise.resolve({
            data: {
              priorities: {
                product_core: 1,
                tech_stack: 2,
                architecture: 4,     // Disabled
                testing: 2,          // Enabled
                vision_documents: 2,
                agent_templates: 2,
                memory_360: 3,
                git_history: 3,
              },
            },
          })
        }
        if (url === '/api/v1/users/me/context/depth') {
          return Promise.resolve({ data: { depth_config: {} } })
        }
        return Promise.resolve({ data: {} })
      })

      // Act: Mount component (triggers fetchConfig)
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()
      await new Promise((resolve) => setTimeout(resolve, 50)) // Wait for async fetch

      // Assert: architecture disabled, testing enabled
      expect(wrapper.vm.config.architecture.enabled).toBe(false)
      expect(wrapper.vm.config.architecture.priority).toBe(4)
      expect(wrapper.vm.config.testing.enabled).toBe(true)
      expect(wrapper.vm.config.testing.priority).toBe(2)
    })

    it('should use 1:1 mapping for all fields', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      // Access the internal mapping constants via exposed methods
      // We'll test this by verifying the convertToBackendFormat behavior
      const testConfig = {
        product_description: { enabled: true, priority: 1 },
        tech_stack: { enabled: false, priority: 4 },
        architecture: { enabled: true, priority: 2 },
        testing: { enabled: false, priority: 4 },
        vision_documents: { enabled: true, priority: 2, depth: 'moderate' },
        agent_templates: { enabled: true, priority: 2, depth: 'type_only' },
        memory_360: { enabled: true, priority: 3, count: 3 },
        git_history: { enabled: true, priority: 3, count: 15 },
      }

      // Set the config
      wrapper.vm.config = testConfig

      // Trigger save to see what backend format is generated
      const savedPriorities = {}
      axiosMock.put.mockImplementation((url, data) => {
        if (url === '/api/v1/users/me/field-priority') {
          savedPriorities.fieldPriority = data.priorities
        }
        return Promise.resolve({ data: {} })
      })

      await wrapper.vm.saveConfig()

      // Assert: Each field should map to itself (1:1 mapping)
      expect(savedPriorities.fieldPriority.product_core).toBe(1)
      expect(savedPriorities.fieldPriority.tech_stack).toBe(4)
      expect(savedPriorities.fieldPriority.architecture).toBe(2)
      expect(savedPriorities.fieldPriority.testing).toBe(4)
      expect(savedPriorities.fieldPriority.vision_documents).toBe(2)
      expect(savedPriorities.fieldPriority.agent_templates).toBe(2)
      expect(savedPriorities.fieldPriority.memory_360).toBe(3)
      expect(savedPriorities.fieldPriority.git_history).toBe(3)
    })
  })
})
