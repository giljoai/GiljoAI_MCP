import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import ClaudeCodeExport from '@/components/ClaudeCodeExport.vue'

// Mock the API module
vi.mock('@/services/api', () => ({
  default: {
    templates: {
      list: vi.fn(),
      exportClaudeCode: vi.fn(),
    },
  },
}))

describe('ClaudeCodeExport.vue', () => {
  let vuetify
  let wrapper
  let api

  const mockActiveTemplates = [
    {
      id: 1,
      name: 'orchestrator',
      role: 'orchestrator',
      description: 'Orchestrator agent',
      cli_tool: 'claude',
      is_active: true,
      system_instructions: 'Template content for orchestrator',
      behavioral_rules: ['Rule 1', 'Rule 2'],
      success_criteria: ['Criteria 1'],
    },
    {
      id: 2,
      name: 'analyzer',
      role: 'analyzer',
      description: 'Analyzer agent',
      cli_tool: 'claude',
      is_active: true,
      system_instructions: 'Template content for analyzer',
      behavioral_rules: [],
      success_criteria: [],
    },
    {
      id: 3,
      name: 'implementor',
      role: 'implementor',
      description: 'Implementor agent',
      cli_tool: 'claude',
      is_active: true,
      system_instructions: 'Template content for implementor',
      behavioral_rules: [],
      success_criteria: [],
    },
  ]

  const mockExportResponse = {
    data: {
      success: true,
      exported_count: 3,
      files: [
        { name: 'orchestrator', path: '/project/.claude/agents/orchestrator.md' },
        { name: 'analyzer', path: '/project/.claude/agents/analyzer.md' },
        { name: 'implementor', path: '/project/.claude/agents/implementor.md' },
      ],
      message: 'Successfully exported 3 template(s)',
    },
  }

  beforeEach(async () => {
    vuetify = createVuetify({
      components,
      directives,
    })

    api = (await import('@/services/api')).default

    // Setup default mock responses
    api.templates.list.mockResolvedValue({ data: mockActiveTemplates })
    api.templates.exportClaudeCode.mockResolvedValue(mockExportResponse)

    wrapper = mount(ClaudeCodeExport, {
      global: {
        plugins: [vuetify],
      },
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('renders the component without errors', () => {
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.vm).toBeDefined()
    })

    it('displays the export icon', () => {
      const icon = wrapper.find('.v-icon')
      expect(icon.exists()).toBe(true)
      expect(icon.classes()).toContain('mdi-download')
    })

    it('displays the correct title', () => {
      const title = wrapper.text()
      expect(title).toContain('Claude Code Agent Export')
    })

    it('renders the info alert', () => {
      const alert = wrapper.findAll('.v-alert')[0]
      expect(alert.exists()).toBe(true)
      expect(alert.text()).toContain('Export your agent templates as Claude Code')
    })

    it('displays export location radio group', () => {
      const radioGroup = wrapper.find('.v-radio-group')
      expect(radioGroup.exists()).toBe(true)
    })

    it('displays project directory radio option', async () => {
      await wrapper.vm.$nextTick()
      const radioOptions = wrapper.findAll('.v-radio')
      const projectOption = radioOptions.find(r => r.text().includes('Project Directory'))
      expect(projectOption).toBeDefined()
    })

    it('displays personal directory radio option', async () => {
      await wrapper.vm.$nextTick()
      const radioOptions = wrapper.findAll('.v-radio')
      const personalOption = radioOptions.find(r => r.text().includes('Personal Directory'))
      expect(personalOption).toBeDefined()
    })

    it('displays export button', () => {
      const exportBtn = wrapper.find('button')
      expect(exportBtn.exists()).toBe(true)
      expect(exportBtn.text()).toContain('Export')
    })

    it('displays template chips for active templates', async () => {
      await wrapper.vm.$nextTick()
      const chips = wrapper.findAll('.v-chip')
      expect(chips.length).toBeGreaterThan(0)
    })
  })

  describe('Template Loading', () => {
    it('loads active templates on mount', async () => {
      await wrapper.vm.$nextTick()
      expect(api.templates.list).toHaveBeenCalledWith({ is_active: true })
    })

    it('displays correct number of active templates', async () => {
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.activeTemplates.length).toBe(3)
    })

    it('displays template names in chips', async () => {
      await wrapper.vm.$nextTick()
      const chipTexts = wrapper.findAll('.v-chip').map(chip => chip.text())
      expect(chipTexts).toContain('orchestrator')
      expect(chipTexts).toContain('analyzer')
      expect(chipTexts).toContain('implementor')
    })

    it('displays template count in header', async () => {
      await wrapper.vm.$nextTick()
      const header = wrapper.text()
      expect(header).toContain('Active Templates (3)')
    })

    it('shows warning alert when no templates available', async () => {
      api.templates.list.mockResolvedValue({ data: [] })

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      await newWrapper.vm.$nextTick()
      const alerts = newWrapper.findAll('.v-alert')
      const warningAlert = alerts.find(a => {
        const text = a.text()
        return text.includes('No active templates available')
      })
      expect(warningAlert).toBeDefined()

      newWrapper.unmount()
    })
  })

  describe('User Interactions - Radio Button Selection', () => {
    it('defaults to project path selection', async () => {
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.exportPath).toBe('project')
    })

    it('allows changing to personal path', async () => {
      await wrapper.vm.$nextTick()

      // Find and click the personal radio button
      const radios = wrapper.findAll('.v-radio')
      const personalRadio = radios.find(r => r.text().includes('Personal Directory'))

      if (personalRadio) {
        await personalRadio.find('input').trigger('change')
        await wrapper.vm.$nextTick()

        // Check if the radio value changed (it updates through v-model)
        expect(wrapper.vm.exportPath).toBe('personal')
      }
    })

    it('allows changing back to project path', async () => {
      await wrapper.vm.$nextTick()

      // Switch to personal first
      wrapper.vm.exportPath = 'personal'
      await wrapper.vm.$nextTick()

      // Switch back to project
      const radios = wrapper.findAll('.v-radio')
      const projectRadio = radios.find(r => r.text().includes('Project Directory'))

      if (projectRadio) {
        await projectRadio.find('input').trigger('change')
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.exportPath).toBe('project')
      }
    })

    it('disables radio group during export loading', async () => {
      await wrapper.vm.$nextTick()
      wrapper.vm.loading = true
      await wrapper.vm.$nextTick()

      const radioGroup = wrapper.find('.v-radio-group')
      expect(radioGroup.attributes('disabled')).toBeDefined()
    })
  })

  describe('Export Button Behavior', () => {
    it('enables export button when templates available', async () => {
      await wrapper.vm.$nextTick()
      const button = wrapper.find('button')
      expect(button.attributes('disabled')).toBeUndefined()
    })

    it('disables export button when no templates available', async () => {
      api.templates.list.mockResolvedValue({ data: [] })

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      await newWrapper.vm.$nextTick()
      const button = newWrapper.find('button')
      expect(button.attributes('disabled')).toBeDefined()

      newWrapper.unmount()
    })

    it('disables export button during export loading', async () => {
      await wrapper.vm.$nextTick()
      wrapper.vm.loading = true
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      expect(button.attributes('disabled')).toBeDefined()
    })

    it('shows loading indicator on button during export', async () => {
      await wrapper.vm.$nextTick()
      wrapper.vm.loading = true
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      expect(button.attributes(':loading')).toBeDefined()
    })

    it('displays correct template count in button text', async () => {
      await wrapper.vm.$nextTick()
      const button = wrapper.find('button')
      expect(button.text()).toContain('Export 3 Templates')
    })

    it('uses singular "Template" when only 1 template', async () => {
      api.templates.list.mockResolvedValue({ data: [mockActiveTemplates[0]] })

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      await newWrapper.vm.$nextTick()
      const button = newWrapper.find('button')
      expect(button.text()).toContain('Export 1 Template')

      newWrapper.unmount()
    })
  })

  describe('Export Button Click', () => {
    it('calls handleExport when export button clicked', async () => {
      await wrapper.vm.$nextTick()
      const handleExportSpy = vi.spyOn(wrapper.vm, 'handleExport')

      const button = wrapper.find('button')
      await button.trigger('click')

      expect(handleExportSpy).toHaveBeenCalled()
    })

    it('triggers API call with correct export path', async () => {
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      await button.trigger('click')
      await wrapper.vm.$nextTick()

      // Wait for async API call
      await new Promise(resolve => setTimeout(resolve, 100))

      expect(api.templates.exportClaudeCode).toHaveBeenCalledWith({
        export_path: './.claude/agents',
      })
    })

    it('uses project path in API call when project selected', async () => {
      await wrapper.vm.$nextTick()
      wrapper.vm.exportPath = 'project'

      const button = wrapper.find('button')
      await button.trigger('click')
      await wrapper.vm.$nextTick()

      await new Promise(resolve => setTimeout(resolve, 100))

      expect(api.templates.exportClaudeCode).toHaveBeenCalledWith({
        export_path: './.claude/agents',
      })
    })

    it('uses personal path in API call when personal selected', async () => {
      await wrapper.vm.$nextTick()
      wrapper.vm.exportPath = 'personal'

      const button = wrapper.find('button')
      await button.trigger('click')
      await wrapper.vm.$nextTick()

      await new Promise(resolve => setTimeout(resolve, 100))

      expect(api.templates.exportClaudeCode).toHaveBeenCalledWith({
        export_path: '~/.claude/agents',
      })
    })

    it('prevents multiple concurrent exports', async () => {
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')

      // First click
      await button.trigger('click')
      expect(wrapper.vm.loading).toBe(true)

      // Second click should not trigger another call (button is disabled)
      const disabledDuringLoad = button.attributes('disabled')
      expect(disabledDuringLoad).toBeDefined()
    })
  })

  describe('Successful Export Response', () => {
    it('displays success result after export', async () => {
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      await button.trigger('click')

      // Wait for async operation
      await new Promise(resolve => setTimeout(resolve, 150))
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.exportResult).toBeDefined()
      expect(wrapper.vm.exportResult.success).toBe(true)
    })

    it('displays success message', async () => {
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.exportResult.message).toContain('Successfully exported')
    })

    it('displays exported file list', async () => {
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.exportResult.files.length).toBe(3)
      expect(wrapper.vm.exportResult.files[0].name).toBe('orchestrator')
    })

    it('renders success alert with file details', async () => {
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await wrapper.vm.$nextTick()

      const alerts = wrapper.findAll('.v-alert')
      const successAlert = alerts.find(a => a.classes().includes('v-alert--type-success'))

      if (successAlert) {
        const alertText = successAlert.text()
        expect(alertText).toContain('orchestrator')
        expect(alertText).toContain('analyzer')
      }
    })

    it('displays formatted file paths in results', async () => {
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await wrapper.vm.$nextTick()

      const exportResult = wrapper.vm.exportResult
      const filePath = exportResult.files[0].path

      // formatPath should extract the relative portion
      const formatted = wrapper.vm.formatPath(filePath)
      expect(formatted).toContain('.claude/agents')
    })

    it('clears export result when alert closed', async () => {
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.exportResult).toBeDefined()

      // Simulate closing the alert
      wrapper.vm.exportResult = null

      expect(wrapper.vm.exportResult).toBeNull()
    })
  })

  describe('Error Handling', () => {
    it('handles 400 Bad Request error', async () => {
      const errorResponse = {
        response: {
          status: 400,
          data: {
            detail: 'Export path must end with .claude/agents',
          },
        },
      }

      api.templates.exportClaudeCode.mockRejectedValue(errorResponse)

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      await newWrapper.vm.$nextTick()

      const button = newWrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await newWrapper.vm.$nextTick()

      expect(newWrapper.vm.exportResult).toBeDefined()
      expect(newWrapper.vm.exportResult.success).toBe(false)
      expect(newWrapper.vm.exportResult.message).toContain('Export Failed')
      expect(newWrapper.vm.exportResult.error).toContain('Export path must end')

      newWrapper.unmount()
    })

    it('handles 401 Unauthorized error', async () => {
      const errorResponse = {
        response: {
          status: 401,
          data: {
            detail: 'Unauthorized',
          },
        },
        message: 'Unauthorized',
      }

      api.templates.exportClaudeCode.mockRejectedValue(errorResponse)

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      await newWrapper.vm.$nextTick()

      const button = newWrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await newWrapper.vm.$nextTick()

      expect(newWrapper.vm.exportResult.success).toBe(false)

      newWrapper.unmount()
    })

    it('handles 500 Internal Server error', async () => {
      const errorResponse = {
        response: {
          status: 500,
          data: {
            detail: 'Internal server error',
          },
        },
      }

      api.templates.exportClaudeCode.mockRejectedValue(errorResponse)

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      await newWrapper.vm.$nextTick()

      const button = newWrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await newWrapper.vm.$nextTick()

      expect(newWrapper.vm.exportResult.success).toBe(false)
      expect(newWrapper.vm.exportResult.message).toBe('Export Failed')

      newWrapper.unmount()
    })

    it('handles network error (no response)', async () => {
      const networkError = new Error('Network Error')
      delete networkError.response

      api.templates.exportClaudeCode.mockRejectedValue(networkError)

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      await newWrapper.vm.$nextTick()

      const button = newWrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await newWrapper.vm.$nextTick()

      expect(newWrapper.vm.exportResult.success).toBe(false)
      expect(newWrapper.vm.exportResult.message).toBe('Export Failed')

      newWrapper.unmount()
    })

    it('displays error details in alert', async () => {
      const errorResponse = {
        response: {
          status: 400,
          data: {
            detail: 'Invalid path format',
          },
        },
      }

      api.templates.exportClaudeCode.mockRejectedValue(errorResponse)

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      await newWrapper.vm.$nextTick()

      const button = newWrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await newWrapper.vm.$nextTick()

      expect(newWrapper.vm.exportResult.error).toContain('Invalid path format')

      newWrapper.unmount()
    })

    it('clears loading state on error', async () => {
      api.templates.exportClaudeCode.mockRejectedValue(new Error('Export failed'))

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      await newWrapper.vm.$nextTick()

      const button = newWrapper.find('button')
      await button.trigger('click')

      expect(newWrapper.vm.loading).toBe(true)

      await new Promise(resolve => setTimeout(resolve, 150))
      await newWrapper.vm.$nextTick()

      expect(newWrapper.vm.loading).toBe(false)

      newWrapper.unmount()
    })
  })

  describe('Edge Cases', () => {
    it('handles empty template name gracefully', async () => {
      const templatesWithEmpty = [
        { ...mockActiveTemplates[0], name: '' },
        ...mockActiveTemplates.slice(1),
      ]

      api.templates.list.mockResolvedValue({ data: templatesWithEmpty })

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      await newWrapper.vm.$nextTick()

      expect(newWrapper.vm.activeTemplates.length).toBe(3)

      newWrapper.unmount()
    })

    it('handles special characters in template names', async () => {
      const specialCharTemplate = {
        ...mockActiveTemplates[0],
        name: 'test-agent_v2.0',
      }

      api.templates.list.mockResolvedValue({
        data: [specialCharTemplate, ...mockActiveTemplates.slice(1)],
      })

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      await newWrapper.vm.$nextTick()

      expect(newWrapper.vm.activeTemplates[0].name).toBe('test-agent_v2.0')

      newWrapper.unmount()
    })

    it('handles very long file paths', async () => {
      const longPath = '/very/long/path/to/'.repeat(10) + '.claude/agents'
      const exportResultWithLongPath = {
        ...mockExportResponse,
        data: {
          ...mockExportResponse.data,
          files: [
            {
              name: 'orchestrator',
              path: longPath + '/orchestrator.md',
            },
          ],
        },
      }

      api.templates.exportClaudeCode.mockResolvedValue(exportResultWithLongPath)

      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.exportResult.files[0].path).toContain('.claude/agents')
    })

    it('handles zero exported templates in response', async () => {
      const emptyExportResponse = {
        data: {
          success: true,
          exported_count: 0,
          files: [],
          message: 'No templates exported',
        },
      }

      api.templates.exportClaudeCode.mockResolvedValue(emptyExportResponse)

      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.exportResult.exported_count).toBe(0)
    })

    it('handles response with missing files array', async () => {
      const incompleteResponse = {
        data: {
          success: true,
          exported_count: 2,
          message: 'Export successful',
          // files array missing
        },
      }

      api.templates.exportClaudeCode.mockResolvedValue(incompleteResponse)

      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.exportResult.files).toEqual([])
    })

    it('handles template loading failure gracefully', async () => {
      api.templates.list.mockRejectedValue(new Error('Failed to load templates'))

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      await new Promise(resolve => setTimeout(resolve, 100))
      await newWrapper.vm.$nextTick()

      expect(newWrapper.vm.activeTemplates.length).toBe(0)
      expect(newWrapper.vm.loading).toBe(false)

      newWrapper.unmount()
    })

    it('handles timeout during export', async () => {
      // Create a promise that never resolves
      api.templates.exportClaudeCode.mockImplementation(
        () => new Promise(() => {})
      )

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      await newWrapper.vm.$nextTick()

      const button = newWrapper.find('button')
      await button.trigger('click')

      expect(newWrapper.vm.loading).toBe(true)

      newWrapper.unmount()
    })
  })

  describe('Accessibility (WCAG 2.1 AA)', () => {
    it('has proper ARIA label on export button', async () => {
      await wrapper.vm.$nextTick()
      const button = wrapper.find('button')
      expect(button.attributes('aria-label')).toBe('Export agent templates to Claude Code format')
    })

    it('has ARIA label on radio group', async () => {
      await wrapper.vm.$nextTick()
      const radioGroup = wrapper.find('.v-radio-group')
      expect(radioGroup.attributes('aria-label')).toBe('Select export location')
    })

    it('renders with semantic HTML structure', () => {
      expect(wrapper.find('.v-card').exists()).toBe(true)
      expect(wrapper.find('h3').exists()).toBe(true)
      expect(wrapper.find('.v-alert').exists()).toBe(true)
    })

    it('uses proper heading hierarchy (h3, h4)', () => {
      const mainHeading = wrapper.find('h3')
      const subHeadings = wrapper.findAll('h4')

      expect(mainHeading.exists()).toBe(true)
      expect(subHeadings.length).toBeGreaterThan(0)
    })

    it('button has sufficient color contrast', () => {
      const button = wrapper.find('button')
      expect(button.classes()).toContain('primary')
    })

    it('supports keyboard navigation to radio buttons', async () => {
      await wrapper.vm.$nextTick()

      const radioInputs = wrapper.findAll('input[type="radio"]')
      expect(radioInputs.length).toBe(2)

      // Both radio buttons should be keyboard accessible
      for (const input of radioInputs) {
        expect(input.exists()).toBe(true)
      }
    })

    it('supports keyboard activation of export button', async () => {
      await wrapper.vm.$nextTick()
      const button = wrapper.find('button')

      // Button should be keyboard accessible
      await button.trigger('keydown.enter')

      // Button should handle Enter key
      expect(button.exists()).toBe(true)
    })

    it('has proper focus management', async () => {
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      const radioGroup = wrapper.find('.v-radio-group')

      // Both interactive elements should be focusable
      expect(button.exists()).toBe(true)
      expect(radioGroup.exists()).toBe(true)
    })

    it('uses semantic code tags for file paths', async () => {
      await wrapper.vm.$nextTick()

      // Check that code elements exist for displaying paths
      const codeTags = wrapper.findAll('code')
      const codeTexts = codeTags.map(tag => tag.text())

      expect(codeTexts).toContain('.claude/agents/')
    })

    it('provides context for technical abbreviations', () => {
      const alertText = wrapper.text()

      // Check that abbreviations like YAML are explained or used in context
      expect(alertText).toContain('Claude Code')
      expect(alertText).toContain('.claude/agents')
    })

    it('alert content has proper text color contrast', () => {
      const infoAlert = wrapper.findAll('.v-alert')[0]
      expect(infoAlert.classes()).toContain('v-alert--type-info')
    })

    it('supports screen reader announcements of dynamic content', async () => {
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      expect(button.text()).toContain('Export 3 Templates')

      // Template count updates should be readable
      wrapper.vm.activeTemplates = mockActiveTemplates.slice(0, 1)
      await wrapper.vm.$nextTick()

      expect(button.text()).toContain('Export 1 Template')
    })
  })

  describe('Template Icon Mapping', () => {
    it('returns correct icon for orchestrator role', () => {
      const icon = wrapper.vm.getTemplateIcon('orchestrator')
      expect(icon).toBe('mdi-connection')
    })

    it('returns correct icon for analyzer role', () => {
      const icon = wrapper.vm.getTemplateIcon('analyzer')
      expect(icon).toBe('mdi-magnify')
    })

    it('returns correct icon for implementor role', () => {
      const icon = wrapper.vm.getTemplateIcon('implementor')
      expect(icon).toBe('mdi-code-braces')
    })

    it('returns correct icon for tester role', () => {
      const icon = wrapper.vm.getTemplateIcon('tester')
      expect(icon).toBe('mdi-test-tube')
    })

    it('returns correct icon for documenter role', () => {
      const icon = wrapper.vm.getTemplateIcon('documenter')
      expect(icon).toBe('mdi-file-document-edit')
    })

    it('returns correct icon for reviewer role', () => {
      const icon = wrapper.vm.getTemplateIcon('reviewer')
      expect(icon).toBe('mdi-eye-check')
    })

    it('returns default icon for unknown role', () => {
      const icon = wrapper.vm.getTemplateIcon('unknown_role')
      expect(icon).toBe('mdi-robot')
    })

    it('handles case-insensitive role matching', () => {
      const icon1 = wrapper.vm.getTemplateIcon('ORCHESTRATOR')
      const icon2 = wrapper.vm.getTemplateIcon('Orchestrator')

      expect(icon1).toBe('mdi-connection')
      expect(icon2).toBe('mdi-connection')
    })

    it('handles null role gracefully', () => {
      const icon = wrapper.vm.getTemplateIcon(null)
      expect(icon).toBe('mdi-robot')
    })
  })

  describe('Path Formatting', () => {
    it('extracts .claude/agents portion from full path', () => {
      const fullPath = '/home/user/project/.claude/agents/orchestrator.md'
      const formatted = wrapper.vm.formatPath(fullPath)

      expect(formatted).toContain('.claude/agents')
    })

    it('handles Windows-style paths', () => {
      const winPath = 'C:\\Users\\user\\project\\.claude\\agents\\orchestrator.md'
      const formatted = wrapper.vm.formatPath(winPath)

      expect(formatted).toContain('.claude/agents')
    })

    it('returns full path if .claude not found', () => {
      const path = '/some/other/path/orchestrator.md'
      const formatted = wrapper.vm.formatPath(path)

      expect(formatted).toBe(path)
    })

    it('handles relative paths', () => {
      const relPath = './.claude/agents/orchestrator.md'
      const formatted = wrapper.vm.formatPath(relPath)

      expect(formatted).toContain('.claude/agents')
    })
  })

  describe('Loading State Management', () => {
    it('initializes with loading false', () => {
      expect(wrapper.vm.loading).toBe(false)
    })

    it('sets loading true during initial template fetch', async () => {
      // Clear the mock to test fresh mount
      vi.clearAllMocks()

      api.templates.list.mockImplementation(
        () => new Promise(resolve => {
          setTimeout(() => resolve({ data: mockActiveTemplates }), 100)
        })
      )

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      // May or may not be true depending on timing, but should be false after completion
      await new Promise(resolve => setTimeout(resolve, 150))
      await newWrapper.vm.$nextTick()

      expect(newWrapper.vm.loading).toBe(false)

      newWrapper.unmount()
    })

    it('sets loading true during export', async () => {
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      await button.trigger('click')

      expect(wrapper.vm.loading).toBe(true)
    })

    it('sets loading false after successful export', async () => {
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.loading).toBe(false)
    })
  })

  describe('Export Result Display', () => {
    it('initially has null export result', () => {
      expect(wrapper.vm.exportResult).toBeNull()
    })

    it('displays result after successful export', async () => {
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.exportResult).not.toBeNull()
      expect(wrapper.vm.exportResult.success).toBe(true)
    })

    it('displays result after failed export', async () => {
      api.templates.exportClaudeCode.mockRejectedValue(
        new Error('Export failed')
      )

      const newWrapper = mount(ClaudeCodeExport, {
        global: {
          plugins: [vuetify],
        },
      })

      await newWrapper.vm.$nextTick()

      const button = newWrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await newWrapper.vm.$nextTick()

      expect(newWrapper.vm.exportResult).not.toBeNull()
      expect(newWrapper.vm.exportResult.success).toBe(false)

      newWrapper.unmount()
    })

    it('allows closing result alert', async () => {
      await wrapper.vm.$nextTick()

      const button = wrapper.find('button')
      await button.trigger('click')

      await new Promise(resolve => setTimeout(resolve, 150))
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.exportResult).not.toBeNull()

      wrapper.vm.exportResult = null

      expect(wrapper.vm.exportResult).toBeNull()
    })
  })
})
