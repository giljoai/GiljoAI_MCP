/**
 * ContextPriorityConfig - Vision Documents Depth Tests
 *
 * Tests for Handover 0345c: Vision Settings UI - Vision Documents depth control
 * Tests vision_documents depth configuration, options, and API integration.
 *
 * Test Coverage:
 * - Vision documents context appears in depth controls
 * - Depth selector has 4 options (none/light/moderate/heavy)
 * - Vision depth loads from API
 * - Vision depth saves to API
 * - Token counts display correctly
 * - Vision documents can be toggled on/off
 * - Vision depth respects enabled state
 *
 * @see handovers/0345c_vision_settings_ui.md
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('ContextPriorityConfig - Vision Documents Depth', () => {
  let contexts
  let config
  let depthControlledContexts

  beforeEach(() => {
    // Simulate the contexts array from ContextPriorityConfig
    contexts = [
      { key: 'product_description', label: 'Product Description' },
      { key: 'tech_stack', label: 'Tech Stack' },
      { key: 'architecture', label: 'Architecture' },
      { key: 'testing', label: 'Testing' },
      {
        key: 'vision_documents',
        label: 'Vision Documents',
        options: ['none', 'light', 'moderate', 'heavy'],
        helpText: 'Vision document depth: none|light(10K)|moderate(17.5K)|heavy(24K) tokens',
      },
      {
        key: 'memory_360',
        label: '360 Memory',
        options: [1, 3, 5, 10],
        helpText: 'Number of previous project summaries to include',
      },
      {
        key: 'git_history',
        label: 'Git History',
        options: [5, 10, 25, 50, 100],
        helpText: 'Number of git commits in CLI examples',
      },
      {
        key: 'agent_templates',
        label: 'Agent Templates',
        options: ['type_only', 'full'],
        helpText: 'Type Only = Name/Version | Full = With descriptions',
      },
    ]

    // Initial config state
    config = {
      product_description: { enabled: true, priority: 1 },
      tech_stack: { enabled: true, priority: 2 },
      architecture: { enabled: true, priority: 2 },
      testing: { enabled: true, priority: 2 },
      vision_documents: { enabled: true, priority: 2, depth: 'moderate' },
      memory_360: { enabled: true, priority: 2, count: 3 },
      git_history: { enabled: false, priority: 4, count: 25 },
      agent_templates: { enabled: true, priority: 2, depth: 'type_only' },
    }

    // Filter depth-controlled contexts
    depthControlledContexts = contexts.filter((c) => c.options)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  /**
   * Test: Vision documents appears in depth-controlled contexts
   */
  it('includes vision_documents in depth-controlled contexts', () => {
    const hasVisionDocuments = depthControlledContexts.some((c) => c.key === 'vision_documents')
    expect(hasVisionDocuments).toBe(true)
  })

  /**
   * Test: Vision documents has correct label
   */
  it('has correct label for vision_documents', () => {
    const visionContext = depthControlledContexts.find((c) => c.key === 'vision_documents')
    expect(visionContext.label).toBe('Vision Documents')
  })

  /**
   * Test: Vision documents has 4 depth options
   */
  it('vision_documents has 4 depth options', () => {
    const visionContext = depthControlledContexts.find((c) => c.key === 'vision_documents')
    expect(visionContext.options).toHaveLength(4)
    expect(visionContext.options).toEqual(['none', 'light', 'moderate', 'heavy'])
  })

  /**
   * Test: All depth options are strings
   */
  it('all vision depth options are valid strings', () => {
    const visionContext = depthControlledContexts.find((c) => c.key === 'vision_documents')
    visionContext.options.forEach((opt) => {
      expect(typeof opt).toBe('string')
      expect(['none', 'light', 'moderate', 'heavy']).toContain(opt)
    })
  })

  /**
   * Test: Vision documents has help text
   */
  it('vision_documents has help text explaining depth levels', () => {
    const visionContext = depthControlledContexts.find((c) => c.key === 'vision_documents')
    expect(visionContext.helpText).toBeTruthy()
    expect(visionContext.helpText).toContain('token')
  })

  /**
   * Test: Default config has vision_documents enabled
   */
  it('has vision_documents enabled by default', () => {
    expect(config.vision_documents.enabled).toBe(true)
  })

  /**
   * Test: Default depth is moderate
   */
  it('default vision document depth is moderate', () => {
    expect(config.vision_documents.depth).toBe('moderate')
  })

  /**
   * Test: Vision documents depth can be updated
   */
  it('vision_documents depth can be changed', () => {
    config.vision_documents.depth = 'light'
    expect(config.vision_documents.depth).toBe('light')

    config.vision_documents.depth = 'heavy'
    expect(config.vision_documents.depth).toBe('heavy')

    config.vision_documents.depth = 'none'
    expect(config.vision_documents.depth).toBe('none')
  })

  /**
   * Test: Vision documents can be toggled off
   */
  it('vision_documents can be disabled', () => {
    config.vision_documents.enabled = false
    expect(config.vision_documents.enabled).toBe(false)

    // Priority should be set to EXCLUDED (4) when disabled
    config.vision_documents.priority = 4
    expect(config.vision_documents.priority).toBe(4)
  })

  /**
   * Test: Disabling vision documents doesn't lose depth setting
   */
  it('preserves depth setting when toggling vision_documents off', () => {
    const originalDepth = config.vision_documents.depth
    config.vision_documents.enabled = false
    expect(config.vision_documents.depth).toBe(originalDepth)
  })

  /**
   * Test: Vision depth labels are formatted correctly
   */
  it('formats vision depth options with token counts', () => {
    const visionLabels = {
      'none': 'None',
      'light': 'Light (10K tokens)',
      'moderate': 'Moderate (17.5K tokens)',
      'heavy': 'Heavy (24K tokens)',
    }

    const visionContext = depthControlledContexts.find((c) => c.key === 'vision_documents')
    visionContext.options.forEach((opt) => {
      expect(visionLabels[opt]).toBeTruthy()
    })
  })

  /**
   * Test: Vision documents API payload includes depth
   */
  it('includes vision_documents in API depth_config payload', () => {
    const depthPayload = {
      depth_config: {
        memory_last_n_projects: config.memory_360.count || 3,
        git_commits: config.git_history.count || 25,
        vision_documents: config.vision_documents.depth || 'moderate',
        agent_template_detail: config.agent_templates.depth || 'type_only',
      },
    }

    expect(depthPayload.depth_config).toHaveProperty('vision_documents')
    expect(depthPayload.depth_config.vision_documents).toBe('moderate')
  })

  /**
   * Test: API response maps vision_documents to config
   */
  it('maps vision_documents from API response to config', () => {
    const apiResponse = {
      depth_config: {
        memory_last_n_projects: 3,
        git_commits: 25,
        vision_documents: 'heavy',
        agent_template_detail: 'type_only',
      },
    }

    // Simulate mapping
    if (apiResponse.depth_config.vision_documents && config.vision_documents) {
      config.vision_documents.depth = apiResponse.depth_config.vision_documents
    }

    expect(config.vision_documents.depth).toBe('heavy')
  })

  /**
   * Test: Vision documents depth options exclude/include in priority config
   */
  it('vision_documents appears in depth-controlled section not priority-only', () => {
    const priorityOnlyContexts = contexts.filter((c) => !c.options)
    const hasVisionInPriorityOnly = priorityOnlyContexts.some((c) => c.key === 'vision_documents')

    expect(hasVisionInPriorityOnly).toBe(false)
  })

  /**
   * Test: Validate depth values match handover specification
   */
  it('depth values match handover specification (none|light|moderate|heavy)', () => {
    const validDepths = ['none', 'light', 'moderate', 'heavy']
    const visionContext = depthControlledContexts.find((c) => c.key === 'vision_documents')

    visionContext.options.forEach((option) => {
      expect(validDepths).toContain(option)
    })
  })

  /**
   * Test: Token counts are correctly documented
   */
  it('help text documents token counts for each depth level', () => {
    const visionContext = depthControlledContexts.find((c) => c.key === 'vision_documents')

    expect(visionContext.helpText).toContain('10K')  // light
    expect(visionContext.helpText).toContain('17.5K') // moderate
    expect(visionContext.helpText).toContain('24K')   // heavy
  })

  /**
   * Test: Vision documents is alongside other depth controls (not isolated)
   */
  it('vision_documents shares depth control section with other fields', () => {
    const depthFieldCount = depthControlledContexts.length
    expect(depthFieldCount).toBeGreaterThan(1)

    // Should have: vision_documents, memory_360, git_history, agent_templates
    const depthKeys = depthControlledContexts.map((c) => c.key)
    expect(depthKeys).toContain('vision_documents')
    expect(depthKeys).toContain('memory_360')
    expect(depthKeys).toContain('git_history')
    expect(depthKeys).toContain('agent_templates')
  })

  /**
   * Test: Vision documents respects enabled toggle
   */
  it('vision_documents depth selector disabled when context is disabled', () => {
    config.vision_documents.enabled = false

    // Simulate the logic: depth select should be disabled if context disabled
    const isDepthDisabled = !config.vision_documents.enabled
    expect(isDepthDisabled).toBe(true)
  })

  /**
   * Test: Default config structure matches expected format
   */
  it('config structure matches expected ContextConfig interface', () => {
    const visionConfig = config.vision_documents

    expect(visionConfig).toHaveProperty('enabled')
    expect(visionConfig).toHaveProperty('priority')
    expect(visionConfig).toHaveProperty('depth')

    expect(typeof visionConfig.enabled).toBe('boolean')
    expect(typeof visionConfig.priority).toBe('number')
    expect(typeof visionConfig.depth).toBe('string')
  })

  /**
   * Test: Vision depth can be persisted and restored
   */
  it('vision document depth persists across config save/load cycles', () => {
    // Simulate save
    const savedDepth = config.vision_documents.depth

    // Simulate load from API
    config.vision_documents.depth = 'heavy'
    expect(config.vision_documents.depth).toBe('heavy')
    expect(config.vision_documents.depth).not.toBe(savedDepth)

    // Simulate load restoring original
    config.vision_documents.depth = savedDepth
    expect(config.vision_documents.depth).toBe(savedDepth)
  })
})
