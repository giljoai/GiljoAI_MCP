import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import ContextPriorityConfig from '@/components/settings/ContextPriorityConfig.vue'
import axios from 'axios'

// Mock axios
vi.mock('axios')

describe('ContextPriorityConfig.vue', () => {
  let wrapper
  const mockAxios = axios

  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks()

    // Setup Vuetify for component
    const vuetify = createVuetify()

    // Mock successful API responses
    mockAxios.get.mockResolvedValue({
      data: {
        priorities: {
          product_core: 1,
          vision_documents: 2,
          project_context: 2,
          memory_360: 3,
          git_history: 3,
          agent_templates: 2,
        },
      },
    })

    mockAxios.put.mockResolvedValue({
      data: {
        version: '2.0',
        priorities: {},
      },
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  // Test 1: Component mounts and initializes
  it('UT-FP-001: Component mounts and loads field priority config', async () => {
    const vuetify = createVuetify()
    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    // Wait for async fetch
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Verify axios was called for GET
    expect(mockAxios.get).toHaveBeenCalledWith('/api/v1/users/me/field-priority')

    // Verify loading state is reset
    expect(wrapper.vm.loading).toBe(false)
  })

  // Test 2: Toggle context enable/disable
  it('UT-FP-002: Toggle context enables/disables correctly', async () => {
    const vuetify = createVuetify()
    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Get initial enabled state
    const initialEnabled = wrapper.vm.config.vision_documents.enabled

    // Call toggleContext
    wrapper.vm.toggleContext('vision_documents')
    await wrapper.vm.$nextTick()

    // Verify state changed
    expect(wrapper.vm.config.vision_documents.enabled).toBe(!initialEnabled)

    // Verify saveConfig was called (axios.put)
    expect(mockAxios.put).toHaveBeenCalled()
  })

  // Test 3: Update priority value
  it('UT-FP-003: Update priority changes value correctly', async () => {
    const vuetify = createVuetify()
    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Update priority for tech_stack to 3
    wrapper.vm.updatePriority('tech_stack', 3)
    await wrapper.vm.$nextTick()

    // Verify state changed
    expect(wrapper.vm.config.tech_stack.priority).toBe(3)

    // Verify save was triggered
    expect(mockAxios.put).toHaveBeenCalled()
  })

  // Test 4: Update depth for string-based context
  it('UT-FP-004: Update depth for vision_documents works correctly', async () => {
    const vuetify = createVuetify()
    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Change depth to 'heavy'
    wrapper.vm.updateDepth('vision_documents', 'heavy')
    await wrapper.vm.$nextTick()

    // Verify state changed
    expect(wrapper.vm.config.vision_documents.depth).toBe('heavy')

    // Verify save was triggered
    expect(mockAxios.put).toHaveBeenCalled()
  })

  // Test 5: Update count for number-based context
  it('UT-FP-005: Update count for memory_360 works correctly', async () => {
    const vuetify = createVuetify()
    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Change count to 10
    wrapper.vm.updateDepth('memory_360', 10)
    await wrapper.vm.$nextTick()

    // Verify state changed
    expect(wrapper.vm.config.memory_360.count).toBe(10)

    // Verify save was triggered
    expect(mockAxios.put).toHaveBeenCalled()
  })

  // Test 6: Format conversion for backend
  it('IT-FP-005: Format conversion maps UI fields to backend categories correctly', async () => {
    const vuetify = createVuetify()
    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()

    // Create test config with specific values
    const localConfig = {
      product_description: { enabled: true, priority: 2 },
      tech_stack: { enabled: true, priority: 3 },
      vision_documents: { enabled: true, priority: 1 },
      architecture: { enabled: true, priority: 2 },
      testing: { enabled: true, priority: 3 },
      agent_templates: { enabled: true, priority: 1 },
      memory_360: { enabled: true, priority: 3, count: 5 },
      git_history: { enabled: false, priority: 4, count: 0 },
    }

    // Convert format
    const backendFormat = wrapper.vm.convertToBackendFormat(localConfig)

    // Verify mappings
    expect(backendFormat.product_core).toBe(2) // product_description=2 and tech_stack=3, so min=2
    expect(backendFormat.vision_documents).toBe(1)
    expect(backendFormat.project_context).toBe(2) // architecture=2 and testing=3, so min=2
    expect(backendFormat.agent_templates).toBe(1)
    expect(backendFormat.memory_360).toBe(3)
    expect(backendFormat.git_history).toBe(4) // disabled, so 4
  })

  // Test 7: Save config makes correct API call
  it('IT-FP-001: saveConfig makes PUT request with correct parameters', async () => {
    const vuetify = createVuetify()
    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Clear mock to test next call
    mockAxios.put.mockClear()

    // Change a priority
    wrapper.vm.updatePriority('tech_stack', 4)
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 50))

    // Verify axios.put was called with correct parameters
    expect(mockAxios.put).toHaveBeenCalledWith(
      '/api/v1/users/me/field-priority',
      expect.objectContaining({
        version: '2.0',
        priorities: expect.any(Object),
      })
    )

    // Verify call args include version and priorities
    const callArgs = mockAxios.put.mock.calls[0]
    expect(callArgs[1].version).toBe('2.0')
    expect(callArgs[1].priorities).toBeDefined()
  })

  // Test 8: API response error handling
  it('IT-FP-003: API error is logged and handled gracefully', async () => {
    const vuetify = createVuetify()

    // Mock error response
    mockAxios.put.mockRejectedValueOnce(new Error('Network error'))

    // Spy on console.error
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Make change that triggers save
    wrapper.vm.updatePriority('tech_stack', 1)
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 50))

    // Verify error was logged
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('CONTEXT PRIORITY CONFIG'),
      expect.any(Error)
    )

    consoleSpy.mockRestore()
  })

  // Test 9: Multiple consecutive changes trigger multiple saves
  it('IT-FP-004: Auto-save on each change triggers multiple API calls', async () => {
    const vuetify = createVuetify()
    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Clear mock to count fresh calls
    mockAxios.put.mockClear()

    // Make 3 changes
    wrapper.vm.updatePriority('tech_stack', 2)
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 50))

    wrapper.vm.updatePriority('vision_documents', 3)
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 50))

    wrapper.vm.toggleContext('agent_templates')
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 50))

    // Verify 3 API calls were made
    expect(mockAxios.put).toHaveBeenCalledTimes(3)
  })

  // Test 10: Disabled field on save doesn't set priority explicitly
  it('UT-FP-002: Disabled context field is saved with priority 4 (Exclude)', async () => {
    const vuetify = createVuetify()
    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()

    // Create config with disabled field
    const localConfig = {
      product_description: { enabled: false, priority: 1 },
      vision_documents: { enabled: true, priority: 2 },
      tech_stack: { enabled: true, priority: 3 },
      architecture: { enabled: true, priority: 1 },
      testing: { enabled: true, priority: 2 },
      agent_templates: { enabled: true, priority: 1 },
      memory_360: { enabled: true, priority: 3 },
      git_history: { enabled: true, priority: 3 },
    }

    const backendFormat = wrapper.vm.convertToBackendFormat(localConfig)

    // Verify disabled field gets priority 4
    expect(backendFormat.product_core).toBe(4) // product_description is disabled
  })

  // Test 11: Component exposes required methods
  it('UT-FP-001: Component exposes required methods for testing', async () => {
    const vuetify = createVuetify()
    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    // Verify exposed methods
    expect(typeof wrapper.vm.toggleContext).toBe('function')
    expect(typeof wrapper.vm.updatePriority).toBe('function')
    expect(typeof wrapper.vm.updateDepth).toBe('function')
    expect(typeof wrapper.vm.saveConfig).toBe('function')
    expect(typeof wrapper.vm.convertToBackendFormat).toBe('function')

    // Verify exposed data
    expect(Array.isArray(wrapper.vm.contexts)).toBe(true)
    expect(Array.isArray(wrapper.vm.priorityOptions)).toBe(true)
    expect(typeof wrapper.vm.config).toBe('object')
  })

  // Test 12: getDepthValue returns correct value based on context type
  it('UT-FP-004 & 005: getDepthValue returns depth or count based on context', async () => {
    const vuetify = createVuetify()
    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()

    // Test string-based depth
    const visionDepth = wrapper.vm.getDepthValue('vision_documents')
    expect(typeof visionDepth).toBe('string')

    // Test number-based count
    const memoryCount = wrapper.vm.getDepthValue('memory_360')
    expect(typeof memoryCount).toBe('number')

    // Test contexts without depth/count
    const archDepth = wrapper.vm.getDepthValue('architecture')
    expect(archDepth).toBeUndefined()
  })

  // Test 13: Priority options are correctly formatted
  it('UT-FP-003: Priority options are correctly defined', async () => {
    const vuetify = createVuetify()
    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    expect(wrapper.vm.priorityOptions).toEqual([
      { title: 'Critical', value: 1 },
      { title: 'Important', value: 2 },
      { title: 'Reference', value: 3 },
      { title: 'Exclude', value: 4 },
    ])
  })

  // Test 14: All contexts are defined
  it('UT-FP-001: All expected contexts are defined', async () => {
    const vuetify = createVuetify()
    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    const contextKeys = wrapper.vm.contexts.map(c => c.key)
    expect(contextKeys).toContain('product_description')
    expect(contextKeys).toContain('vision_documents')
    expect(contextKeys).toContain('tech_stack')
    expect(contextKeys).toContain('architecture')
    expect(contextKeys).toContain('testing')
    expect(contextKeys).toContain('agent_templates')
    expect(contextKeys).toContain('memory_360')
    expect(contextKeys).toContain('git_history')
  })

  // Test 15: Initial config has valid default values
  it('UT-FP-001: Initial config has valid default values', async () => {
    const vuetify = createVuetify()
    wrapper = mount(ContextPriorityConfig, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()

    // Verify all contexts have enabled and priority
    wrapper.vm.contexts.forEach(context => {
      expect(wrapper.vm.config[context.key]).toBeDefined()
      expect(typeof wrapper.vm.config[context.key].enabled).toBe('boolean')
      expect(typeof wrapper.vm.config[context.key].priority).toBe('number')
      expect(wrapper.vm.config[context.key].priority).toBeGreaterThanOrEqual(1)
      expect(wrapper.vm.config[context.key].priority).toBeLessThanOrEqual(4)
    })
  })
})
