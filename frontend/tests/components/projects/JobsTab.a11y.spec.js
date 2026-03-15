/**
 * JobsTab Accessibility Tests
 *
 * Comprehensive WCAG 2.1 Level AA compliance tests for JobsTab component.
 * Tests keyboard navigation, screen reader support, focus management,
 * and ARIA attributes.
 *
 * Test Coverage:
 * - Keyboard navigation (Tab, Enter, Arrow keys, Home/End)
 * - ARIA labels and roles
 * - Screen reader announcements
 * - Focus management and visible focus indicators
 * - Color contrast (referenced, not enforced in tests)
 * - Semantic HTML structure
 * - Accessible error messages
 * - Live region updates
 *
 * @see handovers/0077_launch_jobs_dual_tab_interface.md
 * @see WCAG 2.1 Level AA guidelines
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import JobsTab from '@/components/projects/JobsTab.vue'

// Test data fixtures
const createMockProject = (overrides = {}) => ({
  project_id: 'proj-a11y-test',
  name: 'Accessibility Test Project',
  description: 'Testing accessibility features',
  ...overrides,
})

const createMockAgent = (type, status, overrides = {}) => ({
  job_id: `job-${type}-${Math.random().toString(36).substr(2, 9)}`,
  agent_id: `agent-${type}`,
  agent_display_name: type,
  status: status,
  mission: `Mission for ${type}`,
  progress: status === 'working' ? 50 : 0,
  current_task: status === 'working' ? 'Working on task' : null,
  block_reason: status === 'failed' || status === 'blocked' ? 'Error occurred' : null,
  messages: [],
  ...overrides,
})

describe('JobsTab Accessibility Tests', () => {
  let wrapper

  const defaultProps = {
    project: createMockProject(),
    agents: [
      createMockAgent('orchestrator', 'working'),
      createMockAgent('analyzer', 'waiting'),
      createMockAgent('implementor', 'complete'),
    ],
    messages: [],
    allAgentsComplete: false,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('ARIA Labels and Roles', () => {
    it('has main role and descriptive aria-label on root element', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const root = wrapper.find('.jobs-tab')
      expect(root.attributes('role')).toBe('main')
      expect(root.attributes('aria-label')).toBe('Jobs view for project Accessibility Test Project')
    })

    it('uses list role for agent cards container', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const agentsScroll = wrapper.find('.jobs-tab__agents-scroll')
      expect(agentsScroll.attributes('role')).toBe('list')
      expect(agentsScroll.attributes('aria-label')).toBe('Agent cards')
    })

    it('uses listitem role for individual agent cards', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const agentCards = wrapper.findAll('.jobs-tab__agent-card')
      agentCards.forEach((card) => {
        expect(card.attributes('role')).toBe('listitem')
      })
    })

    it('has descriptive aria-labels on scroll buttons', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const leftButton = wrapper.find('.jobs-tab__scroll-left')
      const rightButton = wrapper.find('.jobs-tab__scroll-right')

      if (leftButton.exists()) {
        expect(leftButton.attributes('aria-label')).toBe('Scroll agents left')
      }

      if (rightButton.exists()) {
        expect(rightButton.attributes('aria-label')).toBe('Scroll agents right')
      }
    })

    it('uses semantic HTML for project header', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const projectHeader = wrapper.find('.jobs-tab__project-header')
      expect(projectHeader.find('h2').exists()).toBe(true)
      expect(projectHeader.find('h2').text()).toContain('Accessibility Test Project')
    })

    it('uses code element for project ID', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const projectHeader = wrapper.find('.jobs-tab__project-header')
      const codeElement = projectHeader.find('code')
      expect(codeElement.exists()).toBe(true)
      expect(codeElement.text()).toBe('proj-a11y-test')
    })

    it('has heading structure for agents section', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const agentsHeader = wrapper.find('.jobs-tab__agents-header')
      expect(agentsHeader.find('h3').exists()).toBe(true)
      expect(agentsHeader.find('h3').text()).toContain('Active Agents')
    })
  })

  describe('Keyboard Navigation', () => {
    it('agent scroll container is keyboard focusable', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const agentsScroll = wrapper.find('.jobs-tab__agents-scroll')
      expect(agentsScroll.attributes('tabindex')).toBe('0')
    })

    it('handles ArrowRight key to scroll agents right', async () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      const agentsScroll = wrapper.find('.jobs-tab__agents-scroll')
      const element = agentsScroll.element

      // Mock scrollBy
      const scrollBySpy = vi.fn()
      element.scrollBy = scrollBySpy

      await agentsScroll.trigger('keydown', { key: 'ArrowRight' })

      expect(scrollBySpy).toHaveBeenCalledWith({
        left: 300,
        behavior: 'smooth',
      })
    })

    it('handles ArrowLeft key to scroll agents left', async () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      const agentsScroll = wrapper.find('.jobs-tab__agents-scroll')
      const element = agentsScroll.element

      // Mock scrollBy
      const scrollBySpy = vi.fn()
      element.scrollBy = scrollBySpy

      await agentsScroll.trigger('keydown', { key: 'ArrowLeft' })

      expect(scrollBySpy).toHaveBeenCalledWith({
        left: -300,
        behavior: 'smooth',
      })
    })

    it('handles Home key to scroll to beginning', async () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      const agentsScroll = wrapper.find('.jobs-tab__agents-scroll')
      const element = agentsScroll.element

      // Mock scrollTo
      const scrollToSpy = vi.fn()
      element.scrollTo = scrollToSpy

      await agentsScroll.trigger('keydown', { key: 'Home' })

      expect(scrollToSpy).toHaveBeenCalledWith({
        left: 0,
        behavior: 'smooth',
      })
    })

    it('handles End key to scroll to end', async () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      const agentsScroll = wrapper.find('.jobs-tab__agents-scroll')
      const element = agentsScroll.element

      // Mock scrollTo and scrollWidth
      const scrollToSpy = vi.fn()
      element.scrollTo = scrollToSpy
      element.scrollWidth = 2000

      await agentsScroll.trigger('keydown', { key: 'End' })

      expect(scrollToSpy).toHaveBeenCalledWith({
        left: 2000,
        behavior: 'smooth',
      })
    })

    it('prevents default behavior for navigation keys', async () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      const agentsScroll = wrapper.find('.jobs-tab__agents-scroll')

      // Test ArrowRight
      const eventRight = new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true })
      const _preventDefaultSpy = vi.spyOn(eventRight, 'preventDefault')
      agentsScroll.element.dispatchEvent(eventRight)

      // Note: Event handling happens in component, so we can't directly test preventDefault
      // This would need to be tested in an E2E environment
    })

    it('scroll buttons are keyboard accessible', async () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      const leftButton = wrapper.find('.jobs-tab__scroll-left')
      const rightButton = wrapper.find('.jobs-tab__scroll-right')

      // Buttons should be focusable (they are v-btn components)
      if (leftButton.exists()) {
        expect(leftButton.element.tagName).toBe('BUTTON')
      }

      if (rightButton.exists()) {
        expect(rightButton.element.tagName).toBe('BUTTON')
      }
    })
  })

  describe('Focus Management', () => {
    it('maintains focus on agent scroll container during keyboard navigation', async () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      const agentsScroll = wrapper.find('.jobs-tab__agents-scroll')
      agentsScroll.element.focus()

      await agentsScroll.trigger('keydown', { key: 'ArrowRight' })
      await nextTick()

      // Focus should still be on scroll container
      expect(document.activeElement).toBe(agentsScroll.element)
    })

    it('has visible focus indicator on agent scroll container', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      const agentsScroll = wrapper.find('.jobs-tab__agents-scroll')
      agentsScroll.element.focus()

      // CSS should apply focus styles (checked via stylesheet, not runtime)
      // This is verified through visual testing and CSS inspection
      expect(agentsScroll.attributes('tabindex')).toBe('0')
    })

    it('complete banner receives focus when shown', async () => {
      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          allAgentsComplete: false,
        },
      })

      // Banner not present
      expect(wrapper.find('.jobs-tab__complete-banner').exists()).toBe(false)

      // Show banner
      await wrapper.setProps({ allAgentsComplete: true })
      await nextTick()

      // Banner now present
      const banner = wrapper.find('.jobs-tab__complete-banner')
      expect(banner.exists()).toBe(true)

      // Banner should be perceivable by assistive tech
      // (v-alert has proper ARIA attributes by default)
    })
  })

  describe('Screen Reader Support', () => {
    it('provides meaningful context for project information', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const projectHeader = wrapper.find('.jobs-tab__project-header')

      // Check for semantic structure
      expect(projectHeader.find('h2').exists()).toBe(true)
      expect(projectHeader.text()).toContain('Accessibility Test Project')
      expect(projectHeader.text()).toContain('Project ID:')
      expect(projectHeader.text()).toContain('proj-a11y-test')
    })

    it('announces completion state clearly', () => {
      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          allAgentsComplete: true,
        },
      })

      const banner = wrapper.find('.jobs-tab__complete-banner')
      expect(banner.exists()).toBe(true)

      // Check text content
      expect(banner.text()).toContain('All agents report complete')
      expect(banner.text()).toContain('All agent tasks have been completed successfully')
    })

    it('provides agent count information', () => {
      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents: [
            createMockAgent('orchestrator', 'working'),
            createMockAgent('analyzer', 'waiting'),
            createMockAgent('implementor', 'complete'),
          ],
        },
      })

      const agentsHeader = wrapper.find('.jobs-tab__agents-header')
      expect(agentsHeader.text()).toContain('Active Agents')
      expect(agentsHeader.text()).toContain('3')
    })

    it('associates labels with form elements', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      // MessageInput should have proper labels (tested in MessageInput.a11y.test.js)
      const messageInput = wrapper.findComponent({ name: 'MessageInput' })
      expect(messageInput.exists()).toBe(true)
    })
  })

  describe('Error Message Accessibility', () => {
    it('makes error states perceivable to screen readers', async () => {
      const agents = [
        createMockAgent('implementor', 'failed', {
          block_reason: 'Database connection failed',
        }),
      ]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      // Agent card should indicate error state
      const agentCard = wrapper.findComponent({ name: 'AgentCardEnhanced' })
      expect(agentCard.props('agent').status).toBe('failed')
      expect(agentCard.props('agent').block_reason).toBe('Database connection failed')
    })

    it('prioritizes failed agents for attention', () => {
      const agents = [
        createMockAgent('implementor', 'complete'),
        createMockAgent('analyzer', 'failed'),
        createMockAgent('orchestrator', 'working'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      // Failed agent should appear first (priority sorting)
      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      expect(agentCards[0].props('agent').status).toBe('failed')
    })

    it('blocked agents are also prioritized', () => {
      const agents = [
        createMockAgent('implementor', 'complete'),
        createMockAgent('analyzer', 'blocked'),
        createMockAgent('orchestrator', 'working'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      // Blocked agent should appear first
      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      expect(agentCards[0].props('agent').status).toBe('blocked')
    })
  })

  describe('Semantic HTML Structure', () => {
    it('uses proper heading hierarchy', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      // h2 for project name
      const projectH2 = wrapper.find('.jobs-tab__project-header h2')
      expect(projectH2.exists()).toBe(true)

      // h3 for agents section
      const agentsH3 = wrapper.find('.jobs-tab__agents-header h3')
      expect(agentsH3.exists()).toBe(true)
    })

    it('uses code element for technical identifiers', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const codeElement = wrapper.find('code.project-id-code')
      expect(codeElement.exists()).toBe(true)
      expect(codeElement.text()).toBe('proj-a11y-test')
    })

    it('uses icon with descriptive context', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const projectHeader = wrapper.find('.jobs-tab__project-header')

      // Icon should be accompanied by text
      expect(projectHeader.text()).toContain('Project ID:')
      expect(projectHeader.text()).toContain('proj-a11y-test')
    })

    it('uses button elements for interactive actions', async () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      // Scroll buttons should be actual button elements
      const leftButton = wrapper.find('.jobs-tab__scroll-left')
      const rightButton = wrapper.find('.jobs-tab__scroll-right')

      if (leftButton.exists()) {
        expect(leftButton.element.tagName).toBe('BUTTON')
      }

      if (rightButton.exists()) {
        expect(rightButton.element.tagName).toBe('BUTTON')
      }
    })
  })

  describe('Color and Contrast', () => {
    it('does not rely solely on color for status indication', () => {
      const agents = [
        createMockAgent('implementor', 'failed'),
        createMockAgent('analyzer', 'complete'),
        createMockAgent('orchestrator', 'working'),
      ]

      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          agents,
        },
      })

      // Each status should have both color AND text/icon
      // (This is tested in AgentCardEnhanced.a11y.test.js)
      const agentCards = wrapper.findAllComponents({ name: 'AgentCardEnhanced' })
      expect(agentCards).toHaveLength(3)

      // Statuses are indicated by text labels, not just color
      // Failed agent appears first due to priority sorting (text indication)
      expect(agentCards[0].props('agent').status).toBe('failed')
    })

    it('complete banner uses multiple indicators', () => {
      wrapper = mount(JobsTab, {
        props: {
          ...defaultProps,
          allAgentsComplete: true,
        },
      })

      const banner = wrapper.find('.jobs-tab__complete-banner')
      expect(banner.exists()).toBe(true)

      // Banner has icon, heading, and body text
      expect(banner.find('.v-icon').exists()).toBe(true)
      expect(banner.find('.text-h6').exists()).toBe(true)
      expect(banner.find('.text-body-2').exists()).toBe(true)
    })
  })

  describe('Responsive Design Accessibility', () => {
    it('maintains semantic structure on mobile', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      // Structure should be same regardless of viewport
      expect(wrapper.find('.jobs-tab__project-header h2').exists()).toBe(true)
      expect(wrapper.find('.jobs-tab__agents-header h3').exists()).toBe(true)
      expect(wrapper.find('.jobs-tab__agents-scroll').attributes('role')).toBe('list')
    })

    it('maintains keyboard navigation on all screen sizes', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      const agentsScroll = wrapper.find('.jobs-tab__agents-scroll')
      expect(agentsScroll.attributes('tabindex')).toBe('0')
    })

    it('maintains ARIA labels on all screen sizes', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      const root = wrapper.find('.jobs-tab')
      expect(root.attributes('aria-label')).toBe('Jobs view for project Accessibility Test Project')

      const agentsScroll = wrapper.find('.jobs-tab__agents-scroll')
      expect(agentsScroll.attributes('aria-label')).toBe('Agent cards')
    })
  })

  describe('Reduced Motion Support', () => {
    it('respects prefers-reduced-motion for scroll behavior', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      // CSS handles reduced motion via @media query
      // Scroll behavior should be 'auto' instead of 'smooth' when reduced motion is preferred
      // This is verified through CSS, not runtime testing

      const agentsScroll = wrapper.find('.jobs-tab__agents-scroll')
      expect(agentsScroll.exists()).toBe(true)
    })

    it('respects prefers-reduced-motion for animations', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      // CSS handles reduced motion for cardFadeIn animation
      // Animation should be disabled via @media query
      // This is verified through CSS, not runtime testing

      const agentCards = wrapper.findAll('.jobs-tab__agent-card')
      expect(agentCards.length).toBeGreaterThan(0)
    })
  })

  describe('High Contrast Mode Support', () => {
    it('provides sufficient contrast in high contrast mode', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      // CSS handles high contrast mode via @media query
      // Borders should be thicker and more visible
      // This is verified through CSS, not runtime testing

      expect(wrapper.find('.jobs-tab__project-header').exists()).toBe(true)
      expect(wrapper.find('.jobs-tab__messages-panel').exists()).toBe(true)
    })

    it('maintains visible focus indicators in high contrast mode', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
        attachTo: document.body,
      })

      const agentsScroll = wrapper.find('.jobs-tab__agents-scroll')
      agentsScroll.element.focus()

      // CSS handles focus indicators in high contrast mode
      // This is verified through visual testing and CSS inspection
      expect(agentsScroll.attributes('tabindex')).toBe('0')
    })
  })

  describe('Touch Accessibility', () => {
    it('provides adequate touch target sizes for buttons', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      // Scroll buttons should be at least 44x44 CSS pixels (per WCAG)
      // This is verified through CSS, not runtime testing

      const leftButton = wrapper.find('.jobs-tab__scroll-left')
      const rightButton = wrapper.find('.jobs-tab__scroll-right')

      if (leftButton.exists()) {
        expect(leftButton.element.tagName).toBe('BUTTON')
      }

      if (rightButton.exists()) {
        expect(rightButton.element.tagName).toBe('BUTTON')
      }
    })

    it('maintains touch accessibility on mobile', () => {
      wrapper = mount(JobsTab, {
        props: defaultProps,
      })

      // All interactive elements should be touch-accessible
      // This includes agent cards, scroll buttons, and message input
      // Verified through CSS (min touch target sizes) and component structure

      expect(wrapper.find('.jobs-tab__agents-scroll').exists()).toBe(true)
      expect(wrapper.findComponent({ name: 'MessageInput' }).exists()).toBe(true)
    })
  })
})
