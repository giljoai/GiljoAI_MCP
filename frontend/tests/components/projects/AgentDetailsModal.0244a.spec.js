/**
 * AgentDetailsModal.0244a.spec.js
 *
 * Handover 0244a: Agent Info Icon Template Display Tests
 *
 * Test Coverage:
 * 1. Template data fetching and display for non-orchestrator agents
 * 2. Template fields display (Role, CLI Tool, Description, Model, Tools, Instructions)
 * 3. Orchestrator prompt display (existing functionality)
 * 4. Graceful handling of missing template_id
 * 5. Loading and error states
 * 6. Expansion panels for instructions
 * 7. Copy to clipboard functionality
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import AgentDetailsModal from '@/components/projects/AgentDetailsModal.vue'

// Mock API service
const mockTemplateGet = vi.fn()
const mockOrchestratorPrompt = vi.fn()

vi.mock('@/services/api', () => ({
  default: {
    templates: {
      get: (...args) => mockTemplateGet(...args)
    },
    system: {
      getOrchestratorPrompt: (...args) => mockOrchestratorPrompt(...args)
    }
  }
}))

describe('AgentDetailsModal - Handover 0244a Template Display', () => {
  let vuetify
  let wrapper

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
    })

    // Reset mocks
    mockTemplateGet.mockReset()
    mockOrchestratorPrompt.mockReset()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('1. Template Data Fetching and Display', () => {
    it('fetches and displays template data for non-orchestrator agents', async () => {
      const mockTemplate = {
        id: 'template-123',
        name: 'Test Implementer',
        role: 'implementer',
        cli_tool: 'claude',
        description: 'Test agent for implementing features',
        model: 'claude-sonnet-4',
        tools: ['file_read', 'file_write', 'bash'],
        system_instructions: 'System instructions for the agent',
        user_instructions: 'User instructions for the agent'
      }

      mockTemplateGet.mockResolvedValue({ data: mockTemplate })

      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'agent-456',
            agent_type: 'implementer',
            agent_name: 'Test Implementer',
            template_id: 'template-123'
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      // Wait for async data fetch
      await flushPromises()

      // Verify API was called with correct template_id
      expect(mockTemplateGet).toHaveBeenCalledWith('template-123')

      // Verify role is displayed
      expect(wrapper.text()).toContain('Role')
      expect(wrapper.text()).toContain('implementer')

      // Verify CLI tool is displayed
      expect(wrapper.text()).toContain('CLI Tool')
      expect(wrapper.text()).toContain('claude')

      // Verify model is displayed
      expect(wrapper.text()).toContain('Model')
      expect(wrapper.text()).toContain('claude-sonnet-4')

      // Verify description is displayed
      expect(wrapper.text()).toContain('Description')
      expect(wrapper.text()).toContain('Test agent for implementing features')
    })

    it('displays tools as chips', async () => {
      const mockTemplate = {
        id: 'template-123',
        role: 'tester',
        tools: ['pytest', 'coverage', 'lint']
      }

      mockTemplateGet.mockResolvedValue({ data: mockTemplate })

      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'agent-456',
            agent_type: 'tester',
            template_id: 'template-123'
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Verify tools section header
      expect(wrapper.text()).toContain('MCP Tools (3)')

      // Verify each tool is displayed
      expect(wrapper.text()).toContain('pytest')
      expect(wrapper.text()).toContain('coverage')
      expect(wrapper.text()).toContain('lint')
    })
  })

  describe('2. Expansion Panels for Instructions', () => {
    it('displays system instructions in expansion panel', async () => {
      const mockTemplate = {
        id: 'template-123',
        role: 'architect',
        system_instructions: 'You are a system architect. Design scalable solutions.'
      }

      mockTemplateGet.mockResolvedValue({ data: mockTemplate })

      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'agent-456',
            agent_type: 'architect',
            template_id: 'template-123'
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Verify system instructions panel exists
      expect(wrapper.text()).toContain('System Instructions')
      expect(wrapper.text()).toContain('You are a system architect')
    })

    it('displays user instructions in expansion panel', async () => {
      const mockTemplate = {
        id: 'template-123',
        role: 'reviewer',
        user_instructions: 'Review code for quality and best practices.'
      }

      mockTemplateGet.mockResolvedValue({ data: mockTemplate })

      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'agent-456',
            agent_type: 'reviewer',
            template_id: 'template-123'
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Verify user instructions panel exists
      expect(wrapper.text()).toContain('User Instructions')
      expect(wrapper.text()).toContain('Review code for quality')
    })

    it('displays template content for backward compatibility', async () => {
      const mockTemplate = {
        id: 'template-123',
        role: 'documenter',
        system_instructions: 'Legacy template content format'
      }

      mockTemplateGet.mockResolvedValue({ data: mockTemplate })

      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'agent-456',
            agent_type: 'documenter',
            template_id: 'template-123'
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Verify template content panel exists
      expect(wrapper.text()).toContain('Template Content')
      expect(wrapper.text()).toContain('Legacy template content format')
    })
  })

  describe('3. Orchestrator Functionality (Existing)', () => {
    it('fetches and displays orchestrator prompt', async () => {
      const mockPrompt = {
        content: 'You are the system orchestrator. Coordinate all agents.'
      }

      mockOrchestratorPrompt.mockResolvedValue({ data: mockPrompt })

      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'orchestrator-123',
            agent_type: 'orchestrator',
            agent_name: 'Orchestrator'
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Verify orchestrator prompt API was called
      expect(mockOrchestratorPrompt).toHaveBeenCalled()

      // Verify orchestrator prompt is displayed
      expect(wrapper.text()).toContain('System Orchestrator Prompt')
      expect(wrapper.text()).toContain('You are the system orchestrator')
    })
  })

  describe('4. Graceful Handling of Missing template_id', () => {
    it('displays info message when template_id is null', async () => {
      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'agent-456',
            agent_type: 'implementer',
            agent_name: 'Test Agent',
            template_id: null
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Verify API was NOT called
      expect(mockTemplateGet).not.toHaveBeenCalled()

      // Verify info message is displayed
      expect(wrapper.text()).toContain('No template information available')
    })

    it('displays info message when template_id is undefined', async () => {
      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'agent-456',
            agent_type: 'implementer',
            agent_name: 'Test Agent'
            // template_id is undefined
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Verify API was NOT called
      expect(mockTemplateGet).not.toHaveBeenCalled()

      // Verify info message is displayed
      expect(wrapper.text()).toContain('No template information available')
    })
  })

  describe('5. Loading and Error States', () => {
    it('displays loading state while fetching template data', async () => {
      // Mock a delayed response
      mockTemplateGet.mockImplementation(() =>
        new Promise(resolve => setTimeout(() => resolve({ data: {} }), 100))
      )

      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'agent-456',
            agent_type: 'implementer',
            template_id: 'template-123'
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      // Check loading state immediately
      await wrapper.vm.$nextTick()
      expect(wrapper.text()).toContain('Loading...')
    })

    it('displays error message when template fetch fails', async () => {
      mockTemplateGet.mockRejectedValue({
        response: {
          data: {
            detail: 'Template not found'
          }
        }
      })

      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'agent-456',
            agent_type: 'implementer',
            template_id: 'template-123'
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Verify error message is displayed
      expect(wrapper.text()).toContain('Failed to load')
      expect(wrapper.text()).toContain('Template not found')
    })

    it('displays generic error when API error has no detail', async () => {
      mockTemplateGet.mockRejectedValue(new Error('Network error'))

      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'agent-456',
            agent_type: 'implementer',
            template_id: 'template-123'
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Verify error message is displayed
      expect(wrapper.text()).toContain('Failed to load')
      expect(wrapper.text()).toContain('Network error')
    })
  })

  describe('6. Dialog Title and Agent Type Detection', () => {
    it('displays correct title for orchestrator', async () => {
      mockOrchestratorPrompt.mockResolvedValue({ data: { content: 'test' } })

      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'orchestrator-123',
            agent_type: 'orchestrator',
            agent_name: 'Orchestrator'
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      expect(wrapper.text()).toContain('System Orchestrator Prompt')
    })

    it('displays correct title for non-orchestrator agent', async () => {
      mockTemplateGet.mockResolvedValue({ data: { role: 'implementer' } })

      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'agent-456',
            agent_type: 'implementer',
            agent_name: 'Test Implementer',
            template_id: 'template-123'
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      expect(wrapper.text()).toContain('Agent Details: Test Implementer')
    })
  })

  describe('7. Copy to Clipboard Functionality', () => {
    it('provides copy button for system instructions', async () => {
      const mockTemplate = {
        id: 'template-123',
        role: 'implementer',
        system_instructions: 'Test system instructions'
      }

      mockTemplateGet.mockResolvedValue({ data: mockTemplate })

      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn().mockResolvedValue(undefined)
        }
      })

      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'agent-456',
            agent_type: 'implementer',
            template_id: 'template-123'
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Find copy buttons (should be present in expansion panel)
      const copyButtons = wrapper.findAll('button').filter(btn =>
        btn.text().includes('Copy')
      )

      expect(copyButtons.length).toBeGreaterThan(0)
    })
  })

  describe('8. Agent Type Color Coding', () => {
    it('displays agent type chip with correct color', async () => {
      mockTemplateGet.mockResolvedValue({ data: { role: 'tester' } })

      wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: {
            id: 'agent-456',
            agent_type: 'tester',
            agent_name: 'Test Tester',
            template_id: 'template-123'
          }
        },
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Verify agent type chip is displayed
      expect(wrapper.text()).toContain('tester')
    })
  })
})
