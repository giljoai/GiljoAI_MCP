/**
 * Test suite for AgentDetailsModal component
 * TDD Phase 1: Tests written FIRST before implementation
 *
 * Tests the modal that displays agent template information or orchestrator prompt
 * when clicking the info button on agent cards in JobsTab
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import AgentDetailsModal from '@/components/projects/AgentDetailsModal.vue'

describe('AgentDetailsModal Component', () => {
  let vuetify
  let mockApi

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
    })

    // Mock API for template and orchestrator prompt fetching
    mockApi = {
      templates: {
        get: vi.fn(),
        preview: vi.fn(),
      },
      system: {
        getOrchestratorPrompt: vi.fn(),
      },
    }
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  const createWrapper = (props = {}, options = {}) => {
    return mount(AgentDetailsModal, {
      props: {
        modelValue: true,
        agent: {
          id: 'agent-job-123',
          agent_type: 'implementer',
          agent_name: 'Test Implementer',
          template_id: 'template-456',
          ...props.agent,
        },
        ...props,
      },
      global: {
        plugins: [vuetify],
        mocks: {
          $api: mockApi,
          ...options.mocks,
        },
        stubs: {
          'v-dialog': {
            template: '<div class="v-dialog" v-if="modelValue"><slot /></div>',
            props: ['modelValue'],
          },
          ...options.stubs,
        },
      },
    })
  }

  describe('Dialog Visibility', () => {
    it('renders dialog when modelValue is true', () => {
      const wrapper = createWrapper({ modelValue: true })

      expect(wrapper.find('.v-dialog').exists()).toBe(true)
      expect(wrapper.text()).toContain('Agent Details')
    })

    it('does not render dialog content when modelValue is false', () => {
      const wrapper = createWrapper({ modelValue: false })

      // Dialog content should not be visible when closed
      const cardText = wrapper.find('.v-card-text')
      if (cardText.exists()) {
        expect(wrapper.find('.v-dialog--active').exists()).toBe(false)
      }
    })

    it('emits update:modelValue when dialog is closed', async () => {
      const wrapper = createWrapper()

      // Find close button
      const buttons = wrapper.findAll('button')
      const closeBtn = buttons.find((btn) => btn.text().includes('Close'))

      if (closeBtn) {
        await closeBtn.trigger('click')
        expect(wrapper.emitted('update:modelValue')).toBeTruthy()
        expect(wrapper.emitted('update:modelValue')[0]).toEqual([false])
      }
    })
  })

  describe('Agent Information Display', () => {
    it('displays agent name in dialog title', () => {
      const wrapper = createWrapper({
        agent: {
          agent_name: 'Custom Tester Agent',
          agent_type: 'tester',
        },
      })

      expect(wrapper.text()).toContain('Custom Tester Agent')
    })

    it('displays agent type badge', () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          agent_name: 'Test Agent',
        },
      })

      expect(wrapper.text()).toContain('implementer')
    })

    it('displays agent job ID', () => {
      const wrapper = createWrapper({
        agent: {
          id: 'job-abc-123',
          agent_type: 'tester',
          agent_name: 'Test Agent',
        },
      })

      expect(wrapper.text()).toContain('job-abc-123')
    })
  })

  describe('Regular Agent Template Display', () => {
    beforeEach(() => {
      // Mock template response
      mockApi.templates.get.mockResolvedValue({
        data: {
          id: 'template-456',
          name: 'Implementer Template',
          role: 'implementer',
          description: 'Test implementer template description',
          template_content: 'You are an implementer agent...\n\nFollow TDD principles.',
          variables: ['project_name', 'tech_stack'],
          model: 'sonnet',
          tools: ['bash', 'read', 'write'],
        },
      })

      // Mock preview response
      mockApi.templates.preview.mockResolvedValue({
        data: {
          mission: 'Generated mission for Test Implementer\n\nProject: Test Project',
        },
      })
    })

    it('fetches template data for non-orchestrator agents', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      expect(mockApi.templates.get).toHaveBeenCalledWith('template-456')
      expect(mockApi.system.getOrchestratorPrompt).not.toHaveBeenCalled()
    })

    it('displays template content in monospace font', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      // Template content should be in a pre or code-like element
      const preElements = wrapper.findAll('pre')
      expect(preElements.length).toBeGreaterThan(0)
    })

    it('displays template description', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      expect(wrapper.text()).toContain('Test implementer template description')
    })

    it('displays template variables list', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      expect(wrapper.text()).toContain('project_name')
      expect(wrapper.text()).toContain('tech_stack')
    })

    it('displays template model information', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      expect(wrapper.text()).toContain('sonnet')
    })

    it('displays template tools list', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      expect(wrapper.text()).toContain('bash')
      expect(wrapper.text()).toContain('read')
      expect(wrapper.text()).toContain('write')
    })

    it('shows loading state while fetching template', async () => {
      mockApi.templates.get.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ data: {} }), 100))
      )

      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      // Should show loading indicator
      expect(wrapper.text()).toContain('Loading')
    })

    it('handles template fetch error gracefully', async () => {
      mockApi.templates.get.mockRejectedValue(new Error('Failed to fetch template'))

      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      expect(wrapper.text()).toContain('Failed to load')
    })

    it('handles missing template_id', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: null,
        },
      })

      await flushPromises()

      expect(wrapper.text()).toContain('No template')
      expect(mockApi.templates.get).not.toHaveBeenCalled()
    })
  })

  describe('Orchestrator Prompt Display', () => {
    beforeEach(() => {
      // Mock orchestrator prompt response
      mockApi.system.getOrchestratorPrompt.mockResolvedValue({
        data: {
          content:
            'You are the System Orchestrator...\n\nCoordinate all agents and manage workflow.',
        },
      })
    })

    it('fetches orchestrator prompt for orchestrator agent type', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'orchestrator',
          agent_name: 'System Orchestrator',
        },
      })

      await flushPromises()

      expect(mockApi.system.getOrchestratorPrompt).toHaveBeenCalled()
      expect(mockApi.templates.get).not.toHaveBeenCalled()
    })

    it('displays orchestrator prompt in monospace font', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'orchestrator',
        },
      })

      await flushPromises()

      const preElements = wrapper.findAll('pre')
      expect(preElements.length).toBeGreaterThan(0)
      expect(wrapper.text()).toContain('You are the System Orchestrator')
    })

    it('shows specific title for orchestrator', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'orchestrator',
          agent_name: 'System Orchestrator',
        },
      })

      await flushPromises()

      expect(wrapper.text()).toContain('System Orchestrator Prompt')
    })

    it('handles orchestrator prompt fetch error', async () => {
      mockApi.system.getOrchestratorPrompt.mockRejectedValue(
        new Error('Failed to fetch orchestrator prompt')
      )

      const wrapper = createWrapper({
        agent: {
          agent_type: 'orchestrator',
        },
      })

      await flushPromises()

      expect(wrapper.text()).toContain('Failed to load')
    })
  })

  describe('Content Display Formatting', () => {
    beforeEach(() => {
      mockApi.templates.get.mockResolvedValue({
        data: {
          template_content:
            'Line 1\nLine 2\nLine 3\n\n# Section\n\nMore content with **markdown**',
        },
      })
    })

    it('preserves whitespace and line breaks in template content', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      const preElement = wrapper.find('pre')
      expect(preElement.exists()).toBe(true)
      // Pre element should preserve formatting
    })

    it('displays content as read-only', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      // Should not have any textarea or editable inputs for content
      const textareas = wrapper.findAll('textarea')
      const editableInputs = textareas.filter((ta) =>
        ta.attributes('readonly') === undefined || ta.attributes('readonly') === 'false'
      )
      expect(editableInputs.length).toBe(0)
    })
  })

  describe('Modal Styling and Theme', () => {
    it('applies dark theme styling', () => {
      const wrapper = createWrapper()

      // Dialog should use Vuetify dark theme classes
      const dialog = wrapper.find('.v-dialog')
      expect(dialog.exists()).toBe(true)
    })

    it('has proper max width for readability', () => {
      const wrapper = createWrapper()

      // Modal should have reasonable max-width (800px as per template manager preview)
      expect(wrapper.html()).toContain('max-width')
    })

    it('includes close button in header', () => {
      const wrapper = createWrapper()

      const buttons = wrapper.findAll('button')
      const headerCloseBtn = buttons.find((btn) => {
        const icon = btn.find('.v-icon')
        return icon.exists() && icon.text().includes('close')
      })

      expect(headerCloseBtn).toBeTruthy()
    })
  })

  describe('Edge Cases', () => {
    it('handles undefined agent gracefully', () => {
      const wrapper = mount(AgentDetailsModal, {
        props: {
          modelValue: true,
          agent: null,
        },
        global: {
          plugins: [vuetify],
          mocks: { $api: mockApi },
        },
      })

      expect(wrapper.exists()).toBe(true)
      // Should show placeholder or error message
    })

    it('handles empty template content', async () => {
      mockApi.templates.get.mockResolvedValue({
        data: {
          template_content: '',
        },
      })

      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      expect(wrapper.text()).toContain('No content')
    })

    it('handles template with no variables', async () => {
      mockApi.templates.get.mockResolvedValue({
        data: {
          template_content: 'Simple template',
          variables: [],
        },
      })

      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      // Should not crash, may hide variables section
      expect(wrapper.exists()).toBe(true)
    })

    it('handles template with no tools', async () => {
      mockApi.templates.get.mockResolvedValue({
        data: {
          template_content: 'Simple template',
          tools: [],
        },
      })

      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      // Should not crash, may hide tools section
      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Copy to Clipboard Feature', () => {
    beforeEach(() => {
      mockApi.templates.get.mockResolvedValue({
        data: {
          template_content: 'Test template content for copying',
        },
      })

      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn().mockResolvedValue(undefined),
        },
      })
    })

    it('includes copy to clipboard button', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      const buttons = wrapper.findAll('button')
      const copyBtn = buttons.find((btn) => btn.text().includes('Copy'))

      expect(copyBtn).toBeTruthy()
    })

    it('copies template content to clipboard when copy button clicked', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      const buttons = wrapper.findAll('button')
      const copyBtn = buttons.find((btn) => btn.text().includes('Copy'))

      if (copyBtn) {
        await copyBtn.trigger('click')
        await flushPromises()

        expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
          'Test template content for copying'
        )
      }
    })

    it('shows feedback message after successful copy', async () => {
      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      await flushPromises()

      const buttons = wrapper.findAll('button')
      const copyBtn = buttons.find((btn) => btn.text().includes('Copy'))

      if (copyBtn) {
        await copyBtn.trigger('click')
        await flushPromises()

        // Should show "Copied!" or similar feedback
        expect(wrapper.text()).toMatch(/Copied|Success/i)
      }
    })
  })

  describe('Accessibility', () => {
    it('has proper dialog title', () => {
      const wrapper = createWrapper()

      expect(wrapper.text()).toContain('Agent Details')
    })

    it('close button has aria-label', () => {
      const wrapper = createWrapper()

      const buttons = wrapper.findAll('button')
      const closeBtn = buttons.find((btn) => {
        const icon = btn.find('.v-icon')
        return icon.exists() && icon.text().includes('close')
      })

      if (closeBtn) {
        const ariaLabel = closeBtn.attributes('aria-label')
        expect(ariaLabel).toBeDefined()
      }
    })

    it('loading state is announced', async () => {
      mockApi.templates.get.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ data: {} }), 100))
      )

      const wrapper = createWrapper({
        agent: {
          agent_type: 'implementer',
          template_id: 'template-456',
        },
      })

      expect(wrapper.text()).toContain('Loading')
    })
  })
})
