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
        SetupStep2Connect: { template: '<div class="step-connect">Step2Connect stub</div>' },
        SetupStep3Commands: { template: '<div class="step-commands">Step3Commands stub</div>' },
        SetupStep4Complete: { template: '<div class="step-complete">Step4Complete stub</div>' },
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

    it('displays the rail title "Set up GiljoAI"', () => {
      const wrapper = mountOverlay()

      // Gradient Rail redesign (FE-6259b): the old centered ".setup-wizard-title"
      // header only exists in learning mode now; setup mode's title lives in
      // the left rail (".rail-title").
      expect(wrapper.find('.rail-title').text()).toBe('Set up GiljoAI')
    })

    it('renders all 4 step labels in the Gradient Rail stepper', () => {
      const wrapper = mountOverlay()
      const labels = wrapper.findAll('.rail-node-label')

      expect(labels).toHaveLength(4)
      expect(labels[0].text()).toBe('Choose Tools')
      expect(labels[1].text()).toBe('Connect')
      expect(labels[2].text()).toBe('Install')
      expect(labels[3].text()).toBe('Launch')
    })

    it('renders 4 tool cards on step 0', () => {
      const wrapper = mountOverlay({ currentStep: 0 })
      const toolCards = wrapper.findAll('.tool-card')

      expect(toolCards).toHaveLength(4)
    })

    it('displays tool names and providers', () => {
      const wrapper = mountOverlay()
      const names = wrapper.findAll('.tool-name')
      const providers = wrapper.findAll('.tool-provider')

      expect(names[0].text()).toBe('Claude Code CLI')
      expect(names[1].text()).toBe('Codex CLI')
      expect(names[2].text()).toBe('Gemini CLI')
      expect(names[3].text()).toBe('Antigravity CLI')

      expect(providers[0].text()).toBe('by Anthropic')
      expect(providers[1].text()).toBe('by OpenAI')
      expect(providers[2].text()).toBe('by Google')
      expect(providers[3].text()).toBe('by Antigravity')
    })
  })

  // -------------------------------------------------------------------
  // Gradient Rail stepper (FE-6259b) — replaces the old horizontal
  // progress bar (.step-circle/.step-label/.step-connector-fill) with a
  // vertical rail of .rail-node elements plus one continuous .spine-fill.
  // -------------------------------------------------------------------
  describe('Gradient Rail stepper', () => {
    it('marks the active step rail-node with the --active class', () => {
      const wrapper = mountOverlay({ currentStep: 0 })
      const node = wrapper.find('[data-testid="rail-node-tools"]')

      expect(node.classes()).toContain('rail-node--active')
      expect(node.classes()).not.toContain('rail-node--done')
    })

    it('the active rail-node label reflects the current step', () => {
      const wrapper = mountOverlay({ currentStep: 0 })
      const node = wrapper.find('[data-testid="rail-node-tools"]')

      expect(node.classes()).toContain('rail-node--active')
      expect(node.find('.rail-node-label').text()).toBe('Choose Tools')
    })

    it('marks completed steps with the --done class', () => {
      const wrapper = mountOverlay({ currentStep: 2 })

      expect(wrapper.find('[data-testid="rail-node-tools"]').classes()).toContain('rail-node--done')
      expect(wrapper.find('[data-testid="rail-node-connect"]').classes()).toContain('rail-node--done')
      expect(wrapper.find('[data-testid="rail-node-install"]').classes()).toContain('rail-node--active')
    })

    it('leaves future steps without --done or --active (Gradient Rail has no separate future class)', () => {
      const wrapper = mountOverlay({ currentStep: 0 })
      for (const id of ['connect', 'install', 'launch']) {
        const node = wrapper.find(`[data-testid="rail-node-${id}"]`)
        expect(node.classes()).not.toContain('rail-node--done')
        expect(node.classes()).not.toContain('rail-node--active')
      }
    })

    it('the rail spine fill height tracks progress (replaces per-step connector fills)', () => {
      const wrapper = mountOverlay({ currentStep: 2 })
      const expectedPct = (Math.min(2, 3) / 3) * 100

      expect(wrapper.find('.spine-fill').attributes('style')).toContain(`height: ${expectedPct}%`)
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

    it('applies the tool-card--sel class to selected cards (Gradient Rail uses a class, not an inline custom property)', async () => {
      const wrapper = mountOverlay()
      const toolCards = wrapper.findAll('.tool-card')

      await toolCards[0].trigger('click')

      expect(toolCards[0].classes()).toContain('tool-card--sel')
    })

    it('does not apply tool-card--sel to unselected cards', () => {
      const wrapper = mountOverlay()
      const toolCards = wrapper.findAll('.tool-card')

      expect(toolCards[0].classes()).not.toContain('tool-card--sel')
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
      const nextBtn = wrapper.find('[data-testid="setup-next-btn"]')

      expect(nextBtn.attributes('disabled')).toBeDefined()
    })

    it('is enabled when at least one tool is selected', async () => {
      const wrapper = mountOverlay()
      const toolCards = wrapper.findAll('.tool-card')

      await toolCards[0].trigger('click')

      const nextBtn = wrapper.find('[data-testid="setup-next-btn"]')
      expect(nextBtn.attributes('disabled')).toBeUndefined()
    })

    it('emits step-complete with tool data when clicked on step 0', async () => {
      const wrapper = mountOverlay()
      const toolCards = wrapper.findAll('.tool-card')

      await toolCards[0].trigger('click')

      const nextBtn = wrapper.find('[data-testid="setup-next-btn"]')
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

      const nextBtn = wrapper.find('[data-testid="setup-next-btn"]')
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

      const nextBtn = wrapper.find('[data-testid="setup-next-btn"]')
      await nextBtn.trigger('click')

      const payload = wrapper.emitted('step-complete')[0][0]
      expect(payload.data.tools).toEqual(['claude_code', 'codex_cli'])
    })

    it('does not emit when button is disabled', async () => {
      const wrapper = mountOverlay({ currentStep: 0, selectedTools: [] })
      const nextBtn = wrapper.find('[data-testid="setup-next-btn"]')

      await nextBtn.trigger('click')

      expect(wrapper.emitted('step-complete')).toBeUndefined()
      expect(wrapper.emitted('update:currentStep')).toBeUndefined()
    })

    it('footer is visible on step 3 with Back and Finish buttons', () => {
      const wrapper = mountOverlay({ currentStep: 3, selectedTools: [] })
      // Gradient Rail redesign (FE-6259b): the footer chrome is ".wz-footer"
      // now (".setup-wizard-footer" only exists in the learning-mode panel).
      const footer = wrapper.find('.wz-footer')

      expect(footer.exists()).toBe(true)
    })

    it('shows "Finish" button on the last step (step 3)', () => {
      const wrapper = mountOverlay({ currentStep: 3 })
      const nextBtn = wrapper.find('[data-testid="setup-finish-btn"]')

      expect(nextBtn.exists()).toBe(true)
      expect(nextBtn.text()).toBe('Finish')
    })

    it('shows "Next" text on non-last steps', () => {
      const wrapper = mountOverlay({ currentStep: 0, selectedTools: ['claude_code'] })
      const nextBtn = wrapper.find('[data-testid="setup-next-btn"]')

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
      const backBtn = wrapper.find('.footer-back')

      expect(backBtn.exists()).toBe(false)
    })

    it('is visible on step > 0', () => {
      const wrapper = mountOverlay({ currentStep: 1 })
      const backBtn = wrapper.find('.footer-back')

      expect(backBtn.exists()).toBe(true)
    })

    it('emits update:currentStep with previous step number when clicked', async () => {
      const wrapper = mountOverlay({ currentStep: 2 })
      const backBtn = wrapper.find('.footer-back')

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
    it('step 1 renders SetupStep2Connect component (0855d)', () => {
      const wrapper = mountOverlay({ currentStep: 1, selectedTools: ['claude_code'] })

      expect(wrapper.find('.step-connect').exists()).toBe(true)
    })

    it('step 2 renders SetupStep3Commands component (0855e)', () => {
      const wrapper = mountOverlay({ currentStep: 2, selectedTools: ['claude_code'] })

      expect(wrapper.find('.step-commands').exists()).toBe(true)
    })

    it('step 3 renders SetupStep4Complete component (0855f)', () => {
      const wrapper = mountOverlay({ currentStep: 3 })

      expect(wrapper.find('.step-complete').exists()).toBe(true)
    })
  })

  // -------------------------------------------------------------------
  // Playwright test-hook reachability (INF-6246)
  // -------------------------------------------------------------------
  describe('Playwright hooks — Choose-Tools screen (INF-6246)', () => {
    it('each tool card renders data-testid=tool-select-{id}', () => {
      const wrapper = mountOverlay({ currentStep: 0 })
      const expectedIds = ['claude_code', 'codex_cli', 'gemini_cli', 'antigravity_cli']
      for (const id of expectedIds) {
        expect(wrapper.find(`[data-testid="tool-select-${id}"]`).exists()).toBe(true)
      }
    })

    it('tool-select-{id} hooks match the tool card count', () => {
      const wrapper = mountOverlay({ currentStep: 0 })
      const hooks = wrapper.findAll('[data-testid^="tool-select-"]')
      expect(hooks).toHaveLength(4)
    })

    it('renders data-testid=setup-next-btn on the Next button', () => {
      const wrapper = mountOverlay({ currentStep: 0 })
      expect(wrapper.find('[data-testid="setup-next-btn"]').exists()).toBe(true)
    })

    it('clicking tool-select-claude_code then setup-next-btn advances to step 1', async () => {
      const wrapper = mountOverlay({ currentStep: 0 })
      await wrapper.find('[data-testid="tool-select-claude_code"]').trigger('click')
      await wrapper.find('[data-testid="setup-next-btn"]').trigger('click')
      const stepEvents = wrapper.emitted('update:currentStep')
      expect(stepEvents).toBeTruthy()
      expect(stepEvents[stepEvents.length - 1]).toEqual([1])
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

      expect(toolCards[0].attributes('aria-label')).toBe('Claude Code CLI')
      expect(toolCards[1].attributes('aria-label')).toBe('Codex CLI')
      expect(toolCards[2].attributes('aria-label')).toBe('Gemini CLI')
    })

    it('the active rail-node carries aria-current="step" (Gradient Rail replaces the progressbar role)', () => {
      const wrapper = mountOverlay({ currentStep: 1 })

      expect(wrapper.find('[data-testid="rail-node-connect"]').attributes('aria-current')).toBe('step')
      expect(wrapper.find('[data-testid="rail-node-tools"]').attributes('aria-current')).toBeUndefined()
      expect(wrapper.find('[data-testid="rail-node-install"]').attributes('aria-current')).toBeUndefined()
    })
  })

  // -------------------------------------------------------------------
  // Learning mode (0855g)
  // -------------------------------------------------------------------
  describe('Learning mode', () => {
    it('displays "How to Use GiljoAI MCP" title when mode is learning', () => {
      const wrapper = mountOverlay({ mode: 'learning' })

      expect(wrapper.find('.setup-wizard-title').text()).toBe('How to Use GiljoAI MCP')
    })

    it('does not render the Gradient Rail stepper in learning mode', () => {
      const wrapper = mountOverlay({ mode: 'learning' })

      expect(wrapper.find('.wizard-rail').exists()).toBe(false)
    })

    it('does not render step content (tool cards) in learning mode', () => {
      const wrapper = mountOverlay({ mode: 'learning' })

      expect(wrapper.find('.step-tools').exists()).toBe(false)
      expect(wrapper.find('.tool-card').exists()).toBe(false)
    })

    it('renders 6 learning content sections', () => {
      const wrapper = mountOverlay({ mode: 'learning' })
      const sections = wrapper.findAll('.learning-section')

      expect(sections).toHaveLength(6)
    })

    it('renders section titles', () => {
      const wrapper = mountOverlay({ mode: 'learning' })
      const titles = wrapper.findAll('.section-title')

      expect(titles[0].text()).toBe('How GiljoAI Works')
      expect(titles[1].text()).toBe('Define Your Product')
      expect(titles[2].text()).toBe('Projects and Missions')
      expect(titles[3].text()).toBe('Skills and Agent Templates')
      expect(titles[4].text()).toBe('360 Memory')
      expect(titles[5].text()).toBe('Dashboard and Monitoring')
    })

    it('first section is expanded by default', () => {
      const wrapper = mountOverlay({ mode: 'learning' })
      const headers = wrapper.findAll('.learning-section-header')

      expect(headers[0].attributes('aria-expanded')).toBe('true')
      expect(headers[1].attributes('aria-expanded')).toBe('false')
    })

    it('toggles section on click', async () => {
      const wrapper = mountOverlay({ mode: 'learning' })
      const headers = wrapper.findAll('.learning-section-header')

      // Collapse the first (open) section
      await headers[0].trigger('click')
      expect(headers[0].attributes('aria-expanded')).toBe('false')

      // Expand the second section
      await headers[1].trigger('click')
      expect(headers[1].attributes('aria-expanded')).toBe('true')
    })

    it('shows "Got it" button in learning mode', () => {
      const wrapper = mountOverlay({ mode: 'learning' })
      const gotItBtn = wrapper.find('.footer-btn-gotit')

      expect(gotItBtn.exists()).toBe(true)
      expect(gotItBtn.text()).toBe('Got it')
    })

    it('does not show Next/Back buttons in learning mode', () => {
      const wrapper = mountOverlay({ mode: 'learning' })

      // .footer-next-btn is the shared class for both the Next and Finish
      // button variants (Gradient Rail redesign, FE-6259b).
      expect(wrapper.find('.footer-next-btn').exists()).toBe(false)
      expect(wrapper.find('.footer-back').exists()).toBe(false)
    })

    it('"Got it" emits dismiss and update:modelValue false', async () => {
      const wrapper = mountOverlay({ mode: 'learning' })
      const gotItBtn = wrapper.find('.footer-btn-gotit')

      await gotItBtn.trigger('click')

      expect(wrapper.emitted('dismiss')).toBeTruthy()
      const modelEvents = wrapper.emitted('update:modelValue')
      expect(modelEvents).toBeTruthy()
      expect(modelEvents[0][0]).toBe(false)
    })

    it('"Got it" does not emit step-complete', async () => {
      const wrapper = mountOverlay({ mode: 'learning' })
      const gotItBtn = wrapper.find('.footer-btn-gotit')

      await gotItBtn.trigger('click')

      expect(wrapper.emitted('step-complete')).toBeUndefined()
    })

    it('setup mode still shows the Gradient Rail stepper (regression)', () => {
      const wrapper = mountOverlay({ mode: 'setup' })

      expect(wrapper.find('.wizard-rail').exists()).toBe(true)
      expect(wrapper.find('.rail-title').text()).toBe('Set up GiljoAI')
    })

    it('close X button works in learning mode', async () => {
      const wrapper = mountOverlay({ mode: 'learning' })
      const closeBtn = wrapper.find('[aria-label="Close guide"]')

      expect(closeBtn.exists()).toBe(true)
      await closeBtn.trigger('click')

      expect(wrapper.emitted('dismiss')).toBeTruthy()
    })
  })
})
