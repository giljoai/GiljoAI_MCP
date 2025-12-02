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
      expect(text).toContain('Always High')
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

      // Should have 8 priority selects (one for each context)
      const selects = wrapper.findAllComponents({ name: 'VSelect' })
      // At minimum should have priority selects, may also have depth selects
      expect(selects.length).toBeGreaterThanOrEqual(8)
    })

    it('renders toggle switches for each context', () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      // Should have 8 switches (one for each context)
      const switches = wrapper.findAllComponents({ name: 'VSwitch' })
      expect(switches.length).toBe(8)
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
    it('has High/Medium/Low priority options', async () => {
      wrapper = mount(ContextPriorityConfig, {
        global: {
          plugins: [vuetify, pinia],
        },
      })

      await wrapper.vm.$nextTick()

      const priorityOptions = wrapper.vm.priorityOptions

      expect(priorityOptions).toContainEqual({ title: 'High', value: 'high' })
      expect(priorityOptions).toContainEqual({ title: 'Medium', value: 'medium' })
      expect(priorityOptions).toContainEqual({ title: 'Low', value: 'low' })
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
})
