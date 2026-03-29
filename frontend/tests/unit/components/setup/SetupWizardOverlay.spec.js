/**
 * Unit tests for SetupWizardOverlay component (Handover 0855c)
 * Covers rendering, progress bar, tool selection, navigation, and dismiss behavior.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import SetupWizardOverlay from '@/components/setup/SetupWizardOverlay.vue'

const vuetify = createVuetify({ components, directives })

function mountOverlay(props = {}) {
  return mount(SetupWizardOverlay, {
    props: {
      modelValue: true,
      currentStep: 0,
      selectedTools: [],
      ...props,
    },
    global: {
      plugins: [vuetify],
      stubs: {
        Teleport: true,
      },
    },
  })
}

describe('SetupWizardOverlay', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // -------------------------------------------------------------------
  // Rendering
  // -------------------------------------------------------------------
  describe('Rendering', () => {
    it('renders the overlay when modelValue is true', () => {
      const wrapper = mountOverlay({ modelValue: true })

      expect(wrapper.find('.setup-wizard-overlay').exists()).toBe(true)
    })

    it('does not render the overlay when modelValue is false', () => {
      const wrapper = mountOverlay({ modelValue: false })

      expect(wrapper.find('.setup-wizard-overlay').exists()).toBe(false)
    })

    it('displays the title "Setup GiljoAI MCP"', () => {
      const wrapper = mountOverlay()

      expect(wrapper.find('.setup-wizard-title').text()).toBe('Setup GiljoAI MCP')
    })

    it('renders all 4 step labels in the progress bar', () => {
      const wrapper = mountOverlay()
      const labels = wrapper.findAll('.step-label')

      expect(labels).toHaveLength(4)
      expect(labels[0].text()).toBe('Choose Tools')
      expect(labels[1].text()).toBe('Connect')
      expect(labels[2].text()).toBe('Install')
      expect(labels[3].text()).toBe('Launch')
    })

    it('renders 3 tool cards on step 0', () => {
      const wrapper = mountOverlay({ currentStep: 0 })
      const toolCards = wrapper.findAll('.tool-card')

      expect(toolCards).toHaveLength(3)
    })

    it('displays tool names and providers', () => {
      const wrapper = mountOverlay()
      const names = wrapper.findAll('.tool-name')
      const providers = wrapper.findAll('.tool-provider')

      expect(names[0].text()).toBe('Claude Code')
      expect(names[1].text()).toBe('Codex CLI')
      expect(names[2].text()).toBe('Gemini CLI')

      expect(providers[0].text()).toBe('by Anthropic')
      expect(providers[1].text()).toBe('by OpenAI')
      expect(providers[2].text()).toBe('by Google')
    })
  })

  // -------------------------------------------------------------------
  // Progress bar
  // -------------------------------------------------------------------
  describe('Progress bar', () => {
    it('marks the active step with the --active class', () => {
      const wrapper = mountOverlay({ currentStep: 0 })
      const circles = wrapper.findAll('.step-circle')

      expect(circles[0].classes()).toContain('step-circle--active')
      expect(circles[0].classes()).not.toContain('step-circle--future')
    })

    it('marks the active step label with --active class', () => {
      const wrapper = mountOverlay({ currentStep: 0 })
      const labels = wrapper.findAll('.step-label')

      expect(labels[0].classes()).toContain('step-label--active')
    })

    it('marks completed steps with --completed class', () => {
      const wrapper = mountOverlay({ currentStep: 2 })
      const circles = wrapper.findAll('.step-circle')

      expect(circles[0].classes()).toContain('step-circle--completed')
      expect(circles[1].classes()).toContain('step-circle--completed')
      expect(circles[2].classes()).toContain('step-circle--active')
    })

    it('marks future steps with --future class', () => {
      const wrapper = mountOverlay({ currentStep: 0 })
      const circles = wrapper.findAll('.step-circle')

      expect(circles[1].classes()).toContain('step-circle--future')
      expect(circles[2].classes()).toContain('step-circle--future')
      expect(circles[3].classes()).toContain('step-circle--future')
    })

    it('shows completed connector fill for steps before current', () => {
      const wrapper = mountOverlay({ currentStep: 2 })
      const connectorFills = wrapper.findAll('.step-connector-fill')

      expect(connectorFills[0].classes()).toContain('step-connector-fill--completed')
      expect(connectorFills[1].classes()).toContain('step-connector-fill--completed')
      expect(connectorFills[2].classes()).not.toContain('step-connector-fill--completed')
    })
  })

  // -------------------------------------------------------------------
  // Tool selection
  // -------------------------------------------------------------------
  describe('Tool selection', () => {
    it('selects a tool when its card is clicked', async () => {
      const wrapper = mountOverlay()
      const toolCards = wrapper.findAll('.tool-card')

      await toolCards[0].trigger('click')

      expect(toolCards[0].attributes('aria-checked')).toBe('true')
    })

    it('deselects a tool when its selected card is clicked again', async () => {
      const wrapper = mountOverlay()
      const toolCards = wrapper.findAll('.tool-card')

      await toolCards[0].trigger('click')
      expect(toolCards[0].attributes('aria-checked')).toBe('true')

      await toolCards[0].trigger('click')
      expect(toolCards[0].attributes('aria-checked')).toBe('false')
    })

    it('allows multiple tools to be selected simultaneously', async () => {
      const wrapper = mountOverlay()
      const toolCards = wrapper.findAll('.tool-card')

      await toolCards[0].trigger('click')
      await toolCards[2].trigger('click')

      expect(toolCards[0].attributes('aria-checked')).toBe('true')
      expect(toolCards[1].attributes('aria-checked')).toBe('false')
      expect(toolCards[2].attributes('aria-checked')).toBe('true')
    })

    it('applies --smooth-border-color style to selected cards', async () => {
      const wrapper = mountOverlay()
      const toolCards = wrapper.findAll('.tool-card')

      await toolCards[0].trigger('click')

      expect(toolCards[0].attributes('style')).toContain('--smooth-border-color: #ffc300')
    })

    it('does not apply --smooth-border-color to unselected cards', () => {
      const wrapper = mountOverlay()
      const toolCards = wrapper.findAll('.tool-card')

      const style = toolCards[0].attributes('style') || ''
      expect(style).not.toContain('--smooth-border-color')
    })

    it('initializes with selectedTools prop', () => {
      const wrapper = mountOverlay({ selectedTools: ['codex_cli'] })
      const toolCards = wrapper.findAll('.tool-card')

      expect(toolCards[0].attributes('aria-checked')).toBe('false')
      expect(toolCards[1].attributes('aria-checked')).toBe('true')
      expect(toolCards[2].attributes('aria-checked')).toBe('false')
    })
  })

  // -------------------------------------------------------------------
  // Next button
  // -------------------------------------------------------------------
  describe('Next button', () => {
    it('is disabled when no tools are selected on step 0', () => {
      const wrapper = mountOverlay({ currentStep: 0, selectedTools: [] })
      const nextBtn = wrapper.find('.footer-btn-next')

      expect(nextBtn.attributes('disabled')).toBeDefined()
    })

    it('is enabled when at least one tool is selected', async () => {
      const wrapper = mountOverlay()
      const toolCards = wrapper.findAll('.tool-card')

      await toolCards[0].trigger('click')

      const nextBtn = wrapper.find('.footer-btn-next')
      expect(nextBtn.attributes('disabled')).toBeUndefined()
    })

    it('emits step-complete with tool data when clicked on step 0', async () => {
      const wrapper = mountOverlay()
      const toolCards = wrapper.findAll('.tool-card')

      await toolCards[0].trigger('click')

      const nextBtn = wrapper.find('.footer-btn-next')
      await nextBtn.trigger('click')

      const stepCompleteEvents = wrapper.emitted('step-complete')
      expect(stepCompleteEvents).toBeTruthy()
      expect(stepCompleteEvents[0][0]).toEqual({
        step: 0,
        data: { tools: ['claude_code'] },
      })
    })

    it('emits update:currentStep with next step number', async () => {
      const wrapper = mountOverlay({ currentStep: 0 })
      const toolCards = wrapper.findAll('.tool-card')

      await toolCards[0].trigger('click')

      const nextBtn = wrapper.find('.footer-btn-next')
      await nextBtn.trigger('click')

      const stepEvents = wrapper.emitted('update:currentStep')
      expect(stepEvents).toBeTruthy()
      expect(stepEvents[0][0]).toBe(1)
    })

    it('includes all selected tools in step-complete payload', async () => {
      const wrapper = mountOverlay()
      const toolCards = wrapper.findAll('.tool-card')

      await toolCards[0].trigger('click')
      await toolCards[1].trigger('click')

      const nextBtn = wrapper.find('.footer-btn-next')
      await nextBtn.trigger('click')

      const payload = wrapper.emitted('step-complete')[0][0]
      expect(payload.data.tools).toEqual(['claude_code', 'codex_cli'])
    })

    it('does not emit when button is disabled', async () => {
      const wrapper = mountOverlay({ currentStep: 0, selectedTools: [] })
      const nextBtn = wrapper.find('.footer-btn-next')

      await nextBtn.trigger('click')

      expect(wrapper.emitted('step-complete')).toBeUndefined()
      expect(wrapper.emitted('update:currentStep')).toBeUndefined()
    })

    it('is enabled on placeholder steps regardless of tool selection', () => {
      const wrapper = mountOverlay({ currentStep: 1, selectedTools: [] })
      const nextBtn = wrapper.find('.footer-btn-next')

      expect(nextBtn.attributes('disabled')).toBeUndefined()
    })

    it('shows "Finish" text on the last step', () => {
      const wrapper = mountOverlay({ currentStep: 3 })
      const nextBtn = wrapper.find('.footer-btn-next')

      expect(nextBtn.text()).toBe('Finish')
    })

    it('shows "Next" text on non-last steps', () => {
      const wrapper = mountOverlay({ currentStep: 0, selectedTools: ['claude_code'] })
      const nextBtn = wrapper.find('.footer-btn-next')

      expect(nextBtn.text()).toBe('Next')
    })
  })

  // -------------------------------------------------------------------
  // Dismiss
  // -------------------------------------------------------------------
  describe('Dismiss', () => {
    it('emits dismiss when close button is clicked', async () => {
      const wrapper = mountOverlay()
      const closeBtn = wrapper.find('[aria-label="Close setup wizard"]')

      await closeBtn.trigger('click')

      expect(wrapper.emitted('dismiss')).toBeTruthy()
    })

    it('emits update:modelValue with false when close button is clicked', async () => {
      const wrapper = mountOverlay()
      const closeBtn = wrapper.find('[aria-label="Close setup wizard"]')

      await closeBtn.trigger('click')

      const modelEvents = wrapper.emitted('update:modelValue')
      expect(modelEvents).toBeTruthy()
      expect(modelEvents[0][0]).toBe(false)
    })
  })

  // -------------------------------------------------------------------
  // Back button
  // -------------------------------------------------------------------
  describe('Back button', () => {
    it('is not visible on step 0', () => {
      const wrapper = mountOverlay({ currentStep: 0 })
      const backBtn = wrapper.find('.footer-btn-back')

      expect(backBtn.exists()).toBe(false)
    })

    it('is visible on step > 0', () => {
      const wrapper = mountOverlay({ currentStep: 1 })
      const backBtn = wrapper.find('.footer-btn-back')

      expect(backBtn.exists()).toBe(true)
    })

    it('emits update:currentStep with previous step number when clicked', async () => {
      const wrapper = mountOverlay({ currentStep: 2 })
      const backBtn = wrapper.find('.footer-btn-back')

      await backBtn.trigger('click')

      const stepEvents = wrapper.emitted('update:currentStep')
      expect(stepEvents).toBeTruthy()
      expect(stepEvents[0][0]).toBe(1)
    })
  })

  // -------------------------------------------------------------------
  // Placeholder steps
  // -------------------------------------------------------------------
  describe('Placeholder steps', () => {
    it('step 1 shows placeholder text about 0855d', () => {
      const wrapper = mountOverlay({ currentStep: 1 })

      expect(wrapper.find('.placeholder-text').text()).toContain('0855d')
    })

    it('step 2 shows placeholder text about 0855e', () => {
      const wrapper = mountOverlay({ currentStep: 2 })

      expect(wrapper.find('.placeholder-text').text()).toContain('0855e')
    })

    it('step 3 shows placeholder text about 0855f', () => {
      const wrapper = mountOverlay({ currentStep: 3 })

      expect(wrapper.find('.placeholder-text').text()).toContain('0855f')
    })
  })

  // -------------------------------------------------------------------
  // Accessibility
  // -------------------------------------------------------------------
  describe('Accessibility', () => {
    it('has role="dialog" and aria-modal on the overlay', () => {
      const wrapper = mountOverlay()
      const overlay = wrapper.find('.setup-wizard-overlay')

      expect(overlay.attributes('role')).toBe('dialog')
      expect(overlay.attributes('aria-modal')).toBe('true')
    })

    it('tool cards have role="checkbox" and aria-checked attributes', () => {
      const wrapper = mountOverlay()
      const toolCards = wrapper.findAll('.tool-card')

      for (const card of toolCards) {
        expect(card.attributes('role')).toBe('checkbox')
        expect(card.attributes('aria-checked')).toBeDefined()
      }
    })

    it('tool cards have aria-label matching tool name', () => {
      const wrapper = mountOverlay()
      const toolCards = wrapper.findAll('.tool-card')

      expect(toolCards[0].attributes('aria-label')).toBe('Claude Code')
      expect(toolCards[1].attributes('aria-label')).toBe('Codex CLI')
      expect(toolCards[2].attributes('aria-label')).toBe('Gemini CLI')
    })

    it('progress bar has correct role and aria attributes', () => {
      const wrapper = mountOverlay({ currentStep: 1 })
      const progressBar = wrapper.find('[role="progressbar"]')

      expect(progressBar.exists()).toBe(true)
      expect(progressBar.attributes('aria-valuenow')).toBe('1')
      expect(progressBar.attributes('aria-valuemin')).toBe('0')
      expect(progressBar.attributes('aria-valuemax')).toBe('3')
    })
  })
})
