/**
 * Unit tests for SetupStep4Complete component (Handover 0855f)
 * Covers launchpad card rendering, emission of complete events, and header content.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import SetupStep4Complete from '@/components/setup/SetupStep4Complete.vue'

const vuetify = createVuetify({ components, directives })

function mountStep4(props = {}) {
  return mount(SetupStep4Complete, {
    props,
    global: {
      plugins: [vuetify],
    },
  })
}

describe('SetupStep4Complete', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // -------------------------------------------------------------------
  // Rendering
  // -------------------------------------------------------------------
  describe('Rendering', () => {
    it('renders 3 launchpad cards', () => {
      const wrapper = mountStep4()
      const cards = wrapper.findAll('.launchpad-card')

      expect(cards).toHaveLength(3)
    })

    it('renders cards with correct titles', () => {
      const wrapper = mountStep4()
      const titles = wrapper.findAll('.card-title')

      expect(titles).toHaveLength(3)
      expect(titles[0].text()).toBe('Define Your Product')
      expect(titles[1].text()).toBe('Start a Project')
      expect(titles[2].text()).toBe('Track Your Work')
    })

    it('renders cards with correct button labels', () => {
      const wrapper = mountStep4()
      const buttons = wrapper.findAll('.card-btn')

      expect(buttons).toHaveLength(3)
      expect(buttons[0].text()).toBe('OPEN PRODUCTS')
      expect(buttons[1].text()).toBe('OPEN PROJECTS')
      expect(buttons[2].text()).toBe('OPEN TASKS')
    })

    it('renders success header with "You\'re all set!" text', () => {
      const wrapper = mountStep4()
      const title = wrapper.find('.complete-title')

      expect(title.exists()).toBe(true)
      expect(title.text()).toBe("You're all set!")
    })

    it('renders subtitle text about AI coding tools', () => {
      const wrapper = mountStep4()
      const subtitle = wrapper.find('.complete-subtitle')

      expect(subtitle.exists()).toBe(true)
      expect(subtitle.text()).toContain('AI coding tools')
      expect(subtitle.text()).toContain('connected and ready')
    })

    it('renders a "Go to Home" link', () => {
      const wrapper = mountStep4()
      const dashboardLink = wrapper.find('.dashboard-link')

      expect(dashboardLink.exists()).toBe(true)
      expect(dashboardLink.text()).toBe('Go to Home')
    })
  })

  // -------------------------------------------------------------------
  // Emit: complete
  // -------------------------------------------------------------------
  describe('Complete event emission', () => {
    it('click "OPEN PRODUCTS" emits complete with products action and route', async () => {
      const wrapper = mountStep4()
      const buttons = wrapper.findAll('.card-btn')

      await buttons[0].trigger('click')

      const events = wrapper.emitted('complete')
      expect(events).toBeTruthy()
      expect(events).toHaveLength(1)
      expect(events[0][0]).toEqual({ action: 'products', route: '/products' })
    })

    it('click "OPEN PROJECTS" emits complete with projects action and route', async () => {
      const wrapper = mountStep4()
      const buttons = wrapper.findAll('.card-btn')

      await buttons[1].trigger('click')

      const events = wrapper.emitted('complete')
      expect(events).toBeTruthy()
      expect(events).toHaveLength(1)
      expect(events[0][0]).toEqual({ action: 'projects', route: '/projects' })
    })

    it('click "OPEN TASKS" emits complete with tasks action and route', async () => {
      const wrapper = mountStep4()
      const buttons = wrapper.findAll('.card-btn')

      await buttons[2].trigger('click')

      const events = wrapper.emitted('complete')
      expect(events).toBeTruthy()
      expect(events).toHaveLength(1)
      expect(events[0][0]).toEqual({ action: 'tasks', route: '/tasks' })
    })

    it('click "Go to Home" emits complete with home action and route', async () => {
      const wrapper = mountStep4()
      const dashboardLink = wrapper.find('.dashboard-link')

      await dashboardLink.trigger('click')

      const events = wrapper.emitted('complete')
      expect(events).toBeTruthy()
      expect(events).toHaveLength(1)
      expect(events[0][0]).toEqual({ action: 'home', route: '/home' })
    })
  })
})
